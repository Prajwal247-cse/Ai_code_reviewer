#!/usr/bin/env python3
"""
AI Code Reviewer — CLI Tool
Usage: python cli/reviewer.py --file path/to/code.py --lang python
       python cli/reviewer.py --code "print('hello')" --lang python
       python cli/reviewer.py --file app.js --lang javascript --output report.json
"""

import argparse
import json
import sys
import os
import requests
from pathlib import Path

# ── ANSI Colors ───────────────────────────────────────────────────────────────

RESET = "\033[0m"
BOLD = "\033[1m"
RED = "\033[91m"
ORANGE = "\033[33m"
YELLOW = "\033[93m"
GREEN = "\033[92m"
CYAN = "\033[96m"
BLUE = "\033[94m"
MAGENTA = "\033[95m"
DIM = "\033[2m"

SEVERITY_COLORS = {
    "critical": RED + BOLD,
    "high": ORANGE + BOLD,
    "medium": YELLOW,
    "low": CYAN,
    "info": DIM,
}

SEVERITY_ICONS = {
    "critical": "🔴",
    "high": "🟠",
    "medium": "🟡",
    "low": "🔵",
    "info": "⚪",
}

TYPE_ICONS = {
    "bug": "🐛",
    "security": "🔐",
    "performance": "⚡",
    "code_smell": "🤢",
    "best_practice": "📘",
    "naming": "🏷️",
    "complexity": "🌀",
    "duplicate": "🔁",
    "memory": "💾",
    "style": "✏️",
}

SUPPORTED_LANGS = [
    "python", "javascript", "typescript", "java",
    "go", "rust", "cpp", "c", "ruby", "php", "swift", "kotlin"
]

FILE_EXT_MAP = {
    ".py": "python", ".js": "javascript", ".ts": "typescript",
    ".java": "java", ".go": "go", ".rs": "rust", ".cpp": "cpp",
    ".c": "c", ".rb": "ruby", ".php": "php", ".swift": "swift",
    ".kt": "kotlin",
}


def detect_language(filepath: str) -> str:
    ext = Path(filepath).suffix.lower()
    return FILE_EXT_MAP.get(ext, "")


def print_banner():
    print(f"""
{CYAN}{BOLD}╔═══════════════════════════════════════╗
║     🤖  AI Code Reviewer  v1.0.0      ║
║     Powered by Claude + AST Analysis  ║
╚═══════════════════════════════════════╝{RESET}
""")


def print_summary(summary: dict):
    score = summary.get("overall_score", 0)
    score_color = GREEN if score >= 80 else YELLOW if score >= 60 else RED
    verdict = summary.get("verdict", "")

    print(f"\n{BOLD}{'─'*50}{RESET}")
    print(f"{BOLD}📊 Review Summary{RESET}")
    print(f"{'─'*50}")
    print(f"  Quality Score : {score_color}{BOLD}{score}/100{RESET}")
    print(f"  Verdict       : {verdict}")
    print(f"  Issues        : {RED}🔴 {summary.get('critical_count',0)} critical{RESET}  "
          f"{ORANGE}🟠 {summary.get('high_count',0)} high{RESET}  "
          f"{YELLOW}🟡 {summary.get('medium_count',0)} medium{RESET}  "
          f"{CYAN}🔵 {summary.get('low_count',0)} low{RESET}  "
          f"{DIM}⚪ {summary.get('info_count',0)} info{RESET}")

    strengths = summary.get("strengths", [])
    if strengths:
        print(f"\n  {GREEN}✅ Strengths:{RESET}")
        for s in strengths:
            print(f"     • {s}")

    priorities = summary.get("top_priorities", [])
    if priorities:
        print(f"\n  {RED}🎯 Top Priorities:{RESET}")
        for p in priorities:
            print(f"     1. {p}")
    print(f"{'─'*50}\n")


def print_issue(issue: dict, index: int):
    sev = issue.get("severity", "info")
    color = SEVERITY_COLORS.get(sev, "")
    icon = SEVERITY_ICONS.get(sev, "•")
    type_icon = TYPE_ICONS.get(issue.get("type", ""), "•")

    line_info = f"Line {issue['line']}" if issue.get("line") else "Global"
    if issue.get("line_end") and issue.get("line_end") != issue.get("line"):
        line_info += f"–{issue['line_end']}"

    conf = issue.get("confidence", 0)
    conf_display = f"{int(conf*100)}%" if conf else "?"

    print(f"  {color}{icon} [{sev.upper()}]{RESET} {type_icon} {BOLD}{issue.get('message','')}{RESET}")
    print(f"     {DIM}📍 {line_info}  |  Type: {issue.get('type','')}  |  Confidence: {conf_display}  |  Rule: {issue.get('rule_id','N/A')}{RESET}")
    print(f"     {BLUE}Why:{RESET} {issue.get('explanation','')}")
    print(f"     {GREEN}Fix:{RESET} {issue.get('suggestion','')}")

    if issue.get("fixed_code"):
        print(f"     {MAGENTA}Improved code:{RESET}")
        for line in issue["fixed_code"].splitlines():
            print(f"       {DIM}│{RESET} {line}")

    if issue.get("references"):
        print(f"     {DIM}📚 Refs: {', '.join(issue['references'][:2])}{RESET}")

    print()


