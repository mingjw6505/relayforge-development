import {App} from '@modelcontextprotocol/ext-apps';
import {PanelPoller, terminal} from './poller.mjs';

const app = new App({name: 'RelayForge Development Progress', version: __PLUGIN_VERSION__},
  {availableDisplayModes: ['fullscreen']});
const el = id => document.getElementById(id);
const statusNames = {running: '进行中', waiting: '等待输入', completed: '已完成', blocked: '受阻结束', cancelled: '已取消'};
const stepNames = {pending: '待处理', active: '当前', done: '完成', blocked: '受阻', skipped: '跳过'};
let latest = null;

function time(value) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? '—' : date.toLocaleTimeString([], {hour12: false});
}

function refreshClock() {
  if (!latest) return;
  const end = terminal(latest.status) ? Date.parse(latest.updated_at) : Date.now();
  const seconds = Math.max(0, Math.floor((end - Date.parse(latest.created_at)) / 1000));
  el('elapsed').textContent = Number.isFinite(seconds)
    ? `${Math.floor(seconds / 60).toString().padStart(2, '0')}:${(seconds % 60).toString().padStart(2, '0')}` : '—';
  const stale = !terminal(latest.status) && Date.now() - Date.parse(latest.updated_at) > 90000;
  el('stale').hidden = !stale;
}

function render(snapshot) {
  latest = snapshot;
  document.body.dataset.status = snapshot.status;
  el('empty').hidden = true;
  el('task').hidden = false;
  el('title').textContent = snapshot.title;
  el('status').textContent = statusNames[snapshot.status];
  el('summary').textContent = snapshot.summary || '等待下一次阶段更新';
  el('updated').textContent = time(snapshot.updated_at);
  const done = snapshot.steps.filter(step => step.status === 'done').length;
  const skipped = snapshot.steps.filter(step => step.status === 'skipped').length;
  el('count').textContent = `${done} / ${snapshot.steps.length}`;
  el('count-label').textContent = `步骤已完成${skipped ? ` · ${skipped} 项跳过` : ''}`;
  el('steps').replaceChildren(...snapshot.steps.map((step, index) => {
    const item = document.createElement('li');
    item.dataset.state = step.status;
    const marker = document.createElement('span');
    marker.className = 'marker';
    marker.textContent = step.status === 'done' ? '✓' : step.status === 'blocked' ? '!' : String(index + 1).padStart(2, '0');
    const name = document.createElement('span');
    name.className = 'step-label';
    name.textContent = step.label;
    const state = document.createElement('span');
    state.className = 'step-state';
    state.textContent = stepNames[step.status];
    item.append(marker, name, state);
    return item;
  }));
  const history = (snapshot.history || []).filter(event => event.summary).slice(-6).reverse();
  el('history').replaceChildren(...history.map(event => {
    const row = document.createElement('li');
    const at = document.createElement('time');
    at.textContent = time(event.at);
    const summary = document.createElement('span');
    summary.textContent = event.summary;
    row.append(at, summary);
    return row;
  }));
  el('refresh').disabled = terminal(snapshot.status);
  el('refresh').textContent = terminal(snapshot.status) ? '任务已结束' : poller.paused ? '恢复刷新' : '暂停刷新';
  refreshClock();
}

function connection(state) {
  el('connection').dataset.state = state;
  el('connection').textContent = {connecting: '正在连接', synced: '同步正常', disconnected: '连接中断 · 正在重试', paused: '已暂停刷新'}[state];
  el('connection-note').textContent = state === 'disconnected'
    ? '保留最后一次收到的状态；连接恢复前不推断任务进展。'
    : '阶段由 Agent 更新，面板自动同步。';
}

const poller = new PanelPoller({callTool: args => app.callServerTool(args, {timeout: 10000}),
  onSnapshot: render, onState: connection});

function theme(context) {
  document.documentElement.dataset.theme = context?.theme === 'dark' ? 'dark' : 'light';
}

app.ontoolresult = result => {
  if (poller.bind(result.structuredContent, {replace: true})) connection(poller.paused ? 'paused' : 'synced');
};
app.onhostcontextchanged = context => theme(context);
let clock;
app.onteardown = async () => {poller.close(); clearInterval(clock); return {};};
el('refresh').onclick = () => {
  if (poller.paused) {poller.resume(); el('refresh').textContent = '暂停刷新';}
  else {poller.pause(); el('refresh').textContent = '恢复刷新';}
};

connection('connecting');
try {
  await app.connect();
  theme(app.getHostContext());
  poller.connected();
  clock = setInterval(refreshClock, 1000);
} catch {
  connection('disconnected');
  el('empty').textContent = '面板未连接。请从本任务重新打开开发进度；开发工作可继续进行。';
}
