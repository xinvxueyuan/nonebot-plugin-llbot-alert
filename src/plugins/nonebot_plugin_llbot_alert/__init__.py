"""llbot-alert：LLBot 状态告警插件（纯后端邮件通知）。

监控两类互相独立的故障并发送邮件告警：

- **服务异常**：``on_bot_disconnect`` —— OneBot 连接断开（LLBot 进程崩溃、
  网络中断等）；
- **账号异常**：``POST /get_status`` 显示 ``online``/``good`` 为假 —— 账号被
  踢下线、登录失效或被冻结。

状态恢复时补发恢复通知；同类异常在冷却期内不重复发送。

"""

from nonebot.plugin import PluginMetadata

from .config import Config

__plugin_meta__ = PluginMetadata(
    name="llbot-alert",
    description=(
        "LLBot 状态告警：检测服务异常（OneBot 连接断开）与账号异常（账号下线），"
        "通过 SMTP 发送告警与恢复邮件（纯后端，无前端界面）"
    ),
    usage=(
        "配置 LLBOT_ALERT_* 环境变量后自动生效："
        "启动时轮询 /get_status 检测账号状态，并监听 on_bot_disconnect 检测服务异常。"
    ),
    type="application",
    config=Config,
    supported_adapters={"~onebot.v11"},
)

# 导入即注册 NoneBot 钩子（启动轮询 + 连接事件监听）。
from . import hooks

__all__ = ["Config", "hooks"]
