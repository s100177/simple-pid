from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Tuple, Dict, Any
import sys
import os

# 添加项目根目录到Python路径（兼容本地开发和Docker环境）
# Docker环境：/app/api/app.py -> project_root = /app (PYTHONPATH已设置为/app)
# 本地环境：./api/app.py -> project_root = ./
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 导入PID控制器
# 在Docker中：PYTHONPATH=/app，simple_pid位于/app/simple_pid/
# 在本地：project_root已添加到sys.path，simple_pid位于./simple_pid/
from simple_pid.pid import PID

app = FastAPI(title="PID Controller API", description="PID控制器API服务", version="1.0.0")

# 存储PID控制器实例的字典
pid_controllers: Dict[str, PID] = {}


# ============= 响应模型 =============
class BaseResponse(BaseModel):
    """基础响应模型"""
    data: Optional[Any] = None
    code: int = Field(default=200, description="状态码，200表示成功")
    message: str = Field(default="success", description="响应消息")


# ============= 请求模型 =============
class PIDCreateRequest(BaseModel):
    """创建PID控制器请求"""
    controller_id: str = Field(..., description="控制器唯一标识ID")
    Kp: float = Field(default=1.0, description="比例增益")
    Ki: float = Field(default=0.0, description="积分增益")
    Kd: float = Field(default=0.0, description="微分增益")
    setpoint: float = Field(default=0, description="目标设定值")
    sample_time: Optional[float] = Field(default=0.01, description="采样时间（秒）")
    output_limits: Optional[Tuple[Optional[float], Optional[float]]] = Field(
        default=(None, None), description="输出限制 (最小值, 最大值)"
    )
    output_rate_limits: Optional[Tuple[Optional[float], Optional[float]]] = Field(
        default=(None, None), description="输出变化率限制"
    )
    auto_mode: bool = Field(default=True, description="是否启用自动模式")
    proportional_on_measurement: bool = Field(default=False, description="比例项是否基于测量值")
    differential_on_measurement: bool = Field(default=True, description="微分项是否基于测量值")
    starting_output: float = Field(default=0.0, description="初始输出值")
    dead_zone: float = Field(default=0.0, description="死区范围。当输出变化量小于此值时，不执行调整，用于降低震荡")


class PIDUpdateRequest(BaseModel):
    """更新PID控制器请求"""
    controller_id: str = Field(..., description="控制器唯一标识ID")
    input_value: float = Field(..., description="当前输入值（测量值）")
    dt: Optional[float] = Field(default=None, description="时间步长（可选）")


class PIDSetpointRequest(BaseModel):
    """设置目标值请求"""
    controller_id: str = Field(..., description="控制器唯一标识ID")
    setpoint: float = Field(..., description="新的目标设定值")


class PIDTuningsRequest(BaseModel):
    """设置PID参数请求"""
    controller_id: str = Field(..., description="控制器唯一标识ID")
    Kp: float = Field(..., description="比例增益")
    Ki: float = Field(..., description="积分增益")
    Kd: float = Field(..., description="微分增益")


class PIDResetRequest(BaseModel):
    """重置PID控制器请求"""
    controller_id: str = Field(..., description="控制器唯一标识ID")


class PIDAutoModeRequest(BaseModel):
    """设置自动模式请求"""
    controller_id: str = Field(..., description="控制器唯一标识ID")
    enabled: bool = Field(..., description="是否启用自动模式")
    last_output: Optional[float] = Field(default=None, description="最后的输出值")


# ============= API接口 =============
@app.get("/", response_model=BaseResponse)
async def root():
    """API根路径"""
    return BaseResponse(
        data={"message": "欢迎使用PID控制器API服务"},
        code=200,
        message="success"
    )


@app.get("/health")
async def health():
    """健康检查端点"""
    return {"status": "healthy"}


