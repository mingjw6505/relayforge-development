# RelayForge Progress Companion

**离线观察原型 · Codex 实时采集未验证。**

这是独立于插件运行路径的本地只读看板。它读取用户明确指定的既有元数据日志，不修改 Skill、Hook、logger、插件清单或 Codex 配置，不调用模型，不控制 Agent。

初次环境检查仅覆盖 PATH 和标准 Codex.app 路径；后续已找到 ChatGPT 应用内的 Codex、插件运行器和实际 RelayForge 日志，并通过历史日志兼容测试。当前仍未观察用户确认的新 Codex 普通任务，故[实现方案](../docs/codex-progress-visualization-implementation-plan.md)的 C1 实时门禁尚未完成，保持原型标识。下面提供源码运行与合成数据预览，不作为生产实时发布。

## 环境

- Python 3.11+，仅标准库；无需 pip、Node、MCP 或外部服务。
- 浏览器支持 ES modules、fetch 和 AbortController。
- 当前验证平台是 macOS / Python 3.12；Windows/Linux 尚未验收。
- 尚未制作可安装 wheel；不要以 `pip install` 是否成功作为交付标准。

## 快速预览（合成日志）

在仓库根目录执行：

```bash
python3 companion/examples/generate_demo.py companion/.local/demo-logs
PYTHONPATH=companion python3 -m relayforge_progress doctor --log-dir companion/.local/demo-logs
PYTHONPATH=companion python3 -m relayforge_progress serve \
  --log-dir companion/.local/demo-logs \
  --state-dir companion/.local/demo-cache \
  --open
```

生成器只接受不存在的新目录，拒绝覆盖已有目录。合成数据仅包含元数据示例，**不是 Codex 采集证据**，也不会调用生产 logger。

服务运行在前台，终端会打印仅监听 `127.0.0.1` 的随机端口地址。链接 fragment 含临时本地访问令牌，请勿分享。页面读取令牌后清除地址栏 fragment；刷新页面后须重新打开终端原链接。Ctrl+C 停止，停止后插件不受影响。

这会启动独立 Companion 页面，不会替换或更新当前 DeepSeek Harness GUI。

## 读取自己的既有日志

先找到已安装插件实际写入的 logs 目录，**不要指向完整 Codex 对话存储目录**。不自动扫描主目录、不替用户启用或信任 Hook。

```bash
PYTHONPATH=companion python3 -m relayforge_progress doctor --log-dir /absolute/plugin-data/logs
PYTHONPATH=companion python3 -m relayforge_progress serve \
  --log-dir /absolute/plugin-data/logs \
  --state-dir /absolute/independent-companion-cache
```

省略 `--state-dir` 时使用当前用户缓存下按来源路径哈希隔离的 Companion 子目录。缓存不能放在源日志目录内，不接受源路径的符号链接。明确指定缓存目录时也不能跨来源复用。POSIX 上已有缓存目录若允许组或其他用户访问会被拒绝；建议使用不存在的新独立目录，由 Companion 以仅当前用户可访问的权限创建。

缓存上限针对规范化记录数量和载荷，尚不包含 SQLite 已分配页/WAL 的物理磁盘硬上限；大规模长期使用前须完成生产磁盘预算验收。

`doctor` 只检查已有记录，不证明 Codex 已信任 Hook，不证明本次任务实际使用了插件；无论看到多少历史记录，当前版本均保持 `collection_verified=false`。

Windows PowerShell 的源码入口示例（仍需独立平台验收）：

```powershell
$env:PYTHONPATH = 'companion'
python -m relayforge_progress doctor --log-dir 'C:\actual\plugin-data\logs'
python -m relayforge_progress serve --log-dir 'C:\actual\plugin-data\logs' --state-dir 'C:\independent\companion-cache'
```

## 页面能展示什么

- 会话/轮次的已记录生命周期，工具开始、结束、有限 outcome 和配对耗时。
- 保留失败记录；后续另一个工具成功不会消除旧失败。
- 结构化工作流声明独立展示：路线、验证摘要、结束但受阻等结果。
- 声明重放、冲突、缺号、留存裁剪等完整性问题。
- 数据读取诊断、覆盖范围、最近事件和当前能力缺口。

“已观察到开始，未观察到结束”不证明进程仍存活；`outcome=completed` 不等于成功；Stop 不等于任务完成；Agent 声明不等于宿主验证。日志未签名，不能用作防篡改审计证据。

## 本次范围与尚未完成项

| 能力 | 当前状态 |
| --- | --- |
| 只读日志增量读取、独立 SQLite、白名单过滤 | 已实现原型 |
| 会话活动与声明流分离、质量诊断 | 已实现原型 |
| loopback API、短期令牌、严格 Host/Origin、静态资源白名单 | 已实现原型 |
| 浏览器列表/详情/诊断/主题与自动刷新 | 已实现原型 |
| SSE、分页 API、用户别名/绑定 | 延后；使用有界快照和轮询，不提供虚假入口 |
| Codex 原生计划读取、MCP App UI | 禁用，待目标版本能力验证和另行授权 |
| 业务阶段、测试名称/通过数量、等待审批原因、百分比/ETA | 不可用，不推断 |
| 后台启动、status/stop 命令、wheel 发布 | 延后，当前使用前台运行与 Ctrl+C |
| 真实 Codex C1、跨平台、性能预算及浏览器视觉验收 | 未通过/未完成，不能宣传为生产产品 |

现有实现方案是目标规格，不代表所有目标已交付。当前交付是受 P0 门禁限制的离线原型。

## 安全边界

API 只有健康、能力和快照读取；没有文件读取、命令执行、Git、审批或任务调度接口。服务不加载 CDN，不开放远程监听。令牌只在当前进程有效、不使用 OpenAI API Key、不读取登录凭据。缓存仅保存白名单元数据，不保存输入输出或完整原始日志；元数据、哈希 ID、时间依然可能敏感。

同机已被控制的进程、浏览器以及对源目录有写权限的主体不在保护承诺内。浏览器服务连接成功只表示 Companion 可达，不表示 Codex 正在执行。

## 测试

在仓库根目录执行：

```bash
python3 -m unittest discover -s companion/tests -v
python3 -m unittest discover -s tests -v
```

前端纯函数测试使用可用的 Node 可执行程序：

```bash
node --test companion/tests/ui.test.mjs
```

插件不变性测试依据[冻结摘要](protected-baseline.json)检查受保护运行文件。新增实现不应以更新摘要的方式掩盖插件变更。

## 后续真实 C1 验证

1. 在用户实际 Codex 版本中，确认现有插件 Hook 已加载且由用户信任。
2. 用户执行一次普通任务，不使用合成日志生成器。
3. 同一真实 session/turn 应包含可配对工具前后记录、工具名、稳定 ID、matched_start、duration、outcome，以及 Stop 或 Interrupt。
4. 保存脱敏字段检查和用户确认记录，补充原生计划、链接打开及平台测试结果。
5. 在完成生产安全、恢复、性能和浏览器验收前，不移除“离线原型”提示。

详细事实与验证结果见[实施报告](../docs/codex-progress-visualization-implementation-report.md)。
