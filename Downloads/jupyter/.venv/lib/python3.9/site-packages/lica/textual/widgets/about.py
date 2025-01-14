# ----------------------------------------------------------------------
# Copyright (c) 2024 Rafael Gonzalez.
#
# See the LICENSE file for details
# ----------------------------------------------------------------------

# ---------------
# Textual imports
# ---------------

from textual import on
from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.containers import Container
from textual.widgets import Label, Button, Markdown

# --------------
# local imports
# -------------


class About(ModalScreen):

    DEFAULT_CSS = """
    About {
        align: center middle; 
    }

    About > Container {
        width: 50;
        height: auto;
        background: $panel;
        border: double yellow;
    }

    About > Container > Label {
        margin: 1;
    }

    About > Container > Button {
        margin: 1;
        width: 100%;
    }
    """

    def __init__(self, title="", version="", description=""):
        self._title = title
        self._version = version
        self._descripition = description
        super().__init__()

    def compose(self) -> ComposeResult:
        with Container():
            yield Label(f"Version: {self._version}")
            yield Markdown(self._descripition)
            yield Button('Dismiss', variant="success")

    def on_mount(self) -> None:
        self.query_one(Container).border_title = self._title

    @on(Button.Pressed)
    def ok_pressed(self, event: Button.Pressed) -> None:
        self.dismiss()
