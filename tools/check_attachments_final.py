#!/usr/bin/env python3
"""
最终版：检查 Obsidian 笔记的图片和附件完整性
只检查目标笔记本身，不依赖源笔记
"""
import os
import re
import argparse
from pathlib import Path
from collections import defaultdict

OBSIDIAN_DIR = None
OUTPUT_REPORT = None

def check_file_exists(filename, md_file_path, base_dir):
    """检查引用的文件是否存在（支持多种目录命名规则 + 全局搜索）"""
    md_dir = os.path.dirname(md_file_path)
    basename = os.path.basename(md_file_path)

    # 可能的路径列表（按优先级排序）
    possible_paths = [
        # 1. 相对于 Markdown 文件的 attachments 目录
        os.path.join(md_dir, 'attachments', filename),
        # 2. 相对于 Markdown 文件的 index_files 目录
        os.path.join(md_dir, 'index_files', filename),
        # 3. Markdown 文件同名的 _files 目录（保留 .md）
        os.path.join(md_dir, basename + '_files', filename),
        # 4. Markdown 文件同名（移除 .md）的 _files 目录
        os.path.join(md_dir, basename.replace('.md', '') + '_files', filename),
        # 5. Markdown 文件同名（移除空格和 .md）的 _files 目录（为知笔记导出格式）
        os.path.join(md_dir, basename.replace('.md', '').replace(' ', '') + '_files', filename),
        # 6. Markdown 文件同目录
        os.path.join(md_dir, filename),
        # 7. 统一的 assets 目录
        os.path.join(base_dir, 'assets', filename),
    ]

    # 检查每个可能路径
    for path in possible_paths:
        if os.path.exists(path):
            return True, path

    # 8. 如果上述路径都没找到，在整个仓库中全局搜索（Obsidian 特性）
    for root, dirs, files in os.walk(base_dir):
        # 跳过 .trash 目录
        if '.trash' in root:
            continue
        if filename in files:
            full_path = os.path.join(root, filename)
            return True, full_path

    return False, None

