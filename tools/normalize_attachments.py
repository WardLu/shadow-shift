#!/usr/bin/env python3
"""
Normalize WizNote note-local attachments for Obsidian.

This tool rewrites note-local references like `Some Note_files/foo.png` into a
single vault-level `attachments/` directory and updates Markdown links
accordingly. Before modifying a Markdown file, it creates a side-by-side backup
with the `.attachbak` suffix.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
from pathlib import Path


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg"}
MARKDOWN_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)\n]+)\)")
MARKDOWN_LINK_RE = re.compile(r"(?<!!)\[([^\]]+)\]\(([^)\n]+)\)")
HTML_IMAGE_RE = re.compile(
    r'<img\b([^>]*?)\bsrc=["\']([^"\']+)["\']([^>]*)>',
    re.IGNORECASE,
)
EMPTY_IMAGE_RE = re.compile(r"!\[[^\]]*\]\(\s*\)")
WIKILINK_RE = re.compile(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]")


class AttachmentNormalizer:
    def __init__(
        self,
        vault_dir: Path,
        dry_run: bool = False,
        remove_empty_placeholders: bool = False,
        delete_unreferenced_images: bool = False,
    ) -> None:
        self.vault_dir = vault_dir
        self.attachments_dir = vault_dir / "attachments"
        self.dry_run = dry_run
        self.remove_empty_placeholders = remove_empty_placeholders
        self.delete_unreferenced_images = delete_unreferenced_images
        self.updated_files = 0
        self.moved_images = 0
        self.moved_attachments = 0
        self.deleted_dirs = 0
        self.created_backups = 0
        self.empty_placeholders_removed = 0
        self.skipped_missing: list[str] = []
        self.unreferenced_images: list[str] = []
        self.source_to_dest: dict[str, str] = {}

    @staticmethod
    def normalize_source(raw_path: str) -> str:
        path = raw_path.strip()
        if path.startswith("<") and path.endswith(">"):
            path = path[1:-1].strip()
        return path

    def is_local_files_ref(self, raw_path: str) -> bool:
        path = self.normalize_source(raw_path)
        if not path or "://" in path or path.startswith("data:") or path.startswith("/"):
            return False
        return "_files/" in path

    def is_local_image_ref(self, raw_path: str) -> bool:
        path = self.normalize_source(raw_path)
        return self.is_local_files_ref(path) and Path(path).suffix.lower() in IMAGE_EXTENSIONS

    def resolve_source_path(self, md_path: Path, raw_path: str) -> Path:
        return (md_path.parent / self.normalize_source(raw_path)).resolve()

    def destination_for(self, source_path: Path) -> Path:
        parent_name = source_path.parent.name
        base_name = source_path.name
        candidate = self.attachments_dir / f"{parent_name}__{base_name}"
        counter = 1
        while candidate.exists() and candidate.resolve() != source_path.resolve():
            candidate = (
                self.attachments_dir
                / f"{parent_name}__{source_path.stem}_{counter}{source_path.suffix}"
            )
            counter += 1
        return candidate

    def ensure_file_moved(self, source_path: Path) -> str | None:
        source_key = str(source_path)
        if source_key in self.source_to_dest:
            return self.source_to_dest[source_key]

        if not source_path.exists() or not source_path.is_file():
            self.skipped_missing.append(str(source_path))
            return None

        dest_path = self.destination_for(source_path)
        dest_rel = dest_path.relative_to(self.vault_dir).as_posix()
        self.source_to_dest[source_key] = dest_rel

        if dest_path.exists():
            return dest_rel

        if not self.dry_run:
            self.attachments_dir.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source_path), str(dest_path))

        if source_path.suffix.lower() in IMAGE_EXTENSIONS:
            self.moved_images += 1
        else:
            self.moved_attachments += 1
        return dest_rel

    def replace_markdown_images(self, text: str, md_path: Path) -> tuple[str, bool]:
        changed = False

        def repl(match: re.Match[str]) -> str:
            nonlocal changed
            raw_path = match.group(2)
            if not self.is_local_image_ref(raw_path):
                return match.group(0)

            source_path = self.resolve_source_path(md_path, raw_path)
            dest_rel = self.ensure_file_moved(source_path)
            if not dest_rel:
                return match.group(0)

            changed = True
            return f"![[{dest_rel}]]"

        return MARKDOWN_IMAGE_RE.sub(repl, text), changed

    def replace_html_images(self, text: str, md_path: Path) -> tuple[str, bool]:
        changed = False

        def repl(match: re.Match[str]) -> str:
            nonlocal changed
            raw_path = match.group(2)
            if not self.is_local_image_ref(raw_path):
                return match.group(0)

            source_path = self.resolve_source_path(md_path, raw_path)
            dest_rel = self.ensure_file_moved(source_path)
            if not dest_rel:
                return match.group(0)

            changed = True
            return f"![[{dest_rel}]]"

        return HTML_IMAGE_RE.sub(repl, text), changed

    def replace_wikilinks(self, text: str, md_path: Path) -> tuple[str, bool]:
        changed = False

        def repl(match: re.Match[str]) -> str:
            nonlocal changed
            raw_path = match.group(1)
            label = match.group(2)
            if not self.is_local_files_ref(raw_path):
                return match.group(0)

            source_path = self.resolve_source_path(md_path, raw_path)
            dest_rel = self.ensure_file_moved(source_path)
            if not dest_rel:
                return match.group(0)

            changed = True
            if label:
                return f"[[{dest_rel}|{label}]]"
            return f"[[{dest_rel}]]"

        return WIKILINK_RE.sub(repl, text), changed

    def replace_markdown_links(self, text: str, md_path: Path) -> tuple[str, bool]:
        changed = False

        def repl(match: re.Match[str]) -> str:
            nonlocal changed
            label = match.group(1)
            raw_path = match.group(2)
            if not self.is_local_files_ref(raw_path):
                return match.group(0)

            source_path = self.resolve_source_path(md_path, raw_path)
            dest_rel = self.ensure_file_moved(source_path)
            if not dest_rel:
                return match.group(0)

            changed = True
            if Path(self.normalize_source(raw_path)).suffix.lower() in IMAGE_EXTENSIONS:
                return f"![[{dest_rel}]]"
            return f"[[{dest_rel}|{label}]]"

        return MARKDOWN_LINK_RE.sub(repl, text), changed

    def backup_markdown(self, md_path: Path) -> None:
        backup_path = Path(str(md_path) + ".attachbak")
        if backup_path.exists():
            return
        if not self.dry_run:
            shutil.copy2(md_path, backup_path)
        self.created_backups += 1

    def process_markdown(self, md_path: Path) -> bool:
        original = md_path.read_text(encoding="utf-8", errors="ignore")
        updated = original

        updated, changed_md = self.replace_markdown_images(updated, md_path)
        updated, changed_html = self.replace_html_images(updated, md_path)
        updated, changed_wiki = self.replace_wikilinks(updated, md_path)
        updated, changed_links = self.replace_markdown_links(updated, md_path)
        changed = changed_md or changed_html or changed_wiki or changed_links

        if self.remove_empty_placeholders:
            placeholder_count = len(EMPTY_IMAGE_RE.findall(updated))
            if placeholder_count:
                updated = EMPTY_IMAGE_RE.sub("", updated)
                self.empty_placeholders_removed += placeholder_count
                changed = True

        if not changed:
            return False

        self.backup_markdown(md_path)
        if not self.dry_run:
            md_path.write_text(updated, encoding="utf-8")
        self.updated_files += 1
        return True

    def cleanup_empty_files_dirs(self) -> None:
        for files_dir in sorted(self.vault_dir.rglob("*_files"), reverse=True):
            if not files_dir.is_dir():
                continue
            if any(files_dir.iterdir()):
                continue
            if not self.dry_run:
                files_dir.rmdir()
            self.deleted_dirs += 1

    def cleanup_unreferenced_images(self) -> None:
        for files_dir in sorted(self.vault_dir.rglob("*_files")):
            if not files_dir.is_dir():
                continue

            image_files = [
                path
                for path in files_dir.iterdir()
                if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
            ]
            self.unreferenced_images.extend(str(path) for path in image_files)

            if self.delete_unreferenced_images and not self.dry_run:
                for path in image_files:
                    path.unlink()

            if self.delete_unreferenced_images and not self.dry_run and not any(files_dir.iterdir()):
                files_dir.rmdir()
                self.deleted_dirs += 1

    def run(self) -> dict[str, int]:
        for md_path in sorted(self.vault_dir.rglob("*.md")):
            self.process_markdown(md_path)

        self.cleanup_empty_files_dirs()
        self.cleanup_unreferenced_images()

        return {
            "updated_files": self.updated_files,
            "moved_images": self.moved_images,
            "moved_attachments": self.moved_attachments,
            "deleted_dirs": self.deleted_dirs,
            "created_backups": self.created_backups,
            "missing_sources": len(self.skipped_missing),
            "empty_placeholders_removed": self.empty_placeholders_removed,
            "unreferenced_images": len(self.unreferenced_images),
        }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Move note-local files from *_files into /attachments, rewrite Markdown "
            "for Obsidian, and optionally delete unreferenced leftover icons/images."
        )
    )
    parser.add_argument(
        "vault",
        nargs="?",
        default=str(Path(__file__).resolve().parent.parent / "wiznote_obsidian"),
        help="Vault directory to process (default: ./wiznote_obsidian)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would change without writing files",
    )
    parser.add_argument(
        "--remove-empty-placeholders",
        action="store_true",
        help="Remove empty image placeholders like ![]() from Markdown files",
    )
    parser.add_argument(
        "--delete-unreferenced-images",
        action="store_true",
        help=(
            "Delete leftover image files still sitting in *_files after migration. "
            "This also cleans up empty leftover icon directories such as "
            "wizIcon_icons_{s,m,l}.png exports when they are no longer referenced."
        ),
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    vault_dir = Path(os.path.abspath(os.path.expanduser(args.vault)))
    if not vault_dir.is_dir():
        raise SystemExit(f"Directory not found: {vault_dir}")

    normalizer = AttachmentNormalizer(
        vault_dir=vault_dir,
        dry_run=args.dry_run,
        remove_empty_placeholders=args.remove_empty_placeholders,
        delete_unreferenced_images=args.delete_unreferenced_images,
    )
    result = normalizer.run()

    print(f"Updated markdown files: {result['updated_files']}")
    print(f"Moved images: {result['moved_images']}")
    print(f"Moved non-image attachments: {result['moved_attachments']}")
    print(f"Deleted empty _files dirs: {result['deleted_dirs']}")
    print(f"Created markdown backups: {result['created_backups']}")
    print(f"Missing source files: {result['missing_sources']}")
    print(f"Empty image placeholders removed: {result['empty_placeholders_removed']}")
    print(f"Unreferenced leftover images: {result['unreferenced_images']}")

    if normalizer.skipped_missing:
        print("\nMissing sources:")
        for item in normalizer.skipped_missing[:50]:
            print(item)
        if len(normalizer.skipped_missing) > 50:
            print(f"... and {len(normalizer.skipped_missing) - 50} more")

    if normalizer.unreferenced_images:
        print("\nUnreferenced images:")
        for item in normalizer.unreferenced_images[:200]:
            print(item)
        if len(normalizer.unreferenced_images) > 200:
            print(f"... and {len(normalizer.unreferenced_images) - 200} more")


if __name__ == "__main__":
    main()
