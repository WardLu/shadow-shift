#!/usr/bin/env python3
"""
图片下载诊断工具 - 检查为什么某些笔记的图片没有被下载

功能：
  - 诊断特定笔记的图片下载问题
  - 检查 API 返回的资源列表
  - 分析 Markdown 中的图片引用
  - 保存完整的 API 响应用于调试
  - 给出具体的修复建议

使用方法：
    # 交互式使用（会提示输入笔记标题）
    python3 tools/diagnose_image_download.py

    # 直接指定笔记标题
    python3 tools/diagnose_image_download.py --note "智能制造MES拆解"

    # 保存调试信息
    python3 tools/diagnose_image_download.py --note "智能制造MES拆解" --save-debug

输出：
  - 控制台：详细的诊断步骤和结果
  - debug_api_response.json：完整的 API 响应（使用 --save-debug）

示例：
    $ python3 tools/diagnose_image_download.py --note "智能制造MES拆解"

    ======================================================================
    🔍 诊断笔记: 智能制造MES拆解
    ======================================================================

    Step 1: 搜索笔记...
    ✅ 找到笔记: abc123...

    Step 2: 检查 API 返回的资源列表...
    ⚠️  API 返回的资源列表为空！

    Step 3: 查看原始 API 响应...
    📦 API 返回的字段:
       - html: 12345 字符
       - resources: 0 项

    📄 完整 API 响应已保存到: debug_api_response.json

    ⚠️  问题确认: API 没有返回图片资源，但 Markdown 中有图片引用
    💡 解决方案:
       1. 使用离线导出方式（在 WizNote 客户端中导出）
       2. 手动下载图片并放到对应的 _files 文件夹
"""

import os
import sys
import json
import getpass
import argparse
from pathlib import Path

# 添加 tools 目录到路径
sys.path.insert(0, str(Path(__file__).parent))

try:
    from wiznote_downloader import WizMigrator
except ImportError:
    print("❌ 无法导入 wiznote_downloader，请确保在项目根目录运行此脚本")
    sys.exit(1)


