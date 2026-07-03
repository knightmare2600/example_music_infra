# Solarized Dark — Terminal Colour Setup

**Purpose:** Fix unreadable dark blue (and other low-contrast ANSI colours) in terminal
output from tools like `grc`, `ls`, `vim`, `git` etc. Remapping at the terminal level
fixes everything at once — no per-app config needed.

---

## Solarized Dark Palette — ANSI Colour Slots

These are the values to enter in each terminal emulator. All values are RGB 0–255.

| Slot | Name | R | G | B | Hex |
|------|------|---|---|---|-----|
| 0 | Black | 7 | 54 | 66 | `#073642` |
| 1 | Red | 220 | 50 | 47 | `#DC322F` |
| 2 | Green | 133 | 153 | 0 | `#859900` |
| 3 | Yellow | 181 | 137 | 0 | `#B58900` |
| 4 | **Blue** | **38** | **139** | **210** | **`#268BD2`** |
| 5 | Magenta | 211 | 54 | 130 | `#D33682` |
| 6 | Cyan | 42 | 161 | 152 | `#2AA198` |
| 7 | White | 238 | 232 | 213 | `#EEE8D5` |
| 8 | Bright Black | 0 | 43 | 54 | `#002B36` |
| 9 | Bright Red | 203 | 75 | 22 | `#CB4B16` |
| 10 | Bright Green | 88 | 110 | 117 | `#586E75` |
| 11 | Bright Yellow | 101 | 123 | 131 | `#657B83` |
| 12 | **Bright Blue** | **131** | **148** | **150** | **`#839496`** |
| 13 | Bright Magenta | 108 | 113 | 196 | `#6C71C4` |
| 14 | Bright Cyan | 147 | 161 | 161 | `#93A1A1` |
| 15 | Bright White | 253 | 246 | 227 | `#FDF6E3` |

**Foreground:** R `131` G `148` B `150` — `#839496`  
**Background:** R `0` G `43` B `54` — `#002B36`  
**Cursor:** R `131` G `148` B `150` — `#839496`

> The key fix is slot 4 (Blue): default is near-black `#0000BB`, Solarized replaces it
> with a proper visible `#268BD2`. This is what makes `grc`, `git`, `ls` etc. readable
> on dark backgrounds.

---

## iTerm2 (macOS)

1. **Preferences** → **Profiles** → select your profile → **Colors** tab
2. Click each ANSI colour swatch and enter the RGB values from the table above
3. Set **Foreground** and **Background** from the values above
4. Alternatively — download a pre-built Solarized Dark `.itermcolors` preset:
   - <https://github.com/altercation/solarized/tree/master/iterm2-colors-solarized>
   - Import via **Colors** tab → **Color Presets…** → **Import…**

---

## Windows Terminal

Edit `settings.json` (open via **Settings** → **Open JSON file**). Add or replace the
`colorScheme` block and reference it in your profile:

```json
{
    "schemes": [
        {
            "name": "Solarized Dark",
            "background": "#002B36",
            "foreground": "#839496",
            "cursorColor": "#839496",
            "selectionBackground": "#073642",
            "black": "#073642",
            "red": "#DC322F",
            "green": "#859900",
            "yellow": "#B58900",
            "blue": "#268BD2",
            "purple": "#D33682",
            "cyan": "#2AA198",
            "white": "#EEE8D5",
            "brightBlack": "#002B36",
            "brightRed": "#CB4B16",
            "brightGreen": "#586E75",
            "brightYellow": "#657B83",
            "brightBlue": "#839496",
            "brightPurple": "#6C71C4",
            "brightCyan": "#93A1A1",
            "brightWhite": "#FDF6E3"
        }
    ],
    "profiles": {
        "list": [
            {
                "guid": "{your-profile-guid}",
                "colorScheme": "Solarized Dark"
            }
        ]
    }
}
```

---

## PuTTY / PuTTY-ND

PuTTY stores colours per saved session. Set once, save the session, then export as `.reg`
for easy deployment to other machines.

1. Open PuTTY → load or create a saved session
2. Navigate to **Window** → **Colours**
3. Select each colour from the list and click **Modify** — enter R, G, B values:

| PuTTY Label | R | G | B |
|-------------|---|---|---|
| Default Foreground | 131 | 148 | 150 |
| Default Background | 0 | 43 | 54 |
| Cursor Colour | 131 | 148 | 150 |
| ANSI Black | 7 | 54 | 66 |
| ANSI Black Bold | 0 | 43 | 54 |
| ANSI Red | 220 | 50 | 47 |
| ANSI Red Bold | 203 | 75 | 22 |
| ANSI Green | 133 | 153 | 0 |
| ANSI Green Bold | 88 | 110 | 117 |
| ANSI Yellow | 181 | 137 | 0 |
| ANSI Yellow Bold | 101 | 123 | 131 |
| **ANSI Blue** | **38** | **139** | **210** |
| ANSI Blue Bold | 131 | 148 | 150 |
| ANSI Magenta | 211 | 54 | 130 |
| ANSI Magenta Bold | 108 | 113 | 196 |
| ANSI Cyan | 42 | 161 | 152 |
| ANSI Cyan Bold | 147 | 161 | 161 |
| ANSI White | 238 | 232 | 213 |
| ANSI White Bold | 253 | 246 | 227 |

4. **Save** the session
5. To export for reuse on other machines:

```
regedit → HKEY_CURRENT_USER\Software\SimonTatham\PuTTY\Sessions\<YourSessionName>
Right-click → Export → save as .reg
```

Import on a new machine with a double-click.

---

## tmux

tmux passes ANSI codes through to the underlying terminal — **no changes needed here**.
Fix iTerm2, Windows Terminal, or PuTTY as above and tmux inherits the palette
automatically. The one exception is if you have hardcoded colour values in
`~/.tmux.conf` using `colour4` (blue) etc. — replace those with explicit hex values:

```bash
# ~/.tmux.conf — replace hardcoded ANSI blue references
# Instead of:  colour4
# Use:         colour32  (approximates #268BD2 in the 256-colour cube)
# Or use true colour if your terminal supports it:
set -g default-terminal "tmux-256color"
set -ga terminal-overrides ",*256col*:Tc"
# Then use: #268BD2 directly in colour definitions
```

---

## Alacritty

In `~/.config/alacritty/alacritty.toml`:

```toml
[colors.primary]
background = "#002B36"
foreground = "#839496"

[colors.normal]
black   = "#073642"
red     = "#DC322F"
green   = "#859900"
yellow  = "#B58900"
blue    = "#268BD2"
magenta = "#D33682"
cyan    = "#2AA198"
white   = "#EEE8D5"

[colors.bright]
black   = "#002B36"
red     = "#CB4B16"
green   = "#586E75"
yellow  = "#657B83"
blue    = "#839496"
magenta = "#6C71C4"
cyan    = "#93A1A1"
white   = "#FDF6E3"
```

---

## GNOME Terminal / Tilix

1. **Edit** → **Preferences** → select your profile → **Colors** tab
2. Uncheck **Use colors from system theme**
3. Set **Built-in schemes** to **Custom**
4. Enter background `#002B36`, foreground `#839496`
5. Click each colour swatch in the palette grid and enter hex values from the table above

---

*Internal Infrastructure Documentation — Example Music Limited*
