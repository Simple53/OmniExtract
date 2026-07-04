"""
OmniExtract 系统托盘管理器
- 后台启动 uvicorn 服务
- 系统托盘图标常驻，支持打开网页、打开输出目录、退出
- 支持有窗口和无窗口两种运行模式
"""
import os
import sys
import threading
import time
import webbrowser
import logging

if getattr(sys, 'frozen', False):
    # PyInstaller temp directory for bundled files (logo)
    bundle_dir = sys._MEIPASS
    # Directory containing the actual .exe for logs and output
    data_dir = os.path.dirname(sys.executable)
else:
    bundle_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = bundle_dir

# 日志配置：始终写入文件，确保无窗口模式下不因 stdout=None 而崩溃
log_file = os.path.join(data_dir, "server.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.FileHandler(log_file, encoding="utf-8")]
)
logger = logging.getLogger("TrayIcon")

# 在无窗口模式 (pythonw.exe) 下，sys.stdout/stderr 为 None，
# 所有 print() 和 uvicorn 的日志输出都会抛 AttributeError 导致崩溃。
# 将它们重定向到日志文件。
if sys.stdout is None or sys.stderr is None:
    _log_stream = open(log_file, "a", encoding="utf-8", buffering=1)
    sys.stdout = _log_stream
    sys.stderr = _log_stream

# 清除 Conda 环境变量干扰
for key in list(os.environ.keys()):
    if "CONDA" in key.upper():
        del os.environ[key]

import uvicorn
from PIL import Image
import pystray

try:
    from server import app
except Exception as e:
    logger.exception("Failed to import FastAPI app from server.py:")
    sys.exit(1)


def run_server():
    """在子线程中启动 uvicorn 服务"""
    try:
        config = uvicorn.Config(
            app,
            host="127.0.0.1",
            port=8000,
            log_level="info"
        )
        config.install_signal_handlers = False
        server = uvicorn.Server(config)
        server.run()
    except Exception as e:
        logger.exception("Uvicorn server crashed:")


def on_open_webpage(icon, item):
    """打开网页界面"""
    logger.info("Tray menu: Open Webpage")
    webbrowser.open("http://127.0.0.1:8000")


def on_open_output(icon, item):
    """打开输出目录"""
    logger.info("Tray menu: Open Output Directory")
    output_dir = os.path.join(data_dir, "output")
    os.makedirs(output_dir, exist_ok=True)
    try:
        os.startfile(output_dir)
    except Exception as e:
        logger.error(f"Failed to open output directory: {e}")


def on_exit(icon, item):
    """退出应用"""
    logger.info("Tray menu: Exit")
    icon.stop()
    os._exit(0)


def main():
    logger.info("Starting OmniExtract tray manager...")

    # 1. 启动后台服务线程
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    # 2. 加载托盘图标（透明背景 PNG）
    logo_path = os.path.join(bundle_dir, "static", "logo.png")
    if os.path.exists(logo_path):
        try:
            image = Image.open(logo_path)
        except Exception as e:
            logger.error(f"Failed to load logo.png: {e}")
            image = Image.new("RGBA", (64, 64), (59, 130, 246, 255))
    else:
        logger.warning("logo.png not found, using fallback icon.")
        image = Image.new("RGBA", (64, 64), (59, 130, 246, 255))

    # 3. 检测系统语言，决定托盘菜单文字
    is_chinese = False
    try:
        import ctypes
        lang_id = ctypes.windll.kernel32.GetUserDefaultUILanguage()
        # Chinese language IDs: 0x0804 (zh-CN), 0x0404 (zh-TW), 0x0C04 (zh-HK)
        is_chinese = (lang_id & 0xFF) == 0x04
    except Exception:
        import locale
        sys_lang = locale.getdefaultlocale()[0] or ""
        is_chinese = sys_lang.startswith("zh")

    if is_chinese:
        label_open = "打开网页界面"
        label_output = "打开输出目录"
        label_exit = "退出"
    else:
        label_open = "Open Webpage"
        label_output = "Open Output Folder"
        label_exit = "Exit"

    # 4. 定义托盘右键菜单
    menu = pystray.Menu(
        pystray.MenuItem(label_open, on_open_webpage, default=True),
        pystray.MenuItem(label_output, on_open_output),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(label_exit, on_exit)
    )

    icon = pystray.Icon(
        "OmniExtract",
        image,
        "OmniExtract",
        menu=menu
    )

    # uvicorn 会在 lifespan 中自动触发打开浏览器，此处不再重复调用

    # 5. 在主线程中阻塞运行托盘（pystray 要求主线程）
    logger.info("Tray icon running. Right-click to see menu.")
    icon.run()


if __name__ == "__main__":
    main()
