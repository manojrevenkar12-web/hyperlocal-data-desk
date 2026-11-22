import json
from pathlib import Path

import pytest

from desk.checks import CheckSettings, blocking_failures, check_release
from desk.domain import Gebietsstand, Municipality
from desk.sources import ParseError, SourceSpec, parse

ROOT = Path(__file__).resolve().parents[1]
SPECS = {s["id"]: SourceSpec.from_dict(s) for s in json.loads((ROOT / "config/sources.json").read_text())["sources"]}
GEB = Gebietsstand({a: Municipality(a, a, 1000, 0, 0) for a in ["08115001", "08115002", "08116001"]})


def csv(unit="Anzahl", rows=None, header="Gemeindeschlüssel;Gemeinde;Genehmigte Wohnungen"):
    rows = rows or ["08115001;A;12", "08115002;B;.", "08115;Böblingen insgesamt;.", "08116001;C;1.204"]
    return "\n".join(
        [
            "Amt",
            "Berichtszeitraum: 3. Quartal 2026",
            f"Einheit: {unit}",
            header,
            *rows,
            "Quelle: Amt",
            "– = nichts vorhanden; . = geheim",
        ]
    ).encode()


def test_csv_with_preamble_signs_district_rows_and_footnotes():
    r = parse(csv(), SPECS["statla-bau"])
    assert [(o.ags, o.value, o.flag) for o in r.rows] == [
        ("08115001", 12.0, None),
        ("08115002", None, "geheim"),
        ("08116001", 1204.0, None),
    ]
    assert r.kreis_totals == {"08115": None} and len(r.footnotes) == 2


def test_a_known_unit_is_converted_and_an_unknown_one_refused():
    r = parse(csv("1.000", ["08115001;A;0,012", "08115002;B;0,003", "08116001;C;1,204"]), SPECS["statla-bau"])
    assert [o.value for o in r.rows] == [12.0, 3.0, 1204.0]
    with pytest.raises(ParseError, match="unit"):
        parse(csv("in Tsd."), SPECS["statla-bau"])


def test_columns_are_found_by_name_not_position():
    r = parse(
        csv(
            rows=["08115001;A;5;12", "08115002;B;5;3", "08116001;C;1;7"],
            header="Gemeindeschlüssel;Gemeinde;Vorquartal;Genehmigte Wohnungen",
        ),
        SPECS["statla-bau"],
    )
    assert [o.value for o in r.rows] == [12.0, 3.0, 7.0]


def test_json_and_html_adapters():
    doc = {
        "meta": {"zeitraum": "2026Q3", "einheit": "Anzahl"},
        "daten": [
            {"ags": "08115001", "wert": 4},
            {"ags": "08115002", "wert": None, "kennzeichen": "."},
            {"ags": "08116001", "wert": 9},
        ],
    }
    r = parse(json.dumps(doc).encode(), SPECS["geburten-api"])
    assert [o.value for o in r.rows] == [4.0, None, 9.0]
    with pytest.raises(ParseError):
        parse(json.dumps({**doc, "daten": [{"ags": "08115001", "anzahl": 4}]}).encode(), SPECS["geburten-api"])
    html = (
        "<table class='statistik'><caption>Gewerbeanmeldungen nach Gemeinden, 3. Quartal 2026 (Anzahl)</caption>"
        "<thead><tr><th>Schlüssel</th><th>Gemeinde</th><th>Anmeldungen</th></tr></thead><tbody>"
        "<tr><td>08115001</td><td>A</td><td>7</td></tr></tbody></table>"
    ).encode()
    assert parse(html, SPECS["gewerbe-presse"]).rows[0].value == 7.0


def test_checks_quarantine_stale_truncated_and_fractional_files():
    s = CheckSettings()
    ok = parse(csv(), SPECS["statla-bau"])
    assert not blocking_failures(check_release(ok, GEB, None, s))
    english = parse(csv(rows=["08115001;A;12", "08115002;B;3", "08116001;C;1,204"]), SPECS["statla-bau"])
    assert [c.name for c in blocking_failures(check_release(english, GEB, None, s))] == ["whole numbers"]
    short = parse(csv(rows=["08115001;A;12"]), SPECS["statla-bau"])
    assert [c.name for c in blocking_failures(check_release(short, GEB, None, s))] == ["coverage"]
    many = Gebietsstand({f"08115{i:03d}": Municipality(f"08115{i:03d}", "x", 1000, 0, 0) for i in range(1, 61)})
    rows = [f"08115{i:03d};x;{i}" for i in range(1, 61)]
    stale = parse(csv(rows=rows), SPECS["statla-bau"])
    prev = {o.ags: o.value for o in stale.rows}
    assert [c.name for c in blocking_failures(check_release(stale, many, prev, s))] == ["fresh"]


def test_district_rows_must_add_up():
    r = parse(csv(rows=["08115001;A;12", "08115002;B;3", "08115;Böblingen insgesamt;20", "08116001;C;7"]), SPECS["statla-bau"])
    assert [c.name for c in blocking_failures(check_release(r, GEB, None, CheckSettings()))] == ["reconciliation"]