@app.post("/pid/createPlus", response_model=BaseResponse)
async def createPlus_pid_controller(request: PIDCreateRequest):
    """
    创建一个新的PID控制器
    """
    try:
        # 检查控制器ID是否已存在
        if request.controller_id in pid_controllers:
            del pid_controllers[request.controller_id]
        
        # 创建PID控制器
        pid = PID(
            Kp=request.Kp,
            Ki=request.Ki,
            Kd=request.Kd,
            setpoint=request.setpoint,
            sample_time=request.sample_time,
            output_limits=request.output_limits,
            output_rate_limits=request.output_rate_limits,
            auto_mode=request.auto_mode,
            proportional_on_measurement=request.proportional_on_measurement,
            differential_on_measurement=request.differential_on_measurement,
            starting_output=request.starting_output,
            dead_zone=request.dead_zone
        )
        
        pid_controllers[request.controller_id] = pid
        
        return BaseResponse(
            data={
                "controller_id": request.controller_id,
                "Kp": request.Kp,
                "Ki": request.Ki,
                "Kd": request.Kd,
                "setpoint": request.setpoint
            },
            code=200,
            message="PID控制器创建成功"
        )
    
    except Exception as e:
        return BaseResponse(
            data=None,
            code=500,
            message=f"创建PID控制器失败: {str(e)}"
        )


@app.post("/pid/create", response_model=BaseResponse)
async def create_pid_controller(request: PIDCreateRequest):
    """
    创建一个新的PID控制器
    """
    try:
        # 检查控制器ID是否已存在
        if request.controller_id in pid_controllers:
            return BaseResponse(
                data=None,
                code=400,
                message=f"控制器ID '{request.controller_id}' 已存在"
            )
        
        # 创建PID控制器
        pid = PID(
            Kp=request.Kp,
            Ki=request.Ki,
            Kd=request.Kd,
            setpoint=request.setpoint,
            sample_time=request.sample_time,
            output_limits=request.output_limits,
            output_rate_limits=request.output_rate_limits,
            auto_mode=request.auto_mode,
            proportional_on_measurement=request.proportional_on_measurement,
            differential_on_measurement=request.differential_on_measurement,
            starting_output=request.starting_output,
            dead_zone=request.dead_zone
        )
        
        pid_controllers[request.controller_id] = pid
        
        return BaseResponse(
            data={
                "controller_id": request.controller_id,
                "Kp": request.Kp,
                "Ki": request.Ki,
                "Kd": request.Kd,
                "setpoint": request.setpoint
            },
            code=200,
            message="PID控制器创建成功"
        )
    
    except Exception as e:
        return BaseResponse(
            data=None,
            code=500,
            message=f"创建PID控制器失败: {str(e)}"
        )


@app.post("/pid/compute", response_model=BaseResponse)
async def compute_pid_output(request: PIDUpdateRequest):
    """
    计算PID控制器输出
    """
    try:
        # 检查控制器是否存在
        if request.controller_id not in pid_controllers:
            return BaseResponse(
                data=None,
                code=404,
                message=f"控制器ID '{request.controller_id}' 不存在"
            )
        
        pid = pid_controllers[request.controller_id]
        
        # 调用PID控制器计算输出
        output = pid(request.input_value, dt=request.dt)
        
        # 获取各个组件值
        p, i, d = pid.components
        
        return BaseResponse(
            data={
                "output": output,
                "input": request.input_value,
                "setpoint": pid.setpoint,
                "components": {
                    "proportional": p,
                    "integral": i,
                    "derivative": d
                }
            },
            code=200,
            message="计算成功"
        )
    
    except ValueError as e:
        return BaseResponse(
            data=None,
            code=400,
            message=f"参数错误: {str(e)}"
        )
    except Exception as e:
        return BaseResponse(
            data=None,
            code=500,
            message=f"计算失败: {str(e)}"
        )


@app.post("/pid/setpoint", response_model=BaseResponse)
async def set_setpoint(request: PIDSetpointRequest):
    """
    设置PID控制器的目标值
    """
    try:
        if request.controller_id not in pid_controllers:
            return BaseResponse(
                data=None,
                code=404,
                message=f"控制器ID '{request.controller_id}' 不存在"
            )
        
        pid = pid_controllers[request.controller_id]
        pid.setpoint = request.setpoint
        
        return BaseResponse(
            data={"setpoint": request.setpoint},
            code=200,
            message="设定值更新成功"
        )
    
    except Exception as e:
        return BaseResponse(
            data=None,
            code=500,
            message=f"设置目标值失败: {str(e)}"
        )


@app.post("/pid/tunings", response_model=BaseResponse)
async def set_tunings(request: PIDTuningsRequest):
    """
    设置PID控制器的调参参数
    """
    try:
        if request.controller_id not in pid_controllers:
            return BaseResponse(
                data=None,
                code=404,
                message=f"控制器ID '{request.controller_id}' 不存在"
            )
        
        pid = pid_controllers[request.controller_id]
        pid.tunings = (request.Kp, request.Ki, request.Kd)
        
        return BaseResponse(
            data={
                "Kp": request.Kp,
                "Ki": request.Ki,
                "Kd": request.Kd
            },
            code=200,
            message="PID参数更新成功"
        )
    
    except Exception as e:
        return BaseResponse(
            data=None,
            code=500,
            message=f"设置PID参数失败: {str(e)}"
        )


