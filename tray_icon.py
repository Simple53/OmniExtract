import os
import sys
import ctypes
import threading
import time
import webbrowser
import uvicorn
from PIL import Image
import pystray

# Window management on Windows
hwnd = None
if sys.platform == "win32":
    hwnd = ctypes.windll.kernel32.GetConsoleWindow()

def disable_close_button():
    if hwnd:
        # Get system menu of the console window
        hmenu = ctypes.windll.user32.GetSystemMenu(hwnd, False)
        if hmenu:
            # Disable (gray out) the Close (X) button
            ctypes.windll.user32.EnableMenuItem(hmenu, 0xF060, 1 | 2) # SC_CLOSE, MF_GRAYED | MF_DISABLED

def hide_console():
    if hwnd:
        ctypes.windll.user32.ShowWindow(hwnd, 0)  # SW_HIDE

def show_console():
    if hwnd:
        ctypes.windll.user32.ShowWindow(hwnd, 5)  # SW_SHOW
        # Set focus to console window
        ctypes.windll.user32.SetForegroundWindow(hwnd)

def open_webpage():
    webbrowser.open("http://127.0.0.1:8000")

def run_server():
    from server import app
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")

def on_exit(icon, item=None):
    if icon:
        icon.stop()
    # Force exit the entire process and all threads
    os._exit(0)

def main():
    # 1. Disable console close button to prevent accidental clicks
    disable_close_button()

    print("==================================================================")
    print("  OmniExtract (万象多模态提取引擎) 服务正在启动...")
    print("  提示: 窗口右上角的 '关闭 (X)' 按钮已被禁用以防止意外退出。")
    print("  - 如需隐藏控制台，请右击系统托盘图标选择 '隐藏控制台'。")
    print("  - 如需完全退出服务，请在控制台按 Ctrl+C，或右击托盘选择 '退出'。")
    print("==================================================================")
    print()

    # 2. Start uvicorn server in a daemon thread
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    # 3. Create tray icon
    logo_path = os.path.join(os.path.dirname(__file__), "static", "logo.png")
    try:
        image = Image.open(logo_path)
    except Exception:
        image = Image.new("RGB", (64, 64), color="blue")

    menu = pystray.Menu(
        pystray.MenuItem("打开网页 (Open Webpage)", lambda: open_webpage()),
        pystray.MenuItem("显示控制台 (Show Console)", lambda: show_console()),
        pystray.MenuItem("隐藏控制台 (Hide Console)", lambda: hide_console()),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("退出服务 (Exit)", lambda icon, item: on_exit(icon, item))
    )

    icon = pystray.Icon(
        "omniextract",
        image,
        "万象 OmniExtract",
        menu=menu
    )

    # Start tray icon in a separate thread so main thread can catch Ctrl+C
    tray_thread = threading.Thread(target=icon.run, daemon=True)
    tray_thread.start()

    # 4. Open webpage in browser automatically
    # Wait a brief moment for uvicorn to bind to port
    time.sleep(1.0)
    open_webpage()

    # 5. Main loop to catch Ctrl+C and prompt the user
    while True:
        try:
            while True:
                time.sleep(0.5)
        except KeyboardInterrupt:
            # Bring console to front to ensure user sees the prompt
            show_console()
            print()
            try:
                # Prompt user for action
                choice = input("检测到 Ctrl+C。是否要完全退出服务？[Y/N] (输入 N 将隐藏并最小化到托盘): ").strip().lower()
                if choice in ("y", "yes"):
                    print("正在关闭服务...")
                    on_exit(icon)
                else:
                    hide_console()
                    print("已最小化并隐藏到系统托盘运行。")
            except Exception:
                # Fallback if input fails (e.g. running in non-tty)
                hide_console()

if __name__ == "__main__":
    main()
