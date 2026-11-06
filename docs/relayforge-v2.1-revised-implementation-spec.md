# RelayForge Development V2.1 完整修订方案与 Agent 实施规范

方案版本：V2.1-R1  
修订日期：2026-11-06  
项目：mingjw6505/relayforge-development  
上游：产品经理插件或用户提供的已明确需求  
下游：独立自动化测试 Agent  
核心架构：统一协调职责、三层执行策略、动态调整、共享研发能力、风险驱动验证、Test Handoff。

本方案规定 RelayForge 从接收明确需求到完成研发并交接测试的行为、数据契约、增量修改范围和阶段验收。保留现有 Quick、Standard、Large 名称，对应 L1、L2、L3；执行层级、风险等级、任务状态和交付状态分别管理。

本文件替代 V2.1 原方案中的同类规定，不需要再与原稿拼接执行。方案版本不等于插件发布版本。撰写、审查或保存本文件不构成修改插件代码、提交、推送或发布授权；用户明确要求实施后，Agent 按第十章及第十二章执行。

## 第一章 项目目标与实施边界

### 1.1 项目定位

RelayForge 是以 Codex 为主要执行环境、保留现有跨宿主兼容性的研发工作流插件，负责接收需求、分析代码库、技术设计、任务拆分、实现、Skill 选择、按需 Subagent 协作、Worktree 隔离、集成、研发验证、代码审查和测试交接。

RelayForge 不负责产品需求访谈、PRD 编写、用户故事和产品原型设计、产品交互决策、最终产品验收，也不替代测试 Agent 作出独立测试结论。

研发过程中可以读取既有需求、确认缺失事实和识别歧义。遇到会改变产品行为、公开契约、数据语义或安全边界的未决问题，返回上游或用户决策；不得为了继续执行而编造产品意图。等待期间可推进不依赖该决策的工作。

### 1.2 核心原则

1. L1 直接执行，不强制生成设计和计划文档。
2. L2 使用最小规格驱动开发，即 specification-driven development，简称 SDD；默认一个主 Agent。
3. L3 只在需要持续依赖协调时采用；多个 Agent 和并行执行均按需启用。
4. 风险决定验证强度，不直接决定路由等级。
5. 复用已有 Skill、任务信息、错误恢复、Worktree 和验证能力。
6. 不为流程完整而创建重复文档、测试、Agent 或后台基础设施。
7. 所有交付均区分实际修改、可能影响、实现状态、研发证据和独立测试结论。
8. 用户指令、仓库约束和宿主权限优先；路由和方案本身不授权外部或破坏性操作。

### 1.3 上游最小输入

| 输入 | 处理规则 |
| --- | --- |
| 需求 ID 或来源 | 优先复用上游 ID；没有 ID 时生成本地安全标识，并保留来源引用 |
| 目标和范围 | 至少明确希望观察到的行为和本次不做的内容 |
| 验收标准 | 复用原始标准和 ID；简单任务允许用用户已明确的结果描述 |
| 已知约束 | 包括兼容、安全、数据、环境及用户明确的预算或排除项 |
| 代码库上下文 | 从实际仓库发现技术栈、约定、测试入口和相关实现 |

上游未提供的信息先从当前对话和仓库查找。影响正确实现的关键缺口必须单独标记并暂停依赖它的任务。非关键实现细节按仓库惯例处理，不强制补写 PRD，不要求每个简单任务填写表单。

### 1.4 本次明确不建设的能力

不新建运行时调度服务、状态数据库、Agent 注册中心、后台服务或新的 Worktree 管理器。不新增 MCP 服务、Hook 或第三方运行依赖；保留已有可选 Hook，在现有日志脚本内增量扩展。

不建设产品经理插件与测试 Agent 的自动传输接口。当前生成 Markdown，由用户手动存入文档中心；未来自动化所需的来源、版本和代码可获取性信息在本版契约中预留。

## 第二章 目标架构与兼容规则

### 2.1 Orchestrator 的准确含义

本版 Orchestrator 是主 Agent 承担的统一协调职责，不是一个拦截所有 Skill 调用的强制运行时入口。task-router 是推荐路由入口；宿主仍可直接选择其他 Skill。

直接调用 development-workflow 时，该 Skill 从请求和代码补齐缺失的路由、验收、依赖、风险和授权上下文，不发起重复路由访谈。直接调用 finishing-development 或 delivery-handoff 时，读取实际成果、已有证据和缺口，不重新启动完整开发。

“只有一个统一 Orchestrator”表示同一任务由一个主协调者管理决策、所有权、集成和交付；不要求建立独立 Orchestrator Agent，也不承诺宿主强制所有调用都先经过 task-router。

### 2.2 执行结构

~~~text
已明确的需求
    |
主 Agent 承担 Orchestrator
    |
任务分析、风险判断和执行策略选择
    |
    +-- L1 Quick：内联执行
    +-- L2 Standard：最小 SDD，默认单 Writer
    +-- L3 Large：依赖协调，按需分析和委派
    |
共享实现原则、证据、恢复和集成规则
    |
finishing-development：缺失验证、审查和范围核对
    |
delivery-handoff：按触发规则整理交接
    |
独立测试 Agent
~~~

L1 复用共享原则和 finishing，不强制加载整份 development-workflow。L2、L3 使用 development-workflow。共享研发引擎表示共同规则和已有工具，不要求将所有代码执行封装到一个新脚本。

### 2.3 模块职责

| 模块 | 职责 |
| --- | --- |
| 主 Agent | 统一协调、持有任务上下文、执行路由调整、集成和交付 |
| task-router | 初始策略选择、风险分离、升级降级条件、按需选择能力 |
| development-workflow | L2/L3 实现、依赖协调、任务状态、证据和错误恢复 |
| writing-plans | 跨会话、延期或交接时持久化必要规格和计划 |
| parallel_worktree.py | 现有任务分支和临时并行 Worktree 隔离、导出、集成、清理 |
| finishing-development | 统一质量验证、审查、范围核对和授权内提交推送 |
| delivery-handoff | 根据事实生成完整文件或简版交接信息 |
| workflow_logger.py | 已有宿主事件采集和受限的工作流声明事件 |
| 两个分析脚本 | 日志报表与配对 Benchmark 统计 |

### 2.4 名称与行为兼容

| 兼容名称 | 执行层级 | 新语义 |
| --- | --- | --- |
| Quick | L1 | 局部、明确、无需额外设计或持续依赖协调 |
| Standard | L2 | 最小 SDD，单个主执行者可管理，包括单人跨会话 |
| Large | L3 | 多个实质任务需要持续依赖协调；可顺序执行 |

保留原有最终路由 metadata 行和 Quick、Standard、Large 字面值，不直接改成 L1/L2/L3 导致旧解析器失效。新结构化记录另加 execution_mode 和 route_policy_version。

这是有意调整行为，而非只添加别名：旧 Quick 限低风险，旧 Standard 可包含高风险单行修复，旧 Large 可由跨会话触发。本版允许高风险 L1，单纯跨会话不再自动触发 L3。同步修改 README、路由场景和相关验收，不将旧规则输出与新规则输出混用同一标注。

风险规范采用 low、medium、high；兼容读取旧 normal，并将其映射为 medium。不要为改名批量改写历史日志。

## 第三章 三层路由与开发策略

### 3.1 L1 Quick

适用于目标明确、原因或修改点已确定、影响局部，且无需新增技术方案、接口设计或持续依赖管理的任务，包括文案、样式、局部配置及已定位的小型缺陷。

