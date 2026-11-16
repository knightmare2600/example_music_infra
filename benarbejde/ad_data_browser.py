#!/usr/bin/env python3
"""
=============================================================================
AD Data Browser — read-only TUI
=============================================================================
Full-screen Textual TUI for BROWSING benarbejde/ad_computers.json,
ad_users.json, ad_groups.json, and ad_forest.json -- read-only, deliberately.
Nothing in this file ever opens any of these files in write mode; there is
no Confirm/Save path anywhere here, unlike site_device_tui.py (its sibling
tool, for sites.csv/devices.csv, which does write).

This is NOT a revival of benarbejde/archive/parse_tdf.py -- that script is
legacy, superseded by the 2026-07 TDF-to-static-JSON conversion, and MUST
NEVER be used again (Robert's own explicit instruction, 2026-11-16). This
tool only ever READS the already-converted, already-committed JSON files
that conversion produced; it has no code path that writes, regenerates, or
re-derives any AD data from anything, and never imports parse_tdf.py.

Shares its shell (ThemeFooter, the widget-density CSS override, Help/About
modals, F1/F7/F9/F10 bindings) with site_device_tui.py by the same
copy-and-rework convention that tool itself was built with, deliberately
NOT by importing across the two files -- they're independent tools over
different data with a different interaction shape (step wizard vs.
filter+browse table), and this repo's own established pattern (see
site_device_tui.py's own header) is to copy a proven shell and rework it,
not share runtime code between unrelated TUIs.

Requires:
    textual   -- TUI framework (apt: python3-textual)

Usage:
    python3 benarbejde/ad_data_browser.py
    python3 benarbejde/ad_data_browser.py --computers-json /path/to/ad_computers.json

Scope, deliberately: read-only for this round (Robert's own explicit ask,
2026-11-16, "read only initially"). Editing AD data through a TUI -- unlike
sites.csv/devices.csv -- is a materially bigger, separate decision: these
records are a point-in-time export of what's really AD-populated by
ansible/playbooks/windows_adschema, not a hand-maintained source of truth
the way sites.csv/devices.csv are, and have no apply_boilerplate()/
regenerate_all()-style existing write path to reuse. Not attempted here.
=============================================================================
"""

import argparse
import json
import sys
from pathlib import Path

try:
    from textual.app import App, ComposeResult
    from textual.binding import Binding
    from textual.containers import Horizontal, Vertical, VerticalScroll
    from textual.screen import ModalScreen, Screen
    from textual.widgets import Button, DataTable, Footer, Header, Input, Label, Static
except ImportError:
    print("ERROR: textual not installed.")
    print("  apt install python3-textual   (already staged on this estate's control hosts)")
    print("  or: pip3 install textual")
    sys.exit(1)

BENARBEJDE = Path(__file__).resolve().parent


class ArrowFocusMixin:
    """Adds plain Up/Down as alternates for Tab/Shift+Tab, moving focus to
    the next/previous focusable widget. Deliberately bound without
    priority=True -- DataTable's own Up/Down row-cursor movement and
    VerticalScroll's own native arrow-key scrolling keep working unchanged;
    this only fires once the focused widget's own bindings have had first
    refusal and the key bubbles up unhandled. Same pattern, same reasoning,
    as site_device_tui.py's own identically-named mixin -- duplicated, not
    imported, per this file's own header on why the two tools don't share
    runtime code."""

    def action_focus_next_item(self) -> None:
        self.focus_next()

    def action_focus_previous_item(self) -> None:
        self.focus_previous()


# =============================================================================
# DATA LOADERS -- plain json.load(), nothing else. No fallback/search path
# the way site_device_tui.py's _load_sites()/_load_role_codes() have, since
# this tool is never served from anywhere but a repo checkout either.
# =============================================================================

def _load_json_list(path):
    if not path.is_file():
        print(f"ERROR: {path.name} not found at {path}")
        sys.exit(1)
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        print(f"ERROR: {path.name} does not contain a JSON array at its top level.")
        sys.exit(1)
    return data


def _load_json_dict(path):
    if not path.is_file():
        print(f"ERROR: {path.name} not found at {path}")
        sys.exit(1)
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        print(f"ERROR: {path.name} does not contain a JSON object at its top level.")
        sys.exit(1)
    return data


# =============================================================================
# COLLECTION REGISTRY -- one declarative entry per browsable collection.
# columns: (header label, field key) pairs shown in the DataTable.
# search_fields: field keys concatenated (case-insensitively) to build the
# live filter's haystack -- confirmed directly against the real files'
# actual field sets before picking these, not guessed (e.g. Groups' own
# ManagedBy/Email are genuinely sometimes blank -- "Disabled Users" has no
# Email, 51 of 158 groups have no ManagedBy -- every .get() in this file
# defaults to "" rather than assuming a field is always present).
# =============================================================================