def diagnose_specific_note(migrator, note_title):
    """诊断特定笔记的图片下载问题"""

    print(f"\n{'='*70}")
    print(f"🔍 诊断笔记: {note_title}")
    print(f"{'='*70}\n")

    # 1. 搜索笔记
    print("Step 1: 搜索笔记...")
    list_url = f"{migrator.kapi_url}/ks/note/list/category/{migrator.kb_guid}"
    params = {
        "category": "/",
        "start": 0,
        "count": 1000,
        "with_abstract": 0,
        "order": "created-desc"
    }

    response = migrator.session.get(list_url, params=params)
    data = response.json()

    if data.get('return_code') != 200 and data.get('returnCode') != 200:
        print(f"❌ API 调用失败: {data}")
        return

    notes = data.get('result', [])

    # 搜索匹配的笔记
    target_note = None
    for note in notes:
        title = note.get('title') or note.get('documentTitle') or note.get('docTitle')
        if title and note_title in title:
            target_note = note
            break

    if not target_note:
        print(f"❌ 未找到笔记: {note_title}")
        print(f"💡 提示: 请检查标题是否正确")
        return

    note_guid = target_note.get('guid') or target_note.get('documentGuid')
    print(f"✅ 找到笔记: {note_guid}\n")

    # 2. 检查 API 返回的资源列表
    print("Step 2: 检查 API 返回的资源列表...")
    resources = migrator.get_note_resources(note_guid)

    if not resources:
        print("⚠️  API 返回的资源列表为空！")
        print("   这就是为什么图片没有被下载的原因。\n")

        # 3. 查看原始 API 响应
        print("Step 3: 查看原始 API 响应...")
        url = f"{migrator.kapi_url}/ks/note/download/{migrator.kb_guid}/{note_guid}"
        params = {
            "downloadInfo": "0",
            "downloadData": "1"
        }

        response = migrator.session.get(url, params=params)

        print(f"   HTTP 状态码: {response.status_code}")

        try:
            data = response.json()
            print(f"   返回码: {data.get('return_code', data.get('returnCode'))}")

            result = data.get('result', data)

            # 检查关键字段
            print(f"\n   📦 API 返回的字段:")
            for key in ['resources', 'html', 'body', 'data']:
                if key in result:
                    value = result[key]
                    if isinstance(value, str):
                        print(f"      - {key}: {len(value)} 字符")
                    elif isinstance(value, list):
                        print(f"      - {key}: {len(value)} 项")
                    elif isinstance(value, dict):
                        print(f"      - {key}: {list(value.keys())[:5]}...")
                    else:
                        print(f"      - {key}: {type(value)}")

            # 保存完整响应到文件
            debug_file = "debug_api_response.json"
            with open(debug_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"\n   📄 完整 API 响应已保存到: {debug_file}")

        except Exception as e:
            print(f"   ❌ 解析 JSON 失败: {str(e)}")
            print(f"   响应内容（前 200 字符）: {response.text[:200]}")

    else:
        print(f"✅ 找到 {len(resources)} 个资源:")
        for name, url in list(resources.items())[:5]:
            print(f"   - {name}: {url[:60]}...")
        if len(resources) > 5:
            print(f"   ... 还有 {len(resources) - 5} 个资源")

    # 4. 检查 Markdown 内容中的图片引用
    print(f"\nStep 4: 检查 Markdown 内容中的图片引用...")

    # 下载笔记内容
    view_url = f"{migrator.kapi_url}/ks/note/view/{migrator.kb_guid}/{note_guid}"
    resp = migrator.session.get(view_url)
    data = resp.json()
    result = data.get('result', data)
    html_content = result.get('body') or result.get('html')

    if html_content:
        # 转换为 Markdown
        from markdownify import markdownify as md
        md_content = md(html_content, heading_style="ATX")

        # 查找图片引用
        import re
        image_refs = re.findall(r'!\[.*?\]\((.*?)\)', md_content)

        if image_refs:
            print(f"   📸 Markdown 中有 {len(image_refs)} 个图片引用:")
            for ref in image_refs[:5]:
                print(f"      - {ref}")
            if len(image_refs) > 5:
                print(f"      ... 还有 {len(image_refs) - 5} 个")
        else:
            print(f"   ℹ️  Markdown 中没有图片引用")

    print(f"\n{'='*70}")
    print(f"📊 诊断总结")
    print(f"{'='*70}")
    print(f"   - API 资源列表: {len(resources)} 个")
    print(f"   - Markdown 图片引用: {len(image_refs) if 'image_refs' in locals() else '未检查'} 个")

    if not resources and image_refs:
        print(f"\n⚠️  问题确认: API 没有返回图片资源，但 Markdown 中有图片引用")
        print(f"   这说明为知笔记的 API 在某些笔记上存在缺陷，无法获取图片资源列表。")
        print(f"\n💡 解决方案:")
        print(f"   1. 使用离线导出方式（在 WizNote 客户端中导出）")
        print(f"   2. 手动下载图片并放到对应的 _files 文件夹")
        print(f"   3. 联系为知笔记客服反馈此问题")


def main():
    parser = argparse.ArgumentParser(
        description="图片下载诊断工具 - 检查为什么某些笔记的图片没有被下载",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 交互式使用（会提示输入笔记标题）
  python3 tools/diagnose_image_download.py

  # 直接指定笔记标题
  python3 tools/diagnose_image_download.py --note "智能制造MES拆解"

  # 保存调试信息
  python3 tools/diagnose_image_download.py --note "智能制造MES拆解" --save-debug

输出文件:
  debug_api_response.json - 完整的 API 响应（使用 --save-debug）
        """
    )

    parser.add_argument(
        '--note', '-n',
        help='要诊断的笔记标题（或部分标题）'
    )

    parser.add_argument(
        '--save-debug',
        action='store_true',
        help='保存完整的 API 响应到 debug_api_response.json'
    )

    args = parser.parse_args()

    print("="*70)
    print("🔍 图片下载诊断工具")
    print("="*70)
    print("\n此工具将帮助你诊断为什么某些笔记的图片没有被下载。\n")

    # 登录
    u = input("📧 Email: ")
    p = getpass.getpass("🔑 Password: ")
    print()

    migrator = WizMigrator(u, p)
    success, error = migrator.login()

    if not success:
        print(f"❌ 登录失败: {error}")
        return

    # 诊断特定笔记
    if args.note:
        note_title = args.note
        print(f"\n📝 诊断笔记: {note_title}")
    else:
        note_title = input("\n📝 请输入要诊断的笔记标题（或部分标题）: ").strip()

        if not note_title:
            note_title = "智能制造MES拆解"
            print(f"   使用默认标题: {note_title}")

    diagnose_specific_note(migrator, note_title)


if __name__ == "__main__":
    main()
