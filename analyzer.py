import os
import certifi

# 彻底清除系统中的 Conda 环境变量干扰，确保只依赖独立的 .venv 虚拟环境
for key in list(os.environ.keys()):
    if "CONDA" in key.upper():
        del os.environ[key]

# 针对 Windows 中文路径 (如 "项目") 导致的 OpenSSL 证书加载 FileNotFoundError 异常进行修复
for env_var in ["SSL_CERT_FILE", "REQUESTS_CA_BUNDLE", "CURL_CA_BUNDLE"]:
    if env_var in os.environ:
        val = os.environ[env_var]
        if not os.path.exists(val) or any(ord(c) > 127 for c in val):
            os.environ[env_var] = certifi.where()
    else:
        os.environ[env_var] = certifi.where()

if "SSL_CERT_DIR" in os.environ:
    val = os.environ["SSL_CERT_DIR"]
    if not os.path.exists(val) or any(ord(c) > 127 for c in val):
        del os.environ["SSL_CERT_DIR"]

import io
import re
import csv
import time
import logging
import base64
from typing import Dict, Optional

import requests
from PIL import Image
import google.genai as genai
from google.genai import types as genai_types
from openai import OpenAI
import urllib3
try:
    from rapidocr_onnxruntime import RapidOCR
except ImportError:
    RapidOCR = None

try:
    import winocr
except ImportError:
    winocr = None

try:
    from ocrmac import ocrmac
except ImportError:
    ocrmac = None

try:
    import pytesseract
except ImportError:
    pytesseract = None



import urllib3.util.connection as xc_conn
import urllib.request
import json

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)

# ── 代理 Fake-IP 绕过补丁 (解决 cdn-mineru.openxlab.org.cn SSL 连接中断) ──────────
_orig_create_connection = xc_conn.create_connection
_resolved_ips = {}

def get_real_ip_via_doh(domain):
    if domain in _resolved_ips:
        return _resolved_ips[domain]
    
    url = f"http://223.5.5.5/resolve?name={domain}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode('utf-8'))
            if data.get("Status") == 0:
                for ans in data.get("Answer", []):
                    if ans.get("type") == 1:
                        ip = ans.get("data")
                        if ip and not ip.startswith("198.18."):
                            _resolved_ips[domain] = ip
                            logger.info(f"DoH resolved {domain} -> {ip}")
                            return ip
    except Exception as e:
        logger.warning(f"DoH resolution failed for {domain}: {e}")
        
    if domain == "cdn-mineru.openxlab.org.cn":
        fallback_ip = "58.205.221.38"
        _resolved_ips[domain] = fallback_ip
        return fallback_ip
    return None

def patched_create_connection(address, *args, **kwargs):
    host, port = address
    if host == "cdn-mineru.openxlab.org.cn":
        real_ip = get_real_ip_via_doh(host)
        if real_ip:
            return _orig_create_connection((real_ip, port), *args, **kwargs)
    return _orig_create_connection(address, *args, **kwargs)

xc_conn.create_connection = patched_create_connection


