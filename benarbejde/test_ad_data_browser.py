#!/usr/bin/env python3
"""
test_ad_data_browser.py -- tests for ad_data_browser.py.

Same two-layer shape as test_site_device_tui.py (its sibling): plain unit
tests for the helpers that don't need a Textual runtime, then Pilot tests
for real navigation/filter/detail behaviour against a small fixture
dataset under tmp_path -- NEVER the real benarbejde/ JSON files. Nothing
in ad_data_browser.py writes to any file, so there is no write-content
layer here the way the sites.csv/devices.csv tool's tests have.

Run: python3 -m pytest benarbejde/test_ad_data_browser.py -v
"""
import asyncio
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ad_data_browser as adb  # noqa: E402


def _run(coro):
    return asyncio.run(coro)


# =============================================================================
# FIXTURE DATA -- a small, self-contained fake AD export, never the real
# benarbejde/ files.
# =============================================================================

@pytest.fixture
def fixture_paths(tmp_path):
    computers = [
        {"Name": "EXARTRTST001", "SamAccountName": "EXARTRTST001$", "Role": "RTR",
         "Site": "TST", "Description": "Test router", "Enabled": True,
         "DNSHostName": "EXARTRTST001.jukebox.internal", "OS": "Debian",
         "OperatingSystemVersion": "12", "IPv4Address": "10.99.0.1",
         "ad_ou": "OU=Network,OU=Devices,OU=Testville,OU=Testland,OU=Sites,DC=jukebox,DC=internal"},
        {"Name": "EXAWKSTST001", "SamAccountName": "EXAWKSTST001$", "Role": "WKS",
         "Site": "TST", "Description": "", "Enabled": False,
         "DNSHostName": "EXAWKSTST001.jukebox.internal", "OS": "Windows 11",
         "OperatingSystemVersion": "23H2", "IPv4Address": "10.99.0.101",
         "ad_ou": "OU=Workstations,OU=Devices,OU=Testville,OU=Testland,OU=Sites,DC=jukebox,DC=internal"},
        {"Name": "EXAWKSOTH001", "SamAccountName": "EXAWKSOTH001$", "Role": "WKS",
         "Site": "OTH", "Description": "", "Enabled": True,
         "DNSHostName": "EXAWKSOTH001.jukebox.internal", "OS": "Windows 11",
         "OperatingSystemVersion": "23H2", "IPv4Address": "10.99.1.101",
         "ad_ou": "OU=Workstations,OU=Devices,OU=Otherville,OU=Testland,OU=Sites,DC=jukebox,DC=internal"},
    ]
    users = [
        {"Name": "Test Person", "SamAccountName": "test.person",
         "UserPrincipalName": "test.person@jukebox.internal",
         "Groups": ["Testers", "Everyone"], "Title": "Tester", "Email": "test.person@jukebox.internal",
         "Country": "UK", "CountryCode": "GB", "Manager": "", "Disabled": False,
         "Locked": False, "MustChangePassword": False, "Department": "QA",
         "Company": "Test Co", "Description": "A fixture user", "telephoneNumber": "",
         "mobile": "", "Street": "", "City": "Testville", "PostalCode": "",
         "physicalDeliveryOfficeName": "", "ad_band_ou_name": "", "ad_band_parent": "",
         "ad_ou": "OU=Testers,OU=Users,OU=Testville,OU=Testland,OU=Sites,DC=jukebox,DC=internal"},
    ]
    groups = [
        {"Name": "Testers", "Description": "Fixture group", "Type": "Security",
         "Scope": "Global", "ManagedBy": "", "Email": "", "Site": "TST"},
    ]
    forest = {
        "_comment": "fixture forest",
        "domain_fqdn": "fixture.internal",
        "netbios_name": "FIXTURE",
        "forest_mode": "WinThreshold",
        "domain_mode": "WinThreshold",
        "hub_sites": ["TST"],
        "cld_site": "TST",
        "dns_forwarders": ["10.99.0.1", "9.9.9.9"],
    }

    paths = {}
    for name, data in [("computers", computers), ("users", users),
                       ("groups", groups), ("forest", forest)]:
        p = tmp_path / f"ad_{name}.json"
        p.write_text(json.dumps(data), encoding="utf-8")
        paths[name] = p
    return paths


