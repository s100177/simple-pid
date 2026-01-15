#!/usr/bin/env python
"""
PID控制器API调用示例 - 水温控制模拟

此示例演示如何通过HTTP API调用远程PID控制器服务来控制水温。
模拟场景：一个热水器系统，通过PID控制器调节加热功率，使水温达到目标温度。

API服务地址：http://58.87.80.234:40002/docs
"""

import time
import requests
import matplotlib.pyplot as plt

plt.rcParams['font.sans-serif'] = ['SimHei']   # 黑体
plt.rcParams['axes.unicode_minus'] = False     # 解决负号显示为方块

# ============= 配置 =============
API_BASE_URL = "http://58.87.80.234:40002"  # API服务地址
CONTROLLER_ID = "water_heater_001"  # 控制器唯一标识


class WaterBoiler:
    """
    水加热器模拟器
    
    模拟一个简单的水加热系统：
    - 加热功率越大，水温上升越快
    - 自然状态下会有热量散失
    """

    def __init__(self, initial_temp=20.0):
        """
        初始化水加热器
        
        参数:
            initial_temp: 初始水温（摄氏度），默认20°C（室温）
        """
        self.water_temp = initial_temp

    def update(self, boiler_power, dt):
        """
        更新水温状态
        
        参数:
            boiler_power: 加热功率（0-100），0表示关闭，100表示最大功率
            dt: 时间步长（秒）
            
        返回:
            当前水温（摄氏度）
        """
        if boiler_power > 0:
            # 加热效果：功率越大，温度上升越快
            # 假设最大功率时每秒升温1°C
            self.water_temp += 1.0 * (boiler_power / 100.0) * dt

        # 热量散失：自然冷却，每秒降温0.02°C
        self.water_temp -= 0.02 * dt
        
        return self.water_temp


class PIDAPIClient:
    """
    PID控制器API客户端
    
    封装所有与PID控制器API的交互
    """

    def __init__(self, base_url):
        """
        初始化API客户端
        
        参数:
            base_url: API服务的基础URL
        """
        self.base_url = base_url

    def create_controller(self, controller_id, Kp, Ki, Kd, setpoint, 
                          output_limits=(None, None)):
        """
        创建PID控制器
        
        参数说明：
        - controller_id: 控制器唯一标识ID，用于后续操作引用
        - Kp (比例增益): 
            * 决定对当前误差的响应强度
            * 值越大，响应越快，但可能产生振荡
            * 典型值：1-10
        - Ki (积分增益):
            * 消除稳态误差（长期偏差）
            * 值越大，消除误差越快，但可能导致超调
            * 典型值：0.001-0.1
        - Kd (微分增益):
            * 预测误差变化趋势，减少超调
            * 值越大，阻尼效果越强
            * 典型值：0.01-1
        - setpoint: 目标设定值（我们希望达到的温度）
        - output_limits: 输出限制 (最小值, 最大值)
        
        返回:
            API响应结果
        """
        url = f"{self.base_url}/pid/create"
        data = {
            "controller_id": controller_id,
            "Kp": Kp,
            "Ki": Ki,
            "Kd": Kd,
            "setpoint": setpoint,
            "output_limits": list(output_limits) if output_limits else [None, None],
            "auto_mode": True,
            "proportional_on_measurement": False,
            "differential_on_measurement": True,
            "starting_output": 0.0
        }
        response = requests.post(url, json=data)
        return response.json()

    def compute_output(self, controller_id, input_value, dt=None):
        """
        计算PID控制器输出
        
        参数说明：
        - controller_id: 控制器ID
        - input_value (输入/测量值):
            * 当前的实际测量值（如当前水温）
            * PID将根据这个值与setpoint的差值计算控制输出
        - dt (时间步长):
            * 两次计算之间的时间间隔（秒）
            * 影响积分和微分的计算
            * 如果不提供，将使用上次调用后的实际时间间隔
        
        返回:
            API响应，包含：
            - output: 控制器输出值（加热功率）
            - components: P、I、D各分量的值
        """
        url = f"{self.base_url}/pid/compute"
        data = {
            "controller_id": controller_id,
            "input_value": input_value,
            "dt": dt
        }
        response = requests.post(url, json=data)
        return response.json()

    def set_setpoint(self, controller_id, setpoint):
        """
        设置目标值
        
        参数:
            controller_id: 控制器ID
            setpoint: 新的目标设定值
        
        返回:
            API响应结果
        """
        url = f"{self.base_url}/pid/setpoint"
        data = {
            "controller_id": controller_id,
            "setpoint": setpoint
        }
        response = requests.post(url, json=data)
        return response.json()

    def delete_controller(self, controller_id):
        """
        删除控制器
        
        参数:
            controller_id: 控制器ID
        
        返回:
            API响应结果
        """
        url = f"{self.base_url}/pid/delete/{controller_id}"
        response = requests.delete(url)
        return response.json()

    def get_info(self, controller_id):
        """
        获取控制器信息
        
        参数:
            controller_id: 控制器ID
        
        返回:
            控制器当前状态信息
        """
        url = f"{self.base_url}/pid/info/{controller_id}"
        response = requests.get(url)
        return response.json()


