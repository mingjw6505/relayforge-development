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
