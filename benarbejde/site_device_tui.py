#!/usr/bin/env python3
"""
=============================================================================
Site/Device Data Entry — TUI
=============================================================================
Full-screen Textual TUI for adding rows to benarbejde/sites.csv and
benarbejde/devices.csv -- the estate's single source of truth for site
identity/addressing and device inventory. Hand-editing these CSVs directly
is error-prone (a malformed phone number, a duplicate octet, a typo'd
timezone all currently go in silently); this tool validates each field as
it's typed and, once a row is written, calls the same regeneration/
boilerplate/consistency-check scripts a human is already supposed to run
by hand afterward (see docs/adding-new-sites-bands-devices-and-subnets.md).

This is a REPO-LOCAL tool only. Unlike bootstrap/web/proxmox/create-vm-tui.py
(its copy source), it never connects to a Proxmox API, never touches a PVE
node, and never touches any live host -- every action here is a local file
edit plus a local subprocess call to another script already in this repo.

Started as a direct copy of create-vm-tui.py (Textual TUI shell, WizardScreen
base class, ThemeFooter, widget-density CSS override) with every
Proxmox-specific piece (login/node modals, VM backend, VM-specific
validators/widgets) removed and reworked for CSV data entry instead -- see
the plan this was built from for the full rationale.

Requires:
    textual   -- TUI framework (apt: python3-textual)

Usage:
    python3 benarbejde/site_device_tui.py
    python3 benarbejde/site_device_tui.py --sites-csv /path/to/sites.csv --role-codes-csv /path/to/role_codes.csv

Build stages (see the plan -- each is independently demoable):
    1. Skeleton + main menu, no CSV writes
    2. Add-Site wizard, validation only, no writes
    3. Add-Site: real write + regenerate_all() + boilerplate offer
    4. Add-Device wizard, full flow incl. suggest_free_ip integration
    5. Post-save sanity pass + "Run Quick Checks" menu option
    6. Polish pass
    7. Tests (pytest for validators, Textual Pilot for wizard walks)   <- this stage
       -- see benarbejde/test_site_device_tui.py (requires apt: python3-pytest)
=============================================================================
"""

import argparse
import contextlib
import csv
import io
import ipaddress
import re
import subprocess
import sys
from pathlib import Path
from zoneinfo import available_timezones

try:
    from textual.app import App, ComposeResult
    from textual.binding import Binding
    from textual.containers import Horizontal, Vertical, VerticalScroll
    from textual.screen import ModalScreen, Screen
    from textual.validation import ValidationResult, Validator
    from textual.widgets import Button, Footer, Header, Input, Label, Select, Static
except ImportError:
    print("ERROR: textual not installed.")
    print("  apt install python3-textual   (already staged on this estate's control hosts)")
    print("  or: pip3 install textual")
    sys.exit(1)

BENARBEJDE = Path(__file__).resolve().parent
REPO_ROOT = BENARBEJDE.parent

# Reuse the real, already-tested implementations rather than duplicating any of
# this -- same convention check_new_site_boilerplate.py itself already uses for
# the same two modules. Both guard their own CLI logic behind
# `if __name__ == "__main__":`, confirmed before relying on this, so importing
# them has no side effect beyond defining functions/constants.
sys.path.insert(0, str(BENARBEJDE))
sys.path.insert(0, str(REPO_ROOT / "at_have_ryggen_fri"))
import regenerate_all as ra  # noqa: E402
import check_new_site_boilerplate as nsb  # noqa: E402
import suggest_free_ip as sfi  # noqa: E402
import generate_inventory as gi  # noqa: E402


# =============================================================================
# DATA LOADERS — this tool only ever runs from inside a repo checkout, so
# unlike create-vm-tui.py (which also has to work standalone from a served
# copy on a PVE node), these default straight to the real benarbejde/ files
# rather than searching cwd/$SITES_CSV/etc. An explicit --sites-csv/
# --role-codes-csv override is still supported for testing against a
# fixture copy (see Stage 7).
# =============================================================================

def _load_sites(csv_path=None):
    path = Path(csv_path) if csv_path else (BENARBEJDE / "sites.csv")
    if not path.is_file():
        print(f"ERROR: sites.csv not found at {path}")
        print("  Pass --sites-csv /path/to/sites.csv to override.")
        sys.exit(1)

    sites = {}
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            code = row["Site"].strip().upper()
            sites[code] = {k: v.strip() for k, v in row.items()}
    return sites


def _load_role_codes(csv_path=None):
    path = Path(csv_path) if csv_path else (BENARBEJDE / "role_codes.csv")
    if not path.is_file():
        print(f"ERROR: role_codes.csv not found at {path}")
        print("  Pass --role-codes-csv /path/to/role_codes.csv to override.")
        sys.exit(1)

    codes = {}
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            code = row["Code"].strip().upper()
            codes[code] = {k: v.strip() for k, v in row.items()}
    return codes


SITES = _load_sites()
ROLE_CODES = _load_role_codes()

# Needed before any Add-Device screen can call gi.build_hostname()/
# gi.policy_expected_octet() -- both read gi.OFFSETS_SINGLE/ROLE_OFFSETS,
# which start out empty until this runs (confirmed: generate_inventory.py
# itself never auto-loads this at import time, every caller does it
# explicitly). Loaded once here, same lifetime as SITES/ROLE_CODES above.
gi.load_address_policy(BENARBEJDE / "address_policy.csv")

# Allow-lists derived directly from the real data already loaded above, not
# hand-maintained -- a new site adding a country/timezone already used by an
# existing one just works with zero code changes, matching the "source of
# truth" convention the rest of this repo follows. CountryCode's allow-list
# naturally includes "N/A" without special-casing it, since CLD/VRK's own
# real rows already use that literal value.
KNOWN_COUNTRY_CODES = sorted({s["CountryCode"].upper() for s in SITES.values() if s.get("CountryCode")})
KNOWN_SUBNETS = set()
for _s in SITES.values():
    _raw = _s.get("Subnet", "")
    if _raw:
        try:
            KNOWN_SUBNETS.add(str(ipaddress.ip_network(_raw, strict=False)))
        except ValueError:
            pass
KNOWN_TIMEZONES = available_timezones()


# =============================================================================
# THEME FOOTER — unchanged from create-vm-tui.py (no VM-specific content).
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
# MAIN MENU — the app's real "home" screen (pushed directly in on_mount, no
# login/node-select/loading phase -- there's no live connection to make,
# just local CSV reads already done at import time above). Each option
# pushes its own independent wizard screen stack; see the plan for why this
# is two separate entry points rather than one branching wizard.
# =============================================================================

