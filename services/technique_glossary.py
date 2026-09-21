"""Canonical grappling technique names + common ASR mishearings.

Used as hints for the LLM and for offline fuzzy correction when no API key
is configured. Titles of instructionals bias which candidates are preferred
(e.g. a video titled "De La Riva Guard" makes "de la bida" → "de la riva").
"""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Iterable, List, Optional, Tuple

# (canonical display name, aliases / common ASR variants)
TECHNIQUE_ENTRIES: List[Tuple[str, Tuple[str, ...]]] = [
    ("de la riva", ("dela riva", "de la river", "de la bida", "dela bida", "dlr", "della riva")),
    ("reverse de la riva", ("reverse dlr", "rdlr", "reverse dela riva")),
    ("berimbolo", ("beri bolo", "berry bolo", "beribolo", "bear imbolo")),
    ("kiss of the dragon", ("kiss of dragon", "kiss the dragon")),
    ("x-guard", ("x guard", "ex guard", "cross guard")),
    ("butterfly guard", ("butterfly", "butter fly guard")),
    ("half guard", ("halfguard", "half-guard")),
    ("deep half", ("deep half guard", "deep halfguard")),
    ("knee shield", ("knee-shield", "kneeshield")),
    ("zombie guard", ("zombi guard",)),
    ("lasso guard", ("lasso", "laso guard")),
    ("spider guard", ("spider",)),
    ("closed guard", ("full guard",)),
    ("open guard", ()),
    ("side control", ("sidecontrol", "side mount", "hundred kilos")),
    ("north-south", ("north south", "northsouth")),
    ("knee on belly", ("knee on stomach", "kob", "knee-on-belly")),
    ("mount", ("full mount", "mounted")),
    ("technical mount", ("s-mount", "s mount")),
    ("back control", ("the back", "taking the back", "rear mount")),
    ("seatbelt", ("seat belt", "seat-belt")),
    ("rear naked choke", ("rnc", "mata leao", "mata leão", "hadaka jime")),
    ("guillotine", ("guillotine choke", "guillotine")),
    ("anaconda", ("anaconda choke",)),
    ("d'arce", ("darce", "d arce", "darce choke", "brabo", "brabo choke")),
    ("armbar", ("arm bar", "juji gatame", "juji")),
    ("kimura", ("kimura lock", "double wrist lock", "gyaku ude garami")),
    ("americana", ("americana lock", "keylock", "key lock", "ude garami")),
    ("omoplata", ("omo plata", "shoulder lock from guard")),
    ("triangle", ("triangle choke", "sankaku")),
    ("arm triangle", ("head and arm", "kata gatame", "head-and-arm")),
    ("heel hook", ("inside heel hook", "outside heel hook", "heelhook")),
    ("toe hold", ("toehold", "foot lock")),
    ("ankle lock", ("achilles lock", "straight ankle")),
    ("knee bar", ("kneebar", "kneebar")),
    ("wrist lock", ("wristlock",)),
    ("collar choke", ("cross collar", "cross-collar choke")),
    ("ezekiel", ("ezekiel choke", "sode guruma jime")),
    ("bow and arrow", ("bow & arrow", "bow-and-arrow")),
    ("clock choke", ()),
    ("loop choke", ()),
    ("scissor sweep", ("scissors sweep",)),
    ("hip bump sweep", ("hipbump", "hip-bump")),
    ("flower sweep", ("pendulum sweep",)),
    ("tornado pass", ()),
    ("leg drag", ("legdrag",)),
    ("knee cut", ("knee slice", "knee-slice", "knee cut pass")),
    ("stack pass", ("double under pass", "double-unders")),
    ("tomeo", ("tomeo nage", "tomoe nage", "stomach throw")),
    ("single leg", ("single-leg", "single leg takedown")),
    ("double leg", ("double-leg", "double leg takedown")),
    ("arm drag", ("armdrag", "arm-drag")),
    ("underhook", ("under hook",)),
    ("overhook", ("over hook", "whizzer")),
    ("crossface", ("cross face", "cross-face")),
    ("far side underhook", ()),
    ("near side underhook", ()),
    ("frame", ("framing", "frames")),
    ("shrimp", ("hip escape", "shrimping")),
    ("bridge", ("upa", "bridging")),
    ("technical stand-up", ("technical standup", "technical stand up")),
]


