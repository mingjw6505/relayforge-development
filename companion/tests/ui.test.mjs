import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

// Import as ESM without requiring a package.json or changing the parent project.
const source = await readFile(new URL('../relayforge_progress/static/app.js', import.meta.url), 'utf8');
const ui = await import(`data:text/javascript;base64,${Buffer.from(source).toString('base64')}`);
const snapshot = () => ({ revision: 1, mode: 'offline_prototype', source: { id: 'local', status: 'readable', collection_verified: false }, sessions: [], runs: [], events: [], capabilities: { native_plan: false, mcp_ui: false, business_stages: false } });
const jsonResponse = (value, init = {}) => new Response(JSON.stringify(value), { headers: { 'Content-Type': 'application/json' }, ...init });

test('labels remain text, are bounded, and reject unknown prototype-key statuses', () => {
  assert.equal(ui.safeText('<img src=x onerror=alert(1)>'), '<img src=x onerror=alert(1)>');
  assert.equal(ui.safeText('x'.repeat(1000)).length, 240);
  assert.equal(ui.safeText('a\nb'), 'a b');
  assert.equal(ui.safeText(null), '未知');
  assert.deepEqual(ui.toolStatus('start_observed'), ['已观察到开始', 'signal']);
  assert.match(ui.toolStatus('completion_unspecified')[0], /未知/u);
  assert.deepEqual(ui.toolStatus('__proto__'), ['未知工具状态', 'muted']);
  assert.deepEqual(ui.qualityStatus('constructor'), ['历史完整性未知', 'muted']);
  assert.equal(ui.summaryValue('toString'), '未知 / 未提供');
  assert.equal(ui.shortId('sha256:1234567890123456'), '123456789012');
});

test('formatters never invent time or duration', () => {
  for (const value of [null, '', 'invalid']) assert.equal(ui.formatTime(value), '未知');
  for (const value of [undefined, null, -1, Infinity, '100']) assert.equal(ui.formatDuration(value), '未提供耗时');
  assert.equal(ui.formatDuration(0), '0 毫秒');
  assert.equal(ui.formatDuration(1500), '1.5 秒');
  assert.equal(ui.formatDuration(61_000), '1 分 1 秒');
  assert.equal(ui.provenanceLabel('host_observed'), '宿主格式记录 · 未签名验证');
  assert.equal(ui.provenanceLabel('agent_declared'), 'Agent 声明 · 非独立执行证据');
  assert.match(ui.provenanceLabel(null), /未验证/u);
});

test('diagnostics and coverage support nested protocol and flat prototype engine formats', () => {
  assert.deepEqual(ui.diagnosticEntries({ diagnostics: { counts: { invalid_lines: 2, refresh_errors: 0 } } }), [['invalid_lines', 2], ['refresh_errors', 0]]);
  assert.deepEqual(ui.diagnosticEntries({ diagnostics: { invalid_lines: 2, refresh_errors: 3, secret: 'not a count', bad: -1 } }), [['invalid_lines', 2], ['refresh_errors', 3]]);
  assert.deepEqual(ui.diagnosticEntries(null), []);
  assert.deepEqual(ui.coverageTimes({ from: '2026-11-06T09:00:00Z', to: '2026-11-06T10:00:00Z' }), { start: ui.formatTime('2026-11-06T09:00:00Z'), end: ui.formatTime('2026-11-06T10:00:00Z') });
  assert.deepEqual(ui.coverageTimes({}), { start: '未知', end: '未知' });
});

test('bootstrap tokens are fragment-only, unique, bounded and whitespace-free', () => {
  assert.equal(ui.readBootstrapToken('#token=example-token'), 'example-token');
  assert.equal(ui.readBootstrapToken('#token=one&token=two'), null);
  assert.equal(ui.readBootstrapToken('#token='), null);
  assert.equal(ui.readBootstrapToken('#token=bad%0Atoken'), null);
  assert.equal(ui.readBootstrapToken('#token=bad%20token'), null);
  assert.equal(ui.readBootstrapToken(`#token=${'x'.repeat(2049)}`), null);
  assert.equal(ui.readBootstrapToken('#workspace'), null);
});