class ImageAnalyzer:
    """
    多引擎 OCR / VLM 分析器。
    支持：Local OCR (RapidOCR)、Gemini、OpenAI Compatible、MinerU API。
    """

    def __init__(
        self,
        api_type: str = "Local OCR",
        api_key: str = None,
        base_url: str = None,
        model_name: str = None,
        split_len: Optional[int] = None,
        split_regex: Optional[str] = None
    ):
        self.api_type = api_type
        self.api_key = api_key
        self.base_url = base_url
        self.model_name = model_name
        self.split_len = split_len
        self.split_regex = split_regex

        self.use_gemini = False
        self.use_openai_compatible = False
        self.use_mineru = False
        self.local_ocr = None

        # 初始化对应引擎
        if self.api_type == "Gemini (Native)" and self.api_key:
            try:
                # 仅在 __init__ 校验配置与模型，Client 会在每次多线程请求时局部创建以避免 event loop 冲突
                self.gemini_model_name = model_name or 'gemini-2.0-flash'
                self.use_gemini = True
                logger.info("Gemini API (google-genai) verified.")
            except Exception as e:
                logger.error(f"Failed to init Gemini: {e}")

        elif self.api_type == "OpenAI Compatible" and self.api_key:
            try:
                self.openai_client = OpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url or "https://api.openai.com/v1"
                )
                self.use_openai_compatible = True
                logger.info(f"OpenAI client initialized. URL: {self.base_url}")
            except Exception as e:
                logger.error(f"Failed to init OpenAI client: {e}")

        elif self.api_type == "MinerU (API)" and self.base_url:
            if not self.api_key:
                logger.warning("MinerU API token (api_key) is missing. Falling back to Local OCR.")
                self.api_type = "Local OCR"
            else:
                self.use_mineru = True
                logger.info(f"MinerU client initialized. URL: {self.base_url}")

        self.use_system_ocr = False

        # 如果需要本地 OCR，但未安装 RapidOCR，则自动降级到系统原生 OCR
        if self.api_type == "Local OCR" and RapidOCR is None:
            logger.warning("RapidOCR is not installed. Auto falling back to System Native OCR.")
            self.api_type = "System Native OCR"

        # System Native OCR 跨平台原生引擎处理
        if self.api_type == "System Native OCR" or self.api_type == "Windows OCR":
            import sys
            if sys.platform == "win32":
                if winocr is None:
                    raise ImportError(
                        "当前为 Windows 系统，但未检测到 `winocr` 库。请运行 `pip install winocr` 进行安装以启用内置 OCR。"
                    )
            elif sys.platform == "darwin":
                if ocrmac is None:
                    raise ImportError(
                        "当前为 macOS 系统，但未检测到 `ocrmac` 库。请运行 `pip install ocrmac` 进行安装以启用内置 OCR。"
                    )
            else:
                # Linux 或其他 (如 Docker)
                if pytesseract is None:
                    raise ImportError(
                        "当前为 Linux/Docker 环境，但未检测到 `pytesseract` 库。请运行 `pip install pytesseract`；"
                        "且确保系统已安装 tesseract-ocr 命令行程序。"
                    )
                import shutil
                if not shutil.which("tesseract"):
                    raise ImportError(
                        "系统未在 PATH 中找到 `tesseract` 命令行程序。请在系统中安装 tesseract-ocr（如 apt-get install tesseract-ocr tesseract-ocr-chi-sim）。"
                    )
            self.use_system_ocr = True
            logger.info(f"System Native OCR initialized. Platform: {sys.platform}")

        # 兜底本地 OCR
        elif not (self.use_gemini or self.use_openai_compatible or self.use_mineru):
            if RapidOCR is None:
                # 检查系统原生 OCR 是否可用（检测对应平台的绑定库）
                system_available = False
                import sys
                if sys.platform == "win32":
                    if winocr is not None:
                        system_available = True
                elif sys.platform == "darwin":
                    if ocrmac is not None:
                        system_available = True
                else:
                    import shutil
                    if shutil.which("tesseract") and pytesseract is not None:
                        system_available = True

                if system_available:
                    logger.info("RapidOCR is not installed. Automatically defaulting to System Native OCR.")
                    self.use_system_ocr = True
                else:
                    raise ImportError(
                        "未检测到本地 OCR 引擎。如果需要使用本地 OCR，请运行 `pip install rapidocr-onnxruntime` 进行安装；"
                        "或者运行 `pip install winocr` (Windows) / `pip install ocrmac` (macOS) 启用轻量系统原生 OCR。"
                    )
            else:
                logger.info("Using local RapidOCR.")
                self.local_ocr = RapidOCR()

    def analyze(self, image_path: str, output_csv_path: str = None, formats: dict = None) -> dict:
        """
        分析图片。
        Returns: {"type": "text"|"table"|"image", "content": str, "csv_path": str|None}
        """
        prompt = self._build_prompt(formats)

        if self.use_gemini:
            res = self._analyze_with_gemini(image_path, prompt, output_csv_path)
            if res and "source" not in res:
                res["source"] = "Gemini API"
        elif self.use_openai_compatible:
            res = self._analyze_with_openai(image_path, prompt, output_csv_path)
            if res and "source" not in res:
                res["source"] = "OpenAI API"
        elif self.use_mineru:
            res = self._analyze_with_mineru(image_path, output_csv_path)
            if res and "source" not in res:
                res["source"] = "MinerU API"
        elif self.use_system_ocr:
            res = self._analyze_with_system_ocr(image_path)
            if res and "source" not in res:
                res["source"] = "System Native OCR"
        else:
            res = self._analyze_with_local(image_path)
            if res and "source" not in res:
                res["source"] = "Local OCR"

        return res

    def _build_prompt(self, formats: dict = None) -> str:
        """根据用户勾选的格式构建动态 Prompt"""
        instructions = []

        text_enabled = formats.get("text", True) if formats else True
        table_enabled = formats.get("table", True) if formats else True
        chart_enabled = formats.get("chart", False) if formats else False
        formula_enabled = formats.get("formula", False) if formats else False
        handwriting_enabled = formats.get("handwriting", False) if formats else False
        seal_enabled = formats.get("seal", False) if formats else False
        chemistry_enabled = formats.get("chemistry", False) if formats else False

        if text_enabled:
            instructions.append("如果图片包含段落、标题等纯文本，请直接提取并输出文字，保留基本行结构与层次。")
        if table_enabled:
            table_cols = formats.get("table_cols") if formats else None
            rule = "如果图片包含表格，请严格提取其中的所有数据，输出为严谨的原生 Markdown 格式表格，保证行列表头对齐，信息绝不错位或丢失。"
            if table_cols:
                try:
                    cols_num = int(table_cols)
                    rule += f" 特别提示：提取的 Markdown 表格必须包含且仅包含 {cols_num} 列。若某行中部分单元格为空白，请保留空单元格，确保每行均有 {cols_num} 列。"
                except ValueError:
                    pass
            instructions.append(rule)
        if chart_enabled:
            instructions.append("如果图片包含统计图表（如折线图、柱状图、饼图等），请将图表中的关键数据提取并组装为 Markdown 格式的表格或结构化数据文本。")
        if formula_enabled:
            instructions.append("如果图片包含数学公式、物理方程式等科学计算公式，请以标准的 LaTeX 格式进行提取与排版，确保上下标与数学符号无误。")
        if handwriting_enabled:
            instructions.append("如果图片包含手写字体，请仔细识别手写内容，并将其转化为排版规整的印刷体文本。")
        if seal_enabled:
            instructions.append("如果图片包含印章、水印或公章等盖章信息，请识读并提取出印章内的文本，并在输出文本中以 [印章: 识别到的文本] 格式标注。")
        if chemistry_enabled:
            instructions.append("如果图片包含化学结构式、化学反应方程式，请将其转化为标准的文本（如 LaTeX 科学式或标准化学符号，例如 H2O、CO2）。")

        instructions.append("如果图片是普通风光、人物、插画等配图（即没有太多文字，且不包含上述所选的任何数据结构），请直接回复严格的 'RETAIN_IMAGE' 这几个字母，不要附带任何其他标点符号或说明。")

        prompt_rules = "\n".join(f"{idx + 1}. {rule}" for idx, rule in enumerate(instructions))
        return f"请分析这张图片，严格遵循以下规则输出：\n{prompt_rules}\n请尽量保证准确度。"

    def _analyze_with_gemini(self, image_path: str, prompt: str, output_csv_path: str) -> dict:
        """使用 Gemini API 分析 (google-genai SDK - 线程安全版)"""
        try:
            # 局部实例化 Client，以防止多线程并发调用时发生 Event loop is closed 错误
            client = genai.Client(api_key=self.api_key)
            if image_path.lower().endswith(".pdf"):
                return self._analyze_pdf_with_gemini(client, image_path, prompt, output_csv_path)
            else:
                with open(image_path, "rb") as f:
                    img_bytes = f.read()
                ext = os.path.splitext(image_path)[1].lower().replace(".", "")
                if ext == "jpg":
                    ext = "jpeg"
                mime = f"image/{ext}" if ext in ["jpeg", "png", "webp", "gif", "bmp"] else "image/jpeg"
                response = client.models.generate_content(
                    model=self.gemini_model_name,
                    contents=[
                        genai_types.Part.from_bytes(data=img_bytes, mime_type=mime),
                        genai_types.Part.from_text(text=prompt)
                    ]
                )
                text = response.text.strip()
                return self._parse_result(text, output_csv_path)
        except Exception as e:
            logger.error(f"Gemini API error on {image_path}: {e}")
            logger.info("Falling back to local OCR.")
            res = self._analyze_with_local(image_path)
            res["source"] = "Local OCR"
            return res

    def _analyze_pdf_with_gemini(self, client, image_path: str, prompt: str, output_csv_path: str) -> dict:
        """使用 Gemini 分析 PDF (google-genai SDK)"""
        with open(image_path, "rb") as f:
            pdf_bytes = f.read()
        response = client.models.generate_content(
            model=self.gemini_model_name,
            contents=[
                genai_types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
                genai_types.Part.from_text(text=prompt)
            ]
        )
        return self._parse_result(response.text.strip(), output_csv_path)

    def _analyze_with_openai(self, image_path: str, prompt: str, output_csv_path: str) -> dict:
        """使用 OpenAI 兼容 API 分析"""
        if image_path.lower().endswith(".pdf"):
            return {
                "type": "error",
                "content": "当前配置的 OpenAI 兼容接口暂不支持直接解析 PDF。请更换为 Gemini API、MinerU API，或将 PDF 转为图片后再上传。",
                "csv_path": None
            }
        try:
            with open(image_path, "rb") as f:
                base64_image = base64.b64encode(f.read()).decode('utf-8')

            ext = os.path.splitext(image_path)[1].lower().replace(".", "")
            if ext == "jpg":
                ext = "jpeg"
            mime_type = f"image/{ext}" if ext in ["jpeg", "png", "webp", "gif"] else "image/jpeg"

            response = self.openai_client.chat.completions.create(
                model=self.model_name or "gpt-4o-mini",
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{base64_image}"}}
                    ]
                }],
                max_tokens=2048,
            )
            text = response.choices[0].message.content.strip()
            return self._parse_result(text, output_csv_path)
        except Exception as e:
            logger.error(f"OpenAI API error on {image_path}: {e}")
            logger.info("Falling back to local OCR.")
            res = self._analyze_with_local(image_path)
            res["source"] = "Local OCR"
            return res

    def _analyze_with_mineru(self, image_path: str, output_csv_path: str) -> dict:
        """使用 MinerU API 分析"""
        try:
            url = self.base_url.rstrip('/')
            if "mineru.net" in url:
                try:
                    # 优先尝试原有的 v4 云端接口
                    return self._analyze_with_mineru_cloud(image_path, output_csv_path, url)
                except Exception as cloud_err:
                    logger.warning(f"MinerU v4 Cloud API failed: {cloud_err}. Trying v1 Agent API as fallback...")
                    # 尝试 /api/v1/agent/parse/file 备选接口
                    return self._analyze_with_mineru_v1_agent(image_path, output_csv_path, url)
            return self._analyze_with_mineru_local(image_path, output_csv_path, url)
        except Exception as e:
            logger.error(f"MinerU API error on {image_path}: {e}")
            logger.info("Falling back to local OCR.")
            res = self._analyze_with_local(image_path)
            res["source"] = "Local OCR"
            return res

    def _analyze_with_mineru_v1_agent(self, image_path: str, output_csv_path: str, base_url: str) -> dict:
        """调用 MinerU v1 Agent 轻量版接口 (无需 Token 验证，限流但防失效)"""
        filename = os.path.basename(image_path)
        post_url = f"{base_url}/api/v1/agent/parse/file"
        
        # 1. POST JSON 获取上传 URL 和 task_id
        post_data = {
            "file_name": filename,
            "is_ocr": True,
            "enable_formula": True
        }
        headers = {"Content-Type": "application/json"}
        res = requests.post(post_url, headers=headers, json=post_data, timeout=30, verify=False)
        res.raise_for_status()
        res_json = res.json()
        if res_json.get("code") != 0:
            raise Exception(f"v1 agent POST failed: {res_json.get('msg')}")
            
        task_id = res_json["data"]["task_id"]
        upload_url = res_json["data"]["file_url"]
        
        logger.info(f"MinerU v1 Agent task obtained. Task ID: {task_id}. Uploading file binary...")
        
        # 2. PUT 上传文件内容
        with open(image_path, "rb") as f:
            res_upload = requests.put(upload_url, data=f, timeout=120, verify=False)
        res_upload.raise_for_status()
        
        logger.info(f"MinerU v1 Agent file uploaded. Polling result...")
        
        # 3. 轮询结果
        status_url = f"{base_url}/api/v1/agent/parse/{task_id}"
        for _ in range(60):
            time.sleep(3)
            res_poll = requests.get(status_url, timeout=30, verify=False)
            res_poll.raise_for_status()
            poll_json = res_poll.json()
            
            if poll_json.get("code") != 0:
                raise Exception(f"v1 agent polling failed: {poll_json.get('msg')}")
                
            data_block = poll_json.get("data", {})
            state = data_block.get("state")
            if state == "done":
                md_url = data_block.get("markdown_url")
                if not md_url:
                    raise Exception("v1 agent done but returned no markdown_url")
                # 下载 markdown 文件内容
                res_md = requests.get(md_url, timeout=30, verify=False)
                res_md.raise_for_status()
                text = res_md.text
                
                res_dict = self._parse_result(text.strip(), output_csv_path)
                res_dict["source"] = "MinerU v1 Agent API"
                return res_dict
            elif state == "failed":
                raise Exception("v1 agent task failed on server side")
            else:
                # waiting-file, running, processing
                continue
                
        raise Exception("v1 agent task poll timeout")

    def _analyze_with_mineru_local(self, image_path: str, output_csv_path: str, url: str) -> dict:
        """调用本地 MinerU /file_parse API"""
        if not url.endswith('/file_parse') and not url.endswith('/tasks'):
            url = f"{url}/file_parse"

        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        backend = self.model_name or "pipeline"

        with open(image_path, "rb") as f:
            files = {"files": f}
            data = {"backend": backend, "return_md": "true"}
            response = requests.post(url, headers=headers, files=files, data=data, timeout=120, verify=False)

        response.raise_for_status()
        res_json = response.json()

        text = ""
        for key in ["markdown", "data", "results"]:
            if key in res_json:
                val = res_json[key]
                if isinstance(val, dict) and "markdown" in val:
                    text = val["markdown"]
                    break
                elif isinstance(val, str) and key == "markdown":
                    text = val
                    break

        if not text:
            logger.warning(f"MinerU response did not contain markdown: {res_json}")
            text = str(res_json)

        return self._parse_result(text.strip(), output_csv_path)

    def _analyze_with_mineru_cloud(self, image_path: str, output_csv_path: str, base_url: str) -> dict:
        """调用 MinerU 云端 API"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        # 1. 申请上传 URL
        filename = os.path.basename(image_path)
        data_id = "img_" + str(int(time.time() * 1000))
        data = {
            "files": [{"name": filename, "data_id": data_id}],
            "model_version": self.model_name or "vlm"
        }

        res = requests.post(
            f"{base_url}/api/v4/file-urls/batch",
            headers=headers, json=data, timeout=30, verify=False
        )
        res.raise_for_status()
        res_json = res.json()
        if res_json.get("code") != 0:
            raise Exception(f"MinerU API Error: {res_json.get('msg')}")

        batch_id = res_json["data"]["batch_id"]
        upload_url = res_json["data"]["file_urls"][0]

        # 2. 上传文件
        with open(image_path, "rb") as f:
            res_upload = requests.put(upload_url, data=f, timeout=120, verify=False)
        res_upload.raise_for_status()

        # 3. 轮询任务状态
        poll_headers = {"Authorization": f"Bearer {self.api_key}", "Accept": "*/*"}
        for _ in range(60):
            time.sleep(5)
            res_poll = requests.get(
                f"{base_url}/api/v4/extract-results/batch/{batch_id}",
                headers=poll_headers, timeout=30, verify=False
            )
            res_poll.raise_for_status()
            poll_json = res_poll.json()
            if poll_json.get("code") != 0:
                raise Exception(f"MinerU API Error: {poll_json.get('msg')}")

            results = poll_json["data"]["extract_result"]
            if not results:
                continue

            task_state = results[0]["state"]
            if task_state == "done":
                return self._download_mineru_zip(results[0]["full_zip_url"], output_csv_path)
            elif task_state == "failed":
                raise Exception(f"MinerU extraction failed: {results[0].get('err_msg', 'Unknown')}")

        raise Exception("MinerU Cloud extraction timed out.")

    def _download_mineru_zip(self, full_zip_url: str, output_csv_path: str) -> dict:
        """下载并解析 MinerU 返回的 ZIP 文件"""
        import zipfile
        zip_res = None
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        }
        for attempt in range(3):
            try:
                try:
                    # 优先使用安全的 verify=True，配合我们的证书路径修复
                    zip_res = requests.get(full_zip_url, headers=headers, timeout=60, verify=True)
                    zip_res.raise_for_status()
                except requests.exceptions.SSLError:
                    # 如果有特殊的代理拦截导致 SSL 校验不通过，回退到 verify=False
                    zip_res = requests.get(full_zip_url, headers=headers, timeout=60, verify=False)
                    zip_res.raise_for_status()
                break
            except Exception as e:
                if attempt < 2:
                    time.sleep(2)
                else:
                    raise Exception(f"Failed to download zip after 3 attempts: {e}")

        with zipfile.ZipFile(io.BytesIO(zip_res.content)) as z:
            md_files = [n for n in z.namelist() if n.endswith('.md')]
            if not md_files:
                return {"type": "text", "content": "", "csv_path": None}
            target_md = "full.md" if "full.md" in md_files else md_files[0]
            with z.open(target_md) as md_f:
                text = md_f.read().decode('utf-8')
                return self._parse_result(text.strip(), output_csv_path)

    def _parse_result(self, text: str, output_csv_path: str, source: str = None) -> dict:
        """解析 API 返回的文本结果"""
        if text:
            text = re.sub(r"<br\s*/?>", " ", text, flags=re.IGNORECASE)

        if text == "RETAIN_IMAGE" or ("RETAIN_IMAGE" in text and len(text) < 20):
            res = {"type": "image", "content": "RETAIN_IMAGE", "csv_path": None}
        elif "|" in text and "-|-" in text.replace(" ", ""):
            text = self._reconstruct_markdown_table(text)
            csv_file = self._markdown_to_csv(text, output_csv_path)
            res = {"type": "table", "content": text, "csv_path": csv_file}
        else:
            res = {"type": "text", "content": text, "csv_path": None}

        if source:
            res["source"] = source
        return res

    def _reconstruct_markdown_table(self, md_text: str) -> str:
        """
        智能重构 Markdown 文本中的表格：
        1. 自动对第一列粘连的 4 位代码和学校名称（如 1433贵州大学）进行拆分。
        2. 重新对齐所有行，确保整张表的列数一致，且其它单元格向后平移。
        """
        lines = md_text.split("\n")
        in_table = False
        table_lines = []
        result_lines = []

        def process_table(t_lines):
            if not t_lines:
                return []

            # 1. 解析所有行
            rows = []
            for line in t_lines:
                stripped = line.strip()
                if stripped.startswith("|"):
                    cells = [c.strip() for c in stripped.split("|")[1:-1]]
                else:
                    cells = [c.strip() for c in stripped.split("|")]
                rows.append((line, cells))

            # 2. 检查每一行是否需要拆分第一列
            processed_rows = []
            has_any_split = False
            for line, cells in rows:
                # 如果是分割线行 (如 |---|---|)，先保留
                if cells and all(re.match(r"^[\s\-:|]+$", c) for c in cells):
                    processed_rows.append(("separator", cells))
                    continue

                # 尝试对第一列进行拆分
                if cells and len(cells) > 0:
                    first_cell = cells[0]
                    split_success = False
                    
                    # 1. 优先根据配置的固定长度拆分
                    if self.split_len and self.split_len > 0:
                        if len(first_cell) > self.split_len:
                            cells = [first_cell[:self.split_len], first_cell[self.split_len:]] + cells[1:]
                            split_success = True
                            has_any_split = True
                            
                    # 2. 其次根据自定义正则拆分
                    if not split_success and self.split_regex:
                        try:
                            m = re.match(self.split_regex, first_cell)
                            if m and len(m.groups()) >= 2:
                                cells = [m.group(1), m.group(2)] + list(m.groups()[2:]) + cells[1:]
                                split_success = True
                                has_any_split = True
                        except Exception:
                            pass
                            
                    # 3. 默认根据内置默认智能正则拆分
                    if not split_success and not self.split_len and not self.split_regex:
                        m = re.match(r"^(\d{4})([一-龥]+.*)$", first_cell)
                        if m:
                            cells = [m.group(1), m.group(2)] + cells[1:]
                            split_success = True
                            has_any_split = True
                processed_rows.append(("data", cells))

            if not has_any_split:
                return t_lines

            # 3. 统计拆分后的最大列数
            max_cols = max(len(cells) for r_type, cells in processed_rows if r_type == "data")

            # 4. 重新构建所有行，保证列数对齐
            new_table_lines = []
            for r_type, cells in processed_rows:
                if r_type == "separator":
                    new_line = "|" + "|".join(["---"] * max_cols) + "|"
                else:
                    # 如果列数不足，说明缺失了学校名称列，在代码后面（第二列）补空单元格
                    if len(cells) < max_cols:
                        cells = [cells[0], ""] + cells[1:]
                    cells = cells + [""] * (max_cols - len(cells))
                    new_line = "| " + " | ".join(cells) + " |"
                new_table_lines.append(new_line)

            return new_table_lines

        for line in lines:
            stripped = line.strip()
            is_tbl_row = stripped.startswith("|") and "|" in stripped

            if is_tbl_row:
                in_table = True
                table_lines.append(line)
            else:
                if in_table:
                    result_lines.extend(process_table(table_lines))
                    table_lines = []
                    in_table = False
                result_lines.append(line)

        if in_table:
            result_lines.extend(process_table(table_lines))

        return "\n".join(result_lines)

    def _analyze_with_local(self, image_path: str) -> dict:
        """使用本地 RapidOCR 分析"""
        if image_path.lower().endswith(".pdf"):
            return {
                "type": "error",
                "content": "本地 OCR 暂不支持直接解析 PDF 文件。请更换为 Gemini API、MinerU API，或将 PDF 转为图片后再上传。",
                "csv_path": None
            }
        try:
            if not self.local_ocr:
                if RapidOCR is None:
                    # 如果未安装 RapidOCR（例如在 Lite 运行环境中），自动降级尝试 System Native OCR！
                    logger.info("RapidOCR not installed. Automatically falling back to System Native OCR...")
                    res = self._analyze_with_system_ocr(image_path)
                    res["source"] = "System Native OCR"
                    return res
                self.local_ocr = RapidOCR()
            result, elapse = self.local_ocr(image_path)
            if not result:
                return {"type": "image", "content": "RETAIN_IMAGE", "csv_path": None}

            # 提取边界框几何特征
            boxes = []
            for box, text, score in result:
                xs = [pt[0] for pt in box]
                ys = [pt[1] for pt in box]
                boxes.append({
                    "text": text,
                    "cx": (min(xs) + max(xs)) / 2,
                    "cy": (min(ys) + max(ys)) / 2,
                    "height": max(ys) - min(ys)
                })

            if not boxes:
                return {"type": "image", "content": "RETAIN_IMAGE", "csv_path": None}

            # 基于 cy 进行行聚类
            boxes.sort(key=lambda b: b["cy"])
            rows = []
            for box in boxes:
                placed = False
                for r in rows:
                    avg_h = (r[0]["height"] + box["height"]) / 2
                    if abs(r[0]["cy"] - box["cy"]) < (avg_h * 0.7):
                        r.append(box)
                        placed = True
                        break
                if not placed:
                    rows.append([box])

            for r in rows:
                r.sort(key=lambda b: b["cx"])
            rows.sort(key=lambda r: sum(b["cy"] for b in r) / len(r))

            # 判定是否属于表格
            multi_col_rows = sum(1 for r in rows if len(r) > 1)
            is_table = len(rows) > 2 and multi_col_rows > len(rows) * 0.4

            if is_table:
                processed_rows = []
                for r in rows:
                    cells = [b["text"] for b in r]
                    if cells and len(cells) > 0:
                        m = re.match(r"^(\d{4})([一-龥]+.*)$", cells[0])
                        if m:
                            cells = [m.group(1), m.group(2)] + cells[1:]
                    processed_rows.append(cells)

                md_lines = []
                col_count = max(len(r) for r in processed_rows)
                for cells in processed_rows:
                    cells = cells + [""] * (col_count - len(cells))
                    md_lines.append("| " + " | ".join(cells) + " |")
                if md_lines:
                    separator = "|" + "|".join(["---"] * col_count) + "|"
                    md_lines.insert(1, separator)
                    return {"type": "table", "content": "\n".join(md_lines), "csv_path": None}

            # 普通文本
            line_texts = ["\t".join(b["text"] for b in r) for r in rows]
            return {"type": "text", "content": "\n".join(line_texts), "csv_path": None}

        except Exception as e:
            # 如果本地 RapidOCR 运行出错，或者缺失，均尝试用系统原生 OCR 进行最终兜底
            logger.warning(f"Local OCR failed or not installed: {e}. Trying System Native OCR as fallback...")
            try:
                res = self._analyze_with_system_ocr(image_path)
                res["source"] = "System Native OCR"
                return res
            except Exception as se:
                logger.error(f"System OCR also failed: {se}")
                return {"type": "image", "content": "RETAIN_IMAGE", "csv_path": None}

    def _analyze_with_system_ocr(self, image_path: str) -> dict:
        """跨平台系统原生 OCR 调度引擎（自动适配 Windows / macOS / Linux）"""
        import sys
        try:
            from PIL import Image
            img = Image.open(image_path)
            width, height = img.size
            boxes = []

            if sys.platform == "win32":
                # Windows Built-in OCR
                import winocr
                result = winocr.recognize_pil_sync(img)
                lines = result.get("lines", [])
                for line in lines:
                    line_text = line.get("text", "")
                    words = line.get("words", [])
                    if not words:
                        continue
                    
                    min_x, min_y = float('inf'), float('inf')
                    max_right, max_bottom = float('-inf'), float('-inf')
                    for w in words:
                        rect = w.get("bounding_rect", {})
                        if rect:
                            x, y = rect.get("x", 0), rect.get("y", 0)
                            w_v, h_v = rect.get("width", 0), rect.get("height", 0)
                            min_x = min(min_x, x)
                            min_y = min(min_y, y)
                            max_right = max(max_right, x + w_v)
                            max_bottom = max(max_bottom, y + h_v)
                    
                    if min_x == float('inf') or min_y == float('inf'):
                        continue
                    w_val = max_right - min_x
                    h_val = max_bottom - min_y
                    boxes.append({
                        "text": line_text,
                        "cx": min_x + w_val / 2,
                        "cy": min_y + h_val / 2,
                        "height": h_val
                    })

            elif sys.platform == "darwin":
                # macOS Vision OCR
                from ocrmac import ocrmac
                # ocrmac.OCR 返回的 bbox 格式为归一化的 [x, y, w, h] (且以左下角为原点)
                annotations = ocrmac.OCR(image_path).recognize()
                for text, confidence, bbox in annotations:
                    if not text or not bbox:
                        continue
                    x, y, w, h = bbox
                    cx = (x + w / 2) * width
                    cy = (1.0 - y - h / 2) * height
                    box_height = h * height
                    boxes.append({
                        "text": text,
                        "cx": cx,
                        "cy": cy,
                        "height": box_height
                    })

            else:
                # Linux / Docker (基于系统 Tesseract OCR 可执行文件)
                import pytesseract
                langs = 'eng'
                try:
                    available_langs = pytesseract.get_languages()
                    if 'chi_sim' in available_langs:
                        langs = 'chi_sim+eng'
                except Exception:
                    pass
                
                data = pytesseract.image_to_data(img, lang=langs, output_type=pytesseract.Output.DICT)
                n_boxes = len(data['level'])
                lines_map = {}
                for i in range(n_boxes):
                    if data['level'][i] == 5: # 单词/字 级
                        text = data['text'][i].strip()
                        if not text:
                            continue
                        block = data['block_num'][i]
                        par = data['par_num'][i]
                        line = data['line_num'][i]
                        line_key = (block, par, line)
                        
                        x, y, w, h = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
                        if line_key not in lines_map:
                            lines_map[line_key] = {"words": [], "text_parts": []}
                        lines_map[line_key]["words"].append({"x": x, "y": y, "w": w, "h": h})
                        lines_map[line_key]["text_parts"].append(text)
                
                for key, val in lines_map.items():
                    words = val["words"]
                    line_text = " ".join(val["text_parts"])
                    min_x = min(w["x"] for w in words)
                    min_y = min(w["y"] for w in words)
                    max_right = max(w["x"] + w["w"] for w in words)
                    max_bottom = max(w["y"] + w["h"] for w in words)
                    
                    w_val = max_right - min_x
                    h_val = max_bottom - min_y
                    boxes.append({
                        "text": line_text,
                        "cx": min_x + w_val / 2,
                        "cy": min_y + h_val / 2,
                        "height": h_val
                    })

            if not boxes:
                return {"type": "image", "content": "RETAIN_IMAGE", "csv_path": None}

            # 基于 cy 进行行聚类 (完全复用原有行排序与表格检测算法)
            boxes.sort(key=lambda b: b["cy"])
            rows = []
            for box in boxes:
                placed = False
                for r in rows:
                    avg_h = (r[0]["height"] + box["height"]) / 2
                    if abs(r[0]["cy"] - box["cy"]) < (avg_h * 0.7):
                        r.append(box)
                        placed = True
                        break
                if not placed:
                    rows.append([box])

            for r in rows:
                r.sort(key=lambda b: b["cx"])
            rows.sort(key=lambda r: sum(b["cy"] for b in r) / len(r))

            # 判定是否属于表格
            multi_col_rows = sum(1 for r in rows if len(r) > 1)
            is_table = len(rows) > 2 and multi_col_rows > len(rows) * 0.4

            if is_table:
                processed_rows = []
                for r in rows:
                    cells = [b["text"] for b in r]
                    if cells and len(cells) > 0:
                        m = re.match(r"^(\d{4})([一-龥]+.*)$", cells[0])
                        if m:
                            cells = [m.group(1), m.group(2)] + cells[1:]
                    processed_rows.append(cells)

                md_lines = []
                col_count = max(len(r) for r in processed_rows)
                for cells in processed_rows:
                    cells = cells + [""] * (col_count - len(cells))
                    md_lines.append("| " + " | ".join(cells) + " |")
                if md_lines:
                    separator = "|" + "|".join(["---"] * col_count) + "|"
                    md_lines.insert(1, separator)
                    return {"type": "table", "content": "\n".join(md_lines), "csv_path": None}

            # 普通文本
            line_texts = ["\t".join(b["text"] for b in r) for r in rows]
            return {"type": "text", "content": "\n".join(line_texts), "csv_path": None}

        except Exception as e:
            logger.error(f"System Native OCR error on {image_path}: {e}")
            return {"type": "image", "content": "RETAIN_IMAGE", "csv_path": None}

    def _markdown_to_csv(self, md_text: str, output_path: str) -> str | None:
        """将 Markdown 表格转为 CSV 文件"""
        lines = md_text.strip().split("\n")
        table_lines = [line.strip() for line in lines if "|" in line]

        if not table_lines or not output_path:
            return None

        with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            for line in table_lines:
                if set(line.replace("|", "").replace("-", "").replace(" ", "").replace(":", "")) == set():
                    continue
                row = [cell.strip() for cell in line.split("|")[1:-1]]
                writer.writerow(row)

        return output_path
