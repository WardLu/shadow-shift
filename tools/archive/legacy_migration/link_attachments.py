#!/usr/bin/env python3
"""
附件链接修复工具 - 自动为 WizNote 导出的笔记添加附件引用
根据文件名和目录结构匹配笔记与附件的关系
"""
import re
import os
from pathlib import Path
from typing import List, Dict, Tuple
import difflib


class AttachmentLinker:
    """附件链接器"""

    def __init__(self, export_dir: str, vault_dir: str, dry_run: bool = False):
        self.export_dir = Path(export_dir)
        self.vault_dir = Path(vault_dir)
        self.dry_run = dry_run
        self.updated_files = []
        self.total_links = 0

    def find_note_attachments(self, note_path: Path, all_attachments: Dict[str, List[Path]]) -> List[Path]:
        """根据笔记路径找到对应的附件"""
        attachments = []

        # 获取笔记的基本信息
        note_name = note_path.stem  # 不含扩展名的文件名
        note_name_lower = note_name.lower()

        # 收集所有可能的附件
        all_attach_files = []
        for attach_dir, attach_files in all_attachments.items():
            all_attach_files.extend(attach_files)

        # 为每个附件计算匹配度
        attachment_scores = []

        for attach in all_attach_files:
            attach_name = attach.stem
            attach_name_lower = attach_name.lower()

            # 计算相似度分数
            score = 0

            # 1. 完全匹配
            if note_name == attach_name:
                score = 100
            # 2. 包含关系（笔记名包含附件名或反之）
            elif note_name in attach_name or attach_name in note_name:
                score = 80
                # 如果是包含关系，根据长度比例调整分数
                if len(note_name) > 0 and len(attach_name) > 0:
                    overlap = min(len(note_name), len(attach_name))
                    total = max(len(note_name), len(attach_name))
                    score += (overlap / total) * 20
            # 3. 模糊匹配
            else:
                similarity = difflib.SequenceMatcher(None, note_name_lower, attach_name_lower).ratio()
                if similarity > 0.4:
                    score = similarity * 60

            # 4. 检查关键词匹配
            note_words = set(note_name_lower.replace('-', ' ').replace('：', ' ').replace(':', ' ').split())
            attach_words = set(attach_name_lower.replace('-', ' ' ).replace('：', ' ').replace(':', ' ').split())

            common_words = note_words & attach_words
            if common_words:
                # 根据共同词的数量和重要性增加分数
                for word in common_words:
                    if len(word) > 2:  # 忽略短词
                        score += 10

            if score > 40:  # 阈值
                attachment_scores.append((attach, score))

        # 按分数排序，取前几个
        attachment_scores.sort(key=lambda x: x[1], reverse=True)

        # 返回最高分的附件（可能有多个）
        if attachment_scores:
            # 取分数差距不大的附件（最高分的 80% 以上）
            max_score = attachment_scores[0][1]
            for attach, score in attachment_scores:
                if score >= max_score * 0.8:
                    attachments.append(attach)
                else:
                    break

        return attachments

    def add_attachment_links_to_note(self, note_path: Path, vault_attach_dir: Path) -> int:
        """为笔记添加附件链接"""
        try:
            with open(note_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 检查是否已有附件链接
            if 'attachments/' in content or '![](' in content:
                return 0

            # 查找对应附件
            all_attachments = self.collect_all_attachments()
            attachments = self.find_note_attachments(note_path, all_attachments)

            if not attachments:
                return 0

            # 过滤出已迁移到 vault 的附件
            migrated_attachments = []
            for attach in attachments:
                vault_attach = vault_attach_dir / attach.name
                if vault_attach.exists():
                    migrated_attachments.append(vault_attach)

            if not migrated_attachments:
                return 0

            # 构建附件链接部分
            attachment_section = "\n\n## 📎 附件\n\n"

            # 按文件类型排序
            attachment_groups = {}
            for attach in migrated_attachments:
                ext = attach.suffix.lower()
                if ext in ['.pdf']:
                    group = 'PDF 文档'
                elif ext in ['.xmind']:
                    group = '思维导图'
                elif ext in ['.xlsx', '.xls']:
                    group = 'Excel 表格'
                elif ext in ['.pptx', '.ppt']:
                    group = 'PowerPoint'
                elif ext in ['.png', '.jpg', '.jpeg', '.gif']:
                    group = '图片'
                else:
                    group = '其他文件'

                if group not in attachment_groups:
                    attachment_groups[group] = []
                attachment_groups[group].append(attach)

            # 生成链接
            for group_name in sorted(attachment_groups.keys()):
                attachment_section += f"### {group_name}\n\n"
                for attach in attachment_groups[group_name]:
                    rel_path = f"attachments/{attach.name}"
                    file_size = attach.stat().st_size
                    size_str = self.format_size(file_size)
                    attachment_section += f"- [[{rel_path}|{attach.stem}]] ({size_str})\n"
                attachment_section += "\n"

            # 在文件末尾添加（在 --- 之后）
            if content.startswith('---'):
                # 找到 front matter 结束位置
                lines = content.split('\n')
                insert_pos = 0
                for i, line in enumerate(lines[1:], 1):
                    if line.strip() == '---':
                        insert_pos = i + 1
                        break

                if insert_pos > 0:
                    lines.insert(insert_pos, attachment_section)
                    content = '\n'.join(lines)
            else:
                content += attachment_section

            # 写入文件
            if not self.dry_run:
                # 备份
                backup_path = Path(str(note_path) + '.attachlinkbak')
                import shutil
                shutil.copy2(note_path, backup_path)

                # 写入
                with open(note_path, 'w', encoding='utf-8') as f:
                    f.write(content)

            self.total_links += len(migrated_attachments)

            return len(migrated_attachments)

        except Exception as e:
            print(f"⚠️  处理文件 {note_path} 时出错: {e}")
            return 0

    def collect_all_attachments(self) -> Dict[str, List[Path]]:
        """收集所有附件"""
        attachments = {}
        for attach_dir in self.export_dir.rglob("attachments"):
            if attach_dir.is_dir():
                files = [f for f in attach_dir.iterdir() if f.is_file()]
                if files:
                    attachments[str(attach_dir)] = files
        return attachments

    def update_all_notes(self) -> Dict:
        """更新所有笔记"""
        print(f"🔍 扫描笔记文件...")

        vault_attach_dir = self.vault_dir / "attachments"
        if not vault_attach_dir.exists():
            print(f"❌ 附件目录不存在: {vault_attach_dir}")
            return {'total_files': 0, 'updated_files': 0, 'total_links': 0}

        # 查找所有笔记文件
        note_files = list(self.vault_dir.rglob("*.md"))

        # 排除系统文件和已经处理过的文件
        excluded_patterns = ['.attachlinkbak', '附件清单', 'node_modules']
        note_files = [
            f for f in note_files
            if not any(pattern in str(f) for pattern in excluded_patterns)
        ]

        print(f"📝 找到 {len(note_files)} 个笔记文件")
        print(f"📁 附件目录: {vault_attach_dir}")
        print(f"模式: {'🧪 干运行' if self.dry_run else '✅ 实际更新'}\n")

        processed = 0
        for note_path in note_files:
            links_added = self.add_attachment_links_to_note(note_path, vault_attach_dir)

            if links_added > 0:
                self.updated_files.append({
                    'file': str(note_path.relative_to(self.vault_dir)),
                    'links': links_added
                })
                print(f"  ✅ {note_path.relative_to(self.vault_dir)}: 添加 {links_added} 个附件链接")

            processed += 1
            if processed % 100 == 0:
                print(f"  进度: {processed}/{len(note_files)}")

        return {
            'total_files': len(note_files),
            'updated_files': len(self.updated_files),
            'total_links': self.total_links,
            'files_detail': self.updated_files
        }

    @staticmethod
    def format_size(size_bytes: int) -> str:
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"


def main():
    import argparse

    parser = argparse.ArgumentParser(description='附件链接修复工具 - 自动为笔记添加附件引用')
    parser.add_argument('--export-dir', required=True, help='WizNote 导出目录（用于查找附件）')
    parser.add_argument('--vault-dir', required=True, help='Obsidian Vault 目录')
    parser.add_argument('--dry-run', action='store_true', help='干运行模式')

    args = parser.parse_args()

    linker = AttachmentLinker(args.export_dir, args.vault_dir, dry_run=args.dry_run)
    result = linker.update_all_notes()

    print(f"\n{'='*60}")
    print(f"📊 更新完成统计")
    print(f"{'='*60}")
    print(f"扫描文件数: {result['total_files']}")
    print(f"更新文件数: {result['updated_files']}")
    print(f"添加链接数: {result['total_links']}")

    if result['updated_files'] > 0:
        print(f"\n📋 更新文件列表：")
        for item in result['files_detail'][:20]:
            print(f"  - {item['file']}: {item['links']} 个附件")

        if len(result['files_detail']) > 20:
            print(f"  ... 还有 {len(result['files_detail']) - 20} 个文件")

    if not args.dry_run:
        print(f"\n💾 备份文件已保存为 .attachlinkbak 后缀")


if __name__ == '__main__':
    main()
