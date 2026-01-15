@echo off

REM 创建日志目录
if not exist logs mkdir logs

REM 构建并启动服务
echo 正在构建并启动 PID API 服务...
docker-compose up -d --build

REM 等待服务启动
echo 等待服务启动...
timeout /t 5 /nobreak >nul

REM 检查服务状态
echo 检查服务状态...
docker-compose ps

REM 显示日志
echo 显示服务日志（按 Ctrl+C 退出）...
docker-compose logs -f