class MainMenuScreen(Screen):
    DEFAULT_CSS = """
    MainMenuScreen { align: center middle; }
    #menu-box { width: 48; height: auto; }
    #menu-title { text-style: bold; margin-bottom: 1; }
    #menu-box Button { width: 100%; margin-bottom: 1; }
    """

    # Duplicated here purely for Footer display order -- see
    # WizardScreen.BINDINGS for the full explanation (Footer renders
    # bindings in first-discovered order, screen-first-then-App).
    BINDINGS = [
        Binding("f1", "show_help", "Help", show=True),
        Binding("f7", "cycle_theme", "Theme", show=True),
        Binding("f9", "show_about", "About", show=True),
        Binding("f10", "app_quit", "Quit", show=True),
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
            yield Label("Example Music Limited — Site/Device Data Entry", id="menu-title")
            yield Button("Add Site",         id="menu-add-site")
            yield Button("Add Device",       id="menu-add-device")
            yield Button("Run Quick Checks", id="menu-run-checks")
            yield Button("Quit (F10)",       id="menu-quit")
        yield ThemeFooter()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "menu-add-site":
            self.app.push_screen(_new_site_wizard())
        elif event.button.id == "menu-add-device":
            self.app.push_screen(_new_device_wizard())
        elif event.button.id == "menu-run-checks":
            self.app.push_screen(QuickChecksScreen(None, _new_standalone_quick_checks))
        elif event.button.id == "menu-quit":
            self.app.exit()


# =============================================================================
# WIZARD SCREEN BASE — adapted from create-vm-tui.py's own WizardScreen.
# Same shared nav/CSS/step-title handling; generalised in one way that
# tool didn't need: action_wizard_reset() there hardcoded a return to its
# one and only wizard's own first screen (IdentityScreen). This tool has
# two independent wizards, so the "what does Reset go back to" and "what
# does Back on Step 1 go back to" targets are supplied by each concrete
# wizard via reset_factory, not hardcoded here.
# =============================================================================

class WizardScreen(Screen):
    STEP_NUM = 1
    STEP_TOTAL = 1
    STEP_TITLE = ""

    BINDINGS = [
        Binding("f1", "show_help", "Help", show=True),
        Binding("f2", "wizard_back", "Back", show=True),
        Binding("f3", "wizard_next", "Next", show=True),
        Binding("f4", "wizard_reset", "Reset", show=True),
        Binding("f7", "cycle_theme", "Theme", show=True),
        Binding("f9", "show_about", "About", show=True),
        Binding("f10", "wizard_quit", "Quit", show=True),
        Binding("ctrl+p", "wizard_back", "Back", show=False),
        Binding("ctrl+n", "wizard_next", "Next", show=False),
    ]

    DEFAULT_CSS = """
    WizardScreen {
        layout: vertical;
    }
    .step-body {
        padding: 0 2;
        height: 1fr;
    }
    .field-label {
        color: $text-muted;
        margin-top: 1;
    }
    .field-row {
        height: 1;
        margin-top: 1;
    }
    .field-row .field-label, .field-row .field-hint {
        margin-top: 0;
        width: auto;
        margin-right: 1;
    }
    .field-row Select, .field-row Input {
        width: 1fr;
    }
    .field-row Input.field-input-narrow {
        width: 20;
    }
    .field-hint {
        color: $text-muted;
        text-style: italic;
        margin-top: 1;
    }
    #step-error {
        color: $error;
        min-height: 1;
    }
    .nav-row {
        height: 1;
        margin-top: 1;
    }
    """

    def __init__(self, draft, reset_factory, *, pop_depth=None):
        """draft: this wizard's own state container (opaque to this base
        class). reset_factory: zero-arg callable returning a fresh instance
        of this wizard's own Step 1 screen -- both F4 Reset and Back-from-
        Step-1 use it, so every concrete screen must pass the same factory
        through to its next_screen().

        pop_depth: how many screens action_wizard_reset() pops before
        pushing reset_factory(). Defaults to STEP_NUM, correct for every
        screen that sits on a stack which has grown by exactly one screen
        per step since the wizard started (every Site/Device input screen).
        A screen reached AFTER a stack collapse (e.g. SiteBoilerplateScreen,
        pushed straight onto MainMenuScreen with STEP_NUM=6 but a real
        stack depth of 1) must pass the true depth explicitly -- found live
        2026-11-13: F4 Reset on SiteBoilerplateScreen tried to pop 6 screens
        off a stack only 1 deep and crashed the whole app with
        ScreenStackError, since STEP_NUM there describes "step 6 of the
        on-screen sequence", not "6 screens pushed since the base"."""
        super().__init__()
        self.draft = draft
        self._reset_factory = reset_factory
        self._reset_armed_timer = None
        self._pop_depth = pop_depth

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        with VerticalScroll(classes="step-body"):
            yield from self.compose_fields()
            yield Static("", id="step-error")
        with Horizontal(classes="nav-row"):
            yield Button(self.back_button_label(), id="nav-back")
            yield Button(self.next_button_label(), variant="primary", id="nav-next")
        yield ThemeFooter()

    def back_button_label(self) -> str:
        return "< Menu (F2)" if self.STEP_NUM <= 1 else "< Back (F2)"

    def next_button_label(self) -> str:
        return "Next > (F3)"

    def on_mount(self) -> None:
        self.sub_title = f"Step {self.STEP_NUM} of {self.STEP_TOTAL} — {self.STEP_TITLE}"

    def compose_fields(self) -> ComposeResult:
        yield from ()

    def action_wizard_back(self) -> None:
        # Step 1 pops back onto MainMenuScreen -- always a real, usable
        # screen underneath, unlike create-vm-tui.py's equivalent (which
        # had to special-case Step 1 as a no-op, since the screen below it
        # there was the App's own dead bare default). Nothing special to do
        # here either way -- pop_screen() already does the right thing at
        # every step depth in this app.
        self.app.pop_screen()

    def action_wizard_next(self) -> None:
        self._try_next()

    def action_wizard_reset(self) -> None:
        if self._reset_armed_timer is None:
            self.query_one("#step-error", Static).update(
                "Press F4 again within 5 seconds to clear every field on every page and "
                "return to Step 1. Nothing has been written to any file yet either way -- "
                "just wait 5 seconds to cancel."
            )
            self._reset_armed_timer = self.set_timer(5, self._disarm_reset)
            return

        self._disarm_reset()
        depth = self._pop_depth if self._pop_depth is not None else self.STEP_NUM
        for _ in range(depth):
            self.app.pop_screen()
        self.app.push_screen(self._reset_factory())

    def _disarm_reset(self) -> None:
        if self._reset_armed_timer is not None:
            self._reset_armed_timer.stop()
            self._reset_armed_timer = None

    def action_wizard_quit(self) -> None:
        self.app.exit()

    def action_show_help(self) -> None:
        self.app.action_show_help()

    def action_show_about(self) -> None:
        self.app.action_show_about()

    def action_cycle_theme(self) -> None:
        self.app.action_cycle_theme()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "nav-back":
            self.action_wizard_back()
        elif event.button.id == "nav-next":
            self._try_next()

    def _try_next(self) -> None:
        error = self.commit()
        if error:
            self.query_one("#step-error", Static).update(error)
            return
        nxt = self.next_screen()
        if nxt is not None:
            self.app.push_screen(nxt)

    def commit(self):
        """Validate + write this screen's fields into self.draft.
        Return an error string to block navigation, or None/'' to proceed."""
        return None

    def next_screen(self):
        """Screen instance to push next, or None to finish the wizard."""
        return None


# =============================================================================
# ADD-SITE VALIDATORS — Stage 2. Each one's failure() message is what
# WizardScreen.commit() surfaces verbatim (see _validator_error() below) --
# never a generic "Fix X" string, per the discipline create-vm-tui.py had to
# retrofit after the fact (commit 664defa). Real site codes confirmed
# directly against sites.csv before writing this: all 57 are exactly 3
# uppercase letters, no exceptions -- not the looser "2-4 letters" this was
# first drafted against.
# =============================================================================

class SiteCodeValidator(Validator):
    _PATTERN = re.compile(r"^[A-Z]{3}$")

    def validate(self, value: str) -> ValidationResult:
        v = value.strip().upper()
        if not self._PATTERN.match(v):
            return self.failure("Site code must be exactly 3 letters, e.g. FAL.")
        if v in SITES:
            return self.failure(f"Site code {v} already exists in sites.csv.")
        if v in ROLE_CODES:
            return self.failure(
                f"{v} collides with role_codes.csv's own Code {v} "
                f"({ROLE_CODES[v]['Name']}) -- pick a different site code."
            )
        return self.success()


class RequiredTextValidator(Validator):
    """Plain non-blank check -- used for fields with no fixed vocabulary
    (City, Street, Office name, ...). Deliberately NOT a closed allow-list
    the way CountryCodeValidator/TimezoneValidator are: those two are
    stable external standards, but Entity/AnsibleRegion (checked via this
    validator too) are open-world estate-specific values that legitimately
    gain a new member whenever the business opens in a new country --
    hard-blocking anything not already in sites.csv would make that
    impossible through this tool."""

    def __init__(self, field_name):
        super().__init__()
        self._field_name = field_name

    def validate(self, value: str) -> ValidationResult:
        if not value.strip():
            return self.failure(f"{self._field_name} is required.")
        return self.success()


class CountryCodeValidator(Validator):
    def validate(self, value: str) -> ValidationResult:
        v = value.strip().upper()
        if not v:
            return self.failure("Country code is required.")
        if v not in KNOWN_COUNTRY_CODES:
            return self.failure(f"'{v}' isn't a known country code. Known: {', '.join(KNOWN_COUNTRY_CODES)}")
        return self.success()


class TimezoneValidator(Validator):
    def validate(self, value: str) -> ValidationResult:
        v = value.strip()
        if not v:
            return self.failure("Timezone is required, e.g. Europe/Copenhagen.")
        if v not in KNOWN_TIMEZONES:
            return self.failure(f"'{v}' isn't a known IANA timezone, e.g. Europe/Copenhagen.")
        return self.success()


class SubnetValidator(Validator):
    def validate(self, value: str) -> ValidationResult:
        v = value.strip()
        if not v:
            return self.failure("Subnet is required, e.g. 192.168.75.0/24.")
        try:
            net = ipaddress.ip_network(v, strict=True)
        except ValueError as e:
            return self.failure(f"Not a valid CIDR subnet: {e}")
        if str(net) in KNOWN_SUBNETS:
            return self.failure(f"Subnet {v} is already used by another site.")
        return self.success()


class IPInSubnetValidator(Validator):
    """Gateway/DC/FW all share this -- a plain IP-address check plus
    containment inside whatever's currently typed in the Subnet field on
    the same screen. subnet_text_fn is a closure reading that Input's live
    .value at validate-time (it's a sibling field, not this validator's
    own value), not evaluated until called -- the Subnet Input is already
    mounted by the time any of these can actually fire."""

    def __init__(self, field_name, subnet_text_fn):
        super().__init__()
        self._field_name = field_name
        self._subnet_text_fn = subnet_text_fn

    def validate(self, value: str) -> ValidationResult:
        v = value.strip()
        if not v:
            return self.failure(f"{self._field_name} is required.")
        try:
            addr = ipaddress.ip_address(v)
        except ValueError:
            return self.failure(f"'{v}' isn't a valid IP address.")
        subnet_text = self._subnet_text_fn().strip()
        if not subnet_text:
            return self.failure("Enter a valid Subnet above first.")
        try:
            net = ipaddress.ip_network(subnet_text, strict=True)
        except ValueError:
            return self.failure("Subnet above isn't valid yet -- fix it first.")
        if addr not in net:
            return self.failure(f"{v} is not inside subnet {subnet_text}.")
        return self.success()


class PhoneValidator(Validator):
    """Robert's own named example: '555-ABC-DEFG' must be rejected. Strips
    the punctuation a real phone number legitimately contains (space, +,
    -, parens) and requires everything left over to be a digit or the
    literal 'x'/'X' placeholder character -- sites.csv's own real rows use
    exactly that convention for not-yet-assigned numbers (e.g.
    '+44 1224 496 0xxx'), so those must keep validating clean, not just
    reject bad input. Loose 6-15 digit-or-x count rather than a strict
    E.164 check -- there's no real number to validate most rows against in
    the first place (confirmed: every Landline/Mobile in sites.csv today
    is either a template or the literal 'N/A' sentinel), so strictness here
    would mostly just reject legitimate placeholders."""

    _STRIP_CHARS = " +-()"

    def validate(self, value: str) -> ValidationResult:
        v = value.strip()
        if not v:
            return self.failure("Required -- use 'N/A' if there is genuinely no number yet.")
        if v.upper() == "N/A":
            return self.success()
        stripped = "".join(c for c in v if c not in self._STRIP_CHARS)
        if not stripped:
            return self.failure("Not a usable phone number.")
        bad_chars = sorted({c for c in stripped if not (c.isdigit() or c in "xX")})
        if bad_chars:
            return self.failure(
                f"Contains non-digit character(s) {''.join(bad_chars)!r} -- "
                f"phone numbers shouldn't have letters."
            )
        if not (6 <= len(stripped) <= 15):
            return self.failure(f"Expected roughly 6-15 digits, got {len(stripped)}.")
        return self.success()


def _validator_error(input_widget: Input):
    """Re-runs the Input's own validators against its current value and
    returns the real failure_descriptions text, or None if valid -- never
    a generic 'Fix X' string. Same pattern create-vm-tui.py's commit()
    methods use (fixed there in 664defa after shipping the generic-message
    version first)."""
    result = input_widget.validate(input_widget.value)
    if result is not None and not result.is_valid:
        return " ".join(result.failure_descriptions) or "Invalid value."
    return None


def _field(label_text, input_id, *, value="", validators=None, placeholder=""):
    yield Label(label_text, classes="field-label")
    yield Input(
        value=value, placeholder=placeholder, id=input_id,
        validators=list(validators or []), validate_on=["changed"],
    )


def _select_field(label_text, select_id, options, *, value=None):
    """Select counterpart to _field() above -- same stacked label-then-widget
    rhythm (not create-vm-tui.py's side-by-side field-row Horizontal), so a
    screen mixing Input and Select fields (every Add-Device screen does)
    reads as one consistent layout rather than two different styles."""
    yield Label(label_text, classes="field-label")
    yield Select(options, id=select_id, allow_blank=False, value=value)


# =============================================================================
# ADD-SITE WIZARD — Stage 2: every screen below validates and stores into
# SiteDraft, but SiteReviewScreen's Confirm does NOT write to disk yet --
# it only previews the row that Stage 3 will actually append. Mirrors
# sites.csv's own 17-column order exactly, split across 4 input screens +
# 1 review screen (one screen per natural group of columns).
# =============================================================================

class SiteDraft:
    def __init__(self):
        self.site = ""
        self.city = ""
        self.country = ""
        self.country_code = ""
        self.province = ""
        self.office_name = ""
        self.street = ""
        self.postal_code = ""
        self.subnet = ""
        self.gateway = ""
        self.dc = ""
        self.fw = ""
        self.landline = ""
        self.mobile = ""
        self.timezone = ""
        self.ansible_region = ""
        self.entity = "Example Music Limited"

    def as_csv_row(self):
        """Exact sites.csv column order -- see the real header this must
        match: Site,City,Country,CountryCode,Province,OfficeName,Street,
        PostalCode,Subnet,Gateway,DC,FW,Landline,Mobile,Timezone,
        AnsibleRegion,Entity."""
        return [
            self.site, self.city, self.country, self.country_code,
            self.province, self.office_name, self.street, self.postal_code,
            self.subnet, self.gateway, self.dc, self.fw,
            self.landline, self.mobile, self.timezone,
            self.ansible_region, self.entity,
        ]


def _new_site_wizard():
    """reset_factory for the whole Add-Site wizard -- every screen in it
    passes this same function through so F4 Reset / Back-from-Step-1 both
    land on a genuinely fresh SiteIdentityScreen + SiteDraft, not whatever
    was previously half-typed."""
    return SiteIdentityScreen(SiteDraft(), _new_site_wizard)


class SiteIdentityScreen(WizardScreen):
    STEP_NUM = 1
    STEP_TOTAL = 5
    STEP_TITLE = "Site Identity"

    def compose_fields(self) -> ComposeResult:
        d = self.draft
        yield from _field("Site code (3 letters)", "site-code", value=d.site,
                          validators=[SiteCodeValidator()], placeholder="FAL")
        yield from _field("City", "site-city", value=d.city,
                          validators=[RequiredTextValidator("City")])
        yield from _field("Country", "site-country", value=d.country,
                          validators=[RequiredTextValidator("Country")])
        yield from _field("Country code", "site-countrycode", value=d.country_code,
                          validators=[CountryCodeValidator()], placeholder="e.g. UK, DK, US")
        yield from _field("Province/State (optional)", "site-province", value=d.province)
        yield from _field("Office name", "site-officename", value=d.office_name,
                          validators=[RequiredTextValidator("Office name")])

    def commit(self):
        for fid in ("site-code", "site-city", "site-country", "site-countrycode", "site-officename"):
            err = _validator_error(self.query_one(f"#{fid}", Input))
            if err:
                return err
        d = self.draft
        d.site = self.query_one("#site-code", Input).value.strip().upper()
        d.city = self.query_one("#site-city", Input).value.strip()
        d.country = self.query_one("#site-country", Input).value.strip()
        d.country_code = self.query_one("#site-countrycode", Input).value.strip().upper()
        d.province = self.query_one("#site-province", Input).value.strip()
        d.office_name = self.query_one("#site-officename", Input).value.strip()
        return None

    def next_screen(self):
        return SiteAddressScreen(self.draft, self._reset_factory)


class SiteAddressScreen(WizardScreen):
    STEP_NUM = 2
    STEP_TOTAL = 5
    STEP_TITLE = "Address"

    def compose_fields(self) -> ComposeResult:
        d = self.draft
        yield from _field("Street", "site-street", value=d.street,
                          validators=[RequiredTextValidator("Street")])
        yield from _field("Postal code", "site-postalcode", value=d.postal_code,
                          validators=[RequiredTextValidator("Postal code")])
        yield from _field("Timezone (IANA)", "site-timezone", value=d.timezone,
                          validators=[TimezoneValidator()], placeholder="Europe/Copenhagen")
        yield from _field("Ansible region", "site-ansibleregion", value=d.ansible_region,
                          validators=[RequiredTextValidator("Ansible region")],
                          placeholder="e.g. uk_site, dk_site, cloud_site")
        yield from _field("Entity", "site-entity", value=d.entity,
                          validators=[RequiredTextValidator("Entity")])

    def commit(self):
        for fid in ("site-street", "site-postalcode", "site-timezone", "site-ansibleregion", "site-entity"):
            err = _validator_error(self.query_one(f"#{fid}", Input))
            if err:
                return err
        d = self.draft
        d.street = self.query_one("#site-street", Input).value.strip()
        d.postal_code = self.query_one("#site-postalcode", Input).value.strip()
        d.timezone = self.query_one("#site-timezone", Input).value.strip()
        d.ansible_region = self.query_one("#site-ansibleregion", Input).value.strip()
        d.entity = self.query_one("#site-entity", Input).value.strip()
        return None

    def next_screen(self):
        return SiteNetworkScreen(self.draft, self._reset_factory)


class SiteNetworkScreen(WizardScreen):
    STEP_NUM = 3
    STEP_TOTAL = 5
    STEP_TITLE = "Network"

    def compose_fields(self) -> ComposeResult:
        d = self.draft
        subnet_text_fn = lambda: self.query_one("#site-subnet", Input).value  # noqa: E731
        yield from _field("Subnet (CIDR)", "site-subnet", value=d.subnet,
                          validators=[SubnetValidator()], placeholder="192.168.75.0/24")
        yield from _field("Gateway", "site-gateway", value=d.gateway,
                          validators=[IPInSubnetValidator("Gateway", subnet_text_fn)])
        yield from _field("DC (domain controller) address", "site-dc", value=d.dc,
                          validators=[IPInSubnetValidator("DC", subnet_text_fn)])
        yield from _field("FW (firewall) address", "site-fw", value=d.fw,
                          validators=[IPInSubnetValidator("FW", subnet_text_fn)])

    def commit(self):
        for fid in ("site-subnet", "site-gateway", "site-dc", "site-fw"):
            err = _validator_error(self.query_one(f"#{fid}", Input))
            if err:
                return err
        d = self.draft
        d.subnet = self.query_one("#site-subnet", Input).value.strip()
        d.gateway = self.query_one("#site-gateway", Input).value.strip()
        d.dc = self.query_one("#site-dc", Input).value.strip()
        d.fw = self.query_one("#site-fw", Input).value.strip()
        return None

    def next_screen(self):
        return SitePhoneScreen(self.draft, self._reset_factory)


class SitePhoneScreen(WizardScreen):
    STEP_NUM = 4
    STEP_TOTAL = 5
    STEP_TITLE = "Phone Numbers"

    def compose_fields(self) -> ComposeResult:
        d = self.draft
        yield from _field("Landline (or 'N/A')", "site-landline", value=d.landline,
                          validators=[PhoneValidator()], placeholder="+44 1224 496 0xxx")
        yield from _field("Mobile (or 'N/A')", "site-mobile", value=d.mobile,
                          validators=[PhoneValidator()], placeholder="+44 7xxx xxxxxx")

    def commit(self):
        for fid in ("site-landline", "site-mobile"):
            err = _validator_error(self.query_one(f"#{fid}", Input))
            if err:
                return err
        d = self.draft
        d.landline = self.query_one("#site-landline", Input).value.strip()
        d.mobile = self.query_one("#site-mobile", Input).value.strip()
        return None

    def next_screen(self):
        return SiteReviewScreen(self.draft, self._reset_factory)


class SiteReviewScreen(WizardScreen):
    STEP_NUM = 5
    STEP_TOTAL = 5
    STEP_TITLE = "Review"

    DEFAULT_CSS = """
    #review-result {
        margin-top: 1;
    }
    """

    def __init__(self, draft, reset_factory):
        super().__init__(draft, reset_factory)
        # Guards against appending the sites.csv row twice if Confirm is
        # pressed again after a regenerate_all() failure (see commit()) --
        # the row write and the regeneration are allowed to be retried
        # independently, but the write itself must only ever happen once
        # per screen instance.
        self._written = False
        self._write_succeeded = False

    def compose_fields(self) -> ComposeResult:
        d = self.draft
        rows = [
            ("Site", d.site), ("City", d.city), ("Country", d.country),
            ("Country code", d.country_code), ("Province", d.province or "(blank)"),
            ("Office name", d.office_name), ("Street", d.street),
            ("Postal code", d.postal_code), ("Subnet", d.subnet),
            ("Gateway", d.gateway), ("DC", d.dc), ("FW", d.fw),
            ("Landline", d.landline), ("Mobile", d.mobile),
            ("Timezone", d.timezone), ("Ansible region", d.ansible_region),
            ("Entity", d.entity),
        ]
        for label, value in rows:
            yield Static(f"{label}: {value}", classes="field-hint", markup=False)
        yield Static("", id="review-result", markup=False)

    def next_button_label(self) -> str:
        return "Confirm (F3)"

    def commit(self):
        if not self._written:
            with (BENARBEJDE / "sites.csv").open("a", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow(self.draft.as_csv_row())
            # Sync the served mirror immediately, same reasoning
            # write_rows_and_regenerate() already uses for devices.csv --
            # leaves the tree internally consistent right away rather than
            # waiting on .githooks/pre-commit's next run.
            (REPO_ROOT / "bootstrap" / "web" / "proxmox" / "sites.csv").write_bytes(
                (BENARBEJDE / "sites.csv").read_bytes()
            )
            self._written = True

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            ok = ra.regenerate_all(REPO_ROOT, BENARBEJDE / "devices.csv", BENARBEJDE / "sites.csv")
        log = buf.getvalue()

        if not ok:
            self._write_succeeded = False
            self.query_one("#review-result", Static).update(
                f"sites.csv row for {self.draft.site} WAS written, but regeneration failed:\n\n"
                f"{log}\n"
                "Press Confirm again to retry regeneration (the row itself won't be "
                "written twice) once the problem above is fixed."
            )
            return None

        self._write_succeeded = True
        self.query_one("#review-result", Static).update(
            f"Wrote {self.draft.site} to sites.csv and regenerated every derived "
            f"artefact:\n\n{log}"
        )
        return None

    def next_screen(self):
        if not self._write_succeeded:
            return None  # stays here -- the error is already shown above
        # Collapse the whole 5-screen wizard stack back onto MainMenuScreen
        # and push the boilerplate offer directly on top of it, rather than
        # stacking it on top of THIS screen -- going back from here with F2
        # would otherwise land back on a Review screen whose Confirm button
        # still exists and would try to write a second, duplicate row.
        for _ in range(self.STEP_NUM):
            self.app.pop_screen()
        self.app.push_screen(SiteBoilerplateScreen(self.draft, self._reset_factory))
        return None


class SiteBoilerplateScreen(WizardScreen):
    """Offered once, directly after a successful sites.csv write -- not
    part of the 5-step numbering above (it's a one-off follow-on action,
    not another piece of sites.csv itself), but still shown with a step
    indicator for consistency. Delegates entirely to
    at_have_ryggen_fri/check_new_site_boilerplate.py's own apply_boilerplate()
    -- it already knows the full day-one equipment list, already refuses
    safely if the site turns out to have devices.csv rows somehow, and
    already calls regenerate_all() itself, so this screen does no CSV
    writing of its own at all."""

    STEP_NUM = 6
    STEP_TOTAL = 6
    STEP_TITLE = "Standard Equipment"

    DEFAULT_CSS = """
    #boilerplate-result {
        margin-top: 1;
    }
    """

    def __init__(self, draft, reset_factory):
        # Real stack depth here is always 1 (SiteReviewScreen.next_screen()
        # collapses the stack to MainMenuScreen before pushing this screen) --
        # NOT STEP_NUM(=6), which only describes this screen's position in
        # the on-screen step sequence. See WizardScreen.__init__'s pop_depth
        # docstring for the live crash this fixes.
        super().__init__(draft, reset_factory, pop_depth=1)

    def compose_fields(self) -> ComposeResult:
        yield Static(
            f"{self.draft.site} was added to sites.csv.\n\n"
            "Apply the standard day-one equipment boilerplate now? This writes real "
            "devices.csv rows (RTR/FWL/SWI/WAP/SBC/RDR/NAS/DCS + 2x PVE+BMC, all "
            "Planned=yes) and regenerates every derived artefact again.",
            classes="field-hint", markup=False,
        )
        yield Static("", id="boilerplate-result", markup=False)

    def next_button_label(self) -> str:
        return "Apply Boilerplate (F3)"

    def back_button_label(self) -> str:
        return "Skip, back to Menu (F2)"

    def commit(self):
        problems = []
        sites = nsb.load_sites(problems)
        devices_sites = nsb.load_devices_sites(problems)
        boilerplate = nsb.load_boilerplate(problems)
        if problems:
            self.query_one("#boilerplate-result", Static).update("\n".join(problems))
            return None
        nsb.gi.load_address_policy(BENARBEJDE / "address_policy.csv")

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            nsb.apply_boilerplate(self.draft.site, sites, devices_sites, boilerplate)
        self.query_one("#boilerplate-result", Static).update(buf.getvalue())
        return None

    def next_screen(self):
        return None  # stays here showing the result either way


# =============================================================================
# ADD-DEVICE VALIDATORS — Stage 4.
# =============================================================================

class OptionalSiteCodeValidator(Validator):
    """SubnetSite is deliberately optional (most devices have no override) --
    blank is always valid; a non-blank value must be a real site code, the
    inverse of SiteCodeValidator's "must not exist yet" check above (this one
    must already exist)."""

    def validate(self, value: str) -> ValidationResult:
        v = value.strip().upper()
        if not v:
            return self.success()
        if v not in SITES:
            return self.failure(f"'{v}' isn't a known site code in sites.csv.")
        return self.success()


class DeviceOctetValidator(Validator):
    """role_fn/occupied_fn/reserved_fn are closures read at validate-time, not
    captured values -- same reasoning as SiteNetworkScreen's
    IPInSubnetValidator.subnet_text_fn, so one Validator instance stays
    correct even though occupied/reserved were snapshotted when the screen
    mounted. A candidate octet already used by a real device always fails,
    regardless of Type; an octet address_policy.csv reserves for a
    DIFFERENT Type than the one being added also fails -- but a role's own
    standard slot (e.g. RTR at .1) correctly passes, since the reservation
    there is FOR that same Type, not against it."""

    def __init__(self, role_fn, occupied_fn, reserved_fn):
        super().__init__()
        self._role_fn = role_fn
        self._occupied_fn = occupied_fn
        self._reserved_fn = reserved_fn

    def validate(self, value: str) -> ValidationResult:
        v = value.strip()
        if not v.isdigit():
            return self.failure("HostOctet must be a whole number, e.g. 83.")
        octet = int(v)
        if not (1 <= octet <= 254):
            return self.failure("HostOctet must be between 1 and 254.")

        occupied = self._occupied_fn()
        if octet in occupied:
            return self.failure(f".{octet} is already occupied by {', '.join(occupied[octet])}.")

        role = self._role_fn()
        labels = self._reserved_fn().get(octet)
        if labels:
            types_here = {lbl.split(" ", 1)[0] for lbl in labels}
            if role not in types_here:
                return self.failure(
                    f".{octet} is reserved by address_policy.csv for "
                    f"{', '.join(sorted(types_here))}, not {role}."
                )
        return self.success()


# Fixed, closed vocabularies -- confirmed directly against every real value
# devices.csv's own rows currently use for each column (Managed/Migrating/
# Planned: blank/no/yes; Legacy additionally allows 'review'; ConnectionType:
# the same 7 values role_codes.csv's own ConnectionMethod column is drawn
# from), not hand-guessed.
BOOL_OPTIONS = [("(blank)", ""), ("no", "no"), ("yes", "yes")]
LEGACY_OPTIONS = BOOL_OPTIONS + [("review", "review")]
CONNECTION_TYPE_OPTIONS = [("(blank)", "")] + [
    (v, v) for v in ("http", "https", "none", "snmp", "ssh", "telnet", "winrm")
]


def _next_device_number(site, role):
    """Smallest positive integer not already used by an existing Site+Type
    row in devices.csv -- matches generate_inventory.py's build_hostname()
    convention (EXA<Type><Site><NNN>) exactly, so the Number this returns is
    always hostname-collision-free against every existing row of the same
    Site+Type (a different Type at the same Number is a different hostname
    string regardless, so no cross-Type check is needed here)."""
    used = set()
    with (BENARBEJDE / "devices.csv").open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("Site", "").strip().upper() == site and row.get("Type", "").strip().upper() == role:
                n = row.get("Number", "").strip()
                if n.isdigit():
                    used.add(int(n))
    n = 1
    while n in used:
        n += 1
    return n


# =============================================================================
# ADD-DEVICE WIZARD — Stage 4. Mirrors devices.csv's own 12-column order,
# split across Site/Role/Octet/Detail input screens + one Review screen.
# Unlike Add-Site, Number and Site/Type are never free text -- Site/Type come
# from a closed Select (sorted SITES/ROLE_CODES), and Number is always
# computed by _next_device_number(), never typed, so there is no path to a
# duplicate (Site, Type, Number) triple through this wizard.
# =============================================================================

class DeviceDraft:
    def __init__(self):
        self.site = ""
        self.type = ""
        self.number = 1
        self.host_octet = ""
        self.os = ""
        self.connection_type = ""
        self.managed = ""
        self.notes = ""
        self.subnet_site = ""
        self.legacy = ""
        self.migrating = ""
        self.planned = ""

    def as_csv_row(self):
        """Exact devices.csv column order: Site,Type,Number,HostOctet,OS,
        ConnectionType,Managed,Notes,SubnetSite,Legacy,Migrating,Planned."""
        return [
            self.site, self.type, str(self.number), self.host_octet,
            self.os, self.connection_type, self.managed, self.notes,
            self.subnet_site, self.legacy, self.migrating, self.planned,
        ]

    def hostname(self):
        return gi.build_hostname(self.type, self.site, self.number)


def _new_device_wizard():
    return DeviceSiteScreen(DeviceDraft(), _new_device_wizard)


class DeviceSiteScreen(WizardScreen):
    STEP_NUM = 1
    STEP_TOTAL = 5
    STEP_TITLE = "Site"

    def compose_fields(self) -> ComposeResult:
        d = self.draft
        yield from _select_field(
            "Site:", "device-site",
            [(f"{code} — {SITES[code].get('City', '')}, {SITES[code].get('Country', '')}", code)
             for code in sorted(SITES)],
            value=d.site or sorted(SITES)[0],
        )

    def commit(self):
        self.draft.site = self.query_one("#device-site", Select).value
        return None

    def next_screen(self):
        return DeviceRoleScreen(self.draft, self._reset_factory)


class DeviceRoleScreen(WizardScreen):
    STEP_NUM = 2
    STEP_TOTAL = 5
    STEP_TITLE = "Role"

    def compose_fields(self) -> ComposeResult:
        d = self.draft
        yield from _select_field(
            "Type (role code):", "device-role",
            [(f"{code} — {ROLE_CODES[code]['Name']}", code) for code in sorted(ROLE_CODES)],
            value=d.type or sorted(ROLE_CODES)[0],
        )
        yield Static("", id="role-hint", classes="field-hint", markup=False)

    def on_mount(self) -> None:
        super().on_mount()
        self._update_hint()

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "device-role":
            self._update_hint()

    def _update_hint(self) -> None:
        role = self.query_one("#device-role", Select).value
        number = _next_device_number(self.draft.site, role)
        lines = [
            f"This will be instance #{number} of {role} at {self.draft.site} -- "
            f"hostname {gi.build_hostname(role, self.draft.site, number)}."
        ]
        slot = gi.policy_expected_octet(role, number)
        if slot and slot[0] == "exact":
            lines.append(f"address_policy.csv expects {role} at the standard .{slot[1]} slot.")
        elif slot and slot[0] == "pool":
            lines.append(
                f"Shares the BMC pool with address_policy.csv "
                f"({sfi.format_ranges(sorted(slot[1]))})."
            )
        if role == "DCR":
            lines.append(
                "DCR is role_codes.csv's legacy alias for DCS -- check_dcr_devices.py will "
                "flag this as a likely typo. Pick DCS instead unless this really is meant "
                "as the legacy code."
            )
        self.query_one("#role-hint", Static).update("\n".join(lines))

    def commit(self):
        role = self.query_one("#device-role", Select).value
        self.draft.type = role
        self.draft.number = _next_device_number(self.draft.site, role)
        return None

    def next_screen(self):
        return DeviceOctetScreen(self.draft, self._reset_factory)


class DeviceOctetScreen(WizardScreen):
    STEP_NUM = 3
    STEP_TOTAL = 5
    STEP_TITLE = "Address (HostOctet)"

    def __init__(self, draft, reset_factory):
        super().__init__(draft, reset_factory)
        # Snapshotted once per screen instance -- re-entering this step (via
        # F2 Back then F3 Next again) builds a fresh instance with fresh
        # data, same lifetime as every other per-step state in this tool.
        self._occupied = sfi.load_occupied_octets(draft.site)
        self._reserved = sfi.load_reserved_octets()

    def _suggested_octet(self) -> str:
        slot = gi.policy_expected_octet(self.draft.type, self.draft.number)
        if slot and slot[0] == "exact":
            return str(slot[1])
        if slot and slot[0] == "pool":
            free = sorted(o for o in slot[1] if o not in self._occupied)
            if free:
                return str(free[0])
        all_used = set(self._occupied) | set(self._reserved)
        free = [o for o in range(2, 255) if o not in all_used]
        return str(free[0]) if free else ""

    def compose_fields(self) -> ComposeResult:
        d = self.draft
        subnet = SITES[d.site].get("Subnet", "")
        prefix = subnet.split("/")[0].rsplit(".", 1)[0] if subnet else ""
        all_used = sorted(set(self._occupied) | set(self._reserved))
        free = [o for o in range(2, 255) if o not in all_used]
        shown = sfi.format_ranges(free[:20]) + (", ..." if len(free) > 20 else "")
        yield Static(
            f"Subnet {subnet} ({prefix}.x) -- {len(free)} free octet(s) estate-wide: {shown}",
            classes="field-hint", markup=False,
        )
        yield from _field(
            "HostOctet", "device-octet",
            value=d.host_octet or self._suggested_octet(),
            validators=[DeviceOctetValidator(
                lambda: self.draft.type, lambda: self._occupied, lambda: self._reserved,
            )],
            placeholder="e.g. 83",
        )

    def commit(self):
        err = _validator_error(self.query_one("#device-octet", Input))
        if err:
            return err
        self.draft.host_octet = self.query_one("#device-octet", Input).value.strip()
        return None

    def next_screen(self):
        return DeviceDetailScreen(self.draft, self._reset_factory)


class DeviceDetailScreen(WizardScreen):
    STEP_NUM = 4
    STEP_TOTAL = 5
    STEP_TITLE = "Details"

    def compose_fields(self) -> ComposeResult:
        d = self.draft
        # Pre-filled from check_new_site_boilerplate.py's own CONNECTION_TYPES
        # override dict, not role_codes.csv's ConnectionMethod column at face
        # value -- that dict exists specifically because reality has drifted
        # from the aspirational policy doc for some Types (WAP is documented
        # as snmp there but every real WAP row uses http). Falls back to
        # role_codes.csv only for a Type CONNECTION_TYPES doesn't cover.
        default_conn = d.connection_type or nsb.CONNECTION_TYPES.get(
            d.type, ROLE_CODES.get(d.type, {}).get("ConnectionMethod", "")
        )
        yield from _field("OS (optional)", "device-os", value=d.os,
                          placeholder="e.g. Debian, Windows Server 2022")
        yield from _select_field("ConnectionType:", "device-conntype",
                                 CONNECTION_TYPE_OPTIONS, value=default_conn)
        yield from _select_field("Managed:", "device-managed", BOOL_OPTIONS, value=d.managed)
        yield from _field("Notes (optional)", "device-notes", value=d.notes)
        yield from _field(
            "SubnetSite override (optional)", "device-subnetsite", value=d.subnet_site,
            validators=[OptionalSiteCodeValidator()],
            placeholder="leave blank unless this device's HostOctet is really on another site's subnet",
        )
        yield from _select_field("Legacy:", "device-legacy", LEGACY_OPTIONS, value=d.legacy)
        yield from _select_field("Migrating:", "device-migrating", BOOL_OPTIONS, value=d.migrating)
        yield from _select_field("Planned:", "device-planned", BOOL_OPTIONS, value=d.planned)

    def commit(self):
        err = _validator_error(self.query_one("#device-subnetsite", Input))
        if err:
            return err
        d = self.draft
        d.os = self.query_one("#device-os", Input).value.strip()
        d.connection_type = self.query_one("#device-conntype", Select).value
        d.managed = self.query_one("#device-managed", Select).value
        d.notes = self.query_one("#device-notes", Input).value.strip()
        d.subnet_site = self.query_one("#device-subnetsite", Input).value.strip().upper()
        d.legacy = self.query_one("#device-legacy", Select).value
        d.migrating = self.query_one("#device-migrating", Select).value
        d.planned = self.query_one("#device-planned", Select).value
        return None

    def next_screen(self):
        return DeviceReviewScreen(self.draft, self._reset_factory)


class DeviceReviewScreen(WizardScreen):
    STEP_NUM = 5
    STEP_TOTAL = 5
    STEP_TITLE = "Review"

    DEFAULT_CSS = """
    #device-review-result {
        margin-top: 1;
    }
    """

    def __init__(self, draft, reset_factory):
        super().__init__(draft, reset_factory)
        # Same double-guard as SiteReviewScreen -- the row write and the
        # regeneration retry are independent, but the write itself must only
        # ever happen once per screen instance.
        self._written = False
        self._write_succeeded = False

    def compose_fields(self) -> ComposeResult:
        d = self.draft
        rows = [
            ("Site", d.site), ("Type", d.type), ("Number", d.number),
            ("Hostname", d.hostname()), ("HostOctet", d.host_octet),
            ("OS", d.os or "(blank)"), ("ConnectionType", d.connection_type or "(blank)"),
            ("Managed", d.managed or "(blank)"), ("Notes", d.notes or "(blank)"),
            ("SubnetSite", d.subnet_site or "(blank)"), ("Legacy", d.legacy or "(blank)"),
            ("Migrating", d.migrating or "(blank)"), ("Planned", d.planned or "(blank)"),
        ]
        for label, value in rows:
            yield Static(f"{label}: {value}", classes="field-hint", markup=False)
        yield Static("", id="device-review-result", markup=False)

    def next_button_label(self) -> str:
        return "Confirm (F3)"

    def commit(self):
        if not self._written:
            with (BENARBEJDE / "devices.csv").open("a", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow(self.draft.as_csv_row())
            (REPO_ROOT / "bootstrap" / "web" / "proxmox" / "devices.csv").write_bytes(
                (BENARBEJDE / "devices.csv").read_bytes()
            )
            self._written = True

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            ok = ra.regenerate_all(REPO_ROOT, BENARBEJDE / "devices.csv", BENARBEJDE / "sites.csv")
        log = buf.getvalue()

        if not ok:
            self._write_succeeded = False
            self.query_one("#device-review-result", Static).update(
                f"devices.csv row for {self.draft.hostname()} WAS written, but regeneration "
                f"failed:\n\n{log}\n"
                "Press Confirm again to retry regeneration (the row itself won't be "
                "written twice) once the problem above is fixed."
            )
            return None

        self._write_succeeded = True
        self.query_one("#device-review-result", Static).update(
            f"Wrote {self.draft.hostname()} to devices.csv and regenerated every derived "
            f"artefact:\n\n{log}"
        )
        return None

    def next_screen(self):
        if not self._write_succeeded:
            return None  # stays here -- the error is already shown above
        # Same collapse-then-push pattern as SiteReviewScreen.next_screen() --
        # going back from here must never land on a Review screen whose
        # Confirm button could try to write a second row.
        for _ in range(self.STEP_NUM):
            self.app.pop_screen()
        self.app.push_screen(QuickChecksScreen(
            self.draft, self._reset_factory, step_num=6, step_total=6,
            after_hostname=self.draft.hostname(),
        ))
        return None


# =============================================================================
# QUICK CHECKS — Stage 5. Runs the three devices.csv sanity checks
# at_have_ryggen_fri already ships, directly against the real committed
# files -- confirmed by reading each one (check_duplicate_devices.py,
# check_subnet_site_mismatch.py, check_dcr_devices.py): none accepts a path
# override, so this only ever makes sense post-write, never against an
# in-progress draft. Shared by two call sites: automatically after a
# successful Add-Device write (DeviceReviewScreen.next_screen() above), and
# on demand from MainMenuScreen's own "Run Quick Checks" button.
# =============================================================================

QUICK_CHECK_SCRIPTS = [
    ("check_duplicate_devices.py", "Duplicate hostnames/IPs"),
    ("check_subnet_site_mismatch.py", "SubnetSite overrides"),
    ("check_dcr_devices.py", "DCR (legacy DC naming) rows"),
]


def _run_quick_checks():
    results = []
    for script, label in QUICK_CHECK_SCRIPTS:
        proc = subprocess.run(
            [sys.executable, str(REPO_ROOT / "at_have_ryggen_fri" / script)],
            cwd=REPO_ROOT, capture_output=True, text=True,
        )
        output = (proc.stdout + proc.stderr).strip()
        results.append((label, proc.returncode, output))
    return results


def _format_quick_check_results(results):
    blocks = []
    for label, rc, output in results:
        status = "OK" if rc == 0 else "FLAGGED"
        blocks.append(f"[{status}] {label}\n{output}")
    return "\n\n".join(blocks)


def _new_standalone_quick_checks():
    return QuickChecksScreen(None, _new_standalone_quick_checks)


class QuickChecksScreen(WizardScreen):
    """Doubles as a standalone menu destination (STEP_NUM=1/1, draft=None,
    reset_factory=itself -- there's no wizard state to lose, F4 Reset just
    re-runs the checks) and as the Add-Device wizard's post-save screen
    (STEP_NUM=6/6, after_hostname set, pop_depth=1 since it's pushed onto a
    freshly-collapsed stack the same way SiteBoilerplateScreen is -- see
    WizardScreen.__init__'s pop_depth docstring for the crash this avoids).
    STEP_NUM/STEP_TOTAL/STEP_TITLE are set per-instance here rather than as
    class attributes, since the same class serves both step positions."""

    def __init__(self, draft, reset_factory, *, step_num=1, step_total=1, after_hostname=None):
        super().__init__(draft, reset_factory, pop_depth=1)
        self.STEP_NUM = step_num
        self.STEP_TOTAL = step_total
        self.STEP_TITLE = "Quick Checks"
        self._after_hostname = after_hostname

    def compose_fields(self) -> ComposeResult:
        heading = (
            f"Post-save checks for {self._after_hostname}:"
            if self._after_hostname else
            "Runs check_duplicate_devices.py, check_subnet_site_mismatch.py, and "
            "check_dcr_devices.py from at_have_ryggen_fri against the real, committed "
            "devices.csv/inventory -- the same three checks run automatically after "
            "every Add-Device write."
        )
        yield Static(heading, classes="field-hint", markup=False)
        yield Static("", id="quick-check-result", markup=False)

    def on_mount(self) -> None:
        super().on_mount()
        self._run()

    def _run(self) -> None:
        self.query_one("#quick-check-result", Static).update(
            _format_quick_check_results(_run_quick_checks())
        )

    def back_button_label(self) -> str:
        return "Back to Menu (F2)"

    def next_button_label(self) -> str:
        return "Re-run Checks (F3)"

    def commit(self):
        self._run()
        return None

    def next_screen(self):
        return None  # stays here -- re-run is in place, not a new screen


# =============================================================================
# HELP / ABOUT
# =============================================================================

class AboutModal(ModalScreen):
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
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="about-box"):
            yield Label("About", id="about-title")
            yield Static("site_device_tui.py — sites.csv/devices.csv data entry", markup=False)
            yield Static(
                "Add Site and Add Device each validate every field, then write one real "
                "row to benarbejde/sites.csv or devices.csv and call this repo's own "
                "regenerate_all()/apply_boilerplate()/quick-checks scripts -- the same "
                "ones docs/adding-new-sites-bands-devices-and-subnets.md already documents "
                "as the manual follow-up steps.",
                markup=False,
            )
            yield Static(
                "Local-only -- never connects to a Proxmox API, never touches a PVE node "
                "or any other live host. Nothing is written to any file until a wizard's "
                "Review screen's Confirm is pressed.",
                markup=False,
            )
            yield Button("Close (Esc)", id="about-close")
        yield ThemeFooter()

    def action_close_about(self) -> None:
        self.dismiss()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "about-close":
            self.dismiss()


class HelpModal(ModalScreen):
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
    ]

    MENU_LINES = [
        "Add Site         Validate then write one row to sites.csv, offer the",
        "                 standard day-one equipment boilerplate afterwards.",
        "Add Device       Validate then write one row to devices.csv, run the",
        "                 post-save quick checks afterwards automatically.",
        "Run Quick Checks Run the same post-save checks on demand, any time --",
        "                 not tied to just-having added a device.",
    ]

    HELP_LINES = [
        "F1              Help (this screen)",
        "F2              Back / Menu",
        "F3              Next / Confirm / Re-run (label on the button says which)",
        "F4              Reset (press twice) -- clears every page, back to Step 1.",
        "                Only clears UNSAVED input -- a row already written by",
        "                Confirm is not undone by this.",
        "F7              Cycle colour theme",
        "F9              About",
        "F10             Quit",
        "Ctrl+P / Ctrl+N Back / Next (alternate)",
        "Tab / Shift+Tab Move between fields",
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

class SiteDeviceTuiApp(App):
    TITLE = "Example Music Limited — Site/Device Data Entry"

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit"),
        Binding("f1", "show_help", "Help", show=True, priority=True),
        Binding("f7", "cycle_theme", "Theme", show=True, priority=True),
        Binding("f9", "show_about", "About", show=True, priority=True),
    ]
    ENABLE_COMMAND_PALETTE = False

    # Same Midnight-Commander-density override as create-vm-tui.py's App
    # class -- trimmed to the widgets this tool actually uses so far
    # (Select/RadioSet/Checkbox rules will be reintroduced in Stage 2+ as
    # those screens are built, not kept here speculatively).
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
    Input.-invalid {
        background: $error 30%;
    }
    Input.-invalid:focus {
        background: $error 50%;
    }
    Select > SelectCurrent {
        height: 1;
        border: none;
        background: $boost;
        padding: 0 1;
    }
    Select:focus > SelectCurrent {
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

    def __init__(self, args):
        super().__init__()
        self.args = args
        self.theme = "textual-dark"

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
        description="Add sites/devices to benarbejde/sites.csv and devices.csv -- TUI.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--sites-csv", dest="sites_csv", default=None,
                        help="Path to sites.csv (default: benarbejde/sites.csv)")
    parser.add_argument("--role-codes-csv", dest="role_codes_csv", default=None,
                        help="Path to role_codes.csv (default: benarbejde/role_codes.csv)")
    return parser.parse_args()


def main():
    global SITES, ROLE_CODES
    args = parse_args()

    if args.sites_csv:
        SITES = _load_sites(args.sites_csv)
    if args.role_codes_csv:
        ROLE_CODES = _load_role_codes(args.role_codes_csv)

    app = SiteDeviceTuiApp(args)
    app.run()


if __name__ == "__main__":
    main()