流程：确认结果和影响 → 选择必要能力 → 内联实现 → 风险所需验证 → finishing → 按规则交接。

不强制 Architect、Subagent、Spec/Plan/Tasks、独立文档、Worktree 或完整测试套件。不重复既有且仍有效的检查。保留仓库的任务分支和用户修改保护规则；不强制 Worktree 不等于可以绕过分支约定。

风险高不自动升级。例如契约已经明确的一行权限修复可以是 L1，但仍需相关拒绝访问、跨主体访问测试和所需审查。若分析发现接口、数据语义或多个关联模块需要设计，再升级 L2。

### 3.2 L2 Standard

适用于普通业务功能、相关多文件修改、中等缺陷、需要局部技术方案，以及单个主 Agent 可以管理的跨会话任务。

流程：读取既有需求和代码 → 补齐最小规格 → 确定技术方案和任务 → 分片实现和验证 → 集成 → finishing → 按用户选择或仓库要求交接。

| 逻辑信息区 | 内容 |
| --- | --- |
| Spec | 目标、范围、外部行为、边界、原始验收标准和未决事项 |
| Plan | 技术方案、修改范围、接口与数据影响、风险和检查 |
| Tasks | 可执行任务、前置依赖、所有权和完成条件 |

三个信息区允许合并，已有内容引用复用，不要求三个文件。当前上下文足够的临时任务可内联维护；跨会话、延期、交接或有明确保存请求时，复用 writing-plans 的存储约定并记录必要内容。不得重复维护相同计划。

默认一个主 Agent。只有边界明确且收益具体的调查、实现或审查任务才委派。SDD 不等于 subagent-driven-development；不因使用计划或子 Agent 自动加载该更重的可选工作流。

### 3.3 L3 Large

适用于多个实质成果、独立上下文或工作流之间存在需要持续维护的依赖、所有权、契约及集成协调的任务。规模、技术栈数量和文件数均不能单独决定 L3。

流程：分析协调需要 → 必要时架构分析 → 拆分 Ticket 和依赖 → 确认契约 → 主 Agent 调度 → 顺序或并行实现 → 集成及检查 → finishing → 按用户选择或仓库要求交接。

Architect 是可选职责，可由主 Agent 承担；仅在架构、接口或数据决策有实际缺口时调用独立能力，已有有效方案只做检查与补充。Coordinator 第一版由 Orchestrator 兼任，不新建专职调度 Agent。

Frontend、Backend、DevOps、Reviewer 等是按需专业能力，不预先注册或默认同时启动。宿主不支持或策略不允许委派时可顺序执行，明确所需独立审查的缺口，不伪称已启动 Agent。

L3 不强制并行。强依赖使并行不可行，但持续协调仍有价值时保留 L3；只有协调本身不再必要时才降为 L2。

### 3.4 路由决策顺序

1. 先识别请求是否属于研发实施。解释、独立审查、纯计划请求不自动进入开发。
2. 读取明确目标、修改点、调用关系、依赖和必要契约。
3. 独立评估风险和必要验证，不用风险替代复杂度判断。
4. 能可靠内联处理且无需额外设计或依赖管理时选 L1。
5. 需要最小 SDD、单个主执行者可管理时选 L2；保存计划本身不触发 L3。
6. 需要持续依赖协调时选 L3，再独立决定是否委派和并行。
7. 有多种合理策略时选择可满足结果与约束的较轻策略，记录具体理由。

未知根因的小 Bug 不默认 L1。先作有界诊断，再根据实际范围选择策略。缺失产品意图不是升级层级的理由。

## 第四章 动态调整与任务管理

### 4.1 升级和降级条件

| 转换 | 触发条件 |
| --- | --- |
| L1 → L2 | 新发现关联模块、接口或数据契约设计，或当前内联执行已不能可靠管理 |
| L2 → L3 | 新发现需要持续调度的实质任务、上下文依赖和集成协调 |
| L3 → L2 | 依赖和所有权可以收敛到一个执行者，持续协调已无收益 |
| L2 → L1 | 事实证明任务是局部明确修改，已不需要最小 SDD 管理 |

允许按上述相邻转换连续升级或降级；同一次分析确认两个条件时分别记录转换，不为记录而重复分析。性能短暂波动、文件数变化或一次工具失败不触发路由调整。

在取得会改变任务边界的新事实、准备委派、契约变更、集成或有界失败复评时重新评估即可，不每步轮询路由。跨会话持久化是记录方式，不单独构成升级条件。

### 4.2 路由变化的原子职责

主 Agent 在下一次受影响任务调度前完成以下处理：确定新事实和原因；更新执行层级；保留有效成果与证据；识别失效消费者；调整后续任务；追加变化记录。

路由调整不重置任务 ID、已完成工作、授权范围、累计失败轮次和有效检查，不删除已有文档以伪装为更轻流程。降级不能跳过高风险门禁。

内联记录与持久化计划使用同一事实来源。必须跨会话恢复时，保存当前层级、路由历史、任务状态、契约版本、工作快照和证据引用；恢复前核对实际仓库，不仅相信旧计划。

### 4.3 状态模型

复用现有任务状态 pending、active、blocked、integrated，不新增独立状态引擎。execution_mode 表示路由，task status 表示任务进展，既有 finishing 状态表示研发检查结果，handoff status 表示测试交接可用性。

无需为原稿示例中的 workflow_state: executing 新增枚举或数据库字段。如下信息可直接存在现有计划中：

~~~yaml
task_run_id: <稳定的本次执行标识>
execution_mode: L2
route_policy_version: v2.1
tasks:
  - id: API-001
    status: active
~~~

### 4.4 L3 Ticket 最小契约

~~~yaml
id: API-001
goal: 实现订单详情 API
owner: primary
scope:
  - backend/orders/
dependencies: []
contract:
  revision: order-detail-v1
  produces:
    - GET /api/orders/{id}
  consumes: []
acceptance:
  - AC-001 返回调用者有权访问的订单详情
  - AC-002 正确处理不存在或无权访问的订单
verification:
  - 订单详情行为测试
  - 相邻接口回归检查
status: pending
evidence: []
~~~

字段可适应现有计划格式，但必须能够识别目标、归属路径、所有者、依赖、契约、验收、检查、状态和证据。示例业务行为仅说明契约形状，不是其他任务的默认产品要求。

调度前检查缺失依赖、循环依赖、路径和接口冲突。只有前置任务已集成且要求的检查通过，消费者才就绪；子 Agent 声称完成不等于 integrated。

### 4.5 契约失效与失败恢复

契约的行为、接口或数据语义变化时，标记所有直接消费者及受影响的传递消费者需复评，暂停受影响执行，更新契约 revision 和证据。保留旧成果用于定位；不把“失效”实现成自动删除或回滚代码。

区分实现错误、契约错误、架构错误和集成错误，分别由当前实现者、主协调者、必要的架构分析或相关 Ticket 局部处理。无关就绪任务可以继续。

两次修复无进展必须复评原因和任务边界；同一未解决问题跨 Agent、阶段和路由共享最多三轮 review/fix 限制，不通过新建 Ticket 或子 Agent 重置计数。达到限制后保留证据和下一步建议；额外尝试须有新证据或明确修订方案，并遵守用户预算。

## 第五章 共享开发与 Worktree 协议

### 5.1 实现和验证

