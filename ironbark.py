#!/usr/bin/env python3
"""IronBark - blacksmith shop reference for heat colour, quench medium and strike order.

Three lookups, one file, standard library only, no network and no stored state:

    ironbark heat 780            nearest documented heat colour band
    ironbark quench 1084         quench medium, target medium temperature, hazard
    ironbark strike knife-blank  numbered hammer strike order for a billet

Exit codes: 0 success, 1 unknown alloy/billet, 2 usage failure.
"""

from __future__ import annotations

import argparse
import math
import os
import sys
import textwrap
from dataclasses import dataclass
from difflib import get_close_matches
from typing import Callable, Final, Sequence

PROG: Final = "ironbark"
VERSION: Final = "1.0.0"

HEAT_MIN_C: Final = 200
HEAT_MAX_C: Final = 1400
TEMP_RANGE_TEXT: Final = f"{HEAT_MIN_C}\u2013{HEAT_MAX_C} \u00b0C"

EXIT_OK: Final = 0
EXIT_UNKNOWN_RECORD: Final = 1
EXIT_USAGE: Final = 2

DRAW_WIDTH: Final = 46


# --------------------------------------------------------------------------- #
# Committed design direction: terminal-dark surface, one accent, system
# monospace, compact aligned columns, box-drawing separators. The geometry
# fields below are consumed by every renderer; the colour fields are the
# committed palette (documented in README.md) and stay unused by the plain-text
# output, which is ANSI-free so two runs compare byte-for-byte.
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Theme:
    accent: str
    accent_oklch: str
    surface: str
    surface_alt: str
    ink: str
    ink_muted: str
    rule: str
    font: str
    rule_char: str
    rule_width: int
    label_width: int
    indent: str
    bullet: str


THEME: Final = Theme(
    accent="#008f93",
    accent_oklch="oklch(0.58 0.12 197)",
    surface="#0e1417",
    surface_alt="#151d21",
    ink="#e8eef1",
    ink_muted="#9fb0b7",
    rule="#2c3a40",
    font="system monospace",
    rule_char="\u2500",
    rule_width=72,
    label_width=8,
    indent="  ",
    bullet="\u00b7",
)


# --------------------------------------------------------------------------- #
# Record shapes.
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class HeatBand:
    min_c: int
    max_c: int
    name: str
    hex: str
    forging_note: str

    @property
    def span(self) -> str:
        return f"{self.min_c}\u2013{self.max_c} \u00b0C"

    def contains(self, temp_c: int) -> bool:
        return self.min_c <= temp_c <= self.max_c

    def distance(self, temp_c: int) -> int:
        """How far temp_c sits outside the band; 0 when it falls inside it."""
        if temp_c < self.min_c:
            return self.min_c - temp_c
        if temp_c > self.max_c:
            return temp_c - self.max_c
        return 0


@dataclass(frozen=True)
class Alloy:
    name: str
    aliases: tuple[str, ...]
    family: str
    quench_medium: str
    medium_temp_c: str
    hazard_note: str


@dataclass(frozen=True)
class StrikeStep:
    face: str
    zone: str
    draw: str


@dataclass(frozen=True)
class Billet:
    name: str
    aliases: tuple[str, ...]
    stock_section: str
    temp_window_c: str
    passes: tuple[StrikeStep, ...]


