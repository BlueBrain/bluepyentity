"""Display KG entity as a tree. Press "f" key for navigating links."""
import itertools
import random
from collections import defaultdict

import click
from rich.highlighter import ReprHighlighter
from rich.style import Style
from rich.text import Text
from textual import events
from textual.app import App
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer, Label, Tree
from textual.widgets.tree import TreeNode

from bluepyentity.app import utils

HINTS = "sadjklewcmpgh"


def _tree():
    """Autovivificated tree"""
    return defaultdict(_tree)


class VimTree(Tree):
    """Add j/k bindings for tree navigation"""

    BINDINGS = [
        Binding("enter", "select_cursor", "Select", show=False),
        Binding("up", "cursor_up", "Cursor Up", show=False),
        Binding("down", "cursor_down", "Cursor Down", show=False),
        Binding("k", "cursor_up", "Cursor Up", show=False),
        Binding("j", "cursor_down", "Cursor Down", show=False),
        Binding("h", "select_cursor", "Cursor Up", show=False),
        Binding("l", "select_cursor", "Cursor Down", show=False),
        Binding("G", "scroll_end", "Goto end", show=False),
    ]


class NexusHeader(Label):
    """Currently updating the title is broken in textual; simple replacement"""

    DEFAULT_CSS = """
    NexusHeader {
        background: $accent;
        content-align: center middle;
        color: $text;
        dock: top;
        height: 1;
    }"""


