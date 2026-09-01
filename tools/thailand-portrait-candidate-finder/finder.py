from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

API_HOST = "https://graph.threads.net"
DEFAULT_FIELDS = "id,permalink,username,text,timestamp,shortcode"


def load_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def normalize(text: str | None) -> str:
    return (text or "").strip().lower()


def contains_terms(text: str, terms: list[str]) -> list[str]:
    haystack = normalize(text)
    return [term for term in terms if normalize(term) in haystack]


def explicit_minor_signal(text: str, minor_risk_terms: list[str]) -> tuple[bool, list[str]]:
    haystack = normalize(text)
    signals = contains_terms(haystack, minor_risk_terms)

    age_patterns = [
        r"\bage\s*[:=-]?\s*(1[3-7])\b",
        r"\b(1[3-7])\s*(?:yo|y/o|years?\s+old)\b",
        r"อายุ\s*(1[3-7])\b",
    ]
    for pattern in age_patterns:
        match = re.search(pattern, haystack, flags=re.IGNORECASE)
        if match:
            signals.append(f"explicit_age_{match.group(1)}")
    return bool(signals), sorted(set(signals))


def explicit_adult_signal(text: str) -> bool:
    haystack = normalize(text)
    patterns = [
        r"\bage\s*[:=-]?\s*(?:1[89]|[2-9][0-9])\b",
        r"\b(?:1[89]|[2-9][0-9])\s*(?:yo|y/o|years?\s+old)\b",
        r"อายุ\s*(?:1[89]|[2-9][0-9])\b",
    ]
    return any(re.search(pattern, haystack, flags=re.IGNORECASE) for pattern in patterns)


def score_post(text: str, config: dict[str, Any]) -> tuple[int, list[str], str, bool]:
    minor, minor_signals = explicit_minor_signal(text, config["minor_risk_terms"])
    if minor:
        return -999, [f"minor-risk:{s}" for s in minor_signals], "excluded_minor_risk", True

    score = 0
    signals: list[str] = []

    strong = contains_terms(text, config["strong_intent_terms"])
    creative = contains_terms(text, config["creative_terms"])
    location = contains_terms(text, config["location_terms"])

    if strong:
        score += 5 * len(strong)
        signals.extend(f"intent:{x}" for x in strong)
    if creative:
        score += 2 * len(creative)
        signals.extend(f"creative:{x}" for x in creative)
    if location:
        score += 2 * len(location)
        signals.extend(f"location:{x}" for x in location)

    adult_status = "manual_check_required"
    if explicit_adult_signal(text):
        score += 3
        signals.append("adult:explicit-text-signal")
        adult_status = "explicit_text_signal_check_profile"

    return score, sorted(set(signals)), adult_status, False


def threads_keyword_search(
    token: str,
    query: str,
    search_type: str,
    limit: int,
    timeout: int = 30,
) -> list[dict[str, Any]]:
    url = f"{API_HOST}/keyword_search"
    headers = {"Authorization": f"Bearer {token}"}
    params = {
        "q": query,
        "search_type": search_type,
        "fields": DEFAULT_FIELDS,
        "limit": limit,
    }

    response = requests.get(url, headers=headers, params=params, timeout=timeout)
    if response.status_code == 429:
        raise RuntimeError("Threads API rate limit reached (HTTP 429). Try again later.")
    if response.status_code >= 400:
        try:
            detail = response.json()
        except ValueError:
            detail = response.text
        raise RuntimeError(f"Threads API error {response.status_code}: {detail}")

    payload = response.json()
    return payload.get("data", [])


def build_candidates(
    all_query_posts: list[tuple[str, dict[str, Any]]],
    config: dict[str, Any],
    min_score: int,
) -> list[dict[str, Any]]:
    by_user: dict[str, dict[str, Any]] = {}

    for query, post in all_query_posts:
        username = (post.get("username") or "").strip()
        text = (post.get("text") or "").strip()
        if not username or not text:
            continue

        score, signals, adult_status, excluded = score_post(text, config)
        if excluded:
            continue

        if username not in by_user:
            by_user[username] = {
                "username": username,
                "score": score,
                "adult_status": adult_status,
                "matched_queries": {query},
                "signals": set(signals),
                "latest_text": text,
                "permalink": post.get("permalink") or "",
                "timestamp": post.get("timestamp") or "",
                "posts_seen": 1,
            }
        else:
            item = by_user[username]
            item["score"] = max(item["score"], score)
            item["matched_queries"].add(query)
            item["signals"].update(signals)
            item["posts_seen"] += 1

            current_ts = str(item.get("timestamp") or "")
            incoming_ts = str(post.get("timestamp") or "")
            if incoming_ts > current_ts:
                item["latest_text"] = text
                item["permalink"] = post.get("permalink") or ""
                item["timestamp"] = incoming_ts

            if adult_status == "explicit_text_signal_check_profile":
                item["adult_status"] = adult_status

    results: list[dict[str, Any]] = []
    for item in by_user.values():
        # Small confidence bonus when the same account appears in multiple relevant searches.
        query_bonus = min(4, max(0, len(item["matched_queries"]) - 1))
        item["score"] += query_bonus
        if query_bonus:
            item["signals"].add(f"multi-query:{len(item['matched_queries'])}")

        if item["score"] < min_score:
            continue

        item["matched_queries"] = sorted(item["matched_queries"])
        item["signals"] = sorted(item["signals"])
        results.append(item)

    results.sort(key=lambda x: (x["score"], x.get("timestamp", "")), reverse=True)
    return results