# --------------------------------------------------------------------------- #
# Reference tables - a shop reference table, not a laboratory specification.
# Bands are deliberately non-contiguous: a temperature that lands in a gap is
# answered with the nearest band and that band's span.
# --------------------------------------------------------------------------- #
HEAT_BANDS: Final[tuple[HeatBand, ...]] = (
    HeatBand(200, 240, "light straw", "#EFE3B0",
             "temper colour on polished tool steel, not forging heat"),
    HeatBand(250, 290, "dark straw", "#D8B65C",
             "temper colour for chisels and plane irons; the steel is spring-tempered here"),
    HeatBand(300, 340, "brown", "#A8703A",
             "temper colour for springs and slim edges; keep the heat even across the part"),
    HeatBand(350, 395, "purple", "#7A4A72",
             "last temper colour before the steel goes grey; read it in shadow"),
    HeatBand(405, 470, "dark blue", "#2F4A78",
             "temper colour for saw plate and thin springs; there is no red glow yet"),
    HeatBand(480, 540, "grey blue", "#5A7286",
             "temper colour for high-carbon edges; most shops are too bright to read it"),
    HeatBand(550, 620, "faint red", "#6E1810",
             "first visible red in dim shop light; read it in shadow, never in daylight"),
    HeatBand(630, 700, "cherry red", "#A8221C",
             "scale starts to run; drawing heat for small sections only"),
    HeatBand(710, 800, "full cherry red", "#C7311B",
             "normalising and straightening heat for knife-thin stock"),
    HeatBand(810, 900, "bright cherry red", "#DE4A17",
             "general forging heat for carbon steel; the hammer moves steel freely"),
    HeatBand(910, 1010, "orange", "#F26A16",
             "forging heat for heavier sections; scale forms fast, brush it off"),
    HeatBand(1020, 1120, "yellow orange", "#FF8C1A",
             "upper forging heat; stop before the steel sparks or burns"),
    HeatBand(1130, 1210, "light yellow", "#FFC12E",
             "top of the forging window for most carbon steels"),
    HeatBand(1225, 1245, "lemon yellow", "#FFDB63",
             "forge-welding heat for thin stock; carbon loss starts here"),
    HeatBand(1265, 1330, "white yellow", "#FFF0A8",
             "forge-welding heat; flux and work fast, the window is short"),
    HeatBand(1345, 1400, "white", "#FFF9EC",
             "welding heat at the top of the table; the steel sparks and burns quickly"),
)


ALLOYS: Final[tuple[Alloy, ...]] = (
    Alloy("1084", ("10xx", "1084 steel", "1084 carbon", "ten eighty four"), "carbon",
          "warm oil, agitated", "55\u201365 \u00b0C",
          "warm oil can flash \u2014 no open flame or hot scale near the quench tank"),
    Alloy("1095", ("10-95", "1095 steel", "ten ninety five"), "carbon",
          "fast oil, agitated", "50\u201360 \u00b0C",
          "water will crack a thin 1095 edge \u2014 fast oil first, water only for heavy sections"),
    Alloy("[redacted]", ("o-1", "[redacted]", "oil hardening", "oil-hardening"), "tool",
          "warm oil, agitated", "50\u201360 \u00b0C",
          "warm oil can flash \u2014 lid the tank before the next heat comes out"),
    Alloy("W1", ("w-1", "w1", "water hardening", "water-hardening"), "tool",
          "water, 20\u201325 \u00b0C", "20\u201325 \u00b0C",
          "water warps thin sections \u2014 keep the section above 3 mm or use fast oil"),
    Alloy("A2", ("a-2", "a2", "air hardening", "air-hardening"), "tool",
          "still air, fan for heavy sections", "20\u201325 \u00b0C room air",
          "never oil-quench A2 \u2014 it is an air-hardening steel and will crack"),
    Alloy("D2", ("d-2", "d2", "high chrome", "high-chrome"), "tool",
          "forced air, oil for sections over 25 mm", "20\u201325 \u00b0C air",
          "temper D2 within the hour \u2014 hard, cold D2 cracks on the bench"),
    Alloy("5160", ("51-60", "5160 steel", "spring steel"), "spring",
          "warm oil, agitated", "50\u201360 \u00b0C",
          "warm oil can flash \u2014 straighten 5160 before it goes cold, not after"),
    Alloy("4140", ("41-40", "4140 steel", "chrome moly", "chrome-moly"), "tool",
          "warm oil, agitated", "50\u201370 \u00b0C",
          "oil smoke is normal; if the tank flames, lid it and step back"),
    Alloy("15N20", ("15-n-20", "15n20 steel", "banding steel"), "carbon",
          "warm oil, agitated", "55\u201365 \u00b0C",
          "thin damascus stock warps in oil \u2014 quench point down, straight down"),
    Alloy("440C", ("440-c", "440 c", "stainless 440c"), "stainless",
          "still air plate quench", "20\u201325 \u00b0C air",
          "440C needs a soak a plain forge colour cannot prove \u2014 read the hazard before starting"),
)


