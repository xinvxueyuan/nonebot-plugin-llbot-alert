"""LLBot 状态告警插件配置。

配置项均通过环境变量（前缀 ``LLBOT_ALERT_``）注入，由 NoneBot2 的
``get_plugin_config`` 统一解析；环境变量名与字段名大小写不敏感。

SMTP 凭据不写死在代码中，部署时由 ``.env`` / ``.env.dev`` 提供。

"""

from pydantic import BaseModel, Field


class Config(BaseModel):
    """LLBot 状态告警插件配置。

    Attributes:
        llbot_alert_enabled: 是否启用告警（关闭时既不轮询也不监听连接事件）。
        llbot_alert_service_name: 告警文案中的服务名。
        llbot_alert_api_url: LLBot 的 ``/get_status`` 接口地址。
        llbot_alert_api_token: 调用该接口的 Bearer Token（留空表示不带认证）。
        llbot_alert_api_timeout: 单次接口调用超时（秒）。
        llbot_alert_poll_interval: 账号状态轮询间隔（秒）。
        llbot_alert_accounts: 需要监控的账号 QQ 号集合；空集合表示全部。
        llbot_alert_to: 告警邮件收件人集合。
        llbot_alert_cooldown: 同类告警的最小重发间隔（秒），防止刷邮件。
        llbot_alert_notify_recovery: 状态恢复时是否补发恢复通知。
        llbot_alert_smtp_host: SMTP 服务器地址。
        llbot_alert_smtp_port: SMTP 端口（SSL 通常为 465）。
        llbot_alert_smtp_ssl: 是否使用 SMTP_SSL。
        llbot_alert_smtp_user: SMTP 登录用户名。
        llbot_alert_smtp_pass: SMTP 登录密码。
        llbot_alert_mail_from: 发件人地址。
        llbot_alert_mail_from_name: 发件人显示名。

    """

    llbot_alert_enabled: bool = True
    llbot_alert_service_name: str = "LLBot"
    llbot_alert_api_url: str = "http://127.0.0.1:3000/get_status"
    llbot_alert_api_token: str = ""
    llbot_alert_api_timeout: float = 10.0
    llbot_alert_poll_interval: int = 60
    llbot_alert_accounts: set[int] = Field(default_factory=set)
    llbot_alert_to: set[str] = Field(default_factory=set)
    llbot_alert_cooldown: int = 600
    llbot_alert_notify_recovery: bool = True
    llbot_alert_smtp_host: str = ""
    llbot_alert_smtp_port: int = 465
    llbot_alert_smtp_ssl: bool = True
    llbot_alert_smtp_user: str = ""
    llbot_alert_smtp_pass: str = ""
    llbot_alert_mail_from: str = ""
    llbot_alert_mail_from_name: str = "LLBot Alert"
