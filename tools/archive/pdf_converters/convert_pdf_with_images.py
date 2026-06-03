#!/usr/bin/env python3
"""
使用 PyMuPDF (fitz) 将 PDF 转换为 Markdown
支持文本和图片提取
"""

import fitz  # PyMuPDF
from pathlib import Path
import sys

def convert_pdf_to_markdown():
    """使用 PyMuPDF 转换 PDF 为 Markdown（包含图片）"""

    # 路径
    export_dir = Path('/Users/wardlu/Documents/VibeCoding/Wiznote to Obisidian/wiznote_download/缺失图片及附件笔记')
    obsidian_attachments = Path("/Users/wardlu/Documents/Ward's Obsidian/02_Areas/产品思考/产品管理/attachments")

    # 确保目标目录存在
    obsidian_attachments.mkdir(parents=True, exist_ok=True)

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
            # 打开 PDF
            doc = fitz.open(pdf_path)

            # 提取内容
            markdown_content = []
            image_count = 0

            for page_num in range(len(doc)):
                page = doc[page_num]

                # 提取文本
                text = page.get_text()

                # 提取图片
                image_list = page.get_images()

                if text.strip():
                    markdown_content.append(text)

                # 处理图片
                for img_index, img in enumerate(image_list):
                    xref = img[0]
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    image_ext = base_image["ext"]

                    # 生成图片文件名
                    image_filename = f"{pdf_path.stem}_page{page_num + 1}_img{img_index + 1}.{image_ext}"
                    image_path = obsidian_attachments / image_filename

                    # 保存图片
                    with open(image_path, 'wb') as img_file:
                        img_file.write(image_bytes)

                    # 在 Markdown 中添加图片引用
                    markdown_content.append(f"\n![[attachments/{image_filename}]]\n")
                    image_count += 1

            doc.close()

            # 组合内容
            full_text = '\n\n'.join(markdown_content)

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
            print(f"  🖼️  {image_count} 张图片")

        except Exception as e:
            print(f"  ❌ 转换失败: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 60)
    print(f"转换完成: {len(pdf_files)} 个文件")

if __name__ == '__main__':
    convert_pdf_to_markdown()
