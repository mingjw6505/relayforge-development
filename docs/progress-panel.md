# Codex 内嵌开发进度卡片

默认展示为聊天内嵌紧凑卡片，采用系统字体、细分隔线和少量状态色。首屏展示
任务、状态、实际任务步骤、当前动作／最终结果、开发模式、当前工作流及 Skill
记录（含工作流、外部及直接读取的 Skill）。绿色表示已完成，蓝色表示当前步骤，
灰色表示待处理；受阻使用红色。
正文 12px，标题 16px，卡片最大宽度 640px。较多步骤可在卡片内横向滚动，
当前步骤变化时自动定位到该步骤，其余更新保留手动滚动位置。
长工作流和 Skill 名称在窄屏换行，不截断名称。

“查看详情”默认收起，点击后在原卡片内展开进展与下一步、验证结果及依据、
最近三条阶段记录。所选方法与阶段、Skill 记录与来源各自再折叠一层。
同一任务更新保留展开状态，切换任务重置为收起。验证失败、部分验证或结果不可用，
以及任务完成但尚无通过结果时，首屏保留简短验证提示，避免折叠掩盖验证边界。
等待／受阻原因仍直接显示在首屏当前信息中。更新时间和暂停／恢复刷新在详情底部。
不再注册 thread 侧栏入口，不默认打开整个侧边应用。

0.1.17 增强阶段历史、等待对象、终态展示、刷新容错与步骤状态标识，提供复用
正式渲染器的本地模拟预览。

0.1.18 将 Quick/L1、Standard/L2、Large/L3 开发模式、具体动作和 SDD/TDD 等
方法阶段分开展示，并同步相应的工具参数、阶段校验与工作流申报约定。

## 信息来源

`load_progress_skill` 真实读取本插件 `skills/<slug>/SKILL.md` 并把说明返回给
Agent，同时保存任务内的名称、读取时间、内容 SHA-256 和来源。核心工作流
加载也会更新当前工作流。成功加载产生读取凭据；计划使用不算已加载。
文件读取失败、名称不存在、路径越界或符号链接不会产生记录。

`start_progress` / `update_progress` 的可选顶层 `skill_uses` 接收本任务实际使用的
外部、直接读取或宿主提供的 Skill。每条只有 `skill` 和 `via`，服务端标记
`source=agent_declared` 与接收时间 `recorded_at`，不生成读取凭据或内容哈希。
该时间是申报入库时间，不是推断的调用时刻。使用后随下一次进度更新同步，
卡片创建前已在同一任务实际使用的 Skill 可随 start 同步；结束任务前补齐尚未同步的使用。

```json
{
  "skill_uses": [
    {"skill": "host:imagegen", "via": "direct_read"},
    {"skill": "relayforge-product:brainstorming", "via": "skill_tool"},
    {"skill": "host:openai-docs", "via": "context"}
  ]
}
```

`skill` 使用真实目录中的 `命名空间:名称`：插件用其插件名，项目用 `project`，
个人或系统 Skill 用 `host`。裸名称归一为 `host:名称`，不接受路径或文件内容。
`via` 为 `direct_read`（直接读取说明）、`skill_tool`（Skill 工具调用）、`context`
（宿主提供且已实际应用的说明）。发现目录元数据、讨论名称或计划使用均不能上报。
输入不接受调用方设置来源、哈希、正文或时间。

`skill_uses` 是增量追加：每次最多 32 条，每任务最多 64 个不同的名称／渠道组合；
同一组合重报不增加记录，省略或 `[]` 保留已有记录。超限明确报错，不静默截断。
按 `expected_revision` 保持原有冲突与重试行为，终态不能补写或改写记录。
旧快照没有该字段仍可读取；旧工具不支持该参数时使用简短文字说明覆盖缺口，
不反复发送不支持的字段或自动修改宿主配置。

首屏“Skill 记录”按带命名空间的名称合并真实加载与实际使用申报；同名但来源
不同的 Skill 分开展示，详情保留每个来源。同一任务的阶段历史只保存当次新增
申报，不回填后来的记录。“当前工作流”仍由本插件的真实加载凭据选择，外部申报
不会覆盖它；加载收尾工作流不会让先前 Skill 从汇总列表消失。

