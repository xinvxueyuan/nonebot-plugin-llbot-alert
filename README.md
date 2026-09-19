# llbot-alert

LLBot 状态告警插件（NoneBot2）：检测 LLBot 的**服务异常**与**账号异常**，通过
SMTP 发送告警邮件与恢复通知。**纯后端，无前端界面**。

## 监控的两类故障

两类故障互相独立，来源与含义都不同：

| 类别 | 检测来源 | 含义 |
| --- | --- | --- |
| **账号异常** | OneBot 心跳事件的 `status.online` / `status.good` | 连接仍在但账号已下线：被踢下线、登录失效或被冻结 |
| **服务异常** | NoneBot `on_bot_disconnect` + 心跳静默守护 | OneBot 连接断开（进程崩溃、网络中断），或连接假死/事件通道阻塞（心跳停发） |

> 心跳（`meta_event/heartbeat`）随连接持续到达，`status` 字段即账号状态，因此
> **无需轮询任何 HTTP 接口**。连接层故障由断开事件与心跳静默共同覆盖。

## 工作流程

1. LLBot 每 `interval` 毫秒推送一次心跳 → 抽取 `status` 判定账号状态；
   `online` / `good` 任为假 → **账号异常** → 发告警邮件；
2. Bot 与 NoneBot 的连接断开 → **服务异常** → 发告警邮件；
3. 超过 `LLBOT_ALERT_HEARTBEAT_TIMEOUT` 秒未收到心跳 → **服务异常**
   （连接假死）→ 发告警邮件；
4. 状态恢复 → 补发**恢复通知**（可用 `LLBOT_ALERT_NOTIFY_RECOVERY` 关闭）；
5. 同一异常在 `LLBOT_ALERT_COOLDOWN` 秒内不重复发送，超过冷却期且仍异常则重发提醒。

## 快速开始

前置要求：Python 3.13、[uv](https://docs.astral.sh/uv/)、NoneBot2 + OneBot V11。

```bash
uv sync --all-groups          # 安装依赖
cp .env.example .env.dev      # 配置（部署到 zhenxun 时写入其 .env.dev）
uv run nb run                 # 本地运行
```

## 配置

全部配置项通过环境变量注入（前缀 `LLBOT_ALERT_`，大小写不敏感），由 NoneBot2 的
`get_plugin_config` 解析。SMTP 凭据由部署侧提供，不写死在代码中。

| 变量 | 说明 | 默认值 |
| --- | --- | --- |
| `LLBOT_ALERT_ENABLED` | 是否启用告警 | `true` |
| `LLBOT_ALERT_SERVICE_NAME` | 邮件文案中的服务名 | `LLBot` |
| `LLBOT_ALERT_ACCOUNTS` | 需监控的账号 QQ 号集合，`[]` 表示全部 | `[]` |
| `LLBOT_ALERT_HEARTBEAT_TIMEOUT` | 心跳静默超时（秒），`0` 表示不检测 | `60` |
| `LLBOT_ALERT_CHECK_INTERVAL` | 心跳静默检查间隔（秒，下限 5） | `15` |
| `LLBOT_ALERT_TO` | 告警邮件收件人集合 | `[]` |
| `LLBOT_ALERT_COOLDOWN` | 同类告警最小重发间隔（秒），`0` 表示仅状态变化时发送 | `600` |
| `LLBOT_ALERT_NOTIFY_RECOVERY` | 恢复时是否补发恢复通知 | `true` |
| `LLBOT_ALERT_SMTP_TIMEOUT` | SMTP 连接/发送超时（秒），超时放弃本次发送 | `10` |
| `LLBOT_ALERT_SMTP_HOST` | SMTP 服务器地址 | 空 |
| `LLBOT_ALERT_SMTP_PORT` | SMTP 端口（SSL 通常 465） | `465` |
| `LLBOT_ALERT_SMTP_SSL` | 是否使用 `SMTP_SSL` | `true` |
| `LLBOT_ALERT_SMTP_USER` | SMTP 登录用户名 | 空 |
| `LLBOT_ALERT_SMTP_PASS` | SMTP 登录密码 | 空 |
| `LLBOT_ALERT_MAIL_FROM` | 发件人地址（须为受 SPF 授权的域名地址） | 空 |
| `LLBOT_ALERT_MAIL_FROM_NAME` | 发件人显示名 | `LLBot Alert` |

未配置收件人或 SMTP 服务器时插件仍可运行，只跳过邮件发送（日志中记录告警）。

## 部署到 zhenxun

1. 打包插件目录并放入 `zhenxun/plugins/`；
2. 在 zhenxun 的 `.env.dev` 追加上述 `LLBOT_ALERT_*` 配置（**追加，不要覆盖**）；
3. 重启 zhenxun，确认日志出现「llbot-alert 心跳静默守护已启动」。

> 邮件服务器的防火墙需放行 zhenxun 所在主机访问 SMTP 端口，否则发送会超时失败。

## 开发

```bash
uv run ruff check .        # 静态检查
uv run ruff format --check .
uv run pyright             # 类型检查
uv run pytest              # 测试
```

## 实现说明

- **账号状态**取自心跳事件，无需调用 `/get_status` 等 HTTP 接口；
- 心跳缺少 `status` 字段时按**不健康**处理（宁可告警不可漏报）；
- SMTP 发送带超时保护（`asyncio.wait_for` + `smtplib` 超时），服务器不可达时
  按超时放弃，避免阻塞事件循环导致进程无法及时退出；
- 仅依赖标准库 `smtplib` / `email`，不引入额外邮件库。
