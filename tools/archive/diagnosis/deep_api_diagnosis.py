#!/usr/bin/env python3
"""
深度 API 诊断工具 - 分析为什么某些笔记的图片无法获取

功能：
  - 分析特定笔记的所有 API 端点
  - 尝试多种 API 调用方式获取资源
  - 对比成功和失败的笔记
  - 提供修复建议

使用方法：
    python3 tools/deep_api_diagnosis.py --note "智能制造MES拆解"
"""

import sys
import json
import getpass
import argparse
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

try:
    from wiznote_downloader import WizMigrator
    IMPORT_SUCCESS = True
except ImportError:
    IMPORT_SUCCESS = False
    print("❌ 无法导入 wiznote_downloader")
    sys.exit(1)


def analyze_note_apis(migrator, note_guid, note_title):
    """深度分析笔记的所有 API 端点"""

    print(f"\n{'='*70}")
    print(f"🔬 深度 API 诊断")
    print(f"{'='*70}\n")

    print(f"笔记标题: {note_title}")
    print(f"笔记 GUID: {note_guid}\n")

    results = {}

    # 1. 尝试 /ks/note/download API（当前使用的方式）
    print("📍 API 1: /ks/note/download（当前方式）")
    print("-" * 70)
    try:
        url = f"{migrator.kapi_url}/ks/note/download/{migrator.kb_guid}/{note_guid}"
        params = {
            "downloadInfo": "0",
            "downloadData": "1"
        }

        response = migrator.session.get(url, params=params, timeout=30)
        data = response.json()

        result = data.get('result', data)
        resources = result.get('resources', [])

        print(f"   HTTP 状态码: {response.status_code}")
        print(f"   返回码: {data.get('return_code', data.get('returnCode'))}")
        print(f"   资源数量: {len(resources)}")

        if resources:
            print(f"   资源列表（前 5 个）:")
            for res in resources[:5]:
                print(f"      - {res.get('name')}: {res.get('url', 'N/A')[:60]}...")

        results['download_api'] = {
            'status': response.status_code,
            'resources_count': len(resources),
            'resources': resources
        }

        # 保存完整响应
        with open('debug_download_api.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"   完整响应已保存: debug_download_api.json")

    except Exception as e:
        print(f"   ❌ 错误: {str(e)}")
        results['download_api'] = {'error': str(e)}

    # 2. 尝试 /ks/note/view API（获取 HTML 内容）
    print(f"\n📍 API 2: /ks/note/view")
    print("-" * 70)
    try:
        url = f"{migrator.kapi_url}/ks/note/view/{migrator.kb_guid}/{note_guid}"
        response = migrator.session.get(url, timeout=30)

        if response.status_code == 200:
            try:
                data = response.json()
                result = data.get('result', data)
                html_content = result.get('body') or result.get('html')

                print(f"   HTTP 状态码: {response.status_code}")
                print(f"   返回码: {data.get('return_code', data.get('returnCode'))}")
                print(f"   HTML 长度: {len(html_content) if html_content else 0} 字符")

                # 提取图片引用
                if html_content:
                    import re
                    image_refs = re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', html_content)
                    print(f"   HTML 中的图片引用: {len(image_refs)} 个")

                    if image_refs:
                        print(f"   图片引用示例（前 3 个）:")
                        for ref in image_refs[:3]:
                            print(f"      - {ref[:80]}...")

                results['view_api'] = {
                    'status': response.status_code,
                    'html_length': len(html_content) if html_content else 0,
                    'image_refs_count': len(image_refs) if html_content else 0
                }

                # 保存完整响应
                with open('debug_view_api.json', 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                print(f"   完整响应已保存: debug_view_api.json")

            except Exception as json_err:
                print(f"   ⚠️  JSON 解析失败: {json_err}")
                print(f"   响应内容（前 200 字符）: {response.text[:200]}")
                results['view_api'] = {'error': 'JSON parse failed'}
        else:
            print(f"   ❌ HTTP {response.status_code}")
            results['view_api'] = {'error': f'HTTP {response.status_code}'}

    except Exception as e:
        print(f"   ❌ 错误: {str(e)}")
        results['view_api'] = {'error': str(e)}

    # 3. 尝试 /ks/resource/list API（如果存在）
    print(f"\n📍 API 3: /ks/resource/list（尝试备用端点）")
    print("-" * 70)
    try:
        url = f"{migrator.kapi_url}/ks/resource/list/{migrator.kb_guid}/{note_guid}"
        response = migrator.session.get(url, timeout=30)

        print(f"   HTTP 状态码: {response.status_code}")

        if response.status_code == 200:
            try:
                data = response.json()
                print(f"   返回码: {data.get('return_code', data.get('returnCode'))}")

                result = data.get('result', data)
                if isinstance(result, list):
                    print(f"   资源数量: {len(result)}")
                    if result:
                        print(f"   资源示例（前 3 个）:")
                        for res in result[:3]:
                            print(f"      - {res}")

                results['resource_list_api'] = {
                    'status': response.status_code,
                    'exists': True
                }

                with open('debug_resource_list.json', 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                print(f"   完整响应已保存: debug_resource_list.json")

            except Exception as json_err:
                print(f"   ⚠️  JSON 解析失败: {json_err}")
                results['resource_list_api'] = {'error': 'JSON parse failed'}
        else:
            print(f"   ℹ️  端点不存在或无权限")
            results['resource_list_api'] = {'exists': False}

    except Exception as e:
        print(f"   ℹ️  端点不可用: {str(e)}")
        results['resource_list_api'] = {'error': str(e)}

    # 4. 分析总结
    print(f"\n{'='*70}")
    print(f"📊 诊断总结")
    print(f"{'='*70}\n")

    download_resources = results.get('download_api', {}).get('resources_count', 0)
    view_images = results.get('view_api', {}).get('image_refs_count', 0)

    print(f"资源对比：")
    print(f"   /ks/note/download API 返回资源: {download_resources} 个")
    print(f"   HTML 内容中的图片引用: {view_images} 个\n")

    if download_resources == 0 and view_images > 0:
        print(f"⚠️  问题确认：")
        print(f"   API 没有返回图片资源，但 HTML 中有 {view_images} 个图片引用")
        print(f"   这是为知笔记 API 的缺陷\n")

        print(f"💡 可能的原因：")
        print(f"   1. API 版本问题：当前使用的 API 版本可能不支持某些笔记类型")
        print(f"   2. 权限问题：某些笔记可能需要特殊权限才能获取资源")
        print(f"   3. 笔记类型：这些可能是特殊类型的笔记（如协作笔记、加密笔记）")
        print(f"   4. 服务器问题：为知笔记服务器可能对某些笔记返回不完整的数据\n")

        print(f"🔧 可能的解决方案：")
        print(f"   1. 尝试其他 API 端点（如已尝试的 /ks/resource/list）")
        print(f"   2. 直接从 HTML 中提取图片 URL 并下载")
        print(f"   3. 使用网页版 WizNote 抓取图片")
        print(f"   4. 联系为知笔记官方反馈此问题")

    elif download_resources > 0:
        print(f"✅ API 正常返回了 {download_resources} 个资源")

    # 保存诊断报告
    report_file = 'api_diagnosis_report.json'
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump({
            'note_title': note_title,
            'note_guid': note_guid,
            'timestamp': datetime.now().isoformat(),
            'results': results
        }, f, indent=2, ensure_ascii=False)

    print(f"\n📄 诊断报告已保存: {report_file}\n")

    return results


def main():
    parser = argparse.ArgumentParser(
        description="深度 API 诊断工具 - 分析为什么某些笔记的图片无法获取"
    )

    parser.add_argument(
        '--note', '-n',
        required=True,
        help='要诊断的笔记标题（或部分标题）'
    )

    args = parser.parse_args()

    print("="*70)
    print("🔬 深度 API 诊断工具")
    print("="*70)
    print()

    # 登录
    u = input("📧 Email: ")
    p = getpass.getpass("🔑 Password: ")
    print()

    migrator = WizMigrator(u, p)
    success, error = migrator.login()

    if not success:
        print(f"❌ 登录失败: {error}")
        return

    # 搜索笔记
    print(f"🔍 搜索笔记: {args.note}\n")

    list_url = f"{migrator.kapi_url}/ks/note/list/category/{migrator.kb_guid}"
    params = {
        "category": "/",
        "start": 0,
        "count": 1000,
        "with_abstract": 0,
        "order": "created-desc"
    }

    response = migrator.session.get(list_url, params=params, timeout=30)
    data = response.json()

    if data.get('return_code') != 200 and data.get('returnCode') != 200:
        print(f"❌ 搜索失败")
        return

    notes = data.get('result', [])

    # 查找匹配的笔记
    target_note = None
    for note in notes:
        title = note.get('title') or note.get('documentTitle') or note.get('docTitle')
        if title and args.note in title:
            target_note = note
            break

    if not target_note:
        print(f"❌ 未找到笔记: {args.note}")
        return

    note_guid = target_note.get('guid') or target_note.get('documentGuid')
    note_title = target_note.get('title') or target_note.get('documentTitle')

    # 执行诊断
    analyze_note_apis(migrator, note_guid, note_title)


if __name__ == "__main__":
    main()