# =============================================================================
# 1. PLAIN HELPER UNIT TESTS -- no Textual runtime needed.
# =============================================================================

class TestCellText:
    def test_bool_true_renders_yes(self):
        assert adb._cell_text(True) == "yes"

    def test_bool_false_renders_no(self):
        assert adb._cell_text(False) == "no"

    def test_none_renders_blank(self):
        assert adb._cell_text(None) == ""

    def test_list_joined_with_comma(self):
        assert adb._cell_text(["Testers", "Everyone"]) == "Testers, Everyone"

    def test_plain_string_passthrough(self):
        assert adb._cell_text("hello") == "hello"

    def test_empty_list_renders_blank(self):
        assert adb._cell_text([]) == ""


class TestParseOuPath:
    def test_real_shaped_dn_parses_root_to_leaf(self):
        dn = ("OU=Telephony,OU=Devices,OU=Aberdeen,OU=Scotland,OU=United "
              "Kingdom,OU=Europe,OU=Sites,DC=jukebox,DC=internal")
        assert adb._parse_ou_path(dn) == (
            "jukebox.internal", "Sites", "Europe", "United Kingdom",
            "Scotland", "Aberdeen", "Devices", "Telephony",
        )

    def test_blank_dn_returns_no_ou_sentinel(self):
        assert adb._parse_ou_path("") == adb._NO_OU_PATH
        assert adb._parse_ou_path(None) == adb._NO_OU_PATH
        assert adb._parse_ou_path("   ") == adb._NO_OU_PATH

    def test_domain_components_join_in_natural_fqdn_order(self):
        # DC=jukebox,DC=internal (child-to-parent, standard DN order) must
        # read as "jukebox.internal", matching ad_forest.json's own
        # domain_fqdn convention -- not reversed to "internal.jukebox".
        assert adb._parse_ou_path("DC=jukebox,DC=internal")[0] == "jukebox.internal"

    def test_shallow_dn_still_parses(self):
        assert adb._parse_ou_path("OU=Sites,DC=jukebox,DC=internal") == (
            "jukebox.internal", "Sites",
        )


class TestSearchText:
    def test_concatenates_requested_fields_lowercased(self):
        record = {"Name": "Annie Lennox", "Site": "ABD"}
        text = adb._search_text(record, ["Name", "Site"])
        assert text == "annie lennox abd"

    def test_missing_field_defaults_blank_not_crash(self):
        record = {"Name": "Only Name"}
        text = adb._search_text(record, ["Name", "Email", "ManagedBy"])
        assert text == "only name  "

    def test_list_field_is_searchable(self):
        record = {"Groups": ["Eurythmics", "Vocalists"]}
        text = adb._search_text(record, ["Groups"])
        assert "eurythmics" in text


# =============================================================================
# 2. PILOT TESTS -- real navigation, filter, and detail view against the
# fixture dataset. Nothing here ever writes a file.
# =============================================================================

def test_menu_navigates_to_each_collection(fixture_paths):
    async def body():
        app = adb.AdDataBrowserApp(fixture_paths)
        async with app.run_test() as pilot:
            await pilot.click("#menu-computers")
            await pilot.pause()
            assert isinstance(app.screen, adb.BrowserScreen)
            assert app.screen.collection == "computers"
            await pilot.press("f2")
            await pilot.pause()

            await pilot.click("#menu-users")
            await pilot.pause()
            assert app.screen.collection == "users"
            await pilot.press("f2")
            await pilot.pause()

            await pilot.click("#menu-groups")
            await pilot.pause()
            assert app.screen.collection == "groups"
            await pilot.press("f2")
            await pilot.pause()

            await pilot.click("#menu-forest")
            await pilot.pause()
            assert isinstance(app.screen, adb.ForestScreen)
    _run(body())


def test_browser_shows_every_record_unfiltered(fixture_paths):
    async def body():
        app = adb.AdDataBrowserApp(fixture_paths)
        async with app.run_test() as pilot:
            await pilot.click("#menu-computers")
            await pilot.pause()
            table = app.screen.query_one("#browser-table", adb.DataTable)
            assert table.row_count == 3
            assert "3 record(s)" in str(app.screen.query_one("#browser-count", adb.Static).renderable)
    _run(body())


