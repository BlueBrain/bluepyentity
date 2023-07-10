from __future__ import annotations

from textual import events
from textual.geometry import Region
from textual.message import Message
from textual.widgets import Input

import bluepyentity.app.search.search_completion as search_completion


class SearchBar(Input):
    """search bar for definition a SPARQL query"""

    def __init__(
        self,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
        input_type: str | None = None,
        initial_candidates=None,
    ):
        super().__init__(
            placeholder="Start typing to search...",
            name=name,
            id=id,
            classes=classes,
        )
        self.input_type = input_type
        self.initial_candidates = initial_candidates
        self.value = ""
        self.selected_candidate = None

    def watch_value(self, value: str) -> None:
        self.post_message(SearchBar.Updated(self, str(value)))

    def restore_value(self):
        """restore previous value if selection did not happen"""
        if self.input_type in ["type", "property", "order"]:
            if self.value == "":
                self.selected_candidate = None
            elif self.selected_candidate:
                self.value = self.selected_candidate.name
            else:
                self.value = ""

    def on_key(self, event: events.Key) -> None:
        """manages key event in the search bar"""
        completion = self.app.query_one("#search-completion-" + self.input_type)
        completion_parent = self.app.query_one("#search-completion-container-" + self.input_type)
        if self.input_type in ["type", "property", "order"]:
            completion.display = True
            completion_parent.display = True

        if event.key == "down":
            completion.highlight_index += 1
            event.stop()
        elif event.key == "up":
            completion.highlight_index -= 1
            event.stop()
        elif event.key == "tab":
            if completion_parent.display:
                # The dropdown is visible, fill in the completion string
                candidate = completion.highlighted_candidate
                self.value = candidate.name
                self.selected_candidate = candidate
                self.post_message(SearchBar.Selected(self, self.input_type, candidate))
            event.stop()
        elif event.key == "escape":
            completion_parent.display = False
            completion.display = False
            self.restore_value()
            self.screen.set_focus(None)

        x, _, width, height = completion.region
        target_region = Region(x, completion.highlight_index, width, height)
        completion_parent.scroll_to_region(target_region, animate=False)

    class Updated(Message, bubble=True):
        """updated input event"""

        def __init__(self, sender: SearchBar, value: str) -> None:
            super().__init__()
            self.sender = sender
            self.value = value

    class Selected(Message, bubble=True):
        """selected completion event"""

        def __init__(
            self,
            sender: SearchBar,
            input_type: str,
            value: search_completion.CompletionCandidate,
        ) -> None:
            super().__init__()
            self.sender = sender
            self.input_type = input_type
            self.value = value
