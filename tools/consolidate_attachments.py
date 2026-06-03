#!/usr/bin/env python3
"""
附件整合工具 - 将散落的资源目录统一到顶层 attachments/

匹配的目录名和后缀可通过 config.json 的 cleanup.resource_dir_names 和 cleanup.resource_dir_suffixes 配置。

三种模式：
  scan     仅扫描并报告散落的资源目录
  dry-run  模拟迁移，显示将要执行的操作但不实际修改
  migrate  执行迁移：移动文件 → 更新引用 → 清理空目录

用法：
  python3 tools/consolidate_attachments.py scan /path/to/vault
  python3 tools/consolidate_attachments.py dry-run /path/to/vault
  python3 tools/consolidate_attachments.py migrate /path/to/vault
"""
import argparse
import json
import os
import re
import shutil
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


# 默认匹配的目录名（可通过 config.json 的 cleanup.resource_dir_names 覆盖）
_RESOURCE_DIR_NAMES = {"attachments", "images", "all_image", "all_images"}

# 默认匹配的目录后缀（可通过 config.json 的 cleanup.resource_dir_suffixes 覆盖）
_RESOURCE_DIR_SUFFIXES = {"_files"}


def _load_cleanup_config() -> dict:
    """从 config.json 加载清理配置"""
    config_path = Path(__file__).parent / "config.json"
    if not config_path.exists():
        config_path = Path(__file__).parent / "config.example.json"
    if not config_path.exists():
        return {}
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("cleanup", {})
    except Exception:
        return {}


_cleanup_cfg = _load_cleanup_config()

if "resource_dir_names" in _cleanup_cfg:
    _RESOURCE_DIR_NAMES = set(_cleanup_cfg["resource_dir_names"])
if "resource_dir_suffixes" in _cleanup_cfg:
    _RESOURCE_DIR_SUFFIXES = set(_cleanup_cfg["resource_dir_suffixes"])


