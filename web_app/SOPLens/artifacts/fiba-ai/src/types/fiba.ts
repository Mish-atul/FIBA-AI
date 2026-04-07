export interface MotionSummary {
  rotation_deg: number;
  displacement_px: number;
  contact_events: number;
  area_change_ratio: number;
  state_change: string;
  vertical_motion: string;
  motion_speed_px_per_frame: number;
  contact_frequency: string;
  approach_score: number;
  grasp_change: string;
  area_growth_trend: string;
}

export interface QueryInfo {
  raw: string;
  verb: string;
  category: string;
  object: string;
  tool: string | null;
}

export interface EdgeStats {
  edge_ready: boolean;
  zero_shot: boolean;
  pipeline_latency_s: number;
  frame_processing_s: number;
  inference_latency_s: number;
  effective_fps: number;
  processed_frames: number;
  total_frames: number;
  frame_skip: number;
  resolution: string;
  models_used: string;
}

export interface ActionResult {
  action_detected: boolean;
  action_label: string;
  action_category: string;
  confidence: number;
  timestamp_range: [number, number];
  evidence: string;
  key_frames: string[];
  skeleton_frames: string[];
  finger_trajectory: string;
  trajectory: string;
  motion_summary: MotionSummary;
  query_info: QueryInfo;
  total_frames: number;
  fps: number;
  processing_time_s: number;
  action_description: string;
  edge_stats: EdgeStats;
}

export interface SOPSegment {
  start_frame: number;
  end_frame: number;
  duration_frames: number;
  predicted_task: string;
  task_name: string;
  confidence: number;
  keyframe_b64: string;
  skeleton_b64: string;
}

export interface SOPStep {
  step_num: number;
  task_name: string;
  description: string;
}

export interface SOPReferenceResult {
  type: 'sop_reference';
  segments: SOPSegment[];
  sop_steps: SOPStep[];
  total_frames: number;
  fps: number;
  processing_time_s: number;
  segment_count: number;
}

export interface SOPStepResult {
  position: number;
  expected_task: string;
  detected_task: string;
  similarity: number;
  is_correct: boolean;
  keyframe_b64: string;
  skeleton_b64: string;
}

export interface SOPValidateResult {
  type: 'sop_validate';
  passed: boolean;
  step_results: SOPStepResult[];
  summary: string;
  total_frames: number;
  fps: number;
  processing_time_s: number;
}

export interface JobStatus {
  job_id: string;
  progress: number;
  message: string;
  done: boolean;
  result: ActionResult | SOPReferenceResult | SOPValidateResult | null;
  error: string | null;
}

export interface SOPStatus {
  has_reference: boolean;
  has_classifier: boolean;
}