BILLETS: Final[tuple[Billet, ...]] = (
    Billet(
        "knife-blank",
        ("kb", "knife blank", "blade blank", "blade"),
        "25 x 5 mm flat bar",
        "950\u20131100 \u00b0C",
        (
            StrikeStep("flat", "tang, rear third", "draw the tang out while the steel is yellow"),
            StrikeStep("flat", "spine side, mid section", "draw toward the tip, keep the edge cool"),
            StrikeStep("cross-peen", "mid section, both faces", "spread the width; stop before the edge thins"),
            StrikeStep("peen", "edge side, front third", "move steel into the tip, never away from it"),
            StrikeStep("flat", "full blank", "straighten with planishing blows, edge down"),
        ),
    ),
    Billet(
        "tong-blank",
        ("tb", "tongs", "tong blank", "reign"),
        "12 mm square bar",
        "1000\u20131150 \u00b0C",
        (
            StrikeStep("flat", "jaw end, first 40 mm", "draw the jaw out square and even"),
            StrikeStep("cross-peen", "jaw shoulder", "step the shoulder down toward the boss"),
            StrikeStep("flat", "boss, both faces", "upset the boss thick before the rivet hole"),
            StrikeStep("peen", "reigns, rear half", "draw the reigns back, keep them in line"),
            StrikeStep("flat", "full tong", "true both jaws together while the steel is yellow"),
        ),
    ),
    Billet(
        "rr-spike",
        ("rrspike", "rr spike", "railroad spike", "spike"),
        "140 lb railroad spike",
        "1000\u20131150 \u00b0C",
        (
            StrikeStep("flat", "head, first 30 mm", "draw the head down into the blade"),
            StrikeStep("cross-peen", "blade half, both faces", "spread the width, keep the spine thick"),
            StrikeStep("flat", "blade half", "straighten the spine line before the steel cools"),
            StrikeStep("peen", "tip", "push the tip forward with light peen blows"),
            StrikeStep("flat", "full piece", "planish flat, then quench point down"),
        ),
    ),
    Billet(
        "leaf",
        ("leaf blank", "decorative leaf", "leaf key"),
        "10 mm round bar",
        "950\u20131100 \u00b0C",
        (
            StrikeStep("flat", "stem, rear half", "draw the stem to a taper first"),
            StrikeStep("cross-peen", "leaf body", "spread the body wide, thin at the edges"),
            StrikeStep("peen", "leaf body, centre line", "cut the centre vein with peen blows"),
            StrikeStep("flat", "leaf edges", "true the edges with light flat blows"),
            StrikeStep("peen", "leaf tip", "pull the tip out, then curl it while hot"),
        ),
    ),
    Billet(
        "chisel-blank",
        ("hc", "chisel", "hot cut", "hot-cut"),
        "18 mm round bar",
        "950\u20131100 \u00b0C",
        (
            StrikeStep("flat", "striking end, rear third", "upset the striking end thick and round"),
            StrikeStep("cross-peen", "cutting end", "draw the cutting end to a wedge"),
            StrikeStep("flat", "cutting end, both faces", "flatten the wedge to a 30 degree angle"),
            StrikeStep("peen", "cutting edge", "thin the very edge, then stop"),
            StrikeStep("flat", "full body", "straighten the body, no bend at the shoulder"),
        ),
    ),
    Billet(
        "bottle-opener",
        ("bo", "bottle opener", "opener"),
        "20 x 5 mm flat bar",
        "950\u20131100 \u00b0C",
        (
            StrikeStep("flat", "handle, rear half", "draw the handle down and round it"),
            StrikeStep("cross-peen", "opener head", "spread the head wide enough for a crown cap"),
            StrikeStep("peen", "opener head, lip side", "cut the lip back with angled peen blows"),
            StrikeStep("flat", "opener lip", "dress the lip square with light flat blows"),
            StrikeStep("flat", "full piece", "straighten, then quench point down"),
        ),
    ),
)


# --------------------------------------------------------------------------- #
# Lookup: one normaliser shared by alloy and billet resolution, so shop
# shorthand behaves identically for both ('o-1' = '[redacted]', 'kb' = 'knife-blank').
# --------------------------------------------------------------------------- #
def normalise(text: str) -> str:
    """Lowercase and drop spaces, hyphens and underscores before comparing."""
    return "".join(character for character in text.strip().lower()
                   if character not in " -_")


def _build_index(records: Sequence[Alloy] | Sequence[Billet]) -> dict[str, object]:
    index: dict[str, object] = {}
    for record in records:
        for token in (record.name, *record.aliases):
            index.setdefault(normalise(token), record)
    return index


ALLOY_INDEX: Final[dict[str, object]] = _build_index(ALLOYS)
BILLET_INDEX: Final[dict[str, object]] = _build_index(BILLETS)


def lookup_alloy(query: str) -> Alloy | None:
    record = ALLOY_INDEX.get(normalise(query))
    return record if isinstance(record, Alloy) else None


def lookup_billet(query: str) -> Billet | None:
    record = BILLET_INDEX.get(normalise(query))
    return record if isinstance(record, Billet) else None


