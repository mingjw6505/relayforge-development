// Synthetic declarations for UI review only; never read or update a real task.
const runId = '11111111-1111-4111-8111-111111111111';
const at = minute => `2026-11-09T06:${String(minute).padStart(2, '0')}:00.000Z`;
const steps = [
  {label: '明确方案', status: 'done'},
  {label: '实现与验证', status: 'active'},
  {label: '检查展示效果', status: 'pending'},
];
const verification = {status: 'partial', passed: 18, pending: 2, evidence: '模拟数据：18 个用例通过，2 个交互场景待验', source: 'agent_declared'};
const history = [
  {revision: 1, at: at(0), status: 'running', summary: '已明确优化范围', current_step: '明确方案', details: {current: '核对状态与交互边界', remaining: '实现并验证'}},
  {revision: 2, at: at(1), status: 'running', kind: 'skill_loaded', skill: 'development-workflow'},
  {revision: 3, at: at(2), status: 'running', summary: '', current_step: '实现与验证', details: {current: '调整等待状态', change: '区分用户确认与外部等待', remaining: '完成态与记录回看'}},
  {revision: 4, at: at(3), status: 'running', summary: '完成后不再显示旧动作', current_step: '实现与验证', details: {change: '终态保留独立验证结论', verification: {status: 'not_run', source: 'agent_declared', evidence: ''}}},
  {revision: 5, at: at(4), status: 'running', summary: '', current_step: '实现与验证', details: {change: '阶段记录可查看当时动作和验证依据', current: '检查历史兼容性', verification: {status: 'passed', passed: 12, evidence: '模拟数据：12 个状态用例通过', source: 'agent_declared'}}},
  {revision: 6, at: at(5), status: 'running', summary: '相同版本只同步、不重绘', current_step: '实现与验证', details: {change: '保留已展开的阶段记录'}},
  {revision: 7, at: at(6), status: 'running', summary: '', current_step: '实现与验证', details: {current: '核对等待与完成状态', change: '卡片开始显示明确的下一步', remaining: '检查窄屏展示', verification}},
];
const base = {
  schema_version: 1, source: 'agent_declared', run_id: runId, revision: 7,
  title: '优化对话内开发进度', status: 'running', summary: '', steps,
  details: {current: '核对等待与完成状态', change: '阶段记录已支持回看当时的动作与验证', remaining: '检查窄屏展示与交互反馈', verification},
  workflow: 'development-workflow',
  skill_loads: [
    {name: 'development-workflow', kind: 'workflow', source: 'mcp_skill_load', loaded_at: at(1), sha256: 'a'.repeat(64)},
    {name: 'frontend-design', kind: 'skill', source: 'mcp_skill_load', loaded_at: at(2), sha256: 'b'.repeat(64)},
  ],
  created_at: at(0), updated_at: at(6), history,
};
const ended = steps.map(step => ({...step, status: 'done'}));
export const previewScenarios = {
  running: {label: '进行中', snapshot: base},
  verifying: {label: '验证中', snapshot: {...base, details: {...base.details, current: '检查刷新与断连恢复', verification: {status: 'running', evidence: '模拟数据：交互检查进行中', source: 'agent_declared'}}}},
  waiting_user: {label: '等待用户', snapshot: {...base, status: 'waiting', details: {waiting_for: 'user', reason: '等待你确认卡片展示是否符合预期', change: '实现和本地验证已完成', remaining: '确认后继续处理反馈', verification}}},
  waiting_external: {label: '等待外部结果', snapshot: {...base, status: 'waiting', details: {waiting_for: 'external', reason: '等待测试环境完成部署', change: '本地状态用例已通过', remaining: '环境就绪后检查真实展示', verification}}},
  completed: {label: '已完成', snapshot: {...base, status: 'completed', summary: '进度卡片优化已完成', steps: ended, details: {change: '阶段历史、等待状态和刷新机制已优化', verification: {status: 'passed', passed: 20, evidence: '模拟数据：20 个检查全部通过', source: 'agent_declared'}}}},
  completed_partial: {label: '完成 · 部分验证', snapshot: {...base, status: 'completed', summary: '实现已完成，仍有验证边界', steps: ended, details: {current: '旧快照中的正在验证', remaining: '旧快照中的剩余项', verification}}},
  blocked: {label: '受阻', snapshot: {...base, status: 'blocked', steps: [steps[0], {...steps[1], status: 'blocked'}, steps[2]], details: {reason: '验收环境暂时不可用', change: '本地实现已保存', remaining: '环境恢复后重新发起验收', verification: {status: 'unavailable', evidence: '模拟数据：缺少验收环境', source: 'agent_declared'}}}},
  cancelled: {label: '已取消', snapshot: {...base, status: 'cancelled', summary: '已按你的要求停止本次任务', steps: [steps[0], {...steps[1], status: 'pending'}, steps[2]], details: {verification}}},
  disconnected: {label: '同步中断', snapshot: base, connection: 'disconnected'},
  unavailable: {label: '记录不可用', snapshot: base, connection: 'unavailable'},
  legacy: {label: '旧快照兼容', snapshot: {...base, details: undefined, skill_loads: [], workflow: null, history: [{revision: 1, at: at(0), status: 'running', summary: '旧版已记录的阶段摘要'}]}},
};
