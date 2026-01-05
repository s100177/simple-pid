"""
快速测试PID控制器API
最简单的使用示例
"""
import requests
import json

BASE_URL = "http://localhost:8000"

# 1. 创建PID控制器
print("1. 创建PID控制器...")
response = requests.post(f"{BASE_URL}/pid/create", json={
    "controller_id": "quick_test",
    "Kp": 1.0,
    "Ki": 0.1,
    "Kd": 0.05,
    "setpoint": 100.0,
    "output_limits": [0, 100]
})
print(json.dumps(response.json(), indent=2, ensure_ascii=False))

# 2. 计算PID输出
print("\n2. 计算PID输出...")
response = requests.post(f"{BASE_URL}/pid/compute", json={
    "controller_id": "quick_test",
    "input_value": 50.0
})
print(json.dumps(response.json(), indent=2, ensure_ascii=False))

# 3. 获取控制器信息
print("\n3. 获取控制器信息...")
response = requests.get(f"{BASE_URL}/pid/info/quick_test")
print(json.dumps(response.json(), indent=2, ensure_ascii=False))

# 4. 删除控制器
print("\n4. 删除控制器...")
response = requests.delete(f"{BASE_URL}/pid/delete/quick_test")
print(json.dumps(response.json(), indent=2, ensure_ascii=False))

print("\n✓ 测试完成！")