def test_filter_narrows_by_any_search_field(fixture_paths):
    async def body():
        app = adb.AdDataBrowserApp(fixture_paths)
        async with app.run_test() as pilot:
            await pilot.click("#menu-computers")
            await pilot.pause()
            table = app.screen.query_one("#browser-table", adb.DataTable)
            # Matches via Description, not Name/Role/Site -- proves the
            # filter really searches every configured field, not just the
            # visible columns.
            app.screen.query_one("#browser-filter", adb.Input).value = "test router"
            await pilot.pause()
            assert table.row_count == 1
            assert "1 of 3 shown" in str(app.screen.query_one("#browser-count", adb.Static).renderable)
    _run(body())


def test_filter_is_case_insensitive_and_clears_back_to_full_list(fixture_paths):
    async def body():
        app = adb.AdDataBrowserApp(fixture_paths)
        async with app.run_test() as pilot:
            await pilot.click("#menu-computers")
            await pilot.pause()
            table = app.screen.query_one("#browser-table", adb.DataTable)
            filt = app.screen.query_one("#browser-filter", adb.Input)

            filt.value = "WKS"
            await pilot.pause()
            assert table.row_count == 2

            filt.value = ""
            await pilot.pause()
            assert table.row_count == 3
    _run(body())


def test_filter_matching_nothing_shows_zero_rows(fixture_paths):
    async def body():
        app = adb.AdDataBrowserApp(fixture_paths)
        async with app.run_test() as pilot:
            await pilot.click("#menu-computers")
            await pilot.pause()
            table = app.screen.query_one("#browser-table", adb.DataTable)
            app.screen.query_one("#browser-filter", adb.Input).value = "nonexistent-zzz"
            await pilot.pause()
            assert table.row_count == 0
            assert "0 of 3 shown" in str(app.screen.query_one("#browser-count", adb.Static).renderable)
    _run(body())


def _find_child(node, label):
    for child in node.children:
        if str(child.label) == label:
            return child
    raise KeyError(f"{label!r} not found under {node.label!r}; children: "
                   f"{[str(c.label) for c in node.children]}")


def test_computers_and_users_get_a_tree_pane_groups_does_not(fixture_paths):
    async def body():
        app = adb.AdDataBrowserApp(fixture_paths)
        async with app.run_test() as pilot:
            for menu_id, expect_tree in (
                ("#menu-computers", True), ("#menu-users", True), ("#menu-groups", False),
            ):
                await pilot.click(menu_id)
                await pilot.pause()
                trees = app.screen.query("#browser-tree")
                assert len(trees) == (1 if expect_tree else 0), menu_id
                await pilot.press("f2")
                await pilot.pause()
    _run(body())


def test_tree_builds_real_ou_hierarchy_from_ad_ou(fixture_paths):
    async def body():
        app = adb.AdDataBrowserApp(fixture_paths)
        async with app.run_test() as pilot:
            await pilot.click("#menu-computers")
            await pilot.pause()
            tree = app.screen.query_one("#browser-tree", adb.Tree)

            assert str(tree.root.label) == "jukebox.internal"
            assert tree.root.data == ("jukebox.internal",)

            sites = _find_child(tree.root, "Sites")
            testland = _find_child(sites, "Testland")
            testville = _find_child(testland, "Testville")
            otherville = _find_child(testland, "Otherville")
            devices = _find_child(testville, "Devices")
            network = _find_child(devices, "Network")
            workstations = _find_child(devices, "Workstations")

            assert network.data == ("jukebox.internal", "Sites", "Testland", "Testville", "Devices", "Network")
            # Testville and Otherville both have a "Devices" > "Workstations"
            # branch -- must be two DISTINCT nodes (different full paths),
            # never merged just because the leaf label matches.
            other_devices = _find_child(otherville, "Devices")
            other_workstations = _find_child(other_devices, "Workstations")
            assert workstations.data != other_workstations.data
    _run(body())


