#!/usr/bin/env python3
"""
将 WizNote 导出的 PDF 转换为 Markdown
使用 PyPDF2 提取文本内容
"""

from pathlib import Path
import sys

def convert_pdf_to_markdown():
    """转换 PDF 为 Markdown"""
    try:
        import PyPDF2
        print("✅ PyPDF2 可用\n")
    except ImportError:
        print("❌ PyPDF2 未安装，正在安装...")
        import subprocess
        try:
            subprocess.run(['pip3', 'install', 'PyPDF2'], check=True)
            print("✅ 安装成功\n")
        except:
            print("❌ 安装失败，请手动安装: pip3 install PyPDF2")
            return

    # 路径
    export_dir = Path('/Users/wardlu/Documents/VibeCoding/Wiznote to Obisidian/wiznote_download/缺失图片及附件笔记')

    # 检查 PDF 文件
    pdf_files = list(export_dir.glob('*.pdf'))

    if not pdf_files:
        print(f"❌ 未找到 PDF 文件")
        return

    print(f"找到 {len(pdf_files)} 个 PDF 文件\n")
    print("=" * 60)

    # 转换每个 PDF
    total = len(pdf_files)
    for idx, pdf_path in enumerate(pdf_files, 1):
        print(f"\n[{idx}/{total}] {pdf_path.name}")

        try:
            # 读取 PDF
            with open(pdf_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)

                # 提取文本
                text_content = []
                for page in reader.pages:
                    text = page.extract_text()
                    if text:
                        text_content.append(text)

                full_text = '\n\n'.join(text_content)

                # 保存为 Markdown
                output_name = pdf_path.stem + '.md'
                output_path = export_dir / output_name

                # 添加 frontmatter
                frontmatter = f"""---
title: "{pdf_path.stem}"
created: 2020-01-01
imported: 2026-02-27
source: WizNote (PDF)
tags: ['WizNote', 'PDF']
value: medium
status: archived
category: "产品思考"

---

# {pdf_path.stem}

"""

                final_content = frontmatter + full_text

                output_path.write_text(final_content, encoding='utf-8')

                print(f"  ✅ 转换成功")
                print(f"  📄 {len(full_text)} 字符")

        except Exception as e:
            print(f"  ❌ 转换失败: {e}")

    print("\n" + "=" * 60)
    print(f"转换完成: {len(pdf_files)} 个文件")

if __name__ == '__main__':
    convert_pdf_to_markdown()
