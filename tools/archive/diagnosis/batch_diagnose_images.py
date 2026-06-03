#!/usr/bin/env python3
"""
批量图片下载诊断工具 - 扫描所有缺失图片的笔记

功能：
  - 扫描 wiznote_download 目录下的所有 Markdown 文件
  - 检查每个笔记的图片引用与实际下载的图片数量
  - 生成详细的缺失图片报告（Markdown 格式）
  - 按严重程度分类（完全缺失 vs 部分缺失）

使用方法：
    # 基本用法（扫描默认目录）
    python3 tools/batch_diagnose_images.py

    # 指定下载目录
    python3 tools/batch_diagnose_images.py --download-dir ~/my_wiznote

    # 只显示严重问题（缺失 >= 10 张图片）
    python3 tools/batch_diagnose_images.py --severe-only

输出：
  - 控制台：实时显示扫描进度和结果
  - missing_images_report.md：详细的缺失图片报告（Markdown 格式）

示例：
    $ python3 tools/batch_diagnose_images.py

    ======================================================================
    🔍 批量图片下载诊断工具
    ======================================================================

    ⚠️  发现 50 个笔记存在图片缺失问题：

    文件名                                                引用     下载     缺失
    ----------------------------------------------------------------------
    技术笔记/产品经理PM/智能制造MES拆解.md                36     0      36
    ...

    📄 详细报告已保存到: missing_images_report.md
"""

import os
import sys
from pathlib import Path
import getpass
import argparse

sys.path.insert(0, str(Path(__file__).parent))

from wiznote_downloader import WizMigrator


