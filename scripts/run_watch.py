#!/usr/bin/env python3
"""AI deals watch.

Pipeline:
1. Ask Gemini 2.5 Flash-Lite with Google Search grounding for a verified JSON report.
2. Compare with previous JSON history.
3. Generate Markdown reports.
4. Commit via GitHub Actions and optionally notify Discord webhook.

The code is deliberately defensive: it validates/sanitizes model output, avoids Discord
message limit errors, and retries Discord 429 responses.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
import hashlib
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

MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
DISCORD_CONTENT_LIMIT = 1900  # Real limit is 2000; keep margin for safety.
DISCORD_MAX_MESSAGES = int(os.getenv("DISCORD_MAX_MESSAGES", "6"))


@dataclass
class DiffResult:
    changed: bool
    new_offers: list[dict[str, Any]]
    modified_offers: list[dict[str, Any]]
    removed_offers: list[dict[str, Any]]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def stable_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def clean_text(value: Any, default: str = "non précisé") -> str:
    if value is None:
        return default
    text = re.sub(r"\s+", " ", str(value)).strip()
    return text if text else default


def valid_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        return parsed.scheme in {"http", "https"} and bool(parsed.netloc)
    except Exception:
        return False


def offer_id(offer: dict[str, Any]) -> str:
    link = clean_text(offer.get("official_link"), "")
    provider = clean_text(offer.get("provider"), "")
    name = clean_text(offer.get("offer"), "")
    identity = link if valid_url(link) else f"{provider}|{name}"
    return sha256_text(identity.lower())[:16]


def offer_fingerprint(offer: dict[str, Any]) -> str:
    relevant = {
        "offer": clean_text(offer.get("offer")),
        "provider": clean_text(offer.get("provider")),
        "type": clean_text(offer.get("type")),
        "region": clean_text(offer.get("region")),
        "gain": clean_text(offer.get("gain")),
        "conditions_limits": clean_text(offer.get("conditions_limits")),
        "problems_traps": clean_text(offer.get("problems_traps")),
        "usage_score": offer.get("usage_score"),
        "validity": clean_text(offer.get("validity")),
        "official_link": clean_text(offer.get("official_link")),
        "community_source": clean_text(offer.get("community_source")),
    }
    return sha256_text(stable_json(relevant))[:16]


def sanitize_offer(raw: dict[str, Any], fallback_rank: int) -> dict[str, Any]:
    score = raw.get("usage_score", 0)
    try:
        score = int(score)
    except Exception:
        score = 0
    score = max(0, min(5, score))

    offer = {
        "rank": int(raw.get("rank") or fallback_rank),
        "offer": clean_text(raw.get("offer")),
        "provider": clean_text(raw.get("provider")),
        "type": clean_text(raw.get("type")),
        "region": clean_text(raw.get("region")),
        "gain": clean_text(raw.get("gain")),
        "conditions_limits": clean_text(raw.get("conditions_limits")),
        "problems_traps": clean_text(raw.get("problems_traps")),
        "usage_score": score,
        "validity": clean_text(raw.get("validity")),
        "official_link": clean_text(raw.get("official_link")),
        "community_source": clean_text(raw.get("community_source")),
    }
    offer["id"] = offer_id(offer)
    offer["fingerprint"] = offer_fingerprint(offer)
    return offer


def normalize_payload(raw: dict[str, Any]) -> dict[str, Any]:
    offers_raw = raw.get("offers") or []
    if not isinstance(offers_raw, list):
        raise ValueError("Le champ 'offers' doit être une liste.")

    offers = []
    seen_ids = set()
    for index, item in enumerate(offers_raw, start=1):
        if not isinstance(item, dict):
            continue
        offer = sanitize_offer(item, index)
        if offer["id"] in seen_ids:
            continue
        seen_ids.add(offer["id"])
        offers.append(offer)

    offers.sort(key=lambda x: x.get("rank", 999))

    return {
        "generated_at": utc_now(),
        "model": MODEL,
        "generated_title": clean_text(raw.get("generated_title"), "Veille bons plans IA"),
        "generated_summary": clean_text(raw.get("generated_summary"), "non précisé"),
        "offers": offers,
        "best_real_use": as_str_list(raw.get("best_real_use"), 5),
        "riskiest_or_unstable": as_str_list(raw.get("riskiest_or_unstable"), 5),
        "watchlist": as_str_list(raw.get("watchlist"), 5),
        "critical_sources_used": as_str_list(raw.get("critical_sources_used"), 20),
    }


def as_str_list(value: Any, limit: int) -> list[str]:
    if not isinstance(value, list):
        return []
    return [clean_text(x) for x in value if clean_text(x) != "non précisé"][:limit]


def extract_json(text: str) -> dict[str, Any]:
    """Extract JSON even if a model accidentally wraps it in markdown fences."""
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped, flags=re.I)
        stripped = re.sub(r"\s*```$", "", stripped)

    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise
        return json.loads(stripped[start : end + 1])


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
    return clean_text(text).replace("|", "\\|")


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


def split_text(text: str, limit: int = DISCORD_CONTENT_LIMIT) -> list[str]:
    """Split long text into Discord-safe chunks without breaking lines when possible."""
    text = text.strip()
    if not text:
        return []

    chunks: list[str] = []
    current = ""
    for line in text.splitlines():
        candidate = line if not current else f"{current}\n{line}"
        if len(candidate) <= limit:
            current = candidate
            continue

        if current:
            chunks.append(current)
            current = ""

        while len(line) > limit:
            chunks.append(line[:limit])
            line = line[limit:]
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
        f"🆕 {len(diff.new_offers)} nouvelles | ♻️ {len(diff.modified_offers)} modifiées | 🗑️ {len(diff.removed_offers)} sorties du top\n"
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

        # Invalid webhook must not be retried aggressively.
        if response.status_code in {401, 403, 404}:
            raise RuntimeError(f"Discord webhook invalide ou inaccessible: HTTP {response.status_code}")

        if attempt == 3:
            raise RuntimeError(f"Discord webhook error HTTP {response.status_code}: {response.text[:500]}")

        time.sleep(2 * attempt)


def notify_discord(diff: DiffResult, payload: dict[str, Any]) -> None:
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
        time.sleep(1.1)  # simple anti-spam buffer


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
            response = client.models.generate_content(
                model=MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    tools=[types.Tool(google_search=types.GoogleSearch())],
                    temperature=0.15,
                ),
            )
            if not response.text:
                raise RuntimeError("Réponse Gemini vide.")
            return response.text
        except Exception as exc:  # SDK exceptions vary; keep retry generic.
            last_error = exc
            if attempt == 3:
                break
            time.sleep(5 * attempt)

    raise RuntimeError(f"Gemini failed after retries: {last_error}")


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
    prompt = PROMPT_FILE.read_text(encoding="utf-8")
    raw_text = call_gemini(prompt)
    raw_payload = extract_json(raw_text)
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