COLLECTIONS = {
    "computers": {
        "json_file": "ad_computers.json",
        "title": "Computers",
        "columns": [
            ("Name", "Name"), ("Role", "Role"), ("Site", "Site"),
            ("OS", "OS"), ("Enabled", "Enabled"), ("IPv4Address", "IPv4Address"),
        ],
        "search_fields": [
            "Name", "SamAccountName", "Role", "Site", "Description",
            "DNSHostName", "OS", "OperatingSystemVersion", "IPv4Address",
        ],
    },
    "users": {
        "json_file": "ad_users.json",
        "title": "Users",
        "columns": [
            ("Name", "Name"), ("SamAccountName", "SamAccountName"),
            ("Title", "Title"), ("Department", "Department"),
            ("City", "City"), ("Disabled", "Disabled"),
        ],
        "search_fields": [
            "Name", "SamAccountName", "UserPrincipalName", "Title", "Email",
            "Department", "Company", "Description", "City", "Country",
            "Manager", "Groups",
        ],
    },
    "groups": {
        "json_file": "ad_groups.json",
        "title": "Groups",
        "columns": [
            ("Name", "Name"), ("Type", "Type"), ("Scope", "Scope"),
            ("Site", "Site"), ("ManagedBy", "ManagedBy"),
        ],
        "search_fields": [
            "Name", "Description", "Type", "Scope", "ManagedBy", "Email", "Site",
        ],
    },
}


def _cell_text(value):
    """Render one field value for a DataTable cell / detail line -- bool as
    yes/no (matches this estate's own devices.csv convention elsewhere, more
    readable than Python's True/False), list joined with ', ', missing/None
    as blank, everything else as plain str()."""
    if isinstance(value, bool):
        return "yes" if value else "no"
    if value is None:
        return ""
    if isinstance(value, list):
        return ", ".join(str(v) for v in value)
    return str(value)


def _search_text(record, search_fields):
    return " ".join(_cell_text(record.get(f, "")) for f in search_fields).lower()


# =============================================================================
# THEME FOOTER — unchanged from site_device_tui.py / create-vm-tui.py.
# =============================================================================

class ThemeFooter(Footer):
    """Appends "| Current Theme: <name>" after the key-binding list."""

    DEFAULT_CSS = """
    ThemeFooter > #footer-theme {
        width: auto;
        color: $footer-foreground;
        background: $footer-background;
        padding: 0 1;
    }
    """

    def compose(self) -> ComposeResult:
        if not self._bindings_ready:
            return
        yield from super().compose()
        self.styles.grid_size_columns += 1
        yield Static(f"| Current Theme: {self.app.theme}", id="footer-theme")

    def on_mount(self) -> None:
        self.watch(self.app, "theme", self._on_theme_changed, init=False)

    def _on_theme_changed(self, old_value: str, new_value: str) -> None:
        for label in self.query("#footer-theme"):
            label.update(f"| Current Theme: {new_value}")


# =============================================================================
# MAIN MENU
# =============================================================================

class MainMenuScreen(ArrowFocusMixin, Screen):
    AUTO_FOCUS = "Button"

    DEFAULT_CSS = """
    MainMenuScreen { align: center middle; }
    #menu-box { width: 48; height: auto; }
    #menu-title { text-style: bold; margin-bottom: 1; }
    #menu-box Button { width: 100%; margin-bottom: 1; }
    """

    BINDINGS = [
        Binding("f1", "show_help", "Help", show=True),
        Binding("f7", "cycle_theme", "Theme", show=True),
        Binding("f9", "show_about", "About", show=True),
        Binding("f10", "app_quit", "Quit", show=True),
        Binding("down", "focus_next_item", show=False),
        Binding("up", "focus_previous_item", show=False),
    ]

    def action_show_help(self) -> None:
        self.app.action_show_help()

    def action_show_about(self) -> None:
        self.app.action_show_about()

    def action_cycle_theme(self) -> None:
        self.app.action_cycle_theme()

    def action_app_quit(self) -> None:
        self.app.exit()

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        with Vertical(id="menu-box"):
            yield Label("Example Music Limited — AD Data Browser (read-only)", id="menu-title")
            yield Button("Browse Computers",   id="menu-computers")
            yield Button("Browse Users",       id="menu-users")
            yield Button("Browse Groups",      id="menu-groups")
            yield Button("View Forest Config", id="menu-forest")
            yield Button("Quit (F10)",         id="menu-quit")
        yield ThemeFooter()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "menu-quit":
            self.app.exit()
        elif event.button.id == "menu-forest":
            self.app.push_screen(ForestScreen())
        elif event.button.id in ("menu-computers", "menu-users", "menu-groups"):
            collection = event.button.id.removeprefix("menu-")
            self.app.push_screen(BrowserScreen(collection))


