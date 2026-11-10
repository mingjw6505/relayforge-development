// Synthetic declarations for UI review only; never read or update a real task.
const runId = '11111111-1111-4111-8111-111111111111';
const at = minute => `2026-11-10T01:${String(minute).padStart(2, '0')}:00.000Z`;
const steps = [
  {label: '确认验收范围', status: 'done'},
  {label: '编写规格说明', status: 'active'},
  {label: '检查规格完整性', status: 'pending'},
];
const phaseLabels = ['范围确认', '规格文档', '实施计划', '实现', '验证', '收尾'];
function sdd(index = 1, status = 'running') {
  return {method: 'sdd', status, source: 'agent_declared', phases: phaseLabels.map((label, position) => ({
    label, status: status === 'completed' || position < index ? 'done'
      : position === index && status === 'blocked' ? 'blocked'
        : position === index && status !== 'cancelled' ? 'active' : 'pending',
  }))};
}
const verification = {status: 'not_run', evidence: '模拟数据：当前尚未进入代码验证', source: 'agent_declared'};
const partial = {status: 'partial', passed: 18, pending: 2, evidence: '模拟数据：18 个用例通过，2 个交互场景待验', source: 'agent_declared'};
const history = [
  {revision: 1, at: at(0), status: 'running', summary: '已选择 Standard / L2', execution_mode: 'L2', method_progress: [sdd(0)], current_step: '确认验收范围', details: {current: '核对需求边界', remaining: '生成规格文档'}},
  {revision: 2, at: at(1), status: 'running', kind: 'skill_loaded', skill: 'development-workflow', execution_mode: 'L2', method_progress: [sdd(0)]},
  {revision: 3, at: at(2), status: 'running', summary: '', execution_mode: 'L2', method_progress: [sdd(0)], details: {change: '明确异常和重试场景'}},
  {revision: 4, at: at(3), status: 'running', summary: '需求范围已确认', execution_mode: 'L2', method_progress: [sdd(1)], details: {current: '开始规格说明', verification}},
  {revision: 5, at: at(4), status: 'running', summary: '规格已补充正常流程', execution_mode: 'L2', method_progress: [sdd(1)], details: {current: '补齐异常流程和验收条件'}},
  {revision: 6, at: at(5), status: 'running', summary: '验收条件已写入规格', execution_mode: 'L2', method_progress: [sdd(1)], details: {change: '覆盖失败重试和重复提交'}},
  {revision: 7, at: at(6), status: 'running', summary: '', execution_mode: 'L2', method_progress: [sdd(1)], current_step: '编写规格说明', details: {current: '正在生成规格文档', change: '已补齐正常流程、异常场景与验收条件', remaining: '核对规格后生成实施计划', verification}},
];
const base = {
  schema_version: 1, source: 'agent_declared', run_id: runId, revision: 7,
  title: '完善请求失败重试机制', status: 'running', summary: '', steps,
  execution_mode: 'L2', method_progress: [sdd(1)],
  details: history.at(-1).details,
  workflow: 'development-workflow',
  skill_loads: [{name: 'development-workflow', kind: 'workflow', source: 'mcp_skill_load', loaded_at: at(1), sha256: 'a'.repeat(64)}],
  created_at: at(0), updated_at: at(6), history,
};
const ended = steps.map(step => ({...step, status: 'done'}));
const implementationSteps = [{label: '编写失败用例', status: 'done'}, {label: '实现重试逻辑', status: 'active'}, {label: '整理代码并验证', status: 'pending'}];
const verificationSteps = [{label: '规格与实现', status: 'done'}, {label: '回归检查', status: 'active'}, {label: '收尾确认', status: 'pending'}];
const scenarios = {
  compact: {label: '紧凑卡片 · 默认示例', snapshot: {...base,
    steps: [{label: '定位问题', status: 'done'}, {label: '修复实现', status: 'active'}, {label: '回归检查', status: 'pending'}, {label: '收尾', status: 'pending'}],
    method_progress: [],
    skill_loads: [...base.skill_loads,
      {name: 'python-pro', kind: 'skill', source: 'mcp_skill_load', loaded_at: at(2), sha256: 'b'.repeat(64)},
      {name: 'systematic-debugging', kind: 'skill', source: 'mcp_skill_load', loaded_at: at(2), sha256: 'c'.repeat(64)}],
    details: {current: '正在补齐超时后的重试逻辑', change: '已定位超时后重复重试的原因', remaining: '补齐回归用例，检查超时与重复提交', verification: {status: 'not_run', evidence: '模拟数据：尚未进入回归检查，暂无验证结果', source: 'agent_declared'}},
    history: [
      {revision: 5, at: at(3), status: 'running', summary: '开始排查失败请求'},
      {revision: 6, at: at(4), status: 'running', summary: '定位到重试次数异常的原因'},
      {revision: 7, at: at(6), status: 'running', summary: '开始补齐超时后的重试逻辑'},
    ],
  }},
  running: {label: 'Standard / L2 · 生成规格', snapshot: base},
  skill_sources: {label: 'Skill · 外部与直接读取', snapshot: {...base,
    title: '核对 Skill 记录来源（模拟）',
    skill_uses: [
      {skill: 'host:imagegen', via: 'direct_read', source: 'agent_declared', recorded_at: at(5)},
      {skill: 'relayforge-product:brainstorming', via: 'skill_tool', source: 'agent_declared', recorded_at: at(5)},
      {skill: 'host:openai-docs', via: 'context', source: 'agent_declared', recorded_at: at(5)},
    ],
  }},
  quick: {label: 'Quick / L1 · 定位修复', snapshot: {...base, execution_mode: 'L1', method_progress: [], workflow: 'task-router', skill_loads: [], steps: [{label: '定位原因', status: 'active'}, {label: '修复与检查', status: 'pending'}], details: {current: '正在定位重试次数不正确的原因', remaining: '修复并运行针对性检查', verification}}},
  tdd: {label: 'Standard / L2 · SDD + TDD', snapshot: {...base, method_progress: [sdd(3), {method: 'tdd', status: 'running', source: 'agent_declared', phases: [{label: '编写失败用例', status: 'done'}, {label: '最小实现', status: 'active'}, {label: '重构', status: 'pending'}]}], details: {current: '正在实现让失败重试用例通过的最小改动', change: '规格与计划已确认，回归用例已观察到预期失败', remaining: '用例通过后整理重试逻辑', verification: {status: 'running', evidence: '模拟数据：当前 TDD 循环处于最小实现', source: 'agent_declared'}}}},
  large: {label: 'Large / L3 · 协作推进', snapshot: {...base, execution_mode: 'L3', method_progress: [sdd(3), {method: 'coordination', status: 'running', source: 'agent_declared', phases: [{label: '接口约定', status: 'done'}, {label: '后端交付', status: 'active'}, {label: '前端接入', status: 'pending'}, {label: '集成验证', status: 'pending'}]}], details: {current: '正在推进后端任务，并核对前端依赖的接口契约', change: '跨模块接口和交付依赖已明确', remaining: '后端交付后接入前端并做集成验证', verification}}},
  verifying: {label: '验证中', snapshot: {...base, method_progress: [sdd(4)], details: {current: '正在验证失败重试与重复提交场景', remaining: '检查完成后进入收尾', verification: {status: 'running', evidence: '模拟数据：回归检查进行中', source: 'agent_declared'}}}},
  waiting_user: {label: '等待用户', snapshot: {...base, status: 'waiting', method_progress: [sdd(1, 'waiting')], details: {waiting_for: 'user', reason: '规格已生成，等待你确认验收范围', change: '正常流程与异常处理已明确', remaining: '确认后生成实施计划', verification}}},
  waiting_external: {label: '等待外部结果', snapshot: {...base, status: 'waiting', method_progress: [sdd(4, 'waiting')], details: {waiting_for: 'external', reason: '等待测试环境完成部署', change: '本地实现已完成', remaining: '环境就绪后检查真实请求', verification: partial}}},
  completed: {label: '已完成', snapshot: {...base, status: 'completed', method_progress: [sdd(6, 'completed')], summary: '请求重试机制已完善', steps: ended, details: {change: '规格、实现和本次验证范围已完成', verification: {status: 'passed', passed: 20, evidence: '模拟数据：20 个检查全部通过', source: 'agent_declared'}}}},
  completed_partial: {label: '完成 · 部分验证', snapshot: {...base, status: 'completed', method_progress: [sdd(6, 'completed')], summary: '实现已完成，仍有验证边界', steps: ended, details: {current: '旧快照中的正在验证', remaining: '旧快照中的剩余项', verification: partial}}},
  blocked: {label: '受阻', snapshot: {...base, status: 'blocked', method_progress: [sdd(4, 'blocked')], steps: [steps[0], {...steps[1], status: 'blocked'}, steps[2]], details: {reason: '验收环境暂时不可用', change: '本地实现已保存', remaining: '环境恢复后重新发起验收', verification: {status: 'unavailable', evidence: '模拟数据：缺少验收环境', source: 'agent_declared'}}}},
  cancelled: {label: '已取消', snapshot: {...base, status: 'cancelled', method_progress: [sdd(1, 'cancelled')], summary: '已按你的要求停止本次任务', steps: [steps[0], {...steps[1], status: 'pending'}, steps[2]], details: {verification}}},
  disconnected: {label: '同步中断', snapshot: base, connection: 'disconnected'},
  unavailable: {label: '记录不可用', snapshot: base, connection: 'unavailable'},
  legacy: {label: '旧快照兼容', snapshot: {...base, execution_mode: undefined, method_progress: undefined, details: undefined, skill_loads: [], workflow: null, history: [{revision: 1, at: at(0), status: 'running', summary: '旧版已记录的阶段摘要'}]}},
};
// Every variant is a coherent new declaration, with its own mode/phase history.
export const previewScenarios = Object.fromEntries(Object.entries(scenarios).map(([name, scenario]) => {
  if (['legacy', 'running', 'compact'].includes(name)) return [name, scenario];
  let selectedSteps = scenario.snapshot.steps;
  if (name === 'tdd') selectedSteps = implementationSteps;
  if (name === 'large') selectedSteps = [{label: '确认接口边界', status: 'done'}, {label: '推进后端交付', status: 'active'}, {label: '接入并集成', status: 'pending'}];
  if (['verifying', 'waiting_external'].includes(name)) selectedSteps = verificationSteps;
  if (name.startsWith('completed')) selectedSteps = verificationSteps.map(step => ({...step, status: 'done'}));
  if (name === 'blocked') selectedSteps = [{label: '完成请求重试实现', status: 'done'}, {label: '验证验收环境', status: 'blocked'}, {label: '确认交付', status: 'pending'}];
  const snapshot = {...scenario.snapshot, steps: selectedSteps, revision: 8, updated_at: at(7)};
  const event = {revision: 8, at: at(7), status: snapshot.status, summary: snapshot.summary,
    execution_mode: snapshot.execution_mode, method_progress: snapshot.method_progress, details: snapshot.details,
    ...(name === 'skill_sources' ? {skill_uses: snapshot.skill_uses} : {}),
    current_step: selectedSteps.find(step => ['active', 'blocked'].includes(step.status))?.label};
  snapshot.history = [...snapshot.history, event];
  return [name, {...scenario, snapshot}];
}));
