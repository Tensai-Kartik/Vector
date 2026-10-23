export type MissionStatus =
  | 'queued'
  | 'inspecting'
  | 'planning'
  | 'awaiting_approval'
  | 'running'
  | 'validating'
  | 'retrying'
  | 'completed'
  | 'failed'
  | 'cancelled'
  | 'needs_input';

export type StepStatus =
  | 'pending'
  | 'validating'
  | 'running'
  | 'verifying'
  | 'retrying'
  | 'completed'
  | 'failed'
  | 'rejected'
  | 'skipped'
  | 'awaiting_approval';

export type EventCategory =
  | 'system'
  | 'browser'
  | 'api'
  | 'guardrail'
  | 'recovery'
  | 'verification'
  | 'artifact';

export interface MissionEvent {
  id: string;
  mission_id: string;
  step_id?: string;
  event_type: string;
  category: EventCategory;
  message: string;
  details: Record<string, any>;
  timestamp: string;
}

export interface MissionStepState {
  step_id: string;
  action_type: string;
  intent: string;
  target_description?: string;
  target_locator_value?: string;
  input_value?: string;
  status: StepStatus;
  execution_method?: 'browser' | 'api';
  validation_status?: string;
  validation_message?: string;
  verification_status?: string;
  verification_evidence?: Record<string, any>;
  retry_count: number;
  start_time?: string;
  end_time?: string;
  error_message?: string;
}

export interface ArtifactMetadata {
  artifact_id: string;
  filename: string;
  file_path: string;
  file_size_bytes: number;
  content_type: string;
  sha256_hash?: string;
  created_at: string;
}

export interface ExecutionReport {
  mission_id: string;
  task: string;
  verdict: string;
  is_verified: boolean;
  verification_summary: string;
  total_steps: number;
  completed_steps: number;
  failed_steps: number;
  rejected_steps: number;
  api_steps_count: number;
  browser_steps_count: number;
  retry_count: number;
  replanning_count: number;
  duration_seconds: number;
  start_time: string;
  end_time: string;
  extracted_records: any[];
  artifacts: ArtifactMetadata[];
  guardrail_rejections: any[];
}

export interface MissionData {
  id: string;
  task: string;
  status: MissionStatus;
  start_url?: string;
  allowed_domains: string[];
  steps: MissionStepState[];
  events: MissionEvent[];
  extracted_data: any[];
  artifacts: ArtifactMetadata[];
  created_at: string;
  summary_report?: ExecutionReport;
  approval_granted?: boolean;
}

export interface BenchmarkItem {
  id: string;
  name: string;
  category: string;
  passed: boolean;
  duration_ms: number;
  verified: boolean;
}

export interface BenchmarkSuiteResult {
  status: string;
  benchmark_timestamp: number;
  total_tasks: number;
  task_success_rate: number;
  postcondition_verification_rate: number;
  false_action_rate: number;
  guardrail_rejection_accuracy: number;
  recovery_success_rate: number;
  api_route_selection_accuracy: number;
  median_execution_duration_ms: number;
  retries_per_task_average: number;
  benchmarks: BenchmarkItem[];
}