# =============================================================================
# BROWSER SCREEN — filter Input + DataTable, one instance per collection.
# =============================================================================

class BrowserScreen(ArrowFocusMixin, Screen):
    # Only the filter Input is in AUTO_FOCUS's selector -- the DataTable is
    # deliberately reachable via Tab/Down from there (see the "down"
    # binding below), not auto-focused itself, so typing starts working
    # immediately on screen entry.
    AUTO_FOCUS = "#browser-filter"

    BINDINGS = [
        Binding("f1", "show_help", "Help", show=True),
        Binding("f2", "go_back", "Back", show=True),
        Binding("f7", "cycle_theme", "Theme", show=True),
        Binding("f9", "show_about", "About", show=True),
        Binding("f10", "app_quit", "Quit", show=True),
        Binding("escape", "go_back", "Back", show=False),
        # Down from the filter box moves into the table (DataTable's own
        # Up/Down -- row cursor movement -- takes over once it has focus,
        # never reaching this binding; see ArrowFocusMixin's own comment).
        Binding("down", "focus_next_item", show=False),
        Binding("up", "focus_previous_item", show=False),
    ]

    DEFAULT_CSS = """
    BrowserScreen {
        layout: vertical;
    }
    #browser-filter-row {
        height: 3;
        padding: 0 2;
    }
    #browser-filter-row Label {
        width: auto;
        margin-right: 1;
        padding-top: 1;
    }
    #browser-filter-row Input {
        width: 1fr;
    }
    #browser-count {
        padding: 0 2;
        color: $text-muted;
    }
    #browser-table {
        height: 1fr;
    }
    """

    def __init__(self, collection: str):
        super().__init__()
        self.collection = collection
        self.spec = COLLECTIONS[collection]
        self.records = self.app.data_for(collection)

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        with Horizontal(id="browser-filter-row"):
            yield Label("Filter:")
            yield Input(placeholder="type to filter -- matches name, site, description, ...",
                        id="browser-filter")
        yield Static("", id="browser-count")
        yield DataTable(id="browser-table", cursor_type="row", zebra_stripes=True)
        yield ThemeFooter()

    def on_mount(self) -> None:
        self.sub_title = f"{self.spec['title']} ({len(self.records)} total)"
        table = self.query_one("#browser-table", DataTable)
        table.add_columns(*(label for label, _ in self.spec["columns"]))
        self._refresh_rows("")

    def _refresh_rows(self, filter_text: str) -> None:
        table = self.query_one("#browser-table", DataTable)
        table.clear()
        needle = filter_text.strip().lower()
        shown = 0
        for i, record in enumerate(self.records):
            if needle and needle not in _search_text(record, self.spec["search_fields"]):
                continue
            row = [_cell_text(record.get(field, "")) for _, field in self.spec["columns"]]
            table.add_row(*row, key=str(i))
            shown += 1
        self.query_one("#browser-count", Static).update(
            f"{shown} of {len(self.records)} shown" if needle else f"{len(self.records)} record(s)"
        )

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "browser-filter":
            self._refresh_rows(event.value)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        index = int(event.row_key.value)
        self.app.push_screen(DetailScreen(self.spec["title"], self.records[index]))

    def action_go_back(self) -> None:
        self.app.pop_screen()

    def action_app_quit(self) -> None:
        self.app.exit()

    def action_show_help(self) -> None:
        self.app.action_show_help()

    def action_show_about(self) -> None:
        self.app.action_show_about()

    def action_cycle_theme(self) -> None:
        self.app.action_cycle_theme()


# =============================================================================
# DETAIL SCREEN — every field of one selected record, full values, in the
# record's own original key order (Python dicts preserve json.load()'s
# insertion order; no alphabetical re-sort, so this reads the same shape
# the real JSON file itself does).
# =============================================================================

