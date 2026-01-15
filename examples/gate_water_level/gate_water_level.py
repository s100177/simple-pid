#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
PID控制器API调用示例 - 闸门控制闸前水位

此示例演示如何通过HTTP API调用PID控制器服务来实现闸门自动控制闸前水位。

应用场景：
    水库/河道闸门自动控制系统，根据闸前水位自动调节闸门开度，
    使闸前水位维持在目标值附近。

控制原理：
    - 被控对象：闸门开度 (0-100%)
    - 控制目标：闸前水位 (米)
    - 测量值：当前闸前水位
    
    当水位高于目标 → 增大闸门开度 → 加快泄水 → 水位下降
    当水位低于目标 → 减小闸门开度 → 减缓泄水 → 水位上升

API服务地址：http://58.87.80.234:40002/docs
"""

import time
import requests
import matplotlib.pyplot as plt

plt.rcParams['font.sans-serif'] = ['SimHei']   # 黑体
plt.rcParams['axes.unicode_minus'] = False     # 解决负号显示为方块

# ============= 配置 =============
API_BASE_URL = "http://58.87.80.234:40002"  # API服务地址
CONTROLLER_ID = "gate_controller_001"  # 控制器唯一标识


class WaterGateSystem:
    """
    闸门-水位系统模拟器
    
    模拟一个简单的水库/河道闸门系统：
    - 上游来水（可以是恒定流量或变化流量）
    - 闸门控制出水流量
    - 水位根据进出水量变化
    
    物理模型：
        dH/dt = (Q_in - Q_out) / A
        
        其中：
        - H: 水位 (m)
        - Q_in: 入流量 (m³/s)
        - Q_out: 出流量，与闸门开度和水位有关 (m³/s)
        - A: 水库/河道断面面积 (m²)
    """

    def __init__(self, initial_level=5.0, area=1000.0, inflow=10.0):
        """
        初始化闸门系统
        
        参数:
            initial_level: 初始水位 (米)，默认5.0米
            area: 水库/河道有效面积 (平方米)，默认1000m²
            inflow: 上游来水流量 (立方米/秒)，默认10m³/s
        """
        self.water_level = initial_level  # 当前水位 (m)
        self.area = area                   # 有效面积 (m²)
        self.base_inflow = inflow         # 基础来水流量 (m³/s)
        self.gate_opening = 50.0          # 当前闸门开度 (%)
        self.max_discharge = 20.0         # 闸门全开时的最大泄流能力 (m³/s)
        
    def get_inflow(self, t):
        """
        获取t时刻的来水流量（可模拟洪水过程）
        
        参数:
            t: 当前时间 (秒)
        返回:
            来水流量 (m³/s)
        """
        # 简单模型：基础流量 + 可选的洪峰模拟
        # 在 t=100-200s 之间模拟一次洪水过程
        if 100 <= t <= 200:
            # 洪峰：流量增加到2倍
            peak_time = 150
            if t <= peak_time:
                factor = 1 + (t - 100) / 50  # 线性上升到2倍
            else:
                factor = 2 - (t - 150) / 50  # 线性下降回1倍
            return self.base_inflow * factor
        return self.base_inflow
    
    def calculate_outflow(self):
        """
        计算当前出流量
        
        出流量 = 闸门开度 × 最大泄流能力 × 水位系数
        水位越高，同等开度下出流量越大（水头压力）
        
        返回:
            出流量 (m³/s)
        """
        # 水位系数：假设标准水位5米时系数为1
        level_factor = (self.water_level / 5.0) ** 0.5  # 平方根关系
        level_factor = max(0.1, min(level_factor, 2.0))  # 限制在0.1-2.0之间
        
        outflow = (self.gate_opening / 100.0) * self.max_discharge * level_factor
        return max(0, outflow)  # 出流量不能为负
    
    def update(self, gate_opening, dt, t):
        """
        更新系统状态
        
        参数:
            gate_opening: 闸门开度 (0-100%)
            dt: 时间步长 (秒)
            t: 当前时间 (秒)，用于计算来水流量
            
        返回:
            (当前水位, 来水流量, 出水流量)
        """
        # 更新闸门开度
        self.gate_opening = max(0, min(100, gate_opening))
        
        # 计算进出流量
        inflow = self.get_inflow(t)
        outflow = self.calculate_outflow()
        
        # 更新水位
        # dH = (Q_in - Q_out) × dt / A
        delta_level = (inflow - outflow) * dt / self.area
        self.water_level += delta_level
        
        # 水位限制（不能为负，也不能超过最大值）
        self.water_level = max(0.5, min(self.water_level, 15.0))
        
        return self.water_level, inflow, outflow


class PIDAPIClient:
    """PID控制器API客户端"""

    def __init__(self, base_url):
        self.base_url = base_url

    def create_controller(self, controller_id, Kp, Ki, Kd, setpoint, 
                          output_limits=(None, None)):
        """创建PID控制器"""
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
            "starting_output": 50.0  # 初始开度50%
        }
        response = requests.post(url, json=data)
        return response.json()

    def compute_output(self, controller_id, input_value, dt=None):
        """计算PID控制器输出"""
        url = f"{self.base_url}/pid/compute"
        data = {
            "controller_id": controller_id,
            "input_value": input_value,
            "dt": dt
        }
        response = requests.post(url, json=data)
        return response.json()

    def set_setpoint(self, controller_id, setpoint):
        """设置目标值"""
        url = f"{self.base_url}/pid/setpoint"
        data = {
            "controller_id": controller_id,
            "setpoint": setpoint
        }
        response = requests.post(url, json=data)
        return response.json()

    def delete_controller(self, controller_id):
        """删除控制器"""
        url = f"{self.base_url}/pid/delete/{controller_id}"
        response = requests.delete(url)
        return response.json()

    def get_info(self, controller_id):
        """获取控制器信息"""
        url = f"{self.base_url}/pid/info/{controller_id}"
        response = requests.get(url)
        return response.json()


def run_simulation():
    """
    运行闸门水位控制模拟
    
    场景说明：
    1. 初始状态：水位5米，目标水位5米，闸门开度50%
    2. 系统稳定后，在t=100s时发生洪水，来水流量增加
    3. PID控制器自动调节闸门开度，维持水位稳定
    4. 观察控制效果
    """
    
    # 初始化系统
    gate_system = WaterGateSystem(
        initial_level=5.0,  # 初始水位5米
        area=1000.0,        # 有效面积1000m²
        inflow=10.0         # 基础来水10m³/s
    )
    api_client = PIDAPIClient(API_BASE_URL)
    
    print("=" * 70)
    print("PID控制器API调用示例 - 闸门控制闸前水位")
    print("=" * 70)
    print(f"API服务地址: {API_BASE_URL}")
    print(f"控制器ID: {CONTROLLER_ID}")
    print()
    
    # ============= 闸门控制PID参数说明 =============
    # 注意：水位控制与温度控制的方向相反！
    # 
    # 温度控制：误差正(目标>实际) → 加大加热 → 温度上升 → Kp为正
    # 水位控制：误差正(目标>实际) → 减小开度 → 水位上升 → Kp为负
    #
    # 因此使用负的Kp值！
    #
    # Kp = -20: 水位每低于目标1米，开度减少20%
    # Ki = -0.5: 累积误差补偿
    # Kd = -5: 抑制水位快速变化
    
    print("[步骤1] 创建PID控制器")
    print("-" * 50)
    
    # 先删除可能存在的旧控制器
    api_client.delete_controller(CONTROLLER_ID)
    
    result = api_client.create_controller(
        controller_id=CONTROLLER_ID,
        Kp=-20.0,     # 负的比例增益（水位控制方向相反）
        Ki=-0.5,      # 负的积分增益
        Kd=-5.0,      # 负的微分增益
        setpoint=5.0,  # 目标水位5米
        output_limits=(0, 100)  # 闸门开度限制在0-100%
    )
    
    print(f"创建结果: {result['message']}")
    print(f"PID参数: Kp=-20, Ki=-0.5, Kd=-5 (负值用于水位控制)")
    print(f"目标水位: 5.0米")
    print(f"闸门开度限制: 0-100%")
    print()
    
    if result['code'] != 200:
        print(f"创建失败: {result['message']}")
        return
    
    # 运行控制循环
    print("[步骤2] 开始控制循环（离散时间模拟）")
    print("-" * 50)
    
    # 数据记录
    time_data = []           # 时间轴
    level_data = []          # 实际水位
    setpoint_data = []       # 目标水位
    gate_opening_data = []   # 闸门开度
    inflow_data = []         # 来水流量
    outflow_data = []        # 出水流量
    p_data, i_data, d_data = [], [], []
    
    # 模拟参数
    dt = 1.0                  # 时间步长1秒
    simulation_duration = 300 # 模拟300秒（5分钟）
    total_steps = int(simulation_duration / dt)
    target_level = 5.0
    
    print(f"模拟时长: {simulation_duration}秒")
    print(f"初始水位: {gate_system.water_level}米")
    print(f"目标水位: {target_level}米")
    print(f"在t=100-200s期间将发生洪水（来水流量增加）")
    print()
    print("控制过程:")
    print()
    
    current_gate_opening = 50.0  # 初始开度
    
    for step in range(total_steps):
        t = step * dt
        
        # 调用API计算控制输出
        result = api_client.compute_output(
            controller_id=CONTROLLER_ID,
            input_value=gate_system.water_level,
            dt=dt
        )
        
        if result['code'] != 200:
            print(f"计算失败: {result['message']}")
            continue
        
        # 获取PID输出（闸门开度）
        data = result['data']
        current_gate_opening = data['output']
        components = data['components']
        
        # 更新系统状态
        level, inflow, outflow = gate_system.update(current_gate_opening, dt, t)
        
        # 记录数据
        time_data.append(t)
        level_data.append(level)
        setpoint_data.append(target_level)
        gate_opening_data.append(current_gate_opening)
        inflow_data.append(inflow)
        outflow_data.append(outflow)
        p_data.append(components['proportional'])
        i_data.append(components['integral'])
        d_data.append(components['derivative'])
        
        # 每30秒打印一次状态
        if step % 30 == 0:
            error = target_level - level
            print(f"  t={t:5.0f}s | "
                  f"水位:{level:5.2f}m | "
                  f"目标:{target_level:4.1f}m | "
                  f"误差:{error:+5.2f}m | "
                  f"开度:{current_gate_opening:5.1f}% | "
                  f"入流:{inflow:5.1f} | "
                  f"出流:{outflow:5.1f} m3/s")
        
        # 洪水开始和结束提示
        if step == 100:
            print(f"\n  >>> t={t}s: 洪水开始，来水流量增加! <<<\n")
        if step == 200:
            print(f"\n  >>> t={t}s: 洪水结束，来水流量恢复 <<<\n")
    
    print()
    print("[步骤3] 模拟结束，清理资源")
    print("-" * 50)
    
    # 获取最终状态
    info = api_client.get_info(CONTROLLER_ID)
    if info['code'] == 200:
        print(f"最终控制器状态:")
        print(f"  - 目标水位: {info['data']['setpoint']}米")
        print(f"  - 最终水位: {gate_system.water_level:.2f}米")
        print(f"  - 最终开度: {gate_system.gate_opening:.1f}%")
    
    api_client.delete_controller(CONTROLLER_ID)
    print("控制器已删除")
    print()
    
    # 绘制结果
    print("[步骤4] 绘制控制效果图")
    print("-" * 50)
    
    fig, axes = plt.subplots(4, 1, figsize=(14, 12))
    
    # 图1: 水位追踪
    axes[0].plot(time_data, level_data, 'b-', linewidth=2, label='Actual Level')
    axes[0].plot(time_data, setpoint_data, 'r--', linewidth=2, label='Target Level')
    axes[0].axvspan(100, 200, alpha=0.2, color='orange', label='Flood Period')
    axes[0].set_xlabel('Time (s)')
    axes[0].set_ylabel('Water Level (m)')
    axes[0].set_title('Water Level Control')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)
    axes[0].set_ylim([3, 8])
    
    # 图2: 闸门开度
    axes[1].plot(time_data, gate_opening_data, 'g-', linewidth=2, label='Gate Opening')
    axes[1].axvspan(100, 200, alpha=0.2, color='orange', label='Flood Period')
    axes[1].set_xlabel('Time (s)')
    axes[1].set_ylabel('Gate Opening (%)')
    axes[1].set_title('Gate Opening (PID Output)')
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)
    axes[1].set_ylim([0, 100])
    
    # 图3: 流量
    axes[2].plot(time_data, inflow_data, 'b-', linewidth=2, label='Inflow')
    axes[2].plot(time_data, outflow_data, 'r-', linewidth=2, label='Outflow')
    axes[2].axvspan(100, 200, alpha=0.2, color='orange', label='Flood Period')
    axes[2].set_xlabel('Time (s)')
    axes[2].set_ylabel('Flow Rate (m3/s)')
    axes[2].set_title('Inflow vs Outflow')
    axes[2].legend()
    axes[2].grid(True, alpha=0.3)
    
    # 图4: PID各分量
    axes[3].plot(time_data, p_data, 'r-', linewidth=1.5, label='P')
    axes[3].plot(time_data, i_data, 'g-', linewidth=1.5, label='I')
    axes[3].plot(time_data, d_data, 'b-', linewidth=1.5, label='D')
    axes[3].axvspan(100, 200, alpha=0.2, color='orange', label='Flood Period')
    axes[3].set_xlabel('Time (s)')
    axes[3].set_ylabel('Component Value')
    axes[3].set_title('PID Components')
    axes[3].legend()
    axes[3].grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('gate_control_result.png', dpi=150)
    print("Control result saved: gate_control_result.png")
    
    try:
        plt.show()
    except:
        print("(No display, image saved to file)")
    
    print()
    print("=" * 70)
    print("Simulation Complete!")
    print("=" * 70)


def print_explanation():
    """打印闸门控制说明"""
    print("""
