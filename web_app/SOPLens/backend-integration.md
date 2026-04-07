# SOPLens — Backend Integration Guide

Connect your Flask backend to the SOPLens frontend.

---

## Setup

### 1. Start the Flask backend

```bash
cd web_app
pip install flask flask-cors
python app.py
# Runs on http://localhost:5000
```

### 2. Start the SOPLens frontend

```bash
pnpm --filter @workspace/fiba-ai run dev
# Runs on http://localhost:<PORT>
```

The Vite dev server proxies all `/api` requests to `http://localhost:5000`, so no CORS issues during development.

### 3. Production

Set the `VITE_API_BASE` environment variable to your backend's public URL if not using localhost.

---

## API Reference

### Base URL

```
http://localhost:5000
```

All frontend calls use `/api/...` which Vite proxies to the above.

---

## Action Detection

### POST `/api/process`

Upload a video and natural language query. Returns a `job_id`.

**Request** — `multipart/form-data`

| Field   | Type   | Required | Description                                         |
|---------|--------|----------|-----------------------------------------------------|
| `video` | File   | Yes      | Video file (any format supported by OpenCV)         |
| `query` | string | Yes      | Natural language description, e.g. "picking up cup" |

**Response**

```json
{ "job_id": "abc12345", "status": "started" }
```

---

### GET `/api/status/<job_id>`

Poll for progress and retrieve final results.

**Response — in progress**

```json
{ "job_id": "abc12345", "progress": 45, "message": "Detecting objects...", "done": false, "result": null, "error": null }
```

**Response — complete (success)**

```json
{
  "job_id": "abc12345",
  "progress": 100,
  "done": true,
  "result": {
    "action_detected": true,
    "action_label": "picking up",
    "action_category": "grasp",
    "confidence": 0.87,
    "timestamp_range": [120, 180],
    "evidence": "Hand approaching cup with grasp formation detected",
    "key_frames": ["<base64_jpeg>", "..."],
    "skeleton_frames": ["<base64_jpeg>"],
    "finger_trajectory": "<base64_jpeg>",
    "trajectory": "<base64_jpeg>",
    "motion_summary": {
      "rotation_deg": 15.5,
      "displacement_px": 245.3,
      "contact_events": 1,
      "area_change_ratio": 1.2,
      "state_change": "open_to_closed",
      "vertical_motion": "upward",
      "motion_speed_px_per_frame": 12.5,
      "contact_frequency": "single",
      "approach_score": 0.92,
      "grasp_change": "formed",
      "area_growth_trend": "increasing"
    },
    "query_info": { "raw": "...", "verb": "pick up", "category": "grasp", "object": "cup", "tool": null },
    "total_frames": 300,
    "fps": 30.0,
    "processing_time_s": 4.5,
    "action_description": "The hand moves toward the cup, forms a grasp, and lifts it.",
    "edge_stats": {
      "edge_ready": true,
      "zero_shot": true,
      "pipeline_latency_s": 4.5,
      "frame_processing_s": 0.015,
      "inference_latency_s": 0.003,
      "effective_fps": 66.7,
      "processed_frames": 150,
      "total_frames": 300,
      "frame_skip": 2,
      "resolution": "640x480",
      "models_used": "yolov8n, mobilenet"
    }
  }
}
```

---

### GET `/api/stream/<job_id>`

Server-Sent Events (SSE) stream for real-time progress. The frontend connects here first, then falls back to polling on error.

**Event format**

```
data: {"progress": 15, "message": "Parsing query...", "done": false}
data: {"progress": 100, "message": "Done!", "done": true}
```

**Frontend pattern**

```javascript
const es = new EventSource(`/api/stream/${jobId}`);
es.onmessage = ({ data }) => {
  const { progress, message, done } = JSON.parse(data);
  if (done) {
    es.close();
    // fetch full result from /api/status/<job_id>
  }
};
es.onerror = () => { es.close(); /* fall back to polling */ };
```

---

## SOP Compliance

### GET `/api/sop/status`