现有项目先检查受影响路径、直接调用者、相邻测试和配置；必要时获取基线，区分既有失败和本次回归。业务规则、回归缺陷和高风险不变量优先通过公共行为边界建立失败测试，再实现一个可验证切片。机械修改不新增镜像实现的测试。

前后端依赖按垂直切片交付，后端契约先验证，再由依赖前端消费并检查集成结果。同一所有者和上下文的简单切片可内联交接；变更所有者、切换上下文或延期时持久化已有 handoff。

与当前任务直接相关且可验证的局部改善可以实施；大规模结构调整另行提出，不能借 V2.1 重写整个 Router、开发引擎或无关上游 Skill。

### 5.2 委派规则

向子 Agent 提供目标、验收、归属路径、输入契约、来源指针、约束和检查，不默认复制整段对话。保留现有叶子 Agent 规则和 Git 变更权限边界。

子 Agent 持有主工作区写入权时，Controller 停止写入；并行 Writer 运行时，Controller 负责协调而不同时修改归属代码。返回结果必须包含实际变更、证据、未完成项和阻断。

### 5.3 并行启动条件

继续使用 skills/development-workflow/scripts/parallel_worktree.py，最多两个并行 Writer。全部条件同时满足才启动：

1. 子任务是有实际收益的独立开发工作，边界和所有权明确。
2. 依赖已满足并经过验证。
3. 无相互接口、运行时或数据契约依赖。
4. 归属路径不重叠。
5. 预计收益大于派发、上下文和集成成本。
6. 使用相同、干净且包含前置成果的基线。
7. 不覆盖或携带用户无关未提交修改。
8. 宿主能力、工具和当前授权允许执行。

已验证但未提交的前置成果可支持主工作区内顺序执行；不得为了并行而制造 commit、stash 或放宽干净基线条件。

### 5.4 集成和恢复

保留现有 detached 临时 Worktree、冻结补丁、逐个集成和受控清理协议。子 Worker 不自行提交或推送。集成后运行必要的跨边界检查，再将 Ticket 标为 integrated。

基线移动、补丁变化、路径重叠或无法干净应用时保留现场，定位相关 Ticket；不自动 reset、clean、强制切分支或删除未登记目录。只有验证 Worker 补丁不变且已经集成，才按现有 helper 清理确切 Worktree。

不满足并行条件时继续顺序执行，不将“不能并行”当作整个开发任务必然阻断。

## 第六章 质量验证与代码证据

### 6.1 finishing 的统一职责

所有执行层级最终进入 finishing-development。实现阶段已执行的验证在 finishing 中核对并复用；只补做缺失或失效检查，不按流程图再完整运行一次验证。

收尾沿用用户已有选择和预算；尚未选择时只询问一次，推荐精简收尾，可加选补充测试、代码审查、交接文档、commit、push。等待选择时可完成最小检查，选定后才执行额外工作；宿主无法交互时按精简收尾并说明跳过项。未回复或界面预选不算授权。“完整收尾”包括补测、审查和交接文档，不包含 commit/push 授权。

精简收尾核对范围与结果、复用证据、完成仓库或明确验收要求的门禁，并在回复中简述结果和缺口。风险建议用于推荐额外检查，不自动增加收尾阶段；用户拒绝必要检查时保留 skipped/partial 和发布限制，不将缺失证据写为通过，不绕过仓库硬性规则。任务层级不自动增加测试、审查、快照包或交接文件。

| 检查 | 选择规则 |
| --- | --- |
| 修改范围和用户变更保护 | 所有任务必须核对 |
| 最小结果检查 | 所有任务必须有与行为相关的证据 |
| Type Check、Lint、Build | 执行仓库/明确验收要求，以及用户选定范围内的额外检查 |
| Unit、Integration、E2E | 必要门禁保留；额外测试按用户选择、行为边界和预算执行，不自动跑全量 |
| 普通代码审查 | 用户选择或明确要求审查时，由 Controller 核对需求和工程质量 |
| 独立代码审查 | 选定审查中的高风险不变量或明确要求时使用；受宿主能力和授权约束 |

必要门禁缺失或失败不能描述为全部验证通过。无法独立审查时如实标记自审和缺口；保留现有阻断提交或推送的规则。非阻断偏好不触发无止境修复。

### 6.2 可定位未提交成果的证据契约

证据必须记录检查、命令或人工检查方法、结果、适用范围、实际被检查的代码快照、依赖或配置条件，以及证据来源。不得只记录 HEAD 就声称覆盖未提交修改。

~~~yaml
check: order-unit-test
command: npm test -- orders
status: passed
scope:
  - orders module
code_ref:
  kind: working_snapshot
  base_commit: <任务开始时的提交>
  head_commit: <检查时的当前提交>
  snapshot_ref: <现有冻结包或任务所属文件清单的可访问位置>
  snapshot_sha256: <实际计算的内容标识>
inputs:
  dependencies_ref: <相关锁文件或版本信息>
  configuration_ref: <不含秘密的相关配置标识>
evidence_ref: <检查输出或已有证据引用>
~~~

已提交且工作区中没有影响本次检查的修改时，code_ref 可使用 kind: commit 和实际 commit。非 Git 场景可用现有文件快照，Git 字段写 not_applicable。

未提交场景覆盖任务所属 committed、staged、unstaged、untracked 文件，以及删除、重命名和必要二进制变化。记录任务开始时已有修改，避免把用户无关成果计入交付。无法可靠归属时披露 Unknown，并停止依赖精确归属的打包、提交或交接步骤。

复用现有 review_package.py、已冻结补丁和内容哈希能力。简单本地检查可直接绑定被检查文件的内容指纹与范围；需要下游获取代码时，必须提供真实可获取的代码成果，而不只有哈希。不新增快照管理引擎，不要求每个低风险任务生成完整包。

快照必须明确覆盖范围。生成的 handoff、日志和证据文件不自动纳入被验证的代码快照，避免文档记录自身摘要形成循环；它们若本身是本次交付内容，单独记录文档版本或成果清单。交接生成后若代码再次变化，重新核对受影响证据并更新交接引用。

### 6.3 证据有效性

相关代码、消费契约、依赖、配置或必要环境条件变化后，重新评估并执行受影响检查。未受影响的有效检查继续复用。哈希不同不意味着所有测试都重跑，HEAD 相同也不意味着证据仍有效。

验证状态采用 passed、failed、not_run、skipped、unavailable。not_run 表示没有执行；skipped 必须有原因；unavailable 表示所需能力或环境不可用。不得把三者折算成 passed。

review/fix 之后按修复差异和新影响范围复查，累计轮次遵守第四章。既有基线失败单独记录，不隐去失败，也不自动认定本次变更有回归。

### 6.4 提交和推送

继续复用既有授权，包括收尾时明确选定的 commit/push。未选定或请求时标为 skipped，不再单独追问提交授权，不为了获得 Final Commit 而提交。

获得提交授权后只暂存任务所属且已核对的内容，遵守仓库版本规则。推送需要相应授权、明确目标和已有任务提交；push-only 不等于授权创建 commit。两者都不授权合并、发布、部署或删除分支。

## 第七章 Test Handoff 交接契约

### 7.1 生成触发条件

| 场景 | 必须交付的形式 |
| --- | --- |
| 任意层级选定交接文档、明确要求交给测试 Agent，或仓库要求完整交接 | 独立 Test-Handoff-<task-id>.md，阻断结果如实标为 blocked |
| 其他 L1/L2/L3 | 最终回复中的简版交接信息 |

