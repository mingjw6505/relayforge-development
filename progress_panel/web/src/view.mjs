export const statusNames = {
  running: '进行中', waiting: '等待中', completed: '已完成', blocked: '受阻', cancelled: '已取消',
};
const verificationNames = {
  not_run: '未执行', running: '验证中', passed: '检查通过', failed: '检查失败',
  partial: '部分验证', skipped: '已跳过', unavailable: '结果不可用',
};
const modeNames = {L1: 'Quick / L1', L2: 'Standard / L2', L3: 'Large / L3'};
const modeDescriptions = {L1: '快速开发', L2: '标准开发', L3: '大型任务'};
const methodNames = {sdd: 'SDD · 规格驱动', tdd: 'TDD · 测试驱动', coordination: '协作与依赖协调'};
const phaseNames = {pending: '待处理', active: '进行中', done: '已完成', blocked: '受阻', skipped: '已跳过'};

/** Selected mode and method phases come from declarations, never skill receipts. */
function executionView(snapshot) {
  const mode = Object.hasOwn(modeNames, snapshot.execution_mode) ? modeNames[snapshot.execution_mode] : '未申报';
  const declared = Array.isArray(snapshot.method_progress) ? snapshot.method_progress : [];
  const methods = declared.filter(item => item?.source === 'agent_declared'
    && Object.hasOwn(methodNames, item.method) && Object.hasOwn(statusNames, item.status)
    && Array.isArray(item.phases) && item.phases.length > 0 && item.phases.length <= 8
    && item.phases.every(phase => typeof phase?.label === 'string' && Object.hasOwn(phaseNames, phase.status)))
    .map(item => {
      const phase = item.phases.find(value => ['active', 'blocked'].includes(value.status));
      const ended = ['completed', 'blocked', 'cancelled'].includes(item.status);
      return {
        key: item.method, title: methodNames[item.method], status: item.status,
        current: ended ? (item.status === 'blocked' && phase ? `${phase.label} · 受阻` : statusNames[item.status])
          : phase ? `${phase.label} · ${phaseNames[phase.status]}` : statusNames[item.status],
        done: item.phases.filter(value => value.status === 'done').length,
        skipped: item.phases.filter(value => value.status === 'skipped').length,
        total: item.phases.length,
        phases: item.phases.map(value => ({...value, stateLabel: phaseNames[value.status]})),
      };
    });
  return {mode, modeDescription: mode === '未申报' ? '' : modeDescriptions[snapshot.execution_mode], methods};
}

function verificationView(value) {
  const verification = value?.source === 'agent_declared' ? value : null;
  const counts = [];
  if (verification?.evidence) {
    for (const [key, label] of [['passed', '项通过'], ['failed', '项失败'], ['pending', '项待验']]) {
      if (Number.isSafeInteger(verification[key]) && verification[key] >= 0) {
        counts.push({kind: key, text: `${verification[key]} ${label}`});
      }
    }
  }
  if (counts.length && verification.status !== 'passed') {
    counts.unshift({kind: verification.status, text: verificationNames[verification.status]});
  }
  return {
    items: counts.length ? counts : [{kind: verification?.status ?? 'not_run', text: verificationNames[verification?.status] ?? '未执行'}],
    evidence: verification?.evidence ?? '',
  };
}

/** Present a milestone using only declarations actually stored at that revision. */
export function historyView(event) {
  const execution = executionView(event);
  const context = {mode: execution.mode === '未申报' ? '' : execution.mode, methods: execution.methods};
  if (event.kind === 'skill_loaded') {
    return {...context, title: `已加载 ${event.skill}`, current: '', change: '', remaining: '', reason: '', verification: [], evidence: ''};
  }
  const info = event.details ?? {};
  const verification = info.verification ? verificationView(info.verification) : null;
  return {
    ...context,
    title: event.summary || info.change || info.reason || info.current || event.current_step || statusNames[event.status] || '已记录状态',
    current: info.current || event.current_step || '',
    change: info.change || '',
    remaining: info.remaining || '',
    reason: info.reason || '',
    verification: verification?.items ?? [],
    evidence: verification?.evidence ?? '',
  };
}

/** Resolve display state for both current and legacy snapshots. */
export function cardView(snapshot) {
  const info = snapshot.details ?? {};
  const receipts = (snapshot.skill_loads ?? []).filter(item => item.source === 'mcp_skill_load'
    && typeof item.name === 'string' && /^[a-f0-9]{64}$/.test(item.sha256));
  const workflow = receipts.some(item => item.kind === 'workflow' && item.name === snapshot.workflow)
    ? snapshot.workflow : '未记录';
  const verification = verificationView(info.verification);
  const currentStep = snapshot.steps.find(step => ['active', 'blocked'].includes(step.status));
  const remainingSteps = snapshot.steps.filter(step => ['pending', 'blocked'].includes(step.status)).map(step => step.label);
  let currentLabel = '当前';
  let current = info.current || currentStep?.label || '等待阶段申报';
  let remaining = info.remaining || (remainingSteps.length
    ? remainingSteps.slice(0, 3).join('、') + (remainingSteps.length > 3 ? '…' : '') : '等待下一阶段申报');
  let status = statusNames[snapshot.status];
  if (snapshot.status === 'completed') {
    currentLabel = '结果';
    current = snapshot.summary || info.change || '本次任务已结束';
    remaining = '无（本次范围）';
  } else if (snapshot.status === 'cancelled') {
    currentLabel = '结果';
    current = snapshot.summary || '本次任务已取消';
    remaining = '已停止（本次尝试）';
  } else if (snapshot.status === 'blocked') {
    currentLabel = '受阻';
    current = info.reason || currentStep?.label || snapshot.summary || '受阻原因未申报';
    remaining = info.remaining || '下一步未申报';
  } else if (snapshot.status === 'waiting') {
    currentLabel = '等待';
    status = {user: '等待你确认', external: '等待外部结果'}[info.waiting_for] || '等待中';
    current = info.reason || info.current || currentStep?.label || '等待原因未申报';
    remaining = info.remaining || '下一步未申报';
  } else if (info.verification?.status === 'running' && info.verification.source === 'agent_declared') {
    status = '验证中';
  }
  const change = info.change || snapshot.summary || '';
  const verificationState = info.verification?.source === 'agent_declared' ? info.verification.status : 'not_run';
  const attention = ['failed', 'partial', 'unavailable'].includes(verificationState)
    || (snapshot.status === 'completed' && verificationState !== 'passed')
    ? `验证：${verification.items.map(item => item.text).join(' · ')}` : '';
  return {
    ...executionView(snapshot),
    title: snapshot.title, status, currentLabel, current,
    attention,
    change: change === current ? '' : change,
    remaining, workflow, receipts, skills: receipts.filter(item => item.kind === 'skill'),
    verification: verification.items,
    evidence: verification.evidence || (verificationState === 'not_run' ? '尚未申报验证结果。' : '未提供验证依据'),
  };
}