class AttachmentConsolidator:
    """附件整合器"""

    def __init__(self, vault_dir: str, dry_run: bool = False):
        self.vault_dir = Path(vault_dir).resolve()
        self.dry_run = dry_run
        self.target_dir = self.vault_dir / "attachments"

        # 统计
        self.scanned_dirs: List[Path] = []
        self.moved_files: List[Dict] = []
        self.updated_notes: List[Dict] = []
        self.cleaned_dirs: List[Path] = []
        self.errors: List[Dict] = []
        self.skipped_files: List[Dict] = []

        # 预计算：迁移后 attachments/ 中会存在的文件名集合（用于引用更新）
        self._target_filenames: Set[str] = set()
        # 已处理的源文件（移动 + 跳过的重复），用于清理判断
        self._processed_src_files: Set[Path] = set()

    # ── 扫描 ──────────────────────────────────────────────

    def scan(self) -> Dict:
        """扫描散落的资源目录"""
        self.scanned_dirs = []

        for root, dirs, files in os.walk(self.vault_dir):
            root_path = Path(root)

            # 跳过 .obsidian, .trash, 目标目录本身
            if self._should_skip(root_path):
                continue

            dir_name = root_path.name

            # 匹配配置中的资源目录名和后缀
            is_name_match = dir_name in _RESOURCE_DIR_NAMES and root_path != self.target_dir
            is_suffix_match = any(dir_name.endswith(s) for s in _RESOURCE_DIR_SUFFIXES)

            if is_name_match or is_suffix_match:
                sub_files = [f for f in root_path.iterdir() if f.is_file()]
                if sub_files:
                    self.scanned_dirs.append(root_path)

        # 统计
        total_files = 0
        total_size = 0
        dir_details = []
        self._target_filenames = set()

        # 顶层 attachments 已有的文件也算进去
        if self.target_dir.is_dir():
            for f in self.target_dir.iterdir():
                if f.is_file():
                    self._target_filenames.add(f.name)

        for d in sorted(self.scanned_dirs):
            files = [f for f in d.iterdir() if f.is_file()]
            size = sum(f.stat().st_size for f in files)
            total_files += len(files)
            total_size += size
            if any(d.name.endswith(s) for s in _RESOURCE_DIR_SUFFIXES):
                dir_type = "_files"
            elif d.name in _RESOURCE_DIR_NAMES:
                dir_type = d.name
            else:
                dir_type = "attachments"
            dir_details.append({
                "path": str(d.relative_to(self.vault_dir)),
                "file_count": len(files),
                "size": size,
                "type": dir_type,
            })
            # 记录迁移后会存在的文件名
            for f in files:
                self._target_filenames.add(f.name)

        return {
            "vault": str(self.vault_dir),
            "dir_count": len(self.scanned_dirs),
            "total_files": total_files,
            "total_size": total_size,
            "dirs": dir_details,
        }

    # ── 迁移 ──────────────────────────────────────────────

    def migrate(self) -> Dict:
        """执行完整迁移：扫描 → 移动文件 → 更新引用 → 清理空目录"""
        # 1. 扫描
        scan_result = self.scan()
        if scan_result["dir_count"] == 0:
            print("✅ 没有发现散落的资源目录，无需操作")
            return scan_result

        # 2. 移动文件
        print(f"\n📦 第1步：移动文件到 {self.target_dir.relative_to(self.vault_dir)}/")
        self.target_dir.mkdir(parents=True, exist_ok=True)
        self._move_all_files()

        # 3. 更新 Markdown 引用
        print(f"\n📝 第2步：更新 Markdown 引用")
        self._update_all_references()

        # 4. 清理空目录
        print(f"\n🧹 第3步：清理空目录")
        self._cleanup_empty_dirs()

        return {
            **scan_result,
            "moved_files": len(self.moved_files),
            "updated_notes": len(self.updated_notes),
            "cleaned_dirs": len(self.cleaned_dirs),
            "errors": len(self.errors),
            "skipped_files": len(self.skipped_files),
        }

    def _move_all_files(self):
        """移动所有散落的资源文件到目标目录"""
        for src_dir in self.scanned_dirs:
            rel_dir = src_dir.relative_to(self.vault_dir)
            files = sorted(f for f in src_dir.iterdir() if f.is_file())
            print(f"  📂 {rel_dir} ({len(files)} 个文件)")

            for src_file in files:
                dest_file = self.target_dir / src_file.name

                # 处理同名文件
                if dest_file.exists():
                    if self._files_identical(src_file, dest_file):
                        # 内容相同，跳过（不需要移动），但标记为已处理
                        self.skipped_files.append({
                            "path": str(src_file.relative_to(self.vault_dir)),
                            "reason": "duplicate_same_content",
                        })
                        self._processed_src_files.add(src_file)
                        continue
                    else:
                        # 内容不同，加后缀
                        dest_file = self._unique_path(dest_file)

                if self.dry_run:
                    print(f"    [DRY] {src_file.name} → {dest_file.relative_to(self.vault_dir)}")
                    self._processed_src_files.add(src_file)
                else:
                    try:
                        shutil.move(str(src_file), str(dest_file))
                        self.moved_files.append({
                            "src": str(src_file.relative_to(self.vault_dir)),
                            "dest": str(dest_file.relative_to(self.vault_dir)),
                        })
                        self._processed_src_files.add(src_file)
                    except Exception as e:
                        self.errors.append({
                            "file": str(src_file.relative_to(self.vault_dir)),
                            "error": str(e),
                        })
                        print(f"    ❌ {src_file.name}: {e}")

    def _update_all_references(self):
        """更新所有 Markdown 文件中的资源引用"""
        md_files = self._find_all_md_files()
        print(f"  扫描 {len(md_files)} 个 Markdown 文件...")

        for md_file in md_files:
            updated_content = self._update_references_in_file(md_file)
            if updated_content is not None:
                rel_path = md_file.relative_to(self.vault_dir)
                if self.dry_run:
                    print(f"  [DRY] 更新引用: {rel_path}")
                    self.updated_notes.append({"path": str(rel_path)})
                else:
                    try:
                        md_file.write_text(updated_content, encoding="utf-8")
                        self.updated_notes.append({"path": str(rel_path)})
                    except Exception as e:
                        self.errors.append({
                            "file": str(rel_path),
                            "error": str(e),
                        })

        if self.updated_notes:
            print(f"  {'将更新' if self.dry_run else '更新了'} {len(self.updated_notes)} 个文件的引用")

    def _update_references_in_file(self, md_file: Path) -> Optional[str]:
        """更新单个文件中的资源引用，返回 None 表示无需更新"""
        try:
            content = md_file.read_text(encoding="utf-8")
        except (UnicodeDecodeError, PermissionError):
            return None

        original = content
        md_dir = md_file.parent

        # 匹配模式：![](path) 和 ![[path]]
        # 需要更新的路径模式：
        #   - xxx_files/filename → attachments/filename
        #   - 相对路径的 attachments/filename → attachments/filename（如果不在顶层）

        def replace_md_image(match):
            prefix = match.group(1)  # ![
            alt = match.group(2)     # alt text
            path = match.group(3)    # path
            suffix = match.group(4)  # )

            new_path = self._resolve_new_path(path, md_dir)
            if new_path != path:
                return f"{prefix}{alt}{new_path}{suffix}"
            return match.group(0)

        def replace_wikilink_image(match):
            prefix = match.group(1)  # ![[
            path = match.group(2)    # path
            suffix = match.group(3)  # ]]

            # 可能有别名：![[path|alias]]
            if "|" in path:
                file_part, alias = path.rsplit("|", 1)
            else:
                file_part = path
                alias = None

            new_path = self._resolve_new_path(file_part, md_dir)
            if new_path != file_part:
                if alias:
                    return f"{prefix}{new_path}|{alias}{suffix}"
                return f"{prefix}{new_path}{suffix}"
            return match.group(0)

        # Markdown 图片语法: ![alt](path)
        content = re.sub(
            r'(!\[)(.*?)\(([^)]+)\)(\))',
            replace_md_image,
            content,
        )

        # 不对，重新来。Markdown 图片语法更精确的匹配
        content = original

        # 标准 Markdown: ![alt](path)
        content = re.sub(
            r'!\[([^\]]*)\]\(([^)]+)\)',
            lambda m: f'![{m.group(1)}]({self._resolve_new_path(m.group(2), md_dir)})',
            content,
        )

        # WikiLink 图片: ![[path]] 或 ![[path|alias]]
        content = re.sub(
            r'!\[\[([^\]|]+)(\|[^\]]*)?\]\]',
            lambda m: f'![[{self._resolve_new_path(m.group(1), md_dir)}{m.group(2) or ""}]]',
            content,
        )

        # 普通链接中的本地文件引用: [text](local_path)（非 http）
        # 谨慎处理，只改 *_files 开头的路径
        content = re.sub(
            r'(?<!!)\[([^\]]*)\]\(([^)]+)\)',
            lambda m: f'[{m.group(1)}]({self._resolve_new_path(m.group(2), md_dir)})'
            if self._is_local_resource_ref(m.group(2))
            else m.group(0),
            content,
        )

        # WikiLink 非图片引用中的本地资源: [[path]]（非笔记链接，带扩展名的）
        # 只处理图片/附件扩展名
        resource_exts = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.svg', '.webp',
                         '.pdf', '.zip', '.mp3', '.mp4', '.wav', '.doc', '.docx', '.xls', '.xlsx'}

        def replace_wikilink_resource(m):
            path = m.group(1)
            alias = m.group(2) or ""
            # 取文件扩展名
            clean_path = path.split("|")[0] if "|" in path else path
            ext = Path(clean_path).suffix.lower()
            if ext in resource_exts:
                new_path = self._resolve_new_path(clean_path, md_dir)
                if new_path != clean_path:
                    return f'[[{new_path}{alias}]]'
            return m.group(0)

        content = re.sub(
            r'\[\[([^\]|]+)(\|[^\]]*)?\]\]',
            replace_wikilink_resource,
            content,
        )

        if content != original:
            return content
        return None

    def _resolve_new_path(self, ref_path: str, md_dir: Path) -> str:
        """将旧的资源路径解析为新的统一路径"""
        # 跳过 URL 和绝对路径
        if ref_path.startswith(("http://", "https://", "data:", "#")):
            return ref_path

        # 提取纯文件名（去掉目录前缀）
        filename = Path(ref_path).name

        # 判断文件是否会在迁移后的 attachments/ 中存在
        # 优先检查实际文件，再检查预计算集合（dry-run 时用）
        in_target = (self.target_dir / filename).exists() or filename in self._target_filenames

        if in_target:
            # 需要更新：当前引用不在 attachments/ 下，或者路径不对
            # 检查引用是否已经指向顶层 attachments/
            if ref_path.startswith("attachments/") or ref_path.startswith("attachments\\"):
                # 引用已经指向 attachments/，但如果不在顶层需要修正
                # 检查当前 attachments/ 是否就是顶层
                current_attach = md_dir / "attachments"
                if current_attach.resolve() == self.target_dir.resolve():
                    return ref_path  # 已经正确
            elif not ("_files/" in ref_path or "_files\\" in ref_path):
                # 不是 _files 也不是 attachments，可能是直接文件名引用
                # 检查原文件是否还存在于原位
                old_full = md_dir / ref_path
                if old_full.exists():
                    return ref_path  # 原文件还在，不动

            # 计算新路径
            try:
                rel = os.path.relpath(self.target_dir / filename, md_dir)
                return rel
            except ValueError:
                return f"attachments/{filename}"

        return ref_path

    def _is_local_resource_ref(self, path: str) -> bool:
        """判断是否是本地资源引用（非 URL）"""
        if path.startswith(("http://", "https://", "data:", "#", "/")):
            return False
        # 只处理包含 _files 的路径
        return "_files/" in path or "_files\\" in path

    def _is_empty_or_nested_empty(self, dir_path: Path) -> bool:
        """检查目录是否为空（或只含空子目录）"""
        for item in dir_path.rglob("*"):
            if item.is_file():
                return False
        return True

    def _cleanup_empty_dirs(self):
        """清理空的旧资源目录（后序遍历，从最深层开始）"""
        for src_dir in sorted(self.scanned_dirs, key=lambda p: len(p.parts), reverse=True):
            if not src_dir.exists():
                continue

            # 检查目录中还有哪些文件未被处理（既没移动也不是重复跳过）
            remaining = []
            for item in src_dir.rglob("*"):
                if item.is_file() and item not in self._processed_src_files:
                    remaining.append(item)

            if not remaining:
                # 所有文件都已处理（移动或跳过重复），目录可以安全删除
                rel = src_dir.relative_to(self.vault_dir)
                if self.dry_run:
                    print(f"  [DRY] 删除目录: {rel}")
                    self.cleaned_dirs.append(src_dir)
                else:
                    try:
                        shutil.rmtree(src_dir)
                        self.cleaned_dirs.append(src_dir)
                        print(f"  🗑️  {rel}")
                    except Exception as e:
                        self.errors.append({
                            "dir": str(rel),
                            "error": str(e),
                        })
            else:
                print(f"  ⚠️  {src_dir.relative_to(self.vault_dir)}: 仍有 {len(remaining)} 个文件未处理")

    # ── 辅助方法 ──────────────────────────────────────────

    def _should_skip(self, path: Path) -> bool:
        """判断是否应跳过该目录"""
        parts = path.relative_to(self.vault_dir).parts
        if not parts:
            return True
        # 跳过 .obsidian, .trash, 隐藏目录
        for part in parts:
            if part.startswith("."):
                return True
        # 跳过目标目录本身
        if path == self.target_dir:
            return True
        return False

    def _find_all_md_files(self) -> List[Path]:
        """找到所有 Markdown 文件（排除 .obsidian, .trash）"""
        md_files = []
        for root, dirs, files in os.walk(self.vault_dir):
            root_path = Path(root)
            if any(p.startswith(".") for p in root_path.relative_to(self.vault_dir).parts):
                continue
            for f in files:
                if f.endswith(".md"):
                    md_files.append(root_path / f)
        return md_files

    def _files_identical(self, a: Path, b: Path) -> bool:
        """比较两个文件内容是否相同"""
        if a.stat().st_size != b.stat().st_size:
            return False
        return a.read_bytes() == b.read_bytes()

    def _unique_path(self, path: Path) -> Path:
        """生成唯一路径，避免覆盖"""
        stem = path.stem
        suffix = path.suffix
        parent = path.parent
        counter = 1
        while path.exists():
            path = parent / f"{stem}_{counter}{suffix}"
            counter += 1
        return path

    @staticmethod
    def format_size(size_bytes: int) -> str:
        """格式化文件大小"""
        for unit in ["B", "KB", "MB", "GB"]:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"


