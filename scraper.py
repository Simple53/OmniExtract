import os
import re
import urllib.parse
import requests
from bs4 import BeautifulSoup
import logging
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)

# 图片过滤垃圾关键词（URL、类名、ID、ALT 属性等匹配）
SKIP_KEYWORDS = frozenset([
    'icon', 'logo', 'avatar', 'button', 'qr', 'qrcode', 'barcode', 'bg', 'spacer', 
    'blank', 'loading', 'placeholder', 'pixel', 'tracking', 'ad', 'advertisement', 
    'banner', 'share', 'header', 'footer', 'sidebar', 'nav', 'sprite', 'emoticon', 
    'emoji', 'wechat', 'weixin', 'subscribe', 'follow', 'gzh', 'mpweixin', 'scan', 
    'pay', 'alipay', 'reward', 'donate', 'zan', 'thumb', 'app-download', 'client'
])
SKIP_EXTENSIONS = frozenset(['.gif'])  # 通常 GIF 是动画/装饰图标


class WebScraper:
    """网页图片抓取器"""

    # 常见反爬站点首页 (用于预热 Cookie)
    _KNOWN_ANTI_CRAWL = {
        "zhihu.com": "https://www.zhihu.com/",
        "weibo.com": "https://weibo.com/",
        "bilibili.com": "https://www.bilibili.com/",
        "toutiao.com": "https://www.toutiao.com/",
        "jianshu.com": "https://www.jianshu.com/",
    }

    def __init__(self, output_dir: str = "temp_downloads"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        self.session = requests.Session()
        self.session.trust_env = False  # 禁用系统代理环境变量，防止开启本地代理软件时请求超时
        self._set_browser_headers()

    def _set_browser_headers(self, referer: str = None):
        """设置完整的 Chrome 浏览器指纹 headers"""
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-CH-UA": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
            "Sec-CH-UA-Mobile": "?0",
            "Sec-CH-UA-Platform": '"Windows"',
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
        }
        if referer:
            headers["Referer"] = referer
        self.session.headers.update(headers)

    def _warmup_cookies(self, url: str):
        """对已知反爬站点预热 Cookie：先访问其首页获取必要 Cookie"""
        parsed = urllib.parse.urlparse(url)
        hostname = parsed.netloc.lower()
        for domain, home_url in self._KNOWN_ANTI_CRAWL.items():
            if domain in hostname:
                try:
                    logger.info(f"Pre-warming cookies for {domain}...")
                    self.session.headers.update({
                        "Sec-Fetch-Site": "none",
                        "Sec-Fetch-Mode": "navigate",
                    })
                    self.session.get(home_url, timeout=10, verify=False, allow_redirects=True)
                    # 更新 Referer 为首页，模拟从首页跳转到文章
                    self.session.headers.update({
                        "Referer": home_url,
                        "Sec-Fetch-Site": "same-origin",
                    })
                    logger.info(f"Cookie warm-up done for {domain}.")
                except Exception as e:
                    logger.warning(f"Cookie warm-up failed for {domain}: {e}")
                break

    def _fetch_html_with_drission(self, url: str) -> str | None:
        """使用 DrissionPage 驱动本地 Chrome 浏览器加载页面并返回完整的 HTML（解决反爬和 JS 动态加载）"""
        try:
            import time
            from DrissionPage import ChromiumPage, ChromiumOptions
            
            logger.info("DrissionPage detected. Using local Chrome browser (headless) to load page...")
            
            # 配置无头模式运行，避免显示浏览器窗口打扰用户
            co = ChromiumOptions()
            try:
                co.set_headless(True)
                co.set_argument('--no-sandbox')
                co.set_argument('--disable-gpu')
            except Exception as e:
                logger.warning(f"Failed to set headless options: {e}")

            page = ChromiumPage(addr_or_opts=co)
            try:
                page.get(url)
                # 等待页面加载和渲染
                time.sleep(3)
                
                # 针对知乎等网页，自动检测并关闭可能会遮挡/卡住内容的登录弹窗
                try:
                    for selector in [
                        '.Modal-closeButton', 
                        'button[aria-label="关闭"]', 
                        '.Modal-wrapper button.close',
                        '.signFlowModal-closeButton',
                        'button.Button.Modal-closeButton.Button--plain'
                    ]:
                        btn = page.ele(selector, timeout=1.5)
                        if btn:
                            btn.click()
                            logger.info(f"Closed login modal overlay using selector: {selector}")
                            time.sleep(1)
                            break
                except Exception:
                    pass

                # 解锁 body 滚动条限制（部分遮罩弹窗会锁定 overflow: hidden）
                try:
                    page.run_js("document.body.style.overflow = 'auto';")
                except Exception:
                    pass

                # 简单向下滚动以加载懒加载的图片
                try:
                    page.scroll.down(2000)
                    time.sleep(2)
                except Exception:
                    pass

                # 将浏览器端的 Cookies 复制给 requests 会话，使之后的图片下载请求能通过防盗链
                try:
                    cookies = page.cookies(as_dict=True)
                    if cookies:
                        self.session.cookies.update(cookies)
                        logger.info("Successfully copied browser cookies to requests session.")
                except Exception as ce:
                    logger.warning(f"Failed to copy cookies from DrissionPage: {ce}")

                html_content = page.html
                return html_content
            finally:
                page.quit()
        except Exception as e:
            logger.warning(f"DrissionPage failed or not installed: {e}. Falling back to standard requests.")
            return None

    def fetch_images(self, url: str) -> list:
        """
        抓取网页中的图片并下载到本地。
        返回本地文件路径列表。
        """
        logger.info(f"Fetching URL: {url}")
        
        # 优先使用 DrissionPage（调用本地 Chrome 解决 JS 渲染与反爬）
        html_content = self._fetch_html_with_drission(url)
        
        if not html_content:
            try:
                # 1. 预热 Cookie（针对知乎等有反爬保护的网站）
                self._warmup_cookies(url)

                # 2. 请求目标页面
                response = self.session.get(url, timeout=20, verify=False, allow_redirects=True)

                # 3. 如果仍然 403，尝试带更多 headers 重试一次
                if response.status_code == 403:
                    logger.warning(f"Got 403, retrying with extended headers: {url}")
                    retry_headers = {
                        "Referer": f"{urllib.parse.urlparse(url).scheme}://{urllib.parse.urlparse(url).netloc}/",
                        "Sec-Fetch-Site": "same-origin",
                        "Sec-Fetch-Mode": "navigate",
                        "Sec-Fetch-Dest": "document",
                        "Pragma": "no-cache",
                        "Cache-Control": "no-cache",
                    }
                    self.session.headers.update(retry_headers)
                    response = self.session.get(url, timeout=20, verify=False, allow_redirects=True)

                response.raise_for_status()
                response.encoding = response.apparent_encoding
                html_content = response.text
            except Exception as e:
                logger.error(f"Error fetching URL {url} with requests: {e}")
                return []

        try:
            soup = BeautifulSoup(html_content, 'html.parser')

            # 尝试定位主内容区域，避免抓取 header/footer 图片
            main_content = (
                soup.find('div', id=re.compile(r'zoom|content|article|detail', re.I))
                or soup.find('div', class_=re.compile(r'content|article|detail', re.I))
                or (soup.body if soup.body else soup)
            )

            img_tags = main_content.find_all('img')
            downloaded_paths = []

            for i, img in enumerate(img_tags):
                # 新增：直接检查 img 节点的属性（如 class, id, alt）进行拦截
                if self._should_skip_img_tag(img):
                    continue

                img_url = self._extract_img_url(img)
                if not img_url:
                    continue

                full_img_url = urllib.parse.urljoin(url, img_url)

                # 跳过图标类图片
                if self._should_skip_url(full_img_url):
                    continue

                logger.info(f"Found image: {full_img_url}")
                local_path = self.download_image(full_img_url, i, referer=url)
                if local_path:
                    downloaded_paths.append(local_path)

            return downloaded_paths
        except requests.RequestException as e:
            logger.error(f"Request error fetching {url}: {e}")
            return []
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return []

    def _extract_img_url(self, img) -> str | None:
        """从 img 标签中提取最佳图片 URL（支持懒加载）"""
        # 优先级：data-original > data-src > original > data-lazy-src > src
        for attr in ['data-original', 'data-src', 'original', 'data-lazy-src', 'src']:
            val = img.get(attr)
            if val and not val.strip().startswith("data:image"):
                val_lower = val.lower()
                if not any(kw in val_lower for kw in SKIP_KEYWORDS):
                    return val.strip()

        # 兜底：取 src
        return img.get('src') or img.get('data-src')

    def _should_skip_img_tag(self, img) -> bool:
        """通过检查 img 标签的属性（如 class、id、alt、title 等）判定是否应该跳过"""
        for attr in ['class', 'id', 'alt', 'title']:
            val = img.get(attr)
            if not val:
                continue
            # BeautifulSoup 针对 class 属性通常解析为 list
            val_str = " ".join(val) if isinstance(val, list) else str(val)
            val_lower = val_str.lower()
            if any(kw in val_lower for kw in SKIP_KEYWORDS):
                logger.info(f"Skipping image tag due to {attr} attribute: '{val_str}'")
                return True
        return False

    def _should_skip_url(self, url: str) -> bool:
        """判断是否应该跳过该 URL"""
        url_lower = url.lower()
        if any(kw in url_lower for kw in SKIP_KEYWORDS):
            return True
        # 跳过 data URI
        if url_lower.startswith('data:'):
            return True
        return False

    def download_image(self, img_url: str, index: int, referer: str = None) -> str | None:
        """下载单张图片到本地"""
        try:
            img_headers = {
                "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
                "Sec-Fetch-Dest": "image",
                "Sec-Fetch-Mode": "no-cors",
                "Sec-Fetch-Site": "same-origin" if referer else "none",
            }
            if referer:
                img_headers["Referer"] = referer

            resp = self.session.get(img_url, timeout=20, stream=True, verify=False, headers=img_headers)
            resp.raise_for_status()

            # 确定文件扩展名
            ext = self._get_extension(img_url, resp.headers.get("Content-Type", ""))

            filename = f"image_{index:03d}{ext}"
            filepath = os.path.join(self.output_dir, filename)

            with open(filepath, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)

            # 过滤小于 10KB 的文件（过滤图标、追踪像素、小修饰图和按钮）
            if os.path.getsize(filepath) < 10240:
                os.remove(filepath)
                return None

            return filepath
        except requests.RequestException as e:
            logger.error(f"Download error for {img_url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error downloading {img_url}: {e}")
            return None

    def _get_extension(self, img_url: str, content_type: str) -> str:
        """根据 Content-Type 和 URL 推断文件扩展名"""
        content_type = content_type.lower()
        type_map = {
            "png": ".png",
            "gif": ".gif",
            "webp": ".webp",
            "jpeg": ".jpg",
            "jpg": ".jpg",
        }
        for key, ext in type_map.items():
            if key in content_type:
                return ext

        # 从 URL 路径推断
        path = urllib.parse.urlparse(img_url).path
        _, path_ext = os.path.splitext(path)
        if path_ext.lower() in [".jpg", ".jpeg", ".png", ".gif", ".webp"]:
            return path_ext.lower()

        return ".jpg"
