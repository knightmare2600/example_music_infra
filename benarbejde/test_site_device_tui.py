#!/usr/bin/env python3
"""
test_site_device_tui.py -- Stage 7 of site_device_tui.py's build plan.

No Pilot/headless-Textual-test usage existed anywhere in this repo before
this file (confirmed before writing it -- only one informal dev-time
comment referenced the idea). This is new test infrastructure, not an
existing convention to follow.

Requires (apt, same as site_device_tui.py's own textual dependency):
    python3-pytest

Run: python3 -m pytest benarbejde/test_site_device_tui.py -v

Three layers:
  1. Plain Validator unit tests -- no Textual runtime, no filesystem beyond
     the fixture_repo below.
  2. Pilot navigation tests -- menu/help/about/F4-reset, no CSV writes.
  3. Pilot write-content tests -- exercise Confirm for real, against a
     fixture_repo built fresh under tmp_path every test, NEVER the real
     benarbejde/ files. regenerate_all() is monkeypatched to a stub for
     these (see fixture_repo's own docstring for exactly why: it's the one
     function in this whole chain that's safe to fake, and the one that
     genuinely isn't safe to call for real here).

Deliberately NOT covered by automated tests, matching the build plan's own
call on this (Stage 7, "regenerate_all()... is directly testable against
fixtures; suggest_free_ip.py and the check_*.py scripts use hardcoded
module-level paths with no override, so their integrations are covered by
each stage's manual demo rather than automated tests"):
  - SiteBoilerplateScreen's write path -- delegates to
    check_new_site_boilerplate.py's own apply_boilerplate(), which reads
    its OWN module-level BENARBEJDE/DEVICES_CSV constants, not anything
    passed in from here. Monkeypatching a second module's globals to make
    this safe is possible but not done here -- same "not yet, unless it
    turns out to be worth it" call the plan already made for suggest_free_ip.py
    and the three check_*.py scripts QuickChecksScreen runs.
  - QuickChecksScreen's three check_*.py subprocess calls -- confirmed
    (reading each script directly, during Stage 5) that none accepts a path
    override; they always run against the REAL repo's committed files, by
    design (they're meant to validate what's actually committed). A test
    can observe that the right three scripts get invoked, but can't safely
    assert on their output without the real repo state as context, so
    that's left to the manual demo each stage already used.
  - The real (non-stubbed) regenerate_all() success path -- confirmed while
    writing this file that generate_network_diagrams.py's own --write CLI
    branch takes no path arguments at all and always operates on the real,
    hardcoded docs/network-diagram/ directory regardless of what sites_csv/
    devices_csv regenerate_all() itself was given. There is no way to
    exercise a genuine regenerate_all() SUCCESS against a fixture without
    that one step also touching the real repo's diagram files -- flagged to
    Robert directly, not worked around quietly here. Only the FAILURE path
    (below) is safe to call for real, since a failing first step never
    reaches that one.
"""
import asyncio
import csv
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import site_device_tui as tui  # noqa: E402
import regenerate_all as ra  # noqa: E402  -- same module object tui.ra already points at


def _run(coro):
    return asyncio.run(coro)


# =============================================================================
# FIXTURE REPO -- a small, self-contained fake estate, never the real
# benarbejde/ files.
# =============================================================================

SITES_HEADER = [
    "Site", "City", "Country", "CountryCode", "Province", "OfficeName",
    "Street", "PostalCode", "Subnet", "Gateway", "DC", "FW", "Landline",
    "Mobile", "Timezone", "AnsibleRegion", "Entity",
]
DEVICES_HEADER = [
    "Site", "Type", "Number", "HostOctet", "OS", "ConnectionType",
    "Managed", "Notes", "SubnetSite", "Legacy", "Migrating", "Planned",
]


def _write_csv(path, header, rows):
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


