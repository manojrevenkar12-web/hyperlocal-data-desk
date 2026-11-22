"""Claude as the writer of lead notes in production. It only drafts: write_checked() in notes.py checks every number
against the facts before a draft is used, exactly as in the lab with the stand-in writer.
"""

from __future__ import annotations

import json

import httpx

from .notes import Facts

SYSTEM = (
    "Du schreibst kurze, nüchterne Recherchehinweise für die Lokalredaktion einer Tageszeitung in Baden-Württemberg. "
    "Verwende nur die Zahlen aus den Fakten, im deutschen Format (1.234,5), keine anderen. Keine Wertung, keine Vermutung "
    "über Ursachen. Höchstens drei Sätze."
)


class ClaudeWriter:
    def __init__(self, api_key: str, model: str, client: httpx.Client | None = None, base_url: str = "https://api.anthropic.com") -> None:
        self.api_key = api_key
        self.model = model
        self.client = client or httpx.Client(timeout=30)
        self.base_url = base_url

    def draft(self, kind: str, facts: Facts) -> str:
        body = {
            "model": self.model,
            "max_tokens": 400,
            "system": SYSTEM,
            "messages": [{"role": "user", "content": f"Art: {kind}\nFakten (JSON):\n{json.dumps(facts, ensure_ascii=False, default=str)}"}],
        }
        r = self.client.post(
            f"{self.base_url}/v1/messages",
            headers={"x-api-key": self.api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json=body,
        )
        r.raise_for_status()
        parts = r.json().get("content", [])
        return "".join(p.get("text", "") for p in parts if p.get("type") == "text").strip()
