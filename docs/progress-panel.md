# Codex 开发进度面板

RelayForge Development 0.1.13 在插件中提供本地 MCP 进度面板。核心工作流在
Codex desktop 开发任务开始时调用 `start_progress`，在真实阶段切换和结束时
调用 `update_progress`。面板每两秒读取其绑定任务，展示步骤、当前工作、受阻、
最近更新及最终结果。它不读取 Hook 日志，也不解析提示词、源码或工具输出。

这是 Agent 主动申报的工作状态；对话仅保留关键沟通和必要文字兜底。步骤数不等于业务完成
百分比，经过时间不代表工具耗时；面板连接正常也不证明 Agent 正在执行。
小样本实测支持当前 Codex App 在调用展示工具后自动打开右侧面板，宿主报告
`fullscreen`。这不保证任意任务都被自动路由，也不是宿主生命周期事件直接打开。

## 安装与兼容

- 运行环境需要 PATH 中的 `python3`，版本 3.11+；Python 服务仅使用标准库。
- 根 `plugin.json` / `mcp.json` 是 portable 包；`.codex-plugin/plugin.json` /
  `.mcp.json` 提供 Codex 兼容注册。三份插件清单版本保持一致。
- MCP 以 `python3 -m progress_panel.server` 启动，工作目录相对插件根解析，
  配置中不包含开发机绝对路径，也不依赖目标项目目录。
- 界面及 MCP Apps SDK 已打包进插件；用户运行时无需 npm、CDN、API Key 或外部服务。
- 更新本地安装后，重启 Codex App，并在新会话测试新工具。仅更新文件不意味着
  已运行会话的 MCP 实例已经刷新。直接调用已有工作流会复用同一份面板规则。
- 当前自动打开验证环境为 macOS、ChatGPT desktop Codex 26.1103.32239。
  Windows/Linux 尚未完成 App 验收；若环境使用 `python` 或 `py -3`，需在宿主
  MCP 启动配置中选用可用的 Python 3.11+ 命令及参数，不能将整条命令写成可执行文件名。
  CLI、Claude Code 或不支持 MCP Apps 的宿主仍可继续技能工作流和简短文字更新。

如果工具不存在或服务不可用，工作流继续正常开发并说明面板不可用，不自动改
宿主配置、信任权限或安装依赖。用户关闭面板后不会在每次阶段更新时被强制重开；
需要时可请求 Agent 使用本任务 ID 调用 `open_progress`。

## 多任务与数据

每次新任务生成随机 UUID；更新及读取均要求明确的 `run_id`，没有“最近任务”
查询或全任务列表。面板同时仅绑定一个任务，旧轮询请求、其他任务的读取结果和
过期 revision 不会覆盖它。若宿主复用右侧面板，只有明确的展示工具结果可
切换到新任务，切换时丢弃旧请求并恢复刷新。主 Agent 持有任务 ID 与 revision，
子任务通过主 Agent 汇总状态。

工具接受短标题、单行阶段摘要和最多 12 个步骤，拒绝未知字段、重复 JSON 键、
超长请求和矛盾的完成声明。并发更新通过事务和 `expected_revision` 处理；相同
更新的丢失响应重试不会重复追加记录。状态为 `completed`、`blocked`、`cancelled`
后不可再改写；仍需等待输入时使用 `waiting`。

状态优先保存在 `PLUGIN_DATA/progress-panel`（兼容 `CLAUDE_PLUGIN_DATA`）。
无宿主数据目录时使用系统用户状态目录：macOS 为
`~/Library/Application Support/RelayForge/progress-panel`，Windows 为
`LOCALAPPDATA/RelayForge/progress-panel`，Linux 为
`XDG_STATE_HOME/relayforge-development/progress-panel`（缺省 `~/.local/state`）。
隔离测试可设置 `RELAYFORGE_PROGRESS_DATA_DIR` 或使用服务的 `--data-dir`。
这些选项只在启动时配置，工具没有文件路径、命令或日志读取参数。

新申报会清理超过七天未更新的任务，并最多保留 200 个任务、每任务最近 20 次
申报。旧任务可能因此不可恢复；缺失时面板报告不可用，不猜测状态。POSIX 数据
目录和数据库权限限制到当前用户，拒绝符号链接的数据目录或数据库。任务 UUID
是本地读取范围引用，不是对同用户恶意进程的安全隔离，也不是防篡改审计凭证。

## 构建与检查

界面源文件在 `progress_panel/web/src`，构建产物和第三方许可证随包提交：

```sh
npm --prefix progress_panel/web ci --ignore-scripts
npm --prefix progress_panel/web run build
npm --prefix progress_panel/web test
python3 -m pytest progress_panel/tests
python3 -m mypy --strict progress_panel/state.py progress_panel/server.py
```

pytest/mypy 等仅为开发检查工具，不属于插件运行依赖。已有仓库的标准库
unittest 检查继续保留。面板测试覆盖并发、任务隔离、重试、结束状态、
MCP 协议、输出边界和轮询行为；这些检查不替代目标 App 的实际渲染验收。

技能接入细则见[任务进度契约](../skills/task-router/references/progress-panel.md)。

## 本地集成验收

2026-11-07 在当前 macOS Codex App 的 0.1.13 本地预览包中完成合成验收：
重启后恢复一个任务并连续创建两个新任务，均观察到阶段更新和最终完成状态；
暂停期间保留旧状态，恢复后同步到最新阶段。预览包关闭 Hook，验收未读取真实日志。

本次宿主为展示调用创建了独立的侧栏标签，连续任务可能留下多个标签；没有
实测同一界面实例的复用。该兼容分支由前端回归检查覆盖，不能据此宣称宿主会
始终复用面板。原先“旧内容未切换”的观察来自旧标签，不能单独证明复用故障。