@pytest.fixture
def fixture_repo(tmp_path, monkeypatch):
    """Builds a minimal fake benarbejde/ + bootstrap/web/proxmox/ tree under
    tmp_path and monkeypatches every module-level global site_device_tui.py
    reads at import time (SITES, ROLE_CODES, KNOWN_*, BENARBEJDE, REPO_ROOT),
    so every test using this fixture runs entirely against it.

    gi.load_address_policy() mutates generate_inventory.py's own
    module-level OFFSETS_SINGLE/ROLE_OFFSETS globals -- genuinely global,
    process-wide state, not scoped per-test by monkeypatch. Safe here only
    because every test in this file that needs it goes through this same
    fixture with the same fixture address_policy.csv content every time;
    nothing in this file ever needs the real one loaded at the same time.
    """
    benarbejde = tmp_path / "benarbejde"
    benarbejde.mkdir()
    (tmp_path / "bootstrap" / "web" / "proxmox").mkdir(parents=True)

    sites_csv = benarbejde / "sites.csv"
    _write_csv(sites_csv, SITES_HEADER, [
        ["TST", "Testville", "Testland", "TL", "", "Test Office",
         "1 Test St", "T1 1AA", "10.99.0.0/24", "10.99.0.253",
         "10.99.0.10", "10.99.0.253", "N/A", "N/A",
         "Europe/London", "test_site", "Test Entity"],
    ])
    role_codes_csv = benarbejde / "role_codes.csv"
    _write_csv(role_codes_csv,
               ["Code", "Name", "Category", "ConnectionMethod", "Emoji", "DNSAlias", "Notes"], [
                   ["RTR", "Router", "Network Infrastructure", "telnet", "", "", ""],
                   ["WKS", "Workstation", "Endpoints", "winrm", "", "", ""],
                   ["PRN", "Printer", "Endpoints", "snmp", "", "", ""],
                   ["DCR", "Domain controller (legacy naming)", "Servers", "ssh", "", "", ""],
               ])
    address_policy_csv = benarbejde / "address_policy.csv"
    _write_csv(address_policy_csv, ["Type", "Octet", "Multi", "Notes"], [
        ["RTR", "1", "no", "Upstream router"],
        ["WKS", "101", "no", "Workstation"],
    ])
    devices_csv = benarbejde / "devices.csv"
    _write_csv(devices_csv, DEVICES_HEADER, [
        ["TST", "RTR", "1", "1", "", "telnet", "", "", "", "no", "", ""],
    ])
    (tmp_path / "bootstrap" / "web" / "proxmox" / "devices.csv").write_bytes(devices_csv.read_bytes())
    (tmp_path / "bootstrap" / "web" / "proxmox" / "sites.csv").write_bytes(sites_csv.read_bytes())

    sites = tui._load_sites(sites_csv)
    role_codes = tui._load_role_codes(role_codes_csv)
    monkeypatch.setattr(tui, "BENARBEJDE", benarbejde)
    monkeypatch.setattr(tui, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(tui, "SITES", sites)
    monkeypatch.setattr(tui, "ROLE_CODES", role_codes)
    monkeypatch.setattr(tui, "KNOWN_COUNTRY_CODES",
                         sorted({s["CountryCode"].upper() for s in sites.values() if s.get("CountryCode")}))
    monkeypatch.setattr(tui, "KNOWN_SUBNETS", {"10.99.0.0/24"})
    monkeypatch.setattr(tui, "KNOWN_TIMEZONES", tui.available_timezones())
    tui.gi.load_address_policy(address_policy_csv)

    return tmp_path


# =============================================================================
# 1. VALIDATOR UNIT TESTS -- no Textual runtime needed.
# =============================================================================

class TestSiteCodeValidator:
    def test_rejects_wrong_length(self, fixture_repo):
        assert not tui.SiteCodeValidator().validate("AB").is_valid
        assert not tui.SiteCodeValidator().validate("ABCD").is_valid

    def test_rejects_lowercase_or_digits(self, fixture_repo):
        assert not tui.SiteCodeValidator().validate("ab1").is_valid

    def test_rejects_existing_site(self, fixture_repo):
        result = tui.SiteCodeValidator().validate("TST")
        assert not result.is_valid
        assert "already exists" in " ".join(result.failure_descriptions)

    def test_rejects_role_code_collision(self, fixture_repo):
        result = tui.SiteCodeValidator().validate("RTR")
        assert not result.is_valid
        assert "collides with role_codes.csv" in " ".join(result.failure_descriptions)

    def test_accepts_new_code(self, fixture_repo):
        assert tui.SiteCodeValidator().validate("NEW").is_valid


class TestRequiredTextValidator:
    def test_rejects_blank(self):
        result = tui.RequiredTextValidator("City").validate("   ")
        assert not result.is_valid
        assert "City is required" in " ".join(result.failure_descriptions)

    def test_accepts_text(self):
        assert tui.RequiredTextValidator("City").validate("Falkirk").is_valid


class TestCountryCodeValidator:
    def test_rejects_unknown(self, fixture_repo):
        assert not tui.CountryCodeValidator().validate("ZZ").is_valid

    def test_accepts_known(self, fixture_repo):
        assert tui.CountryCodeValidator().validate("tl").is_valid  # case-folded


class TestTimezoneValidator:
    def test_rejects_unknown(self, fixture_repo):
        assert not tui.TimezoneValidator().validate("Not/A_Zone").is_valid

    def test_accepts_known(self, fixture_repo):
        assert tui.TimezoneValidator().validate("Europe/Copenhagen").is_valid


class TestSubnetValidator:
    def test_rejects_malformed(self, fixture_repo):
        assert not tui.SubnetValidator().validate("not-a-subnet").is_valid

    def test_rejects_non_strict_host_bits(self, fixture_repo):
        # 192.168.1.5/24 has host bits set -- ip_network(strict=True) must reject it.
        assert not tui.SubnetValidator().validate("192.168.1.5/24").is_valid

    def test_rejects_duplicate_subnet(self, fixture_repo):
        result = tui.SubnetValidator().validate("10.99.0.0/24")
        assert not result.is_valid
        assert "already used by another site" in " ".join(result.failure_descriptions)

    def test_accepts_new_subnet(self, fixture_repo):
        assert tui.SubnetValidator().validate("10.99.9.0/24").is_valid

    def test_exclude_allows_own_unchanged_subnet(self, fixture_repo):
        """Edit Site's own use case: TST keeping its own 10.99.0.0/24 must
        not be flagged as colliding with itself."""
        assert tui.SubnetValidator(exclude="10.99.0.0/24").validate("10.99.0.0/24").is_valid

    def test_exclude_still_rejects_a_different_sites_subnet(self, fixture_repo):
        """Excluding TST's own subnet must not open the door to claiming a
        DIFFERENT site's real subnet instead."""
        result = tui.SubnetValidator(exclude="10.99.0.0/24").validate("10.99.0.0/24")
        assert result.is_valid
        # fixture_repo only has one real subnet (10.99.0.0/24); add a second
        # known one to prove exclude is scoped to just the excluded value.
        tui.KNOWN_SUBNETS.add("10.99.9.0/24")
        try:
            result = tui.SubnetValidator(exclude="10.99.0.0/24").validate("10.99.9.0/24")
            assert not result.is_valid
        finally:
            tui.KNOWN_SUBNETS.discard("10.99.9.0/24")


class TestIPInSubnetValidator:
    def test_rejects_outside_subnet(self, fixture_repo):
        v = tui.IPInSubnetValidator("Gateway", lambda: "10.99.0.0/24")
        result = v.validate("192.168.1.1")
        assert not result.is_valid
        assert "not inside subnet" in " ".join(result.failure_descriptions)

    def test_rejects_when_subnet_field_invalid(self, fixture_repo):
        v = tui.IPInSubnetValidator("Gateway", lambda: "not-a-subnet")
        assert not v.validate("10.99.0.1").is_valid

    def test_accepts_inside_subnet(self, fixture_repo):
        v = tui.IPInSubnetValidator("Gateway", lambda: "10.99.0.0/24")
        assert v.validate("10.99.0.253").is_valid


class TestPhoneValidator:
    def test_rejects_roberts_own_example(self):
        """The exact case that started this whole tool: 555-ABC-DEFG must
        be rejected, with a message naming the actual offending letters."""
        result = tui.PhoneValidator().validate("555-ABC-DEFG")
        assert not result.is_valid
        msg = " ".join(result.failure_descriptions)
        assert "non-digit" in msg
        assert "ABCDEFG" in msg

    def test_accepts_na_sentinel(self):
        assert tui.PhoneValidator().validate("N/A").is_valid
        assert tui.PhoneValidator().validate("n/a").is_valid

    def test_accepts_placeholder_x(self):
        assert tui.PhoneValidator().validate("+44 1224 496 0xxx").is_valid

    def test_rejects_blank(self):
        assert not tui.PhoneValidator().validate("").is_valid

    def test_rejects_too_short(self):
        assert not tui.PhoneValidator().validate("123").is_valid

    def test_accepts_real_looking_number(self):
        assert tui.PhoneValidator().validate("+44 1324 500 0123").is_valid


class TestOptionalSiteCodeValidator:
    def test_accepts_blank(self, fixture_repo):
        assert tui.OptionalSiteCodeValidator().validate("").is_valid

    def test_rejects_unknown_site(self, fixture_repo):
        assert not tui.OptionalSiteCodeValidator().validate("ZZZ").is_valid

    def test_accepts_known_site(self, fixture_repo):
        assert tui.OptionalSiteCodeValidator().validate("tst").is_valid


class TestDeviceOctetValidator:
    def test_rejects_non_digit(self):
        v = tui.DeviceOctetValidator(lambda: "WKS", lambda: {}, lambda: {})
        assert not v.validate("abc").is_valid

    def test_rejects_out_of_range(self):
        v = tui.DeviceOctetValidator(lambda: "WKS", lambda: {}, lambda: {})
        assert not v.validate("999").is_valid

    def test_rejects_occupied(self):
        v = tui.DeviceOctetValidator(lambda: "WKS", lambda: {1: ["TST,RTR,1"]}, lambda: {})
        result = v.validate("1")
        assert not result.is_valid
        assert "already occupied" in " ".join(result.failure_descriptions)

    def test_rejects_reserved_for_different_type(self):
        v = tui.DeviceOctetValidator(lambda: "WKS", lambda: {}, lambda: {1: ["RTR (Upstream router)"]})
        result = v.validate("1")
        assert not result.is_valid
        assert "reserved" in " ".join(result.failure_descriptions)

    def test_allows_own_standard_slot(self):
        """RTR at its own reserved .1 slot must pass -- the reservation is
        FOR this Type, not against it."""
        v = tui.DeviceOctetValidator(lambda: "RTR", lambda: {}, lambda: {1: ["RTR (Upstream router)"]})
        assert v.validate("1").is_valid

    def test_accepts_free_octet(self):
        v = tui.DeviceOctetValidator(lambda: "WKS", lambda: {}, lambda: {})
        assert v.validate("150").is_valid


class TestReplaceCsvRow:
    """_replace_csv_row() -- shared rewrite-in-place helper for Edit Site /
    Edit Device. Unit-tested directly against a tiny ad-hoc CSV, no
    fixture_repo/Textual runtime needed."""

    def _write(self, path, header, rows):
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerow(header)
            w.writerows(rows)

    def test_replaces_the_right_row_only(self, tmp_path):
        path = tmp_path / "data.csv"
        mirror = tmp_path / "mirror.csv"
        self._write(path, ["Key", "Value"], [["a", "1"], ["b", "2"], ["c", "3"]])
        mirror.write_bytes(path.read_bytes())

        tui._replace_csv_row(path, mirror, lambda row: row["Key"] == "b", ["b", "CHANGED"])

        rows = list(csv.DictReader(path.open(newline="", encoding="utf-8")))
        assert [r["Value"] for r in rows] == ["1", "CHANGED", "3"]
        assert mirror.read_bytes() == path.read_bytes()

    def test_output_has_no_crlf(self, tmp_path):
        path = tmp_path / "data.csv"
        mirror = tmp_path / "mirror.csv"
        self._write(path, ["Key", "Value"], [["a", "1"]])
        mirror.write_bytes(path.read_bytes())

        tui._replace_csv_row(path, mirror, lambda row: row["Key"] == "a", ["a", "2"])

        assert b"\r" not in path.read_bytes()

    def test_raises_on_zero_matches(self, tmp_path):
        path = tmp_path / "data.csv"
        mirror = tmp_path / "mirror.csv"
        self._write(path, ["Key", "Value"], [["a", "1"]])
        mirror.write_bytes(path.read_bytes())

        with pytest.raises(ValueError, match="found 0"):
            tui._replace_csv_row(path, mirror, lambda row: row["Key"] == "missing", ["x", "1"])

    def test_raises_on_multiple_matches_without_writing(self, tmp_path):
        path = tmp_path / "data.csv"
        mirror = tmp_path / "mirror.csv"
        self._write(path, ["Key", "Value"], [["a", "1"], ["a", "2"]])
        mirror.write_bytes(path.read_bytes())
        before = path.read_bytes()

        with pytest.raises(ValueError, match="found 2"):
            tui._replace_csv_row(path, mirror, lambda row: row["Key"] == "a", ["a", "X"])
        assert path.read_bytes() == before, "must not write anything on an ambiguous match"


# =============================================================================
# 2. PILOT NAVIGATION TESTS -- no CSV writes.
# =============================================================================

def test_menu_help_about_navigation(fixture_repo):
    async def body():
        app = tui.SiteDeviceTuiApp(None)
        async with app.run_test() as pilot:
            await pilot.press("f1")
            await pilot.pause()
            assert isinstance(app.screen, tui.HelpModal)
            await pilot.click("#help-about")
            await pilot.pause()
            assert isinstance(app.screen, tui.AboutModal)
            await pilot.press("escape")
            await pilot.pause()
            assert isinstance(app.screen, tui.HelpModal)
            await pilot.press("escape")
            await pilot.pause()
            assert isinstance(app.screen, tui.MainMenuScreen)
    _run(body())


def test_add_site_f4_reset_mid_wizard(fixture_repo):
    async def body():
        app = tui.SiteDeviceTuiApp(None)
        async with app.run_test() as pilot:
            await pilot.click("#menu-add-site")
            await pilot.pause()
            for fid, val in {
                "site-code": "NEW", "site-city": "X", "site-country": "X",
                "site-countrycode": "TL", "site-officename": "X",
            }.items():
                app.screen.query_one(f"#{fid}", tui.Input).value = val
            await pilot.pause()
            await pilot.press("f3")
            await pilot.pause()
            assert isinstance(app.screen, tui.SiteAddressScreen)

            await pilot.press("f4")
            await pilot.pause()
            await pilot.press("f4")
            await pilot.pause()
            assert isinstance(app.screen, tui.SiteIdentityScreen)
            assert app.screen.draft.site == ""
    _run(body())


def test_add_device_f4_reset_mid_wizard(fixture_repo):
    async def body():
        app = tui.SiteDeviceTuiApp(None)
        async with app.run_test() as pilot:
            await pilot.click("#menu-add-device")
            await pilot.pause()
            app.screen.query_one("#device-site", tui.Select).value = "TST"
            await pilot.pause()
            await pilot.press("f3")
            await pilot.pause()
            assert isinstance(app.screen, tui.DeviceRoleScreen)

            await pilot.press("f4")
            await pilot.pause()
            await pilot.press("f4")
            await pilot.pause()
            assert isinstance(app.screen, tui.DeviceSiteScreen)
            assert app.screen.draft.site == ""
    _run(body())


def test_quick_checks_screen_f4_reset_after_collapse_does_not_crash(fixture_repo, monkeypatch):
    """Regression test for the live crash found during Stage 6: F4 on a
    screen reached after a stack collapse (STEP_NUM=6, real depth 1) used
    to pop 6 screens off a 1-deep stack and raise ScreenStackError. Covers
    both SiteBoilerplateScreen and QuickChecksScreen's own use of the same
    pop_depth=1 pattern."""
    monkeypatch.setattr(tui, "_run_quick_checks", lambda: [("stub", 0, "ok")])

    async def body():
        app = tui.SiteDeviceTuiApp(None)
        async with app.run_test() as pilot:
            screen = tui.QuickChecksScreen(
                None, tui._new_standalone_quick_checks,
                step_num=6, step_total=6, after_hostname="EXATESTTST001",
            )
            app.push_screen(screen)
            await pilot.pause()
            await pilot.press("f4")
            await pilot.pause()
            await pilot.press("f4")
            await pilot.pause()
            assert isinstance(app.screen, tui.QuickChecksScreen)
            assert len(app.screen_stack) == 3  # Textual's own default screen + MainMenu + this one
    _run(body())


# =============================================================================
# 3. PILOT WRITE-CONTENT TESTS -- real Confirm, real fixture CSVs,
#    regenerate_all() stubbed (see module docstring for exactly why).
# =============================================================================

def _fill(screen, values):
    for fid, val in values.items():
        screen.query_one(f"#{fid}", tui.Input).value = val


async def _walk_to_site_review(pilot, app):
    await pilot.click("#menu-add-site")
    await pilot.pause()
    _fill(app.screen, {
        "site-code": "NEW", "site-city": "Newtown", "site-country": "Testland",
        "site-countrycode": "TL", "site-officename": "Newtown Office",
    })
    await pilot.pause(); await pilot.press("f3"); await pilot.pause()
    _fill(app.screen, {
        "site-street": "2 New St", "site-postalcode": "N1 1AA",
        "site-timezone": "Europe/London", "site-ansibleregion": "test_site",
        "site-entity": "Test Entity",
    })
    await pilot.pause(); await pilot.press("f3"); await pilot.pause()
    _fill(app.screen, {
        "site-subnet": "10.99.5.0/24", "site-gateway": "10.99.5.253",
        "site-dc": "10.99.5.10", "site-fw": "10.99.5.253",
    })
    await pilot.pause(); await pilot.press("f3"); await pilot.pause()
    _fill(app.screen, {"site-landline": "N/A", "site-mobile": "N/A"})
    await pilot.pause(); await pilot.press("f3"); await pilot.pause()
    assert isinstance(app.screen, tui.SiteReviewScreen)


def test_add_site_confirm_writes_correct_row(fixture_repo, monkeypatch):
    calls = []
    monkeypatch.setattr(ra, "regenerate_all", lambda repo_root, devices_csv, sites_csv: (
        calls.append((repo_root, devices_csv, sites_csv)), True)[1])

    async def body():
        app = tui.SiteDeviceTuiApp(None)
        async with app.run_test() as pilot:
            await _walk_to_site_review(pilot, app)
            await pilot.press("f3")  # Confirm -- real write, stubbed regenerate
            await pilot.pause()

    _run(body())

    assert len(calls) == 1
    sites_csv = fixture_repo / "benarbejde" / "sites.csv"
    rows = list(csv.DictReader(sites_csv.open(newline="", encoding="utf-8")))
    new_rows = [r for r in rows if r["Site"] == "NEW"]
    assert len(new_rows) == 1
    assert new_rows[0]["Subnet"] == "10.99.5.0/24"
    assert new_rows[0]["Entity"] == "Test Entity"
    mirror = fixture_repo / "bootstrap" / "web" / "proxmox" / "sites.csv"
    assert mirror.read_bytes() == sites_csv.read_bytes()


def test_add_site_confirm_retry_does_not_double_write(fixture_repo, monkeypatch):
    """First Confirm: regenerate_all() fails -> row written once, error
    shown, stays on Review. Second Confirm: regenerate_all() succeeds ->
    proceeds, but the row must still appear exactly once."""
    results = iter([False, True])
    monkeypatch.setattr(ra, "regenerate_all", lambda *a: next(results))

    async def body():
        app = tui.SiteDeviceTuiApp(None)
        async with app.run_test() as pilot:
            await _walk_to_site_review(pilot, app)
            await pilot.press("f3")
            await pilot.pause()
            assert isinstance(app.screen, tui.SiteReviewScreen)  # stayed -- regen failed

            await pilot.press("f3")
            await pilot.pause()
            assert isinstance(app.screen, tui.SiteBoilerplateScreen)  # proceeded this time

    _run(body())

    sites_csv = fixture_repo / "benarbejde" / "sites.csv"
    rows = list(csv.DictReader(sites_csv.open(newline="", encoding="utf-8")))
    assert len([r for r in rows if r["Site"] == "NEW"]) == 1


async def _walk_to_device_review(pilot, app, *, role="PRN"):
    await pilot.click("#menu-add-device")
    await pilot.pause()
    app.screen.query_one("#device-site", tui.Select).value = "TST"
    await pilot.pause(); await pilot.press("f3"); await pilot.pause()
    app.screen.query_one("#device-role", tui.Select).value = role
    await pilot.pause(); await pilot.press("f3"); await pilot.pause()
    await pilot.press("f3")  # accept suggested octet
    await pilot.pause()
    app.screen.query_one("#device-os", tui.Input).value = "Test Printer"
    await pilot.pause(); await pilot.press("f3"); await pilot.pause()
    assert isinstance(app.screen, tui.DeviceReviewScreen)


def test_add_device_confirm_writes_correct_row(fixture_repo, monkeypatch):
    calls = []
    monkeypatch.setattr(ra, "regenerate_all", lambda repo_root, devices_csv, sites_csv: (
        calls.append((repo_root, devices_csv, sites_csv)), True)[1])

    async def body():
        app = tui.SiteDeviceTuiApp(None)
        async with app.run_test() as pilot:
            await _walk_to_device_review(pilot, app)
            draft = app.screen.draft
            await pilot.press("f3")
            await pilot.pause()
            return draft

    draft = _run(body())

    assert len(calls) == 1
    devices_csv = fixture_repo / "benarbejde" / "devices.csv"
    rows = list(csv.DictReader(devices_csv.open(newline="", encoding="utf-8")))
    new_rows = [r for r in rows if r["Site"] == "TST" and r["Type"] == "PRN"]
    assert len(new_rows) == 1
    assert new_rows[0]["Number"] == "1"  # fixture devices.csv has no existing PRN at TST
    assert new_rows[0]["OS"] == "Test Printer"
    assert draft.hostname() == "EXAPRNTST001"
    mirror = fixture_repo / "bootstrap" / "web" / "proxmox" / "devices.csv"
    assert mirror.read_bytes() == devices_csv.read_bytes()


def test_device_options_empty_sentinel_when_no_devices(fixture_repo):
    screen = tui.DeviceEditPickerScreen(None, lambda: None)
    assert screen._device_options("ZZZ") == [("(no devices at this site)", "")]


def test_device_options_lists_real_devices(fixture_repo):
    screen = tui.DeviceEditPickerScreen(None, lambda: None)
    assert screen._device_options("TST") == [("RTR #1 — EXARTRTST001", "RTR:1")]


async def _walk_to_site_edit(pilot, app, site="TST"):
    await pilot.click("#menu-edit-site")
    await pilot.pause()
    app.screen.query_one("#edit-site-picker", tui.Select).value = site
    await pilot.pause()
    await pilot.press("f3")
    await pilot.pause()
    assert isinstance(app.screen, tui.SiteEditScreen)


def test_edit_site_loads_existing_values_with_identity_read_only(fixture_repo):
    async def body():
        app = tui.SiteDeviceTuiApp(None)
        async with app.run_test() as pilot:
            await _walk_to_site_edit(pilot, app)
            d = app.screen.draft
            assert d.site == "TST" and d.edit_mode is True
            assert d.city == "Testville"
            assert d.subnet == "10.99.0.0/24"
            # Gateway/DC/FW are deliberately set blank at construction and
            # back-filled in on_mount() (see SiteEditScreen's own comment) --
            # confirm the real value actually landed, not left blank.
            assert app.screen.query_one("#esite-gateway", tui.Input).value == "10.99.0.253"
            # No Input exists for the site code -- it's shown as a read-only
            # Static, never an editable field.
            assert len(app.screen.query("#esite-site")) == 0
    _run(body())


def test_edit_site_confirm_rewrites_in_place_without_adding_a_row(fixture_repo, monkeypatch):
    calls = []
    monkeypatch.setattr(ra, "regenerate_all", lambda *a: (calls.append(1), True)[1])

    async def body():
        app = tui.SiteDeviceTuiApp(None)
        async with app.run_test() as pilot:
            await _walk_to_site_edit(pilot, app)
            app.screen.query_one("#esite-city", tui.Input).value = "Testville EDITED"
            await pilot.pause()
            await pilot.press("f3")
            await pilot.pause()

    _run(body())

    assert len(calls) == 1
    sites_csv = fixture_repo / "benarbejde" / "sites.csv"
    rows = list(csv.DictReader(sites_csv.open(newline="", encoding="utf-8")))
    assert len(rows) == 1, "Edit Site must rewrite in place, never append a second row"
    assert rows[0]["City"] == "Testville EDITED"
    assert rows[0]["Subnet"] == "10.99.0.0/24", "unchanged fields must round-trip untouched"
    with sites_csv.open("rb") as f:
        assert b"\r" not in f.read()
    mirror = fixture_repo / "bootstrap" / "web" / "proxmox" / "sites.csv"
    assert mirror.read_bytes() == sites_csv.read_bytes()


def test_edit_site_f4_reset_discards_unsaved_edit(fixture_repo, monkeypatch):
    monkeypatch.setattr(ra, "regenerate_all", lambda *a: True)

    async def body():
        app = tui.SiteDeviceTuiApp(None)
        async with app.run_test() as pilot:
            await _walk_to_site_edit(pilot, app)
            app.screen.query_one("#esite-city", tui.Input).value = "UNSAVED JUNK"
            await pilot.pause()
            await pilot.press("f4")
            await pilot.pause()
            await pilot.press("f4")
            await pilot.pause()
            assert isinstance(app.screen, tui.SiteEditScreen)
            assert app.screen.query_one("#esite-city", tui.Input).value == "Testville"
    _run(body())


async def _walk_to_device_edit(pilot, app, site="TST"):
    await pilot.click("#menu-edit-device")
    await pilot.pause()
    app.screen.query_one("#edit-device-site", tui.Select).value = site
    await pilot.pause()
    await pilot.press("f3")
    await pilot.pause()
    assert isinstance(app.screen, tui.DeviceEditScreen)


def test_edit_device_loads_existing_values_with_identity_read_only(fixture_repo):
    async def body():
        app = tui.SiteDeviceTuiApp(None)
        async with app.run_test() as pilot:
            await _walk_to_device_edit(pilot, app)
            d = app.screen.draft
            assert d.edit_mode is True
            assert (d.site, d.type, d.number) == ("TST", "RTR", 1)
            assert d.host_octet == "1"
            assert d.hostname() == "EXARTRTST001"
            # Identity fields are shown in one read-only Static -- no Input
            # for Site/Type/Number/HostOctet exists on this screen at all.
            for fid in ("edev-site", "edev-type", "edev-number", "edev-hostoctet"):
                assert len(app.screen.query(f"#{fid}")) == 0
    _run(body())


def test_edit_device_confirm_rewrites_in_place_preserving_identity(fixture_repo, monkeypatch):
    calls = []
    monkeypatch.setattr(ra, "regenerate_all", lambda *a: (calls.append(1), True)[1])

    async def body():
        app = tui.SiteDeviceTuiApp(None)
        async with app.run_test() as pilot:
            await _walk_to_device_edit(pilot, app)
            app.screen.query_one("#edev-notes", tui.Input).value = "notes EDITED"
            await pilot.pause()
            await pilot.press("f3")
            await pilot.pause()

    _run(body())

    assert len(calls) == 1
    devices_csv = fixture_repo / "benarbejde" / "devices.csv"
    rows = list(csv.DictReader(devices_csv.open(newline="", encoding="utf-8")))
    assert len(rows) == 1, "Edit Device must rewrite in place, never append a second row"
    assert rows[0]["Notes"] == "notes EDITED"
    assert rows[0]["Site"] == "TST" and rows[0]["Type"] == "RTR" and rows[0]["Number"] == "1"
    assert rows[0]["HostOctet"] == "1", "identity fields must round-trip untouched"
    with devices_csv.open("rb") as f:
        assert b"\r" not in f.read()
    mirror = fixture_repo / "bootstrap" / "web" / "proxmox" / "devices.csv"
    assert mirror.read_bytes() == devices_csv.read_bytes()


def test_edit_device_picker_rejects_blank_pick(fixture_repo, monkeypatch):
    """DeviceEditPickerScreen.commit() must refuse to proceed (and must
    never raise) if the picked site genuinely has zero devices -- exercised
    directly rather than through the UI, since fixture_repo's only site
    always has a device (see test_device_options_empty_sentinel... above
    for the underlying data-level guarantee this depends on)."""
    screen = tui.DeviceEditPickerScreen(None, lambda: None)
    screen._site = "doesn't matter, commit() re-reads the widgets"
    # Simulate the widget state commit() reads without a full Pilot mount:
    # DeviceEditPickerScreen.commit() calls query_one() against two real
    # Selects, so drive it through a real (if minimal) mounted screen.
    async def body():
        app = tui.SiteDeviceTuiApp(None)
        async with app.run_test() as pilot:
            await pilot.click("#menu-edit-device")
            await pilot.pause()
            device_select = app.screen.query_one("#edit-device-pick", tui.Select)
            device_select.set_options([("(no devices at this site)", "")])
            device_select.value = ""
            await pilot.pause()
            error = app.screen.commit()
            assert error is not None
            assert "no devices yet" in error
    _run(body())


def test_add_device_number_increments_for_second_instance(fixture_repo, monkeypatch):
    monkeypatch.setattr(ra, "regenerate_all", lambda *a: True)

    async def body():
        app = tui.SiteDeviceTuiApp(None)
        async with app.run_test() as pilot:
            await _walk_to_device_review(pilot, app)
            await pilot.press("f3")
            await pilot.pause()
            # Second PRN at the same site, fresh wizard from the menu.
            await pilot.press("f2")  # QuickChecksScreen -> back to menu
            await pilot.pause()
            assert isinstance(app.screen, tui.MainMenuScreen)
            await _walk_to_device_review(pilot, app)
            second_draft = app.screen.draft
            await pilot.press("f3")
            await pilot.pause()
            return second_draft

    second_draft = _run(body())
    assert second_draft.number == 2
    assert second_draft.hostname() == "EXAPRNTST002"


# =============================================================================
# 4. regenerate_all() FAILURE-PATH UNIT TEST -- the one real (non-stubbed)
#    call in this file. Safe because a failing first step never reaches
#    generate_network_diagrams.py --write (the step confirmed above to
#    always touch the real repo regardless of path args).
# =============================================================================

def test_regenerate_all_fails_cleanly_without_side_effects(tmp_path):
    sites_csv = tmp_path / "sites.csv"
    sites_csv.write_text(",".join(SITES_HEADER) + "\n", encoding="utf-8")
    devices_csv = tmp_path / "devices.csv"
    devices_csv.write_text(",".join(DEVICES_HEADER) + "\n", encoding="utf-8")
    # Deliberately no address_policy.csv alongside sites_csv -- confirmed
    # directly (while writing this test) that this makes
    # generate_inventory.py's first step fail fast with a clean non-zero
    # exit and no output directory created.

    before = set(tmp_path.rglob("*"))
    ok = ra.regenerate_all(tmp_path, devices_csv, sites_csv)
    after = set(tmp_path.rglob("*"))

    assert ok is False
    assert before == after, "regenerate_all() left stray files behind on a failed first step"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
