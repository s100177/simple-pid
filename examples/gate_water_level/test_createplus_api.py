#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试 /pid/createPlus 接口

验证点：
1. createPlus 能正常创建控制器
2. createPlus 对已存在的控制器能自动覆盖
3. 通过 createPlus 创建的控制器控制效果正常
"""

import requests
from urllib.parse import quote

API_BASE_URL = "http://localhost:5000"
CONTROLLER_ID = "test-createPlus-controller"


def test_createplus_api():
    """测试 createPlus 接口"""
    
    print("=" * 60)
    print("测试 /pid/createPlus 接口")
    print("=" * 60)
    
    # ========== 测试1: 首次创建 ==========
    print("\n[测试1] 首次创建控制器")
    print("-" * 40)
    
    data = {
        "controller_id": CONTROLLER_ID,
        "Kp": 1.5,
        "Ki": 0.0003,
        "Kd": 50,
        "setpoint": 61.643,
        "sample_time": 300,
        "output_limits": [0, 4],
        "output_rate_limits": [-0.001, 0.001],
        "starting_output": 1.5,
        "dead_zone": 0.05
    }
    
    resp = requests.post(f"{API_BASE_URL}/pid/createPlus", json=data)
    result = resp.json()
    print(f"请求: POST /pid/createPlus")
    print(f"响应码: {result['code']}")
    print(f"消息: {result['message']}")
    
    if result['code'] == 200:
        print("[PASS] 首次创建成功")
    else:
        print("[FAIL] 首次创建失败")
        return False
    
    # ========== 测试2: 重复创建（应自动覆盖） ==========
    print("\n[测试2] 重复创建（验证自动覆盖）")
    print("-" * 40)
    
    # 修改参数再次创建
    data["Kp"] = 2.0
    data["setpoint"] = 62.0
    
    resp = requests.post(f"{API_BASE_URL}/pid/createPlus", json=data)
    result = resp.json()
    print(f"请求: POST /pid/createPlus (Kp=2.0, setpoint=62.0)")
    print(f"响应码: {result['code']}")
    print(f"消息: {result['message']}")
    
    if result['code'] == 200:
        print("[PASS] 重复创建成功（已覆盖）")
    else:
        print("[FAIL] 重复创建失败")
        return False
    
    # 验证参数已更新
    encoded_id = quote(CONTROLLER_ID, safe='')
    resp = requests.get(f"{API_BASE_URL}/pid/info/{encoded_id}")
    info = resp.json()
    
    if info['code'] == 200:
        tunings = info['data']['tunings']
        setpoint = info['data']['setpoint']
        print(f"验证参数: Kp={tunings['Kp']}, setpoint={setpoint}")
        if tunings['Kp'] == 2.0 and setpoint == 62.0:
            print("[PASS] 参数已正确更新")
        else:
            print("[FAIL] 参数未更新")
            return False
    
    # ========== 测试3: 对比 create 接口 ==========
    print("\n[测试3] 对比 /pid/create 接口（应报错）")
    print("-" * 40)
    
    resp = requests.post(f"{API_BASE_URL}/pid/create", json=data)
    result = resp.json()
    print(f"请求: POST /pid/create (同ID)")
    print(f"响应码: {result['code']}")
    print(f"消息: {result['message']}")
    
    if result['code'] == 400:
        print("[PASS] create 接口正确拒绝重复创建")
    else:
        print("[WARN] create 接口行为异常")
    
    # ========== 测试4: 控制效果验证 ==========
    print("\n[测试4] 控制效果验证")
    print("-" * 40)
    
    # 重新创建一个标准配置的控制器
    data = {
        "controller_id": CONTROLLER_ID,
        "Kp": 1.5,
        "Ki": 0.0003,
        "Kd": 50,
        "setpoint": 61.643,
        "sample_time": 1.0,  # 快速响应用于测试
        "output_limits": [0, 4],
        "output_rate_limits": [-0.5, 0.5],
        "starting_output": 1.5,
        "dead_zone": 0.01
    }
    
    resp = requests.post(f"{API_BASE_URL}/pid/createPlus", json=data)
    print(f"重建控制器: setpoint=61.643, starting_output=1.5")
    
    # 模拟几个控制周期
    test_inputs = [61.0, 61.2, 61.4, 61.6, 61.643, 61.8, 62.0]
    print(f"\n测试输入序列: {test_inputs}")
    print(f"{'输入值':>10} | {'输出值':>10} | {'P分量':>10} | {'I分量':>10} | {'D分量':>10}")
    print("-" * 60)
    
    for input_val in test_inputs:
        compute_data = {
            "controller_id": CONTROLLER_ID,
            "input_value": input_val,
            "dt": 1.0
        }
        resp = requests.post(f"{API_BASE_URL}/pid/compute", json=compute_data)
        result = resp.json()
        
        if result['code'] == 200:
            out = result['data']['output']
            p = result['data']['components']['proportional']
            i = result['data']['components']['integral']
            d = result['data']['components']['derivative']
            print(f"{input_val:10.3f} | {out:10.3f} | {p:10.3f} | {i:10.3f} | {d:10.3f}")
        else:
            print(f"计算失败: {result['message']}")
    
    # 验证控制方向
    print("\n控制方向验证:")
    print("- 输入 < 目标 -> 输出应增大 (开度增大)")
    print("- 输入 > 目标 -> 输出应减小 (开度减小)")
    
    # ========== 清理 ==========
    print("\n[清理] 删除测试控制器")
    print("-" * 40)
    resp = requests.delete(f"{API_BASE_URL}/pid/delete/{encoded_id}")
    result = resp.json()
    print(f"删除结果: {result['message']}")
    
    print("\n" + "=" * 60)
    print("测试完成!")
    print("=" * 60)
    return True


if __name__ == '__main__':
    try:
        resp = requests.get(f"{API_BASE_URL}/health", timeout=5)
        if resp.status_code == 200:
            print("[OK] API服务已连接\n")
            test_createplus_api()
        else:
            print(f"[ERROR] API服务错误: {resp.status_code}")
    except requests.exceptions.ConnectionError:
        print(f"[ERROR] 无法连接API: {API_BASE_URL}")
        print("请先启动API服务: cd api && python app.py")

