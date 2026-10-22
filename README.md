# nonebot-plugin-llbot-alert

[![Python](https://img.shields.io/badge/python-3.13-blue)](pyproject.toml)

LLBot 状态告警插件（NoneBot2，qbot 子模块）：心跳/连接异常经 SMTP 邮件告警与恢复通知；纯后端，无前端界面与用户命令。

> **qbot 插件** · 宿主仓库：[xinvxueyuan/qbot](https://github.com/xinvxueyuan/qbot)

> - 监控两类互相独立的故障：**账号异常**（心跳 `status.online` / `status.good`）与**服务异常**（连接断开 + 心跳静默守护）；
> - 心跳随连接持续到达，`status` 即账号状态，**无需轮询任何 HTTP 接口**；
> - 状态恢复补发恢复通知，同类告警在冷却期内不重复发送。

## 功能特性

- **账号异常检测**：从 OneBot 心跳事件（`meta_event/heartbeat`）抽取 `status.online` / `status.good`，任一为假（被踢下线、登录失效或被冻结）即发告警邮件；心跳缺少 `status` 字段时按**不健康**处理（宁可告警不可漏报）。
- **服务异常检测**：监听 NoneBot `on_bot_disconnect` 钩子，OneBot 连接断开（LLBot 进程崩溃、网络中断）即发告警邮件。
- **心跳静默守护**：连接仍在但超过 `LLBOT_ALERT_HEARTBEAT_TIMEOUT` 秒未收到任何心跳（连接假死或事件通道阻塞）判定为服务异常，比单靠断开事件更早发现问题。
- **恢复通知**：服务重新连接、账号状态恢复时补发恢复邮件，可用 `LLBOT_ALERT_NOTIFY_RECOVERY=false` 关闭。
- **冷却与重发**：同一异常在 `LLBOT_ALERT_COOLDOWN` 秒内不重复发送；持续异常超过冷却期后重发提醒。
- **纯后端**：无前端界面、无用户命令，配置 `LLBOT_ALERT_*` 环境变量后自动生效。

### 监控的两类故障

两类故障互相独立，来源与含义都不同：

| 类别 | 检测来源 | 含义 |
| --- | --- | --- |
| **账号异常** | OneBot 心跳事件的 `status.online` / `status.good` | 连接仍在但账号已下线：被踢下线、登录失效或被冻结 |
| **服务异常** | NoneBot `on_bot_disconnect` + 心跳静默守护 | OneBot 连接断开（进程崩溃、网络中断），或连接假死/事件通道阻塞（心跳停发） |

> 心跳（`meta_event/heartbeat`）随连接持续到达，`status` 字段即账号状态，因此
> **无需轮询任何 HTTP 接口**。连接层故障由断开事件与心跳静默共同覆盖。

## 安装

- 运行依赖：`nonebot2[fastapi,httpx,websockets] >= 2.5.0`、`nonebot-adapter-onebot >= 2.4.6`；Python `>=3.13, <3.14`。
- 额外依赖：无——邮件发送只用标准库 `smtplib` / `email`。
- 适配器：OneBot V11（`supported_adapters = {"~onebot.v11"}`）。
- 安装（宿主以 git 子模块引入）：

```bash
git submodule add -b main https://github.com/xinvxueyuan/nonebot-plugin-llbot-alert.git vendor/nonebot-plugin-llbot-alert
git -C vendor/nonebot-plugin-llbot-alert checkout <钉定 SHA>
```

- 宿主 `[tool.nonebot] plugin_dirs` 加一行 `vendor/nonebot-plugin-llbot-alert/src/plugins`
- 本地开发运行：`uv sync --all-groups` 安装依赖，`cp .env.example .env.dev` 后按需填写，`uv run nb run` 启动。

## 配置

全部配置项通过环境变量注入（前缀 `LLBOT_ALERT_`，大小写不敏感），由 NoneBot2 的
`get_plugin_config` 解析。SMTP 凭据由部署侧提供，不写死在代码中。

| 键 | 默认 | 说明 |
| --- | --- | --- |
| `LLBOT_ALERT_ENABLED` | `true` | 是否启用告警；关闭时既不处理心跳也不监听连接事件 |
| `LLBOT_ALERT_SERVICE_NAME` | `LLBot` | 邮件文案中的服务名 |
| `LLBOT_ALERT_ACCOUNTS` | `[]` | 需监控的账号 QQ 号集合（JSON 数组）；空集合表示监控全部 |
| `LLBOT_ALERT_TO` | `[]` | 告警邮件收件人集合（JSON 数组） |
| `LLBOT_ALERT_COOLDOWN` | `600` | 同类告警最小重发间隔（秒）；`0` 表示仅在状态变化时发送 |
| `LLBOT_ALERT_NOTIFY_RECOVERY` | `true` | 恢复时是否补发恢复通知 |
| `LLBOT_ALERT_HEARTBEAT_TIMEOUT` | `60` | 心跳静默超时（秒）；`0` 表示不检测静默 |
| `LLBOT_ALERT_CHECK_INTERVAL` | `15` | 心跳静默检查间隔（秒，下限 5） |
| `LLBOT_ALERT_SMTP_TIMEOUT` | `10` | SMTP 连接/发送超时（秒），超时放弃本次发送 |
| `LLBOT_ALERT_SMTP_HOST` | 空 | SMTP 服务器地址 |
| `LLBOT_ALERT_SMTP_PORT` | `465` | SMTP 端口（SSL 通常 465） |
| `LLBOT_ALERT_SMTP_SSL` | `true` | 是否使用 `SMTP_SSL` |
| `LLBOT_ALERT_SMTP_USER` | 空 | SMTP 登录用户名 |
| `LLBOT_ALERT_SMTP_PASS` | 空 | SMTP 登录密码 |
| `LLBOT_ALERT_MAIL_FROM` | 空 | 发件人地址（须为受 SPF 授权的域名地址）；留空时回落到 `LLBOT_ALERT_SMTP_USER` |
| `LLBOT_ALERT_MAIL_FROM_NAME` | `LLBot Alert` | 发件人显示名 |

未配置收件人或 SMTP 服务器时插件仍可运行，只跳过邮件发送（日志中记录告警）。

## 使用与命令

本插件**没有用户命令**：不注册任何 `on_command` / `on_alconna` 处理器，也没有前端界面。填好 `LLBOT_ALERT_*` 后，由 OneBot 心跳事件与 NoneBot `on_bot_disconnect` 钩子自动触发。

### 工作流程

1. LLBot 每 `interval` 毫秒推送一次心跳 → 抽取 `status` 判定账号状态；
   `online` / `good` 任为假 → **账号异常** → 发告警邮件；
2. Bot 与 NoneBot 的连接断开 → **服务异常** → 发告警邮件；
3. 超过 `LLBOT_ALERT_HEARTBEAT_TIMEOUT` 秒未收到心跳 → **服务异常**
   （连接假死）→ 发告警邮件；
4. 状态恢复 → 补发**恢复通知**（可用 `LLBOT_ALERT_NOTIFY_RECOVERY` 关闭）；
5. 同一异常在 `LLBOT_ALERT_COOLDOWN` 秒内不重复发送，超过冷却期且仍异常则重发提醒。

### 部署到 zhenxun

1. 打包插件目录并放入 `zhenxun/plugins/`；
2. 在 zhenxun 的 `.env.dev` 追加上述 `LLBOT_ALERT_*` 配置（**追加，不要覆盖**）；
3. 重启 zhenxun，确认日志出现「llbot-alert 心跳静默守护已启动」。

> 邮件服务器的防火墙需放行 zhenxun 所在主机访问 SMTP 端口，否则发送会超时失败。

## 开发与测试

```bash
uv run python -m pytest tests/ -q
uv run ruff check . && uv run ruff format --check .
uv run pyright
```

测试位于 `tests/`（`test_alerter.py`、`test_heartbeat.py`、`test_hooks.py`、`test_mailer.py`、`test_models.py`），与 `src/plugins/nonebot_plugin_llbot_alert` 下的同名模块一一对应。`pyproject.toml` 的 `dev` 组汇总 `lint`（Ruff、Pyright）与 `test`（nb-cli、nonebug、pytest、pytest-asyncio、pytest-cov、respx），用 `uv sync --all-groups` 安装。

### 实现说明

- **账号状态**取自心跳事件，无需调用 `/get_status` 等 HTTP 接口；
- 心跳缺少 `status` 字段时按**不健康**处理（宁可告警不可漏报）；
- SMTP 发送带超时保护（`asyncio.wait_for` + `smtplib` 超时），服务器不可达时
  按超时放弃，避免阻塞事件循环导致进程无法及时退出；
- 仅依赖标准库 `smtplib` / `email`，不引入额外邮件库。

## 许可证与相关仓库

### 许可证

MIT（见仓库根目录 `LICENSE` 文件，Copyright (c) 2026 新v学员 (xinvxueyuan)；`pyproject.toml` 的 `license` 字段同为 MIT）。

### 相关仓库

本插件是 [qbot](https://github.com/xinvxueyuan/qbot) 的子模块之一，以下仓库与它存在实际联动：

- [xinvxueyuan/qbot](https://github.com/xinvxueyuan/qbot) — 宿主，以 `vendor/nonebot-plugin-llbot-alert` 子模块引入并通过 `plugin_dirs` 加载。
- [xinvxueyuan/lingchu-bot](https://github.com/xinvxueyuan/lingchu-bot) — 群管理主插件，与本插件共用同一条 OneBot V11 / LLBot 连接，本插件告警的正是这条连接与账号状态。
- [xinvxueyuan/nonebot-plugin-info](https://github.com/xinvxueyuan/nonebot-plugin-info) — 读取各插件 `__plugin_meta__.extra` 生成功能菜单；本插件在其中声明了「系统 / 自动告警」条目。
