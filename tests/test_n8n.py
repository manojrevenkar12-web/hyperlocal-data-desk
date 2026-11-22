import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_the_workflow_runs_ingest_and_routes_quarantines_to_the_data_desk():
    wf = json.loads((ROOT / "n8n/workflow.json").read_text())
    names = {n["name"] for n in wf["nodes"]}
    for a, outs in wf["connections"].items():
        assert a in names
        for branch in outs["main"]:
            for c in branch:
                assert c["node"] in names
    cmd = next(n for n in wf["nodes"] if n["type"].endswith("executeCommand"))["parameters"]["command"]
    assert "ingest --source" in cmd
    ids = {s["id"] for s in json.loads((ROOT / "config/sources.json").read_text())["sources"]}
    code = next(n for n in wf["nodes"] if n["name"] == "Quellen")["parameters"]["jsCode"]
    assert all(f"'{i}'" in code for i in ids)
