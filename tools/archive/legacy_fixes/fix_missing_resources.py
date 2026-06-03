#!/usr/bin/env python3
"""
一键修复图片/附件缺失 - 扫描、生成列表、删除文件一站式完成

功能：
  - 扫描所有笔记的图片和附件缺失情况
  - 生成缺失报告
  - 生成重新下载列表
  - 删除有问题的 Markdown 文件
  - 全程只需一个命令

使用方法：
    # 完整流程（推荐）
    python3 tools/fix_missing_resources.py

    # 只扫描，不删除文件
    python3 tools/fix_missing_resources.py --scan-only

    # 只处理严重问题（总缺失 >= 10 个）
    python3 tools/fix_missing_resources.py --severe-only

    # 干运行模式（预览将要删除的文件）
    python3 tools/fix_missing_resources.py --dry-run

输出：
  - missing_resources_report.txt - 详细的缺失报告
  - redownload_list.txt - 重新下载列表
  - deleted_files_log.txt - 删除日志

示例：
    $ python3 tools/fix_missing_resources.py --dry-run

    ======================================================================
    🔧 一键修复图片/附件缺失
    ======================================================================

    📊 Step 1/4: 扫描缺失图片和附件...

    ⚠️  发现 51 个笔记存在图片/附件缺失问题：
    ...

    📋 Step 2/4: 生成重新下载列表...

    ✅ 已生成重新下载列表: redownload_list.txt
       共 51 个笔记需要处理

    🔍 Step 3/4: 预览将要删除的文件（干运行模式）...

    将要删除 51 个 Markdown 文件

    💡 移除 --dry-run 参数以执行删除操作

    📄 详细报告：
       - missing_resources_report.txt
       - redownload_list.txt
"""

import os
import sys
from pathlib import Path
import argparse
import re
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))


def scan_missing_resources(download_dir="wiznote_download"):
    """扫描下载目录，找出图片和附件缺失的笔记"""

    print(f"📊 Step 1/4: 扫描缺失图片和附件...\n")

    download_path = Path(download_dir)
    if not download_path.exists():
        print(f"❌ 下载目录不存在: {download_path}")
        return []

    issues = []

    # 查找所有 Markdown 文件
    for md_file in download_path.rglob("*.md"):
        files_dir = md_file.parent / f"{md_file.stem}_files"

        # 统计 Markdown 中的图片和附件引用
        with open(md_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        # 图片引用
        image_refs = re.findall(r'!\[.*?\]\((.*?)\)', content)
        # 附件引用
        attachment_refs = re.findall(r'\[.*?\]\((.*?\.(pdf|docx|xlsx|zip|rar|7z|pptx|doc|xls|ppt))\)', content, re.IGNORECASE)
        attachment_refs = [ref[0] for ref in attachment_refs]

        if not image_refs and not attachment_refs:
            continue

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
                "md_file": md_file,
                "md_refs": len(image_refs),
                "downloaded": downloaded_images,
                "missing": image_missing,
                "att_refs": len(attachment_refs),
                "att_downloaded": downloaded_attachments,
                "att_missing": attachment_missing,
                "total_missing": image_missing + attachment_missing
            })

    return issues


def generate_reports(issues, output_dir, severe_threshold=10):
    """生成缺失报告和重新下载列表"""

    print(f"\n📋 Step 2/4: 生成重新下载列表...\n")

    output_path = Path(output_dir)

    # 按总缺失数排序
    issues.sort(key=lambda x: x['total_missing'], reverse=True)

    # 1. 生成详细报告
    report_file = output_path / "missing_resources_report.txt"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("="*70 + "\n")
        f.write(f"缺失图片和附件报告\n")
        f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("="*70 + "\n\n")

        f.write(f"{'文件名':<40} {'图片':<12} {'附件':<12} {'总计':<6}\n")
        f.write("-" * 70 + "\n")

        total_image_missing = 0
        total_attachment_missing = 0

        for issue in issues:
            img_info = f"{issue['downloaded']}/{issue['md_refs']}"
            if issue['missing'] > 0:
                img_info += f" ❌{issue['missing']}"

            att_info = f"{issue['att_downloaded']}/{issue['att_refs']}"
            if issue['att_missing'] > 0:
                att_info += f" ❌{issue['att_missing']}"

            f.write(f"{issue['file']:<40} {img_info:<12} {att_info:<12} {issue['total_missing']:<6}\n")

            total_image_missing += issue['missing']
            total_attachment_missing += issue['att_missing']

        f.write("-" * 70 + "\n")

        total_info = f"{'总计':<40} "
        total_info += f"{'缺失 ' + str(total_image_missing):<12} "
        total_info += f"{'缺失 ' + str(total_attachment_missing):<12} "
        total_info += f"{total_image_missing + total_attachment_missing:<6}\n"
        f.write(total_info)

    # 2. 生成重新下载列表
    list_file = output_path / "redownload_list.txt"
    with open(list_file, 'w', encoding='utf-8') as f:
        f.write("需要重新下载的笔记列表\n")
        f.write("="*70 + "\n\n")
        f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"总数: {len(issues)} 个笔记\n")
        f.write(f"图片缺失: {total_image_missing} 张\n")
        f.write(f"附件缺失: {total_attachment_missing} 个\n\n")
        f.write("格式：文件路径 (总缺失数)\n")
        f.write("="*70 + "\n\n")

        for issue in issues:
            f.write(f"{issue['file']} ({issue['total_missing']} 个)\n")

    print(f"✅ 已生成重新下载列表: {list_file}")
    print(f"   共 {len(issues)} 个笔记需要处理")

    severe_count = sum(1 for i in issues if i['total_missing'] >= severe_threshold)
    if severe_count > 0:
        print(f"🚨 其中 {severe_count} 个严重问题（总缺失 ≥{severe_threshold} 个）")

    return report_file, list_file


