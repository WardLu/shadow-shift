"""Validate the open-source release metadata for Shadow Shift."""

from __future__ import annotations

import os
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def latest_changelog_section(changelog: str) -> tuple[str, str]:
    match = re.search(r"^##\s+\[?(\d+\.\d+\.\d+)\]?[^\n]*$", changelog, re.MULTILINE)
    if not match:
        raise ValueError("CHANGELOG.md 缺少最新语义化版本标题")
    rest = changelog[match.end() :]
    next_heading = re.search(r"^##\s+", rest, re.MULTILINE)
    end = match.end() + (next_heading.start() if next_heading else len(rest))
    return match.group(1), changelog[match.start() : end].strip()


def validate_release_metadata(root: Path = ROOT, release_tag: str = "") -> dict[str, str]:
    version, section = latest_changelog_section((root / "CHANGELOG.md").read_text(encoding="utf-8"))
    expected_tag = f"v{version}"
    if release_tag and release_tag != expected_tag:
        raise ValueError(f"Release Tag {release_tag} 必须匹配 {expected_tag}")

    body = re.sub(r"^##[^\n]+\n?", "", section).strip()
    if not body:
        raise ValueError("最新版本发布说明为空")
    if re.fullmatch(r"Released on \d{4}-\d{2}-\d{2}", body, re.IGNORECASE):
        raise ValueError("发布说明不能使用日期占位文案")
    if len(body) < 40:
        raise ValueError("最新版本发布说明过短")

    readme = (root / "README.md").read_text(encoding="utf-8")
    if f"version-{version}-green" not in readme:
        raise ValueError(f"README.md 版本徽章必须指向 {version}")
    return {"version": version, "tag": expected_tag, "notes": section}


if __name__ == "__main__":
    metadata = validate_release_metadata(release_tag=os.environ.get("RELEASE_TAG", ""))
    print(f"Release metadata validated for {metadata['tag']}")
