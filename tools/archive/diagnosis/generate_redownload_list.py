#!/usr/bin/env python3
"""
生成重新下载列表 - 根据缺失图片报告生成需要重新下载的笔记列表

功能：
  - 读取 missing_images_report.md
  - 按缺失图片数量排序
  - 标记严重问题（缺失 >= 10 张图片）
  - 生成 redownload_list.md（Markdown 格式）

使用方法：
    # 基本用法
    python3 tools/generate_redownload_list.py

    # 指定报告文件路径
    python3 tools/generate_redownload_list.py --report ~/missing_images_report.md

    # 自定义严重问题阈值
    python3 tools/generate_redownload_list.py --severe-threshold 5

输出：
  - 控制台：显示严重问题列表和处理建议
  - redownload_list.md：按严重程度排序的重新下载列表（Markdown 格式）

示例：
    $ python3 tools/generate_redownload_list.py

    ======================================================================
    📝 需要重新下载的笔记列表
    ======================================================================

    ✅ 已生成重新下载列表: redownload_list.md
       共 50 个笔记需要处理

    🚨 严重问题（缺失 >= 10 张图片）：9 个笔记

       - 微信收藏/银行股评级（2017.7-2018.12） (64 张)
       - 技术笔记/产品经理PM/智能制造MES拆解.md (36 张)
       ...

    💡 建议：
       1. 在 WizNote 客户端中导出这些笔记
       2. 使用离线迁移工具处理导出的文件
       3. 或手动下载缺失的图片到对应的 _files 文件夹
"""

from pathlib import Path
import argparse