def _norm(s: str) -> str:
    s = s.lower().strip()
    s = s.replace("é", "e").replace("á", "a").replace("ã", "a").replace("ó", "o")
    s = re.sub(r"[^a-z0-9\s\-']", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def all_canonical_names() -> List[str]:
    return [name for name, _ in TECHNIQUE_ENTRIES]


def glossary_prompt_block() -> str:
    lines = []
    for name, aliases in TECHNIQUE_ENTRIES:
        if aliases:
            lines.append(f"- {name} (also heard as: {', '.join(aliases)})")
        else:
            lines.append(f"- {name}")
    return "\n".join(lines)


def title_relevant_techniques(title: str) -> List[str]:
    """Techniques whose names/aliases appear (fuzzily) in the instructional title."""
    t = _norm(title)
    if not t:
        return []
    hits: List[str] = []
    for name, aliases in TECHNIQUE_ENTRIES:
        candidates = (name,) + aliases
        for c in candidates:
            cn = _norm(c)
            if len(cn) >= 3 and cn in t:
                hits.append(name)
                break
            if SequenceMatcher(None, cn, t).ratio() >= 0.72 and len(cn) >= 6:
                hits.append(name)
                break
    # de-dupe preserve order
    seen = set()
    out = []
    for h in hits:
        if h not in seen:
            seen.add(h)
            out.append(h)
    return out


def best_match(
    heard: str,
    *,
    prefer: Optional[Iterable[str]] = None,
    threshold: float = 0.88,
) -> Optional[Tuple[str, float]]:
    """Return (canonical, score) for a heard phrase, or None."""
    h = _norm(heard)
    if len(h) < 5:
        return None
    prefer_set = set(prefer or [])

    def score_against(name: str, aliases: Tuple[str, ...]) -> float:
        best_local = 0.0
        for c in (name,) + aliases:
            cn = _norm(c)
            if not cn:
                continue
            if h == cn:
                return 1.0
            # Require similar token count for multi-word names
            if abs(len(h.split()) - len(cn.split())) > 1:
                continue
            if abs(len(h) - len(cn)) > max(4, len(cn) // 3):
                continue
            best_local = max(best_local, SequenceMatcher(None, h, cn).ratio())
        return best_local

    # Exact / strong alias match against any technique
    best: Optional[Tuple[str, float]] = None
    for name, aliases in TECHNIQUE_ENTRIES:
        score = score_against(name, aliases)
        if best is None or score > best[1]:
            best = (name, score)
    if best and best[1] >= threshold:
        return best

    # Title-preferred only: lower bar, but only vs those techniques' aliases
    title_best: Optional[Tuple[str, float]] = None
    for name, aliases in TECHNIQUE_ENTRIES:
        if name not in prefer_set:
            continue
        score = score_against(name, aliases)
        if title_best is None or score > title_best[1]:
            title_best = (name, score)
    if title_best and title_best[1] >= 0.68:
        return title_best
    return None


def suggest_corrections(
    transcript: str,
    *,
    title: str = "",
    max_suggestions: int = 40,
) -> List[dict]:
    """Scan transcript n-grams for likely ASR mistakes vs glossary."""
    prefer = title_relevant_techniques(title)
    words = re.findall(r"[A-Za-zÀ-ÿ']+", transcript)
    suggestions: List[dict] = []
    seen_heard = set()
    covered_spans: List[Tuple[int, int]] = []

    def overlaps(start: int, end: int) -> bool:
        for a, b in covered_spans:
            if start < b and end > a:
                return True
        return False

    for n in (4, 3, 2):
        for i in range(len(words) - n + 1):
            if overlaps(i, i + n):
                continue
            heard = " ".join(words[i : i + n])
            key = _norm(heard)
            if key in seen_heard or len(key) < 5:
                continue
            # Drop leading filler words from the span before matching
            heard_core = re.sub(
                r"^(from|the|a|an|to|into|and|with|our|my)\s+",
                "",
                key,
            )
            if len(heard_core) < 5:
                continue
            match = best_match(heard_core, prefer=prefer)
            if not match:
                continue
            canonical, score = match
            if _norm(canonical) == heard_core:
                # Already correct — no suggestion
                continue
            # Only rewrite if this looks like a name error (not a random phrase)
            # Require that at least one token overlaps loosely with canonical/aliases
            can_tokens = set(_norm(canonical).split())
            heard_tokens = set(heard_core.split())
            if not (can_tokens & heard_tokens) and score < 0.9:
                # Allow title-preferred near-misses without shared tokens (bida vs riva)
                if canonical not in prefer or score < 0.75:
                    continue
            seen_heard.add(key)
            covered_spans.append((i, i + n))
            # Prefer rewriting the core phrase as heard in transcript (preserve casing via original)
            # Use the shortest span that still contains the mishearing when possible
            from_text = heard
            if heard_core != key:
                # rebuild from original words without leading filler token(s)
                lead = len(key.split()) - len(heard_core.split())
                from_text = " ".join(words[i + lead : i + n])
            suggestions.append(
                {
                    "from": from_text,
                    "to": canonical,
                    "score": round(score, 3),
                    "reason": (
                        "title context"
                        if canonical in prefer
                        else "glossary fuzzy match"
                    ),
                }
            )
            if len(suggestions) >= max_suggestions:
                return suggestions
    return suggestions
