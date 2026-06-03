#!/usr/bin/env python3
"""
从本地文件提取图片 URL - 不需要重新登录

功能：
  - 读取已有的 Markdown 文件
  - 提取图片引用 URL
  - 生成下载脚本
  - 可选择直接下载

使用方法：
    # 提取所有缺失图片的 URL
    python3 tools/extract_image_urls.py

    # 生成下载脚本（推荐）
    python3 tools/extract_image_urls.py --generate-script

    # 直接下载图片（需要登录）
    python3 tools/extract_image_urls.py --download
"""

import re
import sys
from pathlib import Path
from urllib.parse import urlparse
import argparse


def extract_image_urls_from_markdown(md_file, download_dir):
    """从 Markdown 文件中提取图片 URL"""

    with open(md_file, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    # 提取图片引用 ![alt](url)
    image_refs = re.findall(r'!\[.*?\]\((.*?)\)', content)

    # 过滤并分类
    image_urls = []

    for ref in image_refs:
        # 跳过本地相对路径（已下载的）
        if ref.startswith('./') or ref.startswith('../'):
            continue

        # 跳过 _files 文件夹的引用（已下载的）
        if '_files/' in ref:
            continue

        # 跳过 WikiLinks
        if ref.startswith('[[') and ref.endswith(']]'):
            continue

        # 跳过空引用
        if not ref or ref == '#':
            continue

        # 判断 URL 类型
        if ref.startswith('http://') or ref.startswith('https://'):
            # 绝对 URL
            image_urls.append(ref)
        elif ref.startswith('index_files/'):
            # WizNote 相对路径，需要转换为 API URL
            # 但我们不知道 GUID，所以暂时跳过
            continue
        else:
            # 可能是为知笔记的资源 ID
            # 例如：vntukkXSi8zYDUr3w8-EJIRRh68mA9rtZ-cAbLAcBh0.png
            if re.match(r'^[a-zA-Z0-9_-]+\.(png|jpg|jpeg|gif|webp)$', ref):
                image_urls.append(ref)

    return image_urls


def main():
    parser = argparse.ArgumentParser(
        description="从本地文件提取图片 URL - 不需要重新登录"
    )

    parser.add_argument(
        '--download-dir', '-d',
        default='wiznote_download',
        help='下载目录（默认: wiznote_download）'
    )

    parser.add_argument(
        '--missing-list',
        default='missing_resources_report.txt',
        help='缺失资源报告文件（默认: missing_resources_report.txt）'
    )

    parser.add_argument(
        '--generate-script',
        action='store_true',
        help='生成 wget 下载脚本'
    )

    parser.add_argument(
        '--download',
        action='store_true',
        help='直接下载图片（需要登录）'
    )

    args = parser.parse_args()

    print("="*70)
    print("🖼️  从本地文件提取图片 URL")
    print("="*70)
    print()

    # 检查缺失资源报告
    missing_file = Path(args.missing_list)
    if not missing_file.exists():
        print("❌ 未找到缺失资源报告")
        print("💡 请先运行: python3 tools/fix_missing_resources.py --scan-only")
        return

    # 解析缺失列表
    print("📋 解析缺失资源报告...")
    missing_notes = []

    with open(missing_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    for line in lines:
        parts = line.strip().split()
        if len(parts) >= 4:
            file_path = parts[0]
            if file_path.endswith('.md'):
                missing_notes.append(file_path)

    print(f"✅ 找到 {len(missing_notes)} 个缺失图片的笔记\n")

    # 提取图片 URL
    print("🔍 提取图片 URL...")
    download_dir = Path(args.download_dir)

    all_image_urls = []
    notes_with_urls = []

    for i, note_path in enumerate(missing_notes, 1):
        md_file = download_dir / note_path

        if not md_file.exists():
            print(f"   [{i}/{len(missing_notes)}] ⚠️  文件不存在: {note_path}")
            continue

        image_urls = extract_image_urls_from_markdown(md_file, download_dir)

        if image_urls:
            notes_with_urls.append({
                'note': note_path,
                'urls': image_urls,
                'count': len(image_urls)
            })
            all_image_urls.extend(image_urls)
            print(f"   [{i}/{len(missing_notes)}] ✅ {note_path}: {len(image_urls)} 个 URL")
        else:
            print(f"   [{i}/{len(missing_notes)}] ℹ️  {note_path}: 未找到外部 URL")

    # 统计
    print(f"\n{'='*70}")
    print(f"📊 统计信息")
    print(f"{'='*70}\n")

    print(f"检查笔记: {len(missing_notes)} 个")
    print(f"有外部 URL 的笔记: {len(notes_with_urls)} 个")
    print(f"提取的图片 URL 总数: {len(all_image_urls)} 个\n")

    if not all_image_urls:
        print("ℹ️  未找到外部图片 URL")
        print("   所有图片可能都引用自 WizNote 内部资源，需要通过 API 下载\n")
        return

    # 显示 URL 示例
    print(f"图片 URL 示例（前 5 个）：")
    unique_urls = list(set(all_image_urls))
    for url in unique_urls[:5]:
        print(f"   - {url}")

    if len(unique_urls) > 5:
        print(f"   ... 还有 {len(unique_urls) - 5} 个 URL\n")

    # 生成下载脚本
    if args.generate_script or True:  # 默认生成
        print(f"\n📝 生成下载脚本...")

        script_file = 'download_images.sh'
        with open(script_file, 'w', encoding='utf-8') as f:
            f.write("#!/bin/bash\n\n")
            f.write("# 从 WizNote 下载缺失的图片\n\n")
            f.write(f"# 总共 {len(unique_urls)} 个图片 URL\n\n")

            for i, url in enumerate(unique_urls, 1):
                # 提取文件名
                if url.startswith('http'):
                    parsed = urlparse(url)
                    filename = Path(parsed.path).name
                else:
                    filename = url

                f.write(f"# {i}/{len(unique_urls)}\n")
                f.write(f"curl -L -o 'downloaded_images/{filename}' '{url}'\n\n")

        print(f"✅ 下载脚本已生成: {script_file}")
        print(f"\n💡 使用方法：")
        print(f"   mkdir downloaded_images")
        print(f"   chmod +x {script_file}")
        print(f"   ./{script_file}\n")

    # 保存 URL 列表
    url_list_file = 'image_urls.txt'
    with open(url_list_file, 'w', encoding='utf-8') as f:
        for url in unique_urls:
            f.write(f"{url}\n")

    print(f"📄 URL 列表已保存: {url_list_file}\n")

    # 生成详细报告
    report_file = 'image_url_report.md'
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("# 图片 URL 提取报告\n\n")
        f.write(f"> 生成时间: {Path(__file__).stat().st_mtime}\n\n")
        f.write("---\n\n")

        f.write("## 统计信息\n\n")
        f.write(f"- 检查笔记: {len(missing_notes)} 个\n")
        f.write(f"- 有外部 URL 的笔记: {len(notes_with_urls)} 个\n")
        f.write(f"- 提取的图片 URL 总数: {len(all_image_urls)} 个\n")
        f.write(f"- 去重后的 URL 数: {len(unique_urls)} 个\n\n")

        f.write("---\n\n")

        f.write("## 笔记详情\n\n")
        for note_info in notes_with_urls:
            f.write(f"### {note_info['note']}\n\n")
            f.write(f"图片数量: {note_info['count']}\n\n")
            for url in note_info['urls'][:5]:
                f.write(f"- {url}\n")
            if note_info['count'] > 5:
                f.write(f"- ... 还有 {note_info['count'] - 5} 个\n")
            f.write("\n")

    print(f"📄 详细报告已生成: {report_file}\n")

    # 如果指定了 --download
    if args.download:
        print("⚠️  直接下载功能需要重新登录")
        print("   建议使用生成的下载脚本\n")


if __name__ == "__main__":
    main()
