# Zabbix "World Clocks" dashboard widget

A native Zabbix 7.0 custom dashboard widget module showing a configurable row of live clocks —
digital or analog, up to 8 of them, each independently set to any real IANA time zone, with
selectable foreground/background colours. Built and verified against the real
`zabbix-frontend-php_7.0.30-1+debian13` package downloaded directly from `repo.zabbix.com` —
every manifest field, PHP class/namespace, and JavaScript lifecycle method below was checked
against Zabbix's own shipped `widgets/clock`, `widgets/url`, and `widgets/tophosts` modules
inside that package, not invented from general web-development habits.

Installable bundle: [`zabbix-worldclocks-widget.zip`](zabbix-worldclocks-widget.zip) (same
contents as the code blocks below, already arranged as `worldclocks/...`).

**v1.1 — real bug found and fixed on first live test, 2026-09-03:** v1.0 used PHP namespace
`Widgets\Worldclocks\...`, copied from Zabbix's own bundled `widgets/clock` module without
adjusting it for this module's actual install location (`modules/worldclocks/`, correctly
*not* `widgets/`). `CModuleManager.php` derives the required namespace prefix from whichever
top-level directory the module sits in — `Modules\Worldclocks\...` for `modules/`, not
`Widgets\Worldclocks\...`. The mismatch produced `Wrong Widget.php class name for module
located at modules/worldclocks.` — and because Zabbix's own `initModules()` has a genuine bug
(a bare `return;` inside a plain `foreach` loop, confirmed by reading the real source: any
module with a class-name mismatch aborts loading of *every module after it*, not just the
broken one), this took down every dashboard for every user, including Admin, not just this
widget. **If you hit this: `sudo rm -rf /usr/share/zabbix/modules/worldclocks`, then
Administration → General → Modules → Scan directory, and every dashboard recovers
immediately** — do this before anything else, on any version.

**v2.0 — configurable, 2026-09-03:** v1.x hardcoded the seven clocks directly in
`actions/WidgetView.php`; nothing was adjustable from the dashboard UI. v2.0 replaces that with
a real widget configuration form:

1. **Digital or analog** — a genuine radio choice. Analog mode reuses Zabbix's own native clock
   face SVG markup (`CClock.php`, the same PHP helper class the built-in Clock widget itself
   uses), so the dial/hands look and behave identically to Zabbix's own analog clock — this
   widget just draws several of them, each independently ticking in its own time zone.
2. **City/time zone selection, not hardcoded** — up to 8 clock slots, each with its own real
   IANA time zone dropdown (`CWidgetFieldSelect`, populated from PHP's actual
   `DateTimeZone::listIdentifiers()` via Zabbix's `CTimezoneHelper::getList()` — the same
   underlying data source as the `sites.csv` audit below — see the v2.1 fix note further down for
   why this is a plain `CWidgetFieldSelect` and not Zabbix's own, superficially more obvious,
   `CWidgetFieldTimeZone`), a City display name, and an optional Label override. Leave a slot's
   time zone set to
   "(not used)" to hide it.
3. **The BST/GMT problem** — every clock's Label defaults to blank now, which means the front
   end computes the *live, technically-correct* zone abbreviation every second via
   `Intl.DateTimeFormat`'s `timeZoneName` option, instead of a fixed string. London genuinely
   shows `GMT` or `BST` depending on the actual date, not a permanent `BST/GMT` compromise. Type
   something into a Label field to override this per-clock if you'd rather have fixed text.
4. **Foreground/background colour pickers** — yes, genuinely possible, confirmed via Zabbix's
   own `CWidgetFieldColor` field (the same one the native Clock widget itself uses). Applies
   globally to the whole widget (all clocks share one foreground/background pair, not
   per-clock — flagging this scope choice explicitly since it wasn't specified). Foreground
   covers the moving/readable parts (digital digits, or analog hands + tick marks); background
   covers the backdrop (digital cell background, or the analog clock-face circle). Leave either
   blank to keep inheriting the active Zabbix theme's own colours, exactly like v1 always did.
5. **Blinking colon** — a checkbox, digital mode only. Pure CSS `@keyframes` animation on the
   colon characters (no JavaScript timing involved, so it can't drift out of sync with the
   digits), toggleable independently of everything else.

**Design trade-off worth knowing:** Zabbix's only real "repeatable list" field type
(`CWidgetFieldColumnsList`) is a heavyweight popup-editor subsystem built specifically for
`tophosts`' table columns (thresholds, drag-reorder, its own controller action) — genuinely
disproportionate for a small row of clocks. v2.0 uses a **fixed 8 slots** instead, each an
ordinary field trio. This means "add a 9th clock" requires bumping
`Widget::CLOCK_SLOT_COUNT` in code and adding the matching fields, not just clicking "add" in
the UI — a real, deliberate limitation, not an oversight.

**v2.1 — real bug found and fixed on first live test of v2.0, 2026-09-03:** every dashboard
returned a 500 the moment v2.0 was installed. Apache's *default* error log
(`/var/log/apache2/error.log`) showed nothing — the custom Zabbix vhost from `zabbixme.sh` logs
to its own file, `ErrorLog ${APACHE_LOG_DIR}/zabbix_error.log`, worth remembering for any future
issue on this box. That log had the real PHP fatal:

```
PHP Fatal error:  Uncaught TypeError: Zabbix\Widgets\Fields\CWidgetFieldSelect::__construct():
Argument #3 ($values) must be of type array, null given, called in
.../CWidgetFieldTimeZone.php on line 27
```

v2.0 used Zabbix's own `CWidgetFieldTimeZone` field, passing it a custom `$values` array (a
sentinel `"(not used)"` entry plus the real IANA list) to represent an empty/unused clock slot.
That field's real constructor, read directly from the shipped source, is:

