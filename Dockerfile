FROM python:3.10-slim

WORKDIR /app

# 安装系统依赖（OpenCV、Pillow 等所需）
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目文件
COPY . .

# 创建输出目录
RUN mkdir -p output

# 暴露 FastAPI 端口
EXPOSE 8000

# 启动 FastAPI 服务
CMD ["python", "server.py"]