================================================================================
                    Gate Water Level Control - PID API Example
================================================================================

  [Control Scenario]
  ----------------------------------------------------------------------------
  A gate control system that automatically adjusts gate opening to maintain
  upstream water level at a target value.

  [Control Variables]
  ----------------------------------------------------------------------------
    - Setpoint     : Target water level (e.g., 5.0 meters)
    - Input        : Current measured water level (m)
    - Output       : Gate opening percentage (0-100%)

  [Control Logic] - IMPORTANT: Reverse direction!
  ----------------------------------------------------------------------------
  Unlike temperature control, water level control works in REVERSE:

    Water level HIGH (above target)
        -> Error NEGATIVE (target - actual < 0)
        -> Need to INCREASE gate opening
        -> More water flows out
        -> Level DECREASES

    Water level LOW (below target)
        -> Error POSITIVE (target - actual > 0)
        -> Need to DECREASE gate opening
        -> Less water flows out
        -> Level INCREASES

  Therefore, we use NEGATIVE PID gains (Kp, Ki, Kd < 0)!

  [PID Parameters for Gate Control]
  ----------------------------------------------------------------------------
    - Kp = -20  : For each 1m below target, reduce opening by 20%
    - Ki = -0.5 : Accumulated error compensation
    - Kd = -5   : Dampen rapid level changes

  [API Workflow]
  ----------------------------------------------------------------------------
    1. POST /pid/create  - Create controller with negative gains
    2. POST /pid/compute - Send current water level, get gate opening
    3. Apply gate opening to physical gate
    4. Repeat step 2-3 in control loop

================================================================================
""")


if __name__ == '__main__':
    print_explanation()
    print()
    
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print("[OK] API service connected!")
            print()
            run_simulation()
        else:
            print(f"[ERROR] API service error: {response.status_code}")
    except requests.exceptions.ConnectionError:
        print(f"[ERROR] Cannot connect to API: {API_BASE_URL}")
        print("  Please ensure the API service is running.")
    except requests.exceptions.Timeout:
        print(f"[ERROR] Connection timeout: {API_BASE_URL}")

