"""
PID控制器API测试示例
展示如何使用API接口进行PID控制
"""
import requests
import time
import json

BASE_URL = "http://localhost:8000"


def print_response(title, response):
    """打印响应结果"""
    print(f"\n{'='*60}")
    print(f"{title}")
    print(f"{'='*60}")
    result = response.json()
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return result


def test_basic_pid_control():
    """测试基本的PID控制流程"""
    controller_id = "test_temperature_control"
    
    # 1. 创建PID控制器
    print("\n【测试1】创建PID控制器")
    response = requests.post(f"{BASE_URL}/pid/create", json={
        "controller_id": controller_id,
        "Kp": 2.0,
        "Ki": 0.5,
        "Kd": 0.1,
        "setpoint": 100.0,
        "output_limits": [0, 100],
        "sample_time": None  # 每次调用都计算
    })
    result = print_response("创建PID控制器", response)
    
    if result["code"] != 200:
        print("创建失败，退出测试")
        return
    
    # 2. 模拟控制过程
    print("\n【测试2】模拟温度控制过程")
    current_value = 20.0  # 初始温度
    target = 100.0        # 目标温度
    
    print(f"\n目标温度: {target}°C")
    print(f"初始温度: {current_value}°C")
    print("\n开始控制循环...")
    
    for i in range(15):
        # 计算PID输出
        response = requests.post(f"{BASE_URL}/pid/compute", json={
            "controller_id": controller_id,
            "input_value": current_value
        })
        
        result = response.json()
        if result["code"] == 200:
            data = result["data"]
            output = data["output"]
            components = data["components"]
            
            print(f"\n步骤 {i+1:2d}: 当前值={current_value:6.2f}, "
                  f"输出={output:6.2f}, "
                  f"P={components['proportional']:6.2f}, "
                  f"I={components['integral']:6.2f}, "
                  f"D={components['derivative']:6.2f}")
            
            # 模拟系统响应（简化的一阶系统）
            current_value += output * 0.15
            
            # 添加一些噪声
            import random
            current_value += random.uniform(-0.5, 0.5)
            
        else:
            print(f"计算失败: {result['message']}")
            break
        
        time.sleep(0.1)  # 模拟采样间隔
    
    # 3. 获取控制器信息
    print("\n【测试3】获取控制器信息")
    response = requests.get(f"{BASE_URL}/pid/info/{controller_id}")
    print_response("控制器信息", response)
    
    # 4. 修改PID参数
    print("\n【测试4】修改PID参数")
    response = requests.post(f"{BASE_URL}/pid/tunings", json={
        "controller_id": controller_id,
        "Kp": 3.0,
        "Ki": 1.0,
        "Kd": 0.2
    })
    print_response("修改PID参数", response)
    
    # 5. 修改目标值
    print("\n【测试5】修改目标值")
    response = requests.post(f"{BASE_URL}/pid/setpoint", json={
        "controller_id": controller_id,
        "setpoint": 80.0
    })
    print_response("修改目标值", response)
    
    # 6. 重置控制器
    print("\n【测试6】重置控制器")
    response = requests.post(f"{BASE_URL}/pid/reset", json={
        "controller_id": controller_id
    })
    print_response("重置控制器", response)
    
    # 7. 设置自动模式
    print("\n【测试7】禁用自动模式")
    response = requests.post(f"{BASE_URL}/pid/auto_mode", json={
        "controller_id": controller_id,
        "enabled": False
    })
    print_response("禁用自动模式", response)
    
    # 8. 列出所有控制器
    print("\n【测试8】列出所有控制器")
    response = requests.get(f"{BASE_URL}/pid/list")
    print_response("控制器列表", response)
    
    # 9. 删除控制器
    print("\n【测试9】删除控制器")
    response = requests.delete(f"{BASE_URL}/pid/delete/{controller_id}")
    print_response("删除控制器", response)


def test_error_handling():
    """测试错误处理"""
    print("\n" + "="*60)
    print("【错误处理测试】")
    print("="*60)
    
    # 测试1: 访问不存在的控制器
    print("\n1. 访问不存在的控制器")
    response = requests.post(f"{BASE_URL}/pid/compute", json={
        "controller_id": "not_exist",
        "input_value": 50
    })
    print_response("不存在的控制器", response)
    
    # 测试2: 创建重复ID的控制器
    print("\n2. 创建重复ID的控制器")
    controller_id = "duplicate_test"
    
    # 先创建一个
    requests.post(f"{BASE_URL}/pid/create", json={
        "controller_id": controller_id,
        "Kp": 1.0
    })
    
    # 再次创建相同ID
    response = requests.post(f"{BASE_URL}/pid/create", json={
        "controller_id": controller_id,
        "Kp": 1.0
    })
    print_response("重复ID", response)
    
    # 清理
    requests.delete(f"{BASE_URL}/pid/delete/{controller_id}")


def test_multiple_controllers():
    """测试多个控制器"""
    print("\n" + "="*60)
    print("【多控制器测试】")
    print("="*60)
    
    # 创建多个控制器
    controllers = [
        {"id": "temp_control_1", "setpoint": 75},
        {"id": "speed_control_1", "setpoint": 1500},
        {"id": "pressure_control_1", "setpoint": 2.5}
    ]
    
    for ctrl in controllers:
        response = requests.post(f"{BASE_URL}/pid/create", json={
            "controller_id": ctrl["id"],
            "Kp": 1.0,
            "Ki": 0.1,
            "Kd": 0.05,
            "setpoint": ctrl["setpoint"]
        })
        print(f"创建控制器: {ctrl['id']}, 状态码: {response.json()['code']}")
    
    # 列出所有控制器
    response = requests.get(f"{BASE_URL}/pid/list")
    result = print_response("所有控制器", response)
    
    # 清理所有测试控制器
    for ctrl in controllers:
        requests.delete(f"{BASE_URL}/pid/delete/{ctrl['id']}")
    
    print("\n已清理所有测试控制器")


if __name__ == "__main__":
    try:
        print("="*60)
        print("PID控制器API测试")
        print("="*60)
        print(f"服务地址: {BASE_URL}")
        
        # 测试服务是否可用
        try:
            response = requests.get(f"{BASE_URL}/")
            if response.status_code == 200:
                print("✓ API服务正常运行")
            else:
                print("✗ API服务响应异常")
                exit(1)
        except requests.exceptions.ConnectionError:
            print("✗ 无法连接到API服务")
            print("  请确保服务已启动: python main.py")
            exit(1)
        
        # 运行测试
        test_basic_pid_control()
        test_error_handling()
        test_multiple_controllers()
        
        print("\n" + "="*60)
        print("✓ 所有测试完成")
        print("="*60)
        
    except Exception as e:
        print(f"\n✗ 测试过程中出现错误: {str(e)}")
        import traceback
        traceback.print_exc()

