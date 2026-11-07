# Codex 内嵌开发进度卡片

RelayForge Development 0.1.14 将默认展示改为聊天内嵌紧凑卡片。卡片采用已确认
的灰阶、系统字体、信息行与分隔线，首屏展示任务、工作流、已加载 Skill、当前
动作、变更、验证与剩余事项。完整步骤、加载记录与验证依据在卡片内展开。
不再注册 thread 侧栏入口，不默认打开整个侧边应用。

## 信息来源

`load_progress_skill` 真实读取本插件 `skills/<slug>/SKILL.md` 并把说明返回给
Agent，同时保存任务内的名称、读取时间、内容 SHA-256 和来源。核心工作流
加载也会更新当前工作流。只有成功加载的记录进入首屏；计划使用不算已加载。
文件读取失败、名称不存在、路径越界或符号链接不会产生记录。

**已加载不等于已执行或成功。** 记录证明加载工具读取了哪份说明，不能证明
Agent 后续遵守了它，更不是宿主级 Skill 执行审计。仅覆盖经该工具加载的插件
内 Skill；外部 Skill、宿主自动加载或直接读取但未经过该工具的说明不自动推断。
没有记录时显示“未记录”，而不是“未使用”。

步骤、当前动作、变更和验证结果由 Agent 根据实际工作申报，界面不推导百分比、
ETA 或工具活动。验证有独立状态，测试数量必须附简短依据；任务结束不会把
未执行、失败或部分验证自动改为通过。卡片不运行测试、不读取真实日志。

## 运行与兼容

- PATH 中需要 Python 3.11+；运行服务只使用标准库。
- 界面和 SDK 已打包，运行时无需 npm、CDN、API Key 或外部服务。
- portable 注册使用根 `plugin.json` / `mcp.json`，兼容注册使用
  `.codex-plugin/plugin.json` / `.mcp.json`；启动目录相对插件根解析。
- 更新插件后用新聊天验证新工具。重启 App 并不保证旧聊天获得新工具；若工具
  缺失，工作流继续开发并简短说明，不自动修改配置或循环要求重启。
- 不支持 MCP Apps 的宿主可继续 Skill 和文字工作流。跨平台 App 行为仍需独立验收。
- 已有 0.1.13 快照保留且可读取；缺少新增字段时显示未记录/未申报，不补造历史。

## 更新与隔离

`start_progress` 创建随机 UUID 并返回完整快照。`update_progress` 在真实阶段
变化时写入步骤及可选 `details`，返回简短确认。`load_progress_skill` 返回说明
和新 revision；协调 Agent 必须保留每次写入的 revision。`read_progress` 只供
卡片读取，`open_progress` 只在用户要求时再显示，不用于刷新。

`details` 可含 `current`、`change`、`remaining` 及 `verification`。验证状态为
not_run/running/passed/failed/partial/skipped/unavailable；数量可省略，提供时
要求非负整数及 evidence，拒绝自相矛盾的通过声明。details 整体替换，省略时
保持原值，因此新检查或需求变化后应主动清除过期结果。

界面每两秒读取绑定任务；更新不触发额外模型调用。没有“最近任务”回退或
全任务列表。旧请求、其他任务和过期 revision 不覆盖当前视图。并发更新使用
事务与 expected_revision，相同重试不重复记录。终态不可改写，新尝试使用新 ID。

状态使用 `PLUGIN_DATA/progress-panel`（兼容 `CLAUDE_PLUGIN_DATA`）；缺省为
macOS 的 `~/Library/Application Support/RelayForge/progress-panel`、Windows 的
`LOCALAPPDATA/RelayForge/progress-panel`、Linux 的
`XDG_STATE_HOME/relayforge-development/progress-panel`（缺省 `~/.local/state`）。
隔离验证使用 `RELAYFORGE_PROGRESS_DATA_DIR` 或服务 `--data-dir`，工具不接受
文件路径、命令或日志参数。

新申报清理超过七天未更新的任务，最多保留 200 个任务、每任务 20 次历史及
32 个唯一 Skill 加载记录。POSIX 数据目录/数据库仅当前用户可读写，拒绝数据
目录或数据库符号链接。任务 ID 是范围引用，不是同用户进程间的安全隔离。

## 验证与限制

2026-11-08，独立探针 0.0.1 在当前 macOS Codex App 的新聊天中完成内嵌合成
验收：用户确认聊天内可见；约 52 秒记录 18 次 App 读取与 18 次渲染回执，
版本推进 2→3→4→5，宿主报告 inline，最终完成。此结果支持内嵌展示与自动更新
能力，不等于正式插件或真实 Skill 行为已获宿主审计。原聊天未暴露新工具的
具体根因仍未确定。0.1.13 的旧侧栏验收不作为新版内嵌集成的通过证据。

开发检查：

```sh
npm --prefix progress_panel/web ci --ignore-scripts
npm --prefix progress_panel/web run build
npm --prefix progress_panel/web test
python3 -m pytest progress_panel/tests
python3 -m mypy --strict progress_panel/state.py progress_panel/server.py progress_panel/skills.py
python3 -m unittest discover -s tests -v
```

pytest/mypy 等仅为开发依赖。技能接入细则见
[内嵌进度契约](../skills/task-router/references/progress-panel.md)。