def near_matches(query: str, records: Sequence[Alloy] | Sequence[Billet],
                 limit: int = 3) -> list[str]:
    """Up to `limit` documented names that look like what the user typed."""
    tokens: list[tuple[str, str]] = []
    for record in records:
        tokens.append((normalise(record.name), record.name))
        tokens.extend((normalise(alias), record.name) for alias in record.aliases)
    pool = [token for token, _ in tokens]
    found: list[str] = []
    for token in get_close_matches(normalise(query), pool, n=limit * 4, cutoff=0.5):
        name = next(name for candidate, name in tokens if candidate == token)
        if name not in found:
            found.append(name)
        if len(found) == limit:
            break
    return found


def parse_temperature(raw: str) -> float | None:
    """Parse '800', '800.5', '800 \u00b0C'; return None when it is not a number."""
    text = raw.strip().lower()
    for suffix in ("\u00b0 c", "\u00b0c", "deg c", "degc", "c"):
        if text.endswith(suffix):
            text = text[: -len(suffix)].strip()
            break
    try:
        value = float(text)
    except ValueError:
        return None
    return value if math.isfinite(value) else None


def resolve_band(temp_c: int) -> tuple[HeatBand, bool]:
    """Return the band covering temp_c, or the nearest one; bool = exact cover."""
    for band in HEAT_BANDS:
        if band.contains(temp_c):
            return band, True
    nearest = HEAT_BANDS[0]
    for band in HEAT_BANDS:
        if band.distance(temp_c) < nearest.distance(temp_c):
            nearest = band
    return nearest, False


# --------------------------------------------------------------------------- #
# Rendering: aligned columns, box-drawing rule, one label per line.
# --------------------------------------------------------------------------- #
def _rule(width: int | None = None) -> str:
    return THEME.rule_char * (THEME.rule_width if width is None else width)


def _title(text: str) -> str:
    return f"{PROG} {THEME.bullet} {text}"


def _hanging_indent() -> str:
    return " " * (len(THEME.indent) + THEME.label_width)


def _labelled(label: str, value: str) -> list[str]:
    """One labelled line, wrapped under the value column when it runs long."""
    width = THEME.rule_width - len(THEME.indent) - THEME.label_width
    chunks = textwrap.wrap(value, width=width) or [""]
    lines = [f"{THEME.indent}{label:<{THEME.label_width}}{chunks[0]}"]
    lines.extend(_hanging_indent() + chunk for chunk in chunks[1:])
    return lines


def render_heat(band: HeatBand, temp_c: int, exact: bool) -> str:
    lines = [
        _title(f"heat {temp_c} \u00b0C"),
        _rule(),
        *_labelled("band", band.name),
        *_labelled("swatch", band.hex),
        *_labelled("span", band.span),
    ]
    if not exact:
        offset = band.distance(temp_c)
        side = "above" if temp_c > band.max_c else "below"
        lines.extend(_labelled(
            "fit",
            f"{offset} \u00b0C {side} this band \u2014 nearest of "
            f"{len(HEAT_BANDS)} documented bands",
        ))
    lines.extend(_labelled("note", band.forging_note))
    return "\n".join(lines)


def render_quench(alloy: Alloy) -> str:
    lines = [
        _title(f"quench {alloy.name}"),
        _rule(),
        *_labelled("alloy", f"{alloy.name} \u00b7 {alloy.family} steel"),
        *_labelled("medium", alloy.quench_medium),
        *_labelled("temp", f"medium at {alloy.medium_temp_c}"),
        *_labelled("hazard", alloy.hazard_note),
        *_labelled("aliases", ", ".join(alloy.aliases)),
    ]
    return "\n".join(lines)


