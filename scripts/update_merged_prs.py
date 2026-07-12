#!/usr/bin/env python3
"""
Fetches all merged pull requests authored by GITHUB_USERNAME across all of
GitHub and rewrites the section of README.md between the
<!-- MERGED_PRS:START --> / <!-- MERGED_PRS:END --> markers.

Requires: requests
Env vars:
  GITHUB_TOKEN     - provided automatically by GitHub Actions
  GITHUB_USERNAME  - the account whose merged PRs we track
  README_PATH      - path to README.md (default: README.md)
  MAX_PRS          - max number of PRs to list (default: 10)
"""

import os
import re
import sys
import requests

USERNAME = os.environ.get("GITHUB_USERNAME", "AchieverSana")
TOKEN = os.environ.get("GITHUB_TOKEN")
README_PATH = os.environ.get("README_PATH", "README.md")
MAX_PRS = int(os.environ.get("MAX_PRS", "10"))

START_MARKER = "<!-- MERGED_PRS:START -->"
END_MARKER = "<!-- MERGED_PRS:END -->"

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
    return resp.json().get("items", [])


def format_entry(item):
    repo_url = item["html_url"].rsplit("/pull/", 1)[0]
    repo_full_name = "/".join(repo_url.rstrip("/").split("/")[-2:])
    title = item["title"].strip()
    pr_url = item["html_url"]
    pr_number = item["number"]
    return f"- **[{repo_full_name}]({repo_url})** — {title} ([#{pr_number}]({pr_url}))"


def build_section(items):
    if not items:
        return f"{START_MARKER}\n_No merged pull requests found yet._\n{END_MARKER}"
    lines = [format_entry(item) for item in items]
    return f"{START_MARKER}\n" + "\n".join(lines) + f"\n{END_MARKER}"


def update_readme(new_section):
    with open(README_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    pattern = re.compile(
        re.escape(START_MARKER) + r".*?" + re.escape(END_MARKER), re.DOTALL
    )

    if not pattern.search(content):
        print(f"Markers {START_MARKER} / {END_MARKER} not found in {README_PATH}.")
        sys.exit(1)

    updated = pattern.sub(new_section, content)

    if updated == content:
        print("No changes to merged PR list.")
        return False

    with open(README_PATH, "w", encoding="utf-8") as f:
        f.write(updated)
    print("README.md merged PR section updated.")
    return True


def main():
    items = fetch_merged_prs()
    section = build_section(items)
    update_readme(section)


if __name__ == "__main__":
    main()
