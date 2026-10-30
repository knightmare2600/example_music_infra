#!/usr/bin/env bash
# usage: ./qm-type.sh <vmid> 'string to type'

vmid="$1"
text="$2"

# literal char -> qemu keycode (unshifted symbols)
declare -A base=(
  ["-"]="minus"           ["="]="equal"
  ["["]="bracket_left"    ["]"]="bracket_right"
  ["\\"]="backslash"      [";"]="semicolon"
  ["'"]="apostrophe"      [","]="comma"
  ["."]="dot"             ["/"]="slash"
  ["\`"]="grave_accent"   [" "]="spc"
)

# literal char -> shift-<keycode> (shifted symbols, US layout)
declare -A shifted=(
  ["!"]="shift-1"  ["@"]="shift-2"  ["#"]="shift-3"
  ["\$"]="shift-4" ["%"]="shift-5"  ["^"]="shift-6"
  ["&"]="shift-7"  ["*"]="shift-8"  ["("]="shift-9"
  [")"]="shift-0"  ["_"]="shift-minus" ["+"]="shift-equal"
  ["{"]="shift-bracket_left"  ["}"]="shift-bracket_right"
  ["|"]="shift-backslash"     [":"]="shift-semicolon"
  ["\""]="shift-apostrophe"   ["<"]="shift-comma"
  [">"]="shift-dot"           ["?"]="shift-slash"
  ["~"]="shift-grave_accent"
)

for (( i=0; i<${#text}; i++ )); do
  c="${text:$i:1}"
  if [[ -n "${shifted[$c]}" ]]; then
    key="${shifted[$c]}"
  elif [[ -n "${base[$c]}" ]]; then
    key="${base[$c]}"
  elif [[ "$c" =~ [A-Z] ]]; then
    key="shift-${c,,}"
  else
    key="$c"
  fi
  qm sendkey "$vmid" "$key" || echo "failed on char: $c" >&2
  sleep 0.05
done
