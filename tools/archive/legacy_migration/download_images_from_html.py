#!/usr/bin/env python3
"""
从 HTML 中提取并下载图片 - 绕过 API 资源列表限制

功能：
  - 从笔记的 HTML 内容中提取图片 URL
  - 直接下载图片（不依赖 resources API）
  - 保存到对应的 _files 文件夹
  - 生成下载报告

使用方法：
    # 修复所有缺失图片的笔记
    python3 tools/download_images_from_html.py

    # 只修复特定笔记
    python3 tools/download_images_from_html.py --note "智能制造MES拆解"

    # 干运行模式（只显示将要下载的图片）
    python3 tools/download_images_from_html.py --dry-run
"""

import sys
import re
import getpass
import argparse
from pathlib import Path
from datetime import datetime
from urllib.parse import urljoin, urlparse

sys.path.insert(0, str(Path(__file__).parent))

try:
    from wiznote_downloader import WizMigrator
    IMPORT_SUCCESS = True
except ImportError:
    IMPORT_SUCCESS = False
    print("❌ 无法导入 wiznote_downloader")
    sys.exit(1)


def extract_images_from_html(html_content, kapi_url, kb_guid, note_guid):
    """从 HTML 内容中提取图片 URL"""

    # 提取所有 img 标签的 src
    img_srcs = re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', html_content)

    image_urls = []

    for src in img_srcs:
        # 处理相对路径
        if src.startswith('index_files/'):
            # 本地相对路径，转换为 API URL
            # 例如：index_files/abc.png -> /ks/resource/...
            resource_name = src.replace('index_files/', '')
            # 尝试构建资源 URL
            url = f"{kapi_url}/ks/resource/{kb_guid}/{note_guid}/{resource_name}"
            image_urls.append((resource_name, url))

        elif src.startswith('http://') or src.startswith('https://'):
            # 绝对 URL
            # 提取文件名
            parsed = urlparse(src)
            filename = Path(parsed.path).name
            image_urls.append((filename, src))

        elif src.startswith('/'):
            # 服务器绝对路径
            url = urljoin(kapi_url, src)
            filename = Path(src).name
            image_urls.append((filename, url))

        else:
            # 其他相对路径
            resource_name = Path(src).name
            url = f"{kapi_url}/ks/resource/{kb_guid}/{note_guid}/{resource_name}"
            image_urls.append((resource_name, url))

    return image_urls


