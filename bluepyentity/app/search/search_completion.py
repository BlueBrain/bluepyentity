from __future__ import annotations

from dataclasses import dataclass
from operator import attrgetter
from typing import Iterable

from rich.console import Console, ConsoleOptions, RenderableType
from rich.text import Text
from textual import events, log
from textual.css.styles import RenderStyles
from textual.geometry import Size
from textual.widget import Widget

import bluepyentity.app.search.kg as kg


@dataclass
class CompletionCandidate:
    name: str
    count: int | None
    complete_type: str | None
    property_definition: kg.PropertyDefinition | None
    property_definitions: list[kg.PropertyDefinition] | None


class SearchCompletionRender:
    '''render possible completions'''
    def __init__(
        self,
        filter: str,
        matches: Iterable[CompletionCandidate],
        highlight_index: int,
        component_styles: dict[str, RenderStyles],
        input_type: str,
    ) -> None:
        self.filter = filter
        self.matches = matches
        self.highlight_index = highlight_index
        self.component_styles = component_styles
        self._highlight_item_style = self.component_styles.get(
            "search-completion--selected-item"
        ).rich_style
        self.input_type = input_type

    def __rich_console__(self, console: Console, options: ConsoleOptions):
        matches = []
        for index, match in enumerate(self.matches):
            display_count = ""
            if match.count is not None:
                display_count = match.count
            match = Text.from_markup(
                f"{match.name:<{options.max_width - 3}}[dim]{display_count}"
            )
            matches.append(match)
            if self.highlight_index == index:
                match.stylize(self._highlight_item_style)
            match.highlight_regex(self.filter, style="black on #4EBF71")
        return Text("\n").join(matches)


class SearchCompletion(Widget):
    '''a widget showing possible values for an input'''
    COMPONENT_CLASSES = {
        "search-completion--selected-item",
    }

    def __init__(
        self,
        candidates: Iterable[str],
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
        input_type: str | None = None,
    ):
        super().__init__(name=name, id=id, classes=classes)
        self.candidates = []
        self.update_candidates(candidates)
        self.initial_candidates = candidates
        self.input_type = input_type
        self.display = False

    def update_candidates(self, new_candidates: Iterable[CompletionCandidate]) -> None:
        self.candidates = sorted(new_candidates, key=attrgetter("name"))
        self.refresh()

    def initialize_candidates(
        self, initial_candidates: Iterable[CompletionCandidate]
    ) -> None:
        self.candidates = sorted(initial_candidates, key=attrgetter("name"))
        self.initial_candidates = self.candidates
        self.refresh()

    @property
    def highlighted_candidate(self):
        if not self.matches:
            return 0
        return self.matches[self.highlight_index]

    @property
    def highlight_index(self) -> int:
        return self._highlight_index

    @highlight_index.setter
    def highlight_index(self, value: int) -> None:
        self._highlight_index = value % max(len(self.matches), 1)
        self.refresh()

    @property
    def filter(self) -> str:
        return self._filter

    @filter.setter
    def filter(self, value: str):
        self._filter = value
        search_value = value

        new_matches = []
        for candidate in self.candidates:
            if search_value.lower() in candidate.name.lower():
                new_matches.append(candidate)

        self.matches = sorted(
            new_matches,
            key=lambda candidate: candidate.name.startswith(search_value),
            reverse=True,
        )
        log.debug(f"len(self.matches) {len(self.matches)}")
        self.parent.display = len(self.matches) > 0
        self.refresh()

    def on_mount(self, event: events.Mount) -> None:
        self._highlight_index = 0
        self._filter = ""
        self.matches = sorted(self.candidates, key=attrgetter("name"))

    def get_content_height(self, container: Size, viewport: Size, width: int) -> int:
        return len(self.matches)

    def render(self) -> RenderableType:
        return SearchCompletionRender(
            filter=self.filter,
            matches=self.matches,
            highlight_index=self.highlight_index,
            component_styles=self._component_styles,
            input_type=self.input_type,
        )
