#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
蒲阳河倒虹吸出口节制闸PID控制仿真

此示例演示如何通过HTTP API调用PID控制器服务来实现倒虹吸出口节制闸的下游水位自动控制。

应用场景：
    倒虹吸工程中，通过调节出口节制闸开度，控制下游水位维持在目标值。

控制原理：
    - 被控对象：节制闸开度 (0-4米)
    - 控制目标：下游水位 (米)
    - 测量值：当前下游水位
    
    当水位高于目标 → 减小闸门开度 → 减少下泄流量 → 水位下降
    当水位低于目标 → 增大闸门开度 → 增加下泄流量 → 水位上升

设备特性：
    - 采样周期：5分钟（300秒）
    - 死区：调整量 < 0.05米时不调整（由PID底层实现）
    - 步进限制：每次调整量 ≤ 0.3米（由output_rate_limits实现）
"""

import time
import requests
from urllib.parse import quote
import matplotlib.pyplot as plt

plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

# ============= 配置参数 =============
API_BASE_URL = "http://localhost:5000"
CONTROLLER_ID = "JZZ55-蒲阳河倒虹吸出口节制闸2#"
TARGET_LEVEL = 61.643
SAMPLE_TIME = 300.0
MAX_GATE_CHANGE = 0.3  # 每次最大调整量（米）
MIN_GATE_CHANGE = 0.05  # 死区（米）


class InvertedSiphonGateSystem:
    """
    倒虹吸出口节制闸系统模拟器
    
    物理模型：
        - 上游：倒虹吸进口，水位相对稳定
        - 节制闸：控制从上游流入下游的水量
        - 下游：水位由闸门入流和自然出流决定
        
    控制逻辑：
        - 开度增大 → 入流增加 → 水位上升
        - 开度减小 → 入流减少 → 水位下降
    """

    def __init__(self, initial_downstream_level=61.0, upstream_level=62.0, 
                 downstream_area=5000.0, natural_outflow=15.0):
        """
        初始化倒虹吸系统
        
        参数:
            initial_downstream_level: 初始下游水位 (米)
            upstream_level: 上游水位 (米)，相对稳定
            downstream_area: 下游水域有效面积 (平方米)
            natural_outflow: 下游自然出流量 (立方米/秒)
        """
        self.downstream_level = initial_downstream_level
        self.upstream_level = upstream_level
        self.downstream_area = downstream_area
        self.natural_outflow = natural_outflow
        self.gate_opening = 1.5  # 初始闸门开度 (米)
        
        # 物理参数
        self.gate_width = 8.0  # 闸门宽度 (米)
        self.discharge_coefficient = 0.45  # 流量系数
        self.gravity = 9.81  # 重力加速度 (m/s²)
        
    def get_natural_outflow(self, t):
        """
        获取下游自然出流量（可模拟扰动）
        
        参数:
            t: 当前时间 (秒)
        返回:
            出流量 (m³/s)
        """
        # 在 t=1800-3600s (30-60分钟) 之间模拟出流增加（相当于下游用水增加）
        if 1800 <= t <= 3600:
            peak_time = 2700
            if t <= peak_time:
                factor = 1 + (t - 1800) / 900 * 0.3
            else:
                factor = 1.3 - (t - 2700) / 900 * 0.3
            return self.natural_outflow * factor
        return self.natural_outflow
    
    def calculate_gate_inflow(self):
        """
        计算通过节制闸流入下游的流量
        
        流量 = 流量系数 × 过流面积 × sqrt(2g × 水位差)
        
        返回:
            入流量 (m³/s)
        """
        # 水位差（上游 - 下游）
        head_diff = self.upstream_level - self.downstream_level
        head_diff = max(0.1, head_diff)  # 保持最小水头
        
        # 过流面积 = 闸门宽度 × 闸门开度
        flow_area = self.gate_width * self.gate_opening
        
        # 计算流量
        inflow = (self.discharge_coefficient * flow_area * 
                  (2 * self.gravity * head_diff) ** 0.5)
        
        return max(0, inflow)
    
    def update(self, gate_opening, dt, t):
        """
        更新系统状态
        
        参数:
            gate_opening: 闸门开度 (0-4米)
            dt: 时间步长 (秒)
            t: 当前时间 (秒)
            
        返回:
            (当前下游水位, 闸门入流量, 自然出流量)
        """
        # 更新闸门开度
        self.gate_opening = max(0, min(4, gate_opening))
        
        # 计算流量
        gate_inflow = self.calculate_gate_inflow()
        natural_outflow = self.get_natural_outflow(t)
        
        # 更新下游水位：入流 - 出流
        delta_level = (gate_inflow - natural_outflow) * dt / self.downstream_area
        self.downstream_level += delta_level
        
        # 水位限制
        self.downstream_level = max(60.0, min(self.downstream_level, 63.0))
        
        return self.downstream_level, gate_inflow, natural_outflow


class PIDAPIClient:
    """PID控制器API客户端"""

    def __init__(self, base_url):
        self.base_url = base_url

    def create_controller(self, controller_id, Kp, Ki, Kd, setpoint, 
                          sample_time, output_limits, output_rate_limits,
                          starting_output, dead_zone):
        """创建PID控制器"""
        url = f"{self.base_url}/pid/create"
        data = {
            "controller_id": controller_id,
            "Kp": Kp,
            "Ki": Ki,
            "Kd": Kd,
            "setpoint": setpoint,
            "sample_time": sample_time,
            "output_limits": list(output_limits),
            "output_rate_limits": list(output_rate_limits),
            "auto_mode": True,
            "proportional_on_measurement": False,
            "differential_on_measurement": True,
            "starting_output": starting_output,
            "dead_zone": dead_zone
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

    def delete_controller(self, controller_id):
        """删除控制器"""
        encoded_id = quote(controller_id, safe='')
        url = f"{self.base_url}/pid/delete/{encoded_id}"
        response = requests.delete(url)
        return response.json()

    def get_info(self, controller_id):
        """获取控制器信息"""
        encoded_id = quote(controller_id, safe='')
        url = f"{self.base_url}/pid/info/{encoded_id}"
        response = requests.get(url)
        return response.json()


def run_simulation():
    """
    运行倒虹吸闸门水位控制模拟
    
    场景说明：
    1. 初始状态：下游水位61.0米，目标水位61.643米
    2. 系统稳定后，在t=1800s（30分钟）时出流增加（扰动）
    3. PID控制器自动调节闸门开度，维持下游水位稳定
    """
    
    # 初始化系统（初始水位低于目标，测试调节能力）
    gate_system = InvertedSiphonGateSystem(
        initial_downstream_level=61.2,  # 初始下游水位61.2米（低于目标）
        upstream_level=62.5,            # 上游水位62.5米
        downstream_area=8000.0,         # 下游水域面积8000m²（增大惯性）
        natural_outflow=18.0            # 自然出流18m³/s
    )
    
    api_client = PIDAPIClient(API_BASE_URL)
    
    print("=" * 80)
    print("蒲阳河倒虹吸出口节制闸PID控制仿真")
    print("=" * 80)
    print(f"API服务地址: {API_BASE_URL}")
    print(f"控制器ID: {CONTROLLER_ID}")
    print(f"目标水位: {TARGET_LEVEL}米")
    print(f"采样周期: {SAMPLE_TIME}秒 ({SAMPLE_TIME/60:.0f}分钟)")
    print(f"单次动作限制: ≤ {MAX_GATE_CHANGE}")
    print()
    
    # ============= 创建PID控制器 =============
    print("[步骤1] 创建PID控制器")
    print("-" * 60)
    
    # 先删除可能存在的旧控制器
    api_client.delete_controller(CONTROLLER_ID)
    
    # PID参数说明：
    # - 正Kp：水位低于目标 → 误差正 → 开度增大 → 入流增加 → 水位上升
    # - output_rate_limits: (-0.001, 0.001) 允许双向变化，每秒最大0.001米
    result = api_client.create_controller(
        controller_id=CONTROLLER_ID,
        Kp=1.5,           # 比例增益
        Ki=0.0003,        # 积分增益（消除稳态误差）
        Kd=50,            # 微分增益（抑制振荡）
        setpoint=TARGET_LEVEL,
        sample_time=SAMPLE_TIME,
        output_limits=(0, 4),
        output_rate_limits=(-0.001, 0.001),  # 双向限制：±0.3米/300秒
        starting_output=1.5,
        dead_zone=0.05  # 死区：调整量 < 0.05米时不调整
    )
    
    print(f"创建结果: {result['message']}")
    print(f"PID参数: Kp=1.5, Ki=0.0003, Kd=50")
    print(f"目标水位: {TARGET_LEVEL}米")
    print(f"采样时间: {SAMPLE_TIME}秒")
    print(f"输出范围: 0-4米")
    print(f"输出变化率限制: ±0.001/秒 (确保每次≤0.3米)")
    print(f"死区: 0.05米")
    print(f"初始输出: 1.5米")
    print()
    
    if result['code'] != 200:
        print(f"创建失败: {result['message']}")
        return
    
    # ============= 运行控制循环 =============
    print("[步骤2] 开始控制循环")
    print("-" * 60)
    
    # 数据记录
    time_data = []
    level_data = []
    setpoint_data = []
    gate_opening_data = []
    inflow_data = []
    outflow_data = []
    p_data, i_data, d_data = [], [], []
    gate_change_data = []
    
    # 模拟参数
    dt_system = 60.0  # 物理系统更新步长60秒
    simulation_duration = 7200  # 模拟7200秒（2小时）
    total_steps = int(simulation_duration / dt_system)
    
    print(f"仿真时长: {simulation_duration}秒 ({simulation_duration/60:.0f}分钟)")
    print(f"物理更新步长: {dt_system}秒")
    print(f"PID采样周期: {SAMPLE_TIME}秒 ({SAMPLE_TIME/60:.0f}分钟)")
    print(f"初始下游水位: {gate_system.downstream_level}米")
    print(f"目标下游水位: {TARGET_LEVEL}米")
    print(f"在t=1800-3600s期间出流增加30%（模拟扰动）")
    print()
    print("控制过程:")
    print()
    
    current_gate_opening = 1.5
    last_gate_opening = 1.5
    time_since_last_control = 0.0
    components = {'proportional': 0, 'integral': 0, 'derivative': 0}
    gate_change = 0
    
    for step in range(total_steps):
        t = step * dt_system
        time_since_last_control += dt_system
        
        # 只在达到采样周期时调用PID（或第一次）
        if time_since_last_control >= SAMPLE_TIME or step == 0:
            result = api_client.compute_output(
                controller_id=CONTROLLER_ID,
                input_value=gate_system.downstream_level,
                dt=SAMPLE_TIME  # 传入采样周期
            )
            
            if result['code'] != 200:
                print(f"计算失败: {result['message']}")
                continue
            
            # 获取PID输出
            data = result['data']
            current_gate_opening = data['output']
            components = data['components']
            
            # 计算变化量
            gate_change = abs(current_gate_opening - last_gate_opening)
            if gate_change > 0.0001:
                last_gate_opening = current_gate_opening
            else:
                gate_change = 0
            
            time_since_last_control = 0.0
        
        # 更新系统状态
        level, inflow, outflow = gate_system.update(current_gate_opening, dt_system, t)
        
        # 记录数据
        time_data.append(t)
        level_data.append(level)
        setpoint_data.append(TARGET_LEVEL)
        gate_opening_data.append(current_gate_opening)
        inflow_data.append(inflow)
        outflow_data.append(outflow)
        p_data.append(components['proportional'])
        i_data.append(components['integral'])
        d_data.append(components['derivative'])
        gate_change_data.append(gate_change)
        
        # 每5分钟打印一次状态
        if step % 5 == 0:
            error = TARGET_LEVEL - level
            status = "保持" if gate_change == 0 else f"调整{gate_change:.3f}"
            print(f"  t={t/60:5.0f}min | "
                  f"水位:{level:6.3f}m | "
                  f"误差:{error:+6.3f}m | "
                  f"开度:{current_gate_opening:5.3f}m | "
                  f"状态:{status:8s} | "
                  f"入流:{inflow:5.1f} | "
                  f"出流:{outflow:5.1f} m3/s")
        
        # 扰动提示
        if step == 30:  # 1800秒
            print(f"\n  >>> t={t/60:.0f}min: 下游出流增加30%（扰动开始）<<<\n")
        if step == 60:  # 3600秒
            print(f"\n  >>> t={t/60:.0f}min: 出流恢复正常 <<<\n")
    
    print()
    print("[步骤3] 模拟结束")
    print("-" * 60)
    
    # 获取最终状态
    info = api_client.get_info(CONTROLLER_ID)
    if info['code'] == 200:
        print(f"最终控制器状态:")
        print(f"  - 目标水位: {info['data']['setpoint']}米")
        print(f"  - 最终水位: {gate_system.downstream_level:.3f}米")
        print(f"  - 最终开度: {gate_system.gate_opening:.3f}米")
        print(f"  - 稳态误差: {TARGET_LEVEL - gate_system.downstream_level:.3f}米")
    
    api_client.delete_controller(CONTROLLER_ID)
    print("控制器已删除")
    print()
    
    # 统计闸门变化
    gate_changes = [c for c in gate_change_data if c > 0]
    dead_zone_count = sum(1 for c in gate_change_data if c == 0)
    if gate_changes:
        max_change = max(gate_changes)
        avg_change = sum(gate_changes) / len(gate_changes)
        print(f"闸门变化统计:")
        print(f"  - 最大单次变化: {max_change:.4f}米 (限制: {MAX_GATE_CHANGE})")
        print(f"  - 平均单次变化: {avg_change:.4f}米")
        print(f"  - 总调整次数: {len(gate_changes)}")
        print(f"  - 死区次数: {dead_zone_count} (调整量 < {MIN_GATE_CHANGE}米)")
        print(f"  - 是否超限: {'是' if max_change > MAX_GATE_CHANGE else '否'}")
    print()
    
    # 绘制结果
    print("[步骤4] 绘制控制效果图")
    print("-" * 60)
    
    fig, axes = plt.subplots(5, 1, figsize=(16, 14))
    
    # 图1: 水位追踪
    axes[0].plot([t/60 for t in time_data], level_data, 'b-', linewidth=2, label='实际水位')
    axes[0].plot([t/60 for t in time_data], setpoint_data, 'r--', linewidth=2, label='目标水位')
    axes[0].axvspan(30, 60, alpha=0.2, color='orange', label='扰动期')
    axes[0].set_xlabel('时间 (分钟)')
    axes[0].set_ylabel('下游水位 (米)')
    axes[0].set_title('下游水位控制效果')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)
    axes[0].set_ylim([60.5, 62.5])
    
    # 图2: 闸门开度
    axes[1].plot([t/60 for t in time_data], gate_opening_data, 'g-', linewidth=2, label='闸门开度')
    axes[1].axvspan(30, 60, alpha=0.2, color='orange', label='扰动期')
    axes[1].set_xlabel('时间 (分钟)')
    axes[1].set_ylabel('闸门开度 (米)')
    axes[1].set_title('闸门开度变化 (PID输出)')
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)
    axes[1].set_ylim([0, 4])
    
    # 图3: 闸门单次变化量
    axes[2].plot([t/60 for t in time_data], gate_change_data, 'm-', linewidth=1.5, label='单次变化')
    axes[2].axhline(y=MAX_GATE_CHANGE, color='r', linestyle='--', linewidth=2, label=f'最大限制 {MAX_GATE_CHANGE}米')
    axes[2].axhline(y=MIN_GATE_CHANGE, color='orange', linestyle=':', linewidth=2, label=f'死区 {MIN_GATE_CHANGE}米')
    axes[2].axvspan(30, 60, alpha=0.2, color='orange', label='扰动期')
    axes[2].set_xlabel('时间 (分钟)')
    axes[2].set_ylabel('闸门变化量 (米)')
    axes[2].set_title('闸门单次变化量 (死区+步进控制)')
    axes[2].legend()
    axes[2].grid(True, alpha=0.3)
    axes[2].set_ylim([0, 0.35])
    
    # 图4: 流量
    axes[3].plot([t/60 for t in time_data], inflow_data, 'b-', linewidth=2, label='闸门入流')
    axes[3].plot([t/60 for t in time_data], outflow_data, 'r-', linewidth=2, label='自然出流')
    axes[3].axvspan(30, 60, alpha=0.2, color='orange', label='扰动期')
    axes[3].set_xlabel('时间 (分钟)')
    axes[3].set_ylabel('流量 (m³/s)')
    axes[3].set_title('闸门入流 vs 自然出流')
    axes[3].legend()
    axes[3].grid(True, alpha=0.3)
    
    # 图5: PID各分量
    axes[4].plot([t/60 for t in time_data], p_data, 'r-', linewidth=1.5, label='P分量')
    axes[4].plot([t/60 for t in time_data], i_data, 'g-', linewidth=1.5, label='I分量')
    axes[4].plot([t/60 for t in time_data], d_data, 'b-', linewidth=1.5, label='D分量')
    axes[4].axvspan(30, 60, alpha=0.2, color='orange', label='扰动期')
    axes[4].set_xlabel('时间 (分钟)')
    axes[4].set_ylabel('分量值')
    axes[4].set_title('PID各分量')
    axes[4].legend()
    axes[4].grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('puyanghe_gate_control_result.png', dpi=150)
    print("控制效果图已保存: puyanghe_gate_control_result.png")
    
    try:
        plt.show()
    except:
        print("(无法显示图形，已保存到文件)")
    
    print()
    print("=" * 80)
    print("仿真完成!")
    print("=" * 80)


def print_explanation():
    """打印控制说明"""
    print("""