def write_outputs(
    candidates: list[dict[str, Any]],
    raw_posts: list[tuple[str, dict[str, Any]]],
    output_dir: Path,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    csv_path = output_dir / "candidates_latest.csv"
    md_path = output_dir / "candidates_latest.md"
    raw_path = output_dir / "raw_posts_latest.json"

    fields = [
        "username",
        "score",
        "adult_status",
        "matched_queries",
        "signals",
        "latest_text",
        "permalink",
        "timestamp",
        "posts_seen",
    ]

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for item in candidates:
            row = dict(item)
            row["matched_queries"] = " | ".join(item["matched_queries"])
            row["signals"] = " | ".join(item["signals"])
            writer.writerow(row)

    generated = datetime.now(timezone.utc).isoformat()
    with md_path.open("w", encoding="utf-8") as f:
        f.write("# Thailand Portrait Candidate Finder — Latest\n\n")
        f.write(f"Generated: {generated}\n\n")
        f.write("> Important: Do not infer adulthood from appearance. Verify the person is an adult before sending a portrait request. A score is only a relevance signal, not predicted consent.\n\n")
        f.write("| Rank | Username | Score | Adult status | Signals | Post |\n")
        f.write("|---:|---|---:|---|---|---|\n")
        for i, item in enumerate(candidates, start=1):
            text = re.sub(r"\s+", " ", item["latest_text"]).replace("|", "\\|")
            if len(text) > 180:
                text = text[:177] + "..."
            link = item["permalink"]
            username = item["username"].replace("|", "\\|")
            signals = ", ".join(item["signals"][:6]).replace("|", "\\|")
            f.write(
                f"| {i} | @{username} | {item['score']} | {item['adult_status']} | {signals} | "
                f"[{text}]({link}) |\n"
            )

    serializable_raw = [{"query": q, "post": post} for q, post in raw_posts]
    with raw_path.open("w", encoding="utf-8") as f:
        json.dump(serializable_raw, f, ensure_ascii=False, indent=2)

    print(f"Wrote {len(candidates)} candidates")
    print(csv_path)
    print(md_path)
    print(raw_path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Find public Threads posts relevant to portrait collaborations in Thailand.")
    parser.add_argument("--config", default="config.json")
    parser.add_argument("--search-type", choices=["RECENT", "TOP"], default="RECENT")
    parser.add_argument("--limit", type=int, default=25, help="Results requested per query")
    parser.add_argument("--min-score", type=int, default=5)
    parser.add_argument("--delay", type=float, default=0.7, help="Seconds between API requests")
    parser.add_argument("--output", default="output")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    script_dir = Path(__file__).resolve().parent
    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = script_dir / config_path

    output_dir = Path(args.output)
    if not output_dir.is_absolute():
        output_dir = script_dir / output_dir

    token = os.getenv("THREADS_ACCESS_TOKEN", "").strip()
    if not token:
        print("ERROR: THREADS_ACCESS_TOKEN is not set.", file=sys.stderr)
        return 2

    config = load_config(config_path)
    query_posts: list[tuple[str, dict[str, Any]]] = []

    for index, query in enumerate(config["queries"], start=1):
        print(f"[{index}/{len(config['queries'])}] {query}")
        try:
            posts = threads_keyword_search(token, query, args.search_type, args.limit)
        except RuntimeError as exc:
            print(f"WARNING: {exc}", file=sys.stderr)
            continue
        for post in posts:
            query_posts.append((query, post))
        if args.delay > 0:
            time.sleep(args.delay)

    candidates = build_candidates(query_posts, config, args.min_score)
    write_outputs(candidates, query_posts, output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