def parse_redownload_list(report_file):
    """解析缺失图片/附件报告文件（支持 TXT 和 Markdown 格式）

    Args:
        report_file: 报告文件路径

    Returns:
        list: 笔记列表，每个元素为 (文件路径, 总缺失数)
    """
    notes = []

    with open(report_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # 检测文件格式（通过扩展名）
    is_markdown = str(report_file).endswith('.md')

    for line in lines:
        line = line.strip()

        # 跳过空行和注释
        if not line:
            continue

        if is_markdown:
            # Markdown 格式：解析表格行
            # 格式：| 文件名 | 图片（已下载/引用） | 附件（已下载/引用） | 总缺失 |

            # 跳过标题行、分隔符行、表头行
            if line.startswith('#') or line.startswith('|---') or '文件名' in line:
                continue

            # 跳过非表格行
            if not line.startswith('|'):
                continue

            # 解析表格行
            parts = [p.strip() for p in line.split('|')]
            # parts[0] = '' (行首的|)
            # parts[1] = 文件名
            # parts[2] = 图片信息
            # parts[3] = 附件信息
            # parts[4] = 总缺失
            # parts[5] = '' (行尾的|)

            if len(parts) < 5:
                continue

            try:
                file_path = parts[1]
                total_missing = int(parts[4])

                if total_missing > 0 and file_path.endswith('.md'):
                    notes.append((file_path, total_missing))
            except (ValueError, IndexError):
                continue

        else:
            # TXT 格式：解析纯文本格式
            # 格式：微信收藏/银行股评级（2017.7-2018.12） - 集思录.md      96/160 ❌64   0/0          64

            # 跳过分隔符和标题
            if line.startswith('=') or line.startswith('-'):
                continue

            # 跳过总计行
            if '总计' in line or 'Total' in line.lower():
                continue

            # 跳过表头
            if '文件名' in line and ('图片' in line or '附件' in line):
                continue

            # 解析 TXT 格式：文件名 图片信息 附件信息 总计
            # 策略：从右向左解析，提取最后5个字段，剩余部分是文件名

            parts = line.split()

            if len(parts) < 5:
                continue

            try:
                # 从右向左提取字段
                total_missing = int(parts[-1])

                # 文件名提取逻辑：
                # - 如果 parts 数量正好是 5，文件名是 parts[0]
                # - 如果 parts 数量大于 5，文件名是 parts[:-5] 的拼接
                if len(parts) == 5:
                    file_path = parts[0]
                else:
                    file_path = ' '.join(parts[:-5])

                if total_missing > 0 and file_path.endswith('.md'):
                    notes.append((file_path, total_missing))
            except (ValueError, IndexError):
                continue

    return notes


def main():
    parser = argparse.ArgumentParser(
        description="生成重新下载列表 - 根据缺失图片/附件报告生成需要重新下载的笔记列表",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 基本用法
  python3 tools/generate_redownload_list.py

  # 指定报告文件路径
  python3 tools/generate_redownload_list.py --report ~/missing_images_report.md

  # 自定义严重问题阈值
  python3 tools/generate_redownload_list.py --severe-threshold 5

输出文件:
  redownload_list.md - 按严重程度排序的重新下载列表（Markdown 格式）
        """
    )

    parser.add_argument(
        '--report', '-r',
        default='missing_images_report.md',
        help='缺失图片/附件报告文件路径（默认: missing_images_report.md）'
    )

    parser.add_argument(
        '--severe-threshold', '-t',
        type=int,
        default=10,
        help='严重问题的总缺失数阈值（默认: 10）'
    )

    args = parser.parse_args()

    report_file = Path(args.report)

    if not report_file.exists():
        print("❌ 未找到缺失图片/附件报告，请先运行 batch_diagnose_images.py")
        return

    notes = parse_redownload_list(report_file)

    if not notes:
        print("❌ 报告文件为空或没有缺失的图片/附件")
        return

    # 按缺失数量排序
    notes.sort(key=lambda x: x[1], reverse=True)

    print("="*70)
    print("📝 需要重新下载的笔记列表")
    print("="*70)
    print("\n将此列表保存到 redownload_list.md，然后在 WizNote 客户端中")
    print("搜索并导出这些笔记。\n")

    # 保存到文件（Markdown 格式）
    output_file = report_file.parent / "redownload_list.md"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# 需要重新下载的笔记列表\n\n")

        f.write(f"**生成时间**: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        # 统计严重问题
        severe = [n for n in notes if n[1] >= args.severe_threshold]

        f.write("## 📊 统计概览\n\n")
        f.write(f"- **需要处理的笔记数**: {len(notes)} 个\n")
        f.write(f"- **严重问题数**: {len(severe)} 个（缺失 ≥{args.severe_threshold} 个资源）\n")
        f.write(f"- **总缺失资源数**: {sum(n[1] for n in notes)} 个\n\n")

        # 严重问题章节
        if severe:
            f.write("## 🚨 严重问题\n\n")
            f.write(f"以下 {len(severe)} 个笔记缺失资源数 ≥{args.severe_threshold}，建议优先处理：\n\n")
            f.write("| 序号 | 文件路径 | 缺失资源数 |\n")
            f.write("|------|----------|------------|\n")

            for i, (file_path, total_missing) in enumerate(severe, 1):
                # 转义 Markdown 特殊字符
                file_name = file_path.replace('|', '\\|')
                f.write(f"| {i} | {file_name} | {total_missing} |\n")

            f.write("\n")

        # 完整列表章节
        f.write("## 📋 完整列表\n\n")
        f.write("以下是所有需要重新下载的笔记，按缺失资源数降序排列：\n\n")
        f.write("| 序号 | 文件路径 | 缺失资源数 |\n")
        f.write("|------|----------|------------|\n")

        for i, (file_path, total_missing) in enumerate(notes, 1):
            # 转义 Markdown 特殊字符
            file_name = file_path.replace('|', '\\|')
            f.write(f"| {i} | {file_name} | {total_missing} |\n")

        f.write("\n## 💡 使用建议\n\n")
        f.write("### 方案 1：在 WizNote 客户端中导出（推荐）\n\n")
        f.write("1. 打开 WizNote 客户端\n")
        f.write("2. 搜索上述笔记标题\n")
        f.write("3. 右键 → 导出 → 选择 HTML 或 Markdown 格式\n")
        f.write("4. 将导出的文件放到 `wiznote_download/` 目录\n")
        f.write("5. 重新运行迁移工具：`python3 tools/obsidian_formatter.py`\n\n")

        f.write("### 方案 2：使用在线下载工具重新下载\n\n")
        f.write("```bash\n")
        f.write("# 使用更保守的参数重新下载\n")
        f.write("python3 tools/wiznote_downloader.py --workers 3 --timeout 20 --retries 3\n")
        f.write("```\n\n")

        f.write("### 方案 3：手动下载缺失的资源\n\n")
        f.write("1. 登录 WizNote 网页版\n")
        f.write("2. 找到对应的笔记\n")
        f.write("3. 手动保存图片/附件到对应的 `_files` 文件夹\n\n")

        f.write("---\n\n")
        f.write("*本报告由 `generate_redownload_list.py` 自动生成*\n")

    print(f"✅ 已生成重新下载列表: {output_file}")
    print(f"   共 {len(notes)} 个笔记需要处理\n")

    # 控制台显示严重问题
    severe = [n for n in notes if n[1] >= args.severe_threshold]
    if severe:
        print(f"🚨 严重问题（总缺失 ≥{args.severe_threshold} 个）：{len(severe)} 个笔记\n")
        for file_path, total_missing in severe[:10]:
            print(f"   - {file_path} ({total_missing} 个)")
        if len(severe) > 10:
            print(f"   ... 还有 {len(severe) - 10} 个")

    print(f"\n💡 建议：")
    print(f"   1. 在 WizNote 客户端中导出这些笔记")
    print(f"   2. 使用离线迁移工具处理导出的文件")
    print(f"   3. 或手动下载缺失的图片/附件到对应的 _files 文件夹")


if __name__ == "__main__":
    main()
