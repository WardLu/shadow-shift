#!/usr/bin/env python3
"""
Obsidian 仓库清理工具

五种模式：
  dedup    检测并删除重复文件（按内容哈希），保留一个并更新引用
  fuzzy    检测近似重复笔记（按标题+纯文本比对，显示相似度百分比，支持 --threshold）
  clean    检测并清理空笔记和空目录，支持 --fix-untitled 清理「无标题」占位符
  orphan   检测孤儿文件（默认排除 .pdf/.xls/.xlsx/.xmind，预览列出文件详情）
  fix      修复失效引用，将孤儿文件重新链接到笔记

fuzzy 模式特性：
  - 默认阈值 0.8，可通过 --threshold 调整（如 --threshold 0.25）
  - 模板保护：文件名含 template/模板/tpl 的笔记不会被删除
  - 代码块内容保留比较（不删除代码块内的差异）

推荐流程：fix → fuzzy → dedup → orphan → clean

用法：
  python3 tools/vault_cleaner.py fix /path/to/vault               # 修复失效引用（预览）
  python3 tools/vault_cleaner.py fix /path/to/vault --apply       # 执行修复
  python3 tools/vault_cleaner.py fuzzy /path/to/vault             # 近似重复检测（预览）
  python3 tools/vault_cleaner.py fuzzy /path/to/vault --apply     # 删除近似重复
  python3 tools/vault_cleaner.py fuzzy /path/to/vault --threshold 0.25 --apply  # 低阈值
  python3 tools/vault_cleaner.py dedup /path/to/vault             # 检测重复（预览）
  python3 tools/vault_cleaner.py dedup /path/to/vault --apply     # 执行去重删除
  python3 tools/vault_cleaner.py clean /path/to/vault              # 检测空笔记/空目录（预览）
  python3 tools/vault_cleaner.py clean /path/to/vault --fix-untitled --apply  # 清理无标题+空目录
  python3 tools/vault_cleaner.py orphan /path/to/vault            # 检测孤儿（预览）
  python3 tools/vault_cleaner.py orphan /path/to/vault --apply    # 删除孤儿文件
"""
import argparse
import difflib
import hashlib
import os
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


# 去重时扫描的扩展名（含笔记文件）
DEDUP_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".svg", ".webp", ".ico",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".zip", ".rar", ".7z", ".tar", ".gz",
    ".mp3", ".mp4", ".wav", ".avi", ".mov",
    ".xmind", ".md", ".txt", ".csv",
}

# 孤儿检测时扫描的扩展名（仅图片和附件，不含笔记）
RESOURCE_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".svg", ".webp", ".ico",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".zip", ".rar", ".7z", ".tar", ".gz",
    ".mp3", ".mp4", ".wav", ".avi", ".mov",
    ".xmind",
}

# 默认资源目录名（可通过 config.json 的 cleanup.resource_dir_names 覆盖）
_RESOURCE_DIR_NAMES = {"attachments", "images", "all_image", "all_images"}

# 默认排除扩展名（可通过 config.json 的 cleanup.exclude_extensions 或 --exclude-ext 覆盖）
DEFAULT_EXCLUDE_EXT = {".pdf", ".xls", ".xlsx", ".xmind"}

# 默认模板保护关键词（可通过 config.json 的 cleanup.protected_filenames 覆盖）
_PROTECTED_KEYWORDS = {"template", "模板", "tpl"}


def _load_cleanup_config() -> dict:
    """从 config.json 加载清理配置，返回覆盖项"""
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

# 应用配置覆盖
if "resource_dir_names" in _cleanup_cfg:
    _RESOURCE_DIR_NAMES = set(_cleanup_cfg["resource_dir_names"])
if "exclude_extensions" in _cleanup_cfg:
    DEFAULT_EXCLUDE_EXT = set(_cleanup_cfg["exclude_extensions"])
if "protected_keywords" in _cleanup_cfg:
    _PROTECTED_KEYWORDS = set(_cleanup_cfg["protected_keywords"])


def _is_resource_dir(path: Path, vault_dir: Path) -> bool:
    """判断是否是资源目录（attachments/、*_files/、images/ 等）"""
    name = path.name
    if name in _RESOURCE_DIR_NAMES:
        return True
    if name.endswith("_files"):
        return True
    # 顶层 attachments 的子目录也算
    try:
        rel = path.relative_to(vault_dir)
        if rel.parts and rel.parts[0] == "attachments":
            return True
    except ValueError:
        pass
    return False


