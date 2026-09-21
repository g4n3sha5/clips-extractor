"""Instructional transcript ingest: title-aware name fix, cleanup, summarize, save."""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import httpx

from services.technique_glossary import (
    glossary_prompt_block,
    suggest_corrections,
    title_relevant_techniques,
)

FILLER_PATTERNS = [
    re.compile(p, re.I)
    for p in (
        r"\bdon'?t forget to like( and subscribe)?\b",
        r"\bdon'?t forget to (subscribe|comment)\b",
        r"\bhit the (like|bell|subscribe)( button)?\b",
        r"\bthanks for watching\b",
        r"\bsee you (in the )?next (one|video)\b",
        r"\bcheck out my (other|patreon|sponsor)\b",
        r"\bthis video is sponsored by\b",
        r"\buse (promo )?code\b",
        r"\b(um+|uh+|erm+)\b",
        r"\byou know\b",
        r"\bkind of\b",
        r"\bsort of\b",
        r"\bbasically\b",
        r"\bi mean\b",
        r"\bright\?\b",
        r"\bok(ay)? so\b",
        r"\balright so\b",
        r"\blet'?s see\b",
        r"\bas you can see\b",
    )
]

SYSTEM_PROMPT = """You are an expert Brazilian Jiu-Jitsu / MMA grappling coach and editor.
You clean raw instructional transcripts for a technique knowledge base.

Rules:
1. TITLE CONTEXT IS AUTHORITATIVE for technique naming. If the title says
   "De La Riva" and the transcript says "de la bida" / "dela river" / similar,
   correct to "de la riva". Prefer names implied by the title over wild guesses.
2. Fix other common grappling ASR errors using the glossary and martial-arts sense.
3. Strip filler speech, sponsorships, channel CTAs, and empty "alright so / you know" chatter.
4. Keep instructional substance: grips, frames, angles, sequences, pitfalls, counters.
5. Extract the most important concepts and map heard names to canonical technique names.
6. Respond with ONLY valid JSON matching the schema. No markdown fences.
"""


