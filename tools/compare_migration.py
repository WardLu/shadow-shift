#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
为知笔记迁移对比工具
对比源笔记目录和 Obsidian 目录，生成迁移对比报告
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


def normalize_filename(filename):
    """
    标准化文件名，用于比较
    - 移除 .md 后缀
    - 统一空格和连字符
    - 移除特殊字符
    - 转换为小写
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


def get_all_md_files(directory):
    """
    递归获取目录下所有 Markdown 文件
    返回: {相对路径: 完整路径}
    """
    files = {}
    base_path = Path(directory)

    for md_file in base_path.rglob("*.md"):
        relative_path = md_file.relative_to(base_path)
        files[str(relative_path)] = str(md_file)

    return files


def build_target_index(target_files):
    """
    构建 Obsidian 文件索引（标准化文件名 -> 相对路径列表）
    用于快速查找匹配的文件
    """
    index = defaultdict(list)
    for rel_path in target_files.keys():
        # 获取文件名部分
        filename = Path(rel_path).name
        normalized = normalize_filename(filename)
        index[normalized].append(rel_path)
    return index


def find_matching_file(source_filename, target_index):
    """
    在目标索引中查找匹配的文件
    返回: 匹配的相对路径列表
    """
    normalized = normalize_filename(source_filename)
    return target_index.get(normalized, [])


def organize_by_directory(files_dict):
    """
    按目录结构组织文件
    返回: {目录路径: [文件列表]}
    """
    organized = defaultdict(list)
    for rel_path in sorted(files_dict.keys()):
        parts = Path(rel_path).parts
        if len(parts) > 1:
            dir_path = str(Path(*parts[:-1]))
        else:
            dir_path = "根目录"
        organized[dir_path].append(rel_path)
    return organized


def generate_report(source_files, target_files, unmigrated_files):
    """
    生成 Markdown 格式的对比报告
    """
    # 按目录组织未迁移文件
    organized = organize_by_directory(unmigrated_files)

    # 计算已迁移数量
    migrated_count = len(source_files) - len(unmigrated_files)

    # 生成报告
    report_lines = [
        "# 为知笔记迁移对比报告",
        "",
        "## 概览",
        "",
        f"- **源笔记总数**: {len(source_files)}",
        f"- **已迁移笔记数**: {migrated_count}",
        f"- **未迁移笔记数**: {len(unmigrated_files)}",
        f"- **迁移完成率**: {migrated_count / len(source_files) * 100:.1f}%",
        "",
        "---",
        "",
        "## 未迁移笔记列表",
        "",
    ]

    # 构建目录树结构
    dir_tree = {}
    for dir_path in sorted(organized.keys()):
        parts = dir_path.split('/')
        current = dir_tree
        for part in parts:
            if part not in current:
                current[part] = {}
            current = current[part]

    # 记录已处理的目录，避免重复
    processed_dirs = set()

    # 按目录输出
    for dir_path in sorted(organized.keys()):
        files = organized[dir_path]
        parts = dir_path.split('/')

        # 确定需要输出的目录层级
        for i, part in enumerate(parts):
            current_path = '/'.join(parts[:i+1])
            if current_path not in processed_dirs:
                # 输出目录标题
                level = i + 3  # 从 ### 开始
                prefix = "#" * level
                report_lines.append(f"{prefix} {part}")
                report_lines.append("")
                processed_dirs.add(current_path)

        # 列出该目录下的文件
        for rel_path in files:
            filename = Path(rel_path).name
            report_lines.append(f"- **{filename}**")
            report_lines.append(f"  - 相对路径: `{rel_path}`")
            report_lines.append("")

        report_lines.append("---")
        report_lines.append("")

    # 添加附录：文件名匹配规则
    report_lines.extend([
        "---",
        "",
        "## 附录",
        "",
        "### 文件名匹配规则",
        "",
        "为了处理为知笔记和 Obsidian 之间的文件名差异，本报告使用以下匹配规则：",
        "",
        "1. **忽略大小写**: `FileName.md` 和 `filename.md` 视为相同",
        "2. **统一空格和下划线**: `file_name.md` 和 `file name.md` 视为相同",
        "3. **移除特殊字符**: 忽略括号、连字符等特殊字符",
        "4. **仅匹配文件名**: 不考虑目录路径，只匹配文件名本身",
        "",
        "### 报告生成信息",
        "",
        f"- **生成时间**: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- **源目录**: `{SOURCE_DIR}`",
        f"- **目标目录**: `{TARGET_DIR}`",
    ])

    return "\n".join(report_lines)


def main():
    print("开始扫描源笔记目录...")
    source_files = get_all_md_files(SOURCE_DIR)
    print(f"找到 {len(source_files)} 个源笔记文件")

    print("\n开始扫描 Obsidian 目录...")
    target_files = get_all_md_files(TARGET_DIR)
    print(f"找到 {len(target_files)} 个 Obsidian 文件")

    print("\n构建目标文件索引...")
    target_index = build_target_index(target_files)

    print("\n开始对比文件...")
    unmigrated_files = {}

    for rel_path in sorted(source_files.keys()):
        filename = Path(rel_path).name
        matches = find_matching_file(filename, target_index)

        if not matches:
            # 未找到匹配文件，记录为未迁移
            unmigrated_files[rel_path] = source_files[rel_path]

    print(f"发现 {len(unmigrated_files)} 个未迁移文件")

    print("\n生成对比报告...")
    report = generate_report(source_files, target_files, unmigrated_files)

    # 确保输出目录存在
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

    # 写入报告
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"\n报告已生成: {OUTPUT_FILE}")
    print(f"\n总结:")
    print(f"  - 源笔记总数: {len(source_files)}")
    print(f"  - 已迁移笔记数: {len(source_files) - len(unmigrated_files)}")
    print(f"  - 未迁移笔记数: {len(unmigrated_files)}")
    print(f"  - 迁移完成率: {(len(source_files) - len(unmigrated_files)) / len(source_files) * 100:.1f}%")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='为知笔记迁移对比工具')
    parser.add_argument('--source-dir', required=True, help='为知笔记源目录路径')
    parser.add_argument('--target-dir', required=True, help='Obsidian 目标目录路径')
    parser.add_argument('--output', default=None, help='输出报告路径（默认: <cwd>/docs/MIGRATION_COMPARISON_REPORT.md）')
    args = parser.parse_args()

    SOURCE_DIR = args.source_dir
    TARGET_DIR = args.target_dir
    OUTPUT_FILE = args.output or os.path.join(os.getcwd(), 'docs', 'MIGRATION_COMPARISON_REPORT.md')
    main()