class Nexus(Screen):
    """Wrap displaying a nexus resource"""

    BINDINGS = [
        ("f", "follow", "Open a link"),
        ("b", "back", "Back"),
        ("ctrl+t", "app.toggle_dark", "Toggle Dark mode"),
        ("q", "quit", "Quit"),
    ]

    def __init__(self, forge, id_):
        """ibid"""
        self.forge = forge
        self.id_ = id_

        # True if in "follow" command
        self._follow_cmd = False
        # Root tree element
        self._root = None
        # the bookmarked URLs
        self._urls = defaultdict(list)
        # nodes are letters, leaves are urls.
        self._cur_kt = _tree()
        # The selection of letter for the follow command
        self._cur_selection = []
        # The size of the hints depending on the number of links
        self._size_combination = 0

        self.data = self.forge.retrieve(id_, cross_bucket=True)

        self._init_state()

        super().__init__()

    def _init_state(self):
        self._follow_cmd = False
        self._root = None
        self._urls = defaultdict(list)
        self._cur_kt = _tree()
        self._cur_selection = []
        self._size_combination = 0

    def compose(self):
        """Yield child widgets for a container."""
        yield NexusHeader(self.id_)
        yield VimTree(label="resource", id="nexus-tree")
        yield Footer()

    def _add_label(self, value, label):
        """labels bookmarking"""
        self._urls[value].append(label)

    def on_mount(self) -> None:
        """Initialization of the widget."""
        self._init_tree()

        tree = self.query_one(Tree)
        tree.focus()

    def _init_tree(self) -> None:
        # pylint: disable=protected-access
        highlighter = ReprHighlighter()

        preferred_order = [
            "id",
            "name",
            "description",
            "type",
        ]

        def add_node(name: str, node: TreeNode, data: object) -> None:
            """Adds a node to the tree.

            Args:
                name(str): Name of the node.
                node(TreeNode): Parent node.
                data(object): Data associated with the node.
            """
            node.expand()
            if isinstance(data, dict):
                node.set_label(f"{{}} {name}")
                for key, value in data.items():
                    add_node(key, node.add(""), value)
            elif isinstance(data, list):
                node.set_label(f"[] {name}")
                for i, value in enumerate(data):
                    add_node(str(i), node.add(""), value)
            elif type(data).__name__ == "Resource":
                label = "Resource:"
                if hasattr(data, "_store_metadata") and data._store_metadata is not None:
                    label = f"Resource: \\[{data._store_metadata.id} / {data._store_metadata._rev}]"
                node.set_label(label)
                data = vars(data)
                for p in preferred_order:
                    if p in data:
                        add_node(p, node.add(""), data[p])

                for k, v in data.items():
                    if k.startswith("_") or k in preferred_order:
                        continue
                    add_node(k, node.add(""), v)
            else:
                node._allow_expand = False
                node.set_label(
                    Text.assemble(Text.from_markup(f"[b]{name}[/b]="), highlighter(repr(data)))
                )
                if isinstance(data, str) and data.startswith("http"):
                    self._add_label(data, node._label)

        self._root = self.query_one(VimTree)
        self._root.clear()
        self._root.focus()
        add_node("", self._root.root, self.data)

    def display_hints(self):
        """Display a combination of letter to select a link."""
        nb_urls = len(self._urls)
        size_combination = 1
        total_combination = len(HINTS)
        while total_combination < nb_urls and size_combination <= len(HINTS):
            total_combination *= len(HINTS) - size_combination
            size_combination += 1
        assert size_combination < total_combination
        self._size_combination = size_combination

        # as in Vimium, hints have all the same size and shuffled
        needed_hints = list(itertools.combinations(HINTS, size_combination))
        random.shuffle(needed_hints)
        needed_hints = needed_hints[:nb_urls]

        def add_to_keytree(tree, indices, value):
            """place value in the tree under the indices"""
            if len(indices) > 1:
                # add node
                add_to_keytree(tree[indices[0]], indices[1:], value)
            else:
                # add leaf
                tree[indices[0]] = value

        for url, hint in zip(self._urls, needed_hints):
            hint_text = Text("[" + "".join(hint) + "]")
            for elem in self._urls[url]:
                elem.append_text(hint_text)
            add_to_keytree(self._cur_kt, hint, url)

        # required to get all the hints displayed
        self._invalidate_root()

    def _invalidate_root(self):
        # pylint: disable=protected-access
        self._root._invalidate()

    def hide_hints(self):
        """Remove the hints from the node labels."""
        for elems in self._urls.values():
            for elem in elems:
                # +2 because of the []
                elem.right_crop(self._size_combination + 2)
        self._cur_kt = _tree()
        self._cur_selection = []
        self._invalidate_root()

    def _manage_follow_command(self, character):
        self._cur_selection.append(character)
        cur_kt = self._cur_kt[character]

        def leaves(adt, agg):
            if isinstance(adt, defaultdict):
                for value in adt.values():
                    leaves(value, agg)
            else:
                agg.append(adt)
            return agg

        urls = leaves(cur_kt, [])
        if not cur_kt:
            # invalid letter
            return

        self._cur_kt = cur_kt
        start_idx = -self._size_combination - 1
        for url in urls:
            for elem in self._urls[url]:
                elem.stylize(
                    Style(color="red", bold=True), start_idx, start_idx + len(self._cur_selection)
                )

        self._invalidate_root()

        if len(urls) == 1:
            self._follow_cmd = not self._follow_cmd
            url = urls[0]
            self.hide_hints()
            self.app.push_screen(Nexus(self.forge, url))

    async def action_follow(self) -> None:
        """Follow link"""
        self._follow_cmd = not self._follow_cmd

        if self._follow_cmd:
            self.display_hints()
        else:
            self.hide_hints()

    async def action_back(self) -> None:
        """Navigate back"""
        if len(self.app.screen_stack) > 2:
            self.app.pop_screen()

    def on_key(self, event: events.Key) -> None:
        """Manage key pressed events."""
        if self._follow_cmd:
            if event.name == "escape":
                self._follow_cmd = False
                self.hide_hints()
            else:
                self._manage_follow_command(event.character)
                event.stop()


class Explorer(App):
    """Link exploration application"""

    BINDINGS = [
        ("q", "quit", "Quit"),
    ]

    def __init__(self, forge, id_):
        """ibid"""
        self.forge = forge
        self.id_ = id_
        super().__init__()

    def compose(self):
        """Yield child widgets for a container."""
        yield Footer()

    def on_mount(self) -> None:
        """Initialization of the widget."""
        self.push_screen(Nexus(self.forge, self.id_))

    async def action_quit(self) -> None:
        """Quit the app"""
        self.app.exit()


@click.command()
@click.argument("id_")
@click.pass_context
def explorer_app(ctx, id_):
    """Link exploration TUI"""
    forge = utils.forge_from_ctx(ctx)
    Explorer(forge, id_=id_).run()
