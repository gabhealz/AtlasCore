import re
from html.parser import HTMLParser

CSS_ID_PATTERN_TEMPLATE = r"""\bid\s*=\s*["']{css_id}["']"""
CLICKABLE_TAGS = {"a", "button"}
VOID_TAGS = {
    "area",
    "base",
    "br",
    "col",
    "embed",
    "hr",
    "img",
    "input",
    "link",
    "meta",
    "param",
    "source",
    "track",
    "wbr",
}
OPTIONAL_END_TAG_START_RULES = {
    "dd": {"dd", "dt"},
    "dt": {"dd", "dt"},
    "li": {"li"},
    "option": {"optgroup", "option"},
    "p": {
        "address",
        "article",
        "aside",
        "blockquote",
        "details",
        "dialog",
        "div",
        "dl",
        "fieldset",
        "figcaption",
        "figure",
        "footer",
        "form",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "header",
        "hr",
        "li",
        "main",
        "nav",
        "ol",
        "p",
        "pre",
        "section",
        "table",
        "ul",
    },
    "tbody": {"tbody", "tfoot"},
    "td": {"td", "th", "tr"},
    "tfoot": {"tbody"},
    "th": {"td", "th", "tr"},
    "thead": {"tbody", "tfoot"},
    "tr": {"tbody", "tfoot", "tr"},
}
OPTIONAL_END_TAGS = set(OPTIONAL_END_TAG_START_RULES)


class HTMLValidationError(ValueError):
    def __init__(self, *, error_code: str, message: str):
        super().__init__(message)
        self.error_code = error_code
        self.message = message


class _HTMLStructureParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self._stack: list[str] = []
        self.clickable_ids: set[str] = set()
        self.seen_html = False
        self.seen_body = False

    def handle_starttag(self, tag: str, attrs) -> None:
        normalized_tag = tag.lower()
        self._auto_close_optional_tags_for_starttag(normalized_tag)
        if normalized_tag == "html":
            self.seen_html = True
        if normalized_tag == "body":
            self.seen_body = True
        self._register_clickable_id(normalized_tag, attrs)
        if normalized_tag not in VOID_TAGS:
            self._stack.append(normalized_tag)

    def handle_startendtag(self, tag: str, attrs) -> None:
        normalized_tag = tag.lower()
        if normalized_tag == "html":
            self.seen_html = True
        if normalized_tag == "body":
            self.seen_body = True
        self._register_clickable_id(normalized_tag, attrs)

    def handle_endtag(self, tag: str) -> None:
        normalized_tag = tag.lower()
        if normalized_tag in VOID_TAGS:
            return
        while self._stack and self._stack[-1] != normalized_tag:
            if self._stack[-1] in OPTIONAL_END_TAGS:
                self._stack.pop()
                continue

            raise HTMLValidationError(
                error_code="HTML_STRUCTURE_INVALID",
                message="O HTML gerado possui tags fora de ordem ou truncadas.",
            )

        if not self._stack:
            raise HTMLValidationError(
                error_code="HTML_STRUCTURE_INVALID",
                message="O HTML gerado possui fechamento de tag invalido.",
            )

        self._stack.pop()

    def _auto_close_optional_tags_for_starttag(self, next_tag: str) -> None:
        while self._stack:
            current_tag = self._stack[-1]
            start_rules = OPTIONAL_END_TAG_START_RULES.get(current_tag)
            if start_rules is None or next_tag not in start_rules:
                break
            self._stack.pop()

    def _register_clickable_id(self, tag: str, attrs) -> None:
        if tag not in CLICKABLE_TAGS:
            return

        for attr_name, attr_value in attrs:
            if attr_name != "id" or not isinstance(attr_value, str):
                continue

            normalized_id = attr_value.strip().lower()
            if normalized_id:
                self.clickable_ids.add(normalized_id)
            return

    def validate(self, html_content: str) -> None:
        self.feed(html_content)
        self.close()
        if self._stack:
            raise HTMLValidationError(
                error_code="HTML_STRUCTURE_INVALID",
                message="O HTML gerado ficou com tags abertas ou truncadas.",
            )
        if not self.seen_html or not self.seen_body:
            raise HTMLValidationError(
                error_code="HTML_STRUCTURE_INVALID",
                message=(
                    "O HTML gerado precisa conter um documento completo com "
                    "`<html>` e `<body>`."
                ),
            )


def validate_generated_html(
    *,
    html_content: str,
    required_css_ids: list[str] | None = None,
) -> None:
    normalized_html = html_content.strip()
    lower_html = normalized_html.lower()

    if not lower_html.startswith("<!doctype html"):
        raise HTMLValidationError(
            error_code="HTML_STRUCTURE_INVALID",
            message="O HTML gerado precisa iniciar com `<!DOCTYPE html>`.",
        )

    parser = _HTMLStructureParser()
    parser.validate(normalized_html)

    missing_css_ids: list[str] = []
    for css_id in required_css_ids or []:
        normalized_css_id = css_id.strip().lower()
        if not normalized_css_id:
            continue

        css_id_pattern = re.compile(
            CSS_ID_PATTERN_TEMPLATE.format(css_id=re.escape(normalized_css_id)),
            flags=re.IGNORECASE,
        )
        if not css_id_pattern.search(normalized_html):
            missing_css_ids.append(css_id)
            continue

        if normalized_css_id not in parser.clickable_ids:
            missing_css_ids.append(css_id)

    if missing_css_ids:
        missing_ids = ", ".join(missing_css_ids)
        raise HTMLValidationError(
            error_code="HTML_CSS_IDS_MISSING",
            message=(
                "O HTML gerado nao incluiu todos os IDs CSS obrigatorios do "
                "tracking em links ou botoes clicaveis: "
                f"{missing_ids}."
            ),
        )
