#!/usr/bin/env node
'use strict';

// No npm dependencies. Keep diagnostics off the MCP stdout transport.
const {spawn, spawnSync} = require('node:child_process');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const doctor = process.argv.slice(2).includes('--doctor');
const args = process.argv.slice(2);
const env = {...process.env, PYTHONUTF8: '1', PYTHONUNBUFFERED: '1'};
const probe = 'import sys,json; assert sys.version_info >= (3,11), "python_too_old"; import sqlite3; print(json.dumps({"executable":sys.executable,"version":list(sys.version_info[:3])}))';

function candidates() {
  if (process.env.RELAYFORGE_PYTHON) return [[process.env.RELAYFORGE_PYTHON]];
  const common = [['python3'], ['python']];
  const versions = [15, 14, 13, 12, 11];
  return process.platform === 'win32'
    ? [['py', '-3'], ...common, ...versions.map(v => ['py', `-3.${v}`])]
    : [...common, ...versions.map(v => [`python3.${v}`])];
}

function report(value, code) {
  if (doctor) process.stdout.write(JSON.stringify(value) + '\n');
  else process.stderr.write(`[relayforge-progress] ${value.status}: ${value.message}\n`);
  process.exitCode = code;
}

function main() {
  if (Number(process.versions.node.split('.')[0]) < 18) {
    report({status: 'node_too_old', message: 'Use Node.js 18+ or a host-provided compatible Node runtime.'}, 78);
    return;
  }
  if (args.some(arg => arg !== '--doctor') || args.length > 1) {
    report({status: 'invalid_arguments', message: 'Use no arguments for MCP, or --doctor for environment diagnostics.'}, 64);
    return;
  }
  const failures = [];
  let selected;
  const deadline = Date.now() + 6500;
  for (const command of candidates()) {
    const remaining = deadline - Date.now();
    if (remaining <= 0) { failures.push({candidate: 'remaining', reason: 'probe_budget_exhausted'}); break; }
    const result = spawnSync(command[0], [...command.slice(1), '-c', probe], {
      cwd: root, env, encoding: 'utf8', timeout: Math.min(1200, remaining),
      windowsHide: true, maxBuffer: 16384, shell: false,
    });
    let info;
    try { info = JSON.parse(result.stdout); } catch { /* Store aliases and noisy wrappers are not interpreters. */ }
    if (!result.error && result.status === 0 && info && Array.isArray(info.version)
        && info.version[0] === 3 && info.version[1] >= 11 && typeof info.executable === 'string') {
      selected = info;
      break;
    }
    const reason = result.error ? (result.error.code === 'ENOENT' ? 'not_found'
      : result.error.code === 'ETIMEDOUT' ? 'probe_timeout' : 'cannot_execute')
      : /python_too_old/.test(result.stderr || '') ? 'python_too_old'
      : /sqlite3/.test(result.stderr || '') ? 'sqlite_unavailable' : 'invalid_interpreter';
    failures.push({candidate: command.join(' '), reason});
  }
  if (!selected) {
    report({status: 'python_unavailable', failures, message:
      'No usable Python 3.11+ with sqlite3 was found within the probe budget. Run node scripts/progress-launcher.cjs --doctor from the plugin root. Prefer an existing interpreter via RELAYFORGE_PYTHON (executable path only); otherwise install Python from python.org. No software was installed.'}, 78);
    return;
  }
  if (doctor) {
    const check = spawnSync(selected.executable, ['-m', 'progress_panel.doctor'], {
      cwd: root, env, encoding: 'utf8', timeout: 5000, windowsHide: true,
      maxBuffer: 16384, shell: false,
    });
    let health;
    try { health = JSON.parse(check.stdout); } catch { /* Never echo arbitrary child output. */ }
    if (check.error || check.status !== 0 || !health || health.status !== 'runtime_ready') {
      report({status: 'package_check_failed', interpreter: selected, failures,
        phase: ['server_import', 'isolated_sqlite', 'tool_discovery', 'bundled_ui'].includes(health?.phase) ? health.phase : 'package_probe',
        message: 'Python works, but the package, bundled UI or isolated SQLite check failed. Repair/reinstall the plugin; do not reinstall Python without further evidence.'}, 70);
    } else report({...health, interpreter: selected, failures}, 0);
    return;
  }
  // Use the probed absolute executable; do not resolve an alias again or replay input on failure.
  const child = spawn(selected.executable, ['-u', '-m', 'progress_panel.server'], {
    cwd: root, env, stdio: 'inherit', windowsHide: true, shell: false,
  });
  child.on('error', () => report({status: 'server_spawn_failed', message:
    'The selected Python could not start the server. Run the environment doctor; check executable permissions and plugin files.'}, 70));
  child.on('exit', (code, signal) => {
    if (code !== 0) report({status: 'server_exited', message:
      `MCP server stopped (${signal || code}). Check host MCP logs and run --doctor; Python installation alone does not prove UI support.`}, code || 70);
  });
  for (const signal of ['SIGINT', 'SIGTERM']) process.on(signal, () => child.kill(signal));
}

main();
