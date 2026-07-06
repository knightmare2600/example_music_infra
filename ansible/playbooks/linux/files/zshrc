##----------------------------------------------------------------------------##
## .zshrc Make zsh dance to my tune. Deliberately preserve any bashisms like  ##
##        "fg" behaviour. The compatibility shims are commented as such...    ##
##                                                                            ##
## History:                                                                   ##
##                                                                            ##
## 31 Oct 2024  v1.00  Initial version. New arrival from bash                 ##
## 02 Nov 2024  v1.01  Compatibility shims like fg & keyboard word movement   ##
## 01 Apr 2025  v1.02  plug-ins, confirm MacOS Homebrew vs Linux paths        ##
## 24 Dec 2025  v1.05  Compatibility shim for arm64 vs amd64 MacOS            ##
## 25 May 2026  v1.10  Rework MacOS shim                                      ##
## 30 May 2026  v1.11  Midnight Commander solarized support                   ##
## 07 Jun 2026  v1.12  Correct arrow key tomfoolery in PuTTY noodle build     ##
##                                                                            ##
##----------------------------------------------------------------------------##

## Lines configured by zsh-newuser-install
HISTFILE=~/.histfile
HISTSIZE=1000
SAVEHIST=1000
ZSH_THEME="parrot"

## Key bindings. Uses emacs mode for consistency across Linux/MacOS/PuTTY CTRL +
## Arrow bindings only work if terminal sends proper escape sequences.
bindkey -e
bindkey "\e[1~" beginning-of-line
bindkey "\e[4~" end-of-line
bindkey '^[[D' backward-char
bindkey '^[[C' forward-char
bindkey '^[OD' backward-char
bindkey '^[OC' forward-char
bindkey "\e[1;5C" forward-word
bindkey "\e[1;5D" backward-word

## Completion system
zstyle ':completion:*' menu select
autoload -U promptinit && promptinit
autoload -Uz compinit

## compinit -u allows insecure completion dirs (common on mixed systems) a safer
## alternative is compinit with proper permissions fixed via compaudit
compinit -u

## Bash-like fg compatibility
fg() {
  if [[ "$*" =~ ^[0-9]+$ ]]; then
    builtin fg %"$*"
  else
    builtin fg "$@"
  fi
}

## Platform detection
case "$(uname -s)" in

  Darwin)
    ## Homebrew (Apple Silicon + Intel)
    if [[ -d /opt/homebrew ]]; then
      export HOMEBREW_PREFIX="/opt/homebrew"
    elif [[ -d /usr/local/Homebrew ]] || [[ -d /usr/local/opt ]]; then
      export HOMEBREW_PREFIX="/usr/local"
    fi

    ## Ensure Homebrew binaries are first in PATH
    [[ -n "$HOMEBREW_PREFIX" ]] && export PATH="$HOMEBREW_PREFIX/bin:$PATH"

    ## GNU ls fallback handling
    if command -v gls >/dev/null 2>&1; then
      alias ls='gls --color=auto'
    else
      alias ls='ls -G'
    fi

    ## macOS plugins (only sourced if present)
    for plugin in sh-autosuggestions/zsh-autosuggestions.zsh zsh-syntax-highlighting/zsh-syntax-highlighting.zsh
    do
      [[ -f "$HOMEBREW_PREFIX/share/$plugin" ]] && source "$HOMEBREW_PREFIX/share/$plugin"
    done
    ;;

  Linux)
    alias ls='ls --color=auto'

    for plugin in /usr/share/zsh-autosuggestions/zsh-autosuggestions.zsh /usr/share/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh
    do
      [[ -f "$plugin" ]] && source "$plugin"
    done
    ;;
esac

## Shell behaviour
setopt CHECK_JOBS
setopt CHECK_RUNNING_JOBS
setopt interactive_comments

## Syntax highlighting style tweak
ZSH_HIGHLIGHT_STYLES[comment]='fg=cyan'

## Prompt
PROMPT='%F{red}┌─[%F{green}%n%F{cyan}@%F{white}%m%F{red}]─[%F{green}%d%F{red}]
└──╼ %F{%(#.red.yellow)}$ %F{reset}'