def render_strike(billet: Billet) -> str:
    pass_width = max(len("pass"), len(str(len(billet.passes))))
    face_width = max([len("face")] + [len(step.face) for step in billet.passes])
    zone_width = max([len("zone")] + [len(step.zone) for step in billet.passes])
    table_width = (
        len(THEME.indent) + pass_width + 2 + face_width + 2 + zone_width + 2 + DRAW_WIDTH
    )
    lines = [
        _title(f"strike {billet.name}"),
        *_labelled("stock", billet.stock_section),
        *_labelled("window", f"{billet.temp_window_c} forging window"),
        *_labelled("aliases", ", ".join(billet.aliases)),
        _rule(table_width),
        f"{THEME.indent}{'pass':>{pass_width}}  {'face':<{face_width}}  "
        f"{'zone':<{zone_width}}  draw",
        f"{THEME.indent}{_rule(pass_width)}  {_rule(face_width)}  "
        f"{_rule(zone_width)}  {_rule(DRAW_WIDTH)}",
    ]
    hanging = (
        f"{THEME.indent}{' ' * pass_width}  {' ' * face_width}  {' ' * zone_width}  "
    )
    for number, step in enumerate(billet.passes, start=1):
        chunks = textwrap.wrap(step.draw, width=DRAW_WIDTH) or [""]
        lines.append(
            f"{THEME.indent}{number:>{pass_width}}  {step.face:<{face_width}}  "
            f"{step.zone:<{zone_width}}  {chunks[0]}"
        )
        lines.extend(hanging + chunk for chunk in chunks[1:])
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Command summary, shared by the bare invocation and the unknown-command path.
# --------------------------------------------------------------------------- #
COMMAND_SUMMARY: Final[tuple[tuple[str, str, str], ...]] = (
    ("heat <\u00b0C>", "nearest heat colour band, hex, \u00b0C span and forging note",
     f"{PROG} heat 780"),
    ("quench <alloy>", "quench medium, target medium temperature and a hazard note",
     f"{PROG} quench 1084"),
    ("strike <billet>", "numbered hammer strike order with the forging window it assumes",
     f"{PROG} strike knife-blank"),
)
_COMMANDS: Final = frozenset(command.split()[0] for command, _, _ in COMMAND_SUMMARY)

USAGE_EXAMPLES: Final = "\n".join(
    ["worked examples:"]
    + [f"  {example}" for _, _, example in COMMAND_SUMMARY]
    + ["  ironbark heat 1260", "  ironbark quench o-1", "  ironbark strike kb"]
)


def render_usage() -> str:
    column = max(len(command) for command, _, _ in COMMAND_SUMMARY) + 2
    lines = [
        _title("blacksmith shop reference: heat colour, quench medium, strike order"),
        "",
        f"usage: {PROG} <command> <value>",
        "",
    ]
    for command, description, example in COMMAND_SUMMARY:
        lines.append(f"{THEME.indent}{command:<{column}}{description}")
        lines.append(f"{THEME.indent}{' ' * column}example: {example}")
    lines.extend([
        "",
        "lookups ignore case and spacing: 'o-1' = '[redacted]', 'kb' = 'knife-blank'.",
        f"run '{PROG} <command> --help' for one command.",
    ])
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Handlers. Every failure prints one human-readable line - never a traceback.
# --------------------------------------------------------------------------- #
def _fail(message: str, code: int) -> int:
    print(f"{PROG}: {message}", file=sys.stderr)
    return code


def _one_line(raw: str) -> str:
    """Collapse whatever the user typed onto a single line for the error text."""
    return " ".join(raw.split()) or repr(raw)


def _format_number(value: float) -> str:
    return str(int(value)) if value.is_integer() else f"{value:g}"


def run_heat(parts: Sequence[str]) -> int:
    if not parts:
        return _fail(
            f"give a temperature in {TEMP_RANGE_TEXT} \u2014 example: {PROG} heat 780",
            EXIT_USAGE,
        )
    if len(parts) > 1:
        return _fail(f"heat takes one temperature \u2014 example: {PROG} heat 780",
                     EXIT_USAGE)
    raw = parts[0]
    value = parse_temperature(raw)
    if value is None:
        return _fail(
            f"{_one_line(raw)} is not a number \u2014 expected a temperature in "
            f"{TEMP_RANGE_TEXT} (example: {PROG} heat 780)",
            EXIT_USAGE,
        )
    if value < HEAT_MIN_C or value > HEAT_MAX_C:
        return _fail(
            f"{_format_number(value)} \u00b0C is outside the documented range "
            f"{TEMP_RANGE_TEXT} (example: {PROG} heat 780)",
            EXIT_USAGE,
        )
    temp_c = int(math.floor(value + 0.5))
    band, exact = resolve_band(temp_c)
    print(render_heat(band, temp_c, exact))
    return EXIT_OK


def _report_unknown(raw: str, noun: str,
                    records: Sequence[Alloy] | Sequence[Billet]) -> int:
    shown = _one_line(raw)
    print(f"{PROG}: {shown} is not in the {noun} table", file=sys.stderr)
    matches = near_matches(shown, records)
    if matches:
        print(f"near matches: {', '.join(matches)}", file=sys.stderr)
    else:
        documented = ", ".join(record.name for record in records)
        print(f"near matches: none \u2014 documented {noun}s: {documented}",
              file=sys.stderr)
    return EXIT_UNKNOWN_RECORD


