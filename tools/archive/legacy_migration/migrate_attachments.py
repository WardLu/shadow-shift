#!/usr/bin/env python3
"""
附件迁移工具 - 将 WizNote 导出的附件迁移到 Obsidian Vault
"""
import os
import shutil
from pathlib import Path
from typing import Dict, List
import json


class AttachmentMigrator:
    """附件迁移器"""

    def __init__(self, export_dir: str, vault_dir: str, dry_run: bool = False):
        self.export_dir = Path(export_dir)
        self.vault_dir = Path(vault_dir)
        self.dry_run = dry_run
        self.migrated_files = []
        self.total_size = 0

    def find_all_attachments(self) -> Dict[str, List[Path]]:
        """找到所有附件目录及其文件（包括 attachments 和 _files 目录）"""
        attachments = {}

        # 查找 attachments 目录
        for attach_dir in self.export_dir.rglob("attachments"):
            if attach_dir.is_dir():
                files = list(attach_dir.glob("*"))
                files = [f for f in files if f.is_file()]
                if files:
                    attachments[str(attach_dir)] = files

        # 查找 _files 目录（WizNote 下载的图片和附件）
        for files_dir in self.export_dir.rglob("*_files"):
            if files_dir.is_dir():
                files = list(files_dir.glob("*"))
                files = [f for f in files if f.is_file()]
                if files:
                    attachments[str(files_dir)] = files

        return attachments

    def get_vault_attachments_dir(self) -> Path:
        """获取 Vault 中的附件目录"""
        attach_dir = self.vault_dir / "attachments"
        attach_dir.mkdir(parents=True, exist_ok=True)
        return attach_dir

    def migrate_attachments(self) -> Dict:
        """迁移所有附件"""
        print(f"🔍 扫描附件目录...")
        attachments = self.find_all_attachments()

        if not attachments:
            print("❌ 没有找到任何附件")
            return {'total_dirs': 0, 'total_files': 0, 'total_size': 0, 'files': []}

        vault_attach_dir = self.get_vault_attachments_dir()

        print(f"📦 找到 {len(attachments)} 个附件目录")
        print(f"📁 目标目录: {vault_attach_dir}")
        print(f"模式: {'🧪 干运行' if self.dry_run else '✅ 实际迁移'}\n")

        # 计算总文件数
        total_files = sum(len(files) for files in attachments.values())
        print(f"PROGRESS_START:{total_files}")

        current_file = 0
        for source_dir, files in attachments.items():
            print(f"\n📂 处理目录: {Path(source_dir).relative_to(self.export_dir)}")

            for file_path in files:
                try:
                    current_file += 1
                    percent = int((current_file / total_files) * 100) if total_files > 0 else 0

                    # 标准进度输出格式
                    print(f"PROGRESS:{current_file}:{total_files}:{percent}")

                    file_size = file_path.stat().st_size

                    # 复制文件到 Vault
                    dest_path = vault_attach_dir / file_path.name

                    # 处理同名文件
                    if dest_path.exists():
                        base_name = file_path.stem
                        suffix = file_path.suffix
                        counter = 1
                        while dest_path.exists():
                            new_name = f"{base_name}_{counter}{suffix}"
                            dest_path = vault_attach_dir / new_name
                            counter += 1

                    if not self.dry_run:
                        shutil.copy2(file_path, dest_path)

                    self.migrated_files.append({
                        'source': str(file_path.relative_to(self.export_dir)),
                        'dest': f"attachments/{dest_path.name}",
                        'size': file_size
                    })

                    self.total_size += file_size

                    print(f"  ✅ {file_path.name} ({self.format_size(file_size)})")

                except Exception as e:
                    print(f"  ❌ {file_path.name}: {e}")

        return {
            'total_dirs': len(attachments),
            'total_files': len(self.migrated_files),
            'total_size': self.total_size,
            'files': self.migrated_files
        }

    @staticmethod
    def format_size(size_bytes: int) -> str:
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"

    def generate_attachment_list(self) -> str:
        """生成附件清单文件"""
        vault_attach_dir = self.get_vault_attachments_dir()
        list_file = vault_attach_dir / "附件清单.md"

        content = f"# WizNote 附件清单\n\n"
        content += f"## 📊 统计信息\n\n"
        content += f"- **总文件数**: {len(self.migrated_files)}\n"
        content += f"- **总大小**: {self.format_size(self.total_size)}\n"
        content += f"- **迁移时间**: {self.get_current_time()}\n\n"
        content += f"## 📋 文件列表\n\n"

        for item in self.migrated_files:
            content += f"### {item['dest']}\n"
            content += f"- **原始路径**: `{item['source']}`\n"
            content += f"- **大小**: {self.format_size(item['size'])}\n\n"

        if not self.dry_run:
            with open(list_file, 'w', encoding='utf-8') as f:
                f.write(content)

        return str(list_file)

    @staticmethod
    def get_current_time() -> str:
        """获取当前时间"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def main():
    import argparse

    parser = argparse.ArgumentParser(description='附件迁移工具')
    parser.add_argument('--export-dir', required=True, help='WizNote 导出目录')
    parser.add_argument('--vault-dir', required=True, help='Obsidian Vault 目录')
    parser.add_argument('--dry-run', action='store_true', help='干运行模式')

    args = parser.parse_args()

    migrator = AttachmentMigrator(args.export_dir, args.vault_dir, dry_run=args.dry_run)
    result = migrator.migrate_attachments()

    print(f"\n{'='*60}")
    print(f"📊 迁移完成统计")
    print(f"{'='*60}")
    print(f"附件目录数: {result['total_dirs']}")
    print(f"迁移文件数: {result['total_files']}")
    print(f"总大小: {AttachmentMigrator.format_size(result['total_size'])}")

    if result['total_files'] > 0:
        list_file = migrator.generate_attachment_list()
        print(f"\n📄 附件清单: {list_file}")

        print(f"\n💡 使用提示:")
        print(f"  附件已复制到: attachments/")
        print(f"  在 Obsidian 中可以用 [[attachments/文件名]] 引用")


if __name__ == '__main__':
    main()