简版包含结果、实际修改与影响、已执行验证、缺口和代码可获取性；不强制创建文件。风险用于推荐检查，明确的必要门禁仍适用；风险本身不自动增加文件要求。选定或要求维护已有交接时更新同一任务文档，不每次回复新建一份。

保留已有交接文件；本次范围包括维护该交接时更新，路由变化本身不触发文档维护。中途阻断且选定或要求交接时生成文档，必须标为 blocked，不算研发完成。

独立文件优先采用目标仓库公开交付文档约定；没有约定时使用 docs/test-handoffs/Test-Handoff-<safe-task-id>.md。路径中的 ID 需规范化，文档内保留原上游 ID。核对路径不被忽略，避免覆盖同名其他任务。只有用户明确要求本地私有产物时才使用已忽略目录，并说明其不会进入仓库。

用户手动上传文档中心；本版不自动上传、发送消息或建立外部集成。

### 7.2 内容和职责分工

finishing 整理真实变更、风险、验收映射、验证和授权结果；delivery-handoff 接收这些信息，核对引用后生成文档。delivery-handoff 不重复运行实现、测试或审查，不将生成文档当成质量门禁已通过。

直接调用 delivery-handoff 时，读取已有需求、真实代码差异和证据。缺失项目用 Unknown、not_run 或 unavailable 表达；不得编造不存在的执行记录。

修改范围描述实际改变的文件和代码；影响范围描述可能受影响的模块与行为。间接影响必须有调用关系、共享契约或配置等依据，不能确认时写 Unknown。无变化写 None，不能将 Unknown 写成 None。

### 7.3 状态及阻断规则

| Development Status | 条件 |
| --- | --- |
| ready_for_testing | 范围内实现完成，必要研发门禁通过，无阻断问题，目标测试执行方能够取得正确代码和所需测试入口 |
| ready_with_issues | 范围内实现完成且可测试，但存在已披露、经判断不阻断的已知问题或验证缺口 |
| blocked | 必要实现缺失、关键门禁失败或缺失、必要环境不可用，或目标执行方无法取得本次代码，导致不能正常进入约定测试 |

状态是研发交接状态，不是独立测试结论。交接因代码未传递而 blocked 时，Implementation 仍可以是 complete；反之，生成交接文档不能把 Implementation=blocked 改成 complete。

关键门禁包括任务明确要求不可豁免的检查，以及未通过会使交付不安全或不可用的检查。不得自动将关键失败归入 ready_with_issues。非关键缺口需要说明影响、为何仍可测试、下一步与责任方；若需要接受风险，由现有授权规则处理，不因本方案自动获得豁免。

有明确授权接受的可豁免缺口仍保留失败或未验证事实，最高标为 ready_with_issues；不能将其视为 Benchmark 原始质量 rubric 已通过。产品必要范围未完成仍为 blocked，除非上游明确修改了任务范围并同步记录。

### 7.4 代码可获取性

使用 Code Availability 单独描述交接成果：

| 值 | 含义 |
| --- | --- |
| available | 目标测试执行方可访问精确 commit、同一工作快照或已移交的可应用包 |
| local_only | 成果只在研发者本地，尚未确认目标执行方可访问 |
| unavailable | 已知无法取得必要代码成果 |
| unknown | 尚未核实 |

仓库地址和分支名不足以证明代码已交付。未推送 commit、工作区 dirty、私有本地路径都不能自动标 available。测试 Agent 在同一工作区执行并确认快照匹配时，可使用本地快照作为 available 的依据。

提交状态与代码可获取性独立。不强制 commit/push，可通过用户授权的现有包或共享工作区交接。local_only、unavailable、unknown 且阻碍约定测试时，Development Status=blocked，明确解除条件。

### 7.5 完整 Markdown 模板

以下是字段模板，尖括号是待填占位符，最终交接文件不得残留未解释的占位符。选项字段只填实际值，不把多个候选值原样留在结果里。

~~~~markdown
# Test Handoff

## 1. Task Information

- Contract Version: 1
- Task ID: <原始需求 ID 或本地 ID>
- Task Name: <名称>
- Upstream Reference: <需求链接、文件及版本或对话来源>
- Task Run ID: <本次执行标识>
- Execution Mode: <L1 / L2 / L3>
- Development Status: <ready_for_testing / ready_with_issues / blocked>
- Summary: <交付行为与范围>

## 2. Code Changes

### Added Files
- <实际新增文件或 None>

### Modified Files
- <实际修改文件或 None>

### Deleted Files
- <实际删除文件或 None>

### Renamed Files
- <原路径 → 新路径或 None>

### Changed Modules
- <实际改变的模块>

### Change Description
- <与本次需求关联的变化>

### Attribution
- <基线和用户既有修改的排除方式；无法确认处写 Unknown>

## 3. Impact Analysis

### Directly Affected Modules
- <直接影响与依据>

### Indirectly Affected Modules
- <间接影响与依据；未知写 Unknown>

### API Changes
- <接口及兼容影响；无变化写 None>

### Database and Schema Changes
- <迁移、数据和回滚影响；无变化写 None>

### Configuration Changes
- <配置名称和影响，不包含秘密值；无变化写 None>

### Compatibility Risks
- <兼容风险或 None / Unknown>

## 4. Acceptance Criteria Mapping

| Criterion ID | Source | Implementation | Development Status | Evidence or Gap |
| --- | --- | --- | --- | --- |
| <AC-ID> | <原始来源> | <实现位置> | <implemented / partial / not_implemented / unknown> | <研发证据或缺口> |

## 5. Test Guidance

### Recommended Test Scenarios
- <正常、异常和失败流程建议>

### Regression Test Scope
- <需要关注的已有行为>

### Boundary Cases
- <边界条件>

### High Risk Areas
- <高风险不变量>

测试 Agent 可以扩展这些建议，并独立作出测试结论。

## 6. Development Verification

| Check | Status | Command or Method | Scope | Code Reference | Evidence or Reason |
| --- | --- | --- | --- | --- | --- |
| <检查名称> | <passed / failed / not_run / skipped / unavailable> | <实际命令或方法> | <范围> | <commit 或快照标识> | <证据或未执行原因> |

- Review Independence: <independent / self_review / not_run / unavailable>
- Dependency and Configuration References: <相关输入标识>
- Pre-existing Failures: <基线失败或 None / Unknown>

这里只记录研发实际检查，不代表独立自动化测试已通过。

## 7. Environment and Dependencies

### Startup Instructions
- <已验证的入口和步骤；未验证则标明>

### Required Services
- <服务、版本和必要环境>

### Test Data
- <准备方法或可访问引用，不包含真实敏感数据>

### Special Configuration
- <环境变量名称和安全取值来源，不包含凭据>

## 8. Git and Code Availability

- Repository: <仓库标识或 not_applicable>
- Branch: <分支或 not_applicable>
- Base Commit: <任务基线或 Unknown / not_applicable>
- Head Commit: <检查时 HEAD 或 not_applicable>
- Final Commit: <成果 commit；未提交填 not_created>
- Working Tree: <clean / dirty / not_applicable>
- Code Reference Kind: <commit / working_snapshot / file_snapshot>
- Snapshot or Package Reference: <实际位置或 not_applicable>
- Snapshot or Package SHA256: <实际摘要或 not_applicable>
- Code Availability: <available / local_only / unavailable / unknown>
- Retrieval and Verification: <目标执行方取得成果并校验标识的方法>

## 9. Known Issues and Risks

### Known Issues
- <问题、范围及是否阻断；没有则 None>

