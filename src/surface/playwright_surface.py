from typing import Any

from playwright.sync_api import (
    Browser,
    BrowserContext,
    Locator as PlaywrightLocator,
    Page,
    sync_playwright,
)

from src.models.actions import (
    Locator,
    LocatorStrategy,
    Target,
)
from src.surface.base import Surface


class PlaywrightSurface(Surface):
    def __init__(
        self,
        headless: bool = False,
    ):
        self.headless = headless

        self._playwright = None
        self.browser: Browser | None = None
        self.context: BrowserContext | None = None
        self.page: Page | None = None

    def open(
        self,
        target: str,
    ) -> None:
        self._playwright = (
            sync_playwright().start()
        )

        self.browser = (
            self._playwright
            .chromium
            .launch(
                headless=self.headless
            )
        )

        self.context = (
            self.browser.new_context()
        )

        self.page = (
            self.context.new_page()
        )

        self.page.goto(target)

        self.page.wait_for_load_state(
            "domcontentloaded"
        )

    def observe(
        self,
    ) -> dict[str, Any]:
        self._ensure_page()

        controls = self.page.locator(
            "input, button, select, textarea, a"
        )

        interactive_elements = []

        for index in range(
            controls.count()
        ):
            element = controls.nth(
                index
            )

            try:
                tag = element.evaluate(
                    "(el) => "
                    "el.tagName.toLowerCase()"
                )

                role = element.get_attribute(
                    "role"
                )

                element_type = (
                    element.get_attribute(
                        "type"
                    )
                )

                name = element.get_attribute(
                    "name"
                )

                element_id = (
                    element.get_attribute(
                        "id"
                    )
                )

                text = (
                    element.inner_text()
                    .strip()
                )

                if tag == "input":
                    label = None

                    if element_id:
                        label_element = (
                            self.page.locator(
                                f'label[for="'
                                f'{element_id}"]'
                            )
                        )

                        if (
                            label_element.count()
                            == 1
                        ):
                            label = (
                                label_element
                                .inner_text()
                                .strip()
                            )

                    interactive_elements.append(
                        {
                            "index": index,
                            "tag": tag,
                            "type": element_type,
                            "name": name,
                            "label": label,
                            "id": element_id,
                            "value": (
                                element
                                .input_value()
                            ),
                        }
                    )

                else:
                    interactive_elements.append(
                        {
                            "index": index,
                            "tag": tag,
                            "role": role,
                            "text": text,
                        }
                    )

            except Exception:
                continue

        return {
            "url": self.page.url,
            "title": self.page.title(),
            "visible_text": (
                self.page.locator(
                    "body"
                ).inner_text()
            ),
            "controls": (
                interactive_elements
            ),
        }

    def click(
        self,
        target: Target,
    ) -> None:
        locator = self._resolve_target(
            target
        )

        locator.click()

    def type_text(
        self,
        target: Target,
        value: str,
    ) -> None:
        locator = self._resolve_target(
            target
        )

        locator.fill(value)

    def read_text(
        self,
        target: Target,
    ) -> str:
        locator = self._resolve_target(
            target
        )

        return (
            locator.inner_text()
            .strip()
        )

    def screenshot(
        self,
        path: str,
    ) -> None:
        self._ensure_page()

        self.page.screenshot(
            path=path,
            full_page=True,
        )

    def close(
        self,
    ) -> None:
        if self.context:
            self.context.close()

        if self.browser:
            self.browser.close()

        if self._playwright:
            self._playwright.stop()

        self.page = None
        self.context = None
        self.browser = None
        self._playwright = None

    def _resolve_target(
        self,
        target: Target,
    ) -> PlaywrightLocator:
        candidates = [
            target.primary,
            *target.fallbacks,
        ]

        errors: list[str] = []

        for locator_config in candidates:
            try:
                locator = self._build_locator(
                    locator_config
                )

                count = locator.count()

                if count == 1:
                    return locator

                errors.append(
                    f"{locator_config.strategy}: "
                    f"matched {count} elements"
                )

            except Exception as exc:
                errors.append(
                    f"{locator_config.strategy}: "
                    f"{exc}"
                )

        raise RuntimeError(
            "Unable to resolve target. "
            + " | ".join(errors)
        )

    def _build_locator(
        self,
        locator: Locator,
    ) -> PlaywrightLocator:
        self._ensure_page()

        if (
            locator.strategy
            == LocatorStrategy.ROLE
        ):
            if not locator.role:
                raise ValueError(
                    "Role locator requires "
                    "'role'."
                )

            return self.page.get_by_role(
                locator.role,
                name=locator.name,
            )

        if (
            locator.strategy
            == LocatorStrategy.LABEL
        ):
            if not locator.label:
                raise ValueError(
                    "Label locator requires "
                    "'label'."
                )

            return self.page.get_by_label(
                locator.label
            )

        if (
            locator.strategy
            == LocatorStrategy.TEXT
        ):
            if not locator.text:
                raise ValueError(
                    "Text locator requires "
                    "'text'."
                )

            return self.page.get_by_text(
                locator.text,
                exact=True,
            )

        if (
            locator.strategy
            == LocatorStrategy.CSS
        ):
            if not locator.selector:
                raise ValueError(
                    "CSS locator requires "
                    "'selector'."
                )

            return self.page.locator(
                locator.selector
            )

        if (
            locator.strategy
            == LocatorStrategy.TABLE_CELL
        ):
            return (
                self._build_table_cell_locator(
                    locator
                )
            )

        raise ValueError(
            "Unsupported locator strategy: "
            f"{locator.strategy}"
        )

    def _build_table_cell_locator(
        self,
        locator: Locator,
    ) -> PlaywrightLocator:
        if not locator.row_text:
            raise ValueError(
                "TABLE_CELL requires "
                "'row_text'."
            )

        if not locator.column_header:
            raise ValueError(
                "TABLE_CELL requires "
                "'column_header'."
            )

        tables = self.page.locator(
            "table"
        )

        for table_index in range(
            tables.count()
        ):
            table = tables.nth(
                table_index
            )

            headers = table.locator(
                "th"
            )

            header_texts = []

            for header_index in range(
                headers.count()
            ):
                header_texts.append(
                    headers.nth(
                        header_index
                    )
                    .inner_text()
                    .strip()
                )

            if (
                locator.column_header
                not in header_texts
            ):
                continue

            column_index = (
                header_texts.index(
                    locator.column_header
                )
            )

            rows = table.locator(
                "tbody tr"
            )

            for row_index in range(
                rows.count()
            ):
                row = rows.nth(
                    row_index
                )

                cells = row.locator(
                    "td"
                )

                if cells.count() == 0:
                    continue

                first_cell_text = (
                    cells.nth(0)
                    .inner_text()
                    .strip()
                )

                if (
                    first_cell_text
                    != locator.row_text
                ):
                    continue

                if (
                    column_index
                    >= cells.count()
                ):
                    raise RuntimeError(
                        "Table row does not "
                        "contain the requested "
                        "column."
                    )

                return cells.nth(
                    column_index
                )

        raise RuntimeError(
            "Unable to find table cell "
            f"for row '{locator.row_text}' "
            "and column "
            f"'{locator.column_header}'."
        )

    def _ensure_page(
        self,
    ) -> None:
        if self.page is None:
            raise RuntimeError(
                "Surface has not been opened."
            )