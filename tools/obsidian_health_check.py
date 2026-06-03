#!/usr/bin/env python3
"""
Obsidian 仓库健康检查工具
一站式检查：重复内容、附件完整性、链接格式、文件结构

使用方法:
    python3 obsidian_health_check.py --vault "/path/to/your/vault"
    python3 obsidian_health_check.py --quick  # 快速检查
    python3 obsidian_health_check.py --full   # 完整检查（包括相似度分析）
"""

import os
import re
import hashlib
from pathlib import Path
from collections import defaultdict
from datetime import datetime
import difflib


class ObsidianHealthChecker:
    """Obsidian 仓库健康检查器"""

    # 支持的附件类型
    IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg', '.bmp'}
    DOCUMENT_EXTENSIONS = {'.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.xmind'}
    MEDIA_EXTENSIONS = {'.mp3', '.mp4', '.mov', '.avi', '.wav', '.flac'}
    ARCHIVE_EXTENSIONS = {'.zip', '.rar', '.7z', '.tar', '.gz'}

    def __init__(self, vault_path: str):
        self.vault_path = Path(vault_path)
        self.results = {
            'score': 0,
            'check_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'attachments': {
                'total': 0,
                'by_type': defaultdict(lambda: {
                    'wikilink': 0,
                    'markdown': 0,
                    'missing': 0,
                    'found': 0,
                    'details': []
                })
            },
            'duplicates': {
                'files': [],
                'names': [],
                'content': [],
                'empty': [],
                'tiny': []
            },
            'links': {
                'broken': [],
                'external': 0,
                'internal': 0
            },
            'structure': {
                'folders': 0,
                'files': 0,
                'total_size': 0
            }
        }

    def get_attachment_type(self, ext: str) -> str:
        """获取附件类型"""
        ext = ext.lower()
        if ext in self.IMAGE_EXTENSIONS:
            return '图片'
        elif ext in self.DOCUMENT_EXTENSIONS:
            return '文档'
        elif ext in self.MEDIA_EXTENSIONS:
            return '媒体'
        elif ext in self.ARCHIVE_EXTENSIONS:
            return '压缩包'
        else:
            return '其他'

    def get_file_hash(self, file_path: Path) -> str:
        """计算文件内容的 MD5 哈希值"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            return hashlib.md5(content.encode('utf-8')).hexdigest()
        except Exception as e:
            return None

    def get_content_normalized(self, file_path: Path) -> str:
        """获取标准化内容（去除空格、换行等）"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            # 移除 frontmatter
            if content.startswith('---'):
                parts = content.split('---', 2)
                if len(parts) >= 3:
                    content = parts[2]

            # 标准化：移除多余空格、换行
            content = re.sub(r'\s+', ' ', content)
            content = content.lower().strip()

            return content
        except Exception as e:
            return ""

    def run_full_check(self, quick_mode: bool = False):
        """执行完整检查"""
        print("=" * 60)
        print("🏥 Obsidian 仓库健康检查工具")
        print("=" * 60)
        print(f"仓库路径: {self.vault_path}")
        print(f"检查时间: {self.results['check_time']}")
        print(f"检查模式: {'快速检查' if quick_mode else '完整检查'}\n")

        # 获取所有 Markdown 文件
        md_files = list(self.vault_path.rglob("*.md"))
        md_files = [f for f in md_files if '.obsidian' not in str(f) and '.trash' not in str(f)]

        self.results['structure']['files'] = len(md_files)
        print(f"📊 找到 {len(md_files)} 个笔记文件\n")

        # 1. 检查附件
        print("1️⃣  检查附件完整性和格式...")
        self._check_attachments(md_files)

        # 2. 检查重复内容
        if not quick_mode:
            print("\n2️⃣  检查重复内容...")
            self._check_duplicate_files(md_files)
            self._check_duplicate_names(md_files)

            if len(md_files) <= 200:  # 只在文件数少于200时检查相似度
                print("   检查内容相似度（这可能需要一些时间）...")
                self._check_similar_content(md_files)

            self._check_tiny_files(md_files)
        else:
            print("\n2️⃣  跳过重复内容检查（快速模式）")

        # 3. 检查文件结构
        print("\n3️⃣  分析文件结构...")
        self._check_structure()

        # 4. 计算健康度评分
        print("\n4️⃣  计算健康度评分...")
        self._calculate_score()

        # 5. 生成报告
        self.generate_report(quick_mode)

        return self.results

    def _check_attachments(self, md_files):
        """检查附件完整性和格式"""
        for md_file in md_files:
            try:
                with open(md_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                # 1. WikiLink 格式
                wikilink_pattern = r'!?\[\[([^\]|]+)(?:\|[^\]]+)?\]\]'
                for match in re.finditer(wikilink_pattern, content):
                    link_path = match.group(1).strip()

                    # 移除锚点部分（#后面的内容）
                    if '#' in link_path:
                        link_path = link_path.split('#')[0]

                    # 获取扩展名
                    ext = Path(link_path).suffix.lower()

                    # 跳过笔记链接（.md 或无扩展名）
                    if ext == '.md' or not ext:
                        continue

                    attachment_type = self.get_attachment_type(ext)
                    self.results['attachments']['total'] += 1
                    self.results['attachments']['by_type'][attachment_type]['wikilink'] += 1

                    # 检查文件是否存在
                    full_path = md_file.parent / link_path
                    if not full_path.exists():
                        full_path = self.vault_path / link_path
                        if not full_path.exists():
                            matches = list(self.vault_path.rglob(Path(link_path).name))
                            full_path = matches[0] if matches else None

                    if full_path and full_path.exists():
                        self.results['attachments']['by_type'][attachment_type]['found'] += 1
                    else:
                        self.results['attachments']['by_type'][attachment_type]['missing'] += 1
                        self.results['attachments']['by_type'][attachment_type]['details'].append({
                            'note': str(md_file.relative_to(self.vault_path)),
                            'link': link_path,
                            'format': 'wikilink'
                        })

                # 2. Markdown 格式
                content_no_wikilink = re.sub(r'!?\[\[.*?\]\]', '', content)
                md_pattern = r'!?\[([^\]]*)\]\(([^)]+)\)'
                for match in re.finditer(md_pattern, content_no_wikilink):
                    link_path = match.group(2).strip()

                    # 跳过外部链接
                    if link_path.startswith('http://') or link_path.startswith('https://'):
                        self.results['links']['external'] += 1
                        continue

                    # 移除锚点部分（#后面的内容）
                    if '#' in link_path:
                        link_path = link_path.split('#')[0]

                    # 获取扩展名
                    ext = Path(link_path).suffix.lower()

                    # 跳过笔记链接（.md 或无扩展名）
                    if ext == '.md' or not ext:
                        continue

                    attachment_type = self.get_attachment_type(ext)
                    self.results['attachments']['total'] += 1
                    self.results['attachments']['by_type'][attachment_type]['markdown'] += 1

                    # 检查文件是否存在
                    full_path = md_file.parent / link_path
                    if not full_path.exists():
                        full_path = self.vault_path / link_path
                        if not full_path.exists():
                            matches = list(self.vault_path.rglob(Path(link_path).name))
                            full_path = matches[0] if matches else None

                    if full_path and full_path.exists():
                        self.results['attachments']['by_type'][attachment_type]['found'] += 1
                    else:
                        self.results['attachments']['by_type'][attachment_type]['missing'] += 1
                        self.results['attachments']['by_type'][attachment_type]['details'].append({
                            'note': str(md_file.relative_to(self.vault_path)),
                            'link': match.group(2).strip(),  # 保存原始链接（包含锚点）
                            'format': 'markdown'
                        })

            except Exception as e:
                pass

        # 打印结果
        total_wikilink = sum(stats['wikilink'] for stats in self.results['attachments']['by_type'].values())
        total_markdown = sum(stats['markdown'] for stats in self.results['attachments']['by_type'].values())
        total_missing = sum(stats['missing'] for stats in self.results['attachments']['by_type'].values())

        if total_markdown > 0:
            print(f"   ⚠️  发现 {total_markdown} 个 Markdown 格式的附件链接")
        else:
            print(f"   ✅ 所有附件链接使用 WikiLink 格式")

        if total_missing > 0:
            print(f"   ⚠️  {total_missing} 个附件文件缺失")
        else:
            print(f"   ✅ 所有附件文件都存在")

    def _check_duplicate_files(self, md_files):
        """检查完全相同的文件"""
        hash_map = defaultdict(list)

        for md_file in md_files:
            file_hash = self.get_file_hash(md_file)
            if file_hash:
                hash_map[file_hash].append(md_file)

        # 找出重复的文件
        for file_hash, files in hash_map.items():
            if len(files) > 1:
                self.results['duplicates']['files'].append({
                    'hash': file_hash,
                    'files': [str(f.relative_to(self.vault_path)) for f in files],
                    'count': len(files)
                })

        if self.results['duplicates']['files']:
            print(f"   ⚠️  发现 {len(self.results['duplicates']['files'])} 组完全相同的文件")
        else:
            print(f"   ✅ 没有发现完全相同的文件")

    def _check_duplicate_names(self, md_files):
        """检查文件名重复"""
        name_map = defaultdict(list)

        for md_file in md_files:
            filename = md_file.name
            name_map[filename].append(md_file)

        # 找出文件名重复的文件
        for filename, files in name_map.items():
            if len(files) > 1:
                self.results['duplicates']['names'].append({
                    'filename': filename,
                    'files': [str(f.relative_to(self.vault_path)) for f in files],
                    'count': len(files)
                })

        if self.results['duplicates']['names']:
            print(f"   ⚠️  发现 {len(self.results['duplicates']['names'])} 个重复的文件名")
        else:
            print(f"   ✅ 没有发现重复的文件名")

    def _check_similar_content(self, md_files):
        """检查内容相似的文件"""
        for i, file1 in enumerate(md_files):
            content1 = self.get_content_normalized(file1)
            if not content1:
                continue

            for file2 in md_files[i+1:]:
                content2 = self.get_content_normalized(file2)
                if not content2:
                    continue

                # 计算相似度
                similarity = difflib.SequenceMatcher(None, content1, content2).ratio()

                # 如果相似度超过 80%，认为是相似内容
                if similarity > 0.8:
                    self.results['duplicates']['content'].append({
                        'file1': str(file1.relative_to(self.vault_path)),
                        'file2': str(file2.relative_to(self.vault_path)),
                        'similarity': f"{similarity*100:.1f}%"
                    })

        if self.results['duplicates']['content']:
            print(f"   ⚠️  发现 {len(self.results['duplicates']['content'])} 对内容相似的文件")
        else:
            print(f"   ✅ 没有发现内容相似的文件")

    def _check_tiny_files(self, md_files):
        """检查空文件和内容过少的文件"""
        for md_file in md_files:
            try:
                with open(md_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                # 移除 frontmatter
                if content.startswith('---'):
                    parts = content.split('---', 2)
                    if len(parts) >= 3:
                        main_content = parts[2].strip()
                    else:
                        main_content = content
                else:
                    main_content = content

                word_count = len(main_content.split())

                if word_count == 0:
                    self.results['duplicates']['empty'].append({
                        'file': str(md_file.relative_to(self.vault_path)),
                        'words': 0
                    })
                elif word_count < 10:
                    self.results['duplicates']['tiny'].append({
                        'file': str(md_file.relative_to(self.vault_path)),
                        'words': word_count
                    })

            except Exception as e:
                pass

        total_tiny = len(self.results['duplicates']['empty']) + len(self.results['duplicates']['tiny'])
        if total_tiny > 0:
            print(f"   ⚠️  发现 {len(self.results['duplicates']['empty'])} 个空文件，{len(self.results['duplicates']['tiny'])} 个内容过少的文件")
        else:
            print(f"   ✅ 没有发现空文件或内容过少的文件")

    def _check_structure(self):
        """分析文件结构"""
        # 统计文件夹
        all_folders = set()
        total_size = 0

        for file_path in self.vault_path.rglob("*"):
            if '.obsidian' in str(file_path) or '.trash' in str(file_path):
                continue

            if file_path.is_file():
                total_size += file_path.stat().st_size
                all_folders.add(file_path.parent)

        self.results['structure']['folders'] = len(all_folders)
        self.results['structure']['total_size'] = total_size

        # 转换为人类可读格式
        size_mb = total_size / (1024 * 1024)
        size_gb = size_mb / 1024

        if size_gb >= 1:
            size_str = f"{size_gb:.2f} GB"
        else:
            size_str = f"{size_mb:.2f} MB"

        print(f"   📁 文件夹数: {len(all_folders)}")
        print(f"   📄 文件数: {self.results['structure']['files']}")
        print(f"   💾 总大小: {size_str}")

    def _calculate_score(self):
        """计算健康度评分"""
        score = 100

        # 扣分项
        # 1. 重复文件（每个-10分）
        score -= len(self.results['duplicates']['files']) * 10

        # 2. 缺失附件（每个-2分）
        total_missing = sum(stats['missing'] for stats in self.results['attachments']['by_type'].values())
        score -= total_missing * 2

        # 3. Markdown 格式附件（每个-1分）
        total_markdown = sum(stats['markdown'] for stats in self.results['attachments']['by_type'].values())
        score -= total_markdown * 1

        # 4. 空文件（每个-5分）
        score -= len(self.results['duplicates']['empty']) * 5

        # 5. 内容过少（每个-1分）
        score -= len(self.results['duplicates']['tiny']) * 1

        # 6. 相似内容（每对-3分）
        score -= len(self.results['duplicates']['content']) * 3

        self.results['score'] = max(0, min(100, score))

    def generate_report(self, quick_mode: bool = False):
        """生成详细报告"""
        report = []
        report.append("\n" + "=" * 60)
        report.append("🏥 Obsidian 仓库健康检查报告")
        report.append("=" * 60)
        report.append(f"检查时间: {self.results['check_time']}")
        report.append(f"仓库路径: {self.vault_path}")
        report.append(f"检查模式: {'快速检查' if quick_mode else '完整检查'}")

        # 健康度评分
        score = self.results['score']
        if score >= 90:
            emoji = "🌟🌟🌟🌟🌟"
        elif score >= 80:
            emoji = "🌟🌟🌟🌟"
        elif score >= 70:
            emoji = "🌟🌟🌟"
        elif score >= 60:
            emoji = "🌟🌟"
        else:
            emoji = "🌟"

        report.append(f"\n## 📊 总体健康度: {score}/100 {emoji}")

        # 仓库统计
        report.append(f"\n## 📈 仓库统计")
        report.append(f"- 文件总数: {self.results['structure']['files']}")
        report.append(f"- 附件总数: {self.results['attachments']['total']}")
        report.append(f"- 文件夹数: {self.results['structure']['folders']}")

        size_bytes = self.results['structure']['total_size']
        size_mb = size_bytes / (1024 * 1024)
        size_gb = size_mb / 1024
        size_str = f"{size_gb:.2f} GB" if size_gb >= 1 else f"{size_mb:.2f} MB"
        report.append(f"- 总大小: {size_str}")

        # 良好指标
        report.append(f"\n## ✅ 良好指标")
        total_wikilink = sum(stats['wikilink'] for stats in self.results['attachments']['by_type'].values())
        total_markdown = sum(stats['markdown'] for stats in self.results['attachments']['by_type'].values())
        total_attachments = total_wikilink + total_markdown

        if total_attachments > 0:
            wikilink_rate = total_wikilink / total_attachments * 100
            report.append(f"- ✅ {wikilink_rate:.1f}% 附件使用 WikiLink 格式")

        if not self.results['duplicates']['files']:
            report.append(f"- ✅ 0 个重复文件")

        if not self.results['duplicates']['empty']:
            report.append(f"- ✅ 0 个空文件")

        # 需要关注的问题
        issues = []

        # 附件问题
        for attachment_type, stats in self.results['attachments']['by_type'].items():
            if stats['missing'] > 0:
                issues.append(f"- ⚠️  {stats['missing']} 个{attachment_type}文件缺失")
            if stats['markdown'] > 0:
                issues.append(f"- ⚠️  {stats['markdown']} 个{attachment_type}使用 Markdown 格式")

        # 重复问题
        if self.results['duplicates']['files']:
            issues.append(f"- ⚠️  {len(self.results['duplicates']['files'])} 组完全相同的文件")

        if self.results['duplicates']['names']:
            issues.append(f"- ⚠️  {len(self.results['duplicates']['names'])} 个重复的文件名")

        if self.results['duplicates']['content']:
            issues.append(f"- ⚠️  {len(self.results['duplicates']['content'])} 对内容相似的文件")

        if self.results['duplicates']['empty']:
            issues.append(f"- ⚠️  {len(self.results['duplicates']['empty'])} 个空文件")

        if self.results['duplicates']['tiny']:
            issues.append(f"- ⚠️  {len(self.results['duplicates']['tiny'])} 个内容过少的文件")

        if issues:
            report.append(f"\n## ⚠️ 需要关注")
            report.extend(issues)
        else:
            report.append(f"\n## 🎉 完美！没有发现任何问题")

        # 建议操作
        if issues:
            report.append(f"\n## 🔧 建议操作")
            priority = 1

            if self.results['duplicates']['files']:
                report.append(f"{priority}. [高优先级] 删除重复文件")
                priority += 1

            total_missing = sum(stats['missing'] for stats in self.results['attachments']['by_type'].values())
            if total_missing > 0:
                report.append(f"{priority}. [高优先级] 修复 {total_missing} 个缺失的附件")
                priority += 1

            if self.results['duplicates']['empty']:
                report.append(f"{priority}. [中优先级] 删除或补充 {len(self.results['duplicates']['empty'])} 个空文件")
                priority += 1

            if self.results['duplicates']['content']:
                report.append(f"{priority}. [低优先级] 合并或区分 {len(self.results['duplicates']['content'])} 对相似文件")
                priority += 1

        report.append("\n" + "=" * 60)

        # 打印报告
        print('\n'.join(report))

        # 保存详细报告到文件
        output_file = self.vault_path / f"health_check_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report))

            # 添加详细的问题列表
            f.write("\n\n## 📋 详细问题列表\n")

            # 缺失的附件
            for attachment_type, stats in self.results['attachments']['by_type'].items():
                if stats['missing'] > 0:
                    f.write(f"\n### 缺失的{attachment_type}文件\n\n")
                    for i, detail in enumerate(stats['details'], 1):
                        f.write(f"{i}. **笔记**: `{detail['note']}`\n")
                        f.write(f"   **链接**: `{detail['link']}`\n\n")

            # 重复文件
            if self.results['duplicates']['files']:
                f.write(f"\n### 完全相同的文件\n\n")
                for i, dup in enumerate(self.results['duplicates']['files'], 1):
                    f.write(f"#### 第 {i} 组 ({dup['count']} 个文件)\n\n")
                    for file in dup['files']:
                        f.write(f"- `{file}`\n")
                    f.write("\n")

            # 内容相似
            if self.results['duplicates']['content']:
                f.write(f"\n### 内容相似的文件\n\n")
                for i, sim in enumerate(self.results['duplicates']['content'], 1):
                    f.write(f"{i}. **相似度**: {sim['similarity']}\n")
                    f.write(f"   - `{sim['file1']}`\n")
                    f.write(f"   - `{sim['file2']}`\n\n")

            # 空文件和内容过少的文件
            if self.results['duplicates']['empty']:
                f.write(f"\n### 空文件\n\n")
                for empty in self.results['duplicates']['empty']:
                    f.write(f"- `{empty['file']}`\n")

            if self.results['duplicates']['tiny']:
                f.write(f"\n### 内容过少的文件\n\n")
                for tiny in self.results['duplicates']['tiny']:
                    f.write(f"- `{tiny['file']}` ({tiny['words']} 词)\n")

        print(f"\n📄 详细报告已保存: {output_file}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Obsidian 仓库健康检查工具')
    parser.add_argument('--vault', help='Obsidian 仓库路径（默认当前目录）',
                        default=os.getcwd())
    parser.add_argument('--quick', action='store_true', help='快速检查模式（跳过相似度分析）')
    parser.add_argument('--full', action='store_true', help='完整检查模式（包括相似度分析）')

    args = parser.parse_args()

    # 展开路径中的 ~ 符号
    vault_path = os.path.expanduser(args.vault)

    if not Path(vault_path).exists():
        print(f"❌ 仓库路径不存在: {vault_path}")
        return

    checker = ObsidianHealthChecker(vault_path)
    quick_mode = args.quick and not args.full
    checker.run_full_check(quick_mode=quick_mode)


if __name__ == '__main__':
    main()
