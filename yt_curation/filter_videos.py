#!/usr/bin/env python3
"""
Filter YouTube videos by yt-dlp metadata per curation rules and output top URLs.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Optional


def fetch_metadata_cli(url: str, timeout: int = 60) -> Optional[Dict[str, Any]]:
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "yt_dlp", "--dump-json", url],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if proc.returncode != 0:
            print(f"yt-dlp error for {url}: {proc.stderr.strip()}", file=sys.stderr)
            return None
        return json.loads(proc.stdout)
    except Exception as exc:
        print(f"Exception fetching metadata for {url}: {exc}", file=sys.stderr)
        return None


def normalize_text(s: Optional[str]) -> str:
    return (s or "").lower()


def contains_all_words(text: str, words: List[str]) -> bool:
    for w in words:
        if w.lower() not in text:
            return False
    return True


def contains_any_word(text: str, words: List[str]) -> bool:
    for w in words:
        if w.lower() in text:
            return True
    return False


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Filter YouTube metadata or URL list using yt-dlp metadata.")
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--source", "-s", help="Source file with one URL per line.")
    group.add_argument("--metadata-file", "-m", help="Local JSON metadata file to filter directly.")
    group.add_argument("--task-file", "-t", help="Task JSON file containing source_urls and filtering parameters.")
    p.add_argument("--min-duration-seconds", type=int, default=300)
    p.add_argument("--max-duration-seconds", type=int, default=2400)
    p.add_argument(
        "--required-words",
        "-r",
        action="append",
        default=[],
        help="Required word (can be repeated). Title+description must contain ALL required words.",
    )
    p.add_argument(
        "--forbidden-words",
        "-f",
        action="append",
        default=[],
        help="Forbidden word (can be repeated). Exclude if any appears in title or description.",
    )
    p.add_argument("--limit", "-n", type=int, default=10)
    p.add_argument("--output", "-o", default="output.json")
    p.add_argument("--workers", type=int, default=4, help="Concurrent metadata fetch workers")
    return p.parse_args()


def load_task_file(path: Path) -> Dict[str, Any]:
    data = json.loads(path.read_text())
    if not isinstance(data, dict):
        raise ValueError("Task file must be a JSON object.")
    return data


def load_metadata_file(path: Path) -> List[Dict[str, Any]]:
    data = json.loads(path.read_text())
    if isinstance(data, dict):
        if "entries" in data and isinstance(data["entries"], list):
            return data["entries"]
        if "videos" in data and isinstance(data["videos"], list):
            return data["videos"]
        raise ValueError("JSON metadata file must contain a top-level list or an object with an 'entries' or 'videos' list.")
    if isinstance(data, list):
        return data
    raise ValueError("JSON metadata file must be a list of metadata objects.")


def fetch_all(urls: List[str], workers: int = 4) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {ex.submit(fetch_metadata_cli, url): url for url in urls}
        for fut in as_completed(futures):
            meta = fut.result()
            if meta:
                results.append(meta)
    return results


def main() -> None:
    args = parse_args()
    task_data: Dict[str, Any] = {}
    if args.task_file:
        task_path = Path(args.task_file)
        if not task_path.exists():
            print("Task file not found:", task_path, file=sys.stderr)
            sys.exit(2)
        task_data = load_task_file(task_path)

    metas: List[Dict[str, Any]]
    if args.metadata_file:
        meta_path = Path(args.metadata_file)
        if not meta_path.exists():
            print("Metadata file not found:", meta_path, file=sys.stderr)
            sys.exit(2)
        metas = load_metadata_file(meta_path)
        print(f"Loaded {len(metas)} metadata objects from {meta_path}")
    else:
        urls: List[str] = []
        if args.source:
            src = Path(args.source)
            if not src.exists():
                print("Source file not found:", src, file=sys.stderr)
                sys.exit(2)
            urls = [line.strip() for line in src.read_text().splitlines() if line.strip()]
            if not urls:
                print("No URLs in source file", file=sys.stderr)
                sys.exit(2)
        elif task_data.get("source_urls"):
            urls = [str(u).strip() for u in task_data.get("source_urls", []) if str(u).strip()]
            if not urls:
                print("Task file contains no source_urls", file=sys.stderr)
                sys.exit(2)
        else:
            print("No source URLs available to fetch metadata.", file=sys.stderr)
            sys.exit(2)

        print(f"Fetching metadata for {len(urls)} URLs (workers={args.workers})...")
        metas = fetch_all(urls, workers=args.workers)
        print(f"Fetched metadata for {len(metas)} items")

    required = [w.lower() for w in (args.required_words or task_data.get("required_words", []))]
    forbidden = [w.lower() for w in (args.forbidden_words or task_data.get("forbidden_words", []))]
    min_duration = int(task_data.get("min_duration_seconds", args.min_duration_seconds)) if args.min_duration_seconds == 300 and task_data.get("min_duration_seconds") else args.min_duration_seconds
    max_duration = int(task_data.get("max_duration_seconds", args.max_duration_seconds)) if args.max_duration_seconds == 2400 and task_data.get("max_duration_seconds") else args.max_duration_seconds
    limit = int(task_data.get("limit", args.limit)) if args.limit == 10 and task_data.get("limit") else args.limit

    keep: List[Dict[str, Any]] = []
    for m in metas:
        duration = m.get("duration")
        if duration is None:
            continue
        if not (min_duration <= int(duration) <= max_duration):
            continue

        title = normalize_text(m.get("title"))
        description = normalize_text(m.get("description"))
        combined = title + "\n" + description

        if required and not contains_all_words(combined, required):
            continue
        if forbidden and (contains_any_word(title, forbidden) or contains_any_word(description, forbidden)):
            continue

        keep.append(m)

    def sort_key(m: Dict[str, Any]):
        ud = m.get("upload_date") or "0"
        try:
            ud_int = int(ud)
        except Exception:
            ud_int = 0
        vid = m.get("id") or ""
        return (-ud_int, vid)

    keep.sort(key=sort_key)

    urls_out: List[str] = []
    for m in keep[:limit]:
        url = m.get("webpage_url") or ("https://youtube.com/watch?v=" + m.get("id", ""))
        urls_out.append(url)

    out_path = Path(args.output)
    out_path.write_text(json.dumps({"urls": urls_out}, indent=2))
    print(f"Wrote {len(urls_out)} URLs to {out_path}")


if __name__ == "__main__":
    main()
