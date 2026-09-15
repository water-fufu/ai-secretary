# CloudBase 云托管 Dockerfile
# 用 Debian slim（glibc），因为 onnxruntime（fastembed 依赖）不支持 Alpine musllinux
# pip 用腾讯云内部镜像源

FROM python:3.12-slim

# 安装系统依赖
# - libgomp1: faiss-cpu 需要 OpenMP 运行时
# - gcc/g++: 兜底编译工具（大多数包有预编译 wheel，但以防万一）
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

# 先拷贝依赖文件，利用 Docker 层缓存
COPY requirements.txt .

# 用腾讯云 pip 镜像安装依赖
# Debian 官方 Python 镜像没有 PEP 668 限制，不需要 --break-system-packages
RUN pip config set global.index-url http://mirrors.cloud.tencent.com/pypi/simple \
    && pip config set global.trusted-host mirrors.cloud.tencent.com \
    && pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# 拷贝应用代码
COPY . .

# 创建 FAISS 索引持久化目录
RUN mkdir -p /app/data/faiss

# 暴露端口（必须与 CloudBase 服务配置一致：8080）
EXPOSE 8080

# 启动命令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "2"]