def check_note_attachments(obsidian_path, base_dir):
    """检查笔记的附件完整性"""
    if not os.path.exists(obsidian_path):
        return None

    with open(obsidian_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 提取所有图片引用
    md_pattern = r'!\[.*?\]\(([^)]+)\)'
    wikilink_pattern = r'!\[\[(.*?)\]\]'

    md_images = re.findall(md_pattern, content)
    wikilink_images = re.findall(wikilink_pattern, content)

    all_refs = md_images + wikilink_images

    # 过滤掉 URL（只检查本地文件）
    all_refs = [ref for ref in all_refs if not ref.startswith('http')]

    # 过滤掉 block 引用（如 #^block-id）
    all_refs = [ref for ref in all_refs if not ref.startswith('#') and '^' not in ref]

    if not all_refs:
        return {'status': 'no_attachments', 'count': 0, 'missing': [], 'attachments': []}

    # 检查每个引用
    missing = []
    attachments = []

    for ref in all_refs:
        # 处理别名语法
        if '|' in ref:
            ref = ref.split('|')[0]

        # 获取文件名
        filename = os.path.basename(ref)

        # 检查文件是否存在
        exists, path = check_file_exists(filename if not ref.startswith('attachments/') else ref, obsidian_path, base_dir)

        attachments.append({
            'ref': ref,
            'filename': filename,
            'exists': exists,
            'path': path
        })

        if not exists:
            missing.append(ref)

    if not missing:
        return {'status': 'complete', 'count': len(all_refs), 'missing': [], 'attachments': attachments}
    elif len(missing) == len(all_refs):
        return {'status': 'all_missing', 'count': len(all_refs), 'missing': missing, 'attachments': attachments}
    else:
        return {'status': 'partial', 'count': len(all_refs), 'missing': missing, 'attachments': attachments}

def main():
    print("🔍 开始检查 Obsidian 笔记的图片和附件完整性...\n")

    # 查找所有笔记
    md_files = []
    for root, dirs, files in os.walk(OBSIDIAN_DIR):
        # 跳过 .trash 目录
        if '.trash' in root:
            continue
        for file in files:
            if file.endswith('.md'):
                md_files.append(os.path.join(root, file))

    print(f"找到 {len(md_files)} 个笔记\n")

    # 检查每个笔记
    stats = {
        'complete': [],
        'no_attachments': [],
        'all_missing': [],
        'partial': []
    }

    for i, md_file in enumerate(md_files, 1):
        basename = os.path.basename(md_file)
        print(f"[{i}/{len(md_files)}] 检查: {basename}")

        result = check_note_attachments(md_file, OBSIDIAN_DIR)
        if result:
            stats[result['status']].append({
                'path': md_file,
                'basename': basename,
                'count': result['count'],
                'missing': result['missing'],
                'attachments': result.get('attachments', [])
            })

            status_icon = {
                'complete': '✅',
                'no_attachments': '📝',
                'all_missing': '❌',
                'partial': '⚠️'
            }.get(result['status'], '❓')

            if result['status'] == 'complete':
                print(f"   {status_icon} 附件: {result['count']}")
            elif result['status'] == 'no_attachments':
                print(f"   {status_icon} 无附件")
            else:
                print(f"   {status_icon} 附件: {result['count']}, 缺失: {len(result['missing'])}")

    # 生成报告
    print("\n📊 生成报告...")

    report = []
    report.append("# Obsidian 笔记图片和附件完整性检查报告（最终版）\n\n")
    report.append("## 概览\n\n")
    report.append(f"- **笔记总数**: {len(md_files)}\n")
    report.append(f"- **✅ 完整迁移**: {len(stats['complete'])} ({len(stats['complete'])/len(md_files)*100:.1f}%)\n")
    report.append(f"- **📝 无附件**: {len(stats['no_attachments'])} ({len(stats['no_attachments'])/len(md_files)*100:.1f}%)\n")
    report.append(f"- **❌ 完全缺失**: {len(stats['all_missing'])} ({len(stats['all_missing'])/len(md_files)*100:.1f}%)\n")
    report.append(f"- **⚠️ 部分缺失**: {len(stats['partial'])} ({len(stats['partial'])/len(md_files)*100:.1f}%)\n\n")

    # 有附件的笔记统计
    notes_with_attachments = len(stats['complete']) + len(stats['all_missing']) + len(stats['partial'])
    if notes_with_attachments > 0:
        complete_rate = len(stats['complete']) / notes_with_attachments * 100
        report.append(f"**附件完整率**: {complete_rate:.1f}% ({len(stats['complete'])}/{notes_with_attachments})\n\n")

    report.append("---\n\n")

    # 完整迁移的笔记
    if stats['complete']:
        report.append("## ✅ 完整迁移的笔记\n\n")
        report.append(f"共 {len(stats['complete'])} 个笔记\n\n")

        for item in sorted(stats['complete'], key=lambda x: x['count'], reverse=True):
            report.append(f"### {item['basename']}\n")
            report.append(f"- **路径**: `{item['path']}`\n")
            report.append(f"- **图片/附件数**: {item['count']}\n\n")

    # 缺失附件的笔记
    if stats['all_missing'] or stats['partial']:
        report.append("## ❌ 缺失附件的笔记\n\n")

        all_missing = stats['all_missing'] + stats['partial']
        report.append(f"共 {len(all_missing)} 个笔记\n\n")

        for item in sorted(all_missing, key=lambda x: len(x['missing']), reverse=True):
            report.append(f"### {item['basename']}\n")
            report.append(f"- **路径**: `{item['path']}`\n")
            report.append(f"- **附件数**: {item['count']}\n")
            report.append(f"- **缺失数**: {len(item['missing'])}\n")
            report.append(f"- **缺失列表**:\n")
            for missing in item['missing'][:10]:  # 只显示前10个
                report.append(f"  - ❌ {missing}\n")
            if len(item['missing']) > 10:
                report.append(f"  - ... 还有 {len(item['missing']) - 10} 个\n")
            report.append("\n")

    # 保存报告
    with open(OUTPUT_REPORT, 'w', encoding='utf-8') as f:
        f.write(''.join(report))

    print(f"\n✅ 报告已生成: {OUTPUT_REPORT}\n")

    print("=" * 60)
    print("摘要统计")
    print("=" * 60)
    print(f"笔记总数: {len(md_files)}")
    print(f"✅ 完整迁移: {len(stats['complete'])} ({len(stats['complete'])/len(md_files)*100:.1f}%)")
    print(f"📝 无附件: {len(stats['no_attachments'])} ({len(stats['no_attachments'])/len(md_files)*100:.1f}%)")
    print(f"❌ 完全缺失: {len(stats['all_missing'])} ({len(stats['all_missing'])/len(md_files)*100:.1f}%)")
    print(f"⚠️  部分缺失: {len(stats['partial'])} ({len(stats['partial'])/len(md_files)*100:.1f}%)")
    print("=" * 60)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='检查 Obsidian 笔记的图片和附件完整性')
    parser.add_argument('--obsidian-dir', required=True, help='Obsidian vault 目录路径')
    parser.add_argument('--output', default=None, help='输出报告路径（默认: <obsidian-dir>/../docs/ATTACHMENT_MIGRATION_FINAL_REPORT.md）')
    args = parser.parse_args()

    OBSIDIAN_DIR = args.obsidian_dir
    OUTPUT_REPORT = args.output or os.path.join(os.path.dirname(OBSIDIAN_DIR), 'docs', 'ATTACHMENT_MIGRATION_FINAL_REPORT.md')
    main()
