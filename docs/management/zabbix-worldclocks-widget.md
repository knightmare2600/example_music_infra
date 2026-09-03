# Zabbix "World Clocks" dashboard widget

A native Zabbix 7.0 custom dashboard widget module showing a single horizontal row of live
clocks. Built and verified against the real `zabbix-frontend-php_7.0.30-1+debian13` package
downloaded directly from `repo.zabbix.com` — every manifest field, PHP class/namespace, and
JavaScript lifecycle method below was checked against Zabbix's own shipped `widgets/clock` and
`widgets/url` modules inside that package, not invented from general web-development habits.

Installable bundle: [`zabbix-worldclocks-widget.zip`](zabbix-worldclocks-widget.zip) (same
contents as the code blocks below, already arranged as `worldclocks/...`).

**Not yet live-tested** — built and packaged 2026-09-02/03, verified only by source inspection
against the real Zabbix 7.0 package. First live install/test is planned for this evening.

## Clocks shown

| Order | Label   | City         | IANA time zone          |
|-------|---------|--------------|--------------------------|
| 1     | PDT     | Los Angeles  | `America/Los_Angeles`   |
| 2     | EDT     | New York     | `America/New_York`      |
| 3     | BST/GMT | London       | `Europe/London`         |
| 4     | CET     | Copenhagen   | `Europe/Copenhagen`     |
| 5     | AET     | Sydney       | `Australia/Sydney`      |
| 6     | AET     | Melbourne    | `Australia/Melbourne`   |
| 7     | NZT     | Auckland     | `Pacific/Auckland`      |

Labels are fixed literal text (matching the original brief for the first five), not dynamically
recomputed — only the **time itself** shifts automatically with DST, via the IANA identifier.
`AET`/`NZT` for Melbourne and Auckland follow the same generic-family-abbreviation convention
already set by `AET` for Sydney (rather than the more precise but changing `AEDT`/`AEST`/
`NZDT`/`NZST`) — flagging this choice explicitly since it wasn't specified; trivial to change in
`actions/WidgetView.php` if a different label is wanted.

## Timezone coverage audit against `benarbejde/sites.csv`

