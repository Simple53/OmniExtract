# Web OCR Engine (OmniExtract 万象)

基于 FastAPI 的网页长图、表格与文本多模态提取工具。支持多种 OCR/VLM 引擎，支持一键 Docker 部署。

## 功能特性

- 输入网页链接，自动抓取网页内的图片
- 智能无缝切片（基于水平投影法，避免切断文字行）
- 多引擎支持：Gemini Vision API、OpenAI 兼容接口、MinerU API、本地 RapidOCR
- 自动降级：API 失败时自动回退到本地 OCR
- 多格式导出：Markdown、TXT、HTML、Word (docx)、LaTeX、CSV、Excel、ZIP
- SSE 实时进度推送
- 断点续传：支持任务中断后从断点恢复
- 在线编辑：可手动修正切片识别结果并重新合并
- 暗色/浅色主题切换

## 部署与运行

### 方式一：Docker (推荐)

```bash
docker build -t web-ocr .
docker run -p 8000:8000 web-ocr
```

启动后打开 `http://localhost:8000`

### 方式二：本地 Python 运行

```bash
pip install -r requirements.txt
python server.py
```

或使用 uvicorn：

```bash
uvicorn server:app --host 0.0.0.0 --port 8000 --reload
```

## 配置说明

首次启动后，在左侧配置面板中添加 API 引擎：

- **Local OCR**：无需配置，使用 RapidOCR 本地识别（免费，精度一般）
- **Gemini (Native)**：需要 Google API Key
- **OpenAI Compatible**：支持任何 OpenAI 兼容接口（如 DeepSeek、通义千问等）
- **MinerU (API)**：支持 MinerU 云端或本地部署

## 项目结构

```
.
├── server.py          # FastAPI 后端主程序
├── scraper.py         # 网页图片抓取模块
├── slicer.py          # 智能图像切片模块
├── analyzer.py        # OCR/VLM 分析模块
├── index.html         # 前端单页应用
├── requirements.txt   # Python 依赖
├── Dockerfile         # Docker 构建文件
└── output/            # 输出文件目录（运行时生成）
```

## 注意事项

- 使用本地 OCR 时，可能无法精准还原复杂表格结构，推荐配置 Gemini API Key 以获取最佳体验
- 首次使用本地 OCR 时会自动下载 ONNX 模型文件
- `config.json` 和 `history.json` 包含敏感信息，已加入 `.gitignore`