def run_simulation():
    """
    运行PID控制模拟（离散时间模拟，快速展示控制效果）
    
    控制流程：
    1. 创建PID控制器（设定初始目标温度）
    2. 循环：
       a. 读取当前水温（input_value）
       b. 调用API计算控制输出（output）
       c. 将输出作为加热功率应用到热水器
       d. 模拟器更新水温
    3. 中途改变目标温度，观察PID响应
    """
    
    # 初始化
    boiler = WaterBoiler(initial_temp=20.0)  # 初始水温20°C
    api_client = PIDAPIClient(API_BASE_URL)
    
    # ============= PID参数说明 =============
    # Kp = 5.0:  比例增益，误差每1°C产生5单位的功率调整
    # Ki = 0.01: 积分增益，累积误差消除稳态偏差
    # Kd = 0.1:  微分增益，抑制温度变化过快
    # setpoint = 20.0: 初始目标温度（与当前水温相同，避免启动冲击）
    # output_limits = (0, 100): 功率限制在0-100之间
    
    print("=" * 60)
    print("PID控制器API调用示例 - 水温控制")
    print("=" * 60)
    print(f"API服务地址: {API_BASE_URL}")
    print(f"控制器ID: {CONTROLLER_ID}")
    print()
    
    # 步骤1: 创建PID控制器
    print("【步骤1】创建PID控制器")
    print("-" * 40)
    
    # 先尝试删除可能存在的旧控制器
    api_client.delete_controller(CONTROLLER_ID)
    
    result = api_client.create_controller(
        controller_id=CONTROLLER_ID,
        Kp=5.0,      # 比例增益
        Ki=0.01,     # 积分增益
        Kd=0.1,      # 微分增益
        setpoint=20.0,  # 初始目标温度
        output_limits=(0, 100)  # 输出限制
    )
    
    print(f"创建结果: {result['message']}")
    print(f"PID参数: Kp=5.0, Ki=0.01, Kd=0.1")
    print(f"初始目标温度: 20.0°C")
    print(f"输出限制: 0-100")
    print()
    
    if result['code'] != 200:
        print(f"创建失败: {result['message']}")
        return
    
    # 步骤2: 运行控制循环
    print("【步骤2】开始控制循环（离散时间模拟）")
    print("-" * 40)
    
    # 数据记录（用于绘图）
    time_data = []       # 时间轴
    temp_data = []       # 实际温度
    setpoint_data = []   # 目标温度
    power_data = []      # 加热功率
    p_data, i_data, d_data = [], [], []  # PID各分量
    
    # ============= 离散时间模拟参数 =============
    # 使用固定时间步长进行快速模拟，不依赖实际时间
    dt = 0.5  # 每步模拟0.5秒
    simulation_duration = 200  # 模拟200秒（虚拟时间）
    total_steps = int(simulation_duration / dt)
    
    setpoint_changed = False
    current_setpoint = 20.0
    
    print(f"模拟时长: {simulation_duration}秒（虚拟时间）")
    print(f"时间步长: {dt}秒")
    print(f"总步数: {total_steps}")
    print()
    print("控制过程:")
    print()
    
    for step in range(total_steps):
        elapsed = step * dt  # 当前虚拟时间
        
        # 在10秒后改变目标温度为100°C
        if elapsed >= 10 and not setpoint_changed:
            print(f"\n  >>> 时间 {elapsed:.1f}s: 目标温度从 20°C 改为 100°C <<<\n")
            api_client.set_setpoint(CONTROLLER_ID, 100.0)
            setpoint_changed = True
            current_setpoint = 100.0
        
        # 调用API计算控制输出
        result = api_client.compute_output(
            controller_id=CONTROLLER_ID,
            input_value=boiler.water_temp,  # 输入：当前水温
            dt=dt  # 时间步长
        )
        
        if result['code'] != 200:
            print(f"计算失败: {result['message']}")
            continue
        
        # 解析输出
        data = result['data']
        power = data['output']          # 输出：加热功率
        components = data['components']  # PID各分量
        
        # 应用控制输出到模拟器
        boiler.update(power, dt)
        
        # 记录数据
        time_data.append(elapsed)
        temp_data.append(boiler.water_temp)
        setpoint_data.append(current_setpoint)
        power_data.append(power)
        p_data.append(components['proportional'])
        i_data.append(components['integral'])
        d_data.append(components['derivative'])
        
        # 每10秒打印一次状态
        if step % 20 == 0:
            error = current_setpoint - boiler.water_temp
            print(f"  时间: {elapsed:6.1f}s | "
                  f"目标: {current_setpoint:5.1f}°C | "
                  f"实际: {boiler.water_temp:5.1f}°C | "
                  f"误差: {error:+6.1f}°C | "
                  f"功率: {power:5.1f}")
    
    print()
    print("【步骤3】模拟结束，清理资源")
    print("-" * 40)
    
    # 获取最终控制器状态
    info = api_client.get_info(CONTROLLER_ID)
    if info['code'] == 200:
        print(f"最终控制器状态:")
        print(f"  - 目标温度: {info['data']['setpoint']}°C")
        print(f"  - PID参数: Kp={info['data']['tunings']['Kp']}, "
              f"Ki={info['data']['tunings']['Ki']}, "
              f"Kd={info['data']['tunings']['Kd']}")
    
    # 删除控制器
    api_client.delete_controller(CONTROLLER_ID)
    print("控制器已删除")
    print()
    
    # 绘制结果
    print("【步骤4】绘制控制效果图")
    print("-" * 40)
    
    fig, axes = plt.subplots(3, 1, figsize=(12, 10))
    
    # 图1: 温度追踪
    axes[0].plot(time_data, temp_data, 'b-', linewidth=2, label='实际温度 (Measured)')
    axes[0].plot(time_data, setpoint_data, 'r--', linewidth=2, label='目标温度 (Setpoint)')
    axes[0].set_xlabel('时间 (秒)')
    axes[0].set_ylabel('温度 (°C)')
    axes[0].set_title('PID温度控制效果')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)
    
    # 图2: 控制输出（功率）
    axes[1].plot(time_data, power_data, 'g-', linewidth=2, label='加热功率 (Output)')
    axes[1].set_xlabel('时间 (秒)')
    axes[1].set_ylabel('功率 (0-100)')
    axes[1].set_title('PID控制输出（加热功率）')
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)
    
    # 图3: PID各分量
    axes[2].plot(time_data, p_data, 'r-', linewidth=1.5, label='P (比例)')
    axes[2].plot(time_data, i_data, 'g-', linewidth=1.5, label='I (积分)')
    axes[2].plot(time_data, d_data, 'b-', linewidth=1.5, label='D (微分)')
    axes[2].set_xlabel('时间 (秒)')
    axes[2].set_ylabel('分量值')
    axes[2].set_title('PID各分量贡献')
    axes[2].legend()
    axes[2].grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('pid_control_result.png', dpi=150)
    print("控制效果图已保存: pid_control_result.png")
    
    try:
        plt.show()
    except:
        print("(无显示环境，图片已保存到文件)")
    
    print()
    print("=" * 60)
    print("模拟完成!")
    print("=" * 60)