Checked the real source of truth (`benarbejde/sites.csv`, 54 site rows) for every distinct
`Timezone` value actually in use, and cross-checked each one against the real installed IANA
tzdata (`/usr/share/zoneinfo`, via Python's `zoneinfo` module) rather than assuming any of them
are valid or already covered.

**19 distinct timezone values in `sites.csv`.** After adding Melbourne and Auckland, this
widget covers 5 of them (`America/Los_Angeles`, `America/New_York`, `Europe/London`,
`Europe/Copenhagen`, `Australia/Sydney` — `Australia/Melbourne` and `Pacific/Auckland` are the
same zones as Sydney/Auckland already listed above).

### No MDT (Mountain Time) sites

Checked every `Timezone` value in `sites.csv` for `America/Denver`, `America/Boise`,
`America/Edmonton`, `America/Phoenix`, or any other Mountain-time zone: **none present.** No
site in `sites.csv` is on Mountain Time.

### Sites on timezones this widget does NOT cover

| Timezone              | Sites (Site code — City)                                              |
|------------------------|-------------------------------------------------------------------------|
| `America/Chicago`      | ATL — Atlanta, CHI — Chicago                                            |
| `America/Toronto`      | BRK — Brockville, TOR — Toronto                                         |
| `America/Montreal`     | MTL — Montreal *(see note below)*                                       |
| `Asia/Beirut`          | BRT — Beirut                                                             |
| `Europe/Amsterdam`     | AMS — Amsterdam                                                          |
| `Europe/Berlin`        | BER — Berlin, BON — Bonn, BRD — West Berlin (legacy alias for BER), DRS — Dresden, DUS — Dusseldorf, MUN — Munich |
| `Europe/Oslo`          | OSL — Oslo                                                               |
| `Europe/Rome`          | MIL — Milan                                                              |
| `Europe/Stockholm`     | GOT — Gothenburg                                                         |
| `Europe/Vienna`        | VIE — Vienna                                                             |
| `UTC`                  | CLD — CloudSite, VRK — VRack *(both infra-only "cloud sites", not staffed offices)* |
| `Europe/Aarhus`        | AAR — Aarhus *(see bug flagged below — not a real zone at all)*         |

None of these were added to the widget — they weren't requested, and 12 more clocks would no
longer fit the "single horizontal row" brief. Listed here purely as the factual answer to "do we
have any cities on timezones not covered."

**Note on `America/Montreal` (MTL):** confirmed via `readlink` on the real installed tzdata that
this is a genuine, still-valid IANA zone — a backward-compatibility symlink to
`America/Toronto`, same offset, same DST schedule. Not a bug, just worth knowing it's an alias
if anyone goes looking for it in a zone picker and doesn't find it listed as a distinct primary
entry in some tools.

### Real data bug found: `Europe/Aarhus` (AAR row) is not a valid IANA timezone

Checked directly against the installed system tzdata (`python3 -c "import zoneinfo;
zoneinfo.ZoneInfo('Europe/Aarhus')"`) — this raises `No time zone found with key Europe/Aarhus`.
It is not a real IANA identifier; Denmark has exactly one IANA zone, `Europe/Copenhagen`, which
every other Danish site in `sites.csv` (CPH, FAX, FRD, FRE, KGE, KOR, NYB, ODE) already
correctly uses. `Europe/Aarhus` in the AAR row is genuinely broken — a call to `Intl.DateTimeFormat`
or PHP's `DateTimeZone` with this string throws in both languages, not just an edge case.

**Not fixed here** — `sites.csv` is the estate's single source of truth and changing it wasn't
part of this task; flagging it clearly rather than silently working around it or silently
leaving it unmentioned. Worth a follow-up correcting the AAR row's `Timezone` column to
`Europe/Copenhagen` and re-running the CSV → inventory regeneration pipeline
(`docs/adding-a-new-device.md`) to propagate the fix.

## Directory tree

```
worldclocks/
├── manifest.json
├── Widget.php
├── actions/
│   └── WidgetView.php
├── includes/
│   └── WidgetForm.php
├── views/
│   ├── widget.view.php
│   └── widget.edit.php
└── assets/
    ├── js/
    │   └── class.widget.js
    └── css/
        └── widget.css
```

## Files

### `manifest.json`

```json
{
	"manifest_version": 2.0,
	"id": "worldclocks",
	"type": "widget",
	"name": "World Clocks",
	"namespace": "Worldclocks",
	"version": "1.0",
	"author": "Example Music Limited",
	"description": "Displays a row of live clocks for Los Angeles, New York, London, Copenhagen, Sydney, Melbourne and Auckland.",
	"url": "",
	"widget": {
		"js_class": "CWidgetWorldClocks",
		"size": {
			"width": 36,
			"height": 3
		},
		"refresh_rate": 0
	},
	"actions": {
		"widget.worldclocks.view": {
			"class": "WidgetView"
		}
	},
	"assets": {
		"js": ["class.widget.js"],
		"css": ["widget.css"]
	}
}
```

`refresh_rate: 0` is deliberate, matching Zabbix's own native URL widget's choice — nothing here
ever needs a server round-trip after the first load, since the clocks tick client-side every
second.

### `Widget.php`

```php
<?php declare(strict_types = 0);
/**
 * World Clocks widget module.
 */

namespace Widgets\Worldclocks;

use Zabbix\Core\CWidget;

class Widget extends CWidget {

	public function getDefaultName(): string {
		return _('World Clocks');
	}
}
```

### `includes/WidgetForm.php`

```php
<?php declare(strict_types = 0);
/**
 * World Clocks widget form.
 *
 * The seven clocks (time zone, label, city) are fixed in WidgetView.php rather than
 * user-configurable, so this form intentionally adds no fields of its own. Zabbix's core
 * CWidget::getForm() still adds the standard "Refresh interval" field automatically.
 */

namespace Widgets\Worldclocks\Includes;

use Zabbix\Widgets\CWidgetForm;

class WidgetForm extends CWidgetForm {

	public function addFields(): self {
		return $this;
	}
}
```

Confirmed against the real `CWidget::getForm()`: it always injects the "Refresh interval" field
itself before calling `addFields()`, so an empty form here is genuinely valid, not a shortcut.

### `actions/WidgetView.php`

```php
<?php declare(strict_types = 0);
/**
 * World Clocks widget view action.
 *
 * The clock list (IANA time zone, fixed label, city) is the single source of truth for the
 * widget's content -- defined once here in PHP and rendered into data-tz attributes; the
 * front-end JavaScript reads those attributes rather than duplicating this list.
 */

namespace Widgets\Worldclocks\Actions;

use CControllerDashboardWidgetView,
	CControllerResponseData;

class WidgetView extends CControllerDashboardWidgetView {

	protected function doAction(): void {
		$this->setResponse(new CControllerResponseData([
			'name' => $this->getInput('name', $this->widget->getDefaultName()),
			'clocks' => [
				['tz' => 'America/Los_Angeles', 'label' => 'PDT',     'city' => 'Los Angeles'],
				['tz' => 'America/New_York',    'label' => 'EDT',     'city' => 'New York'],
				['tz' => 'Europe/London',       'label' => 'BST/GMT', 'city' => 'London'],
				['tz' => 'Europe/Copenhagen',   'label' => 'CET',     'city' => 'Copenhagen'],
				['tz' => 'Australia/Sydney',    'label' => 'AET',     'city' => 'Sydney'],
				['tz' => 'Australia/Melbourne', 'label' => 'AET',     'city' => 'Melbourne'],
				['tz' => 'Pacific/Auckland',    'label' => 'NZT',     'city' => 'Auckland']
			],
			'user' => [
				'debug_mode' => $this->getDebugMode()
			]
		]));
	}
}
```

Adding or removing a clock only ever requires editing this one array — nothing else in the
module needs to change (the view renders whatever's in `$data['clocks']`, and the JS is fully
generic, driven entirely by each cell's own `data-tz` attribute).

### `views/widget.view.php`

```php
<?php declare(strict_types = 0);
/**
 * World Clocks widget view.
 *
 * Renders one .worldclocks-cell per configured clock. The time text is filled in and ticked
 * every second entirely client-side (assets/js/class.widget.js), so the "--:--:--" placeholder
 * here is only ever visible for the instant before JavaScript first runs.
 *
 * @var CView $this
 * @var array $data
 */

$row = (new CDiv())->addClass('worldclocks-row');

foreach ($data['clocks'] as $clock) {
	$cell = (new CDiv())
		->addClass('worldclocks-cell')
		->setAttribute('data-tz', $clock['tz']);

	$cell->addItem((new CDiv($clock['label']))->addClass('worldclocks-label'));
	$cell->addItem((new CDiv('--:--:--'))->addClass('worldclocks-time'));
	$cell->addItem((new CDiv($clock['city']))->addClass('worldclocks-city'));

	$row->addItem($cell);
}

(new CWidgetView($data))
	->addItem($row)
	->show();
```

### `views/widget.edit.php`

```php
<?php declare(strict_types = 0);
/**
 * World Clocks widget edit form view.
 *
 * No custom fields -- the clocks are fixed (see actions/WidgetView.php). CWidgetFormView still
 * renders the standard "Refresh interval" field that Zabbix's core adds automatically to every
 * widget's form.
 *
 * @var CView $this
 * @var array $data
 */

(new CWidgetFormView($data))
	->show();
```

### `assets/js/class.widget.js`

```javascript
/**
 * World Clocks widget front-end class.
 *
 * Lifecycle methods (onInitialize, processUpdateResponse, onDeactivate) match the pattern used
 * by Zabbix's own native Clock widget (widgets/clock/assets/js/class.widget.js): the server
 * renders the clock cells once (see views/widget.view.php), then this class finds them via
 * this._target and ticks their displayed time every second entirely client-side using
 * Intl.DateTimeFormat against each cell's data-tz attribute -- no further server round trips.
 */
class CWidgetWorldClocks extends CWidget {

	static UPDATE_INTERVAL_MS = 1000;

	onInitialize() {
		this._interval_id = null;
		this._formatters = new Map();
	}

	onDeactivate() {
		this._stopClock();
	}

	processUpdateResponse(response) {
		super.processUpdateResponse(response);

		this._stopClock();
		this._startClock();
	}

	_startClock() {
		this._tick();
		this._interval_id = setInterval(() => this._tick(), CWidgetWorldClocks.UPDATE_INTERVAL_MS);
	}

	_stopClock() {
		if (this._interval_id !== null) {
			clearInterval(this._interval_id);
			this._interval_id = null;
		}
	}

	/**
	 * One Intl.DateTimeFormat instance per time zone, reused across ticks rather than
	 * reconstructed every second.
	 *
	 * @param {string} time_zone  IANA time zone identifier, e.g. "Europe/London".
	 *
	 * @returns {Intl.DateTimeFormat}
	 */
	_getFormatter(time_zone) {
		if (!this._formatters.has(time_zone)) {
			this._formatters.set(time_zone, new Intl.DateTimeFormat('en-GB', {
				timeZone: time_zone,
				hourCycle: 'h23',
				hour: '2-digit',
				minute: '2-digit',
				second: '2-digit'
			}));
		}

		return this._formatters.get(time_zone);
	}

	/**
	 * Builds a deterministic "HH:MM:SS" string for the given time zone, independent of the
	 * browser's own locale punctuation/ordering -- formatToParts() is used (rather than trusting
	 * the formatter's own formatted string) specifically so the separator and field order stay
	 * fixed regardless of which locale the browser reports.
	 *
	 * @param {string} time_zone
	 * @param {Date}   now
	 *
	 * @returns {string}
	 */
	_formatTime(time_zone, now) {
		const parts = this._getFormatter(time_zone).formatToParts(now);
		const get = type => parts.find(part => part.type === type)?.value ?? '--';

		return `${get('hour')}:${get('minute')}:${get('second')}`;
	}

	_tick() {
		const now = new Date();

		for (const cell of this._target.querySelectorAll('.worldclocks-cell')) {
			const time_zone = cell.dataset.tz;
			const time_element = cell.querySelector('.worldclocks-time');

			if (time_zone === undefined || time_element === null) {
				continue;
			}

			try {
				time_element.textContent = this._formatTime(time_zone, now);
			}
			catch (error) {
				// Invalid/unsupported IANA time zone identifier -- leave the placeholder in place.
				time_element.textContent = '--:--:--';
			}
		}
	}
}
```

### `assets/css/widget.css`

```css
/**
 * World Clocks widget styling.
 *
 * Deliberately does not set `color` or `background-color` anywhere -- Zabbix's compiled
 * per-theme stylesheets (blue-theme.css / dark-theme.css / hc-light.css / hc-dark.css) set text
 * colour once at the page root and the dashboard widget body (.dashboard-grid-widget-body) is a
 * plain `display: contents` wrapper with no colour of its own, so leaving colour unset here
 * means every element simply inherits whatever the active theme already has, automatically,
 * without needing per-theme overrides or invented CSS variables that Zabbix does not actually
 * expose for third-party module use.
 *
 * Responsiveness is pure CSS (container queries against the widget's own box, not the viewport)
 * -- no JavaScript resize handling is needed.
 */

.worldclocks-row {
	container-type: inline-size;
	display: flex;
	flex-wrap: wrap;
	align-items: stretch;
	justify-content: space-evenly;
	width: 100%;
	height: 100%;
	padding: 10px;
	box-sizing: border-box;
	gap: 8px 4px;
}

.worldclocks-cell {
	display: flex;
	flex-direction: column;
	align-items: center;
	justify-content: center;
	flex: 1 1 100px;
	min-width: 90px;
	text-align: center;
}

.worldclocks-label {
	font-size: 0.85em;
	font-weight: bold;
	text-transform: uppercase;
	letter-spacing: 0.05em;
	opacity: 0.75;
	white-space: nowrap;
}

.worldclocks-time {
	font-size: 1.6em;
	font-weight: bold;
	line-height: 1.2;
	font-variant-numeric: tabular-nums;
	white-space: nowrap;
}

.worldclocks-city {
	font-size: 0.85em;
	opacity: 0.65;
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
	max-width: 100%;
}

/* Narrower widget: seven columns get tight, shrink the clock face before anything wraps. */
@container (max-width: 620px) {
	.worldclocks-time {
		font-size: 1.25em;
	}
}

/* Narrower still: labels/city no longer need full-size text either. */
@container (max-width: 460px) {
	.worldclocks-label,
	.worldclocks-city {
		font-size: 0.75em;
	}

	.worldclocks-time {
		font-size: 1.05em;
	}
}

/* Too narrow for seven in a row: let cells wrap onto further lines, still centred and readable. */
@container (max-width: 320px) {
	.worldclocks-cell {
		flex: 1 1 45%;
	}
}
```

## Installation

Real, verified install location: **`/usr/share/zabbix/modules/worldclocks/`** — confirmed
directly from `zabbix-frontend-php`'s own `app/controllers/CControllerModuleScan.php`, which
scans both `widgets/` (Zabbix's own bundled widgets, owned by the package, overwritten on every
`apt upgrade`) and `modules/` (ships empty in the package, the real intended drop point for
third-party modules). This is **not** `widgets/` — that would work until the next `apt upgrade`
of `zabbix-frontend-php` silently wipes it.

```bash
# Unzip directly into modules/ -- the zip already contains the worldclocks/ folder itself
sudo unzip zabbix-worldclocks-widget.zip -d /usr/share/zabbix/modules/
```

Or by hand, file by file, using the code blocks above with `vim`:

```bash
sudo mkdir -p /usr/share/zabbix/modules/worldclocks/{actions,includes,views,assets/js,assets/css}
sudo vim /usr/share/zabbix/modules/worldclocks/manifest.json
sudo vim /usr/share/zabbix/modules/worldclocks/Widget.php
sudo vim /usr/share/zabbix/modules/worldclocks/actions/WidgetView.php
sudo vim /usr/share/zabbix/modules/worldclocks/includes/WidgetForm.php
sudo vim /usr/share/zabbix/modules/worldclocks/views/widget.view.php
sudo vim /usr/share/zabbix/modules/worldclocks/views/widget.edit.php
sudo vim /usr/share/zabbix/modules/worldclocks/assets/js/class.widget.js
sudo vim /usr/share/zabbix/modules/worldclocks/assets/css/widget.css
```

Ownership and permissions — matching exactly what the real `zabbix-frontend-php` package itself
uses for its own code files (checked directly inside the `.deb`: `root:root`, dirs `755`, files
`644` — Apache reads via world-read, no `www-data` ownership needed for source files, unlike the
DB-credential-bearing `zabbix.conf.php`):

```bash
sudo chown -R root:root /usr/share/zabbix/modules/worldclocks
sudo find /usr/share/zabbix/modules/worldclocks -type d -exec chmod 755 {} \;
sudo find /usr/share/zabbix/modules/worldclocks -type f -exec chmod 644 {} \;
```

## Enabling the widget

1. Log into the Zabbix web UI as Admin.
2. **Administration → General → Modules**.
3. Click **Scan directory** (top right) — this re-scans both `widgets/` and `modules/` and will
   list "World Clocks".
4. Click on it, set **Status** to **Enabled**, click **Update**.

## Adding it to a dashboard

1. Open or create a dashboard, click **Edit dashboard**.
2. **Add widget** (or click an empty cell).
3. **Type**: select **World Clocks**.
4. It has no configurable fields beyond the standard **Refresh interval** (harmless here — leave
   at Default; the clocks tick themselves regardless).
5. **Add**, then **Save changes**.

## Expected appearance

```
   PDT          EDT        BST/GMT       CET          AET          AET          NZT
 11:32:41     14:32:41     19:32:41    20:32:41     05:32:41     05:32:41     07:32:41
Los Angeles   New York      London     Copenhagen    Sydney      Melbourne    Auckland
```

Text colour follows whichever Zabbix theme is active (light/dark/high-contrast) automatically,
since none is hardcoded. Narrowing the widget shrinks the clock font progressively, then wraps
onto further rows if it gets too tight for seven columns.

## Troubleshooting

**Module doesn't appear after "Scan directory":**
- Check the JSON is valid: `sudo python3 -m json.tool /usr/share/zabbix/modules/worldclocks/manifest.json` (fails loudly on syntax errors).
- Confirm the path is exactly `modules/worldclocks/manifest.json` — `widgets/` is the wrong
  location.
- Confirm ownership/permissions as above — if Apache's PHP process can't read the files, the
  manifest silently fails to load (no error shown, it just won't appear in the list).

**Widget shows a blank/broken tile on the dashboard:**
- Check Apache's error log for a PHP fatal: `sudo tail -50 /var/log/apache2/error.log`
- Common cause: a typo in a `namespace` line — every namespace in the PHP files must read
  exactly `Widgets\Worldclocks...` (case matters, must match `ucfirst("worldclocks")` =
  `Worldclocks`).
- Turn on Zabbix's own frontend debug mode (**Administration → General → GUI → Debug mode**, or
  per-user in profile) to get a debug panel with PHP errors directly in the dashboard widget.

**Clocks show `--:--:--` and never update:**
- Open browser DevTools → Console on the dashboard page — a JS error there will show directly.
- Confirm the JS file is actually being served: DevTools → Network tab, look for
  `modules/worldclocks/assets/js/class.widget.js` — if it's 404, re-check the file was copied to
  the right path and is readable.
- If it loads but nothing updates, check `manifest.json`'s `"js_class"` value matches the JS
  file's `class CWidgetWorldClocks` name exactly (case-sensitive).

**CSS not applying / clocks look unstyled:**
- Confirm `assets/css/widget.css` is listed under `"assets": {"css": [...]}` in `manifest.json`
  (this key is genuinely used by Zabbix's core page header to inject a `<link>` tag — confirmed
  directly in `app/partials/layout.htmlpage.header.php`).
- Check Network tab for a 404 on `modules/worldclocks/assets/css/widget.css`.

**Frontend/browser cache:**
- After any edit to these files, Zabbix's frontend does **not** need a service restart (PHP
  files are interpreted per-request) — but your **browser** will cache the JS/CSS files
  aggressively. Hard-refresh (Ctrl+Shift+R / Cmd+Shift+R) or open DevTools → Network → check
  "Disable cache" while iterating.
- There is no separate PHP opcode/frontend cache to clear for module changes on a standard
  install — if changes still don't show after a hard refresh, check `php.ini`'s
  `opcache.enable` — if opcache is on with a long `opcache.revalidate_freq`,
  `sudo systemctl reload apache2` forces a recheck (this box uses mod_php/Apache directly, not
  PHP-FPM).
