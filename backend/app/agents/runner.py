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
            "tools": [
                {
                    "type": "web_search",
                    "search_context_size": settings.OPENAI_WEB_SEARCH_CONTEXT_SIZE,
                    "user_location": {
                        "type": "approximate",
                        "country": "BR",
                        "city": "Sao Paulo",
                        "region": "SP",
                        "timezone": "America/Sao_Paulo",
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