def call_api(base_url: str, payload: dict) -> dict:
    url = f"{base_url}/api/v1/review"
    try:
        response = requests.post(url, json=payload, timeout=120)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError:
        print(f"{RED}✗ Cannot connect to API at {base_url}{RESET}")
        print(f"  Start the backend: {CYAN}cd backend && uvicorn main:app --reload{RESET}")
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        print(f"{RED}✗ API error: {e.response.status_code} — {e.response.text}{RESET}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="AI Code Reviewer CLI — review source code from terminal",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  python reviewer.py --file app.py
  python reviewer.py --file server.js --lang javascript
  python reviewer.py --code "eval(x)" --lang python
  python reviewer.py --file main.go --output report.json
  python reviewer.py --file Foo.java --focus security bug
        """
    )
    parser.add_argument("--file", "-f", help="Path to source file to review")
    parser.add_argument("--code", "-c", help="Inline code string to review")
    parser.add_argument("--lang", "-l", help=f"Language ({', '.join(SUPPORTED_LANGS)})")
    parser.add_argument("--output", "-o", help="Save JSON output to file")
    parser.add_argument("--api", default="http://localhost:8000", help="API base URL")
    parser.add_argument("--no-refactor", action="store_true", help="Skip refactored code output")
    parser.add_argument("--focus", nargs="+",
                        choices=["bug","security","performance","code_smell","best_practice","naming","complexity","duplicate","memory","style"],
                        help="Focus on specific issue types")
    parser.add_argument("--min-severity", choices=["info","low","medium","high","critical"],
                        default="info", help="Only show issues at or above this severity")
    parser.add_argument("--quiet", "-q", action="store_true", help="Show summary only")
    args = parser.parse_args()

    # ── Load code ────────────────────────────────────────────────────────────
    if args.file:
        path = Path(args.file)
        if not path.exists():
            print(f"{RED}✗ File not found: {args.file}{RESET}")
            sys.exit(1)
        code = path.read_text(encoding="utf-8")
        filename = str(path)
        lang = args.lang or detect_language(args.file)
        if not lang:
            print(f"{RED}✗ Could not auto-detect language. Use --lang{RESET}")
            sys.exit(1)
    elif args.code:
        code = args.code
        filename = None
        lang = args.lang
        if not lang:
            print(f"{RED}✗ --lang required when using --code{RESET}")
            sys.exit(1)
    else:
        parser.print_help()
        sys.exit(0)

    print_banner()
    print(f"  File     : {filename or '<inline>'}")
    print(f"  Language : {lang}")
    print(f"  Lines    : {code.count(chr(10))+1}")
    print(f"  API      : {args.api}")
    if args.focus:
        print(f"  Focus    : {', '.join(args.focus)}")
    print(f"\n  {CYAN}⟳ Sending to AI Code Reviewer...{RESET}\n")

    # ── Call API ─────────────────────────────────────────────────────────────
    payload = {
        "code": code,
        "language": lang,
        "filename": filename,
        "include_refactor": not args.no_refactor,
    }
    if args.focus:
        payload["focus_areas"] = args.focus

    result = call_api(args.api, payload)

    # ── Print results ─────────────────────────────────────────────────────────
    severity_order = ["info","low","medium","high","critical"]
    min_idx = severity_order.index(args.min_severity)

    issues = result.get("issues", [])
    filtered = [i for i in issues if severity_order.index(i.get("severity","info")) >= min_idx]

    if not args.quiet and filtered:
        print(f"{BOLD}📋 Issues Found ({len(filtered)}/{len(issues)} shown){RESET}\n")
        for idx, issue in enumerate(filtered, 1):
            print(f"  {DIM}[{idx}/{len(filtered)}]{RESET}")
            print_issue(issue, idx)

    print_summary(result.get("summary", {}))

    if not args.no_refactor and result.get("refactored_code") and not args.quiet:
        print(f"{BOLD}🔧 Refactored Code{RESET}")
        print(f"{'─'*50}")
        for line in result["refactored_code"].splitlines():
            print(f"  {line}")
        print()

    meta = result.get("analysis_metadata", {})
    print(f"{DIM}⏱  Processed in {result.get('processing_time_ms',0):.0f}ms  |  "
          f"Static hints: {meta.get('static_hints_count',0)}  |  "
          f"Request ID: {result.get('request_id','')[:8]}...{RESET}")

    # ── Save output ──────────────────────────────────────────────────────────
    if args.output:
        with open(args.output, "w") as f:
            json.dump(result, f, indent=2)
        print(f"\n{GREEN}✓ Full JSON report saved to: {args.output}{RESET}")

    # Exit with non-zero if critical issues found
    if result.get("summary", {}).get("critical_count", 0) > 0:
        sys.exit(2)


if __name__ == "__main__":
    main()