test('snapshot fails closed on live modes, verified collection, and malformed arrays', () => {
  assert.equal(ui.validateSnapshot(snapshot()).revision, 1);
  for (const change of [{ mode: 'live' }, { revision: null }, { sessions: {} }, { events: [null] }, { source: { status: 'readable', collection_verified: true } }, { source: { status: 'constructor', collection_verified: false } }, { sessions: [{ id: '1', tools: [], turns: [] }] }, { runs: [{ id: 'r', events: [], issues: [], summary: null }] }]) {
    assert.throws(() => ui.validateSnapshot({ ...snapshot(), ...change }), error => error.code === 'contract');
  }
});

test('request helper uses authenticated same-origin GET without storage/cookies/redirects', async () => {
  let call;
  const result = await ui.requestApi('/api/v1/health', 'short-token', { fetcher: async (path, options) => { call = { path, options }; return jsonResponse({ status: 'ok' }); } });
  assert.deepEqual(result, { status: 'ok' });
  assert.equal(call.path, '/api/v1/health');
  assert.equal(call.options.method, 'GET');
  assert.equal(call.options.headers.Authorization, 'Bearer short-token');
  assert.equal(call.options.credentials, 'omit');
  assert.equal(call.options.cache, 'no-store');
  assert.equal(call.options.redirect, 'error');
  assert.equal(call.options.referrerPolicy, 'no-referrer');
  await assert.rejects(ui.requestApi('https://example.com/steal', 'token'), error => error.code === 'auth');
  await assert.rejects(ui.requestApi('/api/v1/health', null), error => error.code === 'auth');
});

test('request helper treats 401/403 as expired authorization and never trusts error bodies', async () => {
  for (const status of [401, 403]) await assert.rejects(ui.requestApi('/api/v1/snapshot', 'token', { fetcher: async () => new Response('secret-bearing untrusted error', { status }) }), error => error.code === 'auth' && !error.message.includes('secret'));
  await assert.rejects(ui.requestApi('/api/v1/health', 'token', { fetcher: async () => new Response('not found', { status: 404 }) }), error => error.code === 'http');
});

test('request helper rejects HTML, malformed JSON, scalar JSON and oversized bodies', async () => {
  const responses = [
    () => new Response('<html>error</html>', { headers: { 'Content-Type': 'text/html' } }),
    () => new Response('{oops', { headers: { 'Content-Type': 'application/json' } }),
    () => jsonResponse([]),
    () => new Response('{}', { headers: { 'Content-Type': 'application/json', 'Content-Length': String(9 * 1024 * 1024) } }),
    () => new Response(new Uint8Array(8 * 1024 * 1024 + 1), { headers: { 'Content-Type': 'application/json' } }),
  ];
  for (const response of responses) await assert.rejects(ui.requestApi('/api/v1/snapshot', 'token', { fetcher: async () => response() }), error => error.code === 'contract');
});

test('request helper has bounded timeout and caller cancellation', async () => {
  const hangingFetch = async (_path, { signal }) => await new Promise((_resolve, reject) => {
    if (signal.aborted) { reject(new DOMException('Aborted', 'AbortError')); return; }
    signal.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')), { once: true });
  });
  await assert.rejects(ui.requestApi('/api/v1/health', 'token', { fetcher: hangingFetch, timeoutMs: 10 }), error => error.code === 'timeout');
  const controller = new AbortController();
  controller.abort();
  await assert.rejects(ui.requestApi('/api/v1/health', 'token', { fetcher: hangingFetch, signal: controller.signal }), error => error.code === 'cancelled');
});