```php
public function __construct(string $name, ?string $label = null, ?array $values = null) {
	parent::__construct($name, $label, $values === null
		? [ /* built-in System default / Local default / full IANA list */ ]
		: null
	);
```

The ternary is inverted from what its signature suggests: supplying a custom `$values` array
doesn't override the option list — it makes the constructor pass `null` to its own parent
instead, which requires a non-nullable array, producing a hard fatal on every single dashboard
load (this field gets built every time `CWidget::getForm()` runs, which happens for every widget
on the page, not just this one). **Fixed** by using the plain `CWidgetFieldSelect` parent class
directly instead of `CWidgetFieldTimeZone` — it takes a genuinely honoured `$values` array with
no such inversion, populated the same way (`CTimezoneHelper::getList()`, confirmed to return the
flat `["Europe/London" => "(UTC+00:00) Europe/London", ...]` shape this field expects) plus the
`"(not used)"` sentinel. `CWidgetFieldSelect` defaults to `ZBX_WIDGET_FIELD_TYPE_INT32` save
type (built for integer-keyed selects), so `->setSaveType(ZBX_WIDGET_FIELD_TYPE_STR)` is added
explicitly so the string IANA keys round-trip correctly. `views/widget.edit.php` swapped
`CWidgetFieldTimeZoneView` for the matching `CWidgetFieldSelectView`.

**v2.2 — a second real fatal, found on the very next live test of the v2.1 fix, 2026-09-03:**
same symptom (every dashboard 500s), same wrong-log-file trap avoided this time by checking
`zabbix_error.log` straight away. The new fatal:

```
PHP Fatal error:  Uncaught Error: Call to protected method Zabbix\Widgets\CWidgetField::setSaveType()
from scope Modules\Worldclocks\Includes\WidgetForm in .../WidgetForm.php:85
```

