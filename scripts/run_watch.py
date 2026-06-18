#!/usr/bin/env python3
"""AI deals watch.

V3 hardening notes:
- Uses Gemini Google Search grounding in plain text mode.
- Does NOT combine Google Search tool with response_mime_type/application_json because the API rejects that combination.
- Requests compact JSON inside sentinel markers and validates it locally.
- Keeps every model field short to reduce the risk of truncated JSON.
- Saves raw failed model output for debugging instead of silently losing it.
- Supports DRY_RUN=true to test GitHub Actions without consuming Gemini credits.
- Handles Discord content limits with safe chunking and 429 retry handling.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
HISTORY_DIR = DATA_DIR / "history"
REPORTS_DIR = ROOT / "reports"
PROMPT_FILE = ROOT / "prompts" / "research_prompt.md"

LATEST_JSON = DATA_DIR / "latest.json"
LATEST_MD = REPORTS_DIR / "latest.md"
CHANGES_MD = REPORTS_DIR / "changes.md"
FAILED_RAW_TXT = REPORTS_DIR / "failed_raw_response.txt"

MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
MAX_OFFERS = int(os.getenv("AI_DEALS_MAX_OFFERS", "30"))
GEMINI_MAX_OUTPUT_TOKENS = int(os.getenv("GEMINI_MAX_OUTPUT_TOKENS", "32768"))
DISCORD_CONTENT_LIMIT = 1900  # Discord content max is 2000; keep margin.
DISCORD_SUMMARY_LIMIT = 1850
DISCORD_ATTACH_FULL_REPORT = os.getenv("DISCORD_ATTACH_FULL_REPORT", "true").lower() == "true"
DISCORD_MAX_MESSAGES = int(os.getenv("DISCORD_MAX_MESSAGES", "0"))  # 0 = no silent cap; keep every Discord chunk.

ALLOWED_REGIONS = {"Monde", "Europe", "US-only", "Région limitée", "Non précisé"}


@dataclass
class DiffResult:
    changed: bool
    new_offers: list[dict[str, Any]]
    modified_offers: list[dict[str, Any]]
    removed_offers: list[dict[str, Any]]


# Keep the schema intentionally simple. Nested objects/arrays only, no oneOf/anyOf.
# This is more reliable with Google Search grounding and cheaper to generate than a long prose report.
GEMINI_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "generated_title": {"type": "string"},
        "generated_summary": {"type": "string"},
        "offers": {
            "type": "array",
            "minItems": 1,
            "maxItems": MAX_OFFERS,
            "items": {
                "type": "object",
                "properties": {
                    "rank": {"type": "integer"},
                    "offer": {"type": "string"},
                    "provider": {"type": "string"},
                    "type": {"type": "string"},
                    "region": {
                        "type": "string",
                        "enum": ["Monde", "Europe", "US-only", "Région limitée", "Non précisé"],
                    },
                    "gain": {"type": "string"},
                    "conditions_limits": {"type": "string"},
                    "problems_traps": {"type": "string"},
                    "usage_score": {"type": "integer"},
                    "validity": {"type": "string"},
                    "official_link": {"type": "string"},
                    "community_source": {"type": "string"},
                },
                "required": [
                    "rank",
                    "offer",
                    "provider",
                    "type",
                    "region",
                    "gain",
                    "conditions_limits",
                    "problems_traps",
                    "usage_score",
                    "validity",
                    "official_link",
                    "community_source",
                ],
            },
        },
        "best_real_use": {"type": "array", "items": {"type": "string"}, "maxItems": 5},
        "riskiest_or_unstable": {"type": "array", "items": {"type": "string"}, "maxItems": 5},
        "watchlist": {"type": "array", "items": {"type": "string"}, "maxItems": 5},
        "critical_sources_used": {"type": "array", "items": {"type": "string"}, "maxItems": 15},
    },
    "required": [
        "generated_title",
        "generated_summary",
        "offers",
        "best_real_use",
        "riskiest_or_unstable",
        "watchlist",
        "critical_sources_used",
    ],
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def stable_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def clamp_text(text: str, max_chars: int, default: str = "non précisé") -> str:
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    if not text:
        return default
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip() + "…"


def clean_text(value: Any, default: str = "non précisé", max_chars: int = 300) -> str:
    if value is None:
        return default
    return clamp_text(str(value), max_chars=max_chars, default=default)


def valid_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        return parsed.scheme in {"http", "https"} and bool(parsed.netloc)
    except Exception:
        return False


def offer_id(offer: dict[str, Any]) -> str:
    link = clean_text(offer.get("official_link"), "", max_chars=500)
    provider = clean_text(offer.get("provider"), "", max_chars=160)
    name = clean_text(offer.get("offer"), "", max_chars=160)
    identity = link if valid_url(link) else f"{provider}|{name}"
    return sha256_text(identity.lower())[:16]


def offer_fingerprint(offer: dict[str, Any]) -> str:
    relevant = {
        "offer": clean_text(offer.get("offer"), max_chars=160),
        "provider": clean_text(offer.get("provider"), max_chars=100),
        "type": clean_text(offer.get("type"), max_chars=80),
        "region": clean_text(offer.get("region"), max_chars=40),
        "gain": clean_text(offer.get("gain"), max_chars=220),
        "conditions_limits": clean_text(offer.get("conditions_limits"), max_chars=260),
        "problems_traps": clean_text(offer.get("problems_traps"), max_chars=260),
        "usage_score": offer.get("usage_score"),
        "validity": clean_text(offer.get("validity"), max_chars=80),
        "official_link": clean_text(offer.get("official_link"), max_chars=500),
        "community_source": clean_text(offer.get("community_source"), max_chars=220),
    }
    return sha256_text(stable_json(relevant))[:16]


def safe_int(value: Any, default: int, minimum: int, maximum: int) -> int:
    try:
        number = int(value)
    except Exception:
        number = default
    return max(minimum, min(maximum, number))


def sanitize_offer(raw: dict[str, Any], fallback_rank: int) -> dict[str, Any]:
    score = safe_int(raw.get("usage_score"), default=0, minimum=0, maximum=5)
    rank = safe_int(raw.get("rank"), default=fallback_rank, minimum=1, maximum=999)

    region = clean_text(raw.get("region"), max_chars=40)
    if region not in ALLOWED_REGIONS:
        region = "Non précisé"

    offer = {
        "rank": rank,
        "offer": clean_text(raw.get("offer"), max_chars=120),
        "provider": clean_text(raw.get("provider"), max_chars=80),
        "type": clean_text(raw.get("type"), max_chars=80),
        "region": region,
        "gain": clean_text(raw.get("gain"), max_chars=220),
        "conditions_limits": clean_text(raw.get("conditions_limits"), max_chars=260),
        "problems_traps": clean_text(raw.get("problems_traps"), max_chars=260),
        "usage_score": score,
        "validity": clean_text(raw.get("validity"), max_chars=80),
        "official_link": clean_text(raw.get("official_link"), max_chars=500),
        "community_source": clean_text(raw.get("community_source"), max_chars=220),
    }
    offer["id"] = offer_id(offer)
    offer["fingerprint"] = offer_fingerprint(offer)
    return offer


def as_str_list(value: Any, limit: int, item_max_chars: int = 180) -> list[str]:
    if not isinstance(value, list):
        return []
    output: list[str] = []
    for item in value:
        text = clean_text(item, max_chars=item_max_chars)
        if text != "non précisé":
            output.append(text)
        if len(output) >= limit:
            break
    return output


def normalize_payload(raw: dict[str, Any]) -> dict[str, Any]:
    offers_raw = raw.get("offers") or []
    if not isinstance(offers_raw, list):
        raise ValueError("Le champ 'offers' doit être une liste.")

    offers: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for index, item in enumerate(offers_raw[:MAX_OFFERS], start=1):
        if not isinstance(item, dict):
            continue
        offer = sanitize_offer(item, index)
        if offer["id"] in seen_ids:
            continue
        seen_ids.add(offer["id"])
        offers.append(offer)

    if not offers:
        raise ValueError("Aucune offre exploitable dans la réponse Gemini.")

    offers.sort(key=lambda x: x.get("rank", 999))

    return {
        "generated_at": utc_now(),
        "model": MODEL,
        "generated_title": clean_text(raw.get("generated_title"), "Veille bons plans IA", max_chars=120),
        "generated_summary": clean_text(raw.get("generated_summary"), max_chars=500),
        "offers": offers,
        "best_real_use": as_str_list(raw.get("best_real_use"), 5, 180),
        "riskiest_or_unstable": as_str_list(raw.get("riskiest_or_unstable"), 5, 180),
        "watchlist": as_str_list(raw.get("watchlist"), 5, 180),
        "critical_sources_used": as_str_list(raw.get("critical_sources_used"), 15, 180),
    }


def strip_markdown_fence(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped, flags=re.I)
        stripped = re.sub(r"\s*```$", "", stripped)
    return stripped.strip()


def save_failed_raw_response(text: str, error: Exception) -> None:
    REPORTS_DIR.mkdir(exist_ok=True)
    FAILED_RAW_TXT.write_text(
        "# Gemini raw response parse failure\n\n"
        f"Date: {utc_now()}\n"
        f"Error: {type(error).__name__}: {error}\n\n"
        "--- RAW RESPONSE START ---\n"
        f"{text}\n"
        "--- RAW RESPONSE END ---\n",
        encoding="utf-8",
    )


def extract_json(text: str) -> dict[str, Any]:
    """Extract model JSON from plain-text grounded output.

    Gemini Google Search grounding cannot be combined with response_mime_type="application/json".
    So we ask for compact JSON between sentinel markers and parse it locally.
    """
    stripped = strip_markdown_fence(text)

    # Preferred path: JSON between explicit markers.
    marker_start = "BEGIN_AI_DEALS_JSON"
    marker_end = "END_AI_DEALS_JSON"
    if marker_start in stripped and marker_end in stripped:
        start = stripped.index(marker_start) + len(marker_start)
        end = stripped.rindex(marker_end)
        candidate = stripped[start:end].strip()
    else:
        # Fallback path: whole response is JSON, or JSON object is embedded in text.
        candidate = stripped
        if not candidate.lstrip().startswith("{"):
            start = candidate.find("{")
            end = candidate.rfind("}")
            if start != -1 and end != -1 and end > start:
                candidate = candidate[start : end + 1]

    try:
        data = json.loads(candidate)
    except json.JSONDecodeError as exc:
        # Do not try to invent missing JSON. A truncated JSON must be visible in failed_raw_response.txt.
        raise ValueError(
            f"JSON Gemini invalide ou tronqué: {exc}. "
            "Le script attend un objet JSON complet entre BEGIN_AI_DEALS_JSON et END_AI_DEALS_JSON."
        ) from exc

    if not isinstance(data, dict):
        raise ValueError("La réponse JSON doit être un objet racine.")
    return data

def load_previous() -> dict[str, Any] | None:
    if not LATEST_JSON.exists():
        return None
    return json.loads(LATEST_JSON.read_text(encoding="utf-8"))


def diff_payload(previous: dict[str, Any] | None, current: dict[str, Any]) -> DiffResult:
    if not previous:
        return DiffResult(True, current["offers"], [], [])

    prev_by_id = {offer["id"]: offer for offer in previous.get("offers", []) if "id" in offer}
    curr_by_id = {offer["id"]: offer for offer in current.get("offers", []) if "id" in offer}

    new_offers = [offer for oid, offer in curr_by_id.items() if oid not in prev_by_id]
    removed_offers = [offer for oid, offer in prev_by_id.items() if oid not in curr_by_id]
    modified_offers = [
        offer
        for oid, offer in curr_by_id.items()
        if oid in prev_by_id and offer.get("fingerprint") != prev_by_id[oid].get("fingerprint")
    ]

    return DiffResult(
        changed=bool(new_offers or modified_offers or removed_offers),
        new_offers=new_offers,
        modified_offers=modified_offers,
        removed_offers=removed_offers,
    )


def markdown_escape_cell(text: str) -> str:
    return clean_text(text, max_chars=500).replace("|", "\\|")


def build_latest_markdown(payload: dict[str, Any]) -> str:
    lines = [
        f"# {payload['generated_title']}",
        "",
        f"- Généré le : `{payload['generated_at']}`",
        f"- Modèle : `{payload['model']}`",
        f"- Offres retenues : `{len(payload['offers'])}`",
        "",
        "## Résumé",
        "",
        payload["generated_summary"],
        "",
        "## Tableau compact",
        "",
        "| Rang | Offre | Type | Région | Ce que je gagne | Conditions / limites | Problèmes / pièges | Validité | Lien |",
        "|---:|---|---|---|---|---|---|---|---|",
    ]

    for offer in payload["offers"]:
        link = offer["official_link"] if valid_url(offer["official_link"]) else "non précisé"
        lines.append(
            "| {rank} | {offer} | {type} | {region} | {gain} | {limits} | {traps} | {validity} | {link} |".format(
                rank=offer["rank"],
                offer=markdown_escape_cell(f"{offer['offer']} ({offer['provider']})"),
                type=markdown_escape_cell(offer["type"]),
                region=markdown_escape_cell(offer["region"]),
                gain=markdown_escape_cell(offer["gain"]),
                limits=markdown_escape_cell(offer["conditions_limits"]),
                traps=markdown_escape_cell(offer["problems_traps"]),
                validity=markdown_escape_cell(offer["validity"]),
                link=link,
            )
        )

    lines += ["", "## Les 5 meilleurs pour usage réel", ""]
    lines += [f"- {item}" for item in payload["best_real_use"]] or ["- non précisé"]

    lines += ["", "## Les 5 plus risqués / instables", ""]
    lines += [f"- {item}" for item in payload["riskiest_or_unstable"]] or ["- non précisé"]

    lines += ["", "## À surveiller de près", ""]
    lines += [f"- {item}" for item in payload["watchlist"]] or ["- non précisé"]

    lines += ["", "## Sources critiques utilisées", ""]
    lines += [f"- {item}" for item in payload["critical_sources_used"]] or ["- non précisé"]

    return "\n".join(lines) + "\n"


def format_offer_for_changes(prefix: str, offer: dict[str, Any]) -> str:
    link = offer["official_link"] if valid_url(offer["official_link"]) else "non précisé"
    return (
        f"### {prefix} {offer['offer']} — {offer['provider']}\n"
        f"- Type : {offer['type']}\n"
        f"- Région : {offer['region']}\n"
        f"- Score usage : {offer['usage_score']}/5\n"
        f"- Gain : {offer['gain']}\n"
        f"- Limites : {offer['conditions_limits']}\n"
        f"- Pièges : {offer['problems_traps']}\n"
        f"- Validité : {offer['validity']}\n"
        f"- Lien : {link}\n"
    )


def build_changes_markdown(diff: DiffResult, payload: dict[str, Any]) -> str:
    lines = [
        "# Changements veille bons plans IA",
        "",
        f"- Généré le : `{payload['generated_at']}`",
        f"- Nouvelles offres : `{len(diff.new_offers)}`",
        f"- Offres modifiées : `{len(diff.modified_offers)}`",
        f"- Offres disparues : `{len(diff.removed_offers)}`",
        "",
    ]

    if not diff.changed:
        lines.append("Aucun changement détecté.")
        return "\n".join(lines) + "\n"

    if diff.new_offers:
        lines += ["## Nouvelles offres", ""]
        lines += [format_offer_for_changes("🆕", offer) for offer in diff.new_offers]

    if diff.modified_offers:
        lines += ["", "## Offres modifiées", ""]
        lines += [format_offer_for_changes("♻️", offer) for offer in diff.modified_offers]

    if diff.removed_offers:
        lines += ["", "## Offres disparues du top", ""]
        for offer in diff.removed_offers:
            lines.append(f"- {offer.get('offer', 'non précisé')} — {offer.get('provider', 'non précisé')}")

    return "\n".join(lines) + "\n"


def split_long_line(line: str, limit: int) -> list[str]:
    if len(line) <= limit:
        return [line]

    parts: list[str] = []
    current = line
    while len(current) > limit:
        cut = current.rfind(" ", 0, limit)
        if cut < limit // 2:
            cut = limit
        parts.append(current[:cut].rstrip())
        current = current[cut:].lstrip()
    if current:
        parts.append(current)
    return parts


def split_text(text: str, limit: int = DISCORD_CONTENT_LIMIT) -> list[str]:
    """Split long text into Discord-safe chunks without breaking lines when possible."""
    text = text.strip()
    if not text:
        return []

    chunks: list[str] = []
    current = ""
    for original_line in text.splitlines():
        for line in split_long_line(original_line, limit):
            candidate = line if not current else f"{current}\n{line}"
            if len(candidate) <= limit:
                current = candidate
            else:
                if current:
                    chunks.append(current)
                current = line

    if current:
        chunks.append(current)
    return chunks


def discord_clean_text(text: Any, default: str = "non précisé") -> str:
    """Normalize text for Discord without cutting information mid-sentence."""
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    text = text.replace("[`", "(").replace("`]", ")")
    return text or default


def discord_safe_line(text: str, max_chars: int = 160) -> str:
    """Backward-compatible helper: no Discord truncation, only normalization."""
    return discord_clean_text(text)


def has_real_info(text: Any) -> bool:
    value = discord_clean_text(text, default="")
    return bool(value and value.lower() not in {"non précisé", "non precise", "n/a", "na", "none"})


def compact_offer_line(prefix: str, offer: dict[str, Any], include_link: bool = False, include_conditions: bool = False) -> str:
    """Readable Discord block. No ellipsis, no mid-sentence cuts, spaced lines."""
    score = offer.get("usage_score", "?")
    rank = offer.get("rank", "?")

    title = discord_clean_text(offer.get("offer"))
    provider = discord_clean_text(offer.get("provider"))
    gain = discord_clean_text(offer.get("gain"))
    conditions = discord_clean_text(offer.get("conditions_limits"))
    trap = discord_clean_text(offer.get("problems_traps"))

    lines = [
        f"{prefix} **#{rank} {provider}** — {title} | {score}/5",
        f"↳ Gain : {gain}",
    ]

    if include_conditions and has_real_info(conditions):
        lines.append(f"📌 Limites : {conditions}")

    if has_real_info(trap):
        lines.append(f"⚠️ Pièges : {trap}")

    if include_link and valid_url(str(offer.get("official_link", ""))):
        lines.append(str(offer["official_link"]))

    return "\n".join(lines)


def pick_top_offers(payload: dict[str, Any], limit: int = 5) -> list[dict[str, Any]]:
    offers = list(payload.get("offers", []))
    offers.sort(key=lambda o: (-safe_int(o.get("usage_score"), 0, 0, 5), safe_int(o.get("rank"), 999, 1, 999)))
    return offers[:limit]


def build_discord_overview(diff: DiffResult, payload: dict[str, Any]) -> str:
    lines = [
        "🚨 **Veille bons plans IA**",
        "",
        f"🆕 **{len(diff.new_offers)}** nouvelles | ♻️ **{len(diff.modified_offers)}** modifiées | 🗑️ **{len(diff.removed_offers)}** sorties",
        f"📦 Offres retenues dans le rapport : **{len(payload.get('offers', []))}**",
        "📎 Rapport complet en pièce jointe `.md`",
        "",
    ]

    if diff.changed:
        lines.append("🏆 **Top usage réel**")
        lines.append("")
        for offer in pick_top_offers(payload, 5):
            lines.append(compact_offer_line("•", offer, include_link=False, include_conditions=False))
            lines.append("")
    else:
        lines.append("Aucun changement détecté. Rapport complet régénéré en pièce jointe.")
        lines.append("")

    if payload.get("watchlist"):
        lines.append("👀 **À surveiller**")
        lines.append("")
        for item in payload["watchlist"][:5]:
            lines.append(f"• {discord_clean_text(item)}")
        lines.append("")

    text = "\n".join(lines).strip()
    chunks = split_text(text, limit=DISCORD_SUMMARY_LIMIT)
    return chunks[0] if chunks else text


def build_discord_changes_list(diff: DiffResult) -> list[str]:
    """Build readable change messages. New/modified offers are not silently cut."""
    if not diff.changed:
        return []

    sections: list[str] = []

    if diff.new_offers:
        lines = ["🆕 **Nouveautés détectées**", ""]
        for offer in sorted(diff.new_offers, key=lambda o: safe_int(o.get("rank"), 999, 1, 999)):
            lines.append(compact_offer_line("•", offer, include_link=False, include_conditions=True))
            lines.append("")
        sections.extend(split_text("\n".join(lines).strip(), limit=DISCORD_CONTENT_LIMIT))

    if diff.modified_offers:
        lines = ["♻️ **Offres modifiées**", ""]
        for offer in sorted(diff.modified_offers, key=lambda o: safe_int(o.get("rank"), 999, 1, 999)):
            lines.append(compact_offer_line("•", offer, include_link=False, include_conditions=True))
            lines.append("")
        sections.extend(split_text("\n".join(lines).strip(), limit=DISCORD_CONTENT_LIMIT))

    if diff.removed_offers:
        lines = ["🗑️ **Sorties du top**", ""]
        for offer in diff.removed_offers:
            lines.append(f"• {discord_clean_text(offer.get('offer'))} — {discord_clean_text(offer.get('provider'))}")
        sections.extend(split_text("\n".join(lines).strip(), limit=DISCORD_CONTENT_LIMIT))

    return sections


def build_discord_messages(diff: DiffResult, payload: dict[str, Any]) -> list[str]:
    messages = [build_discord_overview(diff, payload)]
    messages.extend(build_discord_changes_list(diff))

    footer = "✅ Détails complets, liens et pièges : voir le fichier Markdown joint."
    if messages and len(messages[-1]) + len(footer) + 2 <= DISCORD_CONTENT_LIMIT:
        messages[-1] += "\n\n" + footer
    else:
        messages.append(footer)

    if DISCORD_MAX_MESSAGES > 0 and len(messages) > DISCORD_MAX_MESSAGES:
        # Never cut a sentence inside a message. If the user sets a hard cap, make the truncation explicit.
        kept = messages[: max(1, DISCORD_MAX_MESSAGES - 1)]
        kept.append(
            "⚠️ Notification Discord limitée par DISCORD_MAX_MESSAGES. "
            "Le rapport complet est disponible en pièce jointe Markdown."
        )
        return kept

    return messages


def discord_report_filename(diff: DiffResult, payload: dict[str, Any]) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M")
    if diff.changed:
        return (
            f"veille-bons-plans-ia-{stamp}-"
            f"new{len(diff.new_offers)}-mod{len(diff.modified_offers)}-out{len(diff.removed_offers)}.md"
        )
    return f"veille-bons-plans-ia-{stamp}-no-change.md"


def discord_retry_after(response: Any, default: float = 2.0) -> float:
    try:
        return float(response.json().get("retry_after", default))
    except Exception:
        try:
            return float(response.headers.get("Retry-After", default))
        except Exception:
            return default


def send_discord_message(webhook_url: str, content: str) -> None:
    import requests

    payload = {"content": content[:DISCORD_CONTENT_LIMIT]}
    for attempt in range(1, 4):
        response = requests.post(webhook_url, json=payload, timeout=20)

        if response.status_code in {200, 204}:
            return

        if response.status_code == 429:
            time.sleep(discord_retry_after(response) + 0.5)
            continue

        if response.status_code in {401, 403, 404}:
            raise RuntimeError(f"Discord webhook invalide ou inaccessible: HTTP {response.status_code}")

        if attempt == 3:
            raise RuntimeError(f"Discord webhook error HTTP {response.status_code}: {response.text[:500]}")

        time.sleep(2 * attempt)


def send_discord_file(webhook_url: str, content: str, filename: str, message: str = "") -> None:
    """Send a Markdown report as a Discord webhook attachment using multipart/form-data."""
    import requests

    safe_message = message[:DISCORD_CONTENT_LIMIT]
    payload_json = json.dumps({"content": safe_message}, ensure_ascii=False)
    files = {
        "files[0]": (filename, content.encode("utf-8"), "text/markdown; charset=utf-8"),
    }
    data = {"payload_json": payload_json}

    for attempt in range(1, 4):
        response = requests.post(webhook_url, data=data, files=files, timeout=30)

        if response.status_code in {200, 204}:
            return

        if response.status_code == 429:
            time.sleep(discord_retry_after(response) + 0.5)
            continue

        if response.status_code in {401, 403, 404}:
            raise RuntimeError(f"Discord webhook invalide ou inaccessible: HTTP {response.status_code}")

        if attempt == 3:
            raise RuntimeError(f"Discord file upload error HTTP {response.status_code}: {response.text[:500]}")

        time.sleep(2 * attempt)


def notify_discord(diff: DiffResult, payload: dict[str, Any]) -> None:
    if os.getenv("DRY_RUN", "false").lower() == "true":
        print("DRY_RUN=true: notification Discord ignorée.")
        return

    webhook = os.getenv("DISCORD_WEBHOOK_URL", "").strip()
    if not webhook:
        print("DISCORD_WEBHOOK_URL absent: notification Discord ignorée.")
        return

    notify_no_change = os.getenv("DISCORD_NOTIFY_NO_CHANGE", "false").lower() == "true"
    if not diff.changed and not notify_no_change:
        print("Aucun changement: Discord ignoré.")
        return

    messages = build_discord_messages(diff, payload)
    for index, message in enumerate(messages, start=1):
        send_discord_message(webhook, message)
        print(f"Discord message envoyé {index}/{len(messages)}")
        time.sleep(1.1)

    if DISCORD_ATTACH_FULL_REPORT and LATEST_MD.exists():
        filename = discord_report_filename(diff, payload)
        send_discord_file(
            webhook,
            LATEST_MD.read_text(encoding="utf-8"),
            filename,
            message=f"📎 Rapport complet Markdown : `{filename}`",
        )
        print(f"Discord fichier envoyé: {filename}")


def build_runtime_prompt() -> str:
    base = PROMPT_FILE.read_text(encoding="utf-8")
    guardrails = f"""