### Unresolved Risks
- <风险、证据缺口及必要决策>

### Limitations and Next Actions
- <限制、解除条件、责任方及下一步>
~~~~

### 7.6 字段和未来兼容

使用固定九个顶层信息区及 Contract Version。章节内允许增加相关说明，缺项明确标识；不得仅因标题齐全判完整。验收映射的 implemented 只代表实现情况，不表示产品验收通过。

保留原始标准 ID；必要时创建本地 AC ID 并注明为研发映射，不能伪称上游提供。环境启动步骤需区分已验证与建议。Git remote 若包含认证信息，必须使用不含凭据的仓库标识。

未来测试 Agent 可读取契约、取得代码、核对快照、分析 Diff、启动环境、准备数据、扩展测试并独立出报告。本版不同时维护独立 JSON handoff；未来可以从同一信息模型导出，避免两套事实来源。

## 第八章 日志采集与兼容

### 8.1 两种来源必须分开

现有 Hook 日志记录宿主暴露的工具、Agent 生命周期和时间；结束回复中的路由与 finishing 状态属于 Agent 声明。两种来源不能互相替代。

本版采用明确的声明事件入口：在现有 scripts/workflow_logger.py 增加可选参数 --record-workflow-event，从 stdin 读取一个受限 JSON 对象。默认无此参数时仍走现有 Hook 输入协议，不新增 Hook、后台进程、服务或运行依赖。

路由选择或变化发生时，由主 Agent 在下一次受影响调度前更新内联记录或既有计划；采集已启用且目标可用时，调用该入口记录。不能仅从最终路由推测中间变化。

没有启用日志、目录不可用、宿主不允许调用或发生中断时，继续维护必要任务上下文，披露 telemetry unavailable 或 partial。日志失败不阻断研发，也不绕过代码归属、门禁和交付要求。不得隐式启用未经允许的 Hook；独立本地测试仅使用临时日志目录。

### 8.2 声明事件契约

保留现有日志顶层 schema_version=1 和旧事件含义。新事件使用 workflow_event_schema_version=1；若实现发现必须破坏旧 envelope，暂停该部分并提出迁移方案，不静默改写旧字段。

公共字段：

| 字段 | 规则 |
| --- | --- |
| event | 本章允许的事件枚举 |
| workflow_event_schema_version | 固定为 1 |
| event_id | 生成一次并保留，重试时使用同一值 |
| task_run_id | 本次任务执行的稳定不透明标识，跨会话继续同一执行时复用 |
| sequence | 同一 task_run_id 下递增的正整数，关联不同类型声明事件 |
| source | 新入口固定为 agent_declared，由 logger 设置，不接受冒充宿主来源 |
| timestamp | logger 写入的 UTC 接收时间；不等同原始事件发生时间 |
| route_policy_version | 新路由策略固定为 v2.1 |

任务恢复所需 task_run_id、sequence 和已声明事件 ID 保存在既有计划或检查点，不建设新状态系统。恢复时不能确定是否已写入则保留原 event_id 重放，统计端去重。无法还原中断前事实时标记缺失，不补造事件。

| 新事件 | 必需业务字段 | 含义 |
| --- | --- | --- |
| route_selected | execution_mode、route、risk、reason_code、planned_skills | 一次执行的初始选择 |
| route_changed | from、to、reason_code | 真实策略变更；from 和 to 不得相同 |
| verification_summary | 使用既有 finishing 状态枚举的摘要 | Agent 声明的研发检查结论 |
| handoff_generated | form、development_status、code_availability | 声明生成 file 或 inline 交接，不等于独立验证内容正确 |
| workflow_completed | implementation、development_status | 本次执行结束，允许 implementation=blocked，不表示成功 |

route 字段继续使用旧规范化值 quick、standard、large；execution_mode 使用 L1、L2、L3，必须严格匹配。risk 输出 low、medium、high，旧 normal 只在读取兼容层归一化。

reason_code 采用有限枚举：local_scope、bounded_sdd、design_required、contract_changed、coordination_required、coordination_unnecessary、scope_simplified。用于初选或转换的有效组合需验证；原因细节留在当前对话或计划，不将任意自由文本写入日志。

~~~json
{
  "event": "route_changed",
  "workflow_event_schema_version": 1,
  "event_id": "77777777-7777-4777-8777-777777777777",
  "task_run_id": "11111111-1111-4111-8111-111111111111",
  "sequence": 2,
  "route_policy_version": "v2.1",
  "from": "L2",
  "to": "L3",
  "reason_code": "coordination_required"
}
~~~

示例只表示输入结构，实际执行使用真实新标识，不复用示例 UUID。source、timestamp 和旧 envelope 字段由 logger 补充。

### 8.3 输入限制和观测边界

新入口每次只接受一个不超过 16 KiB 的 JSON 对象，按事件允许字段、类型、枚举、标识格式及长度校验。拒绝未知字段、自由文本 reason、完整 prompt、源代码、命令输出、补丁、环境变量值和凭据，不把被拒绝的 payload 写入日志。planned_skills 只记录规范化 Skill 标识和选择意图，不记录正文。

旧 Hook 输入处理保持原有防泄漏行为。已有日志保留周期和锁机制复用，禁止新建无界事件缓存。

Agent 派发使用已有实际 SubagentStart/Stop 等宿主事件统计。任务关联不可靠时只能作为会话级观测，不强行分配给某个 task_run_id。未观察到 start 不能认定实际启动了 Agent。

本版不新增宣称实际 Skill 加载的 selected_skills 事件。实际并行、实际 Agent 数和 token 都只能根据可靠宿主数据认定；工具无法覆盖的部分保持 unknown，不把计划当观测。需要展示声明信息时明确标 agent_declared。

### 8.4 日志分析器兼容

同步扩展 scripts/analyze_workflow_logs.py：

1. 保留旧 routing_decision、workflow_status、工具和轮次报表。
2. 新增独立 workflow_decisions 报表，统计初始路由、最终路由、升级、降级和声明交付状态。
3. 新旧统计保持分区，不把旧最终声明与新 route_selected 相加为两次任务。
4. 按 event_id 去重；比对规范化的业务字段，排除 logger 在每次接收时生成的 timestamp 等 envelope 字段，避免合法重放被当作冲突。相同 ID 的业务内容冲突、同 task_run_id 同 sequence 冲突、缺失序列和不连续转换报告为数据问题。
5. 转换必须衔接当前已知层级；缺失初选或中途事件时可展示观察到的事件，但完整任务转换统计标为 partial。
6. 旧记录没有 task_run_id 或路由策略版本时保持 legacy，不自动映射到本次执行。
7. 工具调用时长不等于整个任务耗时，轮次结束不等于任务完成，缺失日志不等于零活动。

如果一轮内发生多次调整，必须能从新事件序列恢复全部已成功记录的转换；最终 metadata 行只作为旧兼容输出，不承担事件历史职责。

## 第九章 Benchmark 定义与验收边界

### 9.1 沿用现有配对体系

继续使用 docs/workflow-benchmark.md 和 scripts/analyze_workflow_benchmark.py。baseline 与 candidate 使用同一任务、验收 rubric、初始快照、精确模型与推理设置、宿主工具权限和运行环境，采用独立工作区和新上下文，不泄漏另一版本解法。

记录插件版本和 route_policy_version，不将方案版本当插件版本。新增字段向后兼容；现有质量判定和旧配对条件不能被削弱。原有输出键含义保留，新指标放入清晰的新增结构；确需破坏消费者时必须显式版本迁移。

