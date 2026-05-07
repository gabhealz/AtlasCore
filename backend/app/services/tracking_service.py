from collections.abc import Sequence
from dataclasses import dataclass
from html.parser import HTMLParser

from app.models.cta_button import CTAButton
from app.schemas.tracking import TrackingSheetRowResponse

SUGGESTED_EVENT_PREFIX = "cta_click"
LANDING_PAGE_HTML_KIND = "landing_page_html"


@dataclass
class TrackingSheetValidationError(ValueError):
    error_code: str
    message: str

    def __str__(self) -> str:
        return self.message


class _ClickableIdParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.clickable_ids: set[str] = set()

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag.lower() not in {"a", "button"}:
            return

        for attr_name, attr_value in attrs:
            if attr_name != "id" or not isinstance(attr_value, str):
                continue

            normalized_id = attr_value.strip().lower()
            if normalized_id:
                self.clickable_ids.add(normalized_id)
            return


class TrackingService:
    def build_suggested_event(self, css_id: str) -> str:
        normalized_css_id = css_id.strip().lower()
        encoded_tokens: list[str] = []

        for character in normalized_css_id:
            if character.isalnum():
                encoded_tokens.append(character)
            elif character == "-":
                encoded_tokens.append("_dash_")
            elif character == "_":
                encoded_tokens.append("_underscore_")

        return f"{SUGGESTED_EVENT_PREFIX}_{''.join(encoded_tokens)}"

    def build_tracking_sheet_rows(
        self,
        cta_buttons: Sequence[CTAButton],
    ) -> list[TrackingSheetRowResponse]:
        return [
            TrackingSheetRowResponse(
                name=button.name,
                css_id=button.css_id,
                suggested_event=self.build_suggested_event(button.css_id),
            )
            for button in cta_buttons
        ]

    def validate_html_matches_cta_matrix(
        self,
        *,
        landing_page_html: str,
        cta_buttons: Sequence[CTAButton],
    ) -> None:
        parser = _ClickableIdParser()
        parser.feed(landing_page_html)
        parser.close()

        missing_css_ids = [
            button.css_id
            for button in cta_buttons
            if button.css_id.strip().lower() not in parser.clickable_ids
        ]
        if missing_css_ids:
            missing_ids = ", ".join(missing_css_ids)
            raise TrackingSheetValidationError(
                error_code="TRACKING_SHEET_OUT_OF_SYNC",
                message=(
                    "A Tracking Sheet final nao confere com o HTML aprovado. "
                    "Os seguintes IDs CSS nao foram encontrados em links ou "
                    f"botoes clicaveis: {missing_ids}."
                ),
            )