CONTRAINTE TECHNIQUE STRICTE POUR AUTOMATISATION :
- Retourne au maximum {MAX_OFFERS} offres.
- Retourne un JSON compact uniquement entre ces deux marqueurs exacts :
  BEGIN_AI_DEALS_JSON
  END_AI_DEALS_JSON
- Aucun markdown.
- Aucune phrase avant BEGIN_AI_DEALS_JSON.
- Aucune phrase après END_AI_DEALS_JSON.
- Pas de retours ligne dans les chaînes JSON : remplace-les par des espaces.
- Chaque champ texte doit rester court.
- `offer` <= 90 caractères.
- `gain` <= 160 caractères.
- `conditions_limits` <= 190 caractères.
- `problems_traps` <= 190 caractères.
- `generated_summary` <= 350 caractères.
- `critical_sources_used` <= 10 éléments, format court : provider + URL officielle.
- Si une donnée n'est pas confirmée par source officielle, écris "non précisé".
- Le lien `official_link` doit être une URL officielle directe, pas un article de blog.
"""
    return base.strip() + guardrails


def get_finish_reason(response: Any) -> str:
    try:
        candidates = getattr(response, "candidates", None) or []
        if not candidates:
            return "UNKNOWN"
        finish_reason = getattr(candidates[0], "finish_reason", None)
        return str(finish_reason or "UNKNOWN")
    except Exception:
        return "UNKNOWN"


def extract_text_from_response(response: Any) -> str:
    # python-genai exposes response.text for normal JSON text. Keep fallback for future SDK changes.
    text = getattr(response, "text", None)
    if text:
        return str(text)

    # Best-effort fallback for candidates/parts.
    parts: list[str] = []
    try:
        for candidate in getattr(response, "candidates", []) or []:
            content = getattr(candidate, "content", None)
            for part in getattr(content, "parts", []) or []:
                part_text = getattr(part, "text", None)
                if part_text:
                    parts.append(str(part_text))
    except Exception:
        pass
    return "\n".join(parts).strip()


def call_gemini(prompt: str) -> str:
    """Call Gemini with Google Search grounding.

    Important: do not set response_mime_type="application/json" or response_schema here.
    The Gemini API rejects JSON response MIME type when a tool such as google_search is enabled.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("Secret GEMINI_API_KEY manquant.")

    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)

    last_error: Exception | None = None
    for attempt in range(1, 4):
        try:
            config = types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
                temperature=0.1,
                max_output_tokens=GEMINI_MAX_OUTPUT_TOKENS,
            )
            response = client.models.generate_content(
                model=MODEL,
                contents=prompt,
                config=config,
            )
            finish_reason = get_finish_reason(response)
            text = extract_text_from_response(response)
            if not text:
                raise RuntimeError(f"Réponse Gemini vide. finish_reason={finish_reason}")
            if "MAX_TOKENS" in finish_reason.upper():
                raise RuntimeError(
                    "Réponse Gemini tronquée par limite max_output_tokens. "
                    "Réduis AI_DEALS_MAX_OFFERS ou augmente GEMINI_MAX_OUTPUT_TOKENS."
                )
            return text
        except Exception as exc:
            last_error = exc

        if attempt < 3:
            time.sleep(5 * attempt)

    raise RuntimeError(f"Gemini failed after retries: {last_error}")

