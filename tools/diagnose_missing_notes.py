#!/usr/bin/env python3
"""
诊断工具：找出在第一次对比中标记为"已迁移"，但在第二次附件检查中缺失的笔记
"""
import os
import re
import argparse
from pathlib import Path
from collections import defaultdict

# 配置
SOURCE_DIR = None
TARGET_DIR = None
OUTPUT_FILE = None

def normalize_filename_compare(filename):
    """
    第一次对比工具的标准化算法（compare_migration.py）
    """
    # 移除 .md 后缀
    name = filename.replace('.md', '')
    # 统一空格和下划线
    name = re.sub(r'[\s_]+', ' ', name)
    # 移除特殊字符，只保留中文、英文、数字、空格
    name = re.sub(r'[^\w\s\u4e00-\u9fff]', '', name)
    # 转换为小写
    name = name.lower()
    return name

def normalize_filename_check(filename):
    """
    第二次附件检查工具的标准化算法（check_attachment_migration_fixed.py）
    """
    # 移除扩展名
    name = Path(filename).stem
    # 转小写
    name = name.lower()
    # 统一空格和下划线
    name = name.replace('_', ' ')
    # 移除特殊字符
    name = re.sub(r'[^\w\s]', '', name)
    return name

def get_all_md_files_compare(directory):
    """
    第一次对比工具的文件扫描方法
    """
    files = {}
    base_path = Path(directory)
    for md_file in base_path.rglob("*.md"):
        relative_path = md_file.relative_to(base_path)
        files[str(relative_path)] = str(md_file)
    return files

def find_all_md_files_check(directory):
    """
    第二次附件检查工具的文件扫描方法
    """
    md_files = {}
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.md'):
                full_path = os.path.join(root, file)
                normalized = normalize_filename_check(file)
                md_files[normalized] = {
                    'filename': file,
                    'path': full_path,
                    'relative_path': os.path.relpath(full_path, directory)
                }
    return md_files

