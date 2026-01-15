FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TZ=Asia/Shanghai \
    PYTHONPATH=/app

# 安装系统依赖
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    tzdata \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 复制项目文件
COPY simple_pid/ /app/simple_pid/
COPY api/ /app/api/

# 安装Python依赖
WORKDIR /app/api
RUN pip install --no-cache-dir -r requirements.txt

# 创建日志目录
RUN mkdir -p /app/api/logs

# 暴露端口
EXPOSE 8000

# 启动命令
WORKDIR /app/api
CMD ["python", "app.py"]