def sample_payload() -> dict[str, Any]:
    return normalize_payload(
        {
            "generated_title": "DRY RUN — Veille bons plans IA",
            "generated_summary": "Payload de test local sans appel Gemini. Sert à valider GitHub Actions, JSON, Markdown, diff et Discord.",
            "offers": [
                {
                    "rank": 1,
                    "offer": "Gemini API Free Tier",
                    "provider": "Google",
                    "type": "API LLM",
                    "region": "Monde",
                    "gain": "Free tier pour tests API selon limites en vigueur.",
                    "conditions_limits": "Limites variables selon modèle et compte ; vérifier pricing officiel.",
                    "problems_traps": "Ne pas utiliser pour données privées sensibles en free tier.",
                    "usage_score": 4,
                    "validity": "non précisé",
                    "official_link": "https://ai.google.dev/gemini-api/docs/pricing",
                    "community_source": "non précisé",
                }
            ],
            "best_real_use": ["Gemini API Free Tier — bon pour prototypage"],
            "riskiest_or_unstable": ["DRY RUN — aucun risque réel mesuré"],
            "watchlist": ["Ajouter sources officielles provider par provider"],
            "critical_sources_used": ["DRY RUN local"],
        }
    )


def save_outputs(payload: dict[str, Any], latest_md: str, changes_md: str) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    HISTORY_DIR.mkdir(exist_ok=True)
    REPORTS_DIR.mkdir(exist_ok=True)

    LATEST_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    LATEST_MD.write_text(latest_md, encoding="utf-8")
    CHANGES_MD.write_text(changes_md, encoding="utf-8")

    stamp = payload["generated_at"].replace(":", "-")
    history_file = HISTORY_DIR / f"{stamp}.json"
    history_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_github_output(diff: DiffResult) -> None:
    output_path = os.getenv("GITHUB_OUTPUT")
    if not output_path:
        return
    with open(output_path, "a", encoding="utf-8") as f:
        f.write(f"changed={'true' if diff.changed else 'false'}\n")
        f.write(f"new_count={len(diff.new_offers)}\n")
        f.write(f"modified_count={len(diff.modified_offers)}\n")
        f.write(f"removed_count={len(diff.removed_offers)}\n")