def test_selecting_an_ou_node_filters_the_table_by_prefix(fixture_paths):
    async def body():
        app = adb.AdDataBrowserApp(fixture_paths)
        async with app.run_test() as pilot:
            await pilot.click("#menu-computers")
            await pilot.pause()
            tree = app.screen.query_one("#browser-tree", adb.Tree)
            table = app.screen.query_one("#browser-table", adb.DataTable)

            sites = _find_child(tree.root, "Sites")
            testland = _find_child(sites, "Testland")
            testville = _find_child(testland, "Testville")

            # A leaf-level OU (Network) -- exactly the one router.
            devices = _find_child(testville, "Devices")
            network = _find_child(devices, "Network")
            app.screen.on_tree_node_selected(adb.Tree.NodeSelected(network))
            await pilot.pause()
            assert table.row_count == 1
            assert table.get_row_at(0)[0] == "EXARTRTST001"

            # A higher, aggregating OU (Testville) -- both of its devices
            # (router + workstation), never Otherville's workstation.
            app.screen.on_tree_node_selected(adb.Tree.NodeSelected(testville))
            await pilot.pause()
            assert table.row_count == 2
            names = {table.get_row_at(i)[0] for i in range(table.row_count)}
            assert names == {"EXARTRTST001", "EXAWKSTST001"}

            # The domain root -- everything, same as no OU selected at all.
            app.screen.on_tree_node_selected(adb.Tree.NodeSelected(tree.root))
            await pilot.pause()
            assert table.row_count == 3
    _run(body())


def test_ou_selection_combines_with_text_filter(fixture_paths):
    async def body():
        app = adb.AdDataBrowserApp(fixture_paths)
        async with app.run_test() as pilot:
            await pilot.click("#menu-computers")
            await pilot.pause()
            tree = app.screen.query_one("#browser-tree", adb.Tree)
            table = app.screen.query_one("#browser-table", adb.DataTable)

            sites = _find_child(tree.root, "Sites")
            testland = _find_child(sites, "Testland")
            testville = _find_child(testland, "Testville")
            app.screen.on_tree_node_selected(adb.Tree.NodeSelected(testville))
            await pilot.pause()
            assert table.row_count == 2

            # Narrow further with the text filter, still scoped to Testville
            # -- must not reach back into Otherville's matching workstation.
            app.screen.query_one("#browser-filter", adb.Input).value = "WKS"
            await pilot.pause()
            assert table.row_count == 1
            assert table.get_row_at(0)[0] == "EXAWKSTST001"

            count_text = str(app.screen.query_one("#browser-count", adb.Static).renderable)
            assert "OU: Sites > Testland > Testville" in count_text
    _run(body())


def test_selecting_a_row_shows_every_field_of_that_record(fixture_paths):
    async def body():
        app = adb.AdDataBrowserApp(fixture_paths)
        async with app.run_test() as pilot:
            await pilot.click("#menu-users")
            await pilot.pause()
            table = app.screen.query_one("#browser-table", adb.DataTable)
            table.focus()
            table.cursor_coordinate = (0, 0)
            await pilot.pause()
            await pilot.press("enter")
            await pilot.pause()
            assert isinstance(app.screen, adb.DetailScreen)

            rows = app.screen.query("#detail-body .detail-row")
            keys = [str(r.query_one(".detail-key", adb.Static).renderable) for r in rows]
            assert "Name:" in keys
            assert "SamAccountName:" in keys
            # Every one of the fixture user's real fields is shown, not
            # just the 6 columns visible in the table.
            assert len(rows) == 24

            name_row = [r for r in rows if str(r.query_one(".detail-key", adb.Static).renderable) == "Name:"][0]
            assert str(name_row.query_one(".detail-value", adb.Static).renderable) == "Test Person"
    _run(body())


def test_detail_renders_list_field_joined(fixture_paths):
    async def body():
        app = adb.AdDataBrowserApp(fixture_paths)
        async with app.run_test() as pilot:
            await pilot.click("#menu-users")
            await pilot.pause()
            table = app.screen.query_one("#browser-table", adb.DataTable)
            table.focus()
            table.cursor_coordinate = (0, 0)
            await pilot.pause()
            await pilot.press("enter")
            await pilot.pause()

            rows = app.screen.query("#detail-body .detail-row")
            groups_row = [
                r for r in rows
                if str(r.query_one(".detail-key", adb.Static).renderable) == "Groups:"
            ][0]
            assert str(groups_row.query_one(".detail-value", adb.Static).renderable) == "Testers, Everyone"
    _run(body())