test('DOM smoke: bootstrap, snapshot render, tab switch, diagnostics, filter, and theme', async () => {
  class FakeElement {
    constructor(tag = 'div') { this.tagName = tag; this.children = []; this.dataset = {}; this.attributes = {}; this.handlers = {}; this._text = ''; this.value = ''; }
    set textContent(value) { this._text = String(value); this.children = []; }
    get textContent() { return this._text + this.children.map(child => child.textContent).join(' '); }
    append(...children) { this.children.push(...children); }
    replaceChildren(...children) { this._text = ''; this.children = [...children]; }
    setAttribute(name, value) { this.attributes[name] = String(value); }
    removeAttribute(name) { delete this.attributes[name]; }
    addEventListener(name, callback) { this.handlers[name] = callback; }
    focus() {}
  }
  const originals = new Map(['document', 'location', 'history', 'matchMedia', 'addEventListener', 'fetch'].map(key => [key, Object.getOwnPropertyDescriptor(globalThis, key)]));
  const elements = new Map();
  const getElement = id => { if (!elements.has(id)) elements.set(id, new FakeElement()); return elements.get(id); };
  const tabs = ['sessions', 'runs', 'diagnostics'].map(name => { const node = getElement(`tab-${name}`); node.dataset.tab = name; return node; });
  const windowHandlers = {};
  let cleared = null;
  const calls = [];
  const fixture = snapshot();
  fixture.source.diagnostics = { invalid_lines: 2, refresh_errors: 1 };
  fixture.source.coverage = { from: '2026-11-06T09:00:00Z', to: '2026-11-06T10:00:00Z' };
  fixture.sessions = [{ id: 'sha256:12345678901234567890', label: 'must not use a task title', lifecycle: 'open_observed', last_at: null, turns: [], declarations: [], tools: [{ id: 't1', name: '<script>unsafe</script>', state: 'start_observed' }, { id: 't2', name: 'shell', state: 'completion_failed', ended_at: '2026-11-06T09:00:00Z' }, { id: 't3', name: 'shell', state: 'completion_succeeded' }] }];
  fixture.runs = [{ id: 'run-one', quality: 'intact_ended', route: 'L1', ended: true, summary: { implementation: 'blocked' }, events: [], issues: [] }];
  try {
    Object.assign(globalThis, {
      document: { getElementById: getElement, createElement: tag => new FakeElement(tag), createDocumentFragment: () => new FakeElement('fragment'), querySelectorAll: () => tabs, documentElement: new FakeElement('html'), hidden: false, addEventListener() {} },
      location: { hash: '#token=test-token', pathname: '/', search: '' },
      history: { replaceState: (_state, _unused, url) => { cleared = url; } },
      matchMedia: () => ({ matches: false }),
      addEventListener: (name, handler) => { windowHandlers[name] = handler; },
      fetch: async (path, options) => { calls.push({ path, options }); return jsonResponse(path.endsWith('/snapshot') ? fixture : path.endsWith('/capabilities') ? fixture.capabilities : { status: 'ok' }); },
    });
    ui.initializeConsole();
    await new Promise(resolve => setImmediate(resolve));
    assert.equal(cleared, '/');
    assert.equal(calls.length, 3);
    assert.ok(calls.every(call => call.options.headers.Authorization === 'Bearer test-token'));
    assert.match(getElement('record-detail').textContent, /未见结束事件 ≠ 工具仍然存活/u);
    assert.match(getElement('record-detail').textContent, /工具返回失败/u);
    assert.match(getElement('record-detail').textContent, /<script>unsafe<\/script>/u);
    assert.doesNotMatch(getElement('record-list').textContent, /must not use a task title/u);
    tabs[1].handlers.click();
    assert.match(getElement('record-detail').textContent, /声明受阻/u);
    tabs[2].handlers.click();
    assert.match(getElement('record-detail').textContent, /invalid_lines 2/u);
    assert.doesNotMatch(getElement('record-detail').textContent, /覆盖起始 未知/u);
    getElement('filter-input').value = 'no-match';
    getElement('filter-input').handlers.input();
    assert.match(getElement('record-list').textContent, /没有匹配记录/u);
    getElement('theme-toggle').handlers.click();
    assert.equal(globalThis.document.documentElement.dataset.theme, 'dark');
  } finally {
    windowHandlers.pagehide?.();
    for (const [key, descriptor] of originals) { if (descriptor) Object.defineProperty(globalThis, key, descriptor); else delete globalThis[key]; }
  }
});

test('UI source has no dynamic HTML, persistent token storage, auto-generated samples or intervals', () => {
  assert.doesNotMatch(source, /\.innerHTML\s*=|insertAdjacentHTML|localStorage|sessionStorage|setInterval\(/u);
  assert.match(source, /history\.replaceState/u);
  assert.match(source, /document\.hidden \? 10_000 : 2000/u);
  assert.match(source, /Codex 实时采集仍未验证/u);
});
