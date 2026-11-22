import json
import shutil
from pathlib import Path

import pytest

from lab.play import load_designs, play
from lab.score import score
from lab.study import LockedError, study
from world import generate, load_config

ROOT = Path(__file__).resolve().parents[1]
LAB = json.loads((ROOT / "config/lab.json").read_text())


def imports(pkg: str) -> set[str]:
    out = set()
    for f in (ROOT / "src" / pkg).rglob("*.py"):
        for line in f.read_text().splitlines():
            if line.startswith(("from ", "import ")):
                out.add(line.split()[1].split(".")[0])
    return out


def test_the_product_never_imports_the_world_or_the_lab():
    assert not imports("desk") & {"world", "lab"}


def test_the_world_reads_only_the_vocabulary_and_never_the_desks_settings():
    src = "\n".join(f.read_text() for f in (ROOT / "src/world").rglob("*.py"))
    for name in ["sources.json", "desk.json", "designs.json", "gates.json", "lab.json"]:
        assert name not in src
    for mod in ["desk.pipeline", "desk.leads", "desk.checks", "desk.sources", "desk.store"]:
        assert f"from {mod}" not in src


def test_same_seed_same_world_and_same_outcome():
    a, b = generate(load_config("dev"), 4), generate(load_config("dev"), 4)
    assert [r.raw for r in a.releases] == [r.raw for r in b.releases]
    d = next(x for x in load_designs(ROOT) if x.name == "desk")
    assert score(a, play(ROOT, a, d, LAB), LAB) == score(b, play(ROOT, b, d, LAB), LAB)


def test_every_design_meets_the_same_files():
    w = generate({**load_config("dev"), "quarters": 7}, 2)
    raws = [r.raw for r in w.releases]
    for d in load_designs(ROOT)[:3]:
        play(ROOT, w, d, LAB)
        assert [r.raw for r in w.releases] == raws


def test_the_held_out_study_runs_once(tmp_path):
    shutil.copytree(ROOT / "config", tmp_path / "config")
    (tmp_path / "reports").mkdir()
    (tmp_path / "reports/heldout.lock").write_text("ran")
    with pytest.raises(LockedError):
        study(tmp_path, "heldout")