插件版本和路由策略版本是被比较的 variant 属性，允许 baseline 与 candidate 不同；任务、初始快照、质量 rubric、模型和环境等控制条件仍需匹配。旧记录缺版本时保持 Unknown，不猜测归属。

保留失败、中断、返工和必要人工决策，不只选择成功运行。token 必须来自覆盖主 Agent、子 Agent 和重试的可靠宿主计量，缺失为 null，不用文本长度或单个工具调用估算。

### 9.2 路由标注规则

执行前由固定评估 rubric 为每个可观察决策点定义 allowed_routes、必要行为、风险门禁和禁止行为。允许多个合理层级，不由实施 Agent 看完结果后修改答案。

动态场景按预先设计的顺序揭示新信息；初始判断只依据当时可见信息评分，不能要求 Agent 提前知道后续事实。只有任务根本要求变化时可修订 rubric，同时产生新场景版本，不能用于美化已有结果。

旧版本依据旧策略解释，候选版本依据 v2.1 解释。跨版本可比的主要结论是质量、成本与行为约束；不能仅因“高风险修复从 Standard 变成 Quick”就声称准确率提高。

### 9.3 指标口径

| 指标 | 计算和证据规则 |
| --- | --- |
| 路由准确率 | 命中该决策点 allowed_routes 的次数 / 有有效标注和实际路由的决策点数；同时报告覆盖率 |
| 过度路由率 | 实际等级高于 allowed_routes 中最高等级的次数 / 同一有效分母 |
| 不足路由率 | 实际等级低于 allowed_routes 中最低等级的次数 / 同一有效分母 |
| 其他路由不匹配 | 不在允许集合且不属于上述两类的情况单列，不强行分类 |
| 任务耗时 | 同一任务开始到执行结束的统一计量，包含返工和必要等待，保留失败与中断状态 |
| Token | 可靠宿主统计；覆盖范围不足则不可用于总成本比较 |
| 返工 | 沿用 human_rework 表示交付后纠正干预次数；另报有返工运行占比，不等于必要产品澄清次数 |
| 质量 | 固定 rubric 的验收、必要检查、回归和所需独立审查证据 |
| 动态调整次数 | 去重后有效 route_changed 中按层级方向计数；缺事件时为不完整观测 |
| Agent 协调成本 | 有证据的调度、上下文准备、等待、集成和协调返工；注明时间或 token 单位及归因来源 |
| 过度或不足路由成本 | 仅记录有阶段证据或受控对照支持的额外开销；没有证据只报发生率，成本为 unknown |
| Handoff 完整性 | 适用字段中实际填写且与事实一致的字段比例，以及所有关键字段是否通过 |

并行 Worker 的耗时和 Controller 等待可能重叠，不直接相加为 wall-clock 协调成本。区分可加的资源时间、总 elapsed time 和可靠 token。声明计数与宿主实测分别展示，不伪装成精确因果归因。

### 9.4 Handoff 完整性 rubric

完整性同时核对结构、事实和可执行性。关键项包括任务与上游关联、真实变更、影响和未知项、验收映射、验证真实性、代码快照、可获取性、阻断披露及交付状态一致性。

明确填写 None 或 not_applicable 且有依据的字段可算完成；Unknown 是诚实披露，但不能作为事实已确定。适用字段的 Unknown 计为未验证，并单列披露覆盖率。关键代码不可获取时可以有完整的 blocked 说明，但不得评为 ready_for_testing 的交接通过。

研发只需简版交接的 L1，按简版字段集合评分，不能因没有完整文件扣分。结构检查发现标题齐全但变更或状态错误时，事实检查必须失败。

### 9.5 两类验收

| 类别 | 必须证明的内容 | 可作出的结论 |
| --- | --- | --- |
| F 功能验收 | 规则、脚本、输入校验、旧格式兼容、去重、缺失值、统计和模板行为正确 | 本版功能已实现并通过指定验证 |
| Q 效果验证 | 真实等价任务的配对执行，固定质量 rubric，完整成本证据和足够重复 | 只对已测任务和证据支持范围给出成本与质量结论 |

每阶段及最终功能交付要求 F 通过。真实样本或可靠计量不足时允许报告 F 通过、Q 未评估，不捏造基线，也不宣称“质量不低于旧版”或“降低了多少 Token”。

若 Q 已执行并出现失败，保留并报告失败，不能改写为未评估。失败影响功能正确性时必须回到对应实现修复；仅成本未改善不能伪装为质量失败，也不能因成本目标删减必要检查。

采用现有质量约束：未知或失败质量不具备总体成本改善宣称资格。单个 smoke 对照不是普遍效果证明，文本长度下降不是运行 token 下降。

## 第十章 增量修改范围与阶段实施

### 10.1 真实路径和操作边界

以下路径以本次仓库审查结果为基线。实施 Agent 必须在 Phase 0 再次确认，不为匹配本文而移动目录。

| 路径 | 计划操作 | 范围 |
| --- | --- | --- |
| skills/task-router/SKILL.md | MODIFY | 新路由语义、兼容名称、动态调整、风险分离 |
| skills/development-workflow/SKILL.md | MODIFY | 最小 SDD、L3 协调、成果复用和契约失效 |
| skills/development-workflow/references/ | MODIFY 按需 | 必要契约、快照引用和恢复说明；避免复制主文 |
| skills/writing-plans/SKILL.md | KEEP 或小幅 MODIFY | 优先复用；仅在现有模板无法承载必要字段时补充 |
| skills/finishing-development/SKILL.md | MODIFY | 快照证据、交付状态和 handoff 入口 |
| skills/finishing-development/scripts/review_package.py | KEEP | 复用现有冻结能力，实际缺陷另行定位 |
| skills/delivery-handoff/SKILL.md | ADD | 独立文件和简版交接的激活、收集及生成规则 |
| skills/delivery-handoff/references/test-handoff-template.md | ADD | 保存第七章模板，主 Skill 按需读取 |
| skills/development-workflow/scripts/parallel_worktree.py | KEEP | 不重写，只有可复现实际缺陷才修复 |
| skills/task-router/references/optional-workflows.json | KEEP | 仅真实新增可选依赖时修改，不机械登记核心 Skill |
| scripts/workflow_logger.py | MODIFY | 受限声明入口、字段校验、旧 Hook 兼容 |
| scripts/analyze_workflow_logs.py | MODIFY | 新声明报表、去重、完整性和兼容 |
| scripts/analyze_workflow_benchmark.py | MODIFY | 新指标、覆盖率、政策版本、质量约束 |
| docs/task-router-test-cases.md | MODIFY | 新路由边界和动态场景 |
| docs/workflow-logging.md | MODIFY | 事件来源、启用边界、入口和限制 |
| docs/workflow-benchmark.md | MODIFY | 固定 rubric、指标定义、F/Q 验收 |
| README.md | MODIFY | 统一架构说明、新语义、交接入口和能力边界 |
| tests/ | EXTEND | 在现有测试布局中覆盖真实新行为和兼容 |
| plugin.json 及两份兼容 manifest | 按发布需要 MODIFY | 保持便携性和版本一致；遵守每次 main 提交规则 |

优先不新增 multi-agent-development。只有 Phase 0/3 证明现有结构不能清晰承载时，才提出具体理由和最小方案；不得默认把 L3 拆成第二套任务引擎。

### 10.2 Phase 0 仓库审查

