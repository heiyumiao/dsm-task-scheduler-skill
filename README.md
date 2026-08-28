# DSM Task Scheduler Skill

一个用于创建、检查和修复群晖 DSM 计划任务的 Agent Skill。它面向需要在
**控制面板 → 任务计划** 中可见的任务，而不是仅写入 `/etc/crontab` 的隐藏任务。

仓库附带的 Python helper 会生成 DSM 7 的 `.task` 文件、同步任务计划，并尽量保留
被替换任务的备份。

## 功能

- 创建 daily / weekly 计划任务
- 按星期和时间配置执行计划
- 将命令同时写入 `cmd` 和 `app args`
- 按任务名替换已有任务，并先创建带时间戳的备份
- 调用 `synoschedtask --sync`，让任务出现在 DSM 控制面板中
- 支持启用/禁用任务及邮件通知字段

## 兼容性

核心的 [`SKILL.md`](SKILL.md) 和 Python helper 不依赖特定 AI 产品，可供任何支持
加载 Markdown skill 指令的 coding agent 使用。`agents/openai.yaml` 只是 Codex/OpenAI
客户端使用的可选界面元数据；不使用该客户端时可以忽略。

Python helper 也可以完全脱离 AI agent，直接在 NAS 上运行。

## 仓库结构

```text
.
├── SKILL.md
├── agents/
│   └── openai.yaml                # 可选的 Codex/OpenAI 界面元数据
└── scripts/
    └── create_dsm_scheduled_task.py
```

## 安装

将仓库克隆或复制到你的 agent 能够发现的 skills 目录。具体目录和调用语法以所用
agent 的文档为准。

例如，Codex 的个人安装方式为：

```bash
git clone https://github.com/heiyumiao/dsm-task-scheduler-skill.git \
  ~/.codex/skills/dsm-task-scheduler
```

重新启动或刷新 Codex 后，即可通过 `$dsm-task-scheduler` 调用。其他 agent 如果不支持
自动发现 skills，也可以把 `SKILL.md` 作为项目指令或上下文提供给它。

## 使用方式

可以直接向 agent 说明目标，例如：

```text
使用 dsm-task-scheduler skill，在我的群晖上创建一个工作日 16:35 运行的任务，
任务需要显示在 DSM 控制面板中，并把输出写入日志。
```

也可以把 helper 复制到 NAS 后直接执行：

```bash
scp scripts/create_dsm_scheduled_task.py nas:/tmp/
ssh nas "printf '%s\n' '/volume1/apps/example/run_task.sh' > /tmp/dsm_task_cmd.txt"
ssh nas "sudo python3 /tmp/create_dsm_scheduled_task.py \
  --name example-daily-task \
  --owner taskuser \
  --type weekly \
  --weekdays Mon,Tue,Wed,Thu,Fri \
  --hour 16 \
  --minute 35 \
  --command-file /tmp/dsm_task_cmd.txt"
```

`nas` 是示例 SSH Host，`taskuser` 和脚本路径也需要替换为你的实际配置。

## 环境要求

- Synology DSM 7
- NAS 上可用的 Python 3
- 可通过 SSH 登录，并能使用 `sudo` 写入
  `/usr/syno/etc/synoschedule.d/root/`
- 系统提供 `/usr/syno/bin/synoschedtask`

## 安全提示

- 操作前先确认 SSH 目标，避免修改错误的 NAS。
- helper 默认会按同名任务进行替换；旧 `.task` 文件会保存为
  `*.bak.dsm-task-scheduler_<timestamp>`。
- 从原始 crontab 迁移时，只删除完全相同的重复任务，避免误删系统条目。
- 建议先手动执行一次 wrapper script，确认权限和日志正常后再依赖计划任务。
- 不要把 NAS 地址、用户名、私钥、Token、通知邮箱或真实任务命令提交到仓库。

> [!WARNING]
> 该工具写入 DSM 的内部任务配置目录，并需要较高权限。不同 DSM 版本的内部格式
> 可能发生变化；请先在可恢复的环境中验证，并保留备份。

## 实现说明

DSM 7 的 UI 可见任务位于：

```text
/usr/syno/etc/synoschedule.d/root/*.task
```

helper 写入任务文件后执行：

```bash
sudo /usr/syno/bin/synoschedtask --sync
```

更多字段说明和 agent 执行流程见 [`SKILL.md`](SKILL.md)。