def print_api_explanation():
    """
    打印API输入输出含义说明
    """
    print("""
================================================================================
                        PID控制器API 输入输出说明                              
================================================================================

  [创建控制器 /pid/create]
  ----------------------------------------------------------------------------
  输入参数:
    - controller_id : 控制器唯一标识，用于后续操作引用
    - Kp (比例增益) : 控制对当前误差的响应强度
                      误差=目标值-测量值，Kp越大响应越快但可能振荡
    - Ki (积分增益) : 消除长期稳态误差，累积历史误差进行补偿
    - Kd (微分增益) : 预测误差变化趋势，减少超调和振荡
    - setpoint      : 目标设定值（希望达到的值）
    - output_limits : 输出限制范围 [最小值, 最大值]

  [计算输出 /pid/compute] -- 最核心的接口
  ----------------------------------------------------------------------------
  输入参数:
    - controller_id : 控制器ID
    - input_value   : 当前测量值（如当前温度、当前速度等）
    - dt            : 时间步长（秒），两次计算的间隔时间

  输出结果:
    - output        : PID计算出的控制量（如加热功率、电机转速等）
                      output = P + I + D
    - components    : 各分量详情
      * proportional (P): Kp x 误差，即时响应当前误差
      * integral (I)    : Ki x 累积误差，消除稳态偏差
      * derivative (D)  : Kd x 误差变化率，预测和抑制

  [控制流程示意]
  ----------------------------------------------------------------------------

    目标值(setpoint) ---+
                        |   +--------------+
                        +-> | PID控制器    | --> 控制输出(output)
                        |   |  P + I + D   |      (如：加热功率)
    测量值(input) ------+   +--------------+            |
         ^                                              |
         |              +--------------+                |
         +------------- |  被控对象    | <--------------+
                        | (如：热水器) |
                        +--------------+

================================================================================
""")


if __name__ == '__main__':
    print_api_explanation()
    print()
    
    try:
        # 检查API服务是否可用
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print("[OK] API服务连接成功!")
            print()
            run_simulation()
        else:
            print(f"[ERROR] API服务响应异常: {response.status_code}")
    except requests.exceptions.ConnectionError:
        print(f"[ERROR] 无法连接到API服务: {API_BASE_URL}")
        print("  请确保API服务已启动并可访问")
    except requests.exceptions.Timeout:
        print(f"[ERROR] 连接API服务超时: {API_BASE_URL}")