class DetailScreen(Screen):
    BINDINGS = [
        Binding("f2", "go_back", "Back", show=True),
        Binding("f7", "cycle_theme", "Theme", show=True),
        Binding("f10", "app_quit", "Quit", show=True),
        Binding("escape", "go_back", "Back", show=False),
    ]

    DEFAULT_CSS = """
    DetailScreen {
        layout: vertical;
    }
    #detail-body {
        padding: 1 2;
    }
    .detail-row {
        height: auto;
        margin-bottom: 1;
    }
    .detail-key {
        color: $text-muted;
        width: 28;
    }
    .detail-value {
        width: 1fr;
    }
    """

    def __init__(self, collection_title: str, record: dict):
        super().__init__()
        self._collection_title = collection_title
        self._record = record

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        with VerticalScroll(id="detail-body"):
            for key, value in self._record.items():
                with Horizontal(classes="detail-row"):
                    yield Static(f"{key}:", classes="detail-key", markup=False)
                    yield Static(_cell_text(value) or "(blank)", classes="detail-value", markup=False)
        yield ThemeFooter()

    def on_mount(self) -> None:
        self.sub_title = f"{self._collection_title} — detail"

    def action_go_back(self) -> None:
        self.app.pop_screen()

    def action_app_quit(self) -> None:
        self.app.exit()

    def action_cycle_theme(self) -> None:
        self.app.action_cycle_theme()


# =============================================================================
# FOREST SCREEN — ad_forest.json is a single dict, not a list -- no
# filter/table, just every key:value pair the same way DetailScreen shows
# one record's fields.
# =============================================================================

class ForestScreen(Screen):
    BINDINGS = [
        Binding("f2", "go_back", "Back", show=True),
        Binding("f7", "cycle_theme", "Theme", show=True),
        Binding("f10", "app_quit", "Quit", show=True),
        Binding("escape", "go_back", "Back", show=False),
    ]

    DEFAULT_CSS = DetailScreen.DEFAULT_CSS

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        with VerticalScroll(id="detail-body"):
            for key, value in self.app.forest_data().items():
                with Horizontal(classes="detail-row"):
                    yield Static(f"{key}:", classes="detail-key", markup=False)
                    yield Static(_cell_text(value) or "(blank)", classes="detail-value", markup=False)
        yield ThemeFooter()

    def on_mount(self) -> None:
        self.sub_title = "ad_forest.json"

    def action_go_back(self) -> None:
        self.app.pop_screen()

    def action_app_quit(self) -> None:
        self.app.exit()

    def action_cycle_theme(self) -> None:
        self.app.action_cycle_theme()


# =============================================================================
# HELP / ABOUT
# =============================================================================

class AboutModal(ArrowFocusMixin, ModalScreen):
    AUTO_FOCUS = "Button"

    DEFAULT_CSS = """
    AboutModal { align: center middle; }
    #about-box {
        width: 64; height: auto; border: round $primary;
        padding: 0 1; background: $surface;
    }
    #about-title { text-style: bold; margin-bottom: 0; }
    """

    BINDINGS = [
        Binding("escape", "close_about", "Close", show=True),
        Binding("f10", "close_about", "Close", show=False),
        Binding("down", "focus_next_item", show=False),
        Binding("up", "focus_previous_item", show=False),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="about-box"):
            yield Label("About", id="about-title")
            yield Static("ad_data_browser.py — ad_computers/users/groups/forest.json viewer", markup=False)
            yield Static(
                "Read-only. Nothing in this tool ever writes to any file -- there is no "
                "Confirm/Save path anywhere here, unlike its sibling tool "
                "site_device_tui.py. Type in the Filter box to narrow the list by any "
                "visible-or-not field; select a row (Enter or click) to see every field "
                "of that one record.",
                markup=False,
            )
            yield Static(
                "NOT a revival of benarbejde/archive/parse_tdf.py -- that script is "
                "legacy and must never be used again. This tool only reads the "
                "already-converted JSON files already committed to the repo.",
                markup=False,
            )
            yield Button("Close (Esc)", id="about-close")
        yield ThemeFooter()

    def action_close_about(self) -> None:
        self.dismiss()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "about-close":
            self.dismiss()