def print_scan_report(result: Dict):
    """打印扫描报告"""
    print(f"\n{'=' * 60}")
    print(f"📊 扫描报告: {result['vault']}")
    print(f"{'=' * 60}")
    print(f"散落的资源目录: {result['dir_count']}")
    print(f"资源文件总数:   {result['total_files']}")
    print(f"总大小:         {AttachmentConsolidator.format_size(result['total_size'])}")

    if result["dirs"]:
        print(f"\n{'─' * 60}")
        # 按类型分组
        type_groups = defaultdict(list)
        for d in result["dirs"]:
            type_groups[d["type"]].append(d)

        for dir_type in sorted(type_groups.keys()):
            dirs = type_groups[dir_type]
            suffix = f"{'后缀 ' + dir_type if dir_type == '_files' else dir_type}"
            print(f"\n📂 {suffix} 目录 ({len(dirs)} 个):")
            for d in dirs:
                print(f"  {d['path']}  ({d['file_count']} 文件, {AttachmentConsolidator.format_size(d['size'])})")

    print(f"{'=' * 60}\n")


def print_migrate_report(result: Dict):
    """打印迁移报告"""
    print(f"\n{'=' * 60}")
    print(f"📊 迁移完成")
    print(f"{'=' * 60}")
    print(f"扫描到的资源目录: {result['dir_count']}")
    print(f"移动的文件数:     {result.get('moved_files', 0)}")
    print(f"跳过的重复文件:   {result.get('skipped_files', 0)}")
    print(f"更新的笔记数:     {result.get('updated_notes', 0)}")
    print(f"清理的空目录:     {result.get('cleaned_dirs', 0)}")
    print(f"错误数:           {result.get('errors', 0)}")
    print(f"{'=' * 60}\n")


