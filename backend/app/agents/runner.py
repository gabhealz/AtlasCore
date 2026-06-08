import asyncio
from dataclasses import dataclass
from typing import Any

from litellm import (
    APIConnectionError,
    APIError,
    AuthenticationError,
    BadRequestError,
    RateLimitError,
    ServiceUnavailableError,
    Timeout,
    acompletion,
)
from openai import AsyncOpenAI

from app.core.config import settings


@dataclass(frozen=True, slots=True)
class AgentRunResult:
    content: str
    attempt_count: int
    agent_name: str
    step_name: str
    model: str
    # Fontes reais consultadas pela ferramenta de web_search (queries + URLs
    # visitadas/citadas). Vazio quando a etapa nao usa pesquisa web.
    web_search_sources: tuple[dict[str, Any], ...] = ()


class AgentRunnerError(Exception):
    def __init__(
        self,
        *,
        error_code: str,
        message: str,
        attempt_count: int,
        retriable: bool,
        agent_name: str,
        step_name: str,
        model: str,
    ):
        super().__init__(message)
        self.error_code = error_code
        self.message = message
        self.attempt_count = attempt_count
        self.retriable = retriable
        self.agent_name = agent_name
        self.step_name = step_name
        self.model = model


class AgentRunner:
    def __init__(
        self,
        *,
        completion_fn=None,
        sleep_fn=None,
        api_key: str | None = None,
        model: str | None = None,
        research_model: str | None = None,
        timeout_seconds: float | None = None,
        max_retries: int | None = None,
        base_delay_seconds: float = 1.0,
        zero_data_retention_confirmed: bool | None = None,
        responses_create_fn=None,
    ):
        self._completion_fn = completion_fn or acompletion
        self._responses_create_fn = responses_create_fn
        self._sleep_fn = sleep_fn or asyncio.sleep
        self._api_key = api_key if api_key is not None else settings.OPENAI_API_KEY
        self._model = model or settings.OPENAI_MODEL
        configured_research_model = (
            research_model
            if research_model is not None
            else settings.OPENAI_RESEARCH_MODEL
        )
        self._research_model = configured_research_model.strip() or self._model
        self._timeout_seconds = (
            timeout_seconds
            if timeout_seconds is not None
            else settings.OPENAI_TIMEOUT_SECONDS
        )
        self._zero_data_retention_confirmed = (
            settings.OPENAI_ZERO_DATA_RETENTION_CONFIRMED
            if zero_data_retention_confirmed is None
            else zero_data_retention_confirmed
        )
        configured_max_retries = (
            max_retries if max_retries is not None else settings.OPENAI_MAX_RETRIES
        )
        self._max_attempts = max(1, int(configured_max_retries))
        self._base_delay_seconds = base_delay_seconds

    @property
    def model(self) -> str:
        return self._model

    async def run(
        self,
        *,
        agent_name: str,
        step_name: str,
        system_prompt: str,
        user_prompt: str,
        response_format: dict[str, Any] | None = None,
        enable_web_search: bool = False,
    ) -> AgentRunResult:
        self._validate_configuration(agent_name=agent_name, step_name=step_name)
        if enable_web_search and settings.OPENAI_ENABLE_WEB_SEARCH:
            return await self._run_with_web_search(
                agent_name=agent_name,
                step_name=step_name,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_format=response_format,
            )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        for attempt_count in range(1, self._max_attempts + 1):
            try:
                response = await self._completion_fn(
                    api_key=self._api_key,
                    model=self._model,
                    timeout=self._timeout_seconds,
                    messages=messages,
                    response_format=response_format,
                )
                content = self._extract_content(response)
                if not content:
                    raise AgentRunnerError(
                        error_code="OPENAI_EMPTY_RESPONSE",
                        message="A chamada de IA retornou uma resposta vazia.",
                        attempt_count=attempt_count,
                        retriable=False,
                        agent_name=agent_name,
                        step_name=step_name,
                        model=self._model,
                    )

                return AgentRunResult(
                    content=content,
                    attempt_count=attempt_count,
                    agent_name=agent_name,
                    step_name=step_name,
                    model=self._model,
                )
            except AgentRunnerError:
                raise
            except Exception as exc:
                runner_error = self._classify_exception(
                    exc=exc,
                    attempt_count=attempt_count,
                    agent_name=agent_name,
                    step_name=step_name,
                )
                if runner_error.retriable and attempt_count < self._max_attempts:
                    await self._sleep_fn(self._calculate_delay(attempt_count))
                    continue

                raise runner_error

        raise AgentRunnerError(
            error_code="AGENT_RUNNER_FAILED",
            message="O runner de IA falhou sem retornar um resultado valido.",
            attempt_count=self._max_attempts,
            retriable=False,
            agent_name=agent_name,
            step_name=step_name,
            model=self._model,
        )

    async def _run_with_web_search(
        self,
        *,
        agent_name: str,
        step_name: str,
        system_prompt: str,
        user_prompt: str,
        response_format: dict[str, Any] | None = None,
    ) -> AgentRunResult:
        for attempt_count in range(1, self._max_attempts + 1):
            try:
                response = await self._create_web_search_response(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    response_format=response_format,
                )
                incomplete_reason = self._incomplete_reason(response)
                if incomplete_reason is not None:
                    # A resposta truncou (ex.: estourou max_output_tokens). Nao
                    # salvar documento parcial: tratar como retriavel para tentar
                    # de novo em vez de mascarar com placeholders.
                    runner_error = self._build_retryable_error(
                        error_code="OPENAI_RESPONSE_INCOMPLETE",
                        attempt_count=attempt_count,
                        agent_name=agent_name,
                        step_name=step_name,
                    )
                    if attempt_count < self._max_attempts:
                        await self._sleep_fn(self._calculate_delay(attempt_count))
                        continue
                    raise AgentRunnerError(
                        error_code="OPENAI_RESPONSE_INCOMPLETE",
                        message=(
                            "A pesquisa com IA retornou um documento incompleto "
                            f"(motivo: {incomplete_reason}). Aumente "
                            "OPENAI_MAX_OUTPUT_TOKENS ou reduza o escopo da etapa."
                        ),
                        attempt_count=attempt_count,
                        retriable=False,
                        agent_name=agent_name,
                        step_name=step_name,
                        model=self._research_model,
                    )
                content = self._extract_responses_content(response)
                if not content:
                    raise AgentRunnerError(
                        error_code="OPENAI_EMPTY_RESPONSE",
                        message="A chamada de IA com pesquisa web retornou vazia.",
                        attempt_count=attempt_count,
                        retriable=False,
                        agent_name=agent_name,
                        step_name=step_name,
                        model=self._research_model,
                    )

                return AgentRunResult(
                    content=content,
                    attempt_count=attempt_count,
                    agent_name=agent_name,
                    step_name=step_name,
                    model=self._research_model,
                    web_search_sources=self._extract_web_search_sources(response),
                )
            except AgentRunnerError:
                raise
            except Exception as exc:
                runner_error = self._classify_exception(
                    exc=exc,
                    attempt_count=attempt_count,
                    agent_name=agent_name,
                    step_name=step_name,
                )
                if runner_error.retriable and attempt_count < self._max_attempts:
                    await self._sleep_fn(self._calculate_delay(attempt_count))
                    continue

                raise AgentRunnerError(
                    error_code=runner_error.error_code,
                    message=runner_error.message,
                    attempt_count=runner_error.attempt_count,
                    retriable=runner_error.retriable,
                    agent_name=runner_error.agent_name,
                    step_name=runner_error.step_name,
                    model=self._research_model,
                )

        raise AgentRunnerError(
            error_code="AGENT_RUNNER_FAILED",
            message="A chamada de IA com pesquisa web falhou sem resultado valido.",
            attempt_count=self._max_attempts,
            retriable=False,
            agent_name=agent_name,
            step_name=step_name,
            model=self._research_model,
        )

    async def _create_web_search_response(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_format: dict[str, Any] | None,
    ) -> Any:
        create_fn = self._responses_create_fn
        if create_fn is None:
            client = AsyncOpenAI(api_key=self._api_key, timeout=self._timeout_seconds)
            create_fn = client.responses.create

        payload: dict[str, Any] = {
            "model": self._research_model,
            "instructions": system_prompt,
            "input": user_prompt,
            # Teto alto para o documento de 14 secoes nao truncar no meio.
            "max_output_tokens": settings.OPENAI_MAX_OUTPUT_TOKENS,
            "tools": [
                {
                    "type": "web_search",
                    "search_context_size": settings.OPENAI_WEB_SEARCH_CONTEXT_SIZE,
                    # Localizacao apenas em nivel de pais. NAO fixar cidade/regiao:
                    # a clinica pode ser de qualquer cidade do Brasil e fixar Sao
                    # Paulo enviesava a busca local para a cidade errada. A
                    # localidade real vem das consultas que o modelo monta com a
                    # cidade extraida do briefing (ex.: "dermatologista Curitiba").
                    "user_location": {
                        "type": "approximate",
                        "country": "BR",
                    },
                }
            ],
            "tool_choice": "required",
            "include": ["web_search_call.action.sources"],
        }
        responses_format = self._convert_response_format_for_responses(
            response_format
        )
        if responses_format is not None:
            payload["text"] = {"format": responses_format}

        return await create_fn(**payload)

    @staticmethod
    def _convert_response_format_for_responses(
        response_format: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        if not response_format:
            return None

        if response_format.get("type") != "json_schema":
            return response_format

        json_schema = response_format.get("json_schema")
        if not isinstance(json_schema, dict):
            return None

        return {
            "type": "json_schema",
            "name": json_schema.get("name", "structured_response"),
            "schema": json_schema.get("schema", {}),
            "strict": json_schema.get("strict", True),
        }

    def _validate_configuration(self, *, agent_name: str, step_name: str) -> None:
        if not self._api_key.strip():
            raise AgentRunnerError(
                error_code="OPENAI_CONFIG_MISSING",
                message="OPENAI_API_KEY nao configurada para executar o pipeline.",
                attempt_count=0,
                retriable=False,
                agent_name=agent_name,
                step_name=step_name,
                model=self._model,
            )

        if not self._model.strip():
            raise AgentRunnerError(
                error_code="OPENAI_MODEL_MISSING",
                message="OPENAI_MODEL nao configurado para executar o pipeline.",
                attempt_count=0,
                retriable=False,
                agent_name=agent_name,
                step_name=step_name,
                model=self._model,
            )

        if not self._zero_data_retention_confirmed:
            raise AgentRunnerError(
                error_code="OPENAI_ZDR_NOT_CONFIRMED",
                message=(
                    "Zero Data Retention da OpenAI ainda nao foi confirmado "
                    "para este ambiente. Configure "
                    "OPENAI_ZERO_DATA_RETENTION_CONFIRMED=true apos validar "
                    "a politica da conta antes de executar o pipeline."
                ),
                attempt_count=0,
                retriable=False,
                agent_name=agent_name,
                step_name=step_name,
                model=self._model,
            )

    def _calculate_delay(self, attempt_count: int) -> float:
        return self._base_delay_seconds * (2 ** (attempt_count - 1))

    def _classify_exception(
        self,
        *,
        exc: Exception,
        attempt_count: int,
        agent_name: str,
        step_name: str,
    ) -> AgentRunnerError:
        status_code = self._extract_status_code(exc)
        class_name = exc.__class__.__name__.lower()
        message = str(exc).strip()

        if (
            isinstance(exc, RateLimitError)
            or status_code == 429
            or "ratelimit" in class_name
            or "rate_limit" in class_name
        ):
            return self._build_retryable_error(
                error_code="OPENAI_RATE_LIMIT",
                attempt_count=attempt_count,
                agent_name=agent_name,
                step_name=step_name,
            )

        if (
            isinstance(exc, Timeout)
            or status_code == 408
            or "timeout" in class_name
            or "timed out" in message.lower()
        ):
            return self._build_retryable_error(
                error_code="OPENAI_TIMEOUT",
                attempt_count=attempt_count,
                agent_name=agent_name,
                step_name=step_name,
            )

        if (
            isinstance(exc, APIConnectionError)
            or "connection" in class_name
            or "connection" in message.lower()
        ):
            return self._build_retryable_error(
                error_code="OPENAI_CONNECTION_ERROR",
                attempt_count=attempt_count,
                agent_name=agent_name,
                step_name=step_name,
            )

        if (
            isinstance(exc, ServiceUnavailableError)
            or status_code in {500, 502, 503, 504}
        ):
            return self._build_retryable_error(
                error_code="OPENAI_SERVICE_UNAVAILABLE",
                attempt_count=attempt_count,
                agent_name=agent_name,
                step_name=step_name,
            )

        if isinstance(exc, AuthenticationError) or status_code in {401, 403}:
            return AgentRunnerError(
                error_code="OPENAI_AUTHENTICATION_ERROR",
                message="Falha de autenticacao com o provedor de IA.",
                attempt_count=attempt_count,
                retriable=False,
                agent_name=agent_name,
                step_name=step_name,
                model=self._model,
            )

        if isinstance(exc, BadRequestError) or status_code == 400:
            return AgentRunnerError(
                error_code="OPENAI_BAD_REQUEST",
                message="A chamada de IA foi rejeitada por payload invalido.",
                attempt_count=attempt_count,
                retriable=False,
                agent_name=agent_name,
                step_name=step_name,
                model=self._model,
            )

        if isinstance(exc, APIError):
            if status_code is None or status_code >= 500:
                return self._build_retryable_error(
                    error_code="OPENAI_API_ERROR",
                    attempt_count=attempt_count,
                    agent_name=agent_name,
                    step_name=step_name,
                )

            if status_code == 400:
                return AgentRunnerError(
                    error_code="OPENAI_BAD_REQUEST",
                    message="A chamada de IA foi rejeitada por payload invalido.",
                    attempt_count=attempt_count,
                    retriable=False,
                    agent_name=agent_name,
                    step_name=step_name,
                    model=self._model,
                )

        return AgentRunnerError(
            error_code="AGENT_RUNNER_FAILED",
            message="O pipeline falhou ao executar a chamada de IA.",
            attempt_count=attempt_count,
            retriable=False,
            agent_name=agent_name,
            step_name=step_name,
            model=self._model,
        )

    def _build_retryable_error(
        self,
        *,
        error_code: str,
        attempt_count: int,
        agent_name: str,
        step_name: str,
    ) -> AgentRunnerError:
        return AgentRunnerError(
            error_code=error_code,
            message=(
                "Nao foi possivel concluir a chamada de IA apos "
                f"{attempt_count} tentativas."
            ),
            attempt_count=attempt_count,
            retriable=True,
            agent_name=agent_name,
            step_name=step_name,
            model=self._model,
        )

    @staticmethod
    def _extract_status_code(exc: Exception) -> int | None:
        status_code = getattr(exc, "status_code", None)
        if isinstance(status_code, int):
            return status_code

        response = getattr(exc, "response", None)
        response_status = getattr(response, "status_code", None)
        if isinstance(response_status, int):
            return response_status

        return None

    @staticmethod
    def _extract_content(response: Any) -> str:
        if isinstance(response, dict):
            choices = response.get("choices", [])
            if choices:
                first_choice = choices[0]
                if isinstance(first_choice, dict):
                    message = first_choice.get("message", {})
                    if isinstance(message, dict):
                        content = message.get("content")
                        return content if isinstance(content, str) else ""

        choices = getattr(response, "choices", None)
        if choices:
            first_choice = choices[0]
            message = getattr(first_choice, "message", None)
            content = getattr(message, "content", None)
            return content if isinstance(content, str) else ""

        return ""

    @staticmethod
    def _incomplete_reason(response: Any) -> str | None:
        """Retorna o motivo se a Responses API truncou a saida, senao None.

        A Responses API marca `status == "incomplete"` com
        `incomplete_details.reason` (ex.: "max_output_tokens") quando a resposta
        nao foi concluida. Funciona tanto para objeto quanto para dict.
        """
        if isinstance(response, dict):
            status = response.get("status")
            details = response.get("incomplete_details") or {}
            reason = (
                details.get("reason") if isinstance(details, dict) else None
            )
        else:
            status = getattr(response, "status", None)
            details = getattr(response, "incomplete_details", None)
            reason = getattr(details, "reason", None) if details else None

        if status == "incomplete":
            return str(reason) if reason else "incomplete"
        return None

    @staticmethod
    def _extract_web_search_sources(response: Any) -> tuple[dict[str, Any], ...]:
        """Coleta as fontes reais do web_search: queries executadas e URLs
        visitadas/citadas. Best-effort e tolerante ao formato (objeto ou dict)."""

        def _get(obj: Any, key: str) -> Any:
            if isinstance(obj, dict):
                return obj.get(key)
            return getattr(obj, key, None)

        try:
            items = list(_get(response, "output") or [])
        except TypeError:
            return ()

        collected: list[dict[str, Any]] = []
        seen: set[tuple[str | None, str]] = set()

        def _add(url: Any, title: Any, query: Any) -> None:
            if not isinstance(url, str) or not url.startswith(("http://", "https://")):
                return
            normalized_query = query.strip() if isinstance(query, str) else None
            key = (normalized_query, url)
            if key in seen:
                return
            seen.add(key)
            entry: dict[str, Any] = {"url": url}
            if isinstance(title, str) and title.strip():
                entry["title"] = title.strip()
            if normalized_query:
                entry["query"] = normalized_query
            collected.append(entry)

        for item in items:
            if _get(item, "type") == "web_search_call":
                action = _get(item, "action")
                query = _get(action, "query")
                try:
                    sources_iter = list(_get(action, "sources") or [])
                except TypeError:
                    sources_iter = []
                if not sources_iter and isinstance(query, str) and query.strip():
                    marker = (query.strip(), "")
                    if marker not in seen:
                        seen.add(marker)
                        collected.append({"query": query.strip()})
                for src in sources_iter:
                    _add(_get(src, "url"), _get(src, "title"), query)
                continue

            try:
                content_iter = list(_get(item, "content") or [])
            except TypeError:
                content_iter = []
            for content_item in content_iter:
                try:
                    ann_iter = list(_get(content_item, "annotations") or [])
                except TypeError:
                    ann_iter = []
                for ann in ann_iter:
                    if _get(ann, "type") == "url_citation":
                        _add(_get(ann, "url"), _get(ann, "title"), None)

        return tuple(collected)

    @staticmethod
    def _extract_responses_content(response: Any) -> str:
        output_text = getattr(response, "output_text", None)
        if isinstance(output_text, str):
            return output_text

        if isinstance(response, dict):
            output_text = response.get("output_text")
            if isinstance(output_text, str):
                return output_text

            for output_item in response.get("output", []):
                if not isinstance(output_item, dict):
                    continue
                for content_item in output_item.get("content", []):
                    if not isinstance(content_item, dict):
                        continue
                    text = content_item.get("text")
                    if isinstance(text, str):
                        return text

        output_items = getattr(response, "output", None)
        if output_items:
            for output_item in output_items:
                content_items = getattr(output_item, "content", None)
                if not content_items:
                    continue
                for content_item in content_items:
                    text = getattr(content_item, "text", None)
                    if isinstance(text, str):
                        return text

        return ""
