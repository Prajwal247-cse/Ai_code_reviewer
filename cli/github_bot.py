"""
GitHub PR Review Bot
Triggered via GitHub Actions or manual run.
Fetches changed files, runs AI review, posts inline comments.

Usage:
  GITHUB_TOKEN=xxx PR_NUMBER=42 REPO=owner/repo python github_bot.py

Or via GitHub Actions (see .github/workflows/code-review.yml)
"""

import os
import sys
import json
import logging
import requests
from pathlib import Path

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

REVIEWER_API = os.environ.get("REVIEWER_API_URL", "http://localhost:8000")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
REPO = os.environ.get("GITHUB_REPOSITORY", "")        # e.g. "octocat/hello-world"
PR_NUMBER = os.environ.get("PR_NUMBER") or os.environ.get("GITHUB_PR_NUMBER", "")
MAX_FILES = int(os.environ.get("MAX_FILES", "10"))

FILE_EXT_LANG = {
    ".py": "python", ".js": "javascript", ".ts": "typescript",
    ".java": "java", ".go": "go", ".rs": "rust",
}

GH_API = "https://api.github.com"


def gh_headers():
    return {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def get_pr_files(repo: str, pr_number: str) -> list:
    url = f"{GH_API}/repos/{repo}/pulls/{pr_number}/files"
    r = requests.get(url, headers=gh_headers())
    r.raise_for_status()
    return r.json()


def get_file_content(repo: str, ref: str, filepath: str) -> str:
    url = f"{GH_API}/repos/{repo}/contents/{filepath}?ref={ref}"
    r = requests.get(url, headers=gh_headers())
    r.raise_for_status()
    import base64
    content = r.json().get("content", "")
    return base64.b64decode(content).decode("utf-8", errors="replace")


def get_pr_head_sha(repo: str, pr_number: str) -> str:
    url = f"{GH_API}/repos/{repo}/pulls/{pr_number}"
    r = requests.get(url, headers=gh_headers())
    r.raise_for_status()
    return r.json()["head"]["sha"]


def review_code(code: str, language: str, filename: str) -> dict:
    payload = {
        "code": code,
        "language": language,
        "filename": filename,
        "include_refactor": False,
    }
    r = requests.post(f"{REVIEWER_API}/api/v1/review", json=payload, timeout=120)
    r.raise_for_status()
    return r.json()


def post_pr_review(repo: str, pr_number: str, head_sha: str, comments: list, summary_body: str):
    """Post a review with inline comments to the PR."""
    url = f"{GH_API}/repos/{repo}/pulls/{pr_number}/reviews"
    payload = {
        "commit_id": head_sha,
        "body": summary_body,
        "event": "COMMENT",   # Use "REQUEST_CHANGES" for blocking
        "comments": comments,
    }
    r = requests.post(url, headers=gh_headers(), json=payload)
    r.raise_for_status()
    return r.json()


def build_issue_comment(issue: dict) -> str:
    sev = issue.get("severity", "info").upper()
    icons = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🔵", "INFO": "⚪"}
    icon = icons.get(sev, "•")
    type_icons = {"bug":"🐛","security":"🔐","performance":"⚡","code_smell":"🤢","best_practice":"📘"}
    type_icon = type_icons.get(issue.get("type",""), "•")

    lines = [
        f"### {icon} [{sev}] {type_icon} {issue.get('message','')}",
        f"",
        f"**Why this is a problem:**",
        f"{issue.get('explanation','')}",
        f"",
        f"**Suggestion:** {issue.get('suggestion','')}",
    ]
    if issue.get("fixed_code"):
        lines += [f"", f"**Improved code:**", f"```", issue["fixed_code"], f"```"]
    if issue.get("references"):
        lines += [f"", f"📚 **References:** " + " | ".join(f"[link]({r})" for r in issue["references"][:2])]
    conf = issue.get("confidence", 0)
    lines += [f"", f"*Confidence: {int(conf*100)}% | Rule: {issue.get('rule_id','N/A')} | AI Code Reviewer*"]
    return "\n".join(lines)


def build_pr_summary(all_reviews: list) -> str:
    total_issues = sum(len(r["issues"]) for r in all_reviews)
    critical = sum(r["summary"]["critical_count"] for r in all_reviews)
    high = sum(r["summary"]["high_count"] for r in all_reviews)

    verdict = "✅ Looks good!" if (critical + high) == 0 else f"⚠️ Found {critical} critical and {high} high-severity issues."

    lines = [
        "## 🤖 AI Code Review Summary",
        f"",
        f"**{verdict}**",
        f"",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Files Reviewed | {len(all_reviews)} |",
        f"| Total Issues | {total_issues} |",
        f"| Critical | 🔴 {critical} |",
        f"| High | 🟠 {high} |",
        f"| Medium | 🟡 {sum(r['summary']['medium_count'] for r in all_reviews)} |",
        f"| Low | 🔵 {sum(r['summary']['low_count'] for r in all_reviews)} |",
        f"",
        f"*Automated review by [AI Code Reviewer](https://github.com). "
        f"Review suggestions before acting on them.*",
    ]
    return "\n".join(lines)


def main():
    if not GITHUB_TOKEN:
        logger.error("GITHUB_TOKEN not set")
        sys.exit(1)
    if not REPO or not PR_NUMBER:
        logger.error("GITHUB_REPOSITORY and PR_NUMBER must be set")
        sys.exit(1)

    logger.info(f"Reviewing PR #{PR_NUMBER} in {REPO}")

    pr_files = get_pr_files(REPO, PR_NUMBER)
    head_sha = get_pr_head_sha(REPO, PR_NUMBER)
    logger.info(f"PR has {len(pr_files)} changed files. Head SHA: {head_sha[:8]}")

    all_reviews = []
    gh_comments = []

    for pr_file in pr_files[:MAX_FILES]:
        filepath = pr_file["filename"]
        ext = Path(filepath).suffix.lower()
        language = FILE_EXT_LANG.get(ext)

        if not language:
            logger.info(f"Skipping {filepath} (unsupported extension)")
            continue
        if pr_file.get("status") == "removed":
            continue

        logger.info(f"Reviewing {filepath} ({language})")
        try:
            code = get_file_content(REPO, head_sha, filepath)
            review = review_code(code, language, filepath)
            all_reviews.append(review)

            # Map issues to GitHub inline comments
            for issue in review["issues"]:
                if issue.get("severity") in ("critical", "high", "medium") and issue.get("line"):
                    gh_comments.append({
                        "path": filepath,
                        "line": issue["line"],
                        "side": "RIGHT",
                        "body": build_issue_comment(issue),
                    })
        except Exception as e:
            logger.warning(f"Failed to review {filepath}: {e}")

    if not all_reviews:
        logger.info("No supported files to review.")
        return

    summary = build_pr_summary(all_reviews)
    logger.info(f"Posting review with {len(gh_comments)} inline comments...")

    result = post_pr_review(REPO, PR_NUMBER, head_sha, gh_comments, summary)
    logger.info(f"✅ Review posted: {result.get('html_url','')}")

    # Save full report
    with open("pr_review_report.json", "w") as f:
        json.dump({"reviews": all_reviews, "pr": REPO, "pr_number": PR_NUMBER}, f, indent=2)
    logger.info("Full report saved to pr_review_report.json")


if __name__ == "__main__":
    main()
