#!/bin/zsh
# =============================================================================
# Server-specific coloured prompt (zsh version)
# Solarized dark, glaucoma-friendly. High contrast, muted but distinct colours.
# =============================================================================
#
# WHAT IT DOES
#   Sets PROMPT to colour-coded   user@host[path]$   based on:
#     - environment (production / staging / unknown)
#     - whether you're root or not
#
#   Colour map:
#                   non-root          root
#     production    yellow (226)      red    (167)
#     staging       green  (64)       orange (166)
#     unknown       cyan   (37)       magenta(125)
#
# ENVIRONMENT DETECTION
#   Looks for Ansible-managed marker files (zero-byte placeholders):
#     /etc/.production   -> production
#     /etc/.staging      -> staging
#   Falls back to $SERVER_ENV if neither exists, then "unknown".
#   Re-checked on every prompt draw, so Ansible can flip it without re-login.
#
# INSTALLATION
#   1. Place this script at /opt/scripts/server-prompts.zsh
#   2. Source it from /etc/zsh/zshrc (system-wide, covers sudo -s):
#        if [[ -f /opt/scripts/server-prompts.zsh ]]; then
#            source /opt/scripts/server-prompts.zsh
#        fi
#      (For per-user only, append the same block to ~/.zshrc instead.)
#   3. Open a new shell or run:  source /etc/zsh/zshrc
#
# -----------------------------------------------------------------------------
# PUTTY CONFIGURATION (required for colours to render correctly)
# -----------------------------------------------------------------------------
#   In PuTTY's session config tree, set the following:
#
#   Window -> Colours
#     [x] Allow terminal to use xterm 256-colour mode      <-- ESSENTIAL
#     [x] Allow terminal to specify ANSI colours
#     [ ] Indicate bolded text by changing the colour       (recommend OFF)
#
#   Connection -> Data
#     Terminal-type string:  xterm-256color
#         (default is just "xterm" - change it)
#
#   Optional (Solarized Dark base colours, easier on eyes):
#     Window -> Colours -> Select a colour to adjust
#       Default Foreground       RGB  131, 148, 150
#       Default Background       RGB    0,  43,  54
#       Default Bold Foreground  RGB  147, 161, 161
#       Cursor Colour            RGB  147, 161, 161
#
#   IMPORTANT: After changing settings, go back to "Session" at the top of the
#   tree, select your saved session, and click "Save". Otherwise changes only
#   apply to the current connection.
#
# -----------------------------------------------------------------------------
# COLOUR CODE NOTES
# -----------------------------------------------------------------------------
#   The 256-colour numbers below were picked to render legibly in PuTTY's
#   default 256-cube. Strict Solarized codes (136/160) rendered as green and
#   too-dark-red respectively, hence the swap to 226 and 167.
#
#   To preview all 256 colours on your terminal:
#     for i in {0..255}; do
#         printf '\e[38;5;%dm%3d ' "$i" "$i"
#         (( (i + 1) % 16 == 0 )) && printf '\n'
#     done
#     printf '\e[0m\n'
#
# -----------------------------------------------------------------------------
# ZSH-SPECIFIC NOTES (differences from the bash sibling script)
# -----------------------------------------------------------------------------
#   - Uses zsh's %F{N}...%f colour syntax. No \[ \] markers needed - zsh tracks
#     non-printing widths automatically with this syntax, so Ctrl+R and line
#     editing work correctly out of the box.
#
#   - Prompt escapes translated from bash to zsh:
#         bash \u   ->  zsh %n      (username)
#         bash \h   ->  zsh %m      (hostname, short)
#         bash \w   ->  zsh %~      (cwd with ~ for home)
#         bash \$   ->  zsh %(!.#.$)  ( # if root, $ if not )
#
#   - Hooks into precmd via add-zsh-hook. This appends to the precmd list
#     rather than overwriting it, so Oh My Zsh / Prezto / other frameworks'
#     hooks are preserved. If this script is sourced AFTER an OMZ theme,
#     it cleanly overrides the theme's PROMPT.
#
#   - No PROMPT_SUBST required: $c is expanded at PROMPT assignment time
#     (inside set_prompt), and the resulting prompt-escape string is then
#     interpreted by zsh at draw time.
#
# =============================================================================

# ---------------------------------------------------------------
# Detect environment - checks Ansible-managed marker files
# Called dynamically each prompt so Ansible changes apply without re-login
# ---------------------------------------------------------------
detect_environment() {
    if [[ -e /etc/.production ]]; then
        echo "production"
    elif [[ -e /etc/.staging ]]; then
        echo "staging"
    elif [[ -n "$SERVER_ENV" ]]; then
        echo "$SERVER_ENV"
    else
        echo "unknown"
    fi
}

# ---------------------------------------------------------------
# Set PROMPT before each prompt
# Format: user@host[path]$   (# instead of $ when root)
# ---------------------------------------------------------------
set_prompt() {
    local env c
    env=$(detect_environment)

    case "$env" in
        production)
            [[ $EUID -eq 0 ]] && c=167 || c=226
            ;;
        staging)
            [[ $EUID -eq 0 ]] && c=166 || c=64
            ;;
        *)
            [[ $EUID -eq 0 ]] && c=125 || c=37
            ;;
    esac

    PROMPT="%F{${c}}%n%f@%F{${c}}%m%f%F{${c}}[%~]%f%F{${c}}%(!.#.$)%f "
}

# Register set_prompt as a precmd hook (runs before each prompt).
# add-zsh-hook is the safe way - it appends rather than replacing precmd.
autoload -Uz add-zsh-hook
add-zsh-hook precmd set_prompt
