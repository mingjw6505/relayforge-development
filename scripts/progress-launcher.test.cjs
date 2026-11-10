'use strict';
const {test} = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const path = require('node:path');
const {EventEmitter} = require('node:events');
const source = fs.readFileSync(path.join(__dirname, 'progress-launcher.cjs'), 'utf8');

function run({platform = 'win32', env = {}, replies = [], args = [], exit = 0} = {}) {
  const probes = [], launches = [], out = [], err = [];
  const proc = {platform, versions: {node: '18.20.0'}, env, argv: ['node', 'launcher', ...args],
    stdout: {write: x => out.push(x)}, stderr: {write: x => err.push(x)}, on() {}};
  const childProcess = {
    spawnSync(command, args, options) {
      probes.push({command, args, options});
      return replies.shift() || {error: {code: 'ENOENT'}, stdout: '', stderr: ''};
    },
    spawn(command, args, options) {
      launches.push({command, args, options});
      const child = new EventEmitter();
      child.kill = () => {};
      queueMicrotask(() => child.emit('exit', exit, null));
      return child;
    },
  };
  vm.runInNewContext(source, {require: name => name === 'node:child_process' ? childProcess : require(name),
    process: proc, __dirname, Date, console});
  return {proc, probes, launches, out, err};
}
const valid = {status: 0, stdout: JSON.stringify({executable: 'C:/Python with spaces/python.exe', version: [3, 11, 9]})};

test('falls back from missing py and Store alias to existing python, without shell', () => {
  const r = run({replies: [{error: {code: 'ENOENT'}}, {status: 0, stdout: ''}, valid]});
  assert.deepEqual(r.probes.map(x => x.command), ['py', 'python3', 'python']);
  assert.equal(r.launches[0].command, 'C:/Python with spaces/python.exe');
  assert.equal(r.launches[0].options.shell, false);
  assert.equal(r.launches[0].options.stdio, 'inherit');
  assert.equal(r.launches[0].options.env.PYTHONUTF8, '1');
  assert.equal(r.out.length, 0);
});

test('rejects old Python, missing sqlite and a hung probe before selecting versioned Python', () => {
  const r = run({platform: 'linux', replies: [
    {status: 1, stderr: 'AssertionError: python_too_old'},
    {status: 1, stderr: 'No module named sqlite3'},
    {error: {code: 'ETIMEDOUT'}}, valid,
  ]});
  assert.deepEqual(r.probes.map(x => x.command), ['python3', 'python', 'python3.15', 'python3.14']);
  assert.ok(r.probes.every(x => x.options.timeout <= 1200));
  assert.equal(r.launches.length, 1);
});

test('missing environment returns actionable diagnostic, no MCP stdout or install attempt', () => {
  const r = run();
  assert.equal(r.proc.exitCode, 78);
  assert.equal(r.launches.length, 0);
  assert.equal(r.out.length, 0);
  assert.match(r.err.join(''), /python_unavailable.*RELAYFORGE_PYTHON.*python.org/);
});

test('explicit executable is literal and never silently replaced', () => {
  const r = run({env: {RELAYFORGE_PYTHON: 'bad; executable'}, args: ['--doctor']});
  assert.deepEqual(r.probes.map(x => x.command), ['bad; executable']);
  const result = JSON.parse(r.out.join(''));
  assert.equal(result.status, 'python_unavailable');
  assert.equal(result.failures[0].reason, 'not_found');
});

test('doctor checks package after interpreter, and never starts a long-lived server', () => {
  const r = run({args: ['--doctor'], replies: [valid, {status: 0,
    stdout: JSON.stringify({status: 'runtime_ready', host_ui: 'unverified'})}]});
  assert.equal(JSON.parse(r.out.join('')).host_ui, 'unverified');
  assert.equal(r.launches.length, 0);
  assert.equal(r.probes[1].args.join(' '), '-m progress_panel.doctor');
});

test('package failure is distinct from Python absence and does not echo child output', () => {
  const r = run({args: ['--doctor'], replies: [valid, {status: 1, stdout: 'secret', stderr: 'secret'}]});
  assert.equal(JSON.parse(r.out.join('')).status, 'package_check_failed');
  assert.equal(r.proc.exitCode, 70);
  assert.doesNotMatch(r.out.join(''), /secret/);
});

test('nonzero server exit retains diagnostics without retrying consumed MCP input', async () => {
  const r = run({replies: [valid], exit: 7});
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(r.proc.exitCode, 7);
  assert.match(r.err.join(''), /server_exited/);
  assert.equal(r.launches.length, 1);
  assert.equal(r.out.length, 0);
});