只读检查实际目录、Git 基线与用户既有修改、三份 manifest、核心 Skill、writing-plans、Worktree、review package、日志与分析脚本、可选依赖、现有测试和 Benchmark。

输出简短差异表，区分已具备、需增量补充、真实冲突和环境限制；记录实施起点。核对需求来源和本文的六项关键决策已经明确，不重复访谈已确定选择。

验收：路径已核实、范围已明确、基线可追溯、必要检查入口可用或限制已披露。发现实质冲突仅暂停相关改造并说明最小替代方案，不自行大规模重构。

### 10.3 Phase 1 路由升级

修改 Router 及相关 README、路由场景和必要验证，保留旧 metadata 格式。写清 L1/L2/L3、风险 normal 到 medium 的兼容、单人跨会话 L2、L3 与并行的区别，以及动态调整不丢失成果。

验收：简单局部修改为 L1；高风险局部修复可为 L1，但保留门禁；普通功能和单人跨会话为 L2；需要持续依赖协调为 L3；不按文件数或多个技术栈自动委派。非实施请求不进入开发。

### 10.4 Phase 2 最小 SDD 与共享执行规则

增量修改 development-workflow 和必要 references，复用 writing-plans。补齐逻辑 Spec/Plan/Tasks、任务与路由分离、上下文恢复、契约版本和受影响消费者复评。

验收：L1 不被强制加载完整开发流程；L2 可内联或合并文档；跨会话保存必要信息；路由调整不丢任务、证据、失败计数和授权；有效验证不因新阶段重复执行。

### 10.5 Phase 3 L3 协调验证

优先补充现有 Large 协调规则，复用 Ticket、依赖就绪、路径所有权和 Worktree 协议。验证有依赖任务顺序执行、独立任务按条件并行、集成检查后解锁消费者、局部失败不停止无关任务。

验收：最多两个并行 Writer；Controller 不与 Writer 争用写权限；缺失或循环依赖不能调度；相同干净基线与归属路径受保护；未提交前置成果可支持顺序开发；不为并行创建未经授权的提交或 stash；不覆盖用户修改。

未发现实际 helper 缺陷时不修改 parallel_worktree.py。策略不允许真实委派时验证可执行的顺序退路，同时将未实测的委派能力明确标记，不伪造运行结果。

### 10.6 Phase 4 验证证据与交付

修改 finishing，新增 delivery-handoff 及模板，补充快照证据、生成条件、状态判定、代码可获取性和未来机器读取所需固定字段。

交接 Skill 描述必须有明确激活边界：实施结束需要测试交接、用户请求生成或更新交接材料时使用；不处理普通解释、产品 PRD 或最终测试结论。主 Skill 保持简洁，完整模板放 reference，避免每个 L1 加载模板。

验收：完整与简版触发准确；实际文件与影响分离；原始 AC 可追溯；未执行检查标记正确；dirty 工作区可定位；文件新增、删除、重命名和混合 Git 状态正确处理；代码未移交不标 ready_for_testing；关键失败不能伪装 ready_with_issues。

至少提供一个非提交工作快照的完整交接示例、一个简版 L1 示例和一个 blocked 示例。合成示例须标明演示，不充当真实测试证据。

### 10.7 Phase 5 日志与 Benchmark

实现新声明事件入口，扩展日志分析器和 Benchmark，更新相关文档与测试。保留现有 Hook 输入和旧路由行，补充新旧混合记录、去重、冲突、缺失序列和不可靠计量处理。

验收 F：一轮多次路由转换可恢复；旧日志仍可分析；新旧声明不重复计任务；未知字段和敏感 payload 不落盘；记录不能冒充宿主观测；重复或缺失数据如实报告；质量未知或失败不能取得总体成本改善资格。

验收 Q：有真实对照条件则运行配对任务，保留失败与原始证据，报告样本、测量范围及限制；否则明确 Q 未评估。不能用脚本 fixture、文档字数或生成的 JSON 宣称真实 Agent 效果。

### 10.8 每阶段的共同要求

完成后核对改动范围，执行与该阶段相关的检查，简要报告完成、未完成、证据和架构偏差。在实施已获授权且没有实质冲突时继续下一阶段，不增加例行审批。

阶段验收未满足时不得标为通过。可以先推进不依赖阻断项的工作，但不能绕过依赖关系。用户只要求某阶段时止于该阶段，不自动扩大范围。

开发过程中复用有效测试结果；阶段完成不等于必须再跑同一批测试。最终根据累计改动补足必要完整回归。

## 第十一章 验收矩阵与发布约束

### 11.1 必须覆盖的行为场景

| ID | 场景 | 验收结果 |
| --- | --- | --- |
| R01 | 明确文案修改 | L1； focused check；无强制计划、Agent 或文件 handoff |
| R02 | 契约已明确的局部权限缺陷 | 可 L1；保留相关拒绝访问与权限检查及所需审查 |
| R03 | 小型前后端功能 | L2 单 Writer；验证后端契约后完成前端；不按技术栈分 Agent |
| R04 | 单人跨会话开发 | L2 加持久化；不因跨会话自动升 L3 |
| R05 | 大型持续依赖协调 | L3；只有就绪任务能调度；顺序执行也合法 |
| R06 | 独立双任务且条件满足 | 最多两个 Writer；冻结、集成和检查可追溯 |
| R07 | 脏基线或未提交前置成果 | 不强行并行或提交；安全顺序退路或明确实际阻断 |
| R08 | L1 发现设计需要，L2 发现协调需要 | 记录相邻升级，复用已有实现和证据 |
| R09 | 协调需求消失和任务范围简化 | 可降级，不绕过风险门禁，不删除成果 |
| R10 | 契约变更 | 受影响消费者和证据复评，无关成果保留 |
| R11 | 连续修复无进展 | 两次复评、三轮共享限制，换 Agent 不重置 |
| H01 | 任意层级选定或要求完整交接 | 生成完整固定结构文档；未选定且无仓库要求时使用简版 |
| H02 | 普通 L1 | 简版交接足够，不因无完整文件判失败 |
| H03 | 同 HEAD 不同工作区内容 | 证据绑定不同快照；失效检查被识别 |
| H04 | staged、unstaged、untracked 和用户既有修改 | 归属清楚；不遗漏本次新增，不纳入无关内容 |
| H05 | 代码只在本地且下游不可访问 | local_only 与 blocked，明确解除条件，不自动 commit/push |
| H06 | 必要门禁失败或未完成范围 | blocked；不能以已生成文档或 ready_with_issues 掩盖 |
| H07 | 可测试的非阻断问题 | ready_with_issues；问题、影响、证据缺口和后续动作可见 |
| L01 | 同轮多个路由变更 | 实际成功记录的变化全部可恢复，最终路由不是唯一信息 |
| L02 | 旧日志与新声明混合 | 旧报表有效，新统计独立，无重复累计 |
| L03 | 重放、序列缺失或冲突 | 去重或报告不完整，不虚构完整事件链 |
| L04 | 非法字段和任意自由文本 | 拒绝持久化；不在错误日志中回显敏感 payload |
| B01 | 缺失 token、错误配对或质量未知 | 指标不可用或比较不合格，不当作零成本或通过 |
| B02 | 标题齐全但事实错误的 handoff | 完整性事实检查失败 |
| B03 | 未运行真实配对实验 | F/Q 状态分开，Q 未评估，不宣称质量或成本改善 |

这些场景是行为契约，不以逐字匹配 Skill 文案替代验收。脚本部分采用有实际输入输出断言的测试；Agent 路由和文档行为使用受控任务检查，并记录宿主能力和证据。未执行的行为场景如实列出，其必需项缺失时功能验收为 partial，而非通过。