def run_quench(parts: Sequence[str]) -> int:
    if not parts:
        return _fail(
            f"give an alloy to look up \u2014 example: {PROG} quench 1084", EXIT_USAGE
        )
    alloy = lookup_alloy(" ".join(parts))
    if alloy is None:
        return _report_unknown(" ".join(parts), "alloy", ALLOYS)
    print(render_quench(alloy))
    return EXIT_OK


def run_strike(parts: Sequence[str]) -> int:
    if not parts:
        return _fail(
            f"give a billet to lay out \u2014 example: {PROG} strike knife-blank",
            EXIT_USAGE,
        )
    billet = lookup_billet(" ".join(parts))
    if billet is None:
        return _report_unknown(" ".join(parts), "billet", BILLETS)
    print(render_strike(billet))
    return EXIT_OK


# --------------------------------------------------------------------------- #
# Command line surface.
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=PROG,
        description=(
            "Blacksmith shop reference: heat colour, quench medium and hammer "
            "strike order."
        ),
        epilog=USAGE_EXAMPLES,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version",
                        version=f"{PROG} {VERSION}")
    commands = parser.add_subparsers(dest="command", metavar="<command>")

    heat = commands.add_parser(
        "heat",
        help=f"nearest heat colour band for a temperature (example: {PROG} heat 780)",
        description=(
            "Nearest documented heat colour band for a temperature in "
            f"{TEMP_RANGE_TEXT}: band name, hex swatch, \u00b0C span and a forging note."
        ),
        epilog=f"example: {PROG} heat 780",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    heat.add_argument("value", nargs="*", metavar="<\u00b0C>",
                      help=f"temperature in \u00b0C, {TEMP_RANGE_TEXT}")
    heat.set_defaults(handler=run_heat)

    quench = commands.add_parser(
        "quench",
        help=f"quench medium for an alloy (example: {PROG} quench 1084)",
        description=(
            "Quench medium, target medium temperature and hazard note for an "
            "alloy. Names ignore case and spacing, and every documented shop "
            "alias resolves."
        ),
        epilog=f"example: {PROG} quench 1084\n         {PROG} quench o-1",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    quench.add_argument("value", nargs="*", metavar="<alloy>",
                        help="alloy name or shop alias, e.g. 1084, O1, o-1")
    quench.set_defaults(handler=run_quench)

    strike = commands.add_parser(
        "strike",
        help=f"numbered strike order for a billet (example: {PROG} strike knife-blank)",
        description=(
            "Numbered hammer strike order for a billet: the forging window it "
            "assumes, then each pass with hammer face, target zone and draw "
            "direction."
        ),
        epilog=f"example: {PROG} strike knife-blank\n         {PROG} strike kb",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    strike.add_argument("value", nargs="*", metavar="<billet>",
                        help="billet name or shop nickname, e.g. knife-blank, kb")
    strike.set_defaults(handler=run_strike)
    return parser


def _configure_output() -> None:
    """Emit UTF-8 whatever the shop shell's locale is: the tables carry \u00b0C."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8")
        except (ValueError, OSError):
            continue  # detached or already-wrapped stream: keep its own encoding


def main(argv: Sequence[str] | None = None) -> int:
    """Run one IronBark command and return its exit code (0, 1 or 2)."""
    _configure_output()
    arguments = list(sys.argv[1:] if argv is None else argv)
    parser = build_parser()
    if not arguments:
        print(render_usage())
        return EXIT_OK
    first = arguments[0]
    if first in ("-h", "--help"):
        parser.print_help()
        return EXIT_OK
    if first == "--version":
        print(f"{PROG} {VERSION}")
        return EXIT_OK
    if first not in _COMMANDS:
        print(f"{PROG}: unknown command {first}", file=sys.stderr)
        print("", file=sys.stderr)
        print(render_usage(), file=sys.stderr)
        return EXIT_USAGE
    parsed = parser.parse_args(arguments)
    handler: Callable[[Sequence[str]], int] = getattr(parsed, "handler")
    return handler(parsed.value)


def run_cli() -> int:
    """Console-script entry point: main() plus a clean exit on a closed pipe."""
    try:
        return main()
    except BrokenPipeError:
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        return EXIT_OK


if __name__ == "__main__":
    sys.exit(run_cli())
