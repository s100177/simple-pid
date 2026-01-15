# Docker 部署指南

## 📦 快速开始

### 1. 构建并启动服务

```bash
# 构建镜像并启动容器
docker-compose up -d

# 查看日志
docker-compose logs -f

# 查看服务状态
docker-compose ps
```

### 2. 访问服务

- API服务: http://localhost:8000
- API文档: http://localhost:8000/docs
- 健康检查: http://localhost:8000/health

### 3. 停止服务

```bash
docker-compose down
```

## 🔧 配置说明

### 端口配置

默认端口映射：`8000:8000`

如需修改端口，编辑 `docker-compose.yml`：

```yaml
ports:
  - "自定义端口:8000"
```

### 资源限制

当前配置：
- CPU限制: 2.0 核
- 内存限制: 4GB
- CPU保留: 0.5 核
- 内存保留: 1GB

可根据实际需求调整 `docker-compose.yml` 中的 `deploy.resources` 部分。

### 日志配置

- **容器日志**: 使用 Docker 的 json-file 驱动，最大 50MB，保留 5 个文件
- **应用日志**: 挂载到 `./logs/app.log`

查看日志：
```bash
# 查看容器日志
docker-compose logs -f app

# 查看应用日志文件
tail -f logs/app.log
```

## 🛠️ 常用命令

### 构建镜像

```bash
# 构建镜像
docker-compose build

# 重新构建（不使用缓存）
docker-compose build --no-cache
```

### 服务管理

```bash
# 启动服务
docker-compose up -d

# 停止服务
docker-compose stop

# 重启服务
docker-compose restart

# 停止并删除容器
docker-compose down

# 停止并删除容器、网络、卷
docker-compose down -v
```

### 查看信息

```bash
# 查看运行状态
docker-compose ps

# 查看日志
docker-compose logs -f app

# 进入容器
docker-compose exec app /bin/bash

# 查看资源使用
docker stats simple-pid-api
```

### 健康检查

```bash
# 检查健康状态
curl http://localhost:8000/health

# 查看健康检查历史
docker inspect simple-pid-api | grep -A 10 Health
```

## 📁 目录结构

```
.
├── Dockerfile              # Docker镜像构建文件
├── docker-compose.yml      # Docker Compose配置
├── .dockerignore          # Docker忽略文件
├── simple_pid/            # PID控制器核心代码
├── api/                   # API服务代码
│   ├── app.py            # FastAPI应用
│   └── requirements.txt  # Python依赖
└── logs/                  # 日志目录（自动创建）
```

## 🔍 故障排查

### 1. 端口被占用

```bash
# 检查端口占用
netstat -tuln | grep 8000
# 或
lsof -i :8000

# 修改 docker-compose.yml 中的端口映射
```

### 2. 容器无法启动

```bash
# 查看详细日志
docker-compose logs app

# 检查镜像构建
docker-compose build --no-cache

# 检查容器状态
docker-compose ps -a
```

### 3. 导入错误

确保 `simple_pid` 目录已正确复制到容器中：

```bash
# 进入容器检查
docker-compose exec app ls -la /app/simple_pid
```

### 4. 健康检查失败

```bash
# 手动测试健康检查
docker-compose exec app python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/health').read())"
```

## 🚀 生产环境建议

1. **使用环境变量文件**: 创建 `.env` 文件管理配置
2. **持久化数据**: 考虑使用 Redis 或数据库存储 PID 控制器状态
3. **反向代理**: 使用 Nginx 作为反向代理
4. **监控**: 集成 Prometheus 等监控工具
5. **备份**: 定期备份日志和配置

## 📝 环境变量

可在 `docker-compose.yml` 中设置以下环境变量：

- `ENV`: 运行环境（production/development）
- `PYTHONUNBUFFERED`: Python输出不缓冲
- `PYTHONDONTWRITEBYTECODE`: 不生成 .pyc 文件
- `TZ`: 时区设置
- `PYTHONPATH`: Python模块搜索路径

## 🔐 安全建议

1. 使用非 root 用户运行（可在 Dockerfile 中添加）
2. 限制容器权限（已配置 `no-new-privileges`）
3. 使用 tmpfs 限制临时文件系统（已配置）
4. 定期更新基础镜像
5. 扫描镜像漏洞：`docker scan simple-pid-api:latest`