@app.post("/pid/reset", response_model=BaseResponse)
async def reset_pid(request: PIDResetRequest):
    """
    重置PID控制器
    """
    try:
        if request.controller_id not in pid_controllers:
            return BaseResponse(
                data=None,
                code=404,
                message=f"控制器ID '{request.controller_id}' 不存在"
            )
        
        pid = pid_controllers[request.controller_id]
        pid.reset()
        
        return BaseResponse(
            data={"controller_id": request.controller_id},
            code=200,
            message="PID控制器重置成功"
        )
    
    except Exception as e:
        return BaseResponse(
            data=None,
            code=500,
            message=f"重置失败: {str(e)}"
        )


@app.post("/pid/auto_mode", response_model=BaseResponse)
async def set_auto_mode(request: PIDAutoModeRequest):
    """
    设置PID控制器的自动模式
    """
    try:
        if request.controller_id not in pid_controllers:
            return BaseResponse(
                data=None,
                code=404,
                message=f"控制器ID '{request.controller_id}' 不存在"
            )
        
        pid = pid_controllers[request.controller_id]
        pid.set_auto_mode(request.enabled, last_output=request.last_output)
        
        return BaseResponse(
            data={
                "auto_mode": request.enabled,
                "controller_id": request.controller_id
            },
            code=200,
            message=f"自动模式已{'启用' if request.enabled else '禁用'}"
        )
    
    except Exception as e:
        return BaseResponse(
            data=None,
            code=500,
            message=f"设置自动模式失败: {str(e)}"
        )


@app.get("/pid/info/{controller_id}", response_model=BaseResponse)
async def get_pid_info(controller_id: str):
    """
    获取PID控制器信息
    """
    try:
        if controller_id not in pid_controllers:
            return BaseResponse(
                data=None,
                code=404,
                message=f"控制器ID '{controller_id}' 不存在"
            )
        
        pid = pid_controllers[controller_id]
        p, i, d = pid.components
        
        return BaseResponse(
            data={
                "controller_id": controller_id,
                "tunings": {
                    "Kp": pid.Kp,
                    "Ki": pid.Ki,
                    "Kd": pid.Kd
                },
                "setpoint": pid.setpoint,
                "auto_mode": pid.auto_mode,
                "output_limits": pid.output_limits,
                "output_rate_limits": pid.output_rate_limits,
                "components": {
                    "proportional": p,
                    "integral": i,
                    "derivative": d
                }
            },
            code=200,
            message="获取信息成功"
        )
    
    except Exception as e:
        return BaseResponse(
            data=None,
            code=500,
            message=f"获取信息失败: {str(e)}"
        )


@app.delete("/pid/delete/{controller_id}", response_model=BaseResponse)
async def delete_pid_controller(controller_id: str):
    """
    删除PID控制器
    """
    try:
        if controller_id not in pid_controllers:
            return BaseResponse(
                data=None,
                code=404,
                message=f"控制器ID '{controller_id}' 不存在"
            )
        
        del pid_controllers[controller_id]
        
        return BaseResponse(
            data={"controller_id": controller_id},
            code=200,
            message="PID控制器删除成功"
        )
    
    except Exception as e:
        return BaseResponse(
            data=None,
            code=500,
            message=f"删除失败: {str(e)}"
        )


@app.get("/pid/list", response_model=BaseResponse)
async def list_pid_controllers():
    """
    列出所有PID控制器
    """
    try:
        controller_list = []
        for controller_id, pid in pid_controllers.items():
            controller_list.append({
                "controller_id": controller_id,
                "Kp": pid.Kp,
                "Ki": pid.Ki,
                "Kd": pid.Kd,
                "setpoint": pid.setpoint,
                "auto_mode": pid.auto_mode
            })
        
        return BaseResponse(
            data={
                "controllers": controller_list,
                "total": len(controller_list)
            },
            code=200,
            message="获取列表成功"
        )
    
    except Exception as e:
        return BaseResponse(
            data=None,
            code=500,
            message=f"获取列表失败: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)