def delete_markdown_files(issues, download_dir, severe_only=False, severe_threshold=10, dry_run=False, force=False):
    """删除有问题的 Markdown 文件"""

    step_num = "3/4" if not dry_run else "3/4"
    action = "预览将要删除的文件" if dry_run else "删除有问题的 Markdown 文件"
    print(f"\n🔍 Step {step_num}: {action}{'（干运行模式）' if dry_run else ''}...\n")

    # 过滤严重问题
    if severe_only:
        issues = [i for i in issues if i['total_missing'] >= severe_threshold]
        if not issues:
            print("✅ 没有严重问题需要处理")
            return []

    download_path = Path(download_dir)
    md_files_to_delete = [i['md_file'] for i in issues if i['md_file'].exists()]

    if not md_files_to_delete:
        print("✅ 所有有问题的 Markdown 文件都已不存在")
        return []

    # 显示将要删除的文件
    print(f"将要{'删除' if not dry_run else '预览'} {len(md_files_to_delete)} 个 Markdown 文件：\n")

    for i, md_file in enumerate(md_files_to_delete[:20], 1):
        rel_path = md_file.relative_to(download_path)
        print(f"   {i}. {rel_path}")

    if len(md_files_to_delete) > 20:
        print(f"   ... 还有 {len(md_files_to_delete) - 20} 个文件")

    print()

    # 干运行模式
    if dry_run:
        print("🔍 干运行模式 - 不会实际删除文件\n")
        return []

    # 确认删除
    if not force:
        confirm = input(f"\n⚠️  确认删除这 {len(md_files_to_delete)} 个文件？[y/N] ").strip().lower()
        if confirm != 'y':
            print("❌ 操作已取消")
            return []

    # 执行删除
    print(f"\n🗑️  正在删除 {len(md_files_to_delete)} 个 Markdown 文件...\n")

    deleted_count = 0
    failed_count = 0

    for md_file in md_files_to_delete:
        try:
            md_file.unlink()
            deleted_count += 1
            if deleted_count <= 10:
                print(f"   ✅ 已删除: {md_file.relative_to(download_path)}")
        except Exception as e:
            failed_count += 1
            print(f"   ❌ 删除失败: {md_file.relative_to(download_path)} - {str(e)}")

    if deleted_count > 10:
        print(f"   ... 已删除 {deleted_count - 10} 个文件")

    print(f"\n{'='*70}")
    print(f"📊 删除统计")
    print(f"{'='*70}")
    print(f"   ✅ 成功删除: {deleted_count} 个文件")
    if failed_count > 0:
        print(f"   ❌ 删除失败: {failed_count} 个文件")

    # 保存删除日志
    log_file = download_path.parent / "deleted_files_log.txt"
    with open(log_file, 'w', encoding='utf-8') as f:
        f.write("="*70 + "\n")
        f.write("已删除的 Markdown 文件列表\n")
        f.write("="*70 + "\n\n")
        f.write(f"删除时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"删除总数: {deleted_count}\n\n")

        for md_file in md_files_to_delete:
            f.write(f"{md_file.relative_to(download_path)}\n")

    print(f"\n📄 删除日志已保存到: {log_file}")

    return md_files_to_delete


def main():
    parser = argparse.ArgumentParser(
        description="一键修复图片/附件缺失 - 扫描、生成列表、删除文件一站式完成",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 完整流程（推荐）
  python3 tools/fix_missing_resources.py

  # 只扫描，不删除文件
  python3 tools/fix_missing_resources.py --scan-only

  # 只处理严重问题
  python3 tools/fix_missing_resources.py --severe-only

  # 干运行模式（预览将要删除的文件）
  python3 tools/fix_missing_resources.py --dry-run

  # 强制执行（不询问确认）
  python3 tools/fix_missing_resources.py --force

输出文件:
  missing_resources_report.txt - 详细的缺失报告
  redownload_list.txt - 重新下载列表
  deleted_files_log.txt - 删除日志

下一步:
  运行 python3 tools/wiznote_downloader.py 重新下载
        """
    )

    parser.add_argument(
        '--download-dir', '-d',
        default='wiznote_download',
        help='下载目录路径（默认: wiznote_download）'
    )

    parser.add_argument(
        '--scan-only',
        action='store_true',
        help='只扫描，不删除文件'
    )

    parser.add_argument(
        '--severe-only', '-s',
        action='store_true',
        help='只处理严重问题（总缺失 >= 10 个）'
    )

    parser.add_argument(
        '--severe-threshold', '-t',
        type=int,
        default=10,
        help='严重问题的总缺失数阈值（默认: 10）'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='干运行模式（只预览，不实际删除）'
    )

    parser.add_argument(
        '--force', '-f',
        action='store_true',
        help='强制执行（不询问确认）'
    )

    args = parser.parse_args()

    print("="*70)
    print("🔧 一键修复图片/附件缺失")
    print("="*70)
    print()

    # Step 1: 扫描
    issues = scan_missing_resources(args.download_dir)

    if not issues:
        print("\n✅ 所有图片和附件都已正确下载！")
        return

    # 显示扫描结果
    print(f"\n⚠️  发现 {len(issues)} 个笔记存在图片/附件缺失问题：\n")
    print(f"{'文件名':<40} {'图片':<12} {'附件':<12} {'总计':<6}")
    print("-" * 70)

    total_image_missing = 0
    total_attachment_missing = 0

    for issue in issues[:20]:
        img_info = f"{issue['downloaded']}/{issue['md_refs']}"
        if issue['missing'] > 0:
            img_info += f" ❌{issue['missing']}"

        att_info = f"{issue['att_downloaded']}/{issue['att_refs']}"
        if issue['att_missing'] > 0:
            att_info += f" ❌{issue['att_missing']}"

        print(f"{issue['file'][:38]:<40} {img_info:<12} {att_info:<12} {issue['total_missing']:<6}")

        total_image_missing += issue['missing']
        total_attachment_missing += issue['att_missing']

    if len(issues) > 20:
        print(f"   ... 还有 {len(issues) - 20} 个笔记")

    print("-" * 70)
    total_info = f"{'总计':<40} "
    total_info += f"{'缺失 ' + str(total_image_missing):<12} "
    total_info += f"{'缺失 ' + str(total_attachment_missing):<12} "
    total_info += f"{total_image_missing + total_attachment_missing:<6}"
    print(total_info)

    # Step 2: 生成报告
    report_file, list_file = generate_reports(issues, Path(args.download_dir).parent, args.severe_threshold)

    # 如果只扫描，到此结束
    if args.scan_only:
        print(f"\n📄 详细报告：")
        print(f"   - {report_file}")
        print(f"   - {list_file}")
        print(f"\n💡 移除 --scan-only 参数以删除有问题的文件")
        return

    # Step 3: 删除文件
    deleted_files = delete_markdown_files(
        issues,
        args.download_dir,
        args.severe_only,
        args.severe_threshold,
        args.dry_run,
        args.force
    )

    # Step 4: 下一步提示
    print(f"\n{'='*70}")
    print(f"💡 Step 4/4: 下一步")
    print(f"{'='*70}")
    print(f"\n1. 运行在线下载工具重新下载这些笔记：")
    print(f"   python3 tools/wiznote_downloader.py\n")

    print(f"2. 或使用极速模式（如果网络好）：")
    print(f"   python3 tools/wiznote_downloader.py --workers 10 --timeout 20\n")

    if deleted_files:
        print(f"3. wiznote_downloader.py 会自动跳过已存在的笔记")
        print(f"   您删除的 {len(deleted_files)} 个笔记将被重新下载\n")

    print(f"📄 详细报告：")
    print(f"   - {report_file}")
    print(f"   - {list_file}")


if __name__ == "__main__":
    main()