Check if a reference or trained classifier is available.

```json
{ "has_reference": true, "has_classifier": false }
```

---

### POST `/api/sop/reference`

Upload the reference (correct procedure) video. Returns a `job_id`. Poll `/api/status/<job_id>`.

**Request** — `multipart/form-data`: `video` (File, required)

**Final result shape**

```json
{
  "type": "sop_reference",
  "segment_count": 5,
  "segments": [
    {
      "start_frame": 0, "end_frame": 45, "duration_frames": 45,
      "predicted_task": "pick_item", "task_name": "Pick Item from Shelf",
      "confidence": 0.95, "keyframe_b64": "<base64>", "skeleton_b64": "<base64>"
    }
  ],
  "sop_steps": [{ "step_num": 1, "task_name": "Pick Item from Shelf", "description": "..." }],
  "total_frames": 450, "fps": 30.0, "processing_time_s": 8.5
}
```

---

### POST `/api/sop/validate`

Upload a test video to validate against the learned reference. Returns a `job_id`. Poll `/api/status/<job_id>`.

**Prerequisite**: A reference must be loaded (via `/api/sop/reference`) or a classifier trained offline.

**Request** — `multipart/form-data`: `video` (File, required)

**Final result shape**

```json
{
  "type": "sop_validate",
  "passed": false,
  "step_results": [
    {
      "position": 1, "expected_task": "pick_item", "detected_task": "pick_item",
      "similarity": 0.92, "is_correct": true,
      "keyframe_b64": "<base64>", "skeleton_b64": "<base64>"
    },
    {
      "position": 2, "expected_task": "scan_barcode", "detected_task": "place_item",
      "similarity": 0.34, "is_correct": false,
      "keyframe_b64": "<base64>", "skeleton_b64": "<base64>"
    }
  ],
  "summary": "2 steps processed. Sequence violation at position 2.",
  "total_frames": 320, "fps": 30.0, "processing_time_s": 6.2
}
```

---

## Processing Pipeline Stages

| Stage       | Progress | Description                    |
|-------------|----------|--------------------------------|
| Parse Query | 0–15%    | Natural language parsing       |
| Detect      | 15–45%   | Object & hand detection        |
| Track       | 45–72%   | Cross-frame tracking           |
| Infer       | 72–85%   | Action inference               |
| Render      | 85–100%  | Visualization generation       |

---

## Error Handling

| Error message                       | Cause                          | Recommended action                      |
|-------------------------------------|--------------------------------|-----------------------------------------|
| `No video file provided`            | Missing file in request        | Show file selection prompt              |
| `No query provided`                 | Empty query string             | Show validation message                 |
| `Job not found`                     | Invalid or expired job ID      | Restart the process                     |
| `No classifier trained and no reference loaded` | SOP validate with no setup | Prompt user to upload reference first |

---

## TypeScript Types

```typescript
interface JobStatus {
  job_id: string;
  progress: number;        // 0–100
  message: string;
  done: boolean;
  result: ActionResult | SOPReferenceResult | SOPValidateResult | null;
  error: string | null;
}

interface ActionResult {
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

interface SOPReferenceResult {
  type: "sop_reference";
  segments: SOPSegment[];
  sop_steps: SOPStep[];
  segment_count: number;
  total_frames: number;
  fps: number;
  processing_time_s: number;
}

interface SOPValidateResult {
  type: "sop_validate";
  passed: boolean;
  step_results: SOPStepResult[];
  summary: string;
  total_frames: number;
  fps: number;
  processing_time_s: number;
}

interface SOPStepResult {
  position: number;
  expected_task: string;
  detected_task: string;
  similarity: number;
  is_correct: boolean;
  keyframe_b64: string;
  skeleton_b64: string;
}
```

---

## Vite Proxy Config (already configured)

```typescript
// vite.config.ts
server: {
  proxy: {
    "/api": {
      target: "http://localhost:5000",
      changeOrigin: true,
    },
  },
}
```

No extra setup needed — all `/api` calls from the frontend hit the Flask backend automatically.
