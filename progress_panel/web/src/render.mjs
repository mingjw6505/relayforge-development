import {cardView, historyView} from './view.mjs';
import {terminal} from './poller.mjs';

const stepNames = {pending: '待处理', active: '进行中', done: '已完成', blocked: '受阻', skipped: '已跳过'};
const stepIcons = {pending: '', active: '', done: '✓', blocked: '!', skipped: '−'};
const connectionNames = {
  connecting: '正在同步进度…', synced: '', disconnected: '同步暂时中断，保留最后申报并重试。',
  paused: '已暂停刷新；任务继续进行。', unavailable: '进度记录已不可用，已停止刷新；保留最后申报。',
};
const time = value => {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? '时间未记录' : date.toLocaleTimeString([], {hour12: false});
};

/** Render the real card in either the MCP host or the isolated local preview. */
export function createPanel(root, {onPauseToggle = () => {}} = {}) {
  const document = root.ownerDocument;
  const el = name => root.querySelector(`[data-ui="${name}"]`);
  let latest = null;
  let syncState = 'connecting';
  let allHistory = false;
  let paused = false;

  function node(tag, value, className = '') {
    const result = document.createElement(tag);
    result.textContent = value;
    if (className) result.className = className;
    return result;
  }

  function renderHistory() {
    const history = latest.history ?? [];
    const opened = new Set([...el('history').querySelectorAll('details[open]')].map(item => item.dataset.revision));
    const selected = (allHistory ? history : history.slice(-3)).slice().reverse();
    el('history').replaceChildren(...selected.map(event => {
      const view = historyView(event);
      const item = document.createElement('li');
      const details = document.createElement('details');
      details.dataset.revision = String(event.revision);
      details.open = opened.has(details.dataset.revision);
      const summary = document.createElement('summary');
      const at = node('time', time(event.at));
      if (event.at) at.dateTime = event.at;
      summary.append(at, node('span', view.title));
      const body = node('div', '', 'rf-history-body');
      const lines = [
        ['当时模式', view.mode],
        ['本次使用申报', view.skillUses.join('；')],
        ['方法进度', view.methods.map(method => `${method.title}：${method.current}`).join('；')],
        ['当时动作', view.current], ['当时变更', view.change], ['当时剩余', view.remaining],
        ['等待／受阻原因', view.reason],
        ['当时验证', view.verification.map(value => value.text).join(' · ')], ['验证依据', view.evidence],
      ].filter(([, value]) => value);
      for (const [label, value] of lines) body.append(node('p', `${label}：${value}`));
      if (!lines.length) body.append(node('p', event.kind === 'skill_loaded'
        ? '加载工具已读取说明；不代表执行或成功。' : '这条历史未保存更多详情。'));
      details.append(summary, body);
      item.append(details);
      return item;
    }));
    el('history-count').textContent = `保留 ${history.length} 条`;
    el('more-history').hidden = history.length <= 3;
    el('more-history').textContent = allHistory ? '仅显示最近 3 条' : `查看全部 ${history.length} 条记录`;
    el('more-history').setAttribute('aria-expanded', String(allHistory));
  }

  function syncControls() {
    const ended = latest && terminal(latest.status);
    el('refresh').disabled = Boolean(ended || syncState === 'unavailable');
    el('refresh').textContent = ended ? '任务已结束' : syncState === 'unavailable' ? '记录不可用' : paused ? '恢复刷新' : '暂停刷新';
  }

  function renderMethods(methods) {
    el('method-section').hidden = methods.length === 0;
    el('methods').replaceChildren(...methods.map(method => {
      const track = node('div', '', 'rf-method-track');
      track.dataset.method = method.key;
      const heading = node('div', '', 'rf-method-heading');
      heading.append(node('span', method.title, 'rf-method-name'), node('span', method.current, 'rf-method-current'));
      const phases = node('ol', '', 'rf-method-phases');
      phases.setAttribute('aria-label', `${method.title}阶段`);
      phases.append(...method.phases.map(phase => {
        const item = node('li', '', `rf-method-phase rf-phase-${phase.status}`);
        item.setAttribute('aria-label', `${phase.label}：${phase.stateLabel}`);
        if (phase.status === 'active') item.setAttribute('aria-current', 'step');
        const mark = node('span', stepIcons[phase.status], 'rf-phase-mark');
        mark.setAttribute('aria-hidden', 'true');
        item.append(mark, node('span', phase.label));
        return item;
      }));
      const count = `${method.done} / ${method.total} 阶段已完成${method.skipped ? ` · ${method.skipped} 阶段已跳过` : ''}`;
      track.append(heading, phases, node('p', count, 'rf-method-count'));
      return track;
    }));
  }

  function updateFreshness(now = Date.now()) {
    const age = now - Date.parse(latest?.updated_at);
    el('stale').hidden = !(latest?.status === 'running' && syncState === 'synced' && age > 90000);
  }

  function setConnection(state) {
    syncState = state;
    paused = state === 'paused';
    el('connection').hidden = state === 'synced';
    el('connection').textContent = connectionNames[state] ?? connectionNames.disconnected;
    syncControls();
    updateFreshness();
  }

  function render(snapshot) {
    const differentTask = latest?.run_id !== snapshot.run_id;
    const previousStep = latest?.steps.findIndex(step => ['active', 'blocked'].includes(step.status));
    if (differentTask) {
      allHistory = false;
      el('records').hidden = true;
      el('details').setAttribute('aria-expanded', 'false');
      el('details-label').textContent = '查看详情';
      el('method-section').open = false;
      el('load-section').open = false;
      el('history').replaceChildren();
    }
    latest = snapshot;
    const view = cardView(snapshot);
    el('empty').hidden = true;
    el('task').hidden = false;
    root.dataset.status = snapshot.status;
    for (const key of ['title', 'status', 'current', 'remaining', 'workflow']) el(key).textContent = view[key];
    el('change').textContent = view.change || '暂无新进展申报';
    el('mode').textContent = view.mode;
    el('mode').title = view.modeDescription;
    el('skills').textContent = view.skills.length ? view.skills.map(skill => skill.name).join(' · ') : '未记录';
    el('skills').title = view.skills.map(skill => `${skill.id}：${skill.records.map(record => record.label).join('；')}`).join('\n');
    renderMethods(view.methods);
    el('current-label').textContent = view.currentLabel;
    el('attention').textContent = view.attention;
    el('attention').hidden = !view.attention;
    el('remaining-label').textContent = terminal(snapshot.status) ? '剩余' : '下一步';
    el('verification').replaceChildren(...view.verification.map(item => node('span', item.text, `rf-verification-${item.kind}`)));
    el('evidence').textContent = view.evidence;
    const scrollLeft = differentTask ? 0 : el('steps').scrollLeft;
    el('steps').replaceChildren(...snapshot.steps.map((step, index) => {
      const item = node('li', '', `rf-step-${step.status}`);
      item.dataset.connected = String(index > 0 && snapshot.steps[index - 1].status === 'done');
      item.setAttribute('aria-label', `${step.label}：${stepNames[step.status]}`);
      const icon = node('span', stepIcons[step.status], 'rf-step-icon');
      icon.setAttribute('aria-hidden', 'true');
      if (step.status === 'active') item.setAttribute('aria-current', 'step');
      item.append(icon, node('span', step.label, 'rf-step-label'));
      return item;
    }));
    el('steps').scrollLeft = scrollLeft;
    const currentIndex = snapshot.steps.findIndex(step => ['active', 'blocked'].includes(step.status));
    if (currentIndex >= 0 && (differentTask || currentIndex !== previousStep)) {
      const steps = el('steps');
      const current = steps.children[currentIndex];
      steps.scrollLeft += current.getBoundingClientRect().left - steps.getBoundingClientRect().left
        - (steps.clientWidth - current.clientWidth) / 2;
    }
    el('load-section').hidden = view.skills.length === 0;
    el('load-heading').textContent = `Skill 记录与来源 · ${view.skills.length} 项`;
    el('loads').replaceChildren(...view.skills.map(skill => {
      const item = document.createElement('li');
      item.append(node('span', skill.id, 'rf-load-name'));
      for (const record of skill.records) {
        const evidence = node('div', '', 'rf-load-evidence');
        evidence.append(node('time', time(record.at)),
          node('span', `${record.label}${record.digest ? ` · ${record.digest.slice(0, 8)}` : ''}`));
        item.append(evidence);
      }
      return item;
    }));
    el('updated').textContent = `阶段申报 ${time(snapshot.updated_at)}`;
    renderHistory();
    syncControls();
    updateFreshness();
  }

  el('details').onclick = () => {
    const open = el('details').getAttribute('aria-expanded') !== 'true';
    el('details').setAttribute('aria-expanded', String(open));
    el('details-label').textContent = open ? '收起详情' : '查看详情';
    el('records').hidden = !open;
  };
  el('more-history').onclick = () => {allHistory = !allHistory; renderHistory();};
  el('refresh').onclick = onPauseToggle;
  return {render, setConnection, updateFreshness};
}