def download_image_from_markdown(migrator, note, download_dir):
    """从 Markdown 文件中提取资源 ID 并下载图片"""

    note_guid = note.get('guid') or note.get('documentGuid') or note.get('docGuid')
    note_title = note.get('title') or note.get('documentTitle') or note.get('docTitle') or 'Untitled'

    # 调试：打印第一个笔记的所有字段
    if not hasattr(download_image_from_markdown, 'debug_printed'):
        print(f"\n   🔍 调试：笔记对象字段")
        print(f"      可用字段: {list(note.keys())}")
        print(f"      GUID 尝试: guid={note.get('guid')}, documentGuid={note.get('documentGuid')}, docGuid={note.get('docGuid')}")
        print(f"      最终 GUID: {note_guid}\n")
        download_image_from_markdown.debug_printed = True

    # 获取笔记的分类路径
    category = note.get('category', note.get('documentCategory', '/'))
    rel_path = category.strip('/')

    # 构建 Markdown 文件路径
    output_dir = Path(download_dir) / rel_path
    md_file = output_dir / f"{migrator.sanitize_filename(note_title)}.md"
    files_dir = output_dir / f"{migrator.sanitize_filename(note_title)}_files"

    if not md_file.exists():
        return None  # Markdown 文件不存在

    # 读取 Markdown 内容
    with open(md_file, 'r', encoding='utf-8', errors='ignore') as f:
        md_content = f.read()

    # 提取图片引用（Markdown 格式: ![alt](resource_id.png)）
    image_refs = re.findall(r'!\[.*?\]\((.*?)\)', md_content)

    # 过滤出资源 ID（为知笔记格式的资源 ID）
    resource_ids = []
    for ref in image_refs:
        # 跳过已下载的本地路径
        if ref.startswith('./') or ref.startswith('../') or '_files/' in ref:
            continue

        # 跳过 HTTP URL
        if ref.startswith('http://') or ref.startswith('https://'):
            continue

        # 跳过 WikiLinks
        if ref.startswith('[[') and ref.endswith(']]'):
            continue

        # 检查是否是为知笔记的资源 ID 格式
        # 通常是：随机字符串.扩展名
        if re.match(r'^[a-zA-Z0-9_\-]+\.(png|jpg|jpeg|gif|webp|bmp|svg)$', ref, re.IGNORECASE):
            resource_ids.append(ref)

    if not resource_ids:
        return None

    # 创建 _files 文件夹
    files_dir.mkdir(exist_ok=True)

    # 尝试从 HTML 中获取完整的图片 URL
    html_image_urls = extract_images_from_html_content(migrator, note_guid, note_title)

    # 调试：打印第一个笔记的 HTML 提取结果
    if not hasattr(download_image_from_markdown, 'html_debug_printed'):
        print(f"\n   🔍 调试：HTML 提取结果")
        print(f"      资源 ID 数量: {len(resource_ids)}")
        print(f"      HTML 图片 URL 数量: {len(html_image_urls)}")
        if html_image_urls:
            print(f"      前 3 个 URL:")
            for filename, url in html_image_urls[:3]:
                print(f"        - {filename}: {url[:80]}...")
        download_image_from_markdown.html_debug_printed = True

    # 如果 HTML 中有图片 URL，使用它们
    if html_image_urls:
        # 构建资源 ID 到 URL 的映射
        resource_url_map = {}
        for filename, url in html_image_urls:
            resource_url_map[filename] = url

        # 下载图片
        downloaded = 0
        failed = 0

        for resource_id in resource_ids:
            img_path = files_dir / resource_id

            if img_path.exists():
                downloaded += 1
                continue

            # 使用 HTML 中的 URL 或回退到资源 API
            if resource_id in resource_url_map:
                resource_url = resource_url_map[resource_id]
            else:
                # 回退方案：尝试资源 API
                resource_url = f"{migrator.kapi_url}/ks/resource/{migrator.kb_guid}/{note_guid}/{resource_id}"

            # 下载图片
            try:
                success = migrator.download_file(resource_url, str(img_path))
                if success:
                    downloaded += 1
                else:
                    failed += 1
            except Exception as e:
                failed += 1

        return {
            'title': note_title,
            'images_found': len(resource_ids),
            'images_downloaded': downloaded,
            'images_failed': failed
        }

    # 如果 HTML 中没有图片 URL，尝试资源 API
    downloaded = 0
    failed = 0

    # 只在第一张图片时打印调试信息
    debug_printed = False

    for resource_id in resource_ids:
        img_path = files_dir / resource_id

        if img_path.exists():
            downloaded += 1
            continue

        # 构建资源下载 URL
        # 为知笔记资源 API: /ks/resource/{kb_guid}/{note_guid}/{resource_id}
        resource_url = f"{migrator.kapi_url}/ks/resource/{migrator.kb_guid}/{note_guid}/{resource_id}"

        # 第一张图片打印调试信息
        if not debug_printed:
            print(f"   🔍 测试资源 API: {resource_url}")
            try:
                test_response = migrator.session.head(resource_url, timeout=10)
                print(f"      HTTP {test_response.status_code}")
                if test_response.status_code != 200:
                    # 如果 HEAD 失败，尝试 GET 看详细错误
                    test_response = migrator.session.get(resource_url, timeout=10)
                    print(f"      响应: {test_response.text[:200]}")
            except Exception as e:
                print(f"      错误: {str(e)}")
            debug_printed = True

        # 下载图片
        try:
            success = migrator.download_file(resource_url, str(img_path))
            if success:
                downloaded += 1
            else:
                failed += 1
                print(f"      ❌ 下载失败: {resource_id}")
        except Exception as e:
            failed += 1
            print(f"      ❌ 下载异常: {resource_id}")
            print(f"         错误: {str(e)}")

    return {
        'title': note_title,
        'images_found': len(resource_ids),
        'images_downloaded': downloaded,
        'images_failed': failed
    }


