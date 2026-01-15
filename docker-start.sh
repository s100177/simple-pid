#!/bin/bash

# 创建日志目录
mkdir -p logs

# 构建并启动服务
echo "正在构建并启动 PID API 服务..."
docker-compose up -d --build

# 等待服务启动
echo "等待服务启动..."
sleep 5

# 检查服务状态
echo "检查服务状态..."
docker-compose ps

# 显示日志
echo "显示服务日志（按 Ctrl+C 退出）..."
docker-compose logs -f

