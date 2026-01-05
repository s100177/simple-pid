# PID控制器 FastAPI 接口文档

这是一个基于FastAPI封装的PID控制器API服务，提供完整的PID控制器管理和计算功能。

## 安装依赖

```bash
pip install -r requirements.txt
```

## 启动服务

```bash
python main.py
```

或者使用uvicorn：

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

服务将在 `http://localhost:8000` 启动

## API文档

启动服务后，可以访问以下地址查看交互式API文档：
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## 响应格式

所有接口统一返回以下格式：

```json
{
  "data": {},        // 返回的数据，可以是任意类型
  "code": 200,       // 状态码，200表示成功，其他表示错误
  "message": "success"  // 响应消息
}
```

### 错误码说明
- `200`: 成功
- `400`: 请求参数错误
- `404`: 资源不存在（控制器ID不存在）
- `500`: 服务器内部错误

## API接口列表

### 1. 创建PID控制器
**POST** `/pid/create`

创建一个新的PID控制器实例。

**请求体：**
```json
{
  "controller_id": "pid_001",
  "Kp": 1.0,
  "Ki": 0.0,
  "Kd": 0.0,
  "setpoint": 100,
  "sample_time": 0.01,
  "output_limits": [0, 100],
  "output_rate_limits": [null, null],
  "auto_mode": true,
  "proportional_on_measurement": false,
  "differential_on_measurement": true,
  "starting_output": 0.0
}
```

**响应示例：**
```json
{
  "data": {
    "controller_id": "pid_001",
    "Kp": 1.0,
    "Ki": 0.0,
    "Kd": 0.0,
    "setpoint": 100
  },
  "code": 200,
  "message": "PID控制器创建成功"
}
```

### 2. 计算PID输出
**POST** `/pid/compute`

根据输入值计算PID控制器的输出。

**请求体：**
```json
{
  "controller_id": "pid_001",
  "input_value": 80.5,
  "dt": null
}
```

**响应示例：**
```json
{
  "data": {
    "output": 19.5,
    "input": 80.5,
    "setpoint": 100,
    "components": {
      "proportional": 19.5,
      "integral": 0.0,
      "derivative": 0.0
    }
  },
  "code": 200,
  "message": "计算成功"
}
```

### 3. 设置目标值
**POST** `/pid/setpoint`

更新PID控制器的目标设定值。

**请求体：**
```json
{
  "controller_id": "pid_001",
  "setpoint": 120
}
```

### 4. 设置PID参数
**POST** `/pid/tunings`

更新PID控制器的Kp、Ki、Kd参数。

**请求体：**
```json
{
  "controller_id": "pid_001",
  "Kp": 2.0,
  "Ki": 0.5,
  "Kd": 0.1
}
```

### 5. 重置PID控制器
**POST** `/pid/reset`

重置PID控制器的内部状态。

**请求体：**
```json
{
  "controller_id": "pid_001"
}
```

### 6. 设置自动模式
**POST** `/pid/auto_mode`

启用或禁用PID控制器的自动模式。

**请求体：**
```json
{
  "controller_id": "pid_001",
  "enabled": true,
  "last_output": null
}
```

### 7. 获取控制器信息
**GET** `/pid/info/{controller_id}`

获取指定PID控制器的详细信息。

**响应示例：**
```json
{
  "data": {
    "controller_id": "pid_001",
    "tunings": {
      "Kp": 1.0,
      "Ki": 0.0,
      "Kd": 0.0
    },
    "setpoint": 100,
    "auto_mode": true,
    "output_limits": [0, 100],
    "output_rate_limits": [null, null],
    "components": {
      "proportional": 19.5,
      "integral": 0.0,
      "derivative": 0.0
    }
  },
  "code": 200,
  "message": "获取信息成功"
}
```

### 8. 列出所有控制器
**GET** `/pid/list`

获取所有已创建的PID控制器列表。

**响应示例：**
```json
{
  "data": {
    "controllers": [
      {
        "controller_id": "pid_001",
        "Kp": 1.0,
        "Ki": 0.0,
        "Kd": 0.0,
        "setpoint": 100,
        "auto_mode": true
      }
    ],
    "total": 1
  },
  "code": 200,
  "message": "获取列表成功"
}
```

### 9. 删除控制器
**DELETE** `/pid/delete/{controller_id}`

删除指定的PID控制器。

**响应示例：**
```json
{
  "data": {
    "controller_id": "pid_001"
  },
  "code": 200,
  "message": "PID控制器删除成功"
}
```

## 使用示例

### Python示例

```python
import requests

BASE_URL = "http://localhost:8000"

# 1. 创建PID控制器
response = requests.post(f"{BASE_URL}/pid/create", json={
    "controller_id": "temp_control",
    "Kp": 2.0,
    "Ki": 0.5,
    "Kd": 0.1,
    "setpoint": 75,
    "output_limits": [0, 100]
})
print(response.json())

# 2. 循环计算输出
current_temp = 20
for i in range(10):
    response = requests.post(f"{BASE_URL}/pid/compute", json={
        "controller_id": "temp_control",
        "input_value": current_temp
    })
    result = response.json()
    if result["code"] == 200:
        output = result["data"]["output"]
        print(f"当前温度: {current_temp}, PID输出: {output}")
        # 模拟系统响应
        current_temp += output * 0.1
```

### cURL示例

```bash
# 创建控制器
curl -X POST "http://localhost:8000/pid/create" \
  -H "Content-Type: application/json" \
  -d '{
    "controller_id": "test_pid",
    "Kp": 1.0,
    "Ki": 0.0,
    "Kd": 0.0,
    "setpoint": 100
  }'

# 计算输出
curl -X POST "http://localhost:8000/pid/compute" \
  -H "Content-Type: application/json" \
  -d '{
    "controller_id": "test_pid",
    "input_value": 85.0
  }'

# 获取控制器信息
curl -X GET "http://localhost:8000/pid/info/test_pid"
```

## 注意事项

1. 每个控制器需要唯一的`controller_id`
2. 控制器实例存储在内存中，服务重启后会丢失
3. 建议在生产环境中使用持久化存储（如Redis或数据库）
4. 输出限制和输出变化率限制可以设置为`null`表示无限制

## 常见错误处理

### 控制器ID已存在
```json
{
  "data": null,
  "code": 400,
  "message": "控制器ID 'pid_001' 已存在"
}
```

### 控制器不存在
```json
{
  "data": null,
  "code": 404,
  "message": "控制器ID 'pid_999' 不存在"
}
```

### 参数错误
```json
{
  "data": null,
  "code": 400,
  "message": "参数错误: dt has negative value -0.1, must be positive"
}
```

