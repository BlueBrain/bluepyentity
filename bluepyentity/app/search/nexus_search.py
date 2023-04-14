from __future__ import annotations
from enum import Enum
from textual import events, log
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.widgets import Checkbox, DataTable, Footer, Static
import bluepyentity.app.search.kg as kg
from bluepyentity.app.search.search_bar import SearchBar
from bluepyentity.app.search.search_completion import CompletionCandidate, SearchCompletion
import bluepyentity
from bluepyentity.app.explorer import Nexus
from rich.text import Text

# remove kgforge in explore
# manage back from explorer
# keybinding for column selection
# keybinding for cells
# fetch all properties dynamically
# manage incoming links
# more predicates
# pagination
# input for number of rows
# remove special case for entityid

DEFAULT_SHORT_LIST = ["entityid", "createdAt", "project", "name", "type", "self"]


def build_completion_candidates(property_definitions):
    """create a list of completion candidate out of property definitions"""
    return [
        CompletionCandidate(
            name=pd.value.split("/")[-1],
            count=None,
            complete_type=None,
            property_definition=pd,
            property_definitions=None,
        )
        for pd in property_definitions
    ]


class NexusSearch(App):
    """search and explore the knowledge graph in a TUI"""

    BINDINGS = [
        ("q", "quit", "Quit"),
    ]

    class State(Enum):
        STAND_BY = (0,)
        INPUT = (1,)
        COLUMNS_SELECTION = 2

    BINDINGS_FOR_STATE = {
        State.STAND_BY: [("s", "search", "Search")],
        State.INPUT: [],
        State.COLUMNS_SELECTION: [],
    }

    def __init__(
        self,
        driver_class=None,
        css_path=None,
        watch_css: bool = False,
        token: str | None = None,
        bucket: str | None = None,
    ):
        self.token = token
        self.org, self.project = bucket.split("/")
        self._active_state = NexusSearch.State.STAND_BY
        self._current_focus = None
        self.table = None
        self.completion_items = {}
        super().__init__(driver_class, css_path, watch_css)

        self.completion_items["type"] = []
        self.completion_items["property"] = []
        self.completion_items["order"] = []
        self.completion_items["value"] = []

        self.selected_columns = {}
        self.current_binding = None
        self.current_results = None

    def compose(self) -> ComposeResult:
        type_counts = kg.load_types(self.org, self.project, self.token)
        types = [
            CompletionCandidate(
                name=t["key"].split("/")[-1],
                count=t["doc_count"],
                complete_type=t["key"],
                property_definition=None,
                property_definitions=None,
            )
            for t in type_counts
        ]
        self.completion_items["type"] = types
        l_input_types = []

        def label(input_type):
            return f"\[{input_type[0]}]{input_type[1:]}>"

        for input_type in ["type", "property", "value", "order"]:
            l_input_types.append(
                Vertical(
                    Horizontal(
                        Static(
                            label(input_type),
                            id="search-prompt-" + input_type,
                            classes="search-prompt",
                        ),
                        SearchBar(
                            id="search-input-" + input_type,
                            input_type=input_type,
                        ),
                    ),
                    Container(
                        SearchCompletion(
                            candidates=self.completion_items[input_type],
                            id="search-completion-" + input_type,
                            classes="search-completion",
                        ),
                        id="search-completion-container-" + input_type,
                        classes="search-completion-container",
                    ),
                    id="search-container-" + input_type,
                    classes="search-container",
                )
            )
        self.vs = VerticalScroll(classes="column-choice")
        self.vs.display = False
        l_input_types.append(self.vs)
        yield Horizontal(*l_input_types, id="h1", classes="search-bar-container")
        self.table = DataTable(zebra_stripes=True)
        yield self.table
        self.footer = Footer()
        yield self.footer

    async def action_quit(self) -> None:
        """Quit the app"""
        self.app.exit()

    # @property
    # def namespace_bindings(self):
    #     return self.BINDINGS_FOR_STATE[self._active_state]

    def set_active_state(self, state):
        """set the current active state"""
        log.info(f"state[{self._active_state}]->state[{state}]")
        self._active_state = state
        self.footer.make_key_text()
        self.footer._bindings_changed(focused=None)

    async def on_key(self, event: events.Key) -> None:
        key_focus = {"t": "type", "p": "property", "v": "value", "o": "order"}
        log.info(f"active state {self._active_state}")

        def set_focus(search_category):
            current_focus = self.query_one("#search-input-" + search_category)
            current_focus.focus()
            self.set_active_state(NexusSearch.State.INPUT)

        if self._active_state == NexusSearch.State.STAND_BY:
            if event.key in "tpvo":
                set_focus(key_focus[event.key])
                return
            if event.key in "s":
                self.action_search()
                return
            if event.key in "c":
                self.set_active_state(NexusSearch.State.COLUMNS_SELECTION)
                self.show_column_selection()
                return
        if self._active_state == NexusSearch.State.INPUT:
            if event.key == "escape":
                self.set_active_state(NexusSearch.State.STAND_BY)
                return
        if self._active_state == NexusSearch.State.COLUMNS_SELECTION:
            if event.key in "c":
                self.set_active_state(NexusSearch.State.STAND_BY)
                self.process_columns_selection()
        self.refresh_all()

    def refresh_all(self):
        """refresh all components"""

        def refresh_children(component):
            for c in component.children:
                refresh_children(c)
            try:
                component.refresh(layout=True)
            except:
                pass

        refresh_children(self)

    def action_search(self):
        """perform the query based on the search bar inputs"""
        search_input = self.query_one("#search-input-type")
        type_ = None
        if search_input.selected_candidate:
            type_ = search_input.selected_candidate.complete_type

        if not type_:
            return

        properties_definition = None
        if search_input.selected_candidate:
            properties_definition = search_input.selected_candidate.property_definitions
        value = self.query_one("#search-input-value").value

        property_definition = None
        selected_candidate = self.query_one("#search-input-property").selected_candidate
        if selected_candidate:
            property_definition = selected_candidate.property_definition

        order_input = self.query_one("#search-input-order")
        order_property = None
        if order_input.selected_candidate:
            order_property = order_input.selected_candidate.property_definition
        qd = kg.QueryDefinition(
            type=type_,
            property_predicate=kg.PropertyPredicate(property_definition, value, "CONTAINS"),
            order_by=order_property,
            select_clause=properties_definition,
        )
        results, binding = kg.run_query(self.org, self.project, self.token, qd, "out")
        self.current_results = results
        self.current_binding = binding
        self.refresh_table()
        self.table.focus()

    def refresh_table(self):
        """refresh the results displayed in the table"""
        self.table.clear(True)
        to_display = []
        log(f"number of results {len(self.current_results)}")
        if not self.current_binding:
            self.refresh_all()
            return
        for k in self.current_binding.keys():
            checkbox_status = self.selected_columns[k]
            if checkbox_status.value:
                key = k.split("/")[-1]
                self.table.add_column(key, key=key)
                to_display.append(k)
        for elem in self.current_results:

            def _display(k):
                if k not in self.current_binding:
                    return "[NO DATA]"
                else:
                    binding = self.current_binding[k]
                    if binding not in elem:
                        text = Text("[NO DATA]")
                        text.stylize("bold red")

                        return text 

                    return str(elem.get(self.current_binding[k]).get("value", ""))

            row = [_display(k) for k in to_display]
            self.table.add_row(*row)
            self.refresh_all()

    def on_data_table_cell_selected(self, event) -> None:
        """move to explore if a row is selected"""
        row_key = event.cell_key.row_key
        entityid = self.table.get_cell(row_key, "entityid")
        forge = bluepyentity.environments.create_forge(
            "prod",
            self.token,
            bucket=f"{self.org}/{self.project}",
            debug=True,
        )
        self.push_screen(Nexus(forge, entityid))

    def on_search_bar_updated(self, event: SearchBar.Updated) -> None:
        input_type = event.sender.input_type
        completion = self.app.query_one("#search-completion-" + input_type)
        initial_candidates = completion.initial_candidates
        value = event.value
        candidates = []
        for candidate in initial_candidates:
            if value.lower() in candidate.name.lower():
                candidates.append(candidate)
        # Update the dropdown list with the new candidates
        completion.update_candidates(candidates)
        completion.filter = value
        completion.highlight_index = completion.highlight_index
        self.refresh_all()

    def on_search_bar_selected(self, event: SearchBar.Selected) -> None:
        input_type = event.sender.input_type
        if input_type == "type":
            type_completion_candidate = event.value
            property_definitions = kg.get_properties_of_type(
                self.org, self.project, self.token, type_completion_candidate.complete_type
            )
            type_completion_candidate.property_definitions = property_definitions
            candidate_properties = build_completion_candidates(property_definitions)
            for impacted_input_type in ["property", "order"]:
                completion = self.app.query_one("#search-completion-" + impacted_input_type)
                completion.initialize_candidates(candidate_properties)
            for c in self.vs.children:
                c.remove()
            self.selected_columns = {}
            for pd in property_definitions:
                value = False
                for k in DEFAULT_SHORT_LIST:
                    if k in pd.value:
                        value = True
                        break
                cb = Checkbox(pd.value, value=value)
                self.selected_columns[pd.value] = cb
                self.vs.mount(cb)
            self.refresh_all()

    def show_column_selection(self):
        self.vs.display = True

    def process_columns_selection(self):
        self.vs.display = False
        self.refresh_table()
        self.table.focus()
