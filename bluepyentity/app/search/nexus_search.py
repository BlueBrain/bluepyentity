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


def build_completion_candidates(property_definitions):
    """create a list of completion candidate out of property definitions"""
    return [
        CompletionCandidate(
            name=pd.property_name.split("/")[-1],
            count=None,
            complete_name=None,
            property_definition=pd,
        )
        for pd in property_definitions
    ]


def get_column_names(results):
    """get a sorted list of unique columns from a query result"""
    column_names = set()
    for res in results:
        for key in res.keys():
            column_names.add(key)
    return sorted(list(column_names))


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
        log_dir: str | None = None,
    ):
        self.token = token
        self.org, self.project = bucket.split("/")

        self._active_state = NexusSearch.State.STAND_BY

        # the textual widget for the table
        self.table = None
        # write to queries to log directory if set
        self.log_dir = log_dir
        super().__init__(driver_class, css_path, watch_css)

        # store the column vertical scroll
        self.columns_vs = None
        # store the column checkbox widgets
        self.selected_columns = {}
        # store the list of results returned from the query
        self.current_results = []

    def compose(self) -> ComposeResult:
        type_counts = kg.load_types(self.org, self.project, self.token, self.log_dir)
        types = [
            CompletionCandidate(
                name=t["key"].split("/")[-1],
                count=t["doc_count"],
                complete_name=t["key"],
                property_definition=None,
            )
            for t in type_counts
        ]
        l_horizontal_widget_content = []

        def label(input_type):
            return f"\[{input_type[0]}]{input_type[1:]}>"

        for input_type in ["type", "property", "value", "order"]:
            if input_type == "type":
                completion_list = types
            else:
                completion_list = []
            l_horizontal_widget_content.append(
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
                            candidates=completion_list,
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

        self.columns_vs = VerticalScroll(classes="column-choice")
        self.columns_vs.display = False
        l_horizontal_widget_content.append(self.columns_vs)
        
        yield Horizontal(*l_horizontal_widget_content, id="h1", classes="search-bar-container")

        self.table = DataTable(zebra_stripes=True)
        yield self.table

        self.footer = Footer()
        yield self.footer

    async def action_quit(self) -> None:
        """Quit the app"""
        self.app.exit()

    def set_active_state(self, state):
        """set the current active state"""
        log.info(f"state[{self._active_state}]->state[{state}]")
        self._active_state = state
        self.footer.make_key_text()
        self.footer._bindings_changed(focused=None)

    async def on_key(self, event: events.Key) -> None:
        """manages key pressed events"""
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
                self.show_columns_selection()
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
            type_ = search_input.selected_candidate.complete_name

        if not type_:
            return

        value = self.query_one("#search-input-value").value

        selected_candidate = self.query_one("#search-input-property").selected_candidate
        property_definition = None
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
        )
        results = kg.run_query(self.org, self.project, self.token, qd, self.log_dir)
        self.current_results = results
        column_names = get_column_names(results)
        for cn in column_names:
            value = True
            cb = Checkbox(cn, value=value)
            # assuming all the properties do not collide here
            self.selected_columns[cn] = cb
            self.columns_vs.mount(cb)
        self.refresh_table()
        self.table.focus()

    def refresh_table(self):
        """refresh the results displayed in the table"""
        self.table.clear(True)
        to_display = []
        log(f"number of results {len(self.current_results)}")

        column_names = get_column_names(self.current_results)
        for k in column_names:
            checkbox_status = self.selected_columns.get(k, None)

            if checkbox_status is None or checkbox_status.value:
                self.table.add_column(k, key=k)
                to_display.append(k)
        for elem in self.current_results:

            def _display(k):
                if k not in elem:
                    text = Text("[NO DATA]")
                    text.stylize("bold red")
                    return text

                return str(elem.get(k).get("value", ""))

            row = [_display(k) for k in to_display]
            log(f"adding row: {str(row)}")
            self.table.add_row(*row)
            self.refresh_all()

        self.table.add_row(*to_display)

    def on_data_table_cell_selected(self, event) -> None:
        """move to explore if a row is selected"""
        row_key = event.cell_key.row_key
        entityid = self.table.get_cell(row_key, "@id")
        forge = bluepyentity.environments.create_forge(
            "prod",
            self.token,
            bucket=f"{self.org}/{self.project}",
            debug=True,
        )
        self.push_screen(Nexus(forge, entityid))

    def on_search_bar_updated(self, event: SearchBar.Updated) -> None:
        """manages update events in the search bar"""
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
        """manages selection event in the search bar"""
        input_type = event.sender.input_type
        if input_type == "type":
            type_completion_candidate = event.value
            property_definitions = kg.get_properties_of_type(
                self.org,
                self.project,
                self.token,
                type_completion_candidate.complete_name,
                self.log_dir,
            )
            candidate_properties = build_completion_candidates(property_definitions)
            for impacted_input_type in ["property", "order"]:
                completion = self.app.query_one("#search-completion-" + impacted_input_type)
                completion.initialize_candidates(candidate_properties)
            for c in self.columns_vs.children:
                c.remove()
            self.refresh_all()

    def show_columns_selection(self):
        """ show columns selection widget"""
        self.columns_vs.display = True

    def process_columns_selection(self):
        """update table based on columns selection"""
        self.columns_vs.display = False
        self.refresh_table()
        self.table.focus()
