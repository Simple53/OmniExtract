<div align="center">

<img src="static/logo.png" alt="OmniExtract Logo" width="150" style="border-radius: 16px;" />

# OmniExtract 万象多模态提取引擎 / Multimodal Extraction Engine

**极速、极简的网页/图片多模态数据提取工具**  
*Fast and minimalist multimodal data extraction tool for web pages, documents, and images.*

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776ab?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Release](https://img.shields.io/github/v/release/Simple53/OmniExtract?color=green)](https://github.com/Simple53/OmniExtract/releases)
[![Windows EXE](https://img.shields.io/badge/Windows-EXE-0078D4?logo=windows&logoColor=white)](https://github.com/Simple53/OmniExtract/releases)
[![Docker](https://img.shields.io/badge/Docker-支持-2496ED?logo=docker&logoColor=white)](https://hub.docker.com/)

[English](#english) | [中文说明](#中文说明)

</div>

---

## English

### ✨ Key Features

| Feature | Description |
|---|---|
| 🌐 **Web Image Scraping** | Input URL, automatically filter and scrape valid body images, skipping icons, ads, QR codes, etc. Powered by `DrissionPage` headless browser to bypass anti-crawler systems (like Zhihu, Toutiao). |
| ✂️ **Smart Image Slicing** | Automatically split long screenshots vertically using horizontal projection, preventing text lines from being cut in half. |
| 🤖 **Multi-Engine OCR/VLM** | Support Gemini Vision, OpenAI Compatible API, MinerU API, and Local RapidOCR, with automatic fallback cascade. |
| 📊 **Table Structure Recovery** | Smartly identify and reconstruct Excel tables, keeping merged cell structures intact. |
| 🖼️ **Multi-Format Export** | Support Markdown, TXT, HTML, Word (docx), LaTeX, CSV, Excel, and unified ZIP package downloads. |
| 📡 **SSE Real-time Progress** | Stream processing status via Server-Sent Events (SSE) for real-time visualization of task progress. |
| ✏️ **Online Editor** | Manually modify the markdown content of any slice, delete redundant slices, and re-merge. |
| 🔄 **Breakpoint Resume** | Load historical session data to resume processing from where it was interrupted. |
| 🌙 **Theme Switch** | Dual support for light and dark themes. |

---

### 🚀 Quick Start

#### Method 1: Run EXE (Windows, Recommended)
1. Go to [Releases Page](https://github.com/Simple53/OmniExtract/releases).
2. Download `OmniExtract-lite.exe` (Lite version, ~25MB) or `OmniExtract-full.exe` (Full version with local offline OCR, ~105MB).
3. Double-click the EXE to run. The browser will automatically open `http://127.0.0.1:8000`.

#### Method 2: Docker Deployment
No Python setup required. Fast and clean.
```bash
git clone https://github.com/Simple53/OmniExtract.git
cd OmniExtract
docker build -t omniextract .
docker run -d -p 8000:8000 --name omniextract omniextract
```
Access the application at `http://localhost:8000`.

#### Method 3: Local Python Run
**Requirements: Python 3.10+**
```bash
git clone https://github.com/Simple53/OmniExtract.git
cd OmniExtract

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Run server
python server.py
```
Or double-click `start.bat` on Windows.

---

### 📖 User Guide

1. **Configure API Engine**: Select your preferred engine in the right configuration panel (Gemini, OpenAI, MinerU, or Local/System OCR).
   - **For MinerU Key**: You can visit [MinerU Website](https://mineru.net/), go to the top right **Personal Center -> Key Management -> Add Key** to get a free API Key, and enter it into the **MinerU Token** input field.
2. **Extract Web Pages**: Paste the URL into the input field and click "Start Extraction".
3. **Extract Local Files**: Drag and drop images, PDFs, or PPT files into the drop area, or paste images directly via clipboard (Ctrl+V).
4. **Edit & Output**: Review slice details, edit markdown, delete unwanted parts, and export to Word, PDF, LaTeX, Excel, etc.

---

## 中文说明

### ✨ 核心功能

| 功能 | 说明 |
|---|---|
| 🌐 **网页图片抓取** | 输入 URL，自动过滤并抓取网页正文有效图片，跳过图标、广告图、二维码等。集成 `DrissionPage` 无头静默浏览器，完美穿透知乎、头条等强反爬 JS 校验。 |
| ✂️ **智能无缝切片** | 基于水平投影法自动分割长截图，精准避免切断文字行。 |
| 🤖 **多引擎 OCR/VLM** | 支持 Gemini Vision、OpenAI 兼容接口、MinerU API、本地 RapidOCR 以及系统原生 OCR，支持自动降级回退。 |
| 📊 **表格结构还原** | 智能识别并导出带合并单元格的 Excel 表格。 |
| 🖼️ **多格式导出** | 支持 Markdown、TXT、HTML、Word (docx)、LaTeX、CSV、Excel 以及 ZIP 打包下载。 |
| 📡 **SSE 实时进度** | 流式推送识别进度，切片状态实时可见。 |
| ✏️ **在线编辑** | 可手动修正切片识别结果、删除废弃切片，然后重新合并导出。 |
| 🔄 **断点续传** | 任务中断后可从中断点继续识别。 |
| 🌙 **主题切换** | 支持深色/浅色模式。 |

---

### 🚀 快速开始

#### 方式一：下载 EXE（Windows，最简单）
1. 前往 [Releases 页面](https://github.com/Simple53/OmniExtract/releases)。
2. 下载 `OmniExtract-lite.exe`（轻量版，约 25MB）或 `OmniExtract-full.exe`（内置离线 OCR，约 105MB）。
3. 双击运行，浏览器会自动打开 `http://127.0.0.1:8000`。

#### 方式二：🐳 Docker 部署（推荐）
```bash
git clone https://github.com/Simple53/OmniExtract.git
cd OmniExtract
docker build -t omniextract .
docker run -d -p 8000:8000 --name omniextract omniextract
```
启动后打开浏览器访问 `http://localhost:8000`。

#### 方式三：🐍 本地 Python 运行
**环境要求：Python 3.10+**
```bash
git clone https://github.com/Simple53/OmniExtract.git
cd OmniExtract

python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux

pip install -r requirements.txt
python server.py
```
或直接双击运行 `start.bat`。

---

### 📖 使用指南

1. **配置 API 引擎**：在右侧 **“隐藏配置/显示配置”** 面板中选择适合的 OCR 或 VLM 引擎（支持 Gemini、OpenAI 兼容接口、MinerU 或本地原生 OCR）。
   - **申请 MinerU Key**：您可以访问 [MinerU 官网](https://mineru.net/)，在右上角 **“个人中心” —— “秘钥管理” —— “添加秘钥”** 免费申请您的 API Key，并配置填入面板中的 **MinerU Token** 输入框。
2. **提取网页内容**：输入目标网页 URL，点击“开始提取”按键，系统会自动抓取并过滤正文图片、执行智能无缝切片并流式推送识别进度。
3. **提取本地文件**：支持点击选择或直接向中心区域拖入本地文件（支持图片、PDF、PPT 等），或者通过剪贴板（Ctrl+V）直接粘贴截图加入提取队列。
4. **人工校对与保存**：在“切片明细”中对比原图和识别文字进行任意局部保存，支持在“合成结果预览”中对完整的排版 Markdown 进行实时编辑与保存，最后打包导出为 Word、PDF、Markdown 或 Excel 等。

---

### 🏗️ Directory Structure / 项目结构
```
OmniExtract/
├── server.py              # FastAPI 后端主程序 (API & Routing)
├── scraper.py             # 网页图片抓取与过滤 (DrissionPage/Requests)
├── slicer.py              # 基于水平投影的智能图像切片 (Pillow/Numpy)
├── analyzer.py            # 多引擎 OCR/VLM 分析与降级 (Multi-engine Analyzer)
├── index.html             # 前端单页应用 (Single-page App)
├── requirements.txt       # Python 依赖清单
├── Dockerfile             # Docker 容器构建文件
├── start.bat              # Windows 一键前台启动脚本 (Windows Foreground Startup Script)
├── tray_icon.py           # 托盘管理与后台运行服务 (System Tray & Background Manager)
├── 启动(后台无窗口).vbs    # Windows 一键后台静默启动脚本 (Windows Background Silent Startup Script)
├── 停止(关闭后台).bat      # Windows 一键停止后台服务脚本 (Windows Stop Background Server Script)
├── static/
│   ├── logo.png           # 透明背景主图标 (Main Logo Image)
│   ├── logo.ico           # Windows 多分辨率图标 (Windows multi-res Icon)
│   ├── logo_dark.ico      # 暗色调多分辨率图标 (Dark theme multi-res Icon)
│   ├── logo_dark.jpg      # 备用暗色背景图 (Alternative dark background image)
│   ├── logo_[size].png    # 各尺寸分级适配图标 (Icon images of various sizes)
│   ├── css/all.min.css    # FontAwesome 图标库
│   ├── js/marked.min.js   # Markdown 渲染库
│   └── webfonts/          # 字体文件
└── output/                # 任务输出目录 (Output Directory)
```
