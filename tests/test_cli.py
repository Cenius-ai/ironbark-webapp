"""Command-level tests for IronBark: happy paths, failure paths, exit codes.

Every case runs a real subprocess, so exit codes, stream routing and
byte-for-byte determinism are covered, not just the helper functions.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

import ironbark

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "ironbark.py"


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=str(ROOT),
        timeout=30,
    )


# --------------------------------------------------------------------------- #
# Usage, help and exit-code contract
# --------------------------------------------------------------------------- #
def test_bare_invocation_lists_three_commands_and_exits_zero():
    result = run()
    assert result.returncode == 0
    for command, example in (
        ("heat", "ironbark heat 780"),
        ("quench", "ironbark quench 1084"),
        ("strike", "ironbark strike knife-blank"),
    ):
        assert command in result.stdout
        assert example in result.stdout
    assert result.stderr == ""


def test_help_lists_three_commands_with_examples():
    result = run("--help")
    assert result.returncode == 0
    assert "heat" in result.stdout
    assert "quench" in result.stdout
    assert "strike" in result.stdout
    assert "ironbark heat 780" in result.stdout


@pytest.mark.parametrize("command", ["heat", "quench", "strike"])
def test_subcommand_help_exits_zero(command):
    result = run(command, "--help")
    assert result.returncode == 0
    assert f"ironbark {command}" in result.stdout


def test_heat_help_states_the_accepted_range():
    result = run("heat", "--help")
    assert result.returncode == 0
    assert "200" in result.stdout and "1400" in result.stdout
    assert "ironbark heat 780" in result.stdout


def test_unknown_command_prints_message_and_summary():
    result = run("frobnicate")
    assert result.returncode == 2
    assert "unknown command frobnicate" in result.stderr
    assert "ironbark heat 780" in result.stderr
    assert "Traceback" not in result.stderr


def test_version_prints_and_exits_zero():
    result = run("--version")
    assert result.returncode == 0
    assert result.stdout.strip() == f"ironbark {ironbark.VERSION}"


# --------------------------------------------------------------------------- #
# heat
# --------------------------------------------------------------------------- #
def test_heat_exact_band_prints_name_hex_span_and_note():
    result = run("heat", "800")
    assert result.returncode == 0
    out = result.stdout
    assert "full cherry red" in out
    assert "#C7311B" in out
    assert "710\u2013800 \u00b0C" in out
    assert "normalising and straightening heat" in out
    assert "nearest of" not in out  # an exact match is printed as-is


def test_heat_between_bands_resolves_to_nearest_with_its_span():
    result = run("heat", "1260")
    assert result.returncode == 0
    assert "white yellow" in result.stdout
    assert "1265\u20131330 \u00b0C" in result.stdout
    assert "nearest of" in result.stdout


@pytest.mark.parametrize("argument", ["hot", "5000", "199", "nan", ""])
def test_heat_rejects_bad_input_with_one_range_line(argument):
    result = run("heat", argument)
    assert result.returncode == 2
    assert "200\u20131400 \u00b0C" in result.stderr
    assert len([line for line in result.stderr.splitlines() if line.strip()]) == 1
    assert "Traceback" not in result.stderr
    assert "usage:" not in result.stderr


def test_heat_accepts_the_range_endpoints():
    assert run("heat", "200").returncode == 0
    assert run("heat", "1400").returncode == 0


def test_heat_bare_prints_the_example_invocation():
    result = run("heat")
    assert result.returncode == 2
    assert "ironbark heat 780" in result.stderr
    assert "Traceback" not in result.stderr


# --------------------------------------------------------------------------- #
# quench
# --------------------------------------------------------------------------- #
def test_quench_1084_prints_labelled_medium_temperature_and_hazard():
    result = run("quench", "1084")
    assert result.returncode == 0
    lines = [line.strip() for line in result.stdout.splitlines()]
    assert any(line.startswith("medium") and "warm oil" in line for line in lines)
    assert any(line.startswith("temp") and "\u00b0C" in line for line in lines)
    assert any(line.startswith("hazard") for line in lines)


@pytest.mark.parametrize("alias", ["[redacted]", "[redacted]", "o-1", "oil hardening"])
def test_quench_aliases_resolve_to_the_same_record(alias):
    canonical = run("quench", "[redacted]")
    assert canonical.returncode == 0
    assert run("quench", alias).stdout == canonical.stdout


def test_quench_alias_with_a_space_resolves():
    assert run("quench", "1084 steel").stdout == run("quench", "1084").stdout
    assert run("quench", "10xx").stdout == run("quench", "1084").stdout


def test_quench_bare_prints_the_example_invocation():
    result = run("quench")
    assert result.returncode == 2
    assert "ironbark quench 1084" in result.stderr
    assert "Traceback" not in result.stderr


def test_quench_unknown_offers_near_matches_and_exits_one():
    result = run("quench", "1085")
    assert result.returncode == 1
    assert "1085 is not in the alloy table" in result.stderr
    near = [line for line in result.stderr.splitlines() if line.startswith("near matches:")]
    assert len(near) == 1
    assert len(near[0].split(",")) <= 3


def test_quench_unknown_without_matches_lists_the_documented_alloys():
    result = run("quench", "unobtainium")
    assert result.returncode == 1
    assert "unobtainium is not in the alloy table" in result.stderr
    assert "1084" in result.stderr and "440C" in result.stderr
    assert "Traceback" not in result.stderr


# --------------------------------------------------------------------------- #
# strike
# --------------------------------------------------------------------------- #
def test_strike_prints_window_header_and_numbered_passes():
    result = run("strike", "knife-blank")
    assert result.returncode == 0
    out = result.stdout
    assert "950\u20131100 \u00b0C" in out
    assert "forging window" in out
    for number in range(1, 6):
        assert f"{number:>4}  " in out
    assert "flat" in out and "cross-peen" in out and "peen" in out
    assert "tang, rear third" in out
    assert "draw toward the tip" in out


@pytest.mark.parametrize("nickname", ["kb", "knife blank", "KNIFE-BLANK"])
def test_strike_alias_resolves_to_the_same_order(nickname):
    canonical = run("strike", "knife-blank")
    assert canonical.returncode == 0
    assert run("strike", nickname).stdout == canonical.stdout


def test_strike_bare_prints_the_example_invocation():
    result = run("strike")
    assert result.returncode == 2
    assert "ironbark strike knife-blank" in result.stderr
    assert "Traceback" not in result.stderr


def test_strike_unknown_exits_one_with_near_matches():
    result = run("strike", "knif")
    assert result.returncode == 1
    assert "not in the billet table" in result.stderr
    assert "knife-blank" in result.stderr


# --------------------------------------------------------------------------- #
# Whole-surface guarantees
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "arguments",
    [
        ("heat", "hot"),
        ("heat", "5000"),
        ("quench",),
        ("strike",),
        ("frobnicate",),
        ("quench", "unobtainium"),
        ("strike", "unobtainium"),
    ],
)
def test_no_failure_path_ever_prints_a_traceback(arguments):
    result = run(*arguments)
    assert result.returncode != 0
    combined = result.stdout + result.stderr
    assert "Traceback" not in combined
    assert "Error" not in combined


def test_output_is_byte_for_byte_deterministic():
    assert run("heat", "940").stdout == run("heat", "940").stdout
    assert run("strike", "leaf").stdout == run("strike", "leaf").stdout


def test_results_go_to_stdout_and_errors_to_stderr():
    assert run("quench", "A2").stderr == ""
    failure = run("quench", "nope")
    assert failure.stdout == ""
    assert failure.stderr


def test_output_carries_the_celsius_token():
    assert "\u00b0C" in run("heat", "820").stdout
    assert "\u00b0C" in run("strike", "leaf").stdout
