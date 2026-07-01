<div align="center">

<img src="static/logo.jpg" alt="OmniExtract Logo" width="100" style="border-radius: 16px;" />

# OmniExtract 万象多模态提取引擎

**极速、极简的网页/图片多模态数据提取工具**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776ab?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Release](https://img.shields.io/github/v/release/Simple53/OmniExtract?color=green)](https://github.com/Simple53/OmniExtract/releases)
[![Windows EXE](https://img.shields.io/badge/Windows-EXE-0078D4?logo=windows&logoColor=white)](https://github.com/Simple53/OmniExtract/releases)
[![Docker](https://img.shields.io/badge/Docker-支持-2496ED?logo=docker&logoColor=white)](https://hub.docker.com/)

[📦 下载 EXE](https://github.com/Simple53/OmniExtract/releases) · [🐳 Docker 部署](#-docker-部署推荐) · [🔧 本地运行](#-本地-python-运行) · [📖 使用说明](#-使用说明)

</div>

---

## ✨ 核心功能

| 功能 | 说明 |
|---|---|
| 🌐 **网页图片抓取** | 输入 URL，自动过滤并抓取网页正文有效图片，跳过图标、广告图、二维码等干扰项 |
| ✂️ **智能无缝切片** | 基于水平投影法自动分割长截图，精准避免切断文字行 |
| 🤖 **多引擎 OCR/VLM** | 支持 Gemini Vision、OpenAI 兼容、MinerU API、本地 RapidOCR，自动降级回退 |
| 📊 **表格结构还原** | 智能识别并导出带合并单元格的 Excel 表格 |
| 🖼️ **多格式导出** | Markdown、TXT、HTML、Word (docx)、LaTeX、CSV、Excel、ZIP 打包 |
| 📡 **SSE 实时进度** | 流式推送识别进度，切片状态实时可见 |
| ✏️ **在线编辑** | 可手动修正切片识别结果、删除废弃切片，然后重新合并导出 |
| 🔄 **断点续传** | 任务中断后可从中断点继续识别 |
| 🌙 **主题切换** | 支持深色/浅色模式 |

---

## 🚀 快速开始

### 方式一：下载 EXE（Windows，最简单）

1. 前往 [Releases 页面](https://github.com/Simple53/OmniExtract/releases) 下载 `OmniExtract.exe`
2. 双击运行，浏览器会自动打开 `http://127.0.0.1:8000`

---

### 方式二：🐳 Docker 部署（推荐）

最简单的服务器部署方式，开箱即用，无需安装 Python 环境。

```bash
# 克隆项目
git clone https://github.com/Simple53/OmniExtract.git
cd OmniExtract

# 构建并启动
docker build -t omniextract .
docker run -d -p 8000:8000 --name omniextract omniextract
```

启动后打开浏览器访问 `http://localhost:8000`

---

### 方式三：🐍 本地 Python 运行

**环境要求：Python 3.10+**

```bash
# 1. 克隆项目
git clone https://github.com/Simple53/OmniExtract.git
cd OmniExtract

# 2. 创建虚拟环境（推荐）
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux

# 3. 安装依赖
pip install -r requirements.txt

# 4. 启动服务
python server.py
```

或使用 `start.bat`（Windows 一键启动脚本，自动处理虚拟环境）：

```
双击 start.bat
```

---

## 📖 使用说明

### 1. 配置识别引擎

首次启动后，点击右上角 **「配置」** 展开配置面板，选择并添加识别引擎：

| 引擎 | 说明 | 所需配置 |
|---|---|---|
| **Local OCR** | 本地 RapidOCR，离线运行 | 无需配置 |
| **Gemini (Native)** | Google Gemini Vision API，识别效果最佳 | Google API Key |
| **OpenAI Compatible** | 兼容 OpenAI 格式的任意接口（DeepSeek、通义千问、Kimi 等） | API Key + Base URL |
| **MinerU (API)** | 专为文档解析优化的 MinerU 引擎 | API Key |

> **推荐**：使用 Gemini 或 OpenAI 兼容接口可获得最佳的表格识别和排版还原效果。

### 2. 提取网页图片

1. 在主界面的 URL 输入框中粘贴网页链接
2. 点击「开始提取」
3. 系统自动抓取网页图片、去除干扰图（广告、二维码等），逐张识别
4. 识别完成后点击「合并生成」一键输出所有格式

### 3. 提取本地文件

1. 将图片、PDF、Word、Excel 等文件**拖拽**到上传区域，或直接**粘贴剪贴板图片**（Ctrl+V）
2. 支持批量上传，文件会显示为缩略图，点击可放大预览
3. 点击图片右上角 ✕ 可单独移除，点击「开始提取」开始处理

### 4. 同时处理链接和文件

当检测到同时存在网页链接和本地文件时，系统会弹出选择框：
- **合并解析**：将网页图片与本地文件合并为一份报告
- **仅处理本地文件**：忽略链接只处理文件
- **仅处理网页链接**：忽略本地文件

### 5. 在线编辑与修正

- 识别完成后，点击任意切片可查看识别结果
- 点击**「源码编辑」**直接修改原始 Markdown 内容
- 点击**「重新提取」**对单张切片重新识别
- 点击**「删除废弃切片」**将该切片从最终合并结果中排除
- 切换到**「合成结果预览」**Tab 可在线预览最终合并的 Markdown 文档

### 6. 导出格式说明

点击「合并生成」后即可下载以下格式：

| 格式 | 说明 |
|---|---|
| 📦 ZIP | 包含所有格式的完整打包 |
| 📝 Markdown | 适合进一步编辑处理 |
| 📄 Word (docx) | 可直接在 Office 中打开 |
| 🌐 HTML | 带样式的网页格式 |
| 🔬 LaTeX | 学术排版格式 |
| 📃 TXT | 纯文本 |
| 📊 CSV | 表格数据（多个表格自动合并） |
| 📈 Excel | 带合并单元格的专业表格导出 |

---

## 🏗️ 项目结构

```
OmniExtract/
├── server.py              # FastAPI 后端主程序（API + 路由）
├── scraper.py             # 网页图片智能抓取与过滤模块
├── slicer.py              # 基于水平投影法的智能图像切片模块
├── analyzer.py            # 多引擎 OCR/VLM 分析与降级模块
├── index.html             # 前端单页应用（纯 HTML + JS，无构建步骤）
├── requirements.txt       # Python 依赖清单
├── Dockerfile             # Docker 容器构建文件
├── start.bat              # Windows 一键启动脚本
├── static/
│   ├── logo.jpg           # 应用图标
│   ├── css/all.min.css    # FontAwesome 图标库（本地离线）
│   ├── js/marked.min.js   # Markdown 渲染库（本地离线）
│   └── webfonts/          # 字体文件
└── output/                # 任务输出目录（运行时自动创建）
```

---

## ⚙️ 高级配置

配置数据保存在本地 `config.json`（已加入 `.gitignore`，不会上传至 GitHub）。

**支持的 OpenAI 兼容服务商（示例）：**
- [DeepSeek](https://platform.deepseek.com/)：`https://api.deepseek.com/v1`
- [通义千问](https://help.aliyun.com/zh/model-studio/)：`https://dashscope.aliyuncs.com/compatible-mode/v1`
- [Kimi (月之暗面)](https://platform.moonshot.cn/)：`https://api.moonshot.cn/v1`
- [零一万物](https://platform.lingyiwanwu.com/)：`https://api.lingyiwanwu.com/v1`

---

## 🔒 注意事项

- `config.json` 和 `history.json` 含有 API Key 等敏感信息，已加入 `.gitignore`，**请勿手动提交**
- 使用本地 OCR（RapidOCR）时，首次运行会自动下载约 40MB 的 ONNX 模型文件
- 本地 OCR 精度一般，推荐配置 Gemini 或 OpenAI 接口以获得最佳表格还原效果

---

## 📜 License

本项目基于 [MIT License](LICENSE) 开源。

```
MIT License

Copyright (c) 2025 Simple53

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
