"""
screenprint -- custom Salt execution module for colourised console output.

Ported 2026-07-20 from https://github.com/knightmare2600/saltstack (Robert's own
personal Salt utilities repo -- retired in favour of keeping this here instead,
one repo rather than two). Extended the same day: the original screen_print()
only took a `color` argument (red/yellow/green/cyan/default); the reference
state it was dropped in alongside already called it with a `messagetype`
argument instead (header/success/warning/error/info/banner) that the real
function never actually supported -- the state and the module had drifted
apart, and every call in that file would have raised a TypeError on a real
minion. `messagetype` is now a real, supported parameter, mapped onto the
exact same ANSI colour convention already used estate-wide in
ansible/configs/inventory/group_vars/all/colours.yml (Ansible's own `_c.R/G/Y/O/C/W/NC`)
-- not a new colour scheme invented independently:
    header  -> cyan   (colours.yml: "info, section headers, box borders")
    success -> green  (colours.yml: "success, [+], confirmed values")
    warning -> yellow (colours.yml: "cautions, [!], prompts")
    error   -> red    (colours.yml: "errors, warnings that need action")
    info    -> cyan   (same bucket as header in colours.yml)
    banner  -> white  (colours.yml: "box top-lines... emphasis")
    footer  -> white  (same bucket as banner -- bookends the same check run,
                       added 2026-07-20 alongside salt/states/audit/init.sls's
                       own closing message)

`color` still works on its own for any caller not using messagetype (backward
compatible with the original module) -- messagetype takes priority if both are
given.
"""

# ANSI colour codes -- same values as ansible/configs/inventory/group_vars/all/colours.yml's
# _c.R/G/Y/C/W/NC (that file's own \e is the same escape as \033 here, just a different
# shell-escaping convention -- same bytes).
COLORS = {
    "red": "\033[0;31m",
    "yellow": "\033[1;33m",
    "green": "\033[0;32m",
    "cyan": "\033[0;36m",
    "white": "\033[1;37m",
    "default": "\033[0m",
}

MESSAGETYPE_COLOR = {
    "header": "cyan",
    "success": "green",
    "warning": "yellow",
    "error": "red",
    "info": "cyan",
    "banner": "white",
    "footer": "white",
}


def screen_print(message, color="default", messagetype=None):
    """
    Prints a custom message to the screen with optional colour.

    Args:
        message (str): The message to print.
        color (str): The colour of the message. Options are 'red', 'yellow',
            'green', 'cyan', 'white', or 'default'. Ignored if messagetype is given.
        messagetype (str): One of 'header', 'success', 'warning', 'error',
            'info', 'banner' -- maps to a colour via MESSAGETYPE_COLOR, matching
            this estate's existing colours.yml convention. Takes priority over
            color if both are given.

    Returns:
        str: The printed message with colour.
    """
    if messagetype is not None:
        color = MESSAGETYPE_COLOR.get(messagetype.lower(), "default")

    color_code = COLORS.get(color.lower(), COLORS["default"])
    colored_message = f"{color_code}{message}{COLORS['default']}"

    print(colored_message)

    return colored_message
