import { MissionData, ExecutionReport, BenchmarkSuiteResult } from '../types';
import { getApiBaseUrl } from '../config';

const getBase = () => getApiBaseUrl();

export const api = {
  async getHealth() {
    const res = await fetch(`${getBase()}/health`);
    return res.json();
  },

  async createMission(payload: {
    task: string;
    start_url?: string;
    allowed_domains?: string[];
    require_approval_for_high_risk?: boolean;
    force_execution_method?: 'browser' | 'api' | 'auto';
    demo_mode?: boolean;
    open_browser_window?: boolean;
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