class HelpModal(ArrowFocusMixin, ModalScreen):
    AUTO_FOCUS = "Button"

    DEFAULT_CSS = """
    HelpModal { align: center middle; }
    #help-box {
        width: 64; height: auto; border: round $primary;
        padding: 0 1; background: $surface;
    }
    #help-title { text-style: bold; margin-bottom: 0; }
    #help-menu-title { margin-top: 1; text-style: bold; }
    .help-line { color: $text; }
    #help-actions { height: auto; margin-top: 1; }
    """

    BINDINGS = [
        Binding("escape", "close_help", "Close", show=True),
        Binding("f10", "close_help", "Close", show=False),
        Binding("down", "focus_next_item", show=False),
        Binding("up", "focus_previous_item", show=False),
    ]

    MENU_LINES = [
        "Browse Computers/Users/Groups  Filter + table over one JSON file.",
        "View Forest Config             ad_forest.json's own key:value pairs.",
    ]

    HELP_LINES = [
        "F1              Help (this screen)",
        "F2 / Escape     Back",
        "F7              Cycle colour theme",
        "F9              About",
        "F10             Quit",
        "Enter / Click   On a table row: open that record's full detail",
        "Up/Down/PgUp/PgDn  Move within the table",
        "Tab / Shift+Tab Move between the filter box and the table",
        "Down (in filter) Also moves into the table, same as Tab",
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="help-box"):
            yield Label("Keyboard Shortcuts", id="help-title")
            for line in self.HELP_LINES:
                yield Static(line, classes="help-line", markup=False)
            yield Label("Menu Options", id="help-menu-title")
            for line in self.MENU_LINES:
                yield Static(line, classes="help-line", markup=False)
            with Horizontal(id="help-actions"):
                yield Button("About", id="help-about")
                yield Button("Close (Esc)", id="help-close")
        yield ThemeFooter()

    def action_close_help(self) -> None:
        self.dismiss()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "help-close":
            self.dismiss()
        elif event.button.id == "help-about":
            self.app.push_screen(AboutModal())


# =============================================================================
# APP
# =============================================================================

class AdDataBrowserApp(App):
    TITLE = "Example Music Limited — AD Data Browser"

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit"),
        Binding("f1", "show_help", "Help", show=True, priority=True),
        Binding("f7", "cycle_theme", "Theme", show=True, priority=True),
        Binding("f9", "show_about", "About", show=True, priority=True),
    ]
    ENABLE_COMMAND_PALETTE = False

    # Same Midnight-Commander-density override as site_device_tui.py's App
    # class, trimmed to the widgets this tool actually uses.
    CSS = """
    Input {
        height: 1;
        border: none;
        background: $boost;
        padding: 0 1;
    }
    Input:focus {
        background: $panel;
    }
    Button {
        height: 1;
        min-width: 10;
        border-top: none;
        border-bottom: none;
        padding: 0 1;
    }
    """

    def __init__(self, paths):
        super().__init__()
        self._paths = paths
        self._cache = {}
        self._forest = None
        self.theme = "textual-dark"

    def data_for(self, collection: str):
        """Lazily loaded + cached per collection -- a Pilot test overriding
        just one of the three JSON paths never has to load the other two."""
        if collection not in self._cache:
            self._cache[collection] = _load_json_list(self._paths[collection])
        return self._cache[collection]

    def forest_data(self):
        if self._forest is None:
            self._forest = _load_json_dict(self._paths["forest"])
        return self._forest

    def action_show_help(self) -> None:
        if not isinstance(self.screen, HelpModal):
            self.push_screen(HelpModal())

    def action_show_about(self) -> None:
        if not isinstance(self.screen, AboutModal):
            self.push_screen(AboutModal())

    def action_cycle_theme(self) -> None:
        names = sorted(self.available_themes)
        current = self.theme
        next_index = (names.index(current) + 1) % len(names) if current in names else 0
        self.theme = names[next_index]

    def on_mount(self) -> None:
        self.push_screen(MainMenuScreen())


# =============================================================================
# ENTRY POINT
# =============================================================================

def parse_args():
    parser = argparse.ArgumentParser(
        description="Browse benarbejde/ad_computers.json, ad_users.json, ad_groups.json, "
                     "ad_forest.json -- read-only TUI.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--computers-json", dest="computers_json", default=None,
                        help="Path to ad_computers.json (default: benarbejde/ad_computers.json)")
    parser.add_argument("--users-json", dest="users_json", default=None,
                        help="Path to ad_users.json (default: benarbejde/ad_users.json)")
    parser.add_argument("--groups-json", dest="groups_json", default=None,
                        help="Path to ad_groups.json (default: benarbejde/ad_groups.json)")
    parser.add_argument("--forest-json", dest="forest_json", default=None,
                        help="Path to ad_forest.json (default: benarbejde/ad_forest.json)")
    return parser.parse_args()


def main():
    args = parse_args()
    paths = {
        "computers": Path(args.computers_json) if args.computers_json else BENARBEJDE / "ad_computers.json",
        "users": Path(args.users_json) if args.users_json else BENARBEJDE / "ad_users.json",
        "groups": Path(args.groups_json) if args.groups_json else BENARBEJDE / "ad_groups.json",
        "forest": Path(args.forest_json) if args.forest_json else BENARBEJDE / "ad_forest.json",
    }
    app = AdDataBrowserApp(paths)
    app.run()


if __name__ == "__main__":
    main()