def scan_missing_images(download_dir="wiznote_download"):
    """扫描下载目录，找出图片和附件缺失的笔记

    Args:
        download_dir: 下载目录路径（默认: wiznote_download）

    Returns:
        list: 缺失图片/附件的笔记列表，每个元素包含:
            - file: 文件相对路径
            - md_refs: Markdown 中的图片引用数
            - downloaded: 实际下载的图片数
            - missing: 缺失的图片数
            - att_refs: Markdown 中的附件引用数
            - att_downloaded: 实际下载的附件数
            - att_missing: 缺失的附件数
            - total_missing: 总缺失数（图片+附件）
    """

    print(f"\n{'='*70}")
    print(f"🔍 扫描缺失图片和附件的笔记")
    print(f"{'='*70}\n")

    download_path = Path(download_dir)
    if not download_path.exists():
        print(f"❌ 下载目录不存在: {download_path}")
        return []

    issues = []

    # 查找所有 Markdown 文件
    for md_file in download_path.rglob("*.md"):
        # 检查是否有对应的 _files 文件夹
        files_dir = md_file.parent / f"{md_file.stem}_files"

        # 统计 Markdown 中的图片和附件引用
        with open(md_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        import re
        # 图片引用
        image_refs = re.findall(r'!\[.*?\]\((.*?)\)', content)
        # 附件引用（PDF, DOCX, XLSX, ZIP 等）
        attachment_refs = re.findall(r'\[.*?\]\((.*?\.(pdf|docx|xlsx|zip|rar|7z|pptx|doc|xls|ppt))\)', content, re.IGNORECASE)
        attachment_refs = [ref[0] for ref in attachment_refs]

        if not image_refs and not attachment_refs:
            continue  # 没有图片和附件的笔记跳过

        # 统计实际下载的图片数量
        if files_dir.exists():
            image_exts = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg'}
            downloaded_images = sum(1 for f in files_dir.rglob('*') if f.suffix.lower() in image_exts and f.is_file())

            # 统计实际下载的附件数量
            attachment_exts = {'.pdf', '.docx', '.xlsx', '.zip', '.rar', '.7z', '.pptx', '.doc', '.xls', '.ppt'}
            downloaded_attachments = sum(1 for f in files_dir.rglob('*') if f.suffix.lower() in attachment_exts and f.is_file())
        else:
            downloaded_images = 0
            downloaded_attachments = 0

        # 计算缺失数量
        image_missing = len(image_refs) - downloaded_images
        attachment_missing = len(attachment_refs) - downloaded_attachments

        # 如果有任何缺失，记录问题
        if image_missing > 0 or attachment_missing > 0:
            rel_path = md_file.relative_to(download_path)
            issues.append({
                "file": str(rel_path),
                "md_refs": len(image_refs),
                "downloaded": downloaded_images,
                "missing": image_missing,
                "att_refs": len(attachment_refs),
                "att_downloaded": downloaded_attachments,
                "att_missing": attachment_missing,
                "total_missing": image_missing + attachment_missing
            })

    return issues


def main():
    parser = argparse.ArgumentParser(
        description="批量图片下载诊断工具 - 扫描所有缺失图片的笔记",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 基本用法
  python3 tools/batch_diagnose_images.py

  # 指定下载目录
  python3 tools/batch_diagnose_images.py --download-dir ~/my_wiznote

  # 只显示严重问题
  python3 tools/batch_diagnose_images.py --severe-only

输出文件:
  missing_images_report.md - 详细的缺失图片报告（Markdown 格式）
        """
    )

    parser.add_argument(
        '--download-dir', '-d',
        default='wiznote_download',
        help='下载目录路径（默认: wiznote_download）'
    )

    parser.add_argument(
        '--severe-only', '-s',
        action='store_true',
        help='只显示严重问题（缺失 >= 10 张图片）'
    )

    args = parser.parse_args()

    print("="*70)
    print("🔍 批量图片下载诊断工具")
    print("="*70)

    # 扫描缺失图片
    issues = scan_missing_images(args.download_dir)

    if not issues:
        print("\n✅ 所有图片都已正确下载！")
        return

    # 过滤严重问题
    if args.severe_only:
        issues = [i for i in issues if i['total_missing'] >= 10]
        if not issues:
            print("\n✅ 没有发现严重问题（所有缺失 < 10）")
            return
        print(f"\n⚠️  发现 {len(issues)} 个严重问题（总缺失 >= 10）：\n")
    else:
        print(f"\n⚠️  发现 {len(issues)} 个笔记存在图片/附件缺失问题：\n")

    print(f"{'文件名':<40} {'图片':<12} {'附件':<12} {'总计':<6}")
    print("-" * 70)

    total_image_missing = 0
    total_attachment_missing = 0

    for issue in issues:
        img_info = f"{issue['downloaded']}/{issue['md_refs']}"
        if issue['missing'] > 0:
            img_info += f" ❌{issue['missing']}"

        att_info = f"{issue['att_downloaded']}/{issue['att_refs']}"
        if issue['att_missing'] > 0:
            att_info += f" ❌{issue['att_missing']}"

        print(f"{issue['file'][:38]:<40} {img_info:<12} {att_info:<12} {issue['total_missing']:<6}")

        total_image_missing += issue['missing']
        total_attachment_missing += issue['att_missing']

    print("-" * 70)

    total_info = f"{'总计':<40} "
    total_info += f"{'缺失 ' + str(total_image_missing):<12} "
    total_info += f"{'缺失 ' + str(total_attachment_missing):<12} "
    total_info += f"{total_image_missing + total_attachment_missing:<6}"
    print(total_info)

    print(f"\n{'='*70}")
    print(f"💡 解决方案")
    print(f"{'='*70}\n")

    print("1. 重新下载笔记（推荐）")
    print("   - 在 WizNote 客户端中导出笔记到本地")
    print("   - 使用离线导出功能重新下载\n")

    print("2. 手动下载缺失的图片")
    print("   - 登录 WizNote 网页版")
    print("   - 找到对应的笔记")
    print("   - 手动保存图片到对应的 _files 文件夹\n")

    print("3. 使用诊断工具逐个排查")
    print("   - 运行: python3 tools/diagnose_image_download.py")
    print("   - 输入笔记标题进行详细诊断\n")

    # 保存报告（Markdown 格式）
    report_file = Path(args.download_dir).parent / "missing_images_report.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("# 缺失图片和附件报告\n\n")

        f.write(f"**生成时间**: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        f.write("## 📊 统计概览\n\n")
        f.write(f"- **问题笔记数**: {len(issues)} 个\n")
        f.write(f"- **缺失图片**: {total_image_missing} 张\n")
        f.write(f"- **缺失附件**: {total_attachment_missing} 个\n")
        f.write(f"- **总缺失数**: {total_image_missing + total_attachment_missing} 个\n\n")

        f.write("## 📋 详细列表\n\n")
        f.write("| 文件名 | 图片（已下载/引用） | 附件（已下载/引用） | 总缺失 |\n")
        f.write("|--------|---------------------|---------------------|--------|\n")

        for issue in issues:
            # 图片信息
            img_info = f"{issue['downloaded']}/{issue['md_refs']}"
            if issue['missing'] > 0:
                img_info += f" ❌{issue['missing']}"

            # 附件信息
            att_info = f"{issue['att_downloaded']}/{issue['att_refs']}"
            if issue['att_missing'] > 0:
                att_info += f" ❌{issue['att_missing']}"

            # 文件名（转义 Markdown 特殊字符）
            file_name = issue['file'].replace('|', '\\|')

            f.write(f"| {file_name} | {img_info} | {att_info} | {issue['total_missing']} |\n")

        f.write("\n## 💡 解决方案\n\n")
        f.write("### 方案 1：重新下载笔记（推荐）\n\n")
        f.write("1. 在 WizNote 客户端中导出笔记到本地\n")
        f.write("2. 使用离线导出功能重新下载\n\n")

        f.write("### 方案 2：手动下载缺失的图片/附件\n\n")
        f.write("1. 登录 WizNote 网页版\n")
        f.write("2. 找到对应的笔记\n")
        f.write("3. 手动保存图片/附件到对应的 `_files` 文件夹\n\n")

        f.write("### 方案 3：使用诊断工具逐个排查\n\n")
        f.write("```bash\n")
        f.write("python3 tools/diagnose_image_download.py --note \"笔记标题\"\n")
        f.write("```\n\n")

        f.write("---\n\n")
        f.write("*本报告由 `batch_diagnose_images.py` 自动生成*\n")

    print(f"📄 详细报告已保存到: {report_file}")


if __name__ == "__main__":
    main()
