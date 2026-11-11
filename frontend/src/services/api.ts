import { MissionData, ExecutionReport, BenchmarkSuiteResult } from '../types';
import { getApiBaseUrl } from '../config';

const getBase = () => getApiBaseUrl();

export const api = {
  async getHealth() {
    const res = await fetch(`${getBase()}/health`, { cache: 'no-store' });
    return res.json();
  },

  async ping(): Promise<{ status: string; timestamp: number; active: boolean; uptime_seconds?: number }> {
    const res = await fetch(`${getBase()}/ping`, { cache: 'no-store' });
    if (!res.ok) throw new Error('Ping failed');
    return res.json();
  },

  async wakeBackend(): Promise<any> {
    // Fast wake-up attempt on /ping with fallback to /health
    try {
      const res = await fetch(`${getBase()}/ping`, { method: 'GET', cache: 'no-store' });
      if (res.ok) return await res.json();
    } catch {
      // Fallback probe
    }
    const res = await fetch(`${getBase()}/health`, { method: 'GET', cache: 'no-store' });
    return await res.json();
  },

  async resolveLaunch(task: string): Promise<{
    should_open_tab: boolean;
    direct_tab_sufficient?: boolean;
    launch_url?: string;
    title?: string;
    kind?: string;
    installed_locally?: boolean;
    app_name?: string;
  }> {
    const res = await fetch(`${getBase()}/resolve-launch`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ task }),
    });
    if (!res.ok) return { should_open_tab: false };
    return res.json();
  },

  async createMission(payload: {
    task: string;
    start_url?: string;
    allowed_domains?: string[];
    require_approval_for_high_risk?: boolean;
    force_execution_method?: 'browser' | 'api' | 'auto';
    planner_mode?: 'deterministic' | 'gemini';
    demo_mode?: boolean;
    open_browser_window?: boolean;
    client_handled_url?: string;
  }): Promise<{ mission_id: string; status: string }> {
    const res = await fetch(`${getBase()}/missions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async getMission(id: string): Promise<MissionData> {
    const res = await fetch(`${getBase()}/missions/${id}`);
    if (!res.ok) throw new Error('Mission not found');
    return res.json();
  },

  async listMissions(): Promise<MissionData[]> {
    const res = await fetch(`${getBase()}/missions`);
    return res.json();
  },

  async approveMission(id: string): Promise<void> {
    await fetch(`${getBase()}/missions/${id}/approve`, { method: 'POST' });
  },

  async cancelMission(id: string): Promise<void> {
    await fetch(`${getBase()}/missions/${id}/cancel`, { method: 'POST' });
  },

  async killMission(id: string): Promise<void> {
    await fetch(`${getBase()}/missions/${id}/kill`, { method: 'POST' });
  },

  async killAllMissions(): Promise<void> {
    await fetch(`${getBase()}/missions/kill-all`, { method: 'POST' });
  },

  async getReport(id: string): Promise<ExecutionReport> {
    const res = await fetch(`${getBase()}/missions/${id}/report`);
    if (!res.ok) throw new Error('Report not found');
    return res.json();
  },

  async getSettings() {
    const res = await fetch(`${getBase()}/settings`);
    return res.json();
  },

  async updateSettings(settings: any) {
    const res = await fetch(`${getBase()}/settings`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(settings),
    });
    return res.json();
  },

  async runBenchmarks(): Promise<BenchmarkSuiteResult> {
    const res = await fetch(`${getBase()}/benchmark/run`, { method: 'POST' });
    return res.json();
  },

  async launchFile(filePath: string): Promise<any> {
    const res = await fetch(`${getBase()}/system/launch-file`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path: filePath }),
    });
    return res.json();
  },
};
