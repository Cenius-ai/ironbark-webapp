"""Unit tests for IronBark's reference tables, normaliser and renderers."""

from __future__ import annotations

import ironbark


def test_normalise_ignores_case_spacing_and_separators():
    assert ironbark.normalise("o-1") == ironbark.normalise("[redacted]") == "[redacted]"
    assert ironbark.normalise("  knife blank ") == "knifeblank"
    assert ironbark.normalise("15_n-20") == "15n20"


def test_heat_bands_are_ordered_non_overlapping_and_cover_the_endpoints():
    bands = ironbark.HEAT_BANDS
    assert bands[0].min_c == ironbark.HEAT_MIN_C
    assert bands[-1].max_c == ironbark.HEAT_MAX_C
    for earlier, later in zip(bands, bands[1:]):
        assert earlier.min_c < earlier.max_c
        assert earlier.max_c < later.min_c
    for band in bands:
        assert band.hex.startswith("#") and len(band.hex) == 7
        assert band.forging_note


def test_every_alloy_name_and_alias_resolves_to_its_own_record():
    assert len(ironbark.ALLOYS) >= 10
    owner: dict[str, object] = {}
    for alloy in ironbark.ALLOYS:
        for token in (alloy.name, *alloy.aliases):
            key = ironbark.normalise(token)
            # two records may never claim the same shop spelling
            assert owner.setdefault(key, alloy) is alloy, (
                f"{token!r} is claimed by two alloys"
            )
            assert ironbark.lookup_alloy(token) is alloy
    assert ironbark.lookup_alloy("does-not-exist") is None


def test_every_billet_name_and_alias_resolves_to_its_own_record():
    assert len(ironbark.BILLETS) >= 6
    owner: dict[str, object] = {}
    for billet in ironbark.BILLETS:
        assert len(billet.passes) >= 3
        for token in (billet.name, *billet.aliases):
            key = ironbark.normalise(token)
            assert owner.setdefault(key, billet) is billet, (
                f"{token!r} is claimed by two billets"
            )
            assert ironbark.lookup_billet(token) is billet
        for step in billet.passes:
            assert step.face and step.zone and step.draw


def test_parse_temperature_accepts_numbers_and_rejects_words():
    assert ironbark.parse_temperature("800") == 800
    assert ironbark.parse_temperature(" 812.5 ") == 812.5
    assert ironbark.parse_temperature("800 \u00b0C") == 800
    assert ironbark.parse_temperature("hot") is None
    assert ironbark.parse_temperature("") is None
    assert ironbark.parse_temperature("nan") is None
    assert ironbark.parse_temperature("inf") is None


def test_resolve_band_handles_edges_and_gaps():
    band, exact = ironbark.resolve_band(200)
    assert exact and band.name == "light straw"
    band, exact = ironbark.resolve_band(1400)
    assert exact and band.name == "white"
    band, exact = ironbark.resolve_band(1260)
    assert not exact and band.name == "white yellow"


def test_near_matches_never_exceeds_the_limit():
    assert len(ironbark.near_matches("108", ironbark.ALLOYS)) <= 3
    assert ironbark.near_matches("unobtainium", ironbark.ALLOYS) == []


def test_every_documented_record_renders_with_its_labels():
    for alloy in ironbark.ALLOYS:
        text = ironbark.render_quench(alloy)
        assert "medium" in text and "temp" in text and "hazard" in text
    for billet in ironbark.BILLETS:
        text = ironbark.render_strike(billet)
        assert billet.temp_window_c in text
        for number in range(1, len(billet.passes) + 1):
            assert f"{number:>4}" in text


def test_main_is_importable_and_returns_exit_codes(capsys):
    assert ironbark.main(["heat", "800"]) == 0
    capsys.readouterr()
    assert ironbark.main(["quench", "unobtainium"]) == 1
    capsys.readouterr()
    assert ironbark.main(["heat", "hot"]) == 2
    capsys.readouterr()
    assert ironbark.main([]) == 0
    capsys.readouterr()