def main():
    parser = argparse.ArgumentParser(
        description="附件整合工具 - 将散落的资源目录统一到顶层 attachments/",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
模式说明:
  scan     仅扫描并报告散落的资源目录，不做任何修改
  dry-run  模拟迁移，显示将要执行的操作但不实际修改文件
  migrate  执行完整迁移：移动文件 → 更新引用 → 清理空目录

示例:
  python3 tools/consolidate_attachments.py scan /path/to/vault
  python3 tools/consolidate_attachments.py dry-run /path/to/vault
  python3 tools/consolidate_attachments.py migrate /path/to/vault
        """,
    )
    parser.add_argument("mode", choices=["scan", "dry-run", "migrate"], help="运行模式")
    parser.add_argument("vault_dir", help="Obsidian Vault 目录路径")

    args = parser.parse_args()

    vault = Path(args.vault_dir)
    if not vault.is_dir():
        print(f"❌ 目录不存在: {vault}")
        sys.exit(1)

    # 确认是 Obsidian vault（有 .obsidian 目录）
    if not (vault / ".obsidian").is_dir():
        print(f"⚠️  警告: {vault} 看起来不是 Obsidian Vault（缺少 .obsidian 目录）")
        confirm = input("是否继续？(y/N): ")
        if confirm.lower() != "y":
            sys.exit(0)

    is_dry_run = args.mode == "dry-run"
    consolidator = AttachmentConsolidator(str(vault), dry_run=(args.mode != "scan" and is_dry_run))

    if args.mode == "scan":
        result = consolidator.scan()
        print_scan_report(result)

    elif args.mode in ("dry-run", "migrate"):
        if args.mode == "migrate":
            print("⚠️  即将执行迁移操作，会移动文件并修改 Markdown 内容")
            confirm = input("确认继续？(y/N): ")
            if confirm.lower() != "y":
                print("已取消")
                sys.exit(0)

        consolidator.dry_run = (args.mode == "dry-run")
        result = consolidator.migrate()
        print_migrate_report(result)


if __name__ == "__main__":
    main()