def main():
    print("🔍 开始诊断缺失的 25 个笔记...\n")

    # === 第一步：模拟第一次对比工具 ===
    print("📊 步骤 1: 使用第一次对比工具的逻辑扫描文件...")
    source_files_compare = get_all_md_files_compare(SOURCE_DIR)
    target_files_compare = get_all_md_files_compare(TARGET_DIR)

    # 构建目标索引（第一次对比的逻辑）
    target_index_compare = defaultdict(list)
    for rel_path in target_files_compare.keys():
        filename = Path(rel_path).name
        normalized = normalize_filename_compare(filename)
        target_index_compare[normalized].append(rel_path)

    # 找出第一次对比中标记为"已迁移"的笔记
    migrated_compare = {}
    for rel_path in sorted(source_files_compare.keys()):
        filename = Path(rel_path).name
        normalized = normalize_filename_compare(filename)
        matches = target_index_compare.get(normalized, [])

        if matches:
            # 找到匹配，标记为已迁移
            migrated_compare[rel_path] = {
                'source_path': source_files_compare[rel_path],
                'target_matches': matches,
                'normalized_name': normalized
            }

    print(f"   第一次对比工具认为已迁移: {len(migrated_compare)} 个笔记\n")

    # === 第二步：模拟第二次附件检查工具 ===
    print("📊 步骤 2: 使用第二次附件检查工具的逻辑扫描文件...")
    wiznote_files_check = find_all_md_files_check(SOURCE_DIR)
    obsidian_files_check = find_all_md_files_check(TARGET_DIR)

    # 找出第二次检查中匹配的笔记
    migrated_check = {}
    for norm_name, obs_info in obsidian_files_check.items():
        if norm_name in wiznote_files_check:
            wiz_info = wiznote_files_check[norm_name]
            migrated_check[norm_name] = {
                'name': obs_info['filename'],
                'wiznote_path': wiz_info['path'],
                'obsidian_path': obs_info['path']
            }

    print(f"   第二次附件检查工具找到: {len(migrated_check)} 个笔记\n")

    # === 第三步：找出差异 ===
    print("🔍 步骤 3: 找出缺失的笔记...")

    # 获取第二次检查的标准化名称集合
    check_normalized_set = set(migrated_check.keys())

    # 检查第一次对比中的每个"已迁移"笔记，看是否在第二次检查中
    missing_notes = []
    for source_rel_path, info in migrated_compare.items():
        normalized_name = info['normalized_name']

        if normalized_name not in check_normalized_set:
            # 这个笔记在第一次对比中被认为已迁移，但在第二次检查中缺失
            missing_notes.append({
                'source_rel_path': source_rel_path,
                'source_full_path': info['source_path'],
                'expected_target_matches': info['target_matches'],
                'normalized_name': normalized_name,
                'source_filename': Path(source_rel_path).name
            })

    print(f"   发现缺失笔记: {len(missing_notes)} 个\n")

    # === 第四步：分析原因 ===
    print("🔬 步骤 4: 分析缺失原因...\n")

    reasons = defaultdict(list)

    for note in missing_notes:
        source_filename = note['source_filename']

        # 使用两种方法标准化
        norm_compare = normalize_filename_compare(source_filename)
        norm_check = normalize_filename_check(source_filename)

        # 检查标准化结果是否相同
        if norm_compare == norm_check:
            reasons['标准化相同但未匹配'].append(note)
        else:
            reasons['标准化算法差异'].append({
                **note,
                'norm_compare': norm_compare,
                'norm_check': norm_check
            })

    # === 第五步：生成报告 ===
    print("📝 步骤 5: 生成调查报告...\n")

    report_lines = [
        "# 缺失 25 个笔记调查报告",
        "",
        "## 问题概述",
        "",
        f"- **第一次对比报告**: 显示 **{len(migrated_compare)} 个已迁移笔记**",
        f"- **第二次附件检查**: 只检查了 **{len(migrated_check)} 个笔记**",
        f"- **缺失笔记数**: **{len(missing_notes)} 个**",
        "",
        "---",
        "",
        "## 缺失笔记列表",
        "",
    ]

    # 按原因分类输出
    for reason, notes in reasons.items():
        report_lines.append(f"### {reason} ({len(notes)} 个)")
        report_lines.append("")

        for i, note in enumerate(notes, 1):
            report_lines.append(f"#### {i}. {note['source_filename']}")
            report_lines.append("")
            report_lines.append(f"- **源路径**: `{note['source_rel_path']}`")
            report_lines.append(f"- **标准化名称**: `{note['normalized_name']}`")
            report_lines.append(f"- **应该匹配的目标路径**:")
            for match in note['expected_target_matches']:
                report_lines.append(f"  - `{match}`")

            if reason == '标准化算法差异':
                report_lines.append(f"- **第一次对比标准化**: `{note['norm_compare']}`")
                report_lines.append(f"- **第二次检查标准化**: `{note['norm_check']}`")
                report_lines.append(f"- **差异原因**: 两个工具的标准化算法不同")

            report_lines.append("")

    # 添加技术分析
    report_lines.extend([
        "---",
        "",
        "## 技术分析",
        "",
        "### 两个工具的标准化算法差异",
        "",
        "#### compare_migration.py（第一次对比）",
        "",
        "```python",
        "def normalize_filename(filename):",
        "    # 移除 .md 后缀",
        "    name = filename.replace('.md', '')",
        "    # 统一空格和下划线",
        "    name = re.sub(r'[\\s_]+', ' ', name)",
        "    # 移除特殊字符，只保留中文、英文、数字、空格",
        "    name = re.sub(r'[^\\w\\s\\u4e00-\\u9fff]', '', name)",
        "    # 转换为小写",
        "    name = name.lower()",
        "    return name",
        "```",
        "",
        "#### check_attachment_migration_fixed.py（第二次检查）",
        "",
        "```python",
        "def normalize_filename(filename):",
        "    # 移除扩展名",
        "    name = Path(filename).stem",
        "    # 转小写",
        "    name = name.lower()",
        "    # 统一空格和下划线",
        "    name = name.replace('_', ' ')",
        "    # 移除特殊字符",
        "    name = re.sub(r'[^\\w\\s]', '', name)",
        "    return name",
        "```",
        "",
        "### 关键差异",
        "",
        "1. **`.md` 后缀处理**:",
        "   - 第一次对比：`filename.replace('.md', '')` - 只移除第一个 `.md`",
        "   - 第二次检查：`Path(filename).stem` - 移除所有扩展名",
        "",
        "2. **空格和下划线处理**:",
        "   - 第一次对比：`re.sub(r'[\\s_]+', ' ', name)` - 连续空格/下划线合并为一个空格",
        "   - 第二次检查：`name.replace('_', ' ')` - 只替换单个下划线",
        "",
        "3. **特殊字符处理**:",
        "   - 第一次对比：保留中文字符 `\\u4e00-\\u9fff`",
        "   - 第二次检查：可能移除中文字符",
        "",
        "---",
        "",
        "## 修复建议",
        "",
        "### 方案 1: 统一标准化算法（推荐）",
        "",
        "修改 `check_attachment_migration_fixed.py`，使用与 `compare_migration.py` 相同的标准化算法：",
        "",
        "```python",
        "def normalize_filename(filename):",
        "    # 移除 .md 后缀",
        "    name = filename.replace('.md', '')",
        "    # 统一空格和下划线",
        "    name = re.sub(r'[\\s_]+', ' ', name)",
        "    # 移除特殊字符，只保留中文、英文、数字、空格",
        "    name = re.sub(r'[^\\w\\s\\u4e00-\\u9fff]', '', name)",
        "    # 转换为小写",
        "    name = name.lower()",
        "    return name",
        "```",
        "",
        "### 方案 2: 使用第一次对比的匹配结果",
        "",
        "直接读取第一次对比报告，提取已迁移笔记列表，避免重复匹配。",
        "",
        "---",
        "",
        "## 附录：完整的缺失笔记列表（JSON 格式）",
        "",
        "```json",
    ])

    # 添加 JSON 格式的缺失笔记列表
    import json
    report_lines.append(json.dumps(missing_notes, ensure_ascii=False, indent=2))
    report_lines.append("```")
    report_lines.append("")

    # 添加报告生成信息
    report_lines.extend([
        "---",
        "",
        "## 报告生成信息",
        "",
        f"- **生成时间**: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- **源目录**: `{SOURCE_DIR}`",
        f"- **目标目录**: `{TARGET_DIR}`",
        ""
    ])

    # 保存报告
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report_lines))

    print(f"✅ 调查报告已生成: {OUTPUT_FILE}\n")

    # 打印摘要
    print("=" * 60)
    print("调查摘要")
    print("=" * 60)
    print(f"第一次对比认为已迁移: {len(migrated_compare)} 个")
    print(f"第二次检查实际匹配: {len(migrated_check)} 个")
    print(f"缺失笔记数: {len(missing_notes)} 个")
    print()
    print("缺失原因分类:")
    for reason, notes in reasons.items():
        print(f"  - {reason}: {len(notes)} 个")
    print("=" * 60)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='诊断工具：找出迁移差异中的缺失笔记')
    parser.add_argument('--source-dir', required=True, help='为知笔记源目录路径')
    parser.add_argument('--target-dir', required=True, help='Obsidian 目标目录路径')
    parser.add_argument('--output', default=None, help='输出报告路径（默认: <cwd>/docs/MISSING_25_NOTES_INVESTIGATION.md）')
    args = parser.parse_args()

    SOURCE_DIR = args.source_dir
    TARGET_DIR = args.target_dir
    OUTPUT_FILE = args.output or os.path.join(os.getcwd(), 'docs', 'MISSING_25_NOTES_INVESTIGATION.md')
    main()