def extract_images_from_html_content(migrator, note_guid, note_title=""):
    """从笔记的 HTML 内容中提取图片 URL"""

    try:
        url = f"{migrator.kapi_url}/ks/note/view/{migrator.kb_guid}/{note_guid}"

        # 调试：打印第一个笔记的 API 调用
        if not hasattr(extract_images_from_html_content, 'debug_printed'):
            print(f"\n   🔍 调试：调用 /ks/note/view API")
            print(f"      URL: {url}")
            extract_images_from_html_content.debug_printed = True

        response = migrator.session.get(url, timeout=30)

        # 调试：打印第一个笔记的 API 响应
        if not hasattr(extract_images_from_html_content, 'response_debug_printed'):
            print(f"      HTTP 状态码: {response.status_code}")
            extract_images_from_html_content.response_debug_printed = True

        if response.status_code != 200:
            if not hasattr(extract_images_from_html_content, 'error_debug_printed'):
                print(f"      ❌ API 返回非 200 状态码，跳过")
                extract_images_from_html_content.error_debug_printed = True
            return []

        try:
            data = response.json()

            # 调试：保存第一个笔记的完整响应
            if not hasattr(extract_images_from_html_content, 'saved_response'):
                import json
                with open('debug_note_view_api.json', 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                print(f"      ✅ 完整响应已保存: debug_note_view_api.json")
                extract_images_from_html_content.saved_response = True

            result = data.get('result', data)

            # 调试：打印 result 的字段
            if not hasattr(extract_images_from_html_content, 'result_debug_printed'):
                print(f"      result 类型: {type(result)}")
                if isinstance(result, dict):
                    print(f"      result 字段: {list(result.keys())}")
                extract_images_from_html_content.result_debug_printed = True

            html_content = result.get('body') or result.get('html')

            # 调试：打印第一个笔记的 HTML 内容
            if not hasattr(extract_images_from_html_content, 'html_debug_printed'):
                print(f"      HTML 长度: {len(html_content) if html_content else 0} 字符")
                if html_content:
                    # 提取前 200 个字符
                    preview = html_content[:200].replace('\n', ' ')
                    print(f"      HTML 预览: {preview}...")
                else:
                    print(f"      ⚠️ HTML 内容为空")
                extract_images_from_html_content.html_debug_printed = True

            if not html_content:
                return []

            # 提取所有 img 标签的 src
            img_srcs = re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', html_content)

            image_urls = []

            for src in img_srcs:
                # 处理相对路径
                if src.startswith('index_files/'):
                    # 本地相对路径，转换为 API URL
                    resource_name = src.replace('index_files/', '')
                    url = f"{migrator.kapi_url}/ks/resource/{migrator.kb_guid}/{note_guid}/{resource_name}"
                    image_urls.append((resource_name, url))

                elif src.startswith('http://') or src.startswith('https://'):
                    # 绝对 URL
                    parsed = urlparse(src)
                    filename = Path(parsed.path).name
                    image_urls.append((filename, src))

                elif src.startswith('/'):
                    # 服务器绝对路径
                    url = urljoin(migrator.kapi_url, src)
                    filename = Path(src).name
                    image_urls.append((filename, url))

                else:
                    # 其他相对路径
                    resource_name = Path(src).name
                    url = f"{migrator.kapi_url}/ks/resource/{migrator.kb_guid}/{note_guid}/{resource_name}"
                    image_urls.append((resource_name, url))

            return image_urls

        except Exception as json_err:
            if not hasattr(extract_images_from_html_content, 'json_error_printed'):
                print(f"      ❌ JSON 解析或处理失败: {json_err}")
                print(f"      响应内容（前 200 字符）: {response.text[:200]}")
                extract_images_from_html_content.json_error_printed = True
            return []

    except Exception as outer_err:
        if not hasattr(extract_images_from_html_content, 'outer_error_printed'):
            print(f"      ❌ 外层异常: {outer_err}")
            extract_images_from_html_content.outer_error_printed = True
        return []


def main():
    parser = argparse.ArgumentParser(
        description="从 HTML 中提取并下载图片 - 绕过 API 资源列表限制"
    )

    parser.add_argument(
        '--download-dir', '-d',
        default='wiznote_download',
        help='下载目录（默认: wiznote_download）'
    )

    parser.add_argument(
        '--note', '-n',
        help='只修复特定笔记（笔记标题或部分标题）'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='干运行模式（只显示将要下载的图片）'
    )

    parser.add_argument(
        '--missing-list',
        default='missing_resources_report.txt',
        help='缺失资源报告文件（默认: missing_resources_report.txt）'
    )

    parser.add_argument(
        '--email',
        help='WizNote 登录邮箱'
    )

    parser.add_argument(
        '--password',
        help='WizNote 登录密码'
    )

    args = parser.parse_args()

    print("="*70)
    print("🖼️  从 HTML 中提取并下载图片")
    print("="*70)
    print()

    # 检查缺失资源报告
    missing_file = Path(args.missing_list)
    if not missing_file.exists():
        print("❌ 未找到缺失资源报告")
        print("💡 请先运行: python3 tools/fix_missing_resources.py --scan-only")
        return

    # 登录
    print("🔐 登录 WizNote...")
    if args.email and args.password:
        u = args.email
        p = args.password
        print(f"📧 使用命令行参数登录: {u}")
    else:
        u = input("📧 Email: ")
        p = getpass.getpass("🔑 Password: ")
    print()

    migrator = WizMigrator(u, p)
    success, error = migrator.login()

    if not success:
        print(f"❌ 登录失败: {error}")
        return

    print("✅ 登录成功\n")

    # 获取所有分类
    print("📋 获取分类列表...")
    try:
        # 方法 1: /ks/category/all
        categories = []
        url = f"{migrator.kapi_url}/ks/category/all/{migrator.kb_guid}"
        response = migrator.session.get(url, timeout=(10, 30))

        if response.status_code == 200:
            data = response.json()
            if data.get('return_code') == 200 or data.get('returnCode') == 200:
                categories = data.get('result', [])
                print(f"✅ 找到 {len(categories)} 个分类\n")

        if not categories:
            # 方法 2: /ks/category/list
            url = f"{migrator.kapi_url}/ks/category/list/{migrator.kb_guid}"
            response = migrator.session.get(url, timeout=(10, 30))

            if response.status_code == 200:
                data = response.json()
                if data.get('return_code') == 200 or data.get('returnCode') == 200:
                    categories = data.get('result', [])
                    print(f"✅ 找到 {len(categories)} 个分类\n")

        if not categories:
            print("⚠️  未获取到分类列表，使用根目录")
            categories = ['/']

    except Exception as e:
        print(f"⚠️  获取分类失败: {str(e)}，使用根目录")
        categories = ['/']

    # 获取笔记列表（扫描每个分类）
    print("📋 扫描笔记列表...")
    all_notes = []

    for category in categories:
        if isinstance(category, str):
            cat_path = category
        elif isinstance(category, dict):
            cat_path = category.get('key') or category.get('category') or category.get('path') or '/'
        else:
            continue

        # 分页获取此分类下的笔记
        start = 0
        page_size = 100

        while True:
            try:
                list_url = f"{migrator.kapi_url}/ks/note/list/category/{migrator.kb_guid}"
                params = {
                    "category": cat_path,
                    "start": start,
                    "count": page_size,
                    "with_abstract": 0,
                    "order": "created-desc"
                }

                response = migrator.session.get(list_url, params=params, timeout=(10, 30))

                if response.status_code != 200:
                    break

                data = response.json()
                return_code = data.get('return_code', data.get('returnCode'))

                if return_code != 200:
                    break

                notes = data.get('result', [])
                if not notes:
                    break

                all_notes.extend(notes)
                print(f"   已扫描 {len(all_notes)} 个笔记...", end='\r')

                if len(notes) < page_size:
                    break

                start += page_size

            except Exception:
                break

    print(f"\n✅ 共找到 {len(all_notes)} 个笔记\n")

    # 解析缺失列表
    missing_notes = []
    with open(missing_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    for line in lines:
        parts = line.strip().split()
        if len(parts) >= 4:
            file_path = parts[0]
            if file_path.endswith('.md'):
                missing_notes.append(file_path)

    print(f"📊 需要修复 {len(missing_notes)} 个笔记\n")

    if args.dry_run:
        print("🔍 干运行模式 - 只显示将要处理的笔记\n")

    # 处理笔记
    results = []
    processed = 0

    for note in all_notes:
        note_title = note.get('title') or note.get('documentTitle')
        note_guid = note.get('guid') or note.get('documentGuid')
        category = note.get('category', note.get('documentCategory', '/'))
        rel_path = category.strip('/')

        # 构建相对路径
        safe_title = migrator.sanitize_filename(note_title)
        note_path = f"{rel_path}/{safe_title}.md" if rel_path else f"{safe_title}.md"

        # 检查是否在缺失列表中
        is_missing = any(note_path in mn or mn in note_path for mn in missing_notes)

        if not is_missing:
            continue

        # 如果指定了特定笔记，只处理该笔记
        if args.note and args.note not in note_title:
            continue

        processed += 1

        print(f"[{processed}/{len(missing_notes)}] 处理: {note_title}")

        if args.dry_run:
            continue

        # 下载图片
        result = download_image_from_markdown(migrator, note, args.download_dir)

        if result:
            results.append(result)
            if result['images_downloaded'] > 0:
                print(f"   ✅ 下载 {result['images_downloaded']}/{result['images_found']} 张图片")
            if result['images_failed'] > 0:
                print(f"   ⚠️  失败 {result['images_failed']} 张")
        else:
            print(f"   ℹ️  未找到图片")

    # 生成报告
    print(f"\n{'='*70}")
    print(f"📊 下载统计")
    print(f"{'='*70}\n")

    total_found = sum(r['images_found'] for r in results)
    total_downloaded = sum(r['images_downloaded'] for r in results)
    total_failed = sum(r['images_failed'] for r in results)

    print(f"处理笔记: {len(results)} 个")
    print(f"发现图片: {total_found} 张")
    print(f"成功下载: {total_downloaded} 张")
    print(f"下载失败: {total_failed} 张\n")

    if total_downloaded > 0:
        print(f"✅ 成功从 HTML 中提取并下载了 {total_downloaded} 张图片！\n")

        # 保存报告
        report_file = 'html_image_download_report.md'
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("# 从 HTML 中提取图片下载报告\n\n")
            f.write(f"> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("---\n\n")
            f.write("## 统计信息\n\n")
            f.write(f"- 处理笔记: {len(results)} 个\n")
            f.write(f"- 发现图片: {total_found} 张\n")
            f.write(f"- 成功下载: {total_downloaded} 张\n")
            f.write(f"- 下载失败: {total_failed} 张\n\n")

            if results:
                f.write("## 笔记详情\n\n")
                for r in results:
                    f.write(f"- **{r['title']}**: {r['images_downloaded']}/{r['images_found']} 张\n")

        print(f"📄 报告已保存: {report_file}\n")

    print(f"💡 下一步：")
    print(f"   1. 运行扫描工具验证结果：")
    print(f"      python3 tools/fix_missing_resources.py --scan-only\n")
    print(f"   2. 检查失败的图片（如有）并手动处理\n")


if __name__ == "__main__":
    main()
