/** RelayForge observation console. No execution controls, persistence, or inferred stages. */
const MAX_TEXT = 240;
const RESPONSE_LIMIT = 8 * 1024 * 1024;
const TOOL_STATES = {
  start_observed: ['已观察到开始', 'signal'],
  completion_succeeded: ['工具返回成功', 'neutral'],
  completion_failed: ['工具返回失败', 'failure'],
  completion_unspecified: ['已结束 · 成功结论未知', 'muted'],
  incomplete: ['记录不完整', 'signal'],
  conflicted: ['记录存在冲突', 'failure'],
};
const QUALITY = {
  intact_open: ['现存声明序列完整 · 未结束', 'neutral'],
  intact_ended: ['现存声明序列完整 · 已结束', 'neutral'],
  partial: ['历史部分缺失', 'signal'],
  conflicted: ['声明存在冲突', 'failure'],
};
const SOURCE_STATES = { readable: '日志可读', missing: '来源缺失', denied: '读取被拒绝', degraded: '数据质量降级' };
const EVENT_NAMES = {
  session_started: '会话开始记录', session_ended: '会话结束记录', turn_started: '轮次开始记录',
  turn_stopped: '本轮停止记录', turn_interrupted: '本轮中断记录', tool_started: '工具开始记录',
  tool_completed: '工具结束记录', subagent_started: '子 Agent 开始记录', subagent_stopped: '子 Agent 停止记录',
  route_selected: '路线选择声明', route_changed: '路线变化声明', verification_summary: '验证摘要声明',
  handoff_generated: '交接生成声明', workflow_completed: '运行结束声明', routing_decision: '旧版路线声明', workflow_status: '旧版结果声明',
};
const FIELD_LABELS = {
  implementation: '实现', minimal_checks: '最小检查', test_verification: '测试验证', code_review: '代码审查',
  commit: '提交', push: '推送', development_status: '交付状态', code_availability: '代码可用性',
};
const VALUE_LABELS = {
  complete: '声明已完成', blocked: '声明受阻', passed: '声明通过', failed: '声明失败', partial: '声明部分完成',
  unavailable: '声明不可用', skipped: '声明跳过 / 未执行', completed: '声明已执行', 'findings-open': '声明仍有审查问题',
  ready_for_testing: '声明可进入测试', ready_with_issues: '声明带问题交付', available: '声明可用', local_only: '声明仅本地可用', unknown: '未知',
};
const isObject = value => value !== null && typeof value === 'object' && !Array.isArray(value);