def _slug(title: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", (title or "ingest").strip().lower()).strip("-")
    return (s[:60] or "ingest")


def apply_corrections(text: str, corrections: List[dict]) -> str:
    """Apply from→to replacements (longest first, case-insensitive)."""
    out = text
    ordered = sorted(corrections, key=lambda c: len(c.get("from") or ""), reverse=True)
    for c in ordered:
        src = (c.get("from") or "").strip()
        dst = (c.get("to") or "").strip()
        if not src or not dst:
            continue
        out = re.sub(re.escape(src), dst, out, flags=re.IGNORECASE)
    return out


def strip_fillers(text: str) -> tuple[str, List[str]]:
    removed: List[str] = []
    out = text
    for pat in FILLER_PATTERNS:
        for m in pat.finditer(out):
            removed.append(m.group(0))
        out = pat.sub(" ", out)
    out = re.sub(r"[ \t]{2,}", " ", out)
    out = re.sub(r"\s*\.(\s*\.)+", ".", out)
    out = re.sub(r"\n{3,}", "\n\n", out)
    return out.strip(), removed[:50]


def heuristic_process(
    *,
    title: str,
    transcript: str,
    source_url: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
) -> Dict[str, Any]:
    """Offline path: glossary + filler strip when no LLM key is set."""
    corrections = suggest_corrections(transcript, title=title)
    cleaned = apply_corrections(transcript, corrections)
    cleaned, removed = strip_fillers(cleaned)
    prefer = title_relevant_techniques(title)
    techniques = []
    for c in corrections:
        techniques.append(
            {
                "canonical": c["to"],
                "aliases_heard": [c["from"]],
                "confidence": c.get("score", 0.8),
            }
        )
    for name in prefer:
        if not any(t["canonical"] == name for t in techniques):
            techniques.append(
                {"canonical": name, "aliases_heard": [], "confidence": 0.9}
            )
    concepts = []
    if prefer:
        for name in prefer:
            concepts.append(
                {
                    "name": name,
                    "summary": f"Central topic inferred from instructional title “{title.strip()}”.",
                    "cues": [],
                }
            )
    summary_bits = []
    if prefer:
        summary_bits.append(
            "Focus: " + ", ".join(prefer) + "."
        )
    if corrections:
        summary_bits.append(
            f"Corrected {len(corrections)} likely ASR name error(s)."
        )
    summary_bits.append("Processed offline (no LLM) — set openai_api_key for richer summaries.")
    return {
        "id": "",
        "title": title.strip(),
        "source_url": source_url,
        "start": start,
        "end": end,
        "mode": "heuristic",
        "title_techniques": prefer,
        "corrections": corrections,
        "removed_fillers": removed,
        "cleaned_transcript": cleaned,
        "concepts": concepts,
        "techniques": techniques,
        "summary": " ".join(summary_bits),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def _build_user_prompt(*, title: str, transcript: str) -> str:
    prefer = title_relevant_techniques(title)
    prefer_line = ", ".join(prefer) if prefer else "(none detected — infer carefully)"
    return f"""Instructional title (authoritative context):
{title.strip()}

Techniques likely implied by the title:
{prefer_line}

Glossary of common names / ASR variants:
{glossary_prompt_block()}

Raw transcript:
---
{transcript.strip()}
---

Return JSON with this exact shape:
{{
  "corrections": [{{"from": "...", "to": "...", "reason": "..."}}],
  "removed_segments": ["short note of what was dropped (sponsors, filler, etc.)"],
  "cleaned_transcript": "full cleaned transcript with corrected names, no filler",
  "concepts": [{{"name": "...", "summary": "1-3 sentences", "cues": ["key detail"]}}],
  "techniques": [{{"canonical": "...", "aliases_heard": ["..."], "confidence": 0.0}}],
  "summary": "3-6 sentence overview of the most important teaching points"
}}
"""


async def call_openai_json(
    *,
    api_key: str,
    base_url: str,
    model: str,
    system: str,
    user: str,
    timeout: float = 120.0,
) -> Dict[str, Any]:
    url = base_url.rstrip("/") + "/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    async with httpx.AsyncClient(timeout=timeout) as client:
        res = await client.post(url, headers=headers, json=payload)
        res.raise_for_status()
        data = res.json()
    content = data["choices"][0]["message"]["content"]
    if isinstance(content, list):
        # Some providers return content parts
        content = "".join(
            part.get("text", "") if isinstance(part, dict) else str(part)
            for part in content
        )
    content = content.strip()
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\s*", "", content)
        content = re.sub(r"\s*```$", "", content)
    return json.loads(content)


async def llm_process(
    *,
    title: str,
    transcript: str,
    api_key: str,
    base_url: str,
    model: str,
    source_url: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    llm_caller: Optional[Callable[..., Any]] = None,
) -> Dict[str, Any]:
    caller = llm_caller or call_openai_json
    raw = await caller(
        api_key=api_key,
        base_url=base_url,
        model=model,
        system=SYSTEM_PROMPT,
        user=_build_user_prompt(title=title, transcript=transcript),
    )
    prefer = title_relevant_techniques(title)
    corrections = raw.get("corrections") or []
    # Ensure title-biased glossary suggestions aren't lost if the model misses them
    for sug in suggest_corrections(transcript, title=title):
        if not any(
            _norm_simple(c.get("from")) == _norm_simple(sug["from"])
            for c in corrections
            if isinstance(c, dict)
        ):
            corrections.append(
                {"from": sug["from"], "to": sug["to"], "reason": sug["reason"]}
            )

    cleaned = (raw.get("cleaned_transcript") or "").strip()
    if not cleaned:
        cleaned = apply_corrections(transcript, corrections)
        cleaned, _ = strip_fillers(cleaned)

    return {
        "id": "",
        "title": title.strip(),
        "source_url": source_url,
        "start": start,
        "end": end,
        "mode": "llm",
        "model": model,
        "title_techniques": prefer,
        "corrections": corrections,
        "removed_fillers": raw.get("removed_segments") or [],
        "cleaned_transcript": cleaned,
        "concepts": raw.get("concepts") or [],
        "techniques": raw.get("techniques") or [],
        "summary": (raw.get("summary") or "").strip(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def _norm_simple(s: Optional[str]) -> str:
    return re.sub(r"\s+", " ", (s or "").lower().strip())


async def process_ingest(
    *,
    title: str,
    transcript: str,
    api_key: Optional[str] = None,
    base_url: str = "https://api.openai.com/v1",
    model: str = "gpt-4o-mini",
    source_url: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    llm_caller: Optional[Callable[..., Any]] = None,
) -> Dict[str, Any]:
    title = (title or "").strip()
    transcript = (transcript or "").strip()
    if not title:
        raise ValueError("title is required — it anchors technique-name corrections")
    if not transcript:
        raise ValueError("transcript is required")
    if api_key:
        return await llm_process(
            title=title,
            transcript=transcript,
            api_key=api_key,
            base_url=base_url,
            model=model,
            source_url=source_url,
            start=start,
            end=end,
            llm_caller=llm_caller,
        )
    return heuristic_process(
        title=title,
        transcript=transcript,
        source_url=source_url,
        start=start,
        end=end,
    )


def save_ingest(result: Dict[str, Any], ingest_dir: Path) -> Path:
    ingest_dir.mkdir(parents=True, exist_ok=True)
    ingest_id = result.get("id") or f"{_slug(result.get('title', ''))}-{uuid.uuid4().hex[:8]}"
    result["id"] = ingest_id
    path = ingest_dir / f"{ingest_id}.json"
    path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def list_ingests(ingest_dir: Path) -> List[Dict[str, Any]]:
    if not ingest_dir.is_dir():
        return []
    items: List[Dict[str, Any]] = []
    for path in sorted(ingest_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        items.append(
            {
                "id": data.get("id") or path.stem,
                "title": data.get("title"),
                "mode": data.get("mode"),
                "summary": data.get("summary"),
                "created_at": data.get("created_at"),
                "path": str(path),
            }
        )
    return items


def load_ingest(ingest_dir: Path, ingest_id: str) -> Optional[Dict[str, Any]]:
    # Prevent path traversal
    safe = Path(ingest_id).name
    if safe != ingest_id or ".." in ingest_id:
        return None
    path = ingest_dir / f"{safe}.json"
    if not path.is_file():
        # allow id without matching filename stem edge cases
        for p in ingest_dir.glob("*.json") if ingest_dir.is_dir() else []:
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if data.get("id") == ingest_id:
                return data
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
