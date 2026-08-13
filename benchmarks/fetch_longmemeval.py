"""Fetch the official LongMemEval dataset (ICLR 2025) for independent testing.

LongMemEval (Wu et al., ICLR 2025) is an independent long-context benchmark
with ~115k tokens of chat history per question and heavy interference. The
cleaned files used by ``longmemeval_bench.py`` are:

    longmemeval_oracle.json       ~15 MB   (oracle / short-haystack subset)
    longmemeval_s_cleaned.json   ~277 MB   (S: single session per question)
    longmemeval_m_cleaned.json   ~2.7 GB   (M: multi-session; optional)

The downloader tries Hugging Face first, then the hf-mirror.com mirror, and
can also import an already-downloaded copy via ``--source-dir``.

Usage:
    python benchmarks/fetch_longmemeval.py                 # S + oracle
    python benchmarks/fetch_longmemeval.py --all           # + M set
    python benchmarks/fetch_longmemeval.py --source-dir D:\\data
    python benchmarks/fetch_longmemeval.py --force
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import urllib.error
import urllib.request

_BENCH = os.path.dirname(os.path.abspath(__file__))
# Repo-internal work/ (gitignored): the nightly workflow reads the dataset
# as work/<file> from the checkout root, so fetch and bench must agree.
_WORK = os.path.normpath(os.path.join(_BENCH, "..", "work"))

FILES = {
    "longmemeval_oracle.json": 500_000,
    "longmemeval_s_cleaned.json": 1_000_000,
    "longmemeval_m_cleaned.json": 10_000_000,
}

SOURCES = [
    "https://huggingface.co/datasets/xiaowu0162/longmemeval-cleaned/resolve/main/{name}",
    "https://hf-mirror.com/datasets/xiaowu0162/longmemeval-cleaned/resolve/main/{name}",
]


def _looks_like_dataset(path: str, min_size: int) -> bool:
    try:
        if os.path.getsize(path) < min_size:
            return False
        with open(path, "rb") as handle:
            head = handle.read(64).lstrip()
        return head.startswith(b"[")
    except OSError:
        return False


def _sample_questions(path: str, max_bytes: int = 16 * 1024 * 1024) -> list[dict]:
    """Return the first complete question objects without loading the file."""
    with open(path, "rb") as handle:
        chunk = handle.read(max_bytes)
    chunk = chunk.decode("utf-8", errors="ignore")
    decoder = json.JSONDecoder()
    questions: list[dict] = []
    position = 0
    while position < len(chunk):
        while position < len(chunk) and chunk[position] in " \t\r\n,[]":
            position += 1
        if position >= len(chunk):
            break
        try:
            obj, end = decoder.raw_decode(chunk, position)
        except json.JSONDecodeError:
            break
        if isinstance(obj, dict):
            questions.append(obj)
        position = end
        while position < len(chunk) and chunk[position] in " \t\r\n,":
            position += 1
        if position >= len(chunk) or chunk[position] == "]":
            break
    return questions


def _validate(path: str, min_size: int) -> bool:
    if not _looks_like_dataset(path, min_size):
        return False
    sample = _sample_questions(path)
    if not sample:
        return False
    question = sample[0]
    required = {"question_id", "question_type", "question", "answer"}
    if not required <= set(question):
        return False
    sessions = question.get("haystack_sessions")
    return isinstance(sessions, list) and bool(sessions)


def _download(url: str, target: str, expected_min_size: int) -> bool:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "mnemosis-benchmark-fetcher/0.1"},
    )
    part = target + ".part"
    with urllib.request.urlopen(request, timeout=120) as response:
        total = int(response.headers.get("Content-Length") or 0)
        done = 0
        with open(part, "wb") as out:
            while True:
                block = response.read(1024 * 1024)
                if not block:
                    break
                out.write(block)
                done += len(block)
                if total:
                    percent = done * 100 // max(1, total)
                    print(
                        f"\r  {os.path.basename(target)}: "
                        f"{done / 1e6:.0f}/{total / 1e6:.0f} MB ({percent}%)",
                        end="",
                        flush=True,
                    )
    print()
    if done < expected_min_size:
        try:
            os.remove(part)
        except OSError:
            pass
        return False
    return True


def _ensure(name: str, force: bool, source_dir: str | None) -> str | None:
    target = os.path.join(_WORK, name)
    min_size = FILES[name]
    if not force and _validate(target, min_size):
        print(f"[cached] {name} ({os.path.getsize(target) / 1e6:.1f} MB)")
        return target
    if source_dir:
        candidate = os.path.join(source_dir, name)
        if _validate(candidate, min_size):
            os.makedirs(_WORK, exist_ok=True)
            shutil.copyfile(candidate, target)
            print(f"[copied] {name} <- {candidate}")
            return target
        print(f"[skip]   {name}: not found in --source-dir")
        return None
    os.makedirs(_WORK, exist_ok=True)
    if os.path.exists(target) and not _validate(target, min_size):
        print(
            f"[warn]   {name}: existing file failed validation; "
            "keeping it and trying a fresh download"
        )
    last_error = None
    for template in SOURCES:
        url = template.format(name=name)
        print(f"[fetch]  {name}\n  {url}")
        try:
            if _download(url, target, min_size):
                part = target + ".part"
                if _validate(part, min_size):
                    os.replace(part, target)
                    print(
                        f"[ok]     {name} "
                        f"({os.path.getsize(target) / 1e6:.1f} MB)"
                    )
                    return target
                try:
                    os.remove(part)
                except OSError:
                    pass
                print(f"[bad]    {name}: download failed validation, retrying mirror")
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_error = exc
            print(f"[fail]   {exc}")
    if last_error is not None:
        print(f"[error]  {name}: all sources failed ({last_error})")
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--all",
        action="store_true",
        help="also fetch the 2.7 GB multi-session set",
    )
    parser.add_argument(
        "--force", action="store_true", help="re-download even if cached"
    )
    parser.add_argument(
        "--source-dir",
        default=None,
        help="use an existing local directory with the JSON files",
    )
    args = parser.parse_args(argv)

    os.makedirs(_WORK, exist_ok=True)
    names = ["longmemeval_oracle.json", "longmemeval_s_cleaned.json"]
    if args.all:
        names.append("longmemeval_m_cleaned.json")
    results = {name: _ensure(name, args.force, args.source_dir) for name in names}
    ok = [name for name, path in results.items() if path]
    missing = [name for name, path in results.items() if not path]
    print(f"\nready: {len(ok)}/{len(names)}")
    for name in ok:
        print(f"  {name} -> {results[name]}")
    if missing:
        print("missing:")
        for name in missing:
            print(f"  {name}")
        print(
            "Manual fallback: download the files from\n"
            "  https://huggingface.co/datasets/xiaowu0162/longmemeval-cleaned\n"
            "and run with --source-dir <folder>"
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