v2.1's fix called `->setSaveType(ZBX_WIDGET_FIELD_TYPE_STR)` directly on a `CWidgetFieldSelect`
instance from inside `WidgetForm.php`. Checked the real source before shipping this fix (unlike
v2.0/v2.1, which hadn't verified this specific point): `CWidgetField::setSaveType()` is declared
`protected`. PHP only allows a `protected` method to be called from within the defining class or
its subclasses — `WidgetForm` doesn't extend `CWidgetField`, so calling it on a field instance
held from outside that hierarchy is exactly what PHP blocks, regardless of holding a live object
reference. Grepped every native Zabbix widget for real usage of
`ZBX_WIDGET_FIELD_TYPE_STR` first: **every single one** sets it from inside a small dedicated
field subclass (`CWidgetFieldTimeZone`, `CWidgetFieldTimePeriod`, `CWidgetFieldMultiSelect`,
`svggraph`'s `CWidgetFieldDataSet`, etc.) — never externally. **Fixed** by adding
`includes/CWidgetFieldTimezoneSelect.php`, a minimal subclass whose constructor calls
`setSaveType()` from inside the class hierarchy where it's actually permitted, following the
exact same pattern Zabbix's own code uses everywhere else this need comes up. Also double-checked
every other externally-called setter this module actually uses (`setDefault`, `allowInherited`)
against the real source before shipping this fix — both confirmed `public`, no further landmines
in the current field usage.

**v2.3 — colour pickers didn't render at all, 2026-09-03:** not a crash this time — Robert
confirmed v2.2 fixed the 500s and the widget worked, but the Foreground/Background colour
fields in the edit form showed no actual colour-picker swatch/popup. Checked the real
`CWidgetFieldColorView` source: it renders each colour field with `->appendColorPickerJs(false)`
— deliberately **not** including the JS that activates the interactive picker. That activation
is left to each widget to do itself; the built-in Clock widget (which also has colour fields)
does this in its own `views/widget.edit.js.php`, looping over every `.color-picker input` in its
form and calling jQuery's `.colorpicker(...)` plugin on each. This widget never had that file at
all — the fields rendered as plain (non-interactive) inputs the whole time, not a Zabbix
bug, just a missing piece of this module. **Fixed** by adding `views/widget.edit.js.php`
(adapted directly from Clock's own real code) and wiring it into `views/widget.edit.php` via
`->includeJsFile('widget.edit.js.php')->addJavaScript('worldclocks_form.init();')` — the exact
same chain Clock's own edit view ends with.

## Timezone coverage audit against `benarbejde/sites.csv`

Checked the real source of truth (`benarbejde/sites.csv`, 54 site rows) for every distinct
`Timezone` value actually in use, and cross-checked each one against the real installed IANA
tzdata (`/usr/share/zoneinfo`, via Python's `zoneinfo` module) rather than assuming any of them
are valid or already covered. This audit predates v2.0's configurability and remains accurate as
a record of what was checked and why — v2.0 doesn't change which zones are covered by default,
just makes it editable.

**19 distinct timezone values in `sites.csv`.** The widget's default configuration (7 clocks,
same as v1.1) covers 5 of them (`America/Los_Angeles`, `America/New_York`, `Europe/London`,
`Europe/Copenhagen`, `Australia/Sydney` — `Australia/Melbourne` and `Pacific/Auckland` are
additional zones of their own).

### No MDT (Mountain Time) sites

Checked every `Timezone` value in `sites.csv` for `America/Denver`, `America/Boise`,
`America/Edmonton`, `America/Phoenix`, or any other Mountain-time zone: **none present.** No
site in `sites.csv` is on Mountain Time.

### Sites on timezones not in the default configuration

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

As of v2.0, adding any of these is a dashboard-edit-form change (pick a spare slot's time zone),
not a code change — see "Configuring the clocks" below.

**Note on `America/Montreal` (MTL):** confirmed via `readlink` on the real installed tzdata that
this is a genuine, still-valid IANA zone — a backward-compatibility symlink to
`America/Toronto`, same offset, same DST schedule. Not a bug, just worth knowing it's an alias
if anyone goes looking for it in a zone picker and doesn't find it listed as a distinct primary
entry in some tools.

### Real data bug found and fixed: `Europe/Aarhus` (AAR row) was not a valid IANA timezone

Checked directly against the installed system tzdata (`python3 -c "import zoneinfo;
zoneinfo.ZoneInfo('Europe/Aarhus')"`) — this raised `No time zone found with key
Europe/Aarhus`. It was not a real IANA identifier; Denmark has exactly one IANA zone,
`Europe/Copenhagen`, which every other Danish site in `sites.csv` (CPH, FAX, FRD, FRE, KGE,
KOR, NYB, ODE) already correctly uses. `Europe/Aarhus` in the AAR row was genuinely broken — a
call to `Intl.DateTimeFormat` or PHP's `DateTimeZone` with this string throws in both
languages, not just an edge case.

**Fixed** (commit `12fe77d`, confirmed by Robert): AAR's `Timezone` corrected to
`Europe/Copenhagen` in `benarbejde/sites.csv`, full regeneration pipeline re-run per
`docs/adding-a-new-device.md` — only `ansible/configs/inventory/aar.ini`'s header comment
actually changed (nothing else surfaces this field), served `bootstrap/web/proxmox/sites.csv`
copy synced, harness clean.

## Directory tree

```
worldclocks/
├── manifest.json
├── Widget.php
├── actions/
│   └── WidgetView.php
├── includes/
│   ├── WidgetForm.php
│   └── CWidgetFieldTimezoneSelect.php
├── views/
│   ├── widget.view.php
│   ├── widget.edit.php
│   └── widget.edit.js.php
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
	"version": "2.3",
	"author": "Example Music Limited",
	"description": "Configurable row of live analog or digital clocks for up to 8 IANA time zones, with selectable colours.",
	"url": "",
	"widget": {
		"js_class": "CWidgetWorldClocks",
		"size": {
			"width": 36,
			"height": 4
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

`refresh_rate: 0` is still deliberate, matching Zabbix's own native URL widget's choice —
nothing here ever needs a server round-trip after the first load, since every clock ticks
client-side every second. Default height bumped from 3 to 4 (vs v1.x) to give analog mode's SVG
faces a bit more room; digital mode just gets slightly more whitespace, harmless either way.

### `Widget.php`

```php
<?php declare(strict_types = 0);
/**
 * World Clocks widget module.
 */

namespace Modules\Worldclocks;

use Zabbix\Core\CWidget;

class Widget extends CWidget {

	public const TYPE_DIGITAL = 0;
	public const TYPE_ANALOG = 1;

	// Zabbix has no generic "repeatable field group" type outside the heavyweight
	// CWidgetFieldColumnsList (built for tophosts' table columns, not a fit here) -- a fixed
	// number of optional slots, each a plain CWidgetFieldSelect (time zone) + two
	// CWidgetFieldTextBox fields, is the right-sized real API for a small, fixed-layout
	// "row of clocks" widget.
	public const CLOCK_SLOT_COUNT = 8;

	// Pre-filled defaults for a freshly-added widget instance -- editable afterwards via the
	// widget's own configuration form (includes/WidgetForm.php), not hardcoded at runtime.
	// "label" left blank on every entry so the front end computes the live, DST-correct zone
	// abbreviation via Intl.DateTimeFormat rather than a fixed string that can go stale twice a
	// year (e.g. London showing "BST" through a UK winter).
	public const DEFAULT_CLOCKS = [
		['tz' => 'America/Los_Angeles', 'city' => 'Los Angeles', 'label' => ''],
		['tz' => 'America/New_York',    'city' => 'New York',    'label' => ''],
		['tz' => 'Europe/London',       'city' => 'London',      'label' => ''],
		['tz' => 'Europe/Copenhagen',   'city' => 'Copenhagen',  'label' => ''],
		['tz' => 'Australia/Sydney',    'city' => 'Sydney',      'label' => ''],
		['tz' => 'Australia/Melbourne', 'city' => 'Melbourne',   'label' => ''],
		['tz' => 'Pacific/Auckland',    'city' => 'Auckland',    'label' => '']
	];

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
 */

namespace Modules\Worldclocks\Includes;

use Zabbix\Widgets\CWidgetForm;

use Zabbix\Widgets\Fields\{
	CWidgetFieldCheckBox,
	CWidgetFieldColor,
	CWidgetFieldRadioButtonList,
	CWidgetFieldTextBox
};

use CTimezoneHelper;

use Modules\Worldclocks\Widget;

class WidgetForm extends CWidgetForm {

	public function validate(bool $strict = false): array {
		$errors = parent::validate($strict);

		if ($errors) {
			return $errors;
		}

		$has_clock = false;

		for ($i = 1; $i <= Widget::CLOCK_SLOT_COUNT; $i++) {
			if ($this->getFieldValue('tz_'.$i) !== '') {
				$has_clock = true;
				break;
			}
		}

		if (!$has_clock) {
			$errors[] = _('At least one clock (time zone) must be configured.');
		}

		return $errors;
	}

	public function addFields(): self {
		$this
			->addField(
				(new CWidgetFieldRadioButtonList('clock_type', _('Clock type'), [
					Widget::TYPE_DIGITAL => _('Digital'),
					Widget::TYPE_ANALOG => _('Analog')
				]))->setDefault(Widget::TYPE_DIGITAL)
			)
			->addField(
				(new CWidgetFieldCheckBox('blink_colon', _('Blink colon (digital only)')))->setDefault(0)
			)
			->addField(
				(new CWidgetFieldColor('fg_color', _('Foreground colour')))->allowInherited()
			)
			->addField(
				(new CWidgetFieldColor('bg_color', _('Background colour')))->allowInherited()
			);

		// Deliberately plain CWidgetFieldSelect (via the local CWidgetFieldTimezoneSelect
		// subclass), not Zabbix's own CWidgetFieldTimeZone -- confirmed live (2026-09-03) that
		// CWidgetFieldTimeZone's $values constructor parameter is non-functional: its
		// constructor is `$values === null ? [built-in defaults] : null`, so passing a custom
		// array actually results in `null` being passed to the parent CWidgetFieldSelect, which
		// requires a non-nullable array -- a hard TypeError on every dashboard load. Real IANA
		// identifiers only (PHP's own DateTimeZone::listIdentifiers(), via
		// CTimezoneHelper::getList(), confirmed to return the flat ["Europe/London" =>
		// "(UTC+00:00) Europe/London", ...] shape CWidgetFieldSelect expects) plus our own
		// "(not used)" sentinel. CWidgetFieldTimezoneSelect (includes/CWidgetFieldTimezoneSelect.php)
		// exists solely to set the STR save type from inside the class hierarchy -- also
		// confirmed live: CWidgetField::setSaveType() is `protected`, so it cannot be called
		// externally on a plain CWidgetFieldSelect instance from here (a second real fatal, on
		// the fix for the first one). Every native Zabbix field needing a non-default save type
		// follows the same small-subclass pattern, never an external ->setSaveType() call.
		$timezone_values = ['' => _('(not used)')] + CTimezoneHelper::getList();

		for ($i = 1; $i <= Widget::CLOCK_SLOT_COUNT; $i++) {
			$default = Widget::DEFAULT_CLOCKS[$i - 1] ?? ['tz' => '', 'city' => '', 'label' => ''];

			$this
				->addField(
					(new CWidgetFieldTimezoneSelect('tz_'.$i, _s('Clock %1$d — Time zone', $i), $timezone_values))
						->setDefault($default['tz'])
				)
				->addField(
					(new CWidgetFieldTextBox('city_'.$i, _s('Clock %1$d — City', $i)))
						->setDefault($default['city'])
				)
				->addField(
					(new CWidgetFieldTextBox('label_'.$i, _s('Clock %1$d — Label (blank = auto)', $i)))
						->setDefault($default['label'])
				);
		}

		return $this;
	}
}
```

### `includes/CWidgetFieldTimezoneSelect.php`

```php
<?php declare(strict_types = 0);
/**
 * A plain CWidgetFieldSelect whose only purpose is calling setSaveType(ZBX_WIDGET_FIELD_TYPE_STR)
 * from within the class hierarchy.
 *
 * Confirmed live (2026-09-03): CWidgetField::setSaveType() is declared `protected`, so it cannot
 * be called on a CWidgetFieldSelect instance from outside CWidgetField's own class hierarchy
 * (e.g. not from WidgetForm.php, which doesn't extend CWidgetField) -- PHP fatals with
 * "Call to protected method ... from scope ...". Every native Zabbix field that needs a
 * non-default save type (CWidgetFieldTimeZone, CWidgetFieldTimePeriod, CWidgetFieldMultiSelect,
 * svggraph's CWidgetFieldDataSet, etc.) follows this exact same pattern -- a small dedicated
 * subclass, never an external ->setSaveType() call. This is that subclass for this widget's
 * string-keyed (IANA identifier) time zone select.
 */

namespace Modules\Worldclocks\Includes;

use Zabbix\Widgets\Fields\CWidgetFieldSelect;

class CWidgetFieldTimezoneSelect extends CWidgetFieldSelect {

	public function __construct(string $name, string $label, array $values) {
		parent::__construct($name, $label, $values);

		$this->setSaveType(ZBX_WIDGET_FIELD_TYPE_STR);
	}
}
```

Doesn't override `DEFAULT_VIEW`, so it inherits `CWidgetFieldSelect`'s own value
(`CWidgetFieldSelectView`) automatically — the edit form renders it exactly like any other plain
select, no separate view class needed.

### `actions/WidgetView.php`

```php
<?php declare(strict_types = 0);
/**
 * World Clocks widget view action.
 *
 * Reads the operator's configured clock slots (Widget::CLOCK_SLOT_COUNT of them, each a
 * tz_N/city_N/label_N field trio) and passes only the populated ones down as a plain list --
 * the front end never needs to know about the fixed slot count.
 */

namespace Modules\Worldclocks\Actions;

use CControllerDashboardWidgetView,
	CControllerResponseData;

use Modules\Worldclocks\Widget;

class WidgetView extends CControllerDashboardWidgetView {

	protected function doAction(): void {
		$clocks = [];

		for ($i = 1; $i <= Widget::CLOCK_SLOT_COUNT; $i++) {
			$tz = $this->fields_values['tz_'.$i];

			if ($tz === '') {
				continue;
			}

			$city = $this->fields_values['city_'.$i];

			$clocks[] = [
				'tz' => $tz,
				'city' => $city !== '' ? $city : $this->deriveCityFromTimezone($tz),
				'label' => $this->fields_values['label_'.$i]
			];
		}

		$this->setResponse(new CControllerResponseData([
			'name' => $this->getInput('name', $this->widget->getDefaultName()),
			'clocks' => $clocks,
			'clock_type' => (int) $this->fields_values['clock_type'],
			'blink_colon' => $this->fields_values['blink_colon'] == 1,
			'fg_color' => $this->fields_values['fg_color'],
			'bg_color' => $this->fields_values['bg_color'],
			'user' => [
				'debug_mode' => $this->getDebugMode()
			]
		]));
	}

	/**
	 * Fallback city label when the operator leaves the City field blank -- the last path
	 * segment of the IANA identifier with underscores turned into spaces, e.g.
	 * "America/Los_Angeles" -> "Los Angeles".
	 */
	private function deriveCityFromTimezone(string $tz): string {
		$pos = strrpos($tz, '/');
		$name = $pos === false ? $tz : substr($tz, $pos + 1);

		return str_replace('_', ' ', $name);
	}
}
```

### `views/widget.view.php`

```php
<?php declare(strict_types = 0);
/**
 * World Clocks widget view.
 *
 * Renders one .worldclocks-cell per configured clock, digital or analog per $data['clock_type'].
 * All ticking (time, and the auto-computed label when the operator left it blank) happens
 * entirely client-side every second (assets/js/class.widget.js) -- this view only ever needs to
 * render the initial static structure once.
 *
 * @var CView $this
 * @var array $data
 */

use Modules\Worldclocks\Widget;

$row = (new CDiv())->addClass('worldclocks-row');

if ($data['fg_color'] !== '') {
	$row->addStyle('--worldclocks-fg: #'.$data['fg_color'].';');
}

if ($data['bg_color'] !== '') {
	$row->addStyle('--worldclocks-bg: #'.$data['bg_color'].';');
}

$is_analog = ($data['clock_type'] == Widget::TYPE_ANALOG);

if ($is_analog) {
	$row->addClass('worldclocks-analog');
}

foreach ($data['clocks'] as $clock) {
	$cell = (new CDiv())
		->addClass('worldclocks-cell')
		->setAttribute('data-tz', $clock['tz']);

	if ($is_analog) {
		$cell->addItem((new CClock())->setEnabled(true));
	}
	else {
		$time = (new CDiv([
			(new CSpan('--'))->addClass('worldclocks-h'),
			(new CSpan(':'))->addClass('worldclocks-colon'),
			(new CSpan('--'))->addClass('worldclocks-m'),
			(new CSpan(':'))->addClass('worldclocks-colon'),
			(new CSpan('--'))->addClass('worldclocks-s')
		]))->addClass('worldclocks-time');

		if ($data['blink_colon']) {
			$time->addClass('worldclocks-blink');
		}

		$cell->addItem($time);
	}

	$label = (new CDiv($clock['label']))->addClass('worldclocks-label');

	if ($clock['label'] === '') {
		// No manual label -- assets/js/class.widget.js computes and fills this in every tick
		// via Intl.DateTimeFormat's timeZoneName, so it stays correct across DST transitions
		// (e.g. London genuinely shows GMT or BST depending on the date, not a fixed string).
		$label->setAttribute('data-auto', '1');
	}

	$cell->addItem($label);
	$cell->addItem((new CDiv($clock['city']))->addClass('worldclocks-city'));

	$row->addItem($cell);
}

(new CWidgetView($data))
	->addItem($row)
	->show();
```

`CClock` is reused directly from Zabbix's own core (`include/classes/html/CClock.php`) — the
exact same PHP class the native Clock widget uses to build its analog SVG face and hands, not a
hand-rolled reimplementation.

### `views/widget.edit.php`

```php
<?php declare(strict_types = 0);
/**
 * World Clocks widget edit form view.
 *
 * @var CView $this
 * @var array $data
 */

use Modules\Worldclocks\Widget;

$form = (new CWidgetFormView($data))
	->addField(
		new CWidgetFieldRadioButtonListView($data['fields']['clock_type'])
	)
	->addField(
		new CWidgetFieldCheckBoxView($data['fields']['blink_colon'])
	)
	->addField(
		new CWidgetFieldColorView($data['fields']['fg_color'])
	)
	->addField(
		new CWidgetFieldColorView($data['fields']['bg_color'])
	);

$clocks_fieldset = new CWidgetFormFieldsetCollapsibleView(_('Clocks'));

for ($i = 1; $i <= Widget::CLOCK_SLOT_COUNT; $i++) {
	$clocks_fieldset->addFieldsGroup(
		(new CWidgetFieldsGroupView(_s('Clock %1$d', $i)))
			->addField(
				new CWidgetFieldSelectView($data['fields']['tz_'.$i])
			)
			->addField(
				new CWidgetFieldTextBoxView($data['fields']['city_'.$i])
			)
			->addField(
				new CWidgetFieldTextBoxView($data['fields']['label_'.$i])
			)
	);
}

$form
	->addFieldset($clocks_fieldset)
	->includeJsFile('widget.edit.js.php')
	->addJavaScript('worldclocks_form.init();')
	->show();
```

### `views/widget.edit.js.php`

```php
<?php declare(strict_types = 0);
/**
 * World Clocks widget form JS.
 *
 * Zabbix's own CWidgetFieldColorView deliberately renders each colour field with
 * appendColorPickerJs(false) (confirmed live, 2026-09-03, by reading CColor.php/
 * CWidgetFieldColorView.php directly) -- the interactive colour-picker popup is never activated
 * automatically. Every native widget with a colour field (e.g. the built-in Clock widget) does
 * this exact same manual activation itself in its own widget.edit.js.php; this is that file for
 * this widget's fg_color/bg_color fields, adapted directly from Clock's own real code.
 */
?>

window.worldclocks_form = new class {

	init() {
		const form = document.getElementById('widget-dialogue-form');

		for (const colorpicker of form.querySelectorAll('.<?= ZBX_STYLE_COLOR_PICKER ?> input')) {
			jQuery(colorpicker).colorpicker({
				appendTo: '.overlay-dialogue-body',
				use_default: true
			});
		}
	}
};
```

### `assets/js/class.widget.js`

```javascript
/**
 * World Clocks widget front-end class.
 *
 * Lifecycle methods (onInitialize, processUpdateResponse, onDeactivate) match the pattern used
 * by Zabbix's own native Clock widget. The server renders the clock cells once (see
 * views/widget.view.php), then this class finds them via this._target and ticks every second
 * entirely client-side using Intl.DateTimeFormat against each cell's data-tz attribute -- no
 * further server round trips.
 *
 * Digital mode updates three <span> digit groups per cell (hour/minute/second) around two static
 * colon characters, so the colon can blink via CSS without the digits themselves flickering.
 * Analog mode rotates the same .clock-hand-h/-m/-s elements Zabbix's own native Clock widget
 * uses (assets/css/widget.css reuses that exact SVG markup via CClock.php), computed per-cell in
 * that cell's own time zone rather than the browser's local time.
 */
class CWidgetWorldClocks extends CWidget {

	static TYPE_DIGITAL = 0;
	static TYPE_ANALOG = 1;

	static UPDATE_INTERVAL_MS = 1000;

	onInitialize() {
		this._interval_id = null;
		this._clock_type = CWidgetWorldClocks.TYPE_DIGITAL;
		this._time_formatters = new Map();
		this._label_formatters = new Map();
	}

	onDeactivate() {
		this._stopClock();
	}

	processUpdateResponse(response) {
		super.processUpdateResponse(response);

		this._clock_type = response.clock_type ?? CWidgetWorldClocks.TYPE_DIGITAL;

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
	 * One Intl.DateTimeFormat instance per time zone for the digits, reused across ticks.
	 *
	 * @param {string} time_zone  IANA time zone identifier, e.g. "Europe/London".
	 *
	 * @returns {Intl.DateTimeFormat}
	 */
	_getTimeFormatter(time_zone) {
		if (!this._time_formatters.has(time_zone)) {
			this._time_formatters.set(time_zone, new Intl.DateTimeFormat('en-GB', {
				timeZone: time_zone,
				hourCycle: 'h23',
				hour: '2-digit',
				minute: '2-digit',
				second: '2-digit'
			}));
		}

		return this._time_formatters.get(time_zone);
	}

	/**
	 * One Intl.DateTimeFormat instance per time zone for the auto-computed zone abbreviation
	 * (used only for cells whose Label field was left blank -- see views/widget.view.php's
	 * data-auto attribute). "short" asks ICU for e.g. "GMT"/"BST"/"PDT" rather than a fixed
	 * offset; exact output depends on the browser's own ICU data, not something this code
	 * controls.
	 *
	 * @param {string} time_zone
	 *
	 * @returns {Intl.DateTimeFormat}
	 */
	_getLabelFormatter(time_zone) {
		if (!this._label_formatters.has(time_zone)) {
			this._label_formatters.set(time_zone, new Intl.DateTimeFormat('en-GB', {
				timeZone: time_zone,
				timeZoneName: 'short',
				hour: '2-digit'
			}));
		}

		return this._label_formatters.get(time_zone);
	}

	/**
	 * @param {string} time_zone
	 * @param {Date}   now
	 *
	 * @returns {{hour: number, minute: number, second: number}}
	 */
	_getTimeParts(time_zone, now) {
		const parts = this._getTimeFormatter(time_zone).formatToParts(now);
		const get = type => parseInt(parts.find(part => part.type === type)?.value ?? '0', 10);

		return {
			hour: get('hour'),
			minute: get('minute'),
			second: get('second')
		};
	}

	_tick() {
		const now = new Date();

		for (const cell of this._target.querySelectorAll('.worldclocks-cell')) {
			const time_zone = cell.dataset.tz;

			if (time_zone === undefined) {
				continue;
			}

			try {
				const time = this._getTimeParts(time_zone, now);

				if (this._clock_type === CWidgetWorldClocks.TYPE_ANALOG) {
					this._tickAnalog(cell, time);
				}
				else {
					this._tickDigital(cell, time);
				}
			}
			catch (error) {
				// Invalid/unsupported IANA time zone identifier -- leave whatever was last shown.
			}

			this._tickLabel(cell, time_zone, now);
		}
	}

	_tickDigital(cell, time) {
		const pad = value => String(value).padStart(2, '0');

		const h = cell.querySelector('.worldclocks-h');
		const m = cell.querySelector('.worldclocks-m');
		const s = cell.querySelector('.worldclocks-s');

		if (h !== null) {
			h.textContent = pad(time.hour);
		}

		if (m !== null) {
			m.textContent = pad(time.minute);
		}

		if (s !== null) {
			s.textContent = pad(time.second);
		}
	}

	_tickAnalog(cell, time) {
		const hand_h = cell.querySelector('.clock-hand-h');
		const hand_m = cell.querySelector('.clock-hand-m');
		const hand_s = cell.querySelector('.clock-hand-s');

		const h = time.hour % 12;
		const m = time.minute;
		const s = time.second;

		if (hand_h !== null) {
			this._rotateHand(hand_h, 30 * (h + m / 60 + s / 3600));
		}

		if (hand_m !== null) {
			this._rotateHand(hand_m, 6 * (m + s / 60));
		}

		if (hand_s !== null) {
			this._rotateHand(hand_s, 6 * s);
		}
	}

	_rotateHand(hand_element, degrees) {
		hand_element.setAttribute('transform', `rotate(${degrees} 50 50)`);
	}

	_tickLabel(cell, time_zone, now) {
		const label_element = cell.querySelector('.worldclocks-label[data-auto]');

		if (label_element === null) {
			return;
		}

		try {
			const parts = this._getLabelFormatter(time_zone).formatToParts(now);
			const zone_name = parts.find(part => part.type === 'timeZoneName')?.value;

			if (zone_name !== undefined) {
				label_element.textContent = zone_name;
			}
		}
		catch (error) {
			// Leave whatever label text (placeholder or previous tick's value) is already there.
		}
	}
}
```

### `assets/css/widget.css`

```css
/**
 * World Clocks widget styling.
 *
 * --worldclocks-fg / --worldclocks-bg are set inline on .worldclocks-row only when the operator
 * actually picks a colour (views/widget.view.php) -- left unset, `var(--worldclocks-fg, inherit)`
 * falls back to inheriting the active Zabbix theme's own text colour exactly as before, so an
 * unconfigured widget looks identical to v1. Foreground covers everything "moving/readable"
 * (digital digits, analog hands and tick lines); background covers the backdrop (digital cell
 * background, analog clock-face circle).
 *
 * Responsiveness is pure CSS (container queries against the widget's own box, not the viewport).
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
	color: var(--worldclocks-fg, inherit);
	background-color: var(--worldclocks-bg, transparent);
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
	min-height: 1em;
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

/* Blinking colon -- pure CSS, no JS synchronisation needed. */
@keyframes worldclocks-blink {
	50% {
		opacity: 0;
	}
}

.worldclocks-blink .worldclocks-colon {
	animation: worldclocks-blink 1s steps(1) infinite;
}

/* Analog mode -- reuses Zabbix's own native <svg class="clock-svg"> markup (CClock.php), so hand
   rotation (assets/js/class.widget.js) and the underlying dial geometry are identical to the
   built-in Clock widget's own analog face. Only the colours are overridden here. */
.worldclocks-row.worldclocks-analog .worldclocks-cell {
	gap: 4px;
}

.worldclocks-row.worldclocks-analog .clock-svg {
	width: 100%;
	max-width: 90px;
	height: auto;
}

.worldclocks-row.worldclocks-analog .clock-face {
	fill: var(--worldclocks-bg, #ebebeb);
}

.worldclocks-row.worldclocks-analog .clock-hand,
.worldclocks-row.worldclocks-analog .clock-hand-sec,
.worldclocks-row.worldclocks-analog .clock-lines {
	fill: var(--worldclocks-fg, #1f2c33);
}

/* Narrower widget: shrink the clock face/digits before anything wraps. */
@container (max-width: 620px) {
	.worldclocks-time {
		font-size: 1.25em;
	}

	.worldclocks-row.worldclocks-analog .clock-svg {
		max-width: 70px;
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

	.worldclocks-row.worldclocks-analog .clock-svg {
		max-width: 54px;
	}
}

/* Too narrow for every clock in one row: let cells wrap onto further lines, still centred. */
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
# Remove any prior copy first -- unzip won't overwrite a differently-shaped existing tree
# cleanly on its own, and v1.x's fields don't exist any more (this would break saved widget
# instances anyway -- see "Upgrading from v1.x" below).
sudo rm -rf /usr/share/zabbix/modules/worldclocks

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
sudo vim /usr/share/zabbix/modules/worldclocks/includes/CWidgetFieldTimezoneSelect.php
sudo vim /usr/share/zabbix/modules/worldclocks/views/widget.view.php
sudo vim /usr/share/zabbix/modules/worldclocks/views/widget.edit.php
sudo vim /usr/share/zabbix/modules/worldclocks/views/widget.edit.js.php
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

### Upgrading from v1.x

v1.x widget instances stored no configuration at all (everything was hardcoded), so any
existing "World Clocks" widget already on a dashboard has none of v2.0's new fields saved
against it. After upgrading the module files, **open each existing World Clocks widget's edit
dialog and Apply/Save it once** — Zabbix fills in v2.0's field defaults (the same 7 clocks,
Digital mode, no colours, blink off) at that point. Until you do this, the widget still renders
using whatever cached response it last had; the module files themselves are safe to upgrade with
dashboards open.

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
4. **Clock type**: Digital or Analog.
5. **Blink colon**: only affects Digital mode.
6. **Foreground colour** / **Background colour**: pick from the colour swatch, or leave blank to
   keep following the active Zabbix theme.
7. Expand the **Clocks** section — 8 numbered groups, each with a **Time zone** dropdown (search
   by typing, e.g. "Beirut" or "Toronto"), a **City** text field (what's actually shown on the
   dashboard — leave blank to fall back to the time zone's own city segment, e.g.
   `America/New_York` → "New York"), and a **Label** text field (leave blank for the live
   auto-computed abbreviation, e.g. GMT/BST for London; type something to fix it, e.g. `UTC`).
   Set a slot's Time zone to **(not used)** to hide that clock entirely.
8. **Add**, then **Save changes**.

## Expected appearance

Digital, default 7-clock configuration (labels shown here are what the *auto* computation is
expected to produce for these zones around the given moment — verify visually once installed,
since exact ICU output depends on the browser):

```
   PDT          EDT          GMT          CET          AEST         AEST         NZDT
 11:32:41     14:32:41     19:32:41    20:32:41     05:32:41     05:32:41     07:32:41
Los Angeles   New York      London     Copenhagen    Sydney      Melbourne    Auckland
```

Colour follows whichever Zabbix theme is active (light/dark/high-contrast) automatically unless
you've picked explicit foreground/background colours. Narrowing the widget shrinks the clock
font (and, in Analog mode, the clock face size) progressively, then wraps onto further rows if
it gets too tight for every configured clock in one line.

## Troubleshooting

**Module doesn't appear after "Scan directory":**
- Check the JSON is valid: `sudo python3 -m json.tool /usr/share/zabbix/modules/worldclocks/manifest.json` (fails loudly on syntax errors).
- Confirm the path is exactly `modules/worldclocks/manifest.json` — `widgets/` is the wrong
  location.
- Confirm ownership/permissions as above — if Apache's PHP process can't read the files, the
  manifest silently fails to load (no error shown, it just won't appear in the list).

**Every dashboard says "permission denied" (or similar), even for Admin:**
- This is the exact symptom of the v1.0 bug above — a module with a mismatched class name
  aborts Zabbix's own module loader partway through, taking every other widget down with it,
  not just this one. **`sudo rm -rf /usr/share/zabbix/modules/worldclocks`**, then
  **Administration → General → Modules → Scan directory** — every dashboard recovers
  immediately. Reinstall using the current code from this doc/zip, not an older copy.

**Administration → General → Modules shows "Wrong Widget.php class name for module located
at modules/worldclocks":**
- Every `namespace` line in the PHP files must read exactly `Modules\Worldclocks...` (case
  matters, must match `ucfirst("modules")` = `Modules`, plus the manifest's own `"namespace":
  "Worldclocks"` value) — **not** `Widgets\Worldclocks...`, which is what a module installed
  under `widgets/` would need, not `modules/`. Check all three: `Widget.php`,
  `actions/WidgetView.php`, `includes/WidgetForm.php`.
- This is also treated as a fatal error state by Zabbix's own module loader — see the entry
  above if dashboards stopped working entirely rather than just this widget failing to appear.

**Widget's edit dialog shows "At least one clock (time zone) must be configured":**
- Every one of the 8 Time zone dropdowns is set to "(not used)". Pick a real zone for at least
  one slot.

**Whole dashboard 500s / widget shows a blank/broken tile:**
- **Check the right error log.** The custom Zabbix vhost (from `zabbixme.sh`) logs to its own
  file, not Apache's default: `grep -i errorlog /etc/apache2/sites-available/zabbix.conf` to
  confirm the exact path (as of this writing: `/var/log/apache2/zabbix_error.log`), then
  `sudo tail -150 /var/log/apache2/zabbix_error.log`. The default `/var/log/apache2/error.log`
  will look completely clean even while this vhost is throwing fatals — confirmed live,
  2026-09-03 (the v2.1 incident above).
- If that's quiet too, check `/var/log/apache2/zabbix_access.log` for the actual HTTP status of
  the request that failed, to confirm exactly which action 500'd and when, then cross-reference
  the timestamp against the error log.
- Turn on Zabbix's own frontend debug mode (**Administration → General → GUI → Debug mode**, or
  per-user in profile) to get a debug panel with PHP errors directly in the dashboard widget.

**Clocks show `--` / never update, or analog hands don't move:**
- Open browser DevTools → Console on the dashboard page — a JS error there will show directly.
- Confirm the JS file is actually being served: DevTools → Network tab, look for
  `modules/worldclocks/assets/js/class.widget.js` — if it's 404, re-check the file was copied to
  the right path and is readable.
- If it loads but nothing updates, check `manifest.json`'s `"js_class"` value matches the JS
  file's `class CWidgetWorldClocks` name exactly (case-sensitive).

**A clock's label never shows an abbreviation (auto mode) or colours don't apply:**
- Auto labels: some IANA zones don't have a well-known short abbreviation in every browser's
  ICU data — a numeric offset (e.g. `GMT+1`) instead of a letter code (e.g. `CET`) is the
  browser doing that, not a bug in this widget; type a fixed Label for that clock if you want a
  specific string regardless.
- Colours: confirm the hex value was actually saved (re-open the widget's edit dialog) — a blank
  colour field means "inherit theme", which is correct default behaviour, not a fault.

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
