import json

import boto3
import httpx
from moto import mock_aws

from desk.claude import ClaudeWriter
from desk.notes import lead_facts, write_checked
from desk.publish import datawrapper_chart, publish_datawrapper, publish_s3

FACTS = lead_facts(
    name="Kirchtal",
    kreis_name="Böblingen",
    level="gemeinde",
    unit="genehmigte Wohnungen",
    year=2026,
    quarter=3,
    observed=62,
    expected=20.4,
    population=20_000,
    land_rate=1.1,
    history=[20, 21, 19, 20],
)


def test_claude_drafts_and_the_desk_checks_the_numbers():
    seen = {}

    def handler(req: httpx.Request) -> httpx.Response:
        seen["body"] = json.loads(req.content)
        return httpx.Response(
            200, json={"content": [{"type": "text", "text": "Kirchtal meldet 62 genehmigte Wohnungen, 26 je 1.000 Einwohner."}]}
        )

    w = ClaudeWriter("k", "claude-sonnet-5-5", httpx.Client(transport=httpx.MockTransport(handler)))
    out = write_checked("lead", FACTS, w)
    assert seen["body"]["model"] == "claude-sonnet-5-5" and "Fakten" in seen["body"]["messages"][0]["content"]
    assert out.source == "template" and any("26" in p and "verworfen" in p for p in out.problems)  # 26 per 1,000 is made up


def test_datawrapper_chart_create_upload_publish():
    calls = []

    def handler(req: httpx.Request) -> httpx.Response:
        calls.append((req.method, req.url.path))
        return httpx.Response(201 if req.url.path.endswith("/charts") else 200, json={"id": "aB3xY"})

    rows = [{"ags": "08115001", "name": "A", "rate": 1.25, "lead": True}, {"ags": "08115002", "name": "B", "rate": None}]
    payload = datawrapper_chart("Wohnungsbau", "Genehmigte Wohnungen", "3. Quartal 2026", rows, "Statistisches Landesamt")
    assert "Wert geheim" in payload["csv"] and "1 Gemeinden" in payload["chart"]["metadata"]["annotate"]["notes"]
    cid = publish_datawrapper(payload, "t", httpx.Client(transport=httpx.MockTransport(handler)))
    assert cid == "aB3xY" and [m for m, _ in calls] == ["POST", "PUT", "POST"]


@mock_aws
def test_s3_publish_sets_types_and_short_caching():
    s3 = boto3.client("s3", region_name="eu-central-1")
    s3.create_bucket(Bucket="interaktiv", CreateBucketConfiguration={"LocationConstraint": "eu-central-1"})
    keys = publish_s3({"leads.json": {"a": 1}, "gemeinden.geojson": b"{}"}, "interaktiv", "wohnungsbau/2026q3", s3)
    head = s3.head_object(Bucket="interaktiv", Key=keys[1])
    assert head["ContentType"] == "application/json" and head["CacheControl"] == "public, max-age=300"