================================================================================
              蒲阳河倒虹吸出口节制闸PID控制仿真
================================================================================

  [控制场景]
  ----------------------------------------------------------------------------
  倒虹吸工程中，通过调节出口节制闸开度，控制下游水位维持在目标值61.643米。

  [物理模型]
  ----------------------------------------------------------------------------
    - 上游水位：62.5米（相对稳定）
    - 节制闸：控制从上游流入下游的水量
    - 下游水位：由闸门入流和自然出流的差值决定
    
    关键关系：
    - 开度增大 -> 入流增加 -> 水位上升
    - 开度减小 -> 入流减少 -> 水位下降

  [PID控制逻辑]
  ----------------------------------------------------------------------------
    误差 = 目标水位 - 实际水位
    
    水位低于目标 -> 误差 > 0 -> PID输出增大 -> 开度增大 -> 水位上升
    水位高于目标 -> 误差 < 0 -> PID输出减小 -> 开度减小 -> 水位下降

  [工程约束]
  ----------------------------------------------------------------------------
    - 采样周期：300秒（5分钟）
    - 死区：0.05米（调整量 < 0.05米时不动作）
    - 步进限制：±0.3米/次（output_rate_limits = ±0.001/秒 × 300秒）
    - 闸门开度范围：0-4米

  [PID参数]
  ----------------------------------------------------------------------------
    - Kp = 1.5      : 比例增益（主要响应）
    - Ki = 0.0003   : 积分增益（消除稳态误差）
    - Kd = 50       : 微分增益（抑制振荡）
    - output_rate_limits = [-0.001, 0.001]  (双向限制)

  [仿真场景]
  ----------------------------------------------------------------------------
    1. 0-30分钟：初始水位61.0米，PID调节至目标61.643米
    2. 30-60分钟：下游出流增加30%（扰动）
    3. 60-120分钟：出流恢复正常，观察稳定性

================================================================================
""")


if __name__ == '__main__':
    print_explanation()
    print()
    
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print("[OK] API服务已连接!")
            print()
            run_simulation()
        else:
            print(f"[ERROR] API服务错误: {response.status_code}")
    except requests.exceptions.ConnectionError:
        print(f"[ERROR] 无法连接到API: {API_BASE_URL}")
        print("  请确保API服务正在运行。")
        print("  启动命令: cd api && python app.py")
    except requests.exceptions.Timeout:
        print(f"[ERROR] 连接超时: {API_BASE_URL}")
    except Exception as e:
        print(f"[ERROR] 发生错误: {e}")
