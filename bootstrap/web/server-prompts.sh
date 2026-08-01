#!/bin/bash
# =============================================================================
# Server-specific coloured prompt
# Solarized dark, glaucoma-friendly. High contrast, muted but distinct colours.
# =============================================================================
#
# 2026-08-01 (Robert): also carries the same ls/grep colour aliases as the zsh
# sibling script, for consistency between bash and zsh sessions on the same
# node. See server-prompts.zsh's own 2026-08-01 note for the fuller rationale
# (this script's zsh sibling is now the single home for shell quality-of-life
# config, not a second competing ~/.zshrc). No fg() shim here -- bash already
# accepts a bare job number (fg 1), only zsh needs the %1 translation.
#
# WHAT IT DOES
#   Sets PS1 to colour-coded   user@host[path]$   based on:
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
#   1. Place this script at /opt/scripts/server-prompts.sh
#   2. Source it from /etc/bash.bashrc (system-wide, covers sudo -s):
#        if [[ -f /opt/scripts/server-prompts.sh ]]; then
#            source /opt/scripts/server-prompts.sh
#        fi
#   3. Open a new shell or run:  source /etc/bash.bashrc
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
# =============================================================================

# ---------------------------------------------------------------
# Aliases
# ---------------------------------------------------------------
alias ls='ls --color=auto'
alias ll='ls -lah'
alias grep='grep --color=auto'

# ---------------------------------------------------------------
# Detect environment - checks Ansible-managed marker files
# Called dynamically each prompt so it picks up Ansible changes
# without needing to re-login
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
# Set PS1 before each prompt
# Uses \033 (octal escape) instead of \e for max bash compatibility
# Uses \[ \] to mark non-printing chars (prevents Ctrl+R / ls breakage)
# ---------------------------------------------------------------
set_prompt() {
    local R='\[\033[0m\]'              # reset
    local YEL='\[\033[38;5;226m\]'     # bright yellow (prod non-root)
    local ORG='\[\033[38;5;166m\]'     # solarized orange (staging root)
    local RED='\[\033[38;5;167m\]'     # readable red (prod root)
    local GRN='\[\033[38;5;64m\]'      # solarized green (staging non-root)
    local CYN='\[\033[38;5;37m\]'      # solarized cyan
    local MAG='\[\033[38;5;125m\]'     # solarized magenta
    
    local env c
    env=$(detect_environment)
    
    case "$env" in
        production)
            [[ $EUID -eq 0 ]] && c=$RED || c=$YEL
            ;;
        staging)
            [[ $EUID -eq 0 ]] && c=$ORG || c=$GRN
            ;;
        *)
            [[ $EUID -eq 0 ]] && c=$MAG || c=$CYN
            ;;
    esac
    
    PS1="${c}\u${R}@${c}\h${R}${c}[\w]${R}${c}\\\$${R} "
}

PROMPT_COMMAND='set_prompt'
