#!/usr/bin/env bash
# IronBark end-to-end walkthrough.
#
# Non-interactive, no network, no stored state: every line below runs the real
# commands against the tables embedded in ironbark.py. Failure paths are shown
# and their exit codes are checked, so this script doubles as a smoke test.
#
#   bash demo.sh
#
set -uo pipefail
cd "$(dirname "$0")"

PYTHON="${PYTHON:-python3}"
TABLE=("$PYTHON" ironbark.py)

banner() { printf '\n========== %s ==========\n' "$1"; }

show() {
  printf '\n$ %s\n' "$*"
  "$@"
}

show_expect() {
  local want="$1"
  shift
  printf '\n$ %s\n' "$*"
  "$@"
  local got=$?
  printf '[exit %s - expected %s]\n' "$got" "$want"
  if [ "$got" -ne "$want" ]; then
    printf 'FAIL: expected exit %s, got %s for: %s\n' "$want" "$got" "$*" >&2
    exit 1
  fi
}

banner "IronBark - one command, three shop lookups"
show "${TABLE[@]}" --help

banner "Heat colour: an exact band, then a gap between bands"
show "${TABLE[@]}" heat 780
show "${TABLE[@]}" heat 1260

banner "Quench medium: canonical name, then two shop aliases"
show "${TABLE[@]}" quench 1084
show "${TABLE[@]}" quench o-1
show "${TABLE[@]}" quench "1084 steel"

banner "Hammer strike order: full name, then the shop nickname"
show "${TABLE[@]}" strike knife-blank
show "${TABLE[@]}" strike kb

banner "Honest failures - one line each, never a traceback"
show_expect 2 "${TABLE[@]}" heat hot
show_expect 2 "${TABLE[@]}" heat 5000
show_expect 2 "${TABLE[@]}" heat
show_expect 2 "${TABLE[@]}" quench
show_expect 2 "${TABLE[@]}" strike
show_expect 1 "${TABLE[@]}" quench unobtainium
show_expect 1 "${TABLE[@]}" strike unobtainium
show_expect 2 "${TABLE[@]}" frobnicate

banner "Done"
printf '\nEvery lookup above ran offline from the tables in ironbark.py.\n'
printf 'Exit codes: 0 success, 1 unknown alloy/billet, 2 usage failure.\n'
