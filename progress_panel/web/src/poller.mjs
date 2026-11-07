const statuses = new Set(['running', 'waiting', 'completed', 'blocked', 'cancelled']);
const stepStatuses = new Set(['pending', 'active', 'done', 'blocked', 'skipped']);
export const terminal = status => ['completed', 'blocked', 'cancelled'].includes(status);

export function validSnapshot(value) {
  return value?.schema_version === 1 && value.source === 'agent_declared'
    && /^[a-f0-9-]{36}$/.test(value.run_id) && Number.isInteger(value.revision)
    && value.revision > 0 && statuses.has(value.status)
    && typeof value.title === 'string' && typeof value.summary === 'string'
    && Array.isArray(value.steps) && value.steps.length > 0 && value.steps.length <= 12
    && value.steps.every(step => typeof step.label === 'string' && stepStatuses.has(step.status));
}

export class PanelPoller {
  constructor({callTool, onSnapshot, onState,
    schedule = (callback, delay) => setTimeout(callback, delay),
    cancel = timer => clearTimeout(timer)}) {
    Object.assign(this, {callTool, onSnapshot, onState, schedule, cancel});
    this.runId = null;
    this.snapshot = null;
    this.timer = null;
    this.ready = false;
    this.paused = false;
    this.closed = false;
    this.generation = 0;
    this.errors = 0;
  }

  bind(value, {replace = false} = {}) {
    if (!validSnapshot(value) || this.closed) return false;
    if (this.runId && value.run_id !== this.runId) {
      if (!replace) return false;
      // Hosts may reuse the resource's panel for a new explicit render result.
      // Old reads remain fenced by generation and can never change the new task.
      this.generation += 1;
      this.cancel(this.timer);
      this.timer = null;
      this.snapshot = null;
      this.errors = 0;
      this.paused = false;
    }
    if (this.snapshot && value.revision < this.snapshot.revision) return false;
    this.runId = value.run_id;
    this.snapshot = value;
    if (terminal(value.status)) {
      this.cancel(this.timer);
      this.timer = null;
      this.generation += 1;
    }
    this.onSnapshot(value);
    if (this.ready && !this.timer && !this.inFlight && !this.paused && !terminal(value.status)) this.poll();
    return true;
  }

  connected() {
    this.ready = true;
    if (this.runId && !this.paused && !terminal(this.snapshot.status)) this.poll();
  }

  pause() {
    this.paused = true;
    this.generation += 1;
    this.cancel(this.timer);
    this.timer = null;
    this.onState('paused');
  }

  resume() {
    if (this.closed) return;
    this.paused = false;
    if (this.ready && this.runId && !this.inFlight && !terminal(this.snapshot.status)) this.poll();
  }

  close() {
    this.pause();
    this.closed = true;
  }

  async poll() {
    if (!this.ready || this.paused || this.closed || this.inFlight || !this.runId) return;
    const generation = this.generation;
    this.inFlight = true;
    this.timer = null;
    try {
      const result = await this.callTool({name: 'read_progress', arguments: {run_id: this.runId}});
      if (generation !== this.generation || this.closed) return;
      const next = result.structuredContent;
      if (result.isError || !validSnapshot(next) || next.run_id !== this.runId) throw new Error('invalid_snapshot');
      if (next.revision < this.snapshot.revision) throw new Error('stale_snapshot');
      this.snapshot = next;
      this.errors = 0;
      this.onSnapshot(next);
      this.onState('synced');
    } catch {
      if (generation === this.generation && !this.closed) {
        this.errors += 1;
        this.onState('disconnected');
      }
    } finally {
      this.inFlight = false;
      if (!this.closed && !this.paused && this.ready && this.snapshot && !terminal(this.snapshot.status)) {
        this.timer = this.schedule(() => this.poll(), Math.min(30000, 2000 * 2 ** Math.min(this.errors, 4)));
      }
    }
  }
}
