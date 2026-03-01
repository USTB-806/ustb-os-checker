#!/usr/bin/env python3
"""
Platform entrypoint for ustb-os-checker.
- Keeps test_runner.py unchanged for local debugging.
- Runs test_runner.py and outputs ONE JSON object to stdout for grading platform.
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


CHECKER_DIR = Path(__file__).parent.absolute()


def classify_failure(output: str) -> str:
    text = (output or "").lower()
    infra_markers = [
        "operation not permitted",
        "no usable cargo/rustc pair",
        "unable to install ctrlc handler",
        "rust toolchain not found",
        "kernel build failed",
        "build fs.img failed",
        "qemu run failed",
        "traceback (most recent call last)",
    ]
    for marker in infra_markers:
        if marker in text:
            return "RE"
    return "WA"


def build_result(verdict: str, score: int, comment: str, detail: str = "") -> dict:
    return {
        "verdict": verdict,
        "score": int(max(0, score)),
        "comment": comment,
        "detail": detail,
    }


def save_persisted(result: dict, log_text: str) -> None:
    persisted = Path("/coursegrader/persisted")
    if not persisted.exists():
        return

    user_id = os.environ.get("CGUSERID", "unknown")
    user_dir = persisted / user_id
    user_dir.mkdir(parents=True, exist_ok=True)

    (user_dir / "judge_result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (user_dir / "judge_log.txt").write_text(log_text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="ustb-os-checker platform judge")
    parser.add_argument("--chapter", type=int, default=None, help="chapter number, e.g. 2")
    parser.add_argument(
        "--show-log",
        action="store_true",
        help="print original test_runner output to stderr for debugging",
    )
    args = parser.parse_args()

    chapter = args.chapter
    if chapter is None:
        chapter_env = os.environ.get("CHAPTER", "")
        if chapter_env.isdigit():
            chapter = int(chapter_env)

    if chapter is None:
        result = build_result("RE", 0, "missing chapter", "set --chapter or CHAPTER env")
        print(json.dumps(result, ensure_ascii=False))
        return 0

    cmd = [sys.executable, "test_runner.py", str(chapter)]

    try:
        proc = subprocess.run(
            cmd,
            cwd=CHECKER_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=180,
        )
        output = proc.stdout or ""

        if args.show_log:
            print(output, file=sys.stderr, end="")

        if proc.returncode == 0:
            result = build_result("AC", 100, f"chapter {chapter} passed", output[-8000:])
        else:
            verdict = classify_failure(output)
            result = build_result(verdict, 0, f"chapter {chapter} failed", output[-8000:])

    except subprocess.TimeoutExpired as e:
        output = (e.stdout or "") if isinstance(e.stdout, str) else ""
        if args.show_log and output:
            print(output, file=sys.stderr, end="")
        result = build_result("TLE", 0, f"chapter {chapter} timeout", output[-8000:])
    except Exception as e:
        result = build_result("RE", 0, "judge internal error", str(e))
        output = str(e)

    save_persisted(result, output)
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
