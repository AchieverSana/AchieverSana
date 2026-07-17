#!/usr/bin/env python3
"""
Fetches all merged pull requests authored by GITHUB_USERNAME across all of
GitHub and rewrites two things inside README.md:

  1. The PR list between <!-- MERGED_PRS:START --> / <!-- MERGED_PRS:END -->
  2. Every occurrence of <!-- PR_COUNT -->N<!-- /PR_COUNT --> is updated to
     the live merged-PR count, so the number never goes stale again.

Requires: requests
Env vars:
  GITHUB_TOKEN      - provided automatically by GitHub Actions
  GITHUB_USERNAME   - the account whose merged PRs we track
  README_PATH       - path to README.md (default: README.md)
  MAX_PRS           - max number of PRs to list (default: 10)
"""

import os
import re
import sys
import requests

USERNAME = os.environ.get("GITHUB_USERNAME", "AchieverSana")
TOKEN = os.environ.get("GITHUB_TOKEN")
README_PATH = os.environ.get("README_PATH", "README.md")
MAX_PRS = int(os.environ.get("MAX_PRS", "10"))

LIST_START = "<!-- MERGED_PRS:START -->"
LIST_END = "<!-- MERGED_PRS:END -->"

COUNT_START = "<!-- PR_COUNT -->"
COUNT_END = "<!-- /PR_COUNT -->"

API_URL = "https://api.github.com/search/issues"


def fetch_merged_prs():
    headers = {"Accept": "application/vnd.github+json"}
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"

    params = {
        "q": f"is:pr is:merged author:{USERNAME}",
        "sort": "updated",
        "order": "desc",
        "per_page": MAX_PRS,
    }

    resp = requests.get(API_URL, headers=headers, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    return data.get("items", []), data.get("total_count", 0)


def format_entry(item):
    repo_url = item["html_url"].rsplit("/pull/", 1)[0]
    repo_full_name = "/".join(repo_url.rstrip("/").split("/")[-2:])
    title = item["title"].strip()
    pr_url = item["html_url"]
    pr_number = item["number"]
    return f"- **[{repo_full_name}]({repo_url})** — {title} ([#{pr_number}]({pr_url}))"


def build_list_section(items):
    if not items:
        return f"{LIST_START}\n_No merged pull requests found yet._\n{LIST_END}"
    lines = [format_entry(item) for item in items]
    return f"{LIST_START}\n" + "\n".join(lines) + f"\n{LIST_END}"


def replace_between(content, start_marker, end_marker, new_inner, wrap_markers=True):
    pattern = re.compile(
        re.escape(start_marker) + r".*?" + re.escape(end_marker), re.DOTALL
    )
    if not pattern.search(content):
        print(f"Markers {start_marker} / {end_marker} not found — skipping.")
        return content, False
    replacement = new_inner if wrap_markers else f"{start_marker}{new_inner}{end_marker}"
    updated = pattern.sub(replacement, content)
    return updated, updated != content


def update_readme(list_section, total_count):
    with open(README_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    original = content

    content, _ = replace_between(content, LIST_START, LIST_END, list_section)
    content, _ = replace_between(
        content, COUNT_START, COUNT_END, str(total_count), wrap_markers=False
    )

    if content == original:
        print("No changes to README.")
        return False

    with open(README_PATH, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"README.md updated — {total_count} merged PRs.")
    return True


def main():
    items, total_count = fetch_merged_prs()
    list_section = build_list_section(items)
    update_readme(list_section, total_count)


if __name__ == "__main__":
    main()