def test_detail_blank_field_shown_as_blank_placeholder(fixture_paths):
    async def body():
        app = adb.AdDataBrowserApp(fixture_paths)
        async with app.run_test() as pilot:
            await pilot.click("#menu-groups")
            await pilot.pause()
            table = app.screen.query_one("#browser-table", adb.DataTable)
            table.focus()
            table.cursor_coordinate = (0, 0)
            await pilot.pause()
            await pilot.press("enter")
            await pilot.pause()

            rows = app.screen.query("#detail-body .detail-row")
            managedby_row = [
                r for r in rows
                if str(r.query_one(".detail-key", adb.Static).renderable) == "ManagedBy:"
            ][0]
            assert str(managedby_row.query_one(".detail-value", adb.Static).renderable) == "(blank)"
    _run(body())


def test_back_from_detail_returns_to_browser_not_menu(fixture_paths):
    async def body():
        app = adb.AdDataBrowserApp(fixture_paths)
        async with app.run_test() as pilot:
            await pilot.click("#menu-computers")
            await pilot.pause()
            table = app.screen.query_one("#browser-table", adb.DataTable)
            table.focus()
            table.cursor_coordinate = (0, 0)
            await pilot.pause()
            await pilot.press("enter")
            await pilot.pause()
            assert isinstance(app.screen, adb.DetailScreen)

            await pilot.press("f2")
            await pilot.pause()
            assert isinstance(app.screen, adb.BrowserScreen)

            await pilot.press("f2")
            await pilot.pause()
            assert isinstance(app.screen, adb.MainMenuScreen)
    _run(body())


def test_forest_screen_shows_every_top_level_field(fixture_paths):
    async def body():
        app = adb.AdDataBrowserApp(fixture_paths)
        async with app.run_test() as pilot:
            await pilot.click("#menu-forest")
            await pilot.pause()
            rows = app.screen.query("#detail-body .detail-row")
            keys = [str(r.query_one(".detail-key", adb.Static).renderable) for r in rows]
            assert "domain_fqdn:" in keys
            assert "hub_sites:" in keys

            hub_row = [r for r in rows if str(r.query_one(".detail-key", adb.Static).renderable) == "hub_sites:"][0]
            assert str(hub_row.query_one(".detail-value", adb.Static).renderable) == "TST"
    _run(body())


def test_data_loaded_lazily_per_collection(fixture_paths, monkeypatch):
    """Visiting only Computers must never touch ad_users.json/ad_groups.json
    at all -- confirms data_for()'s own caching is genuinely per-collection,
    not an eager load-everything-at-startup."""
    original_load = adb._load_json_list
    loaded = []

    def tracking_load(path):
        loaded.append(Path(path).name)
        return original_load(path)

    monkeypatch.setattr(adb, "_load_json_list", tracking_load)

    async def body():
        app = adb.AdDataBrowserApp(fixture_paths)
        async with app.run_test() as pilot:
            await pilot.click("#menu-computers")
            await pilot.pause()
    _run(body())

    assert loaded == ["ad_computers.json"]


def test_never_opens_any_file_for_writing(fixture_paths, monkeypatch):
    """Read-only means read-only -- fail loudly if ad_data_browser.py ever
    tries to open a file in a write mode anywhere in a full click-through."""
    import builtins
    real_open = builtins.open

    def guarded_open(file, mode="r", *args, **kwargs):
        if any(c in mode for c in ("w", "a", "x", "+")):
            raise AssertionError(f"ad_data_browser.py opened {file!r} in write mode {mode!r}")
        return real_open(file, mode, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", guarded_open)

    async def body():
        app = adb.AdDataBrowserApp(fixture_paths)
        async with app.run_test() as pilot:
            for menu_id in ("#menu-computers", "#menu-users", "#menu-groups"):
                await pilot.click(menu_id)
                await pilot.pause()
                table = app.screen.query_one("#browser-table", adb.DataTable)
                table.focus()
                table.cursor_coordinate = (0, 0)
                await pilot.pause()
                await pilot.press("enter")
                await pilot.pause()
                await pilot.press("f2")
                await pilot.pause()
                await pilot.press("f2")
                await pilot.pause()
            await pilot.click("#menu-forest")
            await pilot.pause()
    _run(body())


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
