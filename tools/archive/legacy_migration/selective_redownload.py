#!/usr/bin/env python3
"""
选择性重新下载工具 - 只下载图片缺失的笔记

功能：
  - 读取 redownload_list.txt 或 missing_images_report.txt
  - 删除目标笔记的 Markdown 文件（触发重新下载）
  - 调用 wiznote_downloader.py 重新下载
  - 生成下载报告

使用方法：
    # 基本用法（使用默认列表）
    python3 tools/selective_redownload.py

    # 指定列表文件
    python3 tools/selective_redownload.py --list redownload_list.txt

    # 只处理严重问题（缺失 >= 10 张图片）
    python3 tools/selective_redownload.py --severe-only

    # 干运行模式（只显示将要删除的文件）
    python3 tools/selective_redownload.py --dry-run

    # 强制重新下载（不询问确认）
    python3 tools/selective_redownload.py --force

输出：
  - 删除的 Markdown 文件列表
  - 重新下载的笔记统计
  - 下载结果报告

示例：
    $ python3 tools/selective_redownload.py --dry-run

    ======================================================================
    🔄 选择性重新下载工具
    ======================================================================

    📋 将要删除以下 50 个笔记的 Markdown 文件：

       1. 技术笔记/产品经理PM/智能制造MES拆解.md
       2. 技术笔记/产品经理PM/人人都是开发者——无代码产品...

    ⚠️  这将触发这些笔记的重新下载

    💡 移除 --dry-run 参数以执行删除操作
"""

import os
import sys
from pathlib import Path
import argparse
import re

sys.path.insert(0, str(Path(__file__).parent))


