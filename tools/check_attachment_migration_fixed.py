#!/usr/bin/env python3
"""
修复版：检查已迁移笔记的图片和附件完整性（支持 WikiLink 语法）
"""
import os
import re
import json
import argparse
from pathlib import Path
from collections import defaultdict

# 配置
WIZNOTE_DIR = None
OBSIDIAN_DIR = None
OUTPUT_REPORT = None

def normalize_filename(filename):
    """
    标准化文件名，用于匹配
    - 移除 .md 后缀（处理 .md.md 双扩展名）
    - 统一空格和下划线（合并连续的空格/下划线为一个空格）
    - 移除特殊字符，只保留中文、英文、数字、空格
    - 转换为小写
    - 去除首尾空格
    """
    # 移除 .md 后缀（处理 .md.md 双扩展名）
    name = filename.replace('.md', '')
    # 统一空格和下划线（合并连续的空格/下划线为一个空格）
    name = re.sub(r'[\s_]+', ' ', name)
    # 移除特殊字符，只保留中文、英文、数字、空格
    name = re.sub(r'[^\w\s\u4e00-\u9fff]', '', name)
    # 转换为小写
    name = name.lower()
    # 去除首尾空格
    name = name.strip()
    return name

def find_all_md_files(directory):
    """递归查找所有 Markdown 文件"""
    md_files = {}
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.md'):
                full_path = os.path.join(root, file)
                normalized = normalize_filename(file)
                md_files[normalized] = {
                    'filename': file,
                    'path': full_path,
                    'relative_path': os.path.relpath(full_path, directory)
                }
    return md_files

def extract_attachments_from_md(file_path):
    """从 Markdown 文件中提取所有图片和附件引用（支持 WikiLink）"""
    attachments = {
        'images': [],
        'files': []
    }

    if not os.path.exists(file_path):
        return attachments

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"  ⚠️  读取文件失败: {file_path}, 错误: {e}")
        return attachments

    # 匹配标准 Markdown 图片语法 ![alt](path)
    md_pattern = r'!\[.*?\]\((.*?)\)'
    md_matches = re.findall(md_pattern, content)

    # 匹配 Obsidian WikiLink 语法 ![[path]]
    wikilink_pattern = r'!\[\[(.*?)\]\]'
    wikilink_matches = re.findall(wikilink_pattern, content)

    # 处理所有匹配
    all_matches = md_matches + wikilink_matches

    for match in all_matches:
        # 分离出文件名（处理 WikiLink 中的别名语法）
        if '|' in match:
            match = match.split('|')[0]

        # 获取纯文件名
        filename = os.path.basename(match)

        # 判断是否是图片
        lower_match = match.lower()
        if any(ext in lower_match for ext in ['.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.bmp']):
            attachments['images'].append({
                'ref': match,
                'filename': filename
            })
        elif any(ext in lower_match for ext in ['.pdf', '.zip', '.doc', '.docx', '.xls', '.xlsx']):
            attachments['files'].append({
                'ref': match,
                'filename': filename
            })
        elif 'index_files' in match or 'assets' in match or 'attachments' in match or match.startswith('./'):
            # 可能是相对路径的图片
            attachments['images'].append({
                'ref': match,
                'filename': filename
            })

    # 去重（基于 filename）
    seen_images = set()
    seen_files = set()
    unique_images = []
    unique_files = []

    for img in attachments['images']:
        if img['filename'] not in seen_images:
            seen_images.add(img['filename'])
            unique_images.append(img)

    for file in attachments['files']:
        if file['filename'] not in seen_files:
            seen_files.add(file['filename'])
            unique_files.append(file)

    attachments['images'] = unique_images
    attachments['files'] = unique_files

    return attachments

def check_file_exists(filename, md_file_path, base_dir):
    """检查引用的文件是否存在"""
    # 获取 Markdown 文件所在目录
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

    return False, None