/** Limit untrusted labels; callers always insert through textContent. */
export function safeText(value, fallback = '未知') {
  return typeof value === 'string' && value.trim() ? value.replace(/[\u0000-\u001f\u007f]/gu, ' ').slice(0, MAX_TEXT) : fallback;
}
export function shortId(value) {
  return safeText(value, '未提供 ID').replace(/^sha256:/u, '').slice(0, 12);
}
export function formatTime(value) {
  if (typeof value !== 'string' || !value.trim()) return '未知';
  const date = new Date(value);
  return Number.isFinite(date.getTime()) ? new Intl.DateTimeFormat('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false }).format(date) : '未知';
}
export function formatDuration(value) {
  if (!Number.isFinite(value) || value < 0) return '未提供耗时';
  if (value < 1000) return `${Math.round(value)} 毫秒`;
  if (value < 60_000) return `${(value / 1000).toFixed(1)} 秒`;
  return `${Math.floor(value / 60_000)} 分 ${Math.floor(value % 60_000 / 1000)} 秒`;
}
export function toolStatus(state) {
  return Object.hasOwn(TOOL_STATES, state) ? TOOL_STATES[state] : ['未知工具状态', 'muted'];
}
export function qualityStatus(quality) {
  return Object.hasOwn(QUALITY, quality) ? QUALITY[quality] : ['历史完整性未知', 'muted'];
}
export function provenanceLabel(value) {
  return value === 'agent_declared' ? 'Agent 声明 · 非独立执行证据' : value === 'host_observed' || value === 'host_format' ? '宿主格式记录 · 未签名验证' : '来源未提供 · 未验证';
}
export function summaryValue(value) {
  return Object.hasOwn(VALUE_LABELS, value) ? VALUE_LABELS[value] : '未知 / 未提供';
}

/** Support both nested protocol counts and the prototype engine's flat counters. */
export function diagnosticEntries(source) {
  const diagnostics = source?.diagnostics;
  const counts = isObject(diagnostics?.counts) ? diagnostics.counts : isObject(diagnostics) ? diagnostics : {};
  return Object.entries(counts).filter(([, value]) => Number.isSafeInteger(value) && value >= 0).slice(0, 30);
}

/** Coverage names vary by observer version; never infer a missing endpoint. */
export function coverageTimes(coverage) {
  return {
    start: formatTime(coverage?.start ?? coverage?.coverage_start ?? coverage?.from),
    end: formatTime(coverage?.end ?? coverage?.coverage_end ?? coverage?.to),
  };
}

/** Consume a one-use URL bootstrap without storing the capability anywhere persistent. */
export function readBootstrapToken(fragment) {
  const params = new URLSearchParams(typeof fragment === 'string' ? fragment.replace(/^#/u, '') : '');
  const tokens = params.getAll('token');
  const token = tokens.length === 1 ? tokens[0] : null;
  return typeof token === 'string' && token.length >= 1 && token.length <= 2048 && !/[\s\u0000-\u001f\u007f]/u.test(token) ? token : null;
}

/** Validate the outer offline contract; never reinterpret an unknown mode as live. */
export function validateSnapshot(value) {
  if (!isObject(value) || value.mode !== 'offline_prototype' || !isObject(value.source) || value.source.collection_verified !== false || !Object.hasOwn(SOURCE_STATES, value.source.status)) throw new ApiError('contract', '快照不符合离线原型协议');
  if (!(typeof value.revision === 'string' || Number.isSafeInteger(value.revision))) throw new ApiError('contract', '快照版本无效');
  for (const key of ['sessions', 'runs', 'events']) {
    if (!Array.isArray(value[key]) || value[key].length > 100_000 || !value[key].every(isObject)) throw new ApiError('contract', '快照记录结构无效');
  }
  for (const session of value.sessions) {
    if (typeof session.id !== 'string' || !Array.isArray(session.tools) || !session.tools.every(isObject) || !Array.isArray(session.turns) || !session.turns.every(isObject) || !Array.isArray(session.declarations) || !session.declarations.every(isObject)) throw new ApiError('contract', '会话记录结构无效');
  }
  for (const run of value.runs) {
    if (typeof run.id !== 'string' || !Array.isArray(run.events) || !run.events.every(isObject) || !Array.isArray(run.issues) || !isObject(run.summary)) throw new ApiError('contract', '工作流声明结构无效');
  }
  return value;
}

export class ApiError extends Error {
  constructor(code, message) { super(message); this.name = 'ApiError'; this.code = code; }
}

/** Same-origin allowlisted, authenticated GET with cancellation and bounded body reads. */
export async function requestApi(path, token, { signal, fetcher = globalThis.fetch, timeoutMs = 8000 } = {}) {
  if (!['/api/v1/snapshot', '/api/v1/capabilities', '/api/v1/health'].includes(path) || !token) throw new ApiError('auth', '需要重新从启动器打开');
  const controller = new AbortController();
  const abort = () => controller.abort();
  if (signal?.aborted) controller.abort();
  signal?.addEventListener('abort', abort, { once: true });
  let timedOut = false;
  const timer = setTimeout(() => { timedOut = true; controller.abort(); }, timeoutMs);
  let reader;
  try {
    const response = await fetcher(path, { method: 'GET', headers: { Authorization: `Bearer ${token}`, Accept: 'application/json' }, signal: controller.signal, cache: 'no-store', credentials: 'omit', redirect: 'error', referrerPolicy: 'no-referrer' });
    if (response.status === 401 || response.status === 403) throw new ApiError('auth', '授权已失效');
    if (!response.ok) throw new ApiError('http', `接口暂不可用（HTTP ${response.status}）`);
    if (!/^application\/json(?:\s*;|$)/iu.test(response.headers.get('content-type') ?? '')) throw new ApiError('contract', '接口未返回 JSON');
    if (Number(response.headers.get('content-length') ?? 0) > RESPONSE_LIMIT) throw new ApiError('contract', '快照超出页面读取上限');
    if (!response.body) throw new ApiError('contract', '接口返回空响应');
    reader = response.body.getReader();
    const decoder = new TextDecoder('utf-8', { fatal: true });
    const chunks = [];
    let bytes = 0;
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      bytes += value.byteLength;
      if (bytes > RESPONSE_LIMIT) throw new ApiError('contract', '快照超出页面读取上限');
      chunks.push(decoder.decode(value, { stream: true }));
    }
    chunks.push(decoder.decode());
    const value = JSON.parse(chunks.join(''));
    if (!isObject(value)) throw new ApiError('contract', '接口对象结构无效');
    return value;
  } catch (error) {
    if (error instanceof ApiError) throw error;
    if (timedOut) throw new ApiError('timeout', '接口响应超时');
    if (signal?.aborted) throw new ApiError('cancelled', '读取已取消');
    if (error instanceof SyntaxError || error instanceof TypeError && error.message.includes('encoded')) throw new ApiError('contract', '接口响应无法解析');
    throw new ApiError('network', '无法读取本地看板接口');
  } finally {
    clearTimeout(timer);
    signal?.removeEventListener('abort', abort);
    if (reader) { try { await reader.cancel(); } catch { /* Stream already closed/aborted. */ } }
  }
}

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = String(text);
  return node;
}
function badge(text, tone = 'muted') { return element('span', `badge tone-${tone}`, text); }
function block(title, index) {
  const section = element('section', 'detail-block');
  const heading = element('div', 'block-heading');
  heading.append(element('h4', '', title), element('span', 'section-index', index));
  section.append(heading);
  return section;
}
function empty(title, message, detail = false) {
  const node = element('div', detail ? 'detail-empty' : 'empty-state');
  node.append(element('span', 'section-index', 'NOT OBSERVED'), element('h3', '', title), element('p', '', message));
  return node;
}
function textRow(label, value) {
  const row = element('div', 'fact-row');
  row.append(element('dt', '', label), element('dd', '', value));
  return row;
}
function outcomeLabel(value) { return { succeeded: '工具返回成功', failed: '工具返回失败', completed: '工具已结束 · 成功结论未知' }[value] ?? '结果未提供'; }

/** Initialize only in a real document, allowing pure helpers to be tested with node:test. */
export function initializeConsole() {
  const byId = id => document.getElementById(id);
  const nodes = {
    list: byId('record-list'), detail: byId('record-detail'), panel: byId('records-panel'), filter: byId('filter-input'),
    refresh: byId('refresh-button'), notice: byId('notice'), noticeTitle: byId('notice-title'), noticeText: byId('notice-text'),
  };
  let token = readBootstrapToken(globalThis.location.hash);
  // Clearing happens even for malformed or duplicate token fragments.
  if (globalThis.location.hash) globalThis.history.replaceState(null, '', `${globalThis.location.pathname}${globalThis.location.search}`);
  let snapshot = null;
  let tab = 'sessions';
  const selected = { sessions: null, runs: null, diagnostics: 'source' };
  const filters = { sessions: '', runs: '', diagnostics: '' };
  let generation = 0;
  let activeController = null;
  let timer = null;
  let stopped = false;
  let auxiliaryAt = 0;
  let endpointStatus = '尚未连接';
  let stale = false;
  let dark = globalThis.matchMedia?.('(prefers-color-scheme: dark)').matches ?? false;

  function setTheme() {
    document.documentElement.dataset.theme = dark ? 'dark' : 'light';
    byId('theme-toggle').textContent = dark ? '浅色模式 ◑' : '深色模式 ◐';
    byId('theme-toggle').setAttribute('aria-label', dark ? '切换至浅色主题' : '切换至深色主题');
  }
  function showNotice(title, message, tone = 'signal') {
    nodes.notice.hidden = false;
    nodes.notice.dataset.tone = tone;
    nodes.noticeTitle.textContent = title;
    nodes.noticeText.textContent = message;
  }
  function renderReadouts() {
    byId('connection-status').textContent = endpointStatus;
    byId('source-status').textContent = snapshot ? SOURCE_STATES[snapshot.source.status] : '尚未读取';
    byId('last-event').textContent = formatTime(snapshot?.source.last_event_at);
    byId('revision').textContent = snapshot ? safeText(String(snapshot.revision)) : '—';
    byId('count-sessions').textContent = snapshot ? String(snapshot.sessions.length) : '—';
    byId('count-runs').textContent = snapshot ? String(snapshot.runs.length) : '—';
    byId('poll-status').textContent = token ? `${document.hidden ? '后台每 10 秒' : '前台每 2 秒'}读取 · ${stale ? '上次快照，仅供参考' : '轮询观察'}` : '未授权 · 已停止读取';
  }
  function items() {
    if (!snapshot) return [];
    return tab === 'sessions' ? snapshot.sessions : tab === 'runs' ? snapshot.runs : [{ id: 'source' }];
  }
  function searchText(item) {
    if (tab === 'sessions') return `${item.id} ${safeText(item.lifecycle, '')} ${item.tools.map(tool => `${safeText(tool.name, '')} ${toolStatus(tool.state)[0]}`).join(' ')}`;
    if (tab === 'runs') return `${item.id} ${safeText(item.route, '')} ${qualityStatus(item.quality)[0]}`;
    return `数据源 ${safeText(snapshot?.source.id, '')} ${SOURCE_STATES[snapshot?.source.status] ?? ''} 诊断`;
  }
  function renderList() {
    byId('list-title').textContent = { sessions: '会话索引', runs: '声明流索引', diagnostics: '来源索引' }[tab];
    const all = items();
    const filtered = all.filter(item => searchText(item).toLocaleLowerCase().includes(filters[tab].toLocaleLowerCase()));
    byId('list-count').textContent = snapshot ? `${filtered.length} / ${all.length}` : '尚无快照';
    if (!filtered.some(item => item.id === selected[tab])) selected[tab] = filtered[0]?.id ?? null;
    nodes.list.replaceChildren();
    if (!snapshot) { nodes.list.append(empty('尚未载入记录', '没有连接不等于没有活动。请先从启动器授权打开看板。')); return; }
    if (!filtered.length) { nodes.list.append(empty(filters[tab] ? '没有匹配记录' : '当前没有记录', filters[tab] ? '尝试其他 ID、状态或工具名称。' : '空列表不证明采集正常，也不代表本次任务没有活动。')); return; }
    for (const item of filtered.slice(0, 200)) {
      const button = element('button', `record-button${selected[tab] === item.id ? ' is-selected' : ''}`);
      button.type = 'button';
      button.setAttribute('aria-pressed', String(selected[tab] === item.id));
      const heading = element('span', 'record-top');
      heading.append(element('span', 'record-kind', { sessions: 'SESSION', runs: 'DECLARATION', diagnostics: 'SOURCE' }[tab]), element('span', 'record-arrow', '↗'));
      const title = tab === 'diagnostics' ? '本地日志来源' : `${tab === 'sessions' ? '会话' : '声明流'} ${shortId(item.id)}`;
      button.append(heading, element('strong', 'record-title', title));
      if (tab === 'sessions') button.append(element('span', 'record-subtitle', `${item.tools.length} 条工具记录 · ${formatTime(item.last_at)}`), badge('宿主格式 · 未签名', 'muted'));
      else if (tab === 'runs') button.append(element('span', 'record-subtitle', qualityStatus(item.quality)[0]), badge(item.route && ['L1', 'L2', 'L3'].includes(item.route) ? `Agent 声明 · ${item.route}` : 'Agent 声明 · 路线未知'));
      else button.append(element('span', 'record-subtitle', SOURCE_STATES[snapshot.source.status]), badge('实时采集未验证', 'signal'));
      button.addEventListener('click', () => { selected[tab] = item.id; renderList(); renderDetail(); });
      nodes.list.append(button);
    }
    if (filtered.length > 200) nodes.list.append(element('p', 'list-limit', '仅显示前 200 条，请筛选 ID 缩小范围。'));
  }
  function detailHeader(kind, title, status, tone = 'muted') {
    const header = element('header', 'detail-header');
    header.append(element('p', 'eyebrow', kind), element('h3', '', title), badge(status, tone));
    return header;
  }
  function timeline(events, title = '最近事件') {
    const section = block(title, 'EVENT LOG');
    if (!events.length) { section.append(element('p', 'unavailable', '未提供事件。不能从缺失记录推断执行状态。')); return section; }
    const list = element('ol', 'timeline');
    for (const event of events.slice(-40).reverse()) {
      const item = element('li', event.outcome === 'failed' ? 'timeline-item has-failure' : 'timeline-item');
      const body = element('div', 'timeline-body');
      body.append(element('strong', '', EVENT_NAMES[event.event] ?? `未知事件 · ${safeText(event.event)}`));
      if (event.tool_name) body.append(element('span', 'event-meta', safeText(event.tool_name)));
      if (event.outcome) body.append(element('span', 'event-meta', outcomeLabel(event.outcome)));
      body.append(element('span', 'event-provenance', provenanceLabel(event.provenance ?? (['route_selected', 'route_changed', 'verification_summary', 'handoff_generated', 'workflow_completed', 'routing_decision', 'workflow_status'].includes(event.event) ? 'agent_declared' : null))));
      item.append(element('time', '', formatTime(event.timestamp)), body);
      list.append(item);
    }
    section.append(list);
    if (events.length > 40) section.append(element('p', 'small-note', '当前展示最后 40 条事件；不会因后续成功事件清除失败记录。'));
    return section;
  }
  function summarySection(summary, heading = '已声明结果') {
    const section = block(heading, 'AGENT DECLARED');
    section.append(element('p', 'block-note', '以下来自 Agent 声明，不是独立执行证据；历史结果对当前代码的有效性未验证。'));
    const grid = element('dl', 'facts');
    for (const [field, label] of Object.entries(FIELD_LABELS)) grid.append(textRow(label, summaryValue(summary?.[field])));
    section.append(grid);
    return section;
  }
  function sessionDetail(item) {
    const fragment = document.createDocumentFragment();
    fragment.append(detailHeader('SESSION / OBSERVED ACTIVITY', `会话 ${shortId(item.id)}`, '宿主格式记录 · 未签名验证'));
    const facts = element('dl', 'facts intro-facts');
    const lifecycles = { open_observed: '已观察到会话开始', end_observed: '已观察到会话结束', started: '已记录会话开始', ended: '已记录会话结束' };
    facts.append(textRow('生命周期', lifecycles[item.lifecycle] ?? '未提供可靠生命周期'), textRow('最近记录', formatTime(item.last_at)), textRow('轮次记录', `${item.turns.length} 条 · 停止仅表示该轮结束`));
    fragment.append(facts);
    const current = block('当前可观测活动', 'OBSERVED, NOT LIVE');
    const open = item.tools.filter(tool => ['start_observed', 'incomplete', 'conflicted'].includes(tool.state));
    if (!open.length) current.append(element('p', 'unavailable', '没有未配对的开始记录。这不代表任务已完成，也不证明没有工具在运行。'));
    for (const tool of open.slice(-20)) {
      const row = element('div', 'tool-observation');
      row.append(element('strong', '', safeText(tool.name, '未提供工具名')), badge(...toolStatus(tool.state)), element('p', '', `开始记录 ${formatTime(tool.started_at)} · 尚未确认配对结束事件`));
      current.append(row);
    }
    current.append(element('p', 'boundary-note', '未见结束事件 ≠ 工具仍然存活。这里不推断思考、卡住、等待用户或等待审批。'));
    fragment.append(current);
    const failures = item.tools.filter(tool => tool.state === 'completion_failed' || tool.state === 'conflicted');
    const failureSection = block('失败与冲突记录', 'DURABLE HISTORY');
    if (!failures.length) failureSection.append(element('p', 'unavailable', '当前快照未包含失败或冲突记录；这不是“检查全部通过”的结论。'));
    for (const tool of failures.slice(-30).reverse()) {
      const row = element('div', 'failure-record');
      row.append(badge(...toolStatus(tool.state)), element('strong', '', safeText(tool.name, '未提供工具名')), element('p', '', `${formatTime(tool.ended_at ?? tool.started_at)} · ${formatDuration(tool.duration_ms)}`), element('small', '', '没有相同检查身份的复测证据，不标为已修复。'));
      failureSection.append(row);
    }
    if (failures.length > 30) failureSection.append(element('p', 'small-note', `快照包含 ${failures.length} 条失败/冲突记录，当前展示最近 30 条；更早记录未被改为成功。`));
    fragment.append(failureSection);
    const tools = block('工具记录', 'TOOL RECORDS');
    if (!item.tools.length) tools.append(element('p', 'unavailable', '没有提供工具记录。'));
    for (const tool of item.tools.slice(-30).reverse()) {
      const row = element('div', 'tool-row');
      const label = element('div');
      label.append(element('strong', '', safeText(tool.name, '未提供工具名')), element('small', '', `${shortId(tool.id)} · ${formatTime(tool.ended_at ?? tool.started_at)}`));
      row.append(label, badge(...toolStatus(tool.state)), element('span', 'mono small-note', formatDuration(tool.duration_ms)));
      tools.append(row);
    }
    fragment.append(tools);
    for (const declaration of item.declarations.slice(-3)) fragment.append(summarySection(declaration, '轮次末尾的旧版声明'));
    fragment.append(timeline(snapshot.events.filter(event => event.session_id === item.id && !event.task_run_id)));
    fragment.append(unavailability());
    return fragment;
  }
  function unavailability() {
    const section = block('未提供的信息', 'BOUNDARIES');
    section.append(element('p', 'unavailable', '业务阶段、剩余工作项、测试用例数量、审批等待原因与 Skill 实际加载记录：当前数据源未提供。会话与工作流声明不会按时间自动关联。'));
    return section;
  }
  function runDetail(item) {
    const fragment = document.createDocumentFragment();
    fragment.append(detailHeader('WORKFLOW / AGENT DECLARATION', `声明流 ${shortId(item.id)}`, ...qualityStatus(item.quality)));
    const facts = element('dl', 'facts intro-facts');
    facts.append(textRow('来源', 'Agent 声明 · 非独立执行证据'), textRow('路线', ['L1', 'L2', 'L3'].includes(item.route) && !['partial', 'conflicted'].includes(item.quality) ? `${item.route} · 声明路线` : '未知 / 历史不足以确认'), textRow('运行结束', item.ended === true ? '已记录结束声明，不代表成功' : '未提供结束声明'));
    fragment.append(facts, summarySection(item.summary));
    const issues = block('历史完整性', 'INTEGRITY');
    issues.append(element('p', 'block-note', qualityStatus(item.quality)[0]));
    if (!item.issues.length) issues.append(element('p', 'unavailable', '快照未列出具体问题；本地记录未经签名，不作为审计证明。'));
    for (const issue of item.issues.slice(0, 30)) issues.append(element('p', 'issue-row', safeText(typeof issue === 'string' ? issue : issue?.reason, '存在未说明的数据质量问题')));
    fragment.append(issues, timeline(item.events, '声明事件'), unavailability());
    return fragment;
  }
  function diagnosticsDetail() {
    const source = snapshot.source;
    const fragment = document.createDocumentFragment();
    fragment.append(detailHeader('SOURCE / DIAGNOSTICS', '本地日志来源', '离线原型 · 采集未验证', 'signal'));
    const facts = element('dl', 'facts intro-facts');
    facts.append(textRow('来源短 ID', shortId(source.id)), textRow('读取状态', SOURCE_STATES[source.status]), textRow('最近读取', formatTime(source.last_read_at)), textRow('最近事件', formatTime(source.last_event_at)), textRow('实时采集', '未验证'), textRow('看板接口', '可达仅代表 Companion 可达'));
    fragment.append(facts);
    const counts = block('诊断计数', 'DATA QUALITY');
    const entries = diagnosticEntries(source);
    if (!entries.length) counts.append(element('p', 'unavailable', '未提供诊断计数。不能因此认定数据完整。'));
    const list = element('dl', 'facts');
    for (const [key, value] of entries) list.append(textRow(safeText(key), Number.isSafeInteger(value) && value >= 0 ? String(value) : '无效计数'));
    counts.append(list);
    fragment.append(counts);
    const coverage = block('覆盖范围', 'COVERAGE');
    const coverageFacts = element('dl', 'facts');
    const range = coverageTimes(source.coverage);
    coverageFacts.append(textRow('覆盖起始', range.start), textRow('覆盖结束', range.end));
    coverage.append(coverageFacts, element('p', 'boundary-note', '保留期、截断、缺失事件或未采集时段都会造成覆盖缺口；未提供的范围不补齐。'));
    fragment.append(coverage);
    const capabilities = block('能力边界', 'CAPABILITIES');
    const capabilityFacts = element('dl', 'facts');
    capabilityFacts.append(textRow('原生计划', '未接入 / 未验证'), textRow('MCP 内嵌界面', '未接入 / 未验证'), textRow('业务阶段', '不可用'), textRow('任务控制', '不提供'));
    capabilities.append(capabilityFacts);
    fragment.append(capabilities, unavailability());
    return fragment;
  }
  function renderDetail() {
    const item = items().find(candidate => candidate.id === selected[tab]);
    if (!snapshot || !item) { nodes.detail.replaceChildren(empty('为未知留白。', snapshot ? '当前类别没有可选择的记录。没有记录不等于没有活动。' : '尚无已授权快照。请从 Companion 启动器重新打开页面。', true)); return; }
    nodes.detail.replaceChildren(tab === 'sessions' ? sessionDetail(item) : tab === 'runs' ? runDetail(item) : diagnosticsDetail());
  }
  function render() { renderReadouts(); renderList(); renderDetail(); }
  function selectTab(next) {
    tab = next;
    nodes.filter.value = filters[tab];
    for (const button of document.querySelectorAll('[data-tab]')) {
      const active = button.dataset.tab === tab;
      button.setAttribute('aria-selected', String(active));
      button.tabIndex = active ? 0 : -1;
    }
    nodes.panel.setAttribute('aria-labelledby', `tab-${tab}`);
    renderList(); renderDetail();
  }
  function cancelLoop() {
    generation += 1;
    clearTimeout(timer);
    activeController?.abort();
    activeController = null;
  }
  async function poll(epoch) {
    if (stopped || epoch !== generation || !token) return;
    const controller = new AbortController();
    activeController = controller;
    nodes.refresh.disabled = true;
    nodes.refresh.setAttribute('aria-busy', 'true');
    try {
      const now = Date.now();
      const paths = now - auxiliaryAt > 30_000 ? ['/api/v1/snapshot', '/api/v1/capabilities', '/api/v1/health'] : ['/api/v1/snapshot'];
      const results = await Promise.all(paths.map(async path => requestApi(path, token, { signal: controller.signal })));
      if (epoch !== generation || stopped) return;
      const next = validateSnapshot(results[0]);
      if (results[1] && (!['native_plan', 'mcp_ui', 'business_stages'].every(key => typeof results[1][key] === 'boolean'))) throw new ApiError('contract', '能力接口结构无效');
      if (results[1]) auxiliaryAt = now;
      const unchanged = snapshot?.revision === next.revision;
      snapshot = next;
      stale = false;
      endpointStatus = '可达 · 非 Codex 活跃证明';
      showNotice('只读快照已载入', 'Codex 实时采集仍未验证。此页面只显示收到的本地记录；所有阶段与剩余工作量均不推断。', 'neutral');
      // Preserve focus and scroll while an unchanged snapshot is polled repeatedly.
      if (unchanged) renderReadouts(); else render();
    } catch (error) {
      if (epoch !== generation || stopped || error.code === 'cancelled') return;
      controller.abort();
      stale = true;
      if (error.code === 'auth') {
        token = null;
        snapshot = null;
        endpointStatus = '授权失效 · 读取已停止';
        showNotice('授权已失效，请重新打开', '请从本机 Companion 启动器重新打开页面以获取新令牌。页面不会保存或尝试恢复旧令牌，也不会自动重试授权。', 'failure');
      } else {
        endpointStatus = '接口不可用 · 非任务状态';
        showNotice(error.code === 'contract' ? '响应未通过协议校验' : '暂时无法读取看板接口', snapshot ? '正在展示上一次成功读取的快照，不是当前状态。页面会按轮询间隔重试；无法据此判断 Codex 是否运行。' : '未载入任何快照。请确认 Companion 已启动；页面会重试，但不会生成示例数据或假定已连接。', 'failure');
      }
      render();
    } finally {
      if (epoch === generation && !stopped) {
        activeController = null;
        nodes.refresh.disabled = !token;
        nodes.refresh.removeAttribute('aria-busy');
        if (token) timer = setTimeout(() => { void poll(epoch); }, document.hidden ? 10_000 : 2000);
      }
    }
  }
  function restart() { cancelLoop(); if (token && !stopped) void poll(generation); }
  byId('theme-toggle').addEventListener('click', () => { dark = !dark; setTheme(); });
  nodes.refresh.addEventListener('click', restart);
  nodes.filter.addEventListener('input', () => { filters[tab] = nodes.filter.value.slice(0, 128); renderList(); renderDetail(); });
  const tabs = [...document.querySelectorAll('[data-tab]')];
  for (const [index, button] of tabs.entries()) {
    button.addEventListener('click', () => selectTab(button.dataset.tab));
    button.addEventListener('keydown', event => {
      const nextIndex = event.key === 'ArrowRight' ? (index + 1) % tabs.length : event.key === 'ArrowLeft' ? (index + tabs.length - 1) % tabs.length : event.key === 'Home' ? 0 : event.key === 'End' ? tabs.length - 1 : null;
      if (nextIndex !== null) { event.preventDefault(); selectTab(tabs[nextIndex].dataset.tab); tabs[nextIndex].focus(); }
    });
  }
  document.addEventListener('visibilitychange', restart);
  globalThis.addEventListener('pagehide', () => { stopped = true; cancelLoop(); token = null; snapshot = null; }, { once: true });
  globalThis.addEventListener('pageshow', event => {
    if (event.persisted) { endpointStatus = '页面恢复 · 需要重新授权'; showNotice('请从启动器重新打开', '为避免恢复过期授权，页面返回后需要重新从本机启动器打开。'); render(); }
  });
  setTheme();
  renderReadouts();
  if (token) { nodes.refresh.disabled = false; showNotice('正在读取本地看板', '仅请求授权的本机接口。Codex 实时采集未验证。'); restart(); }
}

if (typeof document !== 'undefined') initializeConsole();
