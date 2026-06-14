#!/usr/bin/env python3
"""AI deals watch.

V2 hardening notes:
- Avoids asking Gemini for a huge, free-form JSON blob.
- Uses Gemini JSON mode / structured output when available.
- Keeps every model field short to avoid truncated JSON.
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

MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
MAX_OFFERS = int(os.getenv("AI_DEALS_MAX_OFFERS", "30"))
GEMINI_MAX_OUTPUT_TOKENS = int(os.getenv("GEMINI_MAX_OUTPUT_TOKENS", "32768"))
DISCORD_CONTENT_LIMIT = 1900  # Discord content max is 2000; keep margin.
DISCORD_MAX_MESSAGES = int(os.getenv("DISCORD_MAX_MESSAGES", "6"))

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
    """Extract JSON even if a model accidentally wraps it in markdown fences.

    This function is intentionally strict. It does not try to invent missing JSON if
    the model output was truncated. On failure, the caller stores the raw output.
    """
    stripped = strip_markdown_fence(text)

    try:
        data = json.loads(stripped)
    except json.JSONDecodeError as first_error:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise first_error
        try:
            data = json.loads(stripped[start : end + 1])
        except json.JSONDecodeError as second_error:
            # Keep the first error context if the whole payload was clearly attempted JSON;
            # otherwise show the substring error.
            raise second_error from first_error

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


def build_discord_messages(diff: DiffResult, payload: dict[str, Any]) -> list[str]:
    title = "🚨 Veille bons plans IA"
    if not diff.changed:
        return [f"{title}\nAucun changement détecté. Rapport régénéré : `reports/latest.md`"]

    header = (
        f"{title}\n"
        f"🆕 {len(diff.new_offers)} nouvelles | ♻️ {len(diff.modified_offers)} modifiées | "
        f"🗑️ {len(diff.removed_offers)} sorties du top\n"
        f"Rapport complet : `reports/latest.md`"
    )

    parts = [header]
    selected = [("🆕", x) for x in diff.new_offers] + [("♻️", x) for x in diff.modified_offers]

    for prefix, offer in selected[:10]:
        item = (
            f"{prefix} **{offer['offer']}** — {offer['provider']}\n"
            f"Type: {offer['type']} | Région: {offer['region']} | Score usage: {offer['usage_score']}/5\n"
            f"Gain: {offer['gain']}\n"
            f"Limites: {offer['conditions_limits']}\n"
            f"Pièges: {offer['problems_traps']}\n"
            f"Lien: {offer['official_link']}"
        )
        parts.extend(split_text(item))

    if len(selected) > 10 or diff.removed_offers:
        parts.append("Suite complète dans `reports/changes.md` et l’issue GitHub générée automatiquement.")

    safe_messages: list[str] = []
    for part in parts:
        safe_messages.extend(split_text(part))

    return safe_messages[:DISCORD_MAX_MESSAGES]


def send_discord_message(webhook_url: str, content: str) -> None:
    import requests

    payload = {"content": content[:DISCORD_CONTENT_LIMIT]}
    for attempt in range(1, 4):
        response = requests.post(webhook_url, json=payload, timeout=20)

        if response.status_code in {200, 204}:
            return

        if response.status_code == 429:
            retry_after = 2.0
            try:
                retry_after = float(response.json().get("retry_after", retry_after))
            except Exception:
                retry_after = float(response.headers.get("Retry-After", retry_after))
            time.sleep(retry_after + 0.5)
            continue

        if response.status_code in {401, 403, 404}:
            raise RuntimeError(f"Discord webhook invalide ou inaccessible: HTTP {response.status_code}")

        if attempt == 3:
            raise RuntimeError(f"Discord webhook error HTTP {response.status_code}: {response.text[:500]}")

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


def build_runtime_prompt() -> str:
    base = PROMPT_FILE.read_text(encoding="utf-8")
    guardrails = f"""

CONTRAINTE TECHNIQUE STRICTE POUR AUTOMATISATION :
- Retourne au maximum {MAX_OFFERS} offres.
- JSON compact uniquement.
- Aucun markdown.
- Aucune phrase hors JSON.
- Chaque champ texte doit rester court.
- `gain` <= 180 caractères.
- `conditions_limits` <= 220 caractères.
- `problems_traps` <= 220 caractères.
- `generated_summary` <= 450 caractères.
- `critical_sources_used` <= 15 éléments.
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
                response_mime_type="application/json",
                response_schema=GEMINI_RESPONSE_SCHEMA,
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
        except TypeError as exc:
            # Compatibility fallback for older google-genai versions where response_schema may differ.
            last_error = exc
            try:
                config = types.GenerateContentConfig(
                    tools=[types.Tool(google_search=types.GoogleSearch())],
                    temperature=0.1,
                    max_output_tokens=GEMINI_MAX_OUTPUT_TOKENS,
                    response_mime_type="application/json",
                )
                response = client.models.generate_content(model=MODEL, contents=prompt, config=config)
                text = extract_text_from_response(response)
                if not text:
                    raise RuntimeError("Réponse Gemini vide après fallback JSON mode.")
                return text
            except Exception as fallback_exc:
                last_error = fallback_exc
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


def main() -> int:
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