def check_note_attachments(wiznote_path, obsidian_path):
    """检查单个笔记的图片和附件完整性"""
    # 提取源笔记的附件
    source_attachments = extract_attachments_from_md(wiznote_path)

    # 提取目标笔记的附件
    target_attachments = extract_attachments_from_md(obsidian_path)

    result = {
        'source_images': [],
        'source_files': [],
        'missing_images': [],
        'missing_files': [],
        'status': 'complete'  # complete, partial, missing, no_attachments
    }

    # 检查源笔记是否有附件
    total_source = len(source_attachments['images']) + len(source_attachments['files'])
    if total_source == 0:
        result['status'] = 'no_attachments'
        return result

    # 检查每个图片
    for img in source_attachments['images']:
        result['source_images'].append(img['filename'])

        # 检查目标笔记中是否有引用
        found_in_target = False
        for target_img in target_attachments['images']:
            if img['filename'] == target_img['filename']:
                found_in_target = True
                break

        if not found_in_target:
            # 检查文件是否存在（可能在 attachments 目录但未被引用）
            exists, _ = check_file_exists(img['filename'], obsidian_path, os.path.dirname(obsidian_path))
            if not exists:
                result['missing_images'].append({
                    'name': img['filename'],
                    'reason': '引用缺失且文件不存在'
                })
                result['status'] = 'partial' if result['status'] == 'complete' else result['status']
        else:
            # 即使有引用，也检查文件是否存在
            exists, file_path = check_file_exists(img['filename'], obsidian_path, os.path.dirname(obsidian_path))
            if not exists:
                result['missing_images'].append({
                    'name': img['filename'],
                    'reason': '引用存在但文件缺失'
                })
                result['status'] = 'partial' if result['status'] == 'complete' else result['status']

    # 检查每个文件
    for file in source_attachments['files']:
        result['source_files'].append(file['filename'])

        # 检查目标笔记中是否有引用
        found_in_target = False
        for target_file in target_attachments['files']:
            if file['filename'] == target_file['filename']:
                found_in_target = True
                break

        if not found_in_target:
            result['missing_files'].append({
                'name': file['filename'],
                'reason': '引用缺失'
            })
            result['status'] = 'partial' if result['status'] == 'complete' else result['status']
        else:
            # 检查文件是否存在
            exists, _ = check_file_exists(file['filename'], obsidian_path, os.path.dirname(obsidian_path))
            if not exists:
                result['missing_files'].append({
                    'name': file['filename'],
                    'reason': '引用存在但文件缺失'
                })
                result['status'] = 'partial' if result['status'] == 'complete' else result['status']

    # 如果所有附件都缺失，标记为完全缺失
    if len(result['missing_images']) + len(result['missing_files']) == total_source:
        result['status'] = 'missing'

    return result