class VaultCleaner:
    """Obsidian 仓库清理器"""

    def __init__(self, vault_dir: str, apply: bool = False, exclude_ext: Optional[Set[str]] = None):
        self.vault_dir = Path(vault_dir).resolve()
        self.apply = apply
        self.exclude_ext = exclude_ext or set()
        self.errors: List[Dict] = []

    # ── 去重 ──────────────────────────────────────────────

    def dedup(self) -> Dict:
        """检测并删除重复文件"""
        print("🔍 扫描所有资源文件...")
        all_files = self._scan_resource_files()
        print(f"  找到 {len(all_files)} 个资源文件\n")

        print("🔢 计算文件哈希...")
        hash_groups = self._group_by_hash(all_files)
        dup_groups = {h: paths for h, paths in hash_groups.items() if len(paths) > 1}

        if not dup_groups:
            print("✅ 没有发现重复文件")
            return {"total_files": len(all_files), "dup_groups": 0, "dup_files": 0, "removed": 0}

        total_dup_files = sum(len(paths) - 1 for paths in dup_groups.values())
        print(f"⚠️  发现 {len(dup_groups)} 组重复，共 {total_dup_files} 个冗余文件\n")

        # 选择保留哪个文件，删除其余
        removed = 0
        removed_paths = []
        for file_hash, paths in sorted(dup_groups.items(), key=lambda x: len(x[1]), reverse=True):
            keep, remove_list = self._pick_keeper(paths)
            rel_keep = str(keep.relative_to(self.vault_dir))
            print(f"  保留: {rel_keep}  ({len(remove_list)} 个重复)")

            for rm_path in remove_list:
                rel_rm = str(rm_path.relative_to(self.vault_dir))
                if self.apply:
                    try:
                        # 更新引用：将指向被删文件的引用改为指向保留文件
                        self._update_refs(rm_path, keep)
                        rm_path.unlink()
                        removed += 1
                        removed_paths.append(rel_rm)
                        print(f"    🗑️  {rel_rm}")
                    except Exception as e:
                        self.errors.append({"file": rel_rm, "error": str(e)})
                        print(f"    ❌ {rel_rm}: {e}")
                else:
                    removed += 1
                    removed_paths.append(rel_rm)
                    print(f"    [DRY] {rel_rm}")

        return {
            "total_files": len(all_files),
            "dup_groups": len(dup_groups),
            "dup_files": total_dup_files,
            "removed": removed,
            "removed_paths": removed_paths,
            "errors": len(self.errors),
        }

    # ── 空笔记和空目录清理 ────────────────────────────────

    def clean(self, fix_untitled: bool = False) -> Dict:
        """检测并清理空笔记、空目录，可选修复「无标题」占位符

        Args:
            fix_untitled: 是否清理笔记开头的「无标题」占位符
        """
        print("🔍 扫描空笔记和空目录...\n")

        md_files = self._find_all_md()
        empty_notes = []
        tiny_notes = []
        untitled_notes = []

        for md_file in md_files:
            try:
                content = md_file.read_text(encoding="utf-8")
            except (UnicodeDecodeError, PermissionError):
                continue

            rel = str(md_file.relative_to(self.vault_dir))
            size = md_file.stat().st_size

            # 检测「无标题」占位符
            if fix_untitled:
                # 匹配 frontmatter 后紧跟的「无标题」
                new_content = self._remove_untitled(content)
                if new_content != content:
                    untitled_notes.append({"path": md_file, "rel": rel, "size": size})

            # 去除 frontmatter
            body = content
            if body.startswith("---"):
                end = body.find("---", 3)
                if end != -1:
                    body = body[end + 3:]

            body_text = body.strip()
            plain = re.sub(r'#+\s*', '', body_text)
            plain = re.sub(r'\s+', '', plain)

            if len(plain) == 0:
                empty_notes.append({"path": md_file, "rel": rel, "size": size})
            elif len(plain) < 10:
                tiny_notes.append({"path": md_file, "rel": rel, "size": size, "content": plain[:50]})

        # 空目录
        empty_dirs = []
        for root, dirs, files in os.walk(self.vault_dir, topdown=False):
            root_path = Path(root)
            if any(p.startswith(".") for p in root_path.relative_to(self.vault_dir).parts):
                continue
            if root_path == self.vault_dir:
                continue
            if not files and not dirs:
                rel = str(root_path.relative_to(self.vault_dir))
                empty_dirs.append({"path": root_path, "rel": rel})

        # 输出结果
        print(f"{'=' * 60}")
        print(f"📊 空内容检测结果")
        print(f"{'=' * 60}")
        print(f"笔记总数:     {len(md_files)}")
        print(f"空笔记:       {len(empty_notes)}")
        print(f"内容过少:     {len(tiny_notes)}  (< 10 字符)")
        if fix_untitled:
            print(f"无标题占位符: {len(untitled_notes)}")
        print(f"空目录:       {len(empty_dirs)}")

        changed = 0
        changed_paths = []

        if empty_notes:
            print(f"\n{'─' * 60}")
            print(f"📄 空笔记 ({len(empty_notes)} 个)  {'← 将删除' if self.apply else '← 预览，不会删除'}")
            for note in empty_notes:
                print(f"  {note['rel']}")
                if self.apply:
                    try:
                        note["path"].unlink()
                        changed += 1
                        changed_paths.append(note["rel"])
                    except Exception as e:
                        self.errors.append({"file": note["rel"], "error": str(e)})

        if tiny_notes:
            print(f"\n{'─' * 60}")
            print(f"📄 内容过少的笔记 ({len(tiny_notes)} 个)  {'← 将删除' if self.apply else '← 预览，不会删除'}")
            for note in tiny_notes:
                print(f"  {note['rel']}  (内容: {note['content']})")
                if self.apply:
                    try:
                        note["path"].unlink()
                        changed += 1
                        changed_paths.append(note["rel"])
                    except Exception as e:
                        self.errors.append({"file": note["rel"], "error": str(e)})

        if untitled_notes:
            print(f"\n{'─' * 60}")
            print(f"📄 无标题占位符 ({len(untitled_notes)} 个)  {'← 将清理' if self.apply else '← 预览，不会修改'}")
            for note in untitled_notes:
                print(f"  {note['rel']}")
                if self.apply:
                    try:
                        content = note["path"].read_text(encoding="utf-8")
                        new_content = self._remove_untitled(content)
                        note["path"].write_text(new_content, encoding="utf-8")
                        changed += 1
                        changed_paths.append(note["rel"])
                    except Exception as e:
                        self.errors.append({"file": note["rel"], "error": str(e)})

        if empty_dirs:
            print(f"\n{'─' * 60}")
            print(f"📁 空目录 ({len(empty_dirs)} 个)  {'← 将删除' if self.apply else '← 预览，不会删除'}")
            for d in empty_dirs:
                print(f"  {d['rel']}")
                if self.apply:
                    try:
                        d["path"].rmdir()
                        changed += 1
                        changed_paths.append(d["rel"])
                    except Exception as e:
                        self.errors.append({"dir": d["rel"], "error": str(e)})

        if not empty_notes and not tiny_notes and not untitled_notes and not empty_dirs:
            print("\n✅ 没有发现需要清理的内容")

        print(f"\n{'=' * 60}")
        if self.apply:
            print(f"已清理: {changed} 项")
        else:
            print(f"💡 以上为预览，不会修改任何文件")
            print(f"   使用 --apply 参数实际执行清理")
        print(f"{'=' * 60}\n")

        return {
            "empty_notes": len(empty_notes),
            "tiny_notes": len(tiny_notes),
            "untitled_notes": len(untitled_notes),
            "empty_dirs": len(empty_dirs),
            "changed": changed,
            "errors": len(self.errors),
        }

    @staticmethod
    def _remove_untitled(content: str) -> str:
        """去除 frontmatter 后紧跟的「无标题」占位符，保留空行分隔"""
        if not content.startswith("---"):
            return content
        end = content.find("---", 3)
        if end == -1:
            return content
        fm = content[:end + 3]
        body = content[end + 3:]
        # 去除「无标题」及其后的换行，但保留一个空行
        body = re.sub(r'^\s*无标题\s*\n?', '\n', body, count=1)
        return fm + body

    # ── 近似重复检测 ──────────────────────────────────────

    def fuzzy(self, threshold: float = 0.8) -> Dict:
        """检测近似重复笔记（按标题+去除链接后的纯文本比对）"""
        print("📝 扫描所有笔记...")
        md_files = self._find_all_md()
        print(f"  找到 {len(md_files)} 个笔记\n")

        print("🧹 提取纯文本内容（去除 frontmatter 和链接语法）...")
        notes = []
        for md_file in md_files:
            try:
                content = md_file.read_text(encoding="utf-8")
            except (UnicodeDecodeError, PermissionError):
                continue
            pure = self._strip_to_pure_text(content)
            title = self._extract_title(content, md_file)
            notes.append({
                "path": md_file,
                "rel": str(md_file.relative_to(self.vault_dir)),
                "title": title,
                "pure": pure,
                "short": len(pure.strip()) < 20,  # 内容极少的笔记
                "size": md_file.stat().st_size,
            })

        print(f"  有效笔记: {len(notes)} 个\n")

        # 第一轮：按标题分组（同名笔记高度疑似重复）
        print("🔍 第一轮：按标题分组...")
        title_groups = defaultdict(list)
        for note in notes:
            title_groups[note["title"]].append(note)

        matches = []
        for title, group in title_groups.items():
            if len(group) < 2:
                continue
            # 组内两两比较
            for i in range(len(group)):
                for j in range(i + 1, len(group)):
                    a, b = group[i], group[j]
                    # 两个都是短内容笔记 → 同标题即视为重复
                    if a["short"] and b["short"]:
                        matches.append({
                            "a": a, "b": b,
                            "similarity": 1.0,
                            "reason": "同标题（短内容）",
                        })
                    else:
                        sim = self._similarity(a["pure"], b["pure"])
                        if sim >= threshold:
                            matches.append({
                                "a": a, "b": b,
                                "similarity": sim,
                                "reason": "同标题",
                            })

        # 第二轮：按纯文本哈希分组（标题不同但内容相同）
        print("🔍 第二轮：按纯文本哈希分组...")
        pure_hash_groups = defaultdict(list)
        for note in notes:
            if note["short"]:
                continue  # 短内容笔记不参与哈希匹配，避免误匹配
            h = hashlib.md5(note["pure"].encode("utf-8")).hexdigest()
            pure_hash_groups[h].append(note)

        seen_pairs = set()
        for h, group in pure_hash_groups.items():
            if len(group) < 2:
                continue
            for i in range(len(group)):
                for j in range(i + 1, len(group)):
                    pair_key = tuple(sorted([group[i]["rel"], group[j]["rel"]]))
                    if pair_key in seen_pairs:
                        continue
                    seen_pairs.add(pair_key)
                    sim = self._similarity(group[i]["pure"], group[j]["pure"])
                    if sim >= threshold:
                        matches.append({
                            "a": group[i],
                            "b": group[j],
                            "similarity": sim,
                            "reason": "内容相同",
                        })

        # 去重
        unique_matches = []
        seen = set()
        for m in matches:
            key = tuple(sorted([m["a"]["rel"], m["b"]["rel"]]))
            if key not in seen:
                seen.add(key)
                unique_matches.append(m)

        if not unique_matches:
            print(f"\n{'=' * 60}")
            print(f"📊 近似重复检测结果（阈值 {threshold*100:.0f}%）")
            print(f"{'=' * 60}")
            print(f"笔记总数:     {len(notes)}")
            print(f"近似重复对:   0")
            print("✅ 没有发现近似重复笔记")
            return {"total_notes": len(notes), "matches": 0, "removed": 0}

        # 用 union-find 将匹配对聚合成组
        parent = {}

        def find(x):
            while parent.get(x, x) != x:
                parent[x] = parent.get(parent[x], parent[x])
                x = parent[x]
            return x

        def union(x, y):
            px, py = find(x), find(y)
            if px != py:
                parent[px] = py

        for m in unique_matches:
            union(m["a"]["rel"], m["b"]["rel"])

        groups = defaultdict(list)
        for note_rel in set(find(m["a"]["rel"]) for m in unique_matches):
            # 收集该组所有成员
            members = set()
            for m in unique_matches:
                members.add(m["a"]["rel"])
                members.add(m["b"]["rel"])
            # 只保留属于当前组的
            group_members = [r for r in members if find(r) == note_rel]
            if len(group_members) >= 2:
                groups[note_rel] = group_members

        # 为每组计算最高相似度和原因
        group_info = {}
        for root, members in groups.items():
            best_sim = 0
            best_reason = ""
            for m in unique_matches:
                if m["a"]["rel"] in members and m["b"]["rel"] in members:
                    if m["similarity"] > best_sim:
                        best_sim = m["similarity"]
                        best_reason = m["reason"]
            group_info[root] = {"similarity": best_sim, "reason": best_reason}

        # 按相似度排序
        sorted_groups = sorted(groups.items(), key=lambda x: -group_info[x[0]]["similarity"])

        # 构建 notes 索引
        note_by_rel = {n["rel"]: n for n in notes}

        print(f"\n{'=' * 60}")
        print(f"📊 近似重复检测结果（阈值 {threshold*100:.0f}%）")
        print(f"{'=' * 60}")
        print(f"笔记总数:     {len(notes)}")
        print(f"重复组数:     {len(sorted_groups)}")
        total_drops = sum(len(members) - 1 for _, members in sorted_groups)
        print(f"冗余笔记数:   {total_drops}")

        if not sorted_groups:
            print("✅ 没有发现近似重复笔记")
            return {"total_notes": len(notes), "matches": 0, "removed": 0}

        # 显示匹配结果
        removed = 0
        removed_paths = []
        print(f"\n{'─' * 60}")

        for idx, (root, members) in enumerate(sorted_groups, 1):
            info = group_info[root]
            sim_pct = info["similarity"] * 100
            member_notes = [note_by_rel[r] for r in members if r in note_by_rel]
            keep, drops = self._pick_group_keeper(member_notes)

            print(f"\n  #{idx}  相似度 {sim_pct:.1f}%  ({info['reason']})  [{len(members)} 个副本]")
            print(f"    ✅ 保留: {keep['rel']}")
            for drop in drops:
                print(f"    🗑️  删除: {drop['rel']}")

            for drop in drops:
                # 修复指向被删笔记的引用
                ref_count = self._redirect_note_refs(drop, keep, md_files)
                if ref_count > 0:
                    print(f"    🔗 修复 {ref_count} 个引用 → {keep['title']}")

                if self.apply:
                    try:
                        drop["path"].unlink()
                        removed += 1
                        removed_paths.append(drop["rel"])
                    except Exception as e:
                        self.errors.append({"file": drop["rel"], "error": str(e)})
                        print(f"    ❌ 删除失败: {drop['rel']}: {e}")
                else:
                    removed += 1
                    removed_paths.append(drop["rel"])

        print(f"\n{'=' * 60}")
        print(f"{'已删除' if self.apply else '将删除'}: {removed} 个近似重复笔记")
        if self.errors:
            print(f"错误: {len(self.errors)}")
        print(f"{'=' * 60}\n")

        return {
            "total_notes": len(notes),
            "matches": len(unique_matches),
            "removed": removed,
            "removed_paths": removed_paths,
            "errors": len(self.errors),
        }

    @staticmethod
    def _strip_to_pure_text(content: str) -> str:
        """去除 frontmatter 和链接语法，返回纯文本"""
        # 去除 frontmatter
        if content.startswith("---"):
            end = content.find("---", 3)
            if end != -1:
                content = content[end + 3:]
        # 去除 Obsidian callout: > [!TYPE]
        content = re.sub(r'^\s*>\s*\[!\w+\]\s*$', '', content, flags=re.MULTILINE)
        # 去除块引用标记: > text → text
        content = re.sub(r'^\s*>\s?', '', content, flags=re.MULTILINE)
        # 去除 Markdown 图片: ![alt](path)
        content = re.sub(r'!\[[^\]]*\]\([^)]+\)', '', content)
        # 去除 WikiLink 图片: ![[path]]
        content = re.sub(r'!\[\[[^\]]+\]\]', '', content)
        # 去除普通链接但保留文本: [text](path) → text
        content = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', content)
        # 去除 WikiLink 但保留文本: [[path|text]] → text, [[path]] → path
        content = re.sub(r'\[\[([^\]|]+)\|([^\]]+)\]\]', r'\2', content)
        content = re.sub(r'\[\[([^\]]+)\]\]', r'\1', content)
        # 去除 HTML 标签
        content = re.sub(r'<[^>]+>', '', content)
        # 去除加粗/斜体标记
        content = re.sub(r'\*\*(.+?)\*\*', r'\1', content)
        content = re.sub(r'\*(.+?)\*', r'\1', content)
        content = re.sub(r'__(.+?)__', r'\1', content)
        content = re.sub(r'_(.+?)_', r'\1', content)
        # 去除标题标记
        content = re.sub(r'^#{1,6}\s+', '', content, flags=re.MULTILINE)
        # 去除列表标记
        content = re.sub(r'^[\s]*[-*+]\s+', '', content, flags=re.MULTILINE)
        content = re.sub(r'^[\s]*\d+\.\s+', '', content, flags=re.MULTILINE)
        # 去除代码围栏但保留内容
        content = re.sub(r'```\w*\n?', '', content)
        content = re.sub(r'`([^`]+)`', r'\1', content)
        # 去除水平线
        content = re.sub(r'^[-*_]{3,}\s*$', '', content, flags=re.MULTILINE)
        # 去除多余空白
        content = re.sub(r'\s+', ' ', content).strip()
        return content

    @staticmethod
    def _extract_title(content: str, md_file: Path) -> str:
        """提取笔记标题（优先 frontmatter，其次文件名），去除 .md 后缀"""
        # 尝试从 frontmatter 提取
        if content.startswith("---"):
            end = content.find("---", 3)
            if end != -1:
                fm = content[3:end]
                for line in fm.split("\n"):
                    if line.strip().startswith("title:"):
                        title = line.split(":", 1)[1].strip().strip('"').strip("'")
                        # 去除可能的 .md 后缀
                        if title.endswith(".md"):
                            title = title[:-3]
                        return title
        # 用文件名（stem 已不含 .md）
        return md_file.stem

    @staticmethod
    def _similarity(a: str, b: str) -> float:
        """计算两个字符串的相似度（0~1）"""
        return difflib.SequenceMatcher(None, a, b).ratio()

    def _pick_note_keeper(self, a: Dict, b: Dict) -> Tuple[Dict, Dict]:
        """选择保留哪个笔记：优先路径更短、不在临时草稿目录的"""
        draft_keywords = ("临时草稿", "temp", "draft", "草稿")
        a_is_draft = any(k in a["rel"] for k in draft_keywords)
        b_is_draft = any(k in b["rel"] for k in draft_keywords)

        if a_is_draft and not b_is_draft:
            return b, a
        if b_is_draft and not a_is_draft:
            return a, b

        if len(a["rel"].split(os.sep)) <= len(b["rel"].split(os.sep)):
            return a, b
        return b, a

    def _redirect_note_refs(self, drop: Dict, keep: Dict, md_files: List[Path]) -> int:
        """将所有指向 drop 笔记的 [[引用]] 重定向到 keep 笔记

        处理的引用格式：
        - [[被删笔记标题]]
        - [[被删笔记标题|别名]]
        - [[被删笔记路径/标题]]
        """
        drop_title = drop["path"].stem  # 不含扩展名
        keep_title = keep["path"].stem
        drop_stem = drop_title
        keep_stem = keep_title

        # 如果标题相同，不需要替换
        if drop_stem == keep_stem:
            return 0

        ref_count = 0
        for md_file in md_files:
            # 跳过被删文件本身和已不存在的文件
            if md_file == drop["path"] or not md_file.exists():
                continue
            try:
                content = md_file.read_text(encoding="utf-8")
            except (UnicodeDecodeError, PermissionError):
                continue

            original = content

            # 替换 [[被删标题]] → [[保留标题]]
            # 替换 [[被删标题|别名]] → [[保留标题|别名]]
            # 注意：只替换精确匹配，避免部分匹配
            content = re.sub(
                r'\[\[' + re.escape(drop_stem) + r'(\|[^\]]*)?\]\]',
                lambda m: f'[[{keep_stem}{m.group(1) or ""}]]',
                content,
            )

            # 也处理带路径的引用：[[dir/被删标题]] → [[dir/保留标题]]
            drop_rel_no_ext = str(drop["path"].relative_to(self.vault_dir).with_suffix(""))
            keep_rel_no_ext = str(keep["path"].relative_to(self.vault_dir).with_suffix(""))
            if drop_rel_no_ext != keep_rel_no_ext:
                content = re.sub(
                    r'\[\[' + re.escape(drop_rel_no_ext) + r'(\|[^\]]*)?\]\]',
                    lambda m: f'[[{keep_rel_no_ext}{m.group(1) or ""}]]',
                    content,
                )

            if content != original:
                ref_count += 1
                if self.apply:
                    try:
                        md_file.write_text(content, encoding="utf-8")
                    except Exception as e:
                        self.errors.append({
                            "file": str(md_file.relative_to(self.vault_dir)),
                            "error": str(e),
                        })

        return ref_count

    def _pick_group_keeper(self, members: List[Dict]) -> Tuple[Dict, List[Dict]]:
        """从一组重复笔记中选择保留哪个，返回 (保留, [待删除列表])"""
        draft_keywords = ("临时草稿", "temp", "draft", "草稿")

        def sort_key(n):
            name_lower = n["path"].name.lower()
            is_protected = any(k in name_lower for k in _PROTECTED_KEYWORDS)
            is_draft = any(k in n["rel"] for k in draft_keywords)
            parts = n["rel"].split(os.sep)
            # 排序越小越优先保留：非保护 > 非草稿 > 路径浅 > 路径短
            return (not is_protected, is_draft, len(parts), len(n["rel"]))

        sorted_members = sorted(members, key=sort_key)
        return sorted_members[0], sorted_members[1:]

    def _scan_resource_files(self, resource_dirs_only: bool = False) -> List[Path]:
        """扫描资源文件

        Args:
            resource_dirs_only: True 时只扫描资源目录（attachments/、*_files/、images/），
                               False 时扫描全仓库（用于去重）
        """
        files = []
        for root, dirs, filenames in os.walk(self.vault_dir):
            root_path = Path(root)
            # 跳过隐藏目录
            if any(p.startswith(".") for p in root_path.relative_to(self.vault_dir).parts):
                continue

            # 孤儿检测模式：只扫描资源目录
            if resource_dirs_only and not _is_resource_dir(root_path, self.vault_dir):
                continue

            for fname in filenames:
                fpath = root_path / fname
                ext = fpath.suffix.lower()
                if resource_dirs_only:
                    if ext in RESOURCE_EXTENSIONS:
                        files.append(fpath)
                else:
                    if ext in DEDUP_EXTENSIONS:
                        files.append(fpath)
        return files

    def _group_by_hash(self, files: List[Path]) -> Dict[str, List[Path]]:
        """按文件内容哈希分组"""
        groups = defaultdict(list)
        for i, fpath in enumerate(files):
            if (i + 1) % 500 == 0:
                print(f"  已计算 {i + 1}/{len(files)}...")
            h = self._file_hash(fpath)
            if h:
                groups[h].append(fpath)
        return dict(groups)

    @staticmethod
    def _file_hash(fpath: Path) -> Optional[str]:
        """计算文件 MD5"""
        try:
            hasher = hashlib.md5()
            with open(fpath, "rb") as f:
                while chunk := f.read(8192):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception:
            return None

    def _pick_keeper(self, paths: List[Path]) -> Tuple[Path, List[Path]]:
        """选择保留的文件：优先路径最短的（通常在顶层 attachments/）"""
        # 按路径深度排序，浅的优先
        sorted_paths = sorted(paths, key=lambda p: len(p.parts))
        keeper = sorted_paths[0]
        remove_list = sorted_paths[1:]
        return keeper, remove_list

    def _update_refs(self, old_path: Path, new_path: Path):
        """将所有指向 old_path 的引用更新为指向 new_path

        处理三种场景：
        1. 文件名相同，路径不同 → 替换路径前缀
        2. 文件名不同，路径相同 → 替换文件名
        3. 文件名不同，路径也不同 → 替换完整路径
        """
        old_name = old_path.name
        new_name = new_path.name
        old_dir = old_path.parent
        new_dir = new_path.parent

        # 跳过完全相同的情况
        if old_path == new_path:
            return

        # 计算相对路径
        old_rel = str(old_path.relative_to(self.vault_dir))
        new_rel = str(new_path.relative_to(self.vault_dir))
        old_rel_dir = str(old_dir.relative_to(self.vault_dir))
        new_rel_dir = str(new_dir.relative_to(self.vault_dir))

        for md_file in self._find_all_md():
            try:
                content = md_file.read_text(encoding="utf-8")
            except (UnicodeDecodeError, PermissionError):
                continue

            original = content
            md_dir = md_file.parent

            # 计算从 md_dir 到 old/new 文件的相对路径
            old_ref = os.path.relpath(old_path, md_dir)
            new_ref = os.path.relpath(new_path, md_dir)

            # ── 标准 Markdown: ![alt](path) 和 [text](path) ──
            content = re.sub(
                r'(!?\[[^\]]*\]\()([^)]+)(\))',
                lambda m: f'{m.group(1)}{self._replace_ref(m.group(2), old_ref, new_ref, old_name, new_name)}{m.group(3)}'
                if self._is_local_ref(m.group(2)) else m.group(0),
                content,
            )

            # ── WikiLink: ![[path]] 和 [[path]] ──
            def replace_wikilink(m):
                full_ref = m.group(2).strip()
                alias = m.group(3) or ""
                file_part = full_ref.split("|")[0] if "|" in full_ref else full_ref
                new_file = self._replace_ref(file_part, old_ref, new_ref, old_name, new_name)
                if new_file != file_part:
                    if alias:
                        return f'{m.group(1)}{new_file}{alias}{m.group(4)}'
                    return f'{m.group(1)}{new_file}{m.group(4)}'
                return m.group(0)

            content = re.sub(
                r'(!?\[\[)([^\]]+?)(\|[^\]]*)?(\]\])',
                replace_wikilink,
                content,
            )

            # ── HTML: <img src="path"> ──
            content = re.sub(
                r'(<img[^>]+src=["\'])([^"\']+)(["\'])',
                lambda m: f'{m.group(1)}{self._replace_ref(m.group(2), old_ref, new_ref, old_name, new_name)}{m.group(3)}'
                if self._is_local_ref(m.group(2)) else m.group(0),
                content,
            )

            if content != original:
                if self.apply:
                    try:
                        md_file.write_text(content, encoding="utf-8")
                    except Exception as e:
                        self.errors.append({
                            "file": str(md_file.relative_to(self.vault_dir)),
                            "error": str(e),
                        })

    @staticmethod
    def _is_local_ref(ref: str) -> bool:
        """判断是否是本地引用（非 URL）"""
        return not ref.startswith(("http://", "https://", "data:", "#"))

    @staticmethod
    def _replace_ref(current_ref: str, old_ref: str, new_ref: str,
                     old_name: str, new_name: str) -> str:
        """替换引用路径

        优先精确匹配完整路径，再退化到仅匹配文件名。
        """
        # 精确匹配完整路径（处理路径+文件名都不同的情况）
        if current_ref == old_ref:
            return new_ref

        # 仅文件名相同，路径不同（处理路径不同但文件名相同的情况）
        if current_ref.endswith("/" + old_name) or current_ref == old_name:
            if old_name == new_name:
                # 文件名相同，替换目录前缀
                old_prefix = current_ref[:len(current_ref) - len(old_name)]
                new_prefix = os.path.dirname(new_ref) + "/"
                if old_prefix and old_prefix != new_prefix:
                    return new_prefix + new_name
            else:
                # 文件名也不同，替换整个引用
                return new_ref

        return current_ref

    # ── 孤儿文件检测 ──────────────────────────────────────

    def orphan(self) -> Dict:
        """检测未被任何笔记引用的资源文件（仅扫描资源目录）"""
        print("🔍 扫描资源目录...")
        all_resources = self._scan_resource_files(resource_dirs_only=True)
        print(f"  找到 {len(all_resources)} 个资源文件\n")

        print("📝 收集所有笔记中的引用...")
        ref_names, ref_paths = self._collect_all_references()
        print(f"  引用了 {len(ref_names)} 个不同的文件名，{len(ref_paths)} 个可解析路径\n")

        print("🔎 检测孤儿文件...")
        orphans = []
        non_orphans = []
        excluded = []
        for fpath in all_resources:
            fname = fpath.name
            ext = fpath.suffix.lower()
            if ext in self.exclude_ext:
                excluded.append(fpath)
                continue
            # 优先按绝对路径精确匹配，再退化到文件名匹配
            if fpath.resolve() in ref_paths or fname in ref_names:
                non_orphans.append(fpath)
            else:
                orphans.append(fpath)

        # 统计
        orphan_size = sum(f.stat().st_size for f in orphans)
        excluded_size = sum(f.stat().st_size for f in excluded)
        print(f"\n{'=' * 60}")
        print(f"📊 孤儿文件检测结果")
        print(f"{'=' * 60}")
        print(f"资源文件总数:   {len(all_resources)}")
        print(f"被引用的文件:   {len(non_orphans)}")
        if excluded:
            print(f"已排除的文件:   {len(excluded)}  ({self._format_size(excluded_size)})  {', '.join(sorted(self.exclude_ext))}")
        print(f"孤儿文件:       {len(orphans)}  ({self._format_size(orphan_size)})")

        if orphans:
            # 按扩展名分组显示
            ext_groups = defaultdict(list)
            for f in orphans:
                ext = f.suffix.lower() or "(无)"
                ext_groups[ext].append(f)

            print(f"\n{'─' * 60}")
            print("孤儿文件列表:")
            for ext in sorted(ext_groups, key=lambda e: -sum(f.stat().st_size for f in ext_groups[e])):
                files = sorted(ext_groups[ext])
                size = sum(f.stat().st_size for f in files)
                print(f"\n  {ext}  ({len(files)} 个, {self._format_size(size)})")
                for f in files[:10]:
                    rel = str(f.relative_to(self.vault_dir))
                    fsize = f.stat().st_size
                    print(f"    {rel}  ({self._format_size(fsize)})")
                if len(files) > 10:
                    print(f"    ... 还有 {len(files) - 10} 个")

            if self.apply:
                print(f"\n🗑️  删除孤儿文件...")
                deleted = 0
                for fpath in orphans:
                    try:
                        fpath.unlink()
                        deleted += 1
                    except Exception as e:
                        self.errors.append({"file": str(fpath), "error": str(e)})
                print(f"  已删除 {deleted} 个文件")
            else:
                print(f"\n💡 使用 --apply 参数实际删除孤儿文件")

        print(f"{'=' * 60}\n")

        return {
            "total_resources": len(all_resources),
            "referenced": len(non_orphans),
            "orphans": len(orphans),
            "orphan_size": orphan_size,
            "orphan_paths": [str(f.relative_to(self.vault_dir)) for f in orphans],
            "errors": len(self.errors),
        }

    # ── 修复失效引用 ──────────────────────────────────────

    def fix_orphans(self) -> Dict:
        """修复失效引用：将孤儿文件重新链接到笔记"""
        print("🔍 扫描资源目录...")
        all_resources = self._scan_resource_files(resource_dirs_only=True)
        print(f"  找到 {len(all_resources)} 个资源文件\n")

        # 建立文件名 → 实际路径的索引
        file_index: Dict[str, List[Path]] = defaultdict(list)
        for fpath in all_resources:
            file_index[fpath.name].append(fpath)

        print("📝 扫描所有笔记的引用，查找失效链接...")
        md_files = self._find_all_md()
        print(f"  扫描 {len(md_files)} 个 Markdown 文件\n")

        # 收集所有失效引用: (md_file, original_ref, ref_type) → broken
        broken_refs: List[Dict] = []
        for md_file in md_files:
            try:
                content = md_file.read_text(encoding="utf-8")
            except (UnicodeDecodeError, PermissionError):
                continue

            md_dir = md_file.parent

            # 标准 Markdown: ![alt](path) 和 [text](path)
            for m in re.finditer(r'(!?\[[^\]]*\]\()([^)]+)(\))', content):
                ref = m.group(2)
                if ref.startswith(("http://", "https://", "data:", "#")):
                    continue
                full_path = (md_dir / ref).resolve()
                if not full_path.exists():
                    filename = Path(ref).name
                    if filename in file_index:
                        broken_refs.append({
                            "md_file": md_file,
                            "ref": ref,
                            "filename": filename,
                            "match": file_index[filename][0],
                            "type": "markdown",
                            "line": content[:m.start()].count("\n") + 1,
                        })

            # WikiLink: ![[path]] 和 [[path]]
            for m in re.finditer(r'(!?\[\[)([^\]|#]+?)(\|[^\]]*)?(\]\])', content):
                ref = m.group(2).strip()
                if ref.startswith(("http://", "https://")):
                    continue
                # WikiLink 可能没有扩展名，也可能有
                full_path = (md_dir / ref).resolve()
                if not full_path.exists():
                    # 尝试加 .md 扩展名
                    full_path_md = (md_dir / (ref + ".md")).resolve()
                    if full_path_md.exists():
                        continue  # 是笔记链接，跳过
                    filename = Path(ref).name
                    if filename in file_index:
                        broken_refs.append({
                            "md_file": md_file,
                            "ref": ref,
                            "filename": filename,
                            "match": file_index[filename][0],
                            "type": "wikilink",
                            "line": content[:m.start()].count("\n") + 1,
                        })

            # HTML img: <img src="...">
            for m in re.finditer(r'(<img[^>]+src=["\'])([^"\']+)(["\'])', content):
                ref = m.group(2)
                if ref.startswith(("http://", "https://", "data:")):
                    continue
                full_path = (md_dir / ref).resolve()
                if not full_path.exists():
                    filename = Path(ref).name
                    if filename in file_index:
                        broken_refs.append({
                            "md_file": md_file,
                            "ref": ref,
                            "filename": filename,
                            "match": file_index[filename][0],
                            "type": "html",
                            "line": content[:m.start()].count("\n") + 1,
                        })

        # 去重：同一个 md_file + ref 只处理一次
        seen = set()
        unique_broken = []
        for br in broken_refs:
            key = (str(br["md_file"]), br["ref"])
            if key not in seen:
                seen.add(key)
                unique_broken.append(br)

        # 统计匹配到的孤儿文件
        matched_orphans = set()
        for br in unique_broken:
            matched_orphans.add(str(br["match"]))

        print(f"{'=' * 60}")
        print(f"📊 失效引用修复结果")
        print(f"{'=' * 60}")
        print(f"失效引用数:     {len(unique_broken)}")
        print(f"可匹配的孤儿:   {len(matched_orphans)} 个")

        if not unique_broken:
            print("✅ 没有发现可修复的失效引用")
            return {"broken_refs": 0, "fixed": 0, "errors": 0}

        # 按笔记分组显示
        note_groups = defaultdict(list)
        for br in unique_broken:
            note_groups[str(br["md_file"].relative_to(self.vault_dir))].append(br)

        print(f"涉及笔记数:    {len(note_groups)}")
        print(f"\n{'─' * 60}")

        fixed = 0
        for note_path in sorted(note_groups.keys()):
            refs = note_groups[note_path]
            print(f"\n📝 {note_path}")
            for br in refs:
                old_ref = br["ref"]
                target_file = br["match"]
                new_ref = self._compute_new_ref(br["md_file"], target_file)
                print(f"  {br['type']} L{br['line']}: {old_ref}")
                print(f"    → {new_ref}")

                if self.apply:
                    try:
                        content = br["md_file"].read_text(encoding="utf-8")
                        if br["type"] == "markdown":
                            content = content.replace(f"]({old_ref})", f"]({new_ref})")
                        elif br["type"] == "wikilink":
                            content = content.replace(f"[[{old_ref}]]", f"[[{new_ref}]]")
                            content = content.replace(f"[[{old_ref}|", f"[[{new_ref}|")
                        elif br["type"] == "html":
                            content = content.replace(f'src="{old_ref}"', f'src="{new_ref}"')
                            content = content.replace(f"src='{old_ref}'", f"src='{new_ref}'")
                        br["md_file"].write_text(content, encoding="utf-8")
                        fixed += 1
                    except Exception as e:
                        self.errors.append({"file": note_path, "error": str(e)})
                        print(f"    ❌ 修复失败: {e}")
                else:
                    fixed += 1

        print(f"\n{'=' * 60}")
        print(f"{'已修复' if self.apply else '将修复'}: {fixed}/{len(unique_broken)} 个引用")
        if self.errors:
            print(f"错误: {len(self.errors)}")
        print(f"{'=' * 60}\n")

        return {
            "broken_refs": len(unique_broken),
            "fixed": fixed,
            "errors": len(self.errors),
        }

    def _compute_new_ref(self, md_file: Path, target_file: Path) -> str:
        """计算从 md_file 到 target_file 的相对路径"""
        try:
            return os.path.relpath(target_file, md_file.parent)
        except ValueError:
            return str(target_file.relative_to(self.vault_dir))

    def _collect_all_references(self) -> Tuple[Set[str], Set[Path]]:
        """收集所有 Markdown 文件中的引用，返回 (文件名集合, 解析后的绝对路径集合)

        文件名集合：用于快速匹配（可能存在同名误匹配）
        绝对路径集合：用于精确匹配（避免同名不同路径的误判）
        """
        referenced_names = set()
        referenced_paths = set()
        md_files = self._find_all_md()

        for md_file in md_files:
            md_dir = md_file.parent
            try:
                content = md_file.read_text(encoding="utf-8")
            except (UnicodeDecodeError, PermissionError):
                continue

            refs = []
            # 标准 Markdown: ![alt](path) 和 [text](path)
            for m in re.finditer(r'!\[[^\]]*\]\(([^)]+)\)', content):
                ref = m.group(1)
                if not ref.startswith(("http://", "https://", "data:", "#")):
                    refs.append(ref)

            # WikiLink: ![[path]] 和 [[path]]
            for m in re.finditer(r'!?\[\[([^\]|#]+?)(?:\|[^\]]*)?\]\]', content):
                ref = m.group(1).strip()
                if not ref.startswith(("http://", "https://")):
                    refs.append(ref)

            # HTML img: <img src="...">
            for m in re.finditer(r'<img[^>]+src=["\']([^"\']+)["\']', content):
                ref = m.group(1)
                if not ref.startswith(("http://", "https://", "data:")):
                    refs.append(ref)

            for ref in refs:
                referenced_names.add(Path(ref).name)
                # 解析为绝对路径
                resolved = (md_dir / ref).resolve()
                if resolved.exists():
                    referenced_paths.add(resolved)

        return referenced_names, referenced_paths

    def _find_all_md(self) -> List[Path]:
        """找到所有 Markdown 文件"""
        md_files = []
        for root, dirs, files in os.walk(self.vault_dir):
            root_path = Path(root)
            if any(p.startswith(".") for p in root_path.relative_to(self.vault_dir).parts):
                continue
            for f in files:
                if f.endswith(".md"):
                    md_files.append(root_path / f)
        return md_files

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        for unit in ["B", "KB", "MB", "GB"]:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"