**已加载不等于已执行或成功。** 记录证明加载工具读取了哪份说明，不能证明
Agent 后续遵守了它。外部／直接读取等使用由 Agent 申报，两种来源在详情分别
标记，不把申报伪装为工具或宿主审计。未同步的使用无法自动发现，不保证全局
零遗漏；没有记录时显示“未记录”，而不是“未使用”。不扫描聊天记录、用户日志或
所有 Skill 目录来猜测使用。官方 [Hooks 覆盖说明](https://learn.chatgpt.com/docs/hooks)
也将工具事件定位为部分审计能力；本实现不新增 Hook 或依赖其信任配置。

步骤、当前动作、变更和验证结果由 Agent 根据实际工作申报，界面不推导百分比、
ETA 或工具活动。验证有独立状态，测试数量必须附简短依据；任务结束不会把
未执行、失败或部分验证自动改为通过。卡片不运行测试、不读取真实日志。

## 开发模式、方法阶段与当前动作

卡片将三层信息分别展示：

- 开发模式：Quick / L1、Standard / L2、Large / L3，由路由选择后显式申报。
- 当前动作：例如“正在生成规格文档”，来自 `details.current`。
- 方法进度：在详情的“所选方法与阶段”中展示，例如 SDD 的范围确认、规格、
  计划、实现、验证、收尾，或实现中的
  TDD 失败用例／最小实现／重构循环。仅显示本任务实际选择的阶段，不自动套全流程。

`start_progress` / `update_progress` 增加可选顶层 `execution_mode` 和
`method_progress`。后者是最多三个唯一方法的数组，方法名为 `sdd`、`tdd`、
`coordination`；每条含 `method`、`status`、`phases`，阶段条目沿用步骤的
`label/status`。每方法最多八个唯一阶段、每标签最多 40 字。服务端添加
`source=agent_declared`，拒绝调用方伪造来源。

模式与最近加载的工作流分开保存：加载 `finishing-development` 不会覆盖 L2，
L2/L3 也不因加载相同工作流而混淆。模式相邻升降级；变更保留方法阶段与历史。
方法状态使用任务状态枚举；运行／等待方法必须有一个活动阶段，完成方法的阶段
必须全部完成或明确跳过。整体任务结束时须显式结束方法，不能保留运行中的阶段；
任务完成也不能掩盖受阻的方法。方法完成不表示验证通过。

省略模式／方法参数会保留已有值；显式传入方法数组会整体替换，`[]` 可在范围
真实变化时移除方法。首次未申报或旧快照显示“未申报”，不从步骤数量、日志或
加载凭据推断。阶段完成数按实际 done 统计，跳过数单独显示，不推导百分比。
新阶段历史保存当时的模式和方法进度，读历史不回填新状态。

只有确实生成文档时才描述为“生成规格文档”；SDD 仍允许现有约定支持的对话内
规格和轻量计划。协作进度表示交付／依赖阶段，不代表已启用子代理。模式申报不
更改路由、授权或工作流选择，也不新增测试、审查、提交等强制环节。

## 运行与兼容

- 当前注册无需 Node 或 Go；宿主需已有 Python 3.11+（含 SQLite）。
- 服务需要 Python 3.11+（含 sqlite3），只用 Python 标准库；引导器自动选择已有兼容解释器。
- 界面和 SDK 已打包，运行时无需 npm、CDN、API Key 或外部服务。
- portable 注册使用根 `plugin.json` / `mcp.json`，兼容注册使用
  `.codex-plugin/plugin.json` / `.mcp.json`；启动目录相对插件根解析。
- 更新插件后用新聊天验证新工具。重启 App 并不保证旧聊天获得新工具；若工具
  缺失，工作流继续开发并简短提醒，按环境恢复流程诊断一次；不静默安装或循环要求重启。
- 不支持 MCP Apps 的宿主可继续 Skill 和文字工作流。跨平台 App 行为仍需独立验收。
- 已有 0.1.13 快照保留且可读取；缺少新增字段时显示未记录/未申报，不补造历史。

### Automatic startup

两份 MCP 注册统一调用插件内的 `./scripts/start_progress`，保留 `cwd: "./"`。
每次启动都会选择当前可用的 Python，不修改注册、宿主设置或全局 PATH，
不下载或安装运行时，也不缓存某台机器的解释器路径：

- macOS/Linux 执行随包分发的 POSIX shell 脚本，依次探测 `python3`、`python`，
  再探测 `python3.15` 至 `python3.11`。
- Windows 的 Rust 进程启动规则会优先补全 `.exe`，因此同一注册调用随包分发的
  `scripts/start_progress.exe`，依次探测 `py -3`、`python`、`python3`，再探测
  `py -3.15` 至 `py -3.11`。
- 所有候选均须满足 Python 3.11+ 且支持 SQLite；失败、旧版本或 Store 别名返回
  9009 时继续下一候选。Windows 单次探测限时 1.5 秒，总探测预算 6.5 秒，
  另有有界管道收尾，避免别名挂起阻塞注册；POSIX shell 入口无外部进程超时保证。
- 探测不读取 MCP stdin，输出与错误不会混入协议 stdout。选定解释器后只启动
  一次服务，保留服务退出码；服务失败不触发另一个解释器重新启动任务。
- 候选全部不可用时，启动失败并向 stderr 给出 Python/PATH 检查提示，工作流
  继续使用文字回退。仍须在宿主 PATH 中已有至少一个可工作的候选命令。

启动字段与插件路径限制见 [Agent Plugins 规范](https://agent-plugins.org/specification)；
Windows 扩展名选择见 [Rust Command 文档](https://doc.rust-lang.org/std/process/struct.Command.html#platform-specific-behavior)。
Windows 启动器按 x86 构建；其他架构及桌面宿主行为仍须目标机验收。
服务只依赖 Python 标准库；原生启动器自带所需 Go 运行代码，用户无需安装 Go。
源码、许可证、构建版本与摘要见 [启动器构建说明](../scripts/progress_launcher/README.md)。

插件更新同时携带固定注册和两种入口，无需用户执行配置脚本。上一版尚未发布的
手动配置脚本与 cmd 入口已移除。打包回归检查两种入口、源码／二进制摘要和
全新安装后再次覆盖注册的启动行为，避免把本机配置结果当作发布默认值。

`RELAYFORGE_PYTHON` 可严格指定一个解释器路径（不能填 `py -3` 等命令串）。
失败时不会偷偷改用其他 Python；路径仅来自用户环境，不写入插件注册。

## 环境自检与协助修复

保留已有隔离自检和条件恢复流程，主入口可直接运行自检，无需 Node：

```powershell
.\scripts\start_progress.exe --doctor
```

macOS/Linux 使用 `./scripts/start_progress --doctor`。自检通过所选解释器运行
`progress_panel.doctor`，检查模块、工具、打包 HTML 和临时目录内的 SQLite，
不读取真实任务。`host_tools`、`host_ui`、`state_directory` 明确为 `unverified`。
自检 JSON 只在 `--doctor` 模式输出；正常 MCP 的额外诊断仅写 stderr。

| 结果 / 退出码 | 后续动作 |
| --- | --- |
| `runtime_ready` / 0 | 本地检查通过，继续确认宿主工具和卡片显示 |
| `python_unavailable` / 78 | 查已有解释器、严格覆盖、版本、SQLite、PATH 或别名；预算耗尽不代表未安装 Python |
| `package_check_failed` / 70 | Python 正常，检查插件包或临时 SQLite，不盲目重装 Python |
| 服务非零退出 | 保留退出码，不切换解释器重放 MCP 输入 |

[环境恢复流程](../skills/task-router/references/progress-environment.md) 保留一次性提醒、
优先已有运行时、授权后协助修复／安装、运行时和宿主 UI 分层验收。开发请求不
自动授权安装软件，不修改插件缓存，不绕过管理员或安全限制。插件整体未加载
时无法保证自动提醒。旧 `scripts/progress-launcher.cjs` 及其测试作为可选兼容入口
保留，不被当前 MCP 注册调用；只有使用该旧入口时才需要 Node.js 18+。

需要排查时，可选运行只读探针（正常启动不需要执行）：

```powershell
py -3 scripts/check_progress.py
```

macOS/Linux 使用 `python3 scripts/check_progress.py`，或用可用的 `python`
替代。探针通过临时数据目录验证实际启动及 `initialize`、`tools/list`，不创建
任务、不读取真实任务／Hook 日志、不改注册。Python 的 Windows 进程封装与
Rust 的扩展名规则不同，因此该探针显式选取随包分发的 `.exe`；宿主自动解析
和 inline 渲染仍需在目标 Codex 中独立验证。

可按以下三层排查：

1. 启动探针失败：检查是否存在可工作的 Python 3.11+／SQLite／PATH，服务尚未注册。
2. 探针通过但聊天里没有工具：重新加载已更新的插件，用新聊天检查；旧聊天
   不会因为单独启动服务就必然补充工具，避免循环重启。加载方式见
   [OpenAI 插件打包说明](https://developers.openai.com/plugins/build/plugins)。
3. 工具可用但创建卡片报步骤错误：`start_progress` 必须恰有一个 `active`
   步骤，不能把唯一的步骤设为 `pending`。继续使用同一任务的 ID 和 revision；
   收尾、提交或推送阶段也沿用该卡片，工具缺失时继续文字回退。

`progress_panel/tests/test_launcher.py` 验证真实 MCP 发现、更新不需配置、
POSIX 回退及随包 Windows 产物。Go 启动器测试通过真实子进程覆盖旧解释器、
9009、探测挂起、参数与 stdin 传递以及服务退出码；可在 Windows 上运行同一组
测试，但其他系统上的通过不代表 Windows 原生或宿主渲染验收通过。

## 更新与隔离

`start_progress` 创建随机 UUID 并返回完整快照。`update_progress` 在真实阶段
变化时写入步骤及可选 `details`，返回简短确认。`load_progress_skill` 返回说明
和新 revision；协调 Agent 必须保留每次写入的 revision。`read_progress` 只供
卡片读取，`open_progress` 只在用户要求时再显示，不用于刷新。

`details` 可含 `current`、`change`、`remaining`、`reason`、`waiting_for` 及
`verification`。`reason` 是简短的等待／受阻原因，`waiting_for` 为 `user` 或
`external`。等待对象缺省显示“等待中”；只有明确申报 `user` 才显示“等待你确认”。
验证状态为
not_run/running/passed/failed/partial/skipped/unavailable；数量可省略，提供时
要求非负整数及 evidence，拒绝自相矛盾的通过声明。details 整体替换，省略时
保持有效原值，因此新检查或需求变化后应主动清除过期结果。离开等待状态会清除
`waiting_for`，非等待／受阻状态会清除 `reason`。完成／取消时清除旧动作及剩余事项，
保留独立验证结论；旧快照在渲染时也不会显示终态与“正在做”矛盾的内容。

界面可见时每两秒读取绑定任务；相同 revision 只更新同步状态，不重建卡片内容。
页面隐藏时暂停读取，恢复可见后同步；用户手动暂停不会被可见性变化取消。
更新不触发额外模型调用。没有“最近任务”回退或
全任务列表。旧请求、其他任务和过期 revision 不覆盖当前视图。并发更新使用
事务与 expected_revision，相同重试不重复记录。终态不可改写，新尝试使用新 ID。

临时同步失败会保留最后申报并退避重试；任务不存在等永久错误显示“记录不可用”
并停止轮询。运行中超过 90 秒无阶段申报仅在同步正常时提示，不把等待、长检查或
断连推断为执行卡死。“阶段申报时间”与连接状态分别显示。

新阶段历史保留当时的简短详情、当前步骤和验证依据，默认最近 3 条，可展开当前
保留的全部记录（最多 20 条）。旧历史没有的详情不补造。卡片仍是有界的 Agent
阶段记录，不是原始工具日志或无限审计日志。

状态使用 `PLUGIN_DATA/progress-panel`（兼容 `CLAUDE_PLUGIN_DATA`）；缺省为
macOS 的 `~/Library/Application Support/RelayForge/progress-panel`、Windows 的
`LOCALAPPDATA/RelayForge/progress-panel`、Linux 的
`XDG_STATE_HOME/relayforge-development/progress-panel`（缺省 `~/.local/state`）。
隔离验证使用 `RELAYFORGE_PROGRESS_DATA_DIR` 或服务 `--data-dir`，工具不接受
文件路径、命令或日志参数。

新申报清理超过七天未更新的任务，最多保留 200 个任务、每任务 20 次历史及
32 个唯一 Skill 加载凭据和 64 个 Skill 使用申报组合。POSIX 数据目录/数据库仅当前用户可读写，拒绝数据
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
node --test scripts/progress-launcher.test.cjs
node scripts/progress-launcher.cjs --doctor
```

模拟预览复用正式卡片的 `card.html`、`card.css`、`view.mjs` 和 `render.mjs`，
只使用本地示例数据，不调用 MCP 工具、不改真实任务。生成可嵌入的预览片段：

```sh
npm --prefix progress_panel/web run preview -- /absolute/path/progress-card-preview.html
```

可切换进行中、验证中、用户／外部等待、完成（含部分验证）、受阻、取消、断连、
记录不可用和旧快照；展开记录可回看阶段详情。模拟预览验证展示与交互，不能替代
插件安装后在真实宿主中的验收。

pytest/mypy 等仅为开发依赖。技能接入细则见
[内嵌进度契约](../skills/task-router/references/progress-panel.md)。