def generate_report(results):
    """生成 Markdown 报告"""
    # 统计
    total = len(results)
    complete = sum(1 for r in results if r['result']['status'] == 'complete')
    partial = sum(1 for r in results if r['result']['status'] == 'partial')
    missing = sum(1 for r in results if r['result']['status'] == 'missing')
    no_attachments = sum(1 for r in results if r['result']['status'] == 'no_attachments')

    report = []
    report.append("# 图片和附件迁移完整性检查报告（修正版）\n")
    report.append("## 概览\n")
    report.append(f"- **已迁移笔记总数**: {total}\n")
    report.append(f"- **完整迁移**: {complete} ({complete/total*100:.1f}%)\n")
    report.append(f"- **部分缺失**: {partial} ({partial/total*100:.1f}%)\n")
    report.append(f"- **完全缺失**: {missing} ({missing/total*100:.1f}%)\n")
    report.append(f"- **无附件笔记**: {no_attachments} ({no_attachments/total*100:.1f}%)\n")
    report.append("\n---\n\n")

    # ✅ 完整迁移的笔记
    complete_notes = [r for r in results if r['result']['status'] == 'complete']
    if complete_notes:
        report.append("## ✅ 完整迁移的笔记\n\n")
        report.append(f"共 {len(complete_notes)} 个笔记\n\n")
        for note in complete_notes:
            res = note['result']
            total_attachments = len(res['source_images']) + len(res['source_files'])
            report.append(f"### {note['name']}\n")
            report.append(f"- **源路径**: `{note['wiznote_path']}`\n")
            report.append(f"- **目标路径**: `{note['obsidian_path']}`\n")
            report.append(f"- **图片/附件数**: {total_attachments}\n")
            if res['source_images']:
                report.append(f"  - ✅ 图片 ({len(res['source_images'])}个)\n")
            if res['source_files']:
                report.append(f"  - ✅ 文件 ({len(res['source_files'])}个)\n")
            report.append("\n")

    # ⚠️ 部分缺失的笔记
    partial_notes = [r for r in results if r['result']['status'] == 'partial']
    if partial_notes:
        report.append("## ⚠️ 部分缺失的笔记\n\n")
        report.append(f"共 {len(partial_notes)} 个笔记\n\n")
        for note in partial_notes:
            res = note['result']
            total_source = len(res['source_images']) + len(res['source_files'])
            total_missing = len(res['missing_images']) + len(res['missing_files'])
            report.append(f"### {note['name']}\n")
            report.append(f"- **源路径**: `{note['wiznote_path']}`\n")
            report.append(f"- **目标路径**: `{note['obsidian_path']}`\n")
            report.append(f"- **源图片/附件数**: {total_source}\n")
            report.append(f"- **缺失数**: {total_missing}\n")
            report.append(f"- **缺失列表**:\n")
            for img in res['missing_images']:
                report.append(f"  - ❌ {img['name']} ({img['reason']})\n")
            for file in res['missing_files']:
                report.append(f"  - ❌ {file['name']} ({file['reason']})\n")
            report.append("\n")

    # ❌ 完全缺失的笔记
    missing_notes = [r for r in results if r['result']['status'] == 'missing']
    if missing_notes:
        report.append("## ❌ 完全缺失的笔记\n\n")
        report.append(f"共 {len(missing_notes)} 个笔记\n\n")
        for note in missing_notes:
            res = note['result']
            report.append(f"### {note['name']}\n")
            report.append(f"- **源路径**: `{note['wiznote_path']}`\n")
            report.append(f"- **目标路径**: `{note['obsidian_path']}`\n")
            report.append(f"- **缺失的图片/附件**:\n")
            for img in res['missing_images']:
                report.append(f"  - ❌ {img['name']}\n")
            for file in res['missing_files']:
                report.append(f"  - ❌ {file['name']}\n")
            report.append("\n")

    # 📝 无附件的笔记
    no_attach_notes = [r for r in results if r['result']['status'] == 'no_attachments']
    if no_attach_notes:
        report.append("## 📝 无附件的笔记\n\n")
        report.append(f"共 {len(no_attach_notes)} 个笔记\n\n")
        for i, note in enumerate(no_attach_notes, 1):
            report.append(f"{i}. {note['name']}\n")

    # 修复建议
    report.append("\n---\n\n")
    report.append("## 修复建议\n\n")
    report.append("### 常见缺失原因\n\n")
    report.append("1. **图片引用格式不兼容**: 为知笔记使用 `![](index_files/image.png)`，Obsidian 使用 `![](attachments/image.png)` 或 `![[image.png]]`\n")
    report.append("2. **附件文件未复制**: 迁移时只复制了 Markdown 文件，未复制附件文件\n")
    report.append("3. **路径错误**: 附件路径在迁移过程中未正确更新\n")
    report.append("4. **文件名变化**: 文件名中的特殊字符或空格被转换\n\n")

    report.append("### 如何修复\n\n")
    report.append("#### 方法 1: 手动修复单个笔记\n")
    report.append("```bash\n")
    report.append("# 1. 找到源附件\n")
    report.append(f"cd \"{WIZNOTE_DIR}\"\n")
    report.append("find . -name \"image.png\"  # 替换为实际文件名\n")
    report.append("\n")
    report.append("# 2. 复制到 Obsidian attachments 目录\n")
    report.append(f"cp /path/to/source/image.png \"{OBSIDIAN_DIR}/笔记目录/attachments/\"\n")
    report.append("\n")
    report.append("# 3. 在 Obsidian 中更新引用\n")
    report.append("# 将 ![](index_files/image.png) 改为 ![](attachments/image.png)\n")
    report.append("```\n\n")

    report.append("#### 方法 2: 批量修复（使用脚本）\n")
    report.append("```bash\n")
    report.append("# 运行附件集成工具\n")
    report.append(f"cd \"{os.path.dirname(WIZNOTE_DIR)}\"\n")
    report.append("python3 tools/integrate_missing_attachments.py\n")
    report.append("```\n\n")

    report.append("### 可用工具\n\n")
    report.append("1. **integrate_missing_attachments.py** - 集成缺失的附件\n")
    report.append("2. **remigrate_single_note.py** - 重新迁移单个笔记\n")
    report.append("3. **scan_wikilinks.py** - 扫描和修复 WikiLink 引用\n")
    report.append("4. **obsidian_health_check.py** - 健康检查工具\n\n")

    report.append("### 报告生成信息\n\n")
    report.append(f"- **生成时间**: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    report.append(f"- **源目录**: `{WIZNOTE_DIR}`\n")
    report.append(f"- **目标目录**: `{OBSIDIAN_DIR}`\n")
    report.append(f"- **说明**: 本报告已修正 WikiLink 语法支持，并验证文件实际存在性\n")

    return ''.join(report)

def main():
    print("🔍 开始检查已迁移笔记的图片和附件完整性（修正版）...\n")

    # 1. 查找所有 Markdown 文件
    print("📂 扫描源目录（为知笔记）...")
    wiznote_files = find_all_md_files(WIZNOTE_DIR)
    print(f"   找到 {len(wiznote_files)} 个 Markdown 文件\n")

    print("📂 扫描目标目录（Obsidian）...")
    obsidian_files = find_all_md_files(OBSIDIAN_DIR)
    print(f"   找到 {len(obsidian_files)} 个 Markdown 文件\n")

    # 2. 匹配已迁移的笔记
    print("🔗 匹配已迁移的笔记...")
    migrated = []
    for norm_name, obs_info in obsidian_files.items():
        if norm_name in wiznote_files:
            wiz_info = wiznote_files[norm_name]
            migrated.append({
                'name': obs_info['filename'],
                'wiznote_path': wiz_info['path'],
                'obsidian_path': obs_info['path']
            })

    print(f"   已迁移笔记: {len(migrated)} 个\n")

    # 3. 检查每个笔记的附件完整性
    print("🔍 检查图片和附件完整性（验证文件存在性）...\n")

    results = []
    for i, note in enumerate(migrated, 1):
        print(f"[{i}/{len(migrated)}] 检查: {note['name']}")

        result = check_note_attachments(note['wiznote_path'], note['obsidian_path'])

        status_icon = {
            'complete': '✅',
            'partial': '⚠️',
            'missing': '❌',
            'no_attachments': '📝'
        }[result['status']]

        total = len(result['source_images']) + len(result['source_files'])
        missing = len(result['missing_images']) + len(result['missing_files'])

        if result['status'] == 'no_attachments':
            print(f"   {status_icon} 无附件")
        else:
            print(f"   {status_icon} 附件: {total}, 缺失: {missing}")

        results.append({
            'name': note['name'],
            'wiznote_path': note['wiznote_path'],
            'obsidian_path': note['obsidian_path'],
            'result': result
        })

    # 4. 生成报告
    print("\n📊 生成报告...")
    report = generate_report(results)

    # 5. 保存报告
    os.makedirs(os.path.dirname(OUTPUT_REPORT), exist_ok=True)
    with open(OUTPUT_REPORT, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"\n✅ 报告已生成: {OUTPUT_REPORT}\n")

    # 打印摘要
    complete = sum(1 for r in results if r['result']['status'] == 'complete')
    partial = sum(1 for r in results if r['result']['status'] == 'partial')
    missing = sum(1 for r in results if r['result']['status'] == 'missing')
    no_attachments = sum(1 for r in results if r['result']['status'] == 'no_attachments')

    print("=" * 60)
    print("摘要统计")
    print("=" * 60)
    print(f"已迁移笔记总数: {len(results)}")
    print(f"✅ 完整迁移: {complete} ({complete/len(results)*100:.1f}%)")
    print(f"⚠️  部分缺失: {partial} ({partial/len(results)*100:.1f}%)")
    print(f"❌ 完全缺失: {missing} ({missing/len(results)*100:.1f}%)")
    print(f"📝 无附件笔记: {no_attachments} ({no_attachments/len(results)*100:.1f}%)")
    print("=" * 60)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='检查已迁移笔记的图片和附件完整性（修正版）')
    parser.add_argument('--wiznote-dir', required=True, help='为知笔记源目录路径')
    parser.add_argument('--obsidian-dir', required=True, help='Obsidian 目标目录路径')
    parser.add_argument('--output', default=None, help='输出报告路径（默认: <cwd>/docs/ATTACHMENT_MIGRATION_REPORT.md）')
    args = parser.parse_args()

    WIZNOTE_DIR = args.wiznote_dir
    OBSIDIAN_DIR = args.obsidian_dir
    OUTPUT_REPORT = args.output or os.path.join(os.getcwd(), 'docs', 'ATTACHMENT_MIGRATION_REPORT.md')
    main()