def main():
    parser = argparse.ArgumentParser(
        description="Obsidian 仓库清理工具（去重 + 孤儿文件 + 引用修复）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
模式说明:
  dedup    按内容哈希检测重复文件，每组保留一个，删除其余并更新引用
  fuzzy    检测近似重复笔记（按标题+去除链接后的纯文本比对）
  clean    检测并清理空笔记和空目录
  orphan   检测未被任何笔记引用的资源文件（孤儿文件）
  fix      修复失效引用，将孤儿文件重新链接到笔记

示例:
  python3 tools/vault_cleaner.py dedup /path/to/vault             # 检测重复（预览）
  python3 tools/vault_cleaner.py dedup /path/to/vault --apply     # 执行去重删除
  python3 tools/vault_cleaner.py fuzzy /path/to/vault             # 近似重复检测（预览）
  python3 tools/vault_cleaner.py fuzzy /path/to/vault --apply     # 删除近似重复
  python3 tools/vault_cleaner.py orphan /path/to/vault            # 检测孤儿（预览）
  python3 tools/vault_cleaner.py orphan /path/to/vault --apply    # 删除孤儿文件
  python3 tools/vault_cleaner.py orphan /path/to/vault --apply --exclude-ext .pdf .xls  # 自定义排除
  python3 tools/vault_cleaner.py fix /path/to/vault               # 修复失效引用（预览）
  python3 tools/vault_cleaner.py fix /path/to/vault --apply       # 执行修复
        """,
    )
    parser.add_argument("mode", choices=["dedup", "fuzzy", "clean", "orphan", "fix"], help="运行模式")
    parser.add_argument("vault_dir", help="Obsidian Vault 目录路径")
    parser.add_argument("--apply", action="store_true", help="实际执行删除（默认仅预览）")
    parser.add_argument("--exclude-ext", nargs="+", metavar=".ext",
                        help="排除的文件扩展名（默认排除 .pdf .xls .xlsx .xmind，仅对 orphan 模式有效）")
    parser.add_argument("--threshold", type=float, default=0.8, metavar="0.0-1.0",
                        help="近似重复相似度阈值（默认 0.8，仅对 fuzzy 模式有效）")
    parser.add_argument("--fix-untitled", action="store_true",
                        help="清理笔记开头的「无标题」占位符（仅对 clean 模式有效）")

    args = parser.parse_args()

    vault = Path(args.vault_dir)
    if not vault.is_dir():
        print(f"❌ 目录不存在: {vault}")
        sys.exit(1)

    if not (vault / ".obsidian").is_dir():
        print(f"⚠️  警告: {vault} 看起来不是 Obsidian Vault（缺少 .obsidian 目录）")
        confirm = input("是否继续？(y/N): ")
        if confirm.lower() != "y":
            sys.exit(0)

    if args.apply:
        action = {"fix": "修复引用", "fuzzy": "删除近似重复", "clean": "清理空内容"}.get(args.mode, "删除操作")
        print(f"⚠️  即将执行{action}")
        confirm = input("确认继续？(y/N): ")
        if confirm.lower() != "y":
            print("已取消")
            sys.exit(0)

    if args.exclude_ext:
        exclude_ext = set()
        for ext in args.exclude_ext:
            if not ext.startswith("."):
                ext = "." + ext
            exclude_ext.add(ext.lower())
    else:
        exclude_ext = DEFAULT_EXCLUDE_EXT

    cleaner = VaultCleaner(str(vault), apply=args.apply, exclude_ext=exclude_ext)

    if args.mode == "dedup":
        result = cleaner.dedup()
        print(f"\n{'=' * 60}")
        print(f"📊 去重结果")
        print(f"{'=' * 60}")
        print(f"资源文件总数: {result['total_files']}")
        print(f"重复组数:     {result['dup_groups']}")
        print(f"冗余文件数:   {result['dup_files']}")
        print(f"{'已删除' if args.apply else '将删除'}: {result['removed']} 个")
        if result.get("errors"):
            print(f"错误: {result['errors']}")
        print(f"{'=' * 60}\n")

    elif args.mode == "fuzzy":
        result = cleaner.fuzzy(threshold=args.threshold)

    elif args.mode == "clean":
        result = cleaner.clean(fix_untitled=args.fix_untitled)

    elif args.mode == "orphan":
        result = cleaner.orphan()

    elif args.mode == "fix":
        result = cleaner.fix_orphans()


if __name__ == "__main__":
    main()
