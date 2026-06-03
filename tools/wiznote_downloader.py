import requests
import os
import json
import zipfile
import io
import getpass
from markdownify import markdownify as md
import shutil
from pathlib import Path
import time
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import argparse
import ssl
import certifi

try:
    from websocket import create_connection
    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False
    print("⚠️  警告: 未安装 websocket-client，协作笔记功能将不可用")
    print("   安装命令: pip3 install websocket-client")

# 导入协作笔记解析器
try:
    from collaboration_note_parser import parse_collaboration_note
    COLLABORATION_PARSER_AVAILABLE = True
except ImportError:
    COLLABORATION_PARSER_AVAILABLE = False
    print("⚠️  警告: 协作笔记解析器不可用")

# Default Configuration (可通过命令行参数覆盖)
WIZ_USER_ID = ""
WIZ_PASSWORD = ""
AS_URL = "https://as.wiz.cn"
DEFAULT_MAX_RETRIES = 2
DEFAULT_TIMEOUT = 15
DEFAULT_MAX_WORKERS = 5
DEFAULT_CONNECT_TIMEOUT = 10

class WizMigrator:
    def __init__(self, user_id, password, max_workers=DEFAULT_MAX_WORKERS,
                 max_retries=DEFAULT_MAX_RETRIES, timeout=DEFAULT_TIMEOUT,
                 connect_timeout=DEFAULT_CONNECT_TIMEOUT,
                 on_progress=None):
        self.user_id = user_id
        self.password = password
        self.token = None
        self.kb_guid = None
        self.kapi_url = None
        self.user_guid = None  # 用户 GUID（用于 WebSocket 认证）
        self.session = requests.Session()
        self.processed_count = 0
        self.success_count = 0
        self.known_folders = set() # Track folders to avoid loops

        # 进度回调
        self.on_progress = on_progress

        # 图片统计
        self.total_images_found = 0      # 发现的图片总数
        self.total_images_downloaded = 0  # 成功下载的图片数

        # 附件统计
        self.total_attachments_found = 0      # 发现的附件总数
        self.total_attachments_downloaded = 0  # 成功下载的附件数

        # 失败记录（用于生成报告）
        self.failed_notes = []
        self.failed_images = []
        self.failed_attachments = []
        self.collaborative_notes = []  # 协作笔记（需要特殊处理）
        self.encrypted_notes = []  # 加密笔记（需要用户解密）

        self.lock = threading.Lock()  # 线程锁，保护计数器

        # 配置参数
        self.max_workers = max_workers
        self.max_retries = max_retries
        self.timeout = timeout
        self.connect_timeout = connect_timeout

        # Add headers to mimic browser
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
        })

    def login(self):
        """
        Login to WizNote Account Server

        Returns:
            tuple: (success: bool, error_message: str or None)
        """
        print(f"Logging in as {self.user_id}...")
        try:
            login_url = f"{AS_URL}/as/user/login"
            payload = {
                "user_id": self.user_id,
                "password": self.password,
                "client_type": "web",
                "client_version": "4.0.0"
            }

            response = self.session.post(login_url, data=payload)
            data = response.json()

            if data.get('return_code') != 200 and data.get('returnCode') != 200:
                error_msg = data.get('return_message') or data.get('returnMessage') or "登录失败"
                print(f"Login failed: {error_msg}")
                return False, error_msg

            result = data.get('result', data)
            self.token = result.get('token')
            self.kb_guid = result.get('kb_guid') or result.get('kbGuid')
            self.kapi_url = result.get('kapi_url') or result.get('kbServer') or 'https://ks.wiz.cn'
            self.user_guid = result.get('user_guid') or result.get('userGuid')  # 保存 user_guid

            if not self.token or not self.kb_guid:
                error_msg = "登录失败：服务器未返回必要信息"
                print(f"Login failed: {error_msg}")
                return False, error_msg

            print(f"Login successful!")
            print(f"KB GUID: {self.kb_guid}")

            self.session.headers.update({
                "X-Wiz-Token": self.token
            })
            return True, None

        except Exception as e:
            error_msg = f"登录出错: {str(e)}"
            print(f"Error during login: {str(e)}")
            return False, error_msg

    def sanitize_filename(self, name):
        """Make filename safe for filesystem"""
        safe = re.sub(r'[\\/*?:"<>|]', "_", name)
        safe = safe.strip()
        if not safe:
            safe = "Untitled"
        return safe

    def clean_opening_title(self, content, note_title):
        """
        Remove duplicated opening titles left in note bodies after export.

        Some WizNote notes start with one of the following immediately after the
        generated frontmatter:
        - a Markdown heading matching the note title
        - a plain text line matching the note title
        - a placeholder '无标题'
        """
        if not content:
            return content

        lines = content.splitlines(keepends=True)
        idx = 0

        while idx < len(lines) and not lines[idx].strip():
            idx += 1

        def is_duplicate_opening(line):
            stripped = line.strip()
            if not stripped:
                return False
            if stripped == "无标题":
                return True
            if stripped == note_title:
                return True

            heading = re.match(r'^#{1,6}\s+(.*)$', stripped)
            return bool(heading and heading.group(1).strip() == note_title)

        while idx < len(lines) and is_duplicate_opening(lines[idx]):
            idx += 1
            while idx < len(lines) and not lines[idx].strip():
                idx += 1

        return "".join(lines[idx:]).lstrip("\n")

    def get_note_resources(self, doc_guid):
        """
        获取笔记的资源列表（图片等）
        返回: {资源名: 下载URL}
        """
        try:
            url = f"{self.kapi_url}/ks/note/download/{self.kb_guid}/{doc_guid}"
            params = {
                "downloadInfo": "0",
                "downloadData": "1"
            }

            response = self.session.get(url, params=params)
            data = response.json()

            if data.get('returnCode') != 200 and data.get('return_code') != 200:
                return {}

            result = data.get('result', data)
            resources = result.get('resources', [])

            # 构建资源映射 {name: url}
            resources_map = {}
            for res in resources:
                if 'name' in res and 'url' in res:
                    resources_map[res['name']] = res['url']

            return resources_map

        except Exception as e:
            return {}

    def get_note_attachments(self, doc_guid):
        """
        获取笔记的附件列表
        返回: 附件信息列表
        """
        try:
            url = f"{self.kapi_url}/ks/note/attachments/{self.kb_guid}/{doc_guid}"
            params = {
                'extra': '1',
                'clientType': 'web',
                'clientVersion': '4.0',
                'lang': 'zh-cn'
            }

            response = self.session.get(url, params=params, timeout=(self.connect_timeout, self.timeout))

            # 调试信息
            if response.status_code != 200:
                print(f"    ⚠️  附件 API 返回 HTTP {response.status_code}")
                return []

            data = response.json()
            code = data.get('returnCode', data.get('return_code'))

            if code != 200:
                print(f"    ⚠️  附件 API 返回错误码: {code}")
                return []

            attachments = data.get('result', [])
            return attachments

        except Exception as e:
            print(f"    ❌ 获取附件失败: {str(e)}")
            return []

    def get_collaboration_token(self, doc_guid):
        """
        获取协作笔记的 editor token
        返回: editor_token 或 None
        """
        if not WEBSOCKET_AVAILABLE:
            return None

        try:
            url = f"{self.kapi_url}/ks/note/{self.kb_guid}/{doc_guid}/tokens"
            response = self.session.post(url, timeout=(self.connect_timeout, self.timeout))

            if response.status_code == 200:
                data = response.json()
                if data.get('return_code') == 200 or data.get('returnCode') == 200:
                    result = data.get('result', {})
                    editor_token = result.get('editorToken') or result.get('token')
                    return editor_token
        except Exception as e:
            print(f"    ❌ 获取协作 token 失败: {str(e)}")

        return None

    def get_collaboration_content(self, doc_guid):
        """
        通过 WebSocket 获取协作笔记内容（ShareJS 协议）
        返回: (markdown_content, image_resources) 或 (None, None)
        """
        if not WEBSOCKET_AVAILABLE:
            print("    ⚠️  websocket-client 未安装，无法获取协作笔记")
            return None, None

        if not COLLABORATION_PARSER_AVAILABLE:
            print("    ⚠️  协作笔记解析器不可用")
            return None, None

        # 获取 editor token
        editor_token = self.get_collaboration_token(doc_guid)
        if not editor_token:
            print("    ❌ 无法获取协作笔记 token")
            return None, None

        ws = None
        try:
            # 构建 WebSocket URL
            from urllib.parse import urlparse
            parsed = urlparse(self.kapi_url)
            ws_domain = parsed.netloc
            ws_url = f"wss://{ws_domain}/editor/{self.kb_guid}/{doc_guid}"

            print(f"    🔗 连接 WebSocket: {ws_url}")

            # 创建 WebSocket 连接
            ssl_context = ssl.create_default_context()
            ssl_context.load_verify_locations(certifi.where())

            ws = create_connection(
                ws_url,
                sslopt={"cert_reqs": ssl.CERT_REQUIRED, "ssl_version": ssl.PROTOCOL_TLS_CLIENT, "check_hostname": True},
                header={"Cookie": f"x-live-editor-token={editor_token}"},
                timeout=30
            )

            # ShareJS 协议握手请求
            hs_request = {
                "a": "hs",
                "id": None,
                "auth": {
                    "appId": self.kb_guid,
                    "docId": doc_guid,
                    "userId": self.user_guid,
                    "permission": "w",
                    "token": editor_token
                }
            }

            # 获取内容请求
            f_request = {
                "a": "f",
                "c": self.kb_guid,
                "d": doc_guid,
                "v": None
            }

            # 执行 3 次握手（参考实现不验证响应内容，只接收即可）
            hs_msg = json.dumps(hs_request)
            for i in range(3):
                ws.send(hs_msg)
                try:
                    result = ws.recv()
                    # 只验证是否为有效 JSON，不验证具体内容
                    try:
                        response_data = json.loads(result)
                        # ShareJS 可能返回 {"a":"init"} 或 {"a":"hs"} 等多种格式
                        # 参考实现中不验证这些，继续发送后续请求即可
                    except json.JSONDecodeError:
                        print(f"    ⚠️  握手 {i+1} 响应不是有效 JSON")
                        return None, None
                except Exception as recv_error:
                    print(f"    ⚠️  握手 {i+1} 接收超时: {str(recv_error)}")
                    return None, None

            # 发送获取请求
            fetch_msg = json.dumps(f_request)
            ws.send(fetch_msg)

            # 接收确认响应（第一次）
            try:
                ack_response = ws.recv()
                print(f"    ✅ 收到确认响应: {ack_response[:100]}")
            except Exception as recv_error:
                print(f"    ⚠️  获取确认响应超时: {str(recv_error)}")
                return None, None

            # 接收实际内容（第二次）
            try:
                content_response = ws.recv()
            except Exception as recv_error:
                print(f"    ⚠️  获取内容超时: {str(recv_error)}")
                return None, None

            # 验证响应不为空
            if not content_response or content_response.strip() == '':
                print("    ⚠️  服务器返回空响应")
                return None, None

            # 调试输出：显示原始响应
            print(f"    📦 收到响应（长度: {len(content_response)} 字节）")
            print(f"    🔍 响应预览: {content_response[:300]}")

            # 解析协作笔记内容
            markdown_content = parse_collaboration_note(content_response)
            if not markdown_content:
                print("    ⚠️  协作笔记内容解析失败")
                # 尝试手动解析看看数据结构
                try:
                    data = json.loads(content_response)
                    print(f"    🔍 JSON 结构: {list(data.keys())}")
                    if 'data' in data:
                        print(f"    🔍 data 字段结构: {list(data['data'].keys())}")
                except:
                    pass
                return None, None

            # 提取图片资源列表
            image_resources = {}
            try:
                data = json.loads(content_response)
                resources = data.get('data', {}).get('data', {}).get('resources', {})
                for res_name, res_info in resources.items():
                    if res_info.get('type', '').startswith('image/'):
                        image_resources[res_name] = {
                            'url': f"https://{ws_domain}/editor/{self.kb_guid}/{doc_guid}/resources/{res_name}",
                            'token': editor_token
                        }
            except:
                pass  # 图片提取失败不影响主要内容

            return markdown_content, image_resources

        except Exception as e:
            print(f"    ❌ WebSocket 获取失败: {str(e)}")
            return None, None
        finally:
            # 确保关闭连接
            if ws:
                try:
                    ws.close()
                except:
                    pass

    def download_collaboration_image(self, image_url, editor_token, output_path):
        """
        下载协作笔记的图片（需要特殊的 cookie 认证）
        """
        try:
            # 协作笔记图片需要 x-live-editor-token cookie
            headers = {
                "Cookie": f"x-live-editor-token={editor_token}"
            }

            response = self.session.get(
                image_url,
                headers=headers,
                timeout=(self.connect_timeout, self.timeout),
                stream=True
            )

            if response.status_code == 200:
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                with open(output_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                return True
        except Exception as e:
            print(f"    ❌ 协作图片下载失败: {str(e)}")

        return False

    def download_file(self, url, output_path, description="文件"):
        """
        下载文件到本地（支持重试和超时）
        """
        for attempt in range(self.max_retries):
            try:
                # 分离连接超时和读取超时
                response = self.session.get(
                    url,
                    timeout=(self.connect_timeout, self.timeout),
                    stream=True
                )
                response.raise_for_status()

                # 创建目录
                os.makedirs(os.path.dirname(output_path), exist_ok=True)

                # 下载文件
                with open(output_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)

                return True

            except requests.exceptions.Timeout:
                if attempt < self.max_retries - 1:
                    time.sleep(1)  # 短暂等待后重试
                else:
                    return False
            except Exception as e:
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)  # 指数退避
                else:
                    return False

        return False

    def process_note(self, note, output_base):
        """Download and convert a single note"""
        return self._process_note_internal(note, output_base)

    def _process_note_internal(self, note, output_base):
        """内部方法：实际处理笔记"""
        # Handle different field naming conventions (snake_case vs camelCase)
        note_guid = note.get('guid') or note.get('documentGuid') or note.get('docGuid')
        note_title = note.get('title') or note.get('documentTitle') or note.get('docTitle')
        note_type = note.get('type', note.get('documentType', 'document'))

        if not note_guid:
            return None

        if not note_title:
            note_title = "Untitled"

        # 检测是否为加密笔记
        is_encrypted = note.get('encrypted', note.get('isEncrypted', False))
        if isinstance(is_encrypted, str):
            is_encrypted = is_encrypted.lower() in ['true', '1', 'yes']
        elif isinstance(is_encrypted, int):
            is_encrypted = is_encrypted == 1

        if is_encrypted:
            category = note.get('category', note.get('documentCategory', '/'))
            rel_path = category.strip('/')
            output_dir = Path(output_base) / rel_path

            return {
                "status": "encrypted",
                "title": note_title,
                "note_guid": note_guid,
                "path": rel_path,
                "message": "加密笔记需要先在 WizNote 客户端中解密"
            }

        # 检测是否为 Lite/Markdown 笔记
        is_lite_note = note_type in ['lite', 'markdown'] or (note_type and 'lite' in note_type.lower())

        category = note.get('category', note.get('documentCategory', '/'))
        rel_path = category.strip('/')

        output_dir = Path(output_base) / rel_path
        output_dir.mkdir(parents=True, exist_ok=True)

        safe_title = self.sanitize_filename(note_title)
        md_file_path = output_dir / f"{safe_title}.md"

        if md_file_path.exists():
            return {"status": "skip", "title": safe_title}

        try:
            html_content = None
            images_found = 0
            images_downloaded = 0
            attachments_found = 0
            attachments_downloaded = 0
            assets_folder_name = f"{safe_title}_files"
            final_assets_path = output_dir / assets_folder_name
            failed_images_list = []  # 记录失败的图片
            failed_attachments_list = []  # 记录失败的附件

            # 方法 1: 尝试下载 ZIP（某些笔记支持）
            download_url = f"{self.kapi_url}/ks/note/download/{self.kb_guid}/{note_guid}"
            response = self.session.get(download_url, timeout=(self.connect_timeout, self.timeout))

            if response.status_code == 200 and response.content.startswith(b'PK'):
                # ZIP 下载成功
                temp_extract_dir = output_dir / f"_temp_{note_guid}"
                temp_extract_dir.mkdir(exist_ok=True)

                try:
                    with zipfile.ZipFile(io.BytesIO(response.content)) as z:
                        z.extractall(temp_extract_dir)

                    index_html = temp_extract_dir / "index.html"
                    if index_html.exists():
                        with open(index_html, 'r', encoding='utf-8', errors='ignore') as f:
                            html_content = f.read()

                        resource_dir = temp_extract_dir / "index_files"

                        if resource_dir.exists():
                            if final_assets_path.exists():
                                shutil.rmtree(final_assets_path)
                            shutil.move(str(resource_dir), str(final_assets_path))

                            # 统计图片和附件（区分文件类型）
                            image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg'}
                            # 递归查找所有文件（包括子目录）
                            all_files = [f for f in final_assets_path.rglob('*') if f.is_file()]

                            for file_path in all_files:
                                ext = file_path.suffix.lower()
                                if ext in image_extensions:
                                    images_found += 1
                                    images_downloaded += 1
                                else:
                                    # 其他文件算作附件
                                    attachments_found += 1
                                    attachments_downloaded += 1

                            # 替换路径
                            html_content = html_content.replace("index_files/", f"{assets_folder_name}/")

                finally:
                    if temp_extract_dir.exists():
                        shutil.rmtree(temp_extract_dir)

            # 方法 2: 如果 ZIP 失败，使用资源下载 API
            if not html_content:
                # 获取 HTML 内容
                view_url = f"{self.kapi_url}/ks/note/view/{self.kb_guid}/{note_guid}"
                resp = self.session.get(view_url, timeout=(self.connect_timeout, self.timeout))

                # 尝试 JSON 解析
                try:
                    data = resp.json()
                    result = data.get('result', data)

                    # 对于 Lite 笔记，内容可能直接是 Markdown
                    if is_lite_note:
                        html_content = result.get('body') or result.get('html') or result.get('text') or result.get('markdown')
                    else:
                        html_content = result.get('body') or result.get('html')
                except:
                    # 如果不是 JSON，检查是否是 RAW HTML
                    if resp.status_code == 200 and '<html' in resp.text.lower()[:200]:
                        html_content = resp.text

                if html_content:
                    # 资源文件夹（图片和附件都放在这里）
                    assets_folder_name = f"{safe_title}_files"
                    final_assets_path = output_dir / assets_folder_name

                    # 下载图片（使用线程池并发下载）
                    resources = self.get_note_resources(note_guid)
                    images_found = 0
                    images_downloaded = 0

                    if resources:
                        final_assets_path.mkdir(exist_ok=True)

                        # 过滤图片文件
                        image_resources = {
                            name: url for name, url in resources.items()
                            if any(name.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg'])
                        }

                        images_found = len(image_resources)

                        # 并发下载图片
                        with ThreadPoolExecutor(max_workers=5) as executor:
                            futures = {}
                            for img_name, img_url in image_resources.items():
                                img_path = final_assets_path / img_name
                                if not img_path.exists():
                                    future = executor.submit(self.download_file, img_url, str(img_path))
                                    futures[future] = (img_name, img_url)
                                else:
                                    # 图片已存在，计入成功
                                    images_downloaded += 1

                            # 等待所有下载完成
                            for future in as_completed(futures):
                                img_name, img_url = futures[future]
                                if future.result():
                                    images_downloaded += 1
                                else:
                                    # 记录失败的图片
                                    failed_images_list.append({
                                        "name": img_name,
                                        "url": img_url,
                                        "note": safe_title,
                                        "path": str(output_dir.relative_to(output_base))
                                    })

                        # 更新 HTML 中的图片路径
                        html_content = html_content.replace("index_files/", f"{assets_folder_name}/")

                    # 下载附件（使用线程池并发下载）
                    attachments = self.get_note_attachments(note_guid)
                    attachments_found = 0
                    attachments_downloaded = 0

                    if attachments:
                        attachments_found = len(attachments)

                        # 附件也保存在同一个资源文件夹中
                        if not final_assets_path.exists():
                            final_assets_path.mkdir(exist_ok=True)

                        # 并发下载附件
                        with ThreadPoolExecutor(max_workers=3) as executor:
                            futures = {}
                            for att in attachments:
                                # WizNote 附件使用 attGuid 字段
                                att_guid = att.get('attGuid')
                                att_name = att.get('name', 'unknown')

                                if not att_guid:
                                    print(f"    ⚠️  附件缺少 attGuid: {att_name}")
                                    failed_attachments_list.append({
                                        "name": att_name,
                                        "reason": "缺少 attGuid",
                                        "note": safe_title,
                                        "path": str(output_dir.relative_to(output_base))
                                    })
                                    continue

                                att_path = final_assets_path / att_name
                                if not att_path.exists():
                                    att_url = f"{self.kapi_url}/ks/attachment/download/{self.kb_guid}/{note_guid}/{att_guid}"
                                    future = executor.submit(self.download_file, att_url, str(att_path))
                                    futures[future] = (att_name, att_url)
                                else:
                                    # 附件已存在，计入成功
                                    attachments_downloaded += 1

                            # 等待所有下载完成
                            for future in as_completed(futures):
                                att_name, att_url = futures[future]
                                if future.result():
                                    attachments_downloaded += 1
                                else:
                                    # 记录失败的附件
                                    print(f"    ❌ 附件下载失败: {att_name}")
                                    failed_attachments_list.append({
                                        "name": att_name,
                                        "url": att_url,
                                        "note": safe_title,
                                        "path": str(output_dir.relative_to(output_base))
                                    })

            if not html_content:
                return {"status": "error", "title": safe_title, "error": "无法获取笔记内容"}

            # 检测是否为协作笔记（通过特征文本判断）
            is_collaborative = False
            collaborative_indicators = [
                "当前客户端版本较低，无法编辑协作笔记",
                "The current client version is too low to edit collaborative notes",
                "协作笔记",
                "collaborative notes",
                "请升级客户端",
                "upgrade the client"
            ]

            for indicator in collaborative_indicators:
                if indicator in html_content:
                    is_collaborative = True
                    break

            # 如果是协作笔记，尝试通过 WebSocket 获取内容
            is_collaboration_note = False  # 标记是否成功获取协作笔记
            if is_collaborative:
                print(f"    🔄 检测到协作笔记，尝试 WebSocket 获取...")

                # 尝试通过 WebSocket 获取协作笔记内容（返回 Markdown）
                collab_markdown, collab_images = self.get_collaboration_content(note_guid)

                if collab_markdown:
                    print(f"    ✅ 成功获取协作笔记内容（已转为 Markdown）")
                    html_content = collab_markdown  # 虽然变量名叫 html_content，但实际是 Markdown
                    is_collaboration_note = True  # 标记为协作笔记

                    # 下载协作笔记中的图片
                    if collab_images:
                        assets_folder_name = f"{safe_title}_files"
                        final_assets_path = output_dir / assets_folder_name
                        final_assets_path.mkdir(exist_ok=True)

                        images_found = len(collab_images)
                        images_downloaded = 0

                        for img_name, img_info in collab_images.items():
                            img_path = final_assets_path / img_name
                            if not img_path.exists():
                                if self.download_collaboration_image(img_info['url'], img_info['token'], str(img_path)):
                                    images_downloaded += 1
                                else:
                                    failed_images_list.append({
                                        "name": img_name,
                                        "url": img_info['url'],
                                        "note": safe_title,
                                        "path": str(output_dir.relative_to(output_base))
                                    })
                            else:
                                images_downloaded += 1

                        # 更新 Markdown 中的图片路径（Markdown 格式）
                        html_content = html_content.replace("index_files/", f"{assets_folder_name}/")
                else:
                    # WebSocket 获取失败，记录为协作笔记，稍后手动处理
                    view_page_url = f"https://as.wiz.cn/note-plus/note/{self.kb_guid}/{note_guid}"

                    # 检测失败原因
                    failure_reason = "unknown"
                    if not WEBSOCKET_AVAILABLE:
                        failure_reason = "missing_dependency"

                    return {
                        "status": "collaborative",
                        "title": safe_title,
                        "note_guid": note_guid,
                        "view_url": view_page_url,
                        "path": str(output_dir.relative_to(output_base)),
                        "images_found": images_found,
                        "images_downloaded": images_downloaded,
                        "attachments_found": attachments_found,
                        "attachments_downloaded": attachments_downloaded,
                        "failed_images": failed_images_list,
                        "failed_attachments": failed_attachments_list,
                        "failure_reason": failure_reason
                    }

            # 转换为 Markdown
            # 如果是 Lite 笔记或协作笔记，直接使用内容（已经是 Markdown）
            if is_lite_note or is_collaboration_note:
                md_content = html_content
            else:
                # HTML 笔记需要转换为 Markdown
                md_content = md(html_content, heading_style="ATX")

            md_content = self.clean_opening_title(md_content, note_title)

            # 添加附件链接（使用相对路径）
            if attachments_downloaded > 0:
                md_content += f"\n\n## 📎 附件\n\n"
                attachments = self.get_note_attachments(note_guid)
                for att in attachments:
                    att_name = att.get('name', 'unknown')
                    md_content += f"- [[{assets_folder_name}/{att_name}|{att_name}]]\n"

            # 写入文件
            frontmatter = f"---\ntitle: {note_title}\ndate: {note.get('created')}\ntags: {note.get('tags')}\n---\n\n"
            with open(md_file_path, 'w', encoding='utf-8') as f:
                f.write(frontmatter + md_content)

            return {
                "status": "success",
                "title": safe_title,
                "images_found": images_found,
                "images_downloaded": images_downloaded,
                "attachments_found": attachments_found,
                "attachments_downloaded": attachments_downloaded,
                "failed_images": failed_images_list,
                "failed_attachments": failed_attachments_list
            }

        except Exception as e:
            return {
                "status": "error",
                "title": safe_title,
                "error": str(e),
                "note_guid": note_guid,
                "path": str(output_dir.relative_to(output_base))
            }

    def get_all_categories(self):
        """获取所有分类/文件夹列表"""
        print("\n🔍 尝试获取所有分类...")

        # 方法 1: /ks/category/all
        try:
            url = f"{self.kapi_url}/ks/category/all/{self.kb_guid}"
            resp = self.session.get(url, timeout=(self.connect_timeout, self.timeout))
            print(f"  🔍 /ks/category/all 响应: HTTP {resp.status_code}")

            if resp.status_code == 200:
                data = resp.json()
                if data.get('return_code') == 200 or data.get('returnCode') == 200:
                    categories = data.get('result', [])
                    print(f"  ✅ 发现 {len(categories)} 个分类")
                    return categories
        except Exception as e:
            print(f"  ⚠️  /ks/category/all 失败: {str(e)}")

        # 方法 2: /ks/category/list
        try:
            url = f"{self.kapi_url}/ks/category/list/{self.kb_guid}"
            resp = self.session.get(url, timeout=(self.connect_timeout, self.timeout))
            print(f"  🔍 /ks/category/list 响应: HTTP {resp.status_code}")

            if resp.status_code == 200:
                data = resp.json()
                if data.get('return_code') == 200 or data.get('returnCode') == 200:
                    categories = data.get('result', [])
                    print(f"  ✅ 发现 {len(categories)} 个分类")
                    return categories
        except Exception as e:
            print(f"  ⚠️  /ks/category/list 失败: {str(e)}")

        print("  ❌ 无法获取分类列表")
        return []

    def scan_folder_recursive(self, folder, output_base, all_notes):
        """Recursively scan a folder for notes AND subfolders"""
        if folder in self.known_folders:
            return
        self.known_folders.add(folder)

        print(f"\n📁 扫描: {folder}")

        # 1. Get Notes in this folder
        start = 0
        while True:
            list_url = f"{self.kapi_url}/ks/note/list/category/{self.kb_guid}"
            params = {
                "category": folder,
                "start": start,
                "count": 100,
                "with_abstract": 0,
                "order": "created-desc"
            }
            try:
                resp = self.session.get(list_url, params=params, timeout=(self.connect_timeout, self.timeout))

                # 尝试解析 JSON
                try:
                    data = resp.json()
                except Exception as json_err:
                    print(f"  ❌ JSON 解析失败: {json_err}")
                    print(f"  📝 响应内容（前200字符）: {resp.text[:200]}")
                    break

                code = data.get('return_code', data.get('returnCode'))
                if code != 200:
                    print(f"  ⚠️  API 返回错误码: {code}")
                    print(f"  📝 错误信息: {data.get('return_message', data.get('returnMessage'))}")
                    break

                notes = data.get('result', [])
                if not notes:
                    if start == 0:
                        print(f"  ℹ️  此分类无笔记")
                    break

                all_notes.extend(notes)
                print(f"  ✅ 发现 {len(notes)} 个笔记（总计: {len(all_notes)}）")

                start += len(notes)
                if len(notes) < 100:
                    break
            except Exception as e:
                print(f"  ⚠️  扫描失败: {str(e)}")
                break

    def run(self):
        if not self.login():
            return

        print("\n" + "="*70)
        print("🔍 开始扫描笔记...")
        print("="*70)

        output_base = "wiznote_download"
        output_path = os.path.abspath(output_base)
        print(f"📁 下载目录: {output_path}\n")

        # 先尝试获取所有分类
        categories = self.get_all_categories()

        # 收集所有笔记
        all_notes = []

        if categories:
            # 如果获取到分类列表，扫描每个分类
            print(f"\n📂 开始扫描 {len(categories)} 个分类...\n")
            for category in categories:
                if isinstance(category, str):
                    # 分类是字符串路径
                    self.scan_folder_recursive(category, output_base, all_notes)
                elif isinstance(category, dict):
                    # 分类是对象
                    cat_path = category.get('key') or category.get('category') or category.get('path')
                    if cat_path:
                        self.scan_folder_recursive(cat_path, output_base, all_notes)
        else:
            # 如果获取不到分类，尝试扫描根目录
            print("\n⚠️  无法获取分类列表，尝试扫描根目录...\n")
            self.scan_folder_recursive('/', output_base, all_notes)

        if not all_notes:
            print("\n❌ 未发现任何笔记！")
            print("💡 可能的原因：")
            print("   1. WizNote 账号中没有笔记")
            print("   2. API 端点发生变化")
            print("   3. 需要使用其他 API")
            return

        print(f"\n{'='*70}")
        print(f"📊 扫描完成！发现 {len(all_notes)} 个笔记")
        print(f"{'='*70}")
        print(f"\n🚀 开始并发下载（{self.max_workers} 个线程）...\n")

        # 使用线程池并发处理笔记
        start_time = time.time()

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有任务
            futures = {
                executor.submit(self.process_note, note, output_base): note
                for note in all_notes
            }

            # 处理完成的任务
            completed = 0
            for future in as_completed(futures):
                completed += 1
                result = future.result()

                # 调用进度回调
                if self.on_progress:
                    try:
                        self.on_progress(completed, len(all_notes))
                    except:
                        pass  # 忽略回调错误

                if result is None:
                    continue

                # 更新计数器（使用锁保护）
                with self.lock:
                    self.processed_count += 1

                    if result["status"] == "skip":
                        print(f"  [{completed}/{len(all_notes)}] ⏭️  跳过: {result['title']} (已存在)")
                    elif result["status"] == "success":
                        self.success_count += 1

                        # 统计图片
                        images_found = result.get("images_found", 0)
                        images_downloaded = result.get("images_downloaded", 0)
                        self.total_images_found += images_found
                        self.total_images_downloaded += images_downloaded

                        # 统计附件
                        attachments_found = result.get("attachments_found", 0)
                        attachments_downloaded = result.get("attachments_downloaded", 0)
                        self.total_attachments_found += attachments_found
                        self.total_attachments_downloaded += attachments_downloaded

                        # 记录失败项
                        if result.get("failed_images"):
                            self.failed_images.extend(result["failed_images"])
                            if len(result["failed_images"]) > 0:
                                print(f"    ⚠️  {len(result['failed_images'])} 张图片下载失败")
                        if result.get("failed_attachments"):
                            self.failed_attachments.extend(result["failed_attachments"])

                        info_parts = []
                        if images_downloaded > 0:
                            info_parts.append(f"{images_downloaded}/{images_found} 张图片")
                        if attachments_downloaded > 0:
                            info_parts.append(f"{attachments_downloaded}/{attachments_found} 个附件")

                        if info_parts:
                            print(f"  [{completed}/{len(all_notes)}] ✅ 成功: {result['title']} ({', '.join(info_parts)})")
                        else:
                            print(f"  [{completed}/{len(all_notes)}] ✅ 成功: {result['title']}")
                    elif result["status"] == "collaborative":
                        # 协作笔记
                        self.collaborative_notes.append(result)

                        # 统计协作笔记中已下载的图片和附件
                        images_found = result.get("images_found", 0)
                        images_downloaded = result.get("images_downloaded", 0)
                        attachments_found = result.get("attachments_found", 0)
                        attachments_downloaded = result.get("attachments_downloaded", 0)

                        self.total_images_found += images_found
                        self.total_images_downloaded += images_downloaded
                        self.total_attachments_found += attachments_found
                        self.total_attachments_downloaded += attachments_downloaded

                        # 记录失败项
                        if result.get("failed_images"):
                            self.failed_images.extend(result["failed_images"])
                        if result.get("failed_attachments"):
                            self.failed_attachments.extend(result["failed_attachments"])

                        print(f"  [{completed}/{len(all_notes)}] ⚠️  协作笔记: {result['title']} (需手动处理)")
                    elif result["status"] == "encrypted":
                        # 加密笔记
                        self.encrypted_notes.append(result)

                        # 加密笔记通常没有下载任何资源，但为了完整性也统计
                        images_found = result.get("images_found", 0)
                        images_downloaded = result.get("images_downloaded", 0)
                        attachments_found = result.get("attachments_found", 0)
                        attachments_downloaded = result.get("attachments_downloaded", 0)

                        self.total_images_found += images_found
                        self.total_images_downloaded += images_downloaded
                        self.total_attachments_found += attachments_found
                        self.total_attachments_downloaded += attachments_downloaded

                        print(f"  [{completed}/{len(all_notes)}] 🔒 加密笔记: {result['title']} (需先解密)")
                    else:
                        # 记录失败的笔记
                        self.failed_notes.append(result)
                        print(f"  [{completed}/{len(all_notes)}] ❌ 失败: {result['title']} - {result.get('error', '未知错误')}")

        # 计算耗时
        elapsed_time = time.time() - start_time
        minutes, seconds = divmod(int(elapsed_time), 60)

        # 计算成功率（协作笔记不计入失败）
        note_success_rate = (self.success_count / len(all_notes) * 100) if len(all_notes) > 0 else 0
        image_success_rate = (self.total_images_downloaded / self.total_images_found * 100) if self.total_images_found > 0 else 0
        attachment_success_rate = (self.total_attachments_downloaded / self.total_attachments_found * 100) if self.total_attachments_found > 0 else 0

        print(f"\n{'='*70}")
        print(f"🎉 下载完成！")
        print(f"{'='*70}")
        print(f"📊 统计信息:")
        print(f"\n  📝 笔记:")
        print(f"     - 总数: {len(all_notes)} 个")
        print(f"     - 成功: {self.success_count} 个")
        if len(self.collaborative_notes) > 0:
            print(f"     - 协作笔记: {len(self.collaborative_notes)} 个（需手动处理）")
        if len(self.encrypted_notes) > 0:
            print(f"     - 加密笔记: {len(self.encrypted_notes)} 个（需先解密）")
        print(f"     - 失败: {len(self.failed_notes)} 个")
        print(f"     - 成功率: {note_success_rate:.1f}%")

        print(f"\n  🖼️  图片:")
        print(f"     - 总数: {self.total_images_found} 张")
        print(f"     - 成功: {self.total_images_downloaded} 张")
        print(f"     - 失败: {self.total_images_found - self.total_images_downloaded} 张")
        print(f"     - 成功率: {image_success_rate:.1f}%")

        print(f"\n  📎 附件:")
        print(f"     - 总数: {self.total_attachments_found} 个")
        print(f"     - 成功: {self.total_attachments_downloaded} 个")
        print(f"     - 失败: {self.total_attachments_found - self.total_attachments_downloaded} 个")
        print(f"     - 成功率: {attachment_success_rate:.1f}%")

        print(f"\n  ⏱️  耗时: {minutes} 分 {seconds} 秒")
        print(f"\n📁 下载位置: {output_path}")
        print(f"\n💡 下一步:")

        # 检测协作笔记是否因缺少依赖
        missing_dependency_notes = [n for n in self.collaborative_notes if n.get('failure_reason') == 'missing_dependency']
        if missing_dependency_notes:
            print(f"\n   ⚠️  检测到 {len(missing_dependency_notes)} 个协作笔记因缺少依赖而无法下载！")
            print(f"\n   解决方案：")
            print(f"      pip3 install websocket-client")
            print(f"      # 或")
            print(f"      pip3 install -r requirements.txt")
            print(f"\n   安装后删除 wiznote_download 目录并重新运行下载工具。")

        if self.encrypted_notes:
            print(f"\n   ⚠️  检测到 {len(self.encrypted_notes)} 个加密笔记，请先在 WizNote 客户端中解密：")
            print(f"      1. 在 WizNote 客户端中找到加密笔记")
            print(f"      2. 输入密码解密")
            print(f"      3. 右键笔记 → 取消加密")
            print(f"      4. 重新运行下载工具")

        print(f"\n   1. 在 Obsidian 中打开下载的笔记查看效果")
        print(f"   2. 运行格式化工具优化: python3 tools/obsidian_formatter.py --all")
        print(f"   3. 如需迁移附件: python3 tools/obsidian_formatter.py --migrate-attachments")

        # 生成下载报告
        self.generate_report(output_path, note_success_rate, image_success_rate, attachment_success_rate)

    def generate_report(self, output_path, note_success_rate, image_success_rate, attachment_success_rate):
        """生成详细的下载报告"""
        report_path = Path(output_path) / "download_report.md"

        try:
            with open(report_path, 'w', encoding='utf-8') as f:
                # 报告标题
                f.write("# WizNote 下载报告\n\n")
                f.write(f"> 生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write("---\n\n")

                # 统计摘要
                f.write("## 📊 统计摘要\n\n")
                f.write("### 笔记统计\n\n")
                f.write(f"- 总数: {self.processed_count} 个\n")
                f.write(f"- 成功: {self.success_count} 个\n")
                f.write(f"- 协作笔记: {len(self.collaborative_notes)} 个（需手动处理）\n")
                f.write(f"- 加密笔记: {len(self.encrypted_notes)} 个（需先解密）\n")
                f.write(f"- 失败: {len(self.failed_notes)} 个\n")
                f.write(f"- 成功率: {note_success_rate:.1f}%\n\n")

                f.write("### 图片统计\n\n")
                f.write(f"- 总数: {self.total_images_found} 张\n")
                f.write(f"- 成功: {self.total_images_downloaded} 张\n")
                f.write(f"- 失败: {len(self.failed_images)} 张\n")
                f.write(f"- 成功率: {image_success_rate:.1f}%\n\n")

                f.write("### 附件统计\n\n")
                f.write(f"- 总数: {self.total_attachments_found} 个\n")
                f.write(f"- 成功: {self.total_attachments_downloaded} 个\n")
                f.write(f"- 失败: {len(self.failed_attachments)} 个\n")
                f.write(f"- 成功率: {attachment_success_rate:.1f}%\n\n")

                f.write("---\n\n")

                # 协作笔记
                if self.collaborative_notes:
                    f.write("## ⚠️ 协作笔记\n\n")
                    f.write(f"共 {len(self.collaborative_notes)} 个协作笔记无法自动下载：\n\n")

                    # 检测是否因为缺少依赖
                    missing_dependency_notes = [n for n in self.collaborative_notes if n.get('failure_reason') == 'missing_dependency']

                    if missing_dependency_notes:
                        f.write("> ⚠️ **重要提示**：检测到 {0} 个协作笔记因缺少依赖而无法下载。\n\n".format(len(missing_dependency_notes)))
                        f.write("**解决方案**：\n")
                        f.write("```bash\n")
                        f.write("# 安装 websocket-client 依赖\n")
                        f.write("pip3 install websocket-client\n")
                        f.write("# 或使用 requirements.txt\n")
                        f.write("pip3 install -r requirements.txt\n")
                        f.write("```\n\n")
                        f.write("安装依赖后，删除 `wiznote_download` 目录并重新运行下载工具。\n\n")
                        f.write("---\n\n")

                    f.write("> 协作笔记需要特殊权限或客户端版本，无法通过 API 直接获取内容。\n\n")

                    for i, note in enumerate(self.collaborative_notes, 1):
                        f.write(f"### {i}. {note['title']}\n\n")

                        # 显示失败原因
                        if note.get('failure_reason') == 'missing_dependency':
                            f.write("- **失败原因**: ⚠️ 缺少 `websocket-client` 依赖\n")
                        else:
                            f.write("- **失败原因**: WebSocket 获取失败或权限不足\n")

                        f.write(f"- **笔记 GUID**: `{note['note_guid']}`\n")
                        f.write(f"- **路径**: `{note['path']}`\n")
                        if note.get('view_url'):
                            f.write(f"- **在线查看**: [点击查看]({note['view_url']})\n")

                        f.write("\n**手动处理方法**：\n")
                        if note.get('failure_reason') == 'missing_dependency':
                            f.write("1. 安装依赖: `pip3 install websocket-client`\n")
                            f.write("2. 删除 `wiznote_download` 目录\n")
                            f.write("3. 重新运行下载工具\n")
                        else:
                            f.write('1. 点击上面的"在线查看"链接，在浏览器中打开笔记\n')
                            f.write("2. 登录 WizNote 账号后，手动复制内容\n")
                            f.write("3. 或在 WizNote 客户端中导出此笔记\n")
                        f.write("\n")

                    f.write("---\n\n")

                # 加密笔记
                if self.encrypted_notes:
                    f.write("## 🔒 加密笔记\n\n")
                    f.write(f"共 {len(self.encrypted_notes)} 个加密笔记无法自动下载：\n\n")
                    f.write("> 加密笔记需要密码才能访问。由于每篇笔记可能使用不同的密码，请先在 WizNote 客户端中解密后再重新运行下载工具。\n\n")

                    for i, note in enumerate(self.encrypted_notes, 1):
                        f.write(f"### {i}. {note['title']}\n\n")
                        f.write(f"- **笔记 GUID**: `{note['note_guid']}`\n")
                        f.write(f"- **路径**: `{note['path']}`\n")
                        f.write("\n**处理步骤**：\n")
                        f.write("1. 在 WizNote 客户端中找到此笔记\n")
                        f.write("2. 输入密码解密笔记\n")
                        f.write("3. 右键笔记 → 取消加密\n")
                        f.write("4. 重新运行下载工具\n\n")

                    f.write("**💡 提示**：可以批量解密笔记后再运行下载工具，避免重复操作。\n\n")
                    f.write("---\n\n")

                # 失败的笔记
                if self.failed_notes:
                    f.write("## ❌ 失败的笔记\n\n")
                    f.write(f"共 {len(self.failed_notes)} 个笔记下载失败：\n\n")

                    for i, note in enumerate(self.failed_notes, 1):
                        f.write(f"### {i}. {note['title']}\n\n")
                        f.write(f"- **错误**: {note.get('error', '未知错误')}\n")
                        if note.get('note_guid'):
                            f.write(f"- **笔记 GUID**: `{note['note_guid']}`\n")
                        if note.get('path'):
                            f.write(f"- **路径**: `{note['path']}`\n")
                        f.write("\n")

                    f.write("---\n\n")

                # 失败的图片
                if self.failed_images:
                    f.write("## 🖼️ 失败的图片\n\n")
                    f.write(f"共 {len(self.failed_images)} 张图片下载失败：\n\n")

                    for i, img in enumerate(self.failed_images, 1):
                        f.write(f"{i}. **{img['name']}**\n")
                        f.write(f"   - 笔记: {img['note']}\n")
                        f.write(f"   - 路径: `{img['path']}`\n")
                        f.write(f"   - URL: `{img['url']}`\n\n")

                    f.write("---\n\n")

                # 失败的附件
                if self.failed_attachments:
                    f.write("## 📎 失败的附件\n\n")
                    f.write(f"共 {len(self.failed_attachments)} 个附件下载失败：\n\n")

                    for i, att in enumerate(self.failed_attachments, 1):
                        f.write(f"{i}. **{att['name']}**\n")
                        f.write(f"   - 笔记: {att['note']}\n")
                        f.write(f"   - 路径: `{att['path']}`\n")
                        if att.get('url'):
                            f.write(f"   - URL: `{att['url']}`\n")
                        if att.get('reason'):
                            f.write(f"   - 原因: {att['reason']}\n")
                        f.write("\n")

                    f.write("---\n\n")

                # 手动处理建议
                if self.failed_notes or self.failed_images or self.failed_attachments or self.collaborative_notes or self.encrypted_notes:
                    f.write("## 💡 手动处理建议\n\n")

                    if self.encrypted_notes:
                        f.write("### 加密笔记\n\n")
                        f.write("1. 在 WizNote 客户端中找到对应笔记\n")
                        f.write("2. 输入密码解密\n")
                        f.write("3. 右键笔记 → 取消加密\n")
                        f.write("4. 重新运行下载工具\n\n")

                    if self.collaborative_notes:
                        # 检测是否因缺少依赖
                        missing_dep = [n for n in self.collaborative_notes if n.get('failure_reason') == 'missing_dependency']

                        if missing_dep:
                            f.write("### 协作笔记（缺少依赖）\n\n")
                            f.write(f"有 {len(missing_dep)} 个协作笔记因缺少 `websocket-client` 依赖而无法下载。\n\n")
                            f.write("**解决步骤**：\n")
                            f.write("```bash\n")
                            f.write("# 1. 安装依赖\n")
                            f.write("pip3 install websocket-client\n")
                            f.write("# 或使用 requirements.txt\n")
                            f.write("pip3 install -r requirements.txt\n")
                            f.write("```\n\n")
                            f.write("2. 删除 `wiznote_download` 目录\n")
                            f.write("3. 重新运行下载工具\n\n")

                        # 如果还有其他原因失败的协作笔记
                        other_collab = [n for n in self.collaborative_notes if n.get('failure_reason') != 'missing_dependency']
                        if other_collab:
                            f.write("### 协作笔记（权限或其他原因）\n\n")
                            f.write(f"有 {len(other_collab)} 个协作笔记因权限或其他原因无法自动下载。\n\n")
                            f.write("**手动处理方法**：\n")
                            f.write('1. 点击报告中的"在线查看"链接\n')
                            f.write("2. 在浏览器中登录 WizNote 账号\n")
                            f.write("3. 手动复制内容或导出笔记\n\n")

                    if self.failed_notes:
                        f.write("### 失败的笔记\n\n")
                        f.write("1. 在 WizNote 客户端中找到对应笔记\n")
                        f.write("2. 手动导出为 Markdown 或 HTML\n")
                        f.write("3. 复制到对应目录\n\n")

                    if self.failed_images or self.failed_attachments:
                        f.write("### 失败的图片/附件\n\n")
                        f.write("1. 复制上面的 URL 到浏览器下载\n")
                        f.write("2. 或在 WizNote 客户端中右键保存\n")
                        f.write("3. 放到对应笔记的 `_files` 文件夹中\n\n")

                    f.write("**提示**: 如果需要重新下载，可以删除 `wiznote_download` 目录后重新运行工具。\n")

                # 如果全部成功（不包括协作笔记和加密笔记，因为它们不是真正的失败）
                if not self.failed_notes and not self.failed_images and not self.failed_attachments and not self.collaborative_notes and not self.encrypted_notes:
                    f.write("## ✅ 全部成功\n\n")
                    f.write("所有笔记、图片和附件都下载成功！\n")

            print(f"\n📄 下载报告已保存: {report_path}")

        except Exception as e:
            print(f"\n⚠️  生成报告失败: {str(e)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="WizNote to Obsidian - 在线下载工具 v1.1",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 使用默认参数
  python3 wiznote_downloader.py

  # 极速模式（网络好，快速下载）
  python3 wiznote_downloader.py --workers 10 --timeout 20

  # 安全模式（网络差，避免卡住）
  python3 wiznote_downloader.py --workers 3 --timeout 10 --retries 1

  # 超级安全模式（网络很差）
  python3 wiznote_downloader.py --workers 2 --timeout 8 --retries 1 --connect-timeout 5
        """
    )

    parser.add_argument(
        '--workers', '-w',
        type=int,
        default=DEFAULT_MAX_WORKERS,
        help=f'并发下载线程数（默认: {DEFAULT_MAX_WORKERS}，推荐: 3-10）'
    )

    parser.add_argument(
        '--timeout', '-t',
        type=int,
        default=DEFAULT_TIMEOUT,
        help=f'下载超时时间/秒（默认: {DEFAULT_TIMEOUT}，推荐: 10-30）'
    )

    parser.add_argument(
        '--retries', '-r',
        type=int,
        default=DEFAULT_MAX_RETRIES,
        help=f'下载失败重试次数（默认: {DEFAULT_MAX_RETRIES}，推荐: 1-3）'
    )

    parser.add_argument(
        '--connect-timeout', '-c',
        type=int,
        default=DEFAULT_CONNECT_TIMEOUT,
        help=f'连接超时时间/秒（默认: {DEFAULT_CONNECT_TIMEOUT}，推荐: 5-15）'
    )

    args = parser.parse_args()

    print("=" * 70)
    print("WizNote to Obsidian - 在线下载工具 v1.1")
    print("=" * 70)
    print("\n📥 此工具将从 WizNote 云端下载笔记并转换为 Markdown 格式")
    print("📁 默认下载目录: ./wiznote_download/")
    print("🖼️  图片和附件: 支持自动下载（使用增强版 API）")
    print(f"⚡ 性能优化: 并发下载，{args.workers} 个线程同时处理")
    print(f"⚙️  参数配置: 超时 {args.timeout}s, 重试 {args.retries}次, 连接超时 {args.connect_timeout}s\n")
    print("-" * 70)

    u = input("📧 Email: ")
    p = getpass.getpass("🔑 Password: ")
    print()

    migrator = WizMigrator(
        u, p,
        max_workers=args.workers,
        max_retries=args.retries,
        timeout=args.timeout,
        connect_timeout=args.connect_timeout
    )
    migrator.run()