对语义明确但可有多种合理执行方式的场景，遵守预先固定的 allowed_routes 和约束，不以是否使用某条工具命令作为唯一标准。

### 11.2 检查命令和文档结构

先发现可用 Python：Windows 优先可用的 python 或 py -3，其他环境可用 python3。以下以 python 举例，按实际解释器替换：

~~~text
python -m json.tool plugin.json
python -m json.tool .codex-plugin/plugin.json
python -m json.tool .claude-plugin/plugin.json
python -m unittest discover -s tests -v
~~~

保持全部 Skill 的 YAML front matter 中有 name 和明确 description，检查本地链接、模板围栏、相对资源路径和可选依赖是否存在。新 Skill 应进入现有结构审计的覆盖范围。

新增测试重点验证事件输入、兼容、证据归属、状态边界和统计，不写大量只能证明文案包含特定词句的测试。未修改现有脚本不需要为满足阶段数量而新增重复测试。

### 11.3 插件版本和发布

本方案 V2.1-R1 是设计文档版本。实施开始时读取 root plugin.json 的实际插件版本，不能直接把三份 manifest 写成 2.1.0。

每次 target branch 为 main 的提交前，依据仓库 AGENTS.md 将 patch 加 1，并同步 .codex-plugin/plugin.json 与 .claude-plugin/plugin.json。不得版本不一致或未递增就提交 main。其他分支遵守当次正常版本决策；合入 main 的提交仍按仓库要求处理。

授权提交 main 前，除 JSON 解析外执行以下等价版本检查：

~~~python
import json
from pathlib import Path

paths = [
    Path("plugin.json"),
    Path(".codex-plugin/plugin.json"),
    Path(".claude-plugin/plugin.json"),
]
versions = {json.loads(p.read_text(encoding="utf-8"))["version"] for p in paths}
assert len(versions) == 1, f"manifest versions differ: {versions}"
print(f"Plugin version: {versions.pop()}")
~~~

版本一致性检查不能代替验证本次 patch 确实比目标提交基线递增。未授权提交时不为交付而提交。保留 root manifest 的便携结构和既有宿主 metadata，不添加平台硬依赖。

### 11.4 最终交付清单

最终交付包括实际修改文件、架构及行为变化、复用能力、验证结果与未执行项、已知问题、真实 Test Handoff、明确标识的模板示例，以及 Benchmark 的 F/Q 状态。

架构必须满足：一个主协调者；三层策略与风险分离；无强制运行时入口承诺；最小 SDD；按需 Agent；最多两个 Writer；现有状态和隔离机制复用；没有后台服务、数据库或重复执行引擎。

质量必须满足：相关证据绑定实际代码和输入，契约变更使相关成果复评，失败轮次不重置，关键门禁不被交接状态绕过，独立测试结论不由研发自测代替。

成本必须满足：没有测量就不宣称改善，没有质量证据就不宣称优化成功，已有失败和缺失数据不被移除或折算成通过。

## 第十二章 可直接交给实施 Agent 的指令

以下指令用于用户明确启动实施时。仅将方案交给 Agent 进行阅读、审查或整理，不触发实施。

~~~text
你负责实施 RelayForge Development V2.1-R1。
以本完整修订方案为实施规范，不需要再合并原 V2.1 草案。

先执行 Phase 0，只读检查真实仓库、Git 状态、现有模块和验证入口。
当前用户已授权实施时，在阶段验收后继续 Phase 1 到 Phase 5；
如果只授权审查或整理方案，不修改插件代码，不开始后续阶段。

架构约束：
1. 主 Agent 承担唯一协调职责，task-router 是推荐入口，不建设强制运行时调度器。
2. 保留 Quick=L1、Standard=L2、Large=L3 的名称兼容，实施本文明确的新路由语义。
3. 高风险小任务可为 L1；风险验证不可省略。
4. 单人跨会话可以是 L2；L3 基于持续协调需要，不强制并行或多个 Agent。
5. 复用现有 development-workflow、writing-plans、任务状态、恢复和验证能力。
6. 不重写 Worktree 管理器，不扩大两个并行 Writer 上限。
7. 不默认新增 multi-agent-development，不自动启用独立的重型可选工作流。
8. 不新增后台服务、数据库、MCP、Hook 或第三方运行依赖。
9. 不改变用户未提交成果，不自动 stash、reset、clean 或为并行制造 commit。
10. 现有宿主权限、仓库要求和用户授权优先，方案不额外授权提交、推送或发布。

交接约束：
11. 任意层级选定交接文档、明确交给测试 Agent 或仓库要求完整交接时生成独立文件；其他任务使用简版交接。
12. 研发结果、研发检查、交接可用性和独立测试结论分别表达。
13. 未提交代码关联真实快照，覆盖任务所属新增、删除、重命名及混合 Git 状态。
14. 只有确认目标执行方可取得正确成果，才将 Code Availability 标为 available。
15. 必要实现、关键门禁、必要环境或代码移交阻断时使用 blocked。
16. ready_with_issues 仅用于可以正常测试的非阻断缺口，不能绕过必要门禁。

日志与评估约束：
17. 在既有 logger 增加受限声明入口，保留默认 Hook 协议和旧 metadata 解析。
18. 记录真实路由变化；声明事件与宿主观测分开，失败和缺失如实表达。
19. 同步修改日志分析器，处理新旧记录、重放去重、顺序缺失和冲突。
20. Benchmark 使用预先固定 rubric，保留旧配对与质量约束。
21. F 功能验收与 Q 效果验证分开；缺真实效果数据时不宣称质量或成本改善。

执行顺序：
Phase 0 仓库审查。
Phase 1 路由升级及兼容。
Phase 2 最小 SDD 与共享执行规则。
Phase 3 现有 L3 协调和隔离协议验证。
Phase 4 快照证据、质量门禁和 Test Handoff。
Phase 5 事件采集、日志统计和 Benchmark。

每阶段核对修改范围，执行相关验证，报告完成项、未完成项和架构偏差。
复用未失效的检查结果，不为阶段交接重跑全部测试。
阶段验收不是新授权申请；已授权且无实质冲突时继续执行。
发生真实冲突时暂停受影响改造，说明证据与最小解决方案，
不得自行大规模重构，也不要阻断无关的已授权工作。

最终交付：
- 修改文件清单及行为变化。
- 验证证据、未执行检查、未解决问题和 review 独立性。
- 本任务真实 Test Handoff，以及按要求提供的明确标识示例。
- Benchmark F/Q 状态；有真实数据时提供配对比较和测量限制。
- commit/push 是否执行；没有授权就保持未执行。

修改 metadata 或 Skill 后检查三份 JSON、Markdown/Skill 结构和相关测试。
授权提交 main 时，每次 patch 加 1，并保持三份 manifest 版本一致。
不为让清单显示通过而伪造测试、遥测、独立审查或成本数据。
~~~

### 修订决策索引

| 本次补齐项 | 权威章节 |
| --- | --- |
| Orchestrator 职责与非强制入口 | 第二章 |
| 路由行为变更与旧名称兼容 | 第二至四章 |
| Handoff 触发、状态和阻断规则 | 第七章 |
| 未提交代码、快照证据和可获取性 | 第六至七章 |
| 日志事件来源、采集入口和兼容 | 第八章 |
| Benchmark 口径及 F/Q 验收 | 第九至十一章 |