def parse_redownload_list(list_file):
    """解析重新下载列表文件

    Args:
        list_file: 列表文件路径

    Returns:
        list: 笔记路径列表
    """
    notes = []

    with open(list_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    for line in lines:
        line = line.strip()

        # 跳过空行和注释
        if not line or line.startswith('#') or line.startswith('='):
            continue

        # 提取文件路径（移除数量）
        # 格式1：技术笔记/产品经理PM/智能制造MES拆解.md (36 个)
        # 格式2：技术笔记/产品经理PM/智能制造MES拆解.md (36 张)
        match = re.match(r'^(.+?)\s*\(\d+\s*(?:个|张)\)$', line)
        if match:
            notes.append(match.group(1))
        elif line.endswith('.md'):
            notes.append(line)

    return notes


def main():
    parser = argparse.ArgumentParser(
        description="选择性重新下载工具 - 只下载图片缺失的笔记",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 干运行模式（预览将要删除的文件）
  python3 tools/selective_redownload.py --dry-run

  # 执行删除并重新下载
  python3 tools/selective_redownload.py

  # 只处理严重问题
  python3 tools/selective_redownload.py --severe-only

  # 强制执行（不询问确认）
  python3 tools/selective_redownload.py --force

注意事项:
  - 此工具会删除目标笔记的 Markdown 文件
  - wiznote_downloader.py 会自动重新下载这些笔记
  - 建议先使用 --dry-run 预览操作
        """
    )

    parser.add_argument(
        '--list', '-l',
        default='redownload_list.txt',
        help='重新下载列表文件（默认: redownload_list.txt）'
    )

    parser.add_argument(
        '--download-dir', '-d',
        default='wiznote_download',
        help='下载目录（默认: wiznote_download）'
    )

    parser.add_argument(
        '--severe-only', '-s',
        action='store_true',
        help='只处理严重问题（缺失 >= 10 张图片）'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='干运行模式（只显示将要删除的文件，不实际删除）'
    )

    parser.add_argument(
        '--force', '-f',
        action='store_true',
        help='强制执行（不询问确认）'
    )

    args = parser.parse_args()

    print("="*70)
    print("🔄 选择性重新下载工具")
    print("="*70)
    print()

    # 检查列表文件
    list_file = Path(args.list)
    if not list_file.exists():
        print(f"❌ 未找到重新下载列表: {list_file}")
        print(f"💡 请先运行: python3 tools/generate_redownload_list.py")
        return

    # 解析列表
    notes = parse_redownload_list(list_file)

    if not notes:
        print("❌ 列表文件为空或格式不正确")
        return

    # 过滤严重问题
    if args.severe_only:
        # 从原始报告中过滤
        report_file = Path('missing_images_report.txt')
        if report_file.exists():
            with open(report_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            severe_notes = set()
            for line in lines:
                parts = line.strip().split()
                if len(parts) >= 4:
                    try:
                        missing = int(parts[-1])
                        if missing >= 10:
                            severe_notes.add(parts[0])
                    except ValueError:
                        continue

            notes = [n for n in notes if any(sn in n for sn in severe_notes)]

            if not notes:
                print("✅ 没有严重问题（所有缺失图片 < 10 张）")
                return

    print(f"📋 将要处理 {len(notes)} 个笔记：\n")

    # 查找对应的 Markdown 文件
    download_dir = Path(args.download_dir)
    md_files_to_delete = []

    for note_path in notes:
        md_file = download_dir / note_path
        if md_file.exists():
            md_files_to_delete.append(md_file)

    if not md_files_to_delete:
        print("✅ 所有笔记的 Markdown 文件都已不存在")
        print("💡 直接运行 wiznote_downloader.py 即可重新下载")
        return

    # 显示将要删除的文件
    print(f"将要删除 {len(md_files_to_delete)} 个 Markdown 文件：\n")

    for i, md_file in enumerate(md_files_to_delete[:20], 1):
        rel_path = md_file.relative_to(download_dir)
        print(f"   {i}. {rel_path}")

    if len(md_files_to_delete) > 20:
        print(f"   ... 还有 {len(md_files_to_delete) - 20} 个文件")

    print()

    # 干运行模式
    if args.dry_run:
        print("🔍 干运行模式 - 不会实际删除文件\n")
        print("💡 移除 --dry-run 参数以执行删除操作")
        print("💡 删除后运行 wiznote_downloader.py 重新下载")
        return

    # 确认删除
    if not args.force:
        confirm = input(f"\n⚠️  确认删除这 {len(md_files_to_delete)} 个文件？[y/N] ").strip().lower()
        if confirm != 'y':
            print("❌ 操作已取消")
            return

    # 执行删除
    print(f"\n🗑️  正在删除 {len(md_files_to_delete)} 个 Markdown 文件...\n")

    deleted_count = 0
    failed_count = 0

    for md_file in md_files_to_delete:
        try:
            md_file.unlink()
            deleted_count += 1
            if deleted_count <= 10:
                print(f"   ✅ 已删除: {md_file.relative_to(download_dir)}")
        except Exception as e:
            failed_count += 1
            print(f"   ❌ 删除失败: {md_file.relative_to(download_dir)} - {str(e)}")

    if deleted_count > 10:
        print(f"   ... 已删除 {deleted_count - 10} 个文件")

    print(f"\n{'='*70}")
    print(f"📊 删除统计")
    print(f"{'='*70}")
    print(f"   ✅ 成功删除: {deleted_count} 个文件")
    if failed_count > 0:
        print(f"   ❌ 删除失败: {failed_count} 个文件")

    print(f"\n{'='*70}")
    print(f"💡 下一步")
    print(f"{'='*70}")
    print(f"\n1. 运行在线下载工具重新下载这些笔记：")
    print(f"   python3 tools/wiznote_downloader.py\n")

    print(f"2. 或使用极速模式（如果网络好）：")
    print(f"   python3 tools/wiznote_downloader.py --workers 10 --timeout 20\n")

    print(f"3. wiznote_downloader.py 会自动跳过已存在的笔记")
    print(f"   您删除的 {deleted_count} 个笔记将被重新下载\n")

    # 保存删除日志
    log_file = download_dir.parent / "deleted_files_log.txt"
    with open(log_file, 'w', encoding='utf-8') as f:
        f.write("="*70 + "\n")
        f.write("已删除的 Markdown 文件列表\n")
        f.write("="*70 + "\n\n")
        f.write(f"删除时间: {Path(__file__).stat().st_mtime}\n")
        f.write(f"删除总数: {deleted_count}\n\n")

        for md_file in md_files_to_delete:
            f.write(f"{md_file.relative_to(download_dir)}\n")

    print(f"📄 删除日志已保存到: {log_file}")


if __name__ == "__main__":
    main()