def load_current_payload_from_files() -> dict[str, Any]:
    if not LATEST_JSON.exists():
        raise RuntimeError("data/latest.json introuvable. Lance d’abord un vrai run ou récupère les artefacts du repo.")
    payload = json.loads(LATEST_JSON.read_text(encoding="utf-8"))
    if "offers" not in payload:
        raise RuntimeError("data/latest.json existe mais ne contient pas de champ offers.")
    return payload


def notify_from_existing_files(mode: str = "all_current_as_new") -> int:
    """Discord-only test path. No Gemini call, no write, no commit, no issue."""
    payload = load_current_payload_from_files()

    if mode == "no_change":
        diff = DiffResult(False, [], [], [])
    elif mode == "real_diff_from_latest":
        previous = load_previous()
        diff = diff_payload(previous, payload)
    else:
        diff = DiffResult(True, list(payload.get("offers", [])), [], [])

    notify_discord(diff, payload)
    print("Discord notify-only terminé.")
    print(f"mode={mode}")
    print(f"offers={len(payload.get('offers', []))}")
    print(f"new={len(diff.new_offers)} modified={len(diff.modified_offers)} removed={len(diff.removed_offers)}")
    return 0


def main() -> int:
    if os.getenv("NOTIFY_ONLY", "false").lower() == "true":
        mode = os.getenv("NOTIFY_ONLY_MODE", "all_current_as_new")
        return notify_from_existing_files(mode=mode)

    dry_run = os.getenv("DRY_RUN", "false").lower() == "true"

    if dry_run:
        print("DRY_RUN=true: aucun appel Gemini ne sera effectué.")
        payload = sample_payload()
    else:
        prompt = build_runtime_prompt()
        raw_text = call_gemini(prompt)
        try:
            raw_payload = extract_json(raw_text)
        except Exception as exc:
            save_failed_raw_response(raw_text, exc)
            raise RuntimeError(
                "Impossible de parser le JSON Gemini. Le brut est sauvegardé dans "
                "reports/failed_raw_response.txt. "
                "Cause probable : sortie tronquée ou JSON non respecté par le modèle."
            ) from exc
        payload = normalize_payload(raw_payload)

    previous = load_previous()
    diff = diff_payload(previous, payload)

    latest_md = build_latest_markdown(payload)
    changes_md = build_changes_markdown(diff, payload)
    save_outputs(payload, latest_md, changes_md)

    try:
        notify_discord(diff, payload)
    except Exception as exc:
        print(f"WARN: Discord notification failed: {exc}", file=sys.stderr)

    write_github_output(diff)

    print(f"offers={len(payload['offers'])}")
    print(f"changed={diff.changed}")
    print(f"new={len(diff.new_offers)} modified={len(diff.modified_offers)} removed={len(diff.removed_offers)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
