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
from textual.widgets import Footer, Header, Tree, TreeNode

from bluepyentity.app import utils

HINTS = "sadjklewcmpgh"


def _tree():
    """Autovivificated tree"""
    return defaultdict(_tree)


class Explorer(App):
    """Link exploration application"""

    BINDINGS = [
        ("f", "follow", "Open a link"),
        ("b", "back", "Back"),
        ("q", "quit", "Quit"),
    ]

    def __init__(self, forge, id_):
        """ibid"""
        self.forge = forge

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

        self._previous_urls = [id_]

        self._load_data(id_)
        self._init_state()

        super().__init__()

    def _init_state(self):
        self._follow_cmd = False
        self._root = None
        self._urls = defaultdict(list)
        self._cur_kt = _tree()
        # The selection of letter for the follow command
        self._cur_selection = []
        # The size of the hints depending on the number of links
        self._size_combination = 0

    def compose(self):
        """Yield child widgets for a container."""
        yield Header()
        yield Tree("Root")
        yield Footer()

    def _add_label(self, value, label):
        """labels bookmarking"""
        self._urls[value].append(label)

    def _load_data(self, url):
        self.data = self.forge.retrieve(url, cross_bucket=True)

    def _refresh_all(self, url):
        """Reload data and display the tree."""
        self._load_data(url)
        self._init_state()
        self._init_tree()

    def on_mount(self) -> None:
        """Initialization of the widget."""
        self._init_state()
        self._init_tree()

    def _init_tree(self) -> None:
        # pylint: disable=protected-access
        highlighter = ReprHighlighter()

        def add_node(name: str, node: TreeNode, data: object) -> None:
            """Adds a node to the tree.

            Args:
                name(str): Name of the node.
                node(TreeNode): Parent node.
                data(object): Data associated with the node.
            """
            node.expand()
            if isinstance(data, dict):
                node.set_label(Text(f"{{}} {name}"))
                for key, value in data.items():
                    add_node(key, node.add(""), value)
            elif isinstance(data, list):
                node.set_label(Text(f"[] {name}"))
                for index, value in enumerate(data):
                    add_node(str(index), node.add(""), value)
            elif type(data).__name__ == "Resource":
                node.set_label(Text("Resource"))
                for k, v in vars(data).items():
                    if k.startswith("_"):
                        continue
                    add_node(k, node.add(""), v)
            else:
                node._allow_expand = False
                label = Text.assemble(Text.from_markup(f"[b]{name}[/b]="), highlighter(repr(data)))
                node.set_label(label)
                if isinstance(data, str) and data.startswith("http"):
                    self._add_label(data, node._label)

        tree = self.query_one(Tree)
        self._root = tree
        tree.clear()
        add_node("JSON", tree.root, self.data)

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
            self._previous_urls.append(url)
            self._refresh_all(url)
            return

    async def action_follow(self) -> None:
        """Follow link"""
        self._follow_cmd = not self._follow_cmd

        if self._follow_cmd:
            self.display_hints()
        else:
            self.hide_hints()

    async def action_back(self) -> None:
        """Navigate back"""
        if len(self._previous_urls) > 1:
            self._previous_urls.pop()
            url = self._previous_urls[-1]
            self._invalidate_root()
            self._refresh_all(url)

    async def action_quit(self) -> None:
        """Quit the app"""
        self.app.exit()

    def on_key(self, event: events.Key) -> None:
        """Manage key pressed events."""
        if self._follow_cmd:
            self._manage_follow_command(event.character)
            event.stop()


@click.command()
@click.argument("id_")
@click.pass_context
def app(ctx, id_):
    """Link exploration TUI"""
    forge = utils.forge_from_ctx(ctx)
    Explorer(forge, id_=id_).run()
