"""Tests for title-aware transcript ingest."""

from __future__ import annotations

import asyncio
import json

from fastapi.testclient import TestClient

from main import app
from services.ingest import heuristic_process, process_ingest, save_ingest
from services.technique_glossary import suggest_corrections, title_relevant_techniques


def test_title_pulls_de_la_riva():
    hits = title_relevant_techniques("John Danaher — De La Riva Guard System")
    assert "de la riva" in hits


def test_de_la_bida_corrects_with_title_context():
    transcript = (
        "um so you know from de la bida we insert the hook and then "
        "don't forget to like and subscribe okay so we finish"
    )
    sug = suggest_corrections(
        transcript, title="De La Riva entries from seated open guard"
    )
    assert any(
        s["to"] == "de la riva" and "bida" in s["from"].lower() for s in sug
    )


def test_heuristic_process_strips_filler_and_corrects():
    title = "De La Riva Guard fundamentals"
    transcript = (
        "um you know from de la bida we insert the outside hook. "
        "don't forget to like and subscribe. "
        "okay so keep the knee shield."
    )
    result = asyncio.get_event_loop().run_until_complete(
        process_ingest(title=title, transcript=transcript, api_key=None)
    )
    assert result["mode"] == "heuristic"
    assert "de la riva" in result["cleaned_transcript"].lower()
    assert "de la bida" not in result["cleaned_transcript"].lower()
    assert "subscribe" not in result["cleaned_transcript"].lower()
    assert result["corrections"]


def test_llm_process_with_mock_caller():
    async def fake_llm(**kwargs):
        return {
            "corrections": [
                {"from": "de la bida", "to": "de la riva", "reason": "title"}
            ],
            "removed_segments": ["sponsor pitch"],
            "cleaned_transcript": "From de la riva we insert the outside hook.",
            "concepts": [
                {
                    "name": "DLR hook",
                    "summary": "Outside hook controls posture.",
                    "cues": ["toes pointed out"],
                }
            ],
            "techniques": [
                {
                    "canonical": "de la riva",
                    "aliases_heard": ["de la bida"],
                    "confidence": 0.95,
                }
            ],
            "summary": "Entry details for de la riva guard.",
        }

    result = asyncio.get_event_loop().run_until_complete(
        process_ingest(
            title="De La Riva Guard",
            transcript="um from de la bida we insert the hook",
            api_key="sk-test",
            llm_caller=fake_llm,
        )
    )
    assert result["mode"] == "llm"
    assert result["summary"].startswith("Entry details")
    assert result["concepts"][0]["name"] == "DLR hook"


def test_save_and_list_ingest(tmp_path):
    result = heuristic_process(
        title="De La Riva Guard",
        transcript="from de la bida we insert the hook you know",
    )
    path = save_ingest(result, tmp_path)
    assert path.is_file()
    assert result["id"]
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["id"] == result["id"]
    assert data["title"] == "De La Riva Guard"


def test_ingest_endpoint_heuristic(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    client = TestClient(app)
    res = client.post(
        "/api/ingest",
        json={
            "title": "De La Riva Guard System",
            "transcript": "um so from de la bida we insert the hook. thanks for watching.",
            "save": True,
        },
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["mode"] == "heuristic"
    assert body["id"]
    assert body["saved_path"]
    assert "de la riva" in body["cleaned_transcript"].lower()

    listed = client.get("/api/ingest")
    assert listed.status_code == 200
    assert any(i["id"] == body["id"] for i in listed.json()["items"])

    one = client.get(f"/api/ingest/{body['id']}")
    assert one.status_code == 200
    assert one.json()["id"] == body["id"]


def test_config_masks_openai_key():
    from config import Settings, save_settings

    save_settings(Settings(openai_api_key="sk-secret-value"))

    client = TestClient(app)
    res = client.get("/api/config")
    assert res.status_code == 200
    data = res.json()
    assert data["has_openai_api_key"] is True
    assert "openai_api_key" not in data
    assert "sk-secret" not in res.text
