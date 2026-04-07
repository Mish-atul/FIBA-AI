# FIBA AI — Frontend Integration Guide

Complete API reference for integrating the FIBA AI backend with a frontend application.

---

## Base URL

```
http://localhost:5000
```

## CORS

CORS is enabled on all endpoints. The backend runs entirely offline.

---

## API Endpoints Overview

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Web UI (HTML page) |
| POST | `/api/process` | Upload video + query for action detection |
| GET | `/api/status/<job_id>` | Poll job status and results |
| GET | `/api/stream/<job_id>` | SSE real-time progress stream |
| POST | `/api/sop/reference` | Upload reference video for SOP learning |
| POST | `/api/sop/validate` | Upload test video for SOP validation |
| GET | `/api/sop/status` | Check if classifier/reference is loaded |

---

## 1. Action Search API

### POST `/api/process`

Upload a video file with a natural language query to detect actions.

#### Request

**Content-Type:** `multipart/form-data`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `video` | File | Yes | Video file (any format supported by OpenCV) |
| `query` | string | Yes | Natural language query (e.g., "person picking up a cup") |

#### Example Request

```javascript
const formData = new FormData();
formData.append("video", videoFile);
formData.append("query", "person picking up a cup");

const response = await fetch("/api/process", {
  method: "POST",
  body: formData
});

const data = await response.json();
// { job_id: "abc123", status: "started" }
```

#### Response

```json
{
  "job_id": "abc12345",
  "status": "started"
}
```

#### Error Responses

| Status | Error Message |
|--------|--------------|
| 400 | `{"error": "No video file provided"}` |
| 400 | `{"error": "No query provided"}` |
| 400 | `{"error": "Empty filename"}` |

---

### GET `/api/status/<job_id>`

Poll for job status and retrieve results when complete.

#### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `job_id` | string | Job ID returned from `/api/process` |

#### Example Request

```javascript
const response = await fetch(`/api/status/${jobId}`);
const data = await response.json();
```

#### Response (In Progress)

```json
{
  "job_id": "abc12345",
  "progress": 45,
  "message": "Detecting objects...",
  "done": false,
  "result": null,
  "error": null
}
```

#### Response (Complete - Success)

```json
{
  "job_id": "abc12345",
  "progress": 100,
  "message": "Done!",
  "done": true,
  "result": {
    "action_detected": true,
    "action_label": "picking up",
    "action_category": "grasp",
    "confidence": 0.87,
    "timestamp_range": [120, 180],
    "evidence": "Hand approaching cup with grasp formation detected",
    "key_frames": ["base64_encoded_jpeg", "base64_encoded_jpeg"],
    "skeleton_frames": ["base64_encoded_jpeg"],
    "finger_trajectory": "base64_encoded_jpeg",
    "trajectory": "base64_encoded_jpeg",
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
    "query_info": {
      "raw": "person picking up a cup",
      "verb": "pick up",
      "category": "grasp",
      "object": "cup",
      "tool": null
    },
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
  },
  "error": null
}
```

#### Response (Complete - Error)

```json
{
  "job_id": "abc12345",
  "progress": 100,
  "message": "Error: Pipeline failed...",
  "done": true,
  "result": null,
  "error": "Pipeline failed: unable to detect hand"
}
```

---

### GET `/api/stream/<job_id>`

Server-Sent Events (SSE) endpoint for real-time progress updates.

#### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `job_id` | string | Job ID returned from `/api/process` |

#### Example Request

```javascript
const eventSource = new EventSource(`/api/stream/${jobId}`);

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(data.progress, data.message);
  
  if (data.done) {
    eventSource.close();
    // Fetch final results via /api/status/<job_id>
  }
};

eventSource.onerror = () => {
  eventSource.close();
  // Fall back to polling /api/status/<job_id>
};
```

#### SSE Data Format

```
data: {"progress": 15, "message": "Parsing query...", "done": false}

data: {"progress": 45, "message": "Detecting objects...", "done": false}

data: {"progress": 100, "message": "Done!", "done": true}
```

---

## 2. SOP Compliance API

### GET `/api/sop/status`

Check if the SOP classifier or reference is loaded.

#### Example Request

```javascript
const response = await fetch("/api/sop/status");
const data = await response.json();
```

#### Response

```json
{
  "has_reference": true,
  "has_classifier": true
}
```

| Field | Description |
|-------|-------------|
| `has_reference` | A reference video has been processed and learned |
| `has_classifier` | A trained classifier is available (from `train_sop_classifier.py`) |

---

### POST `/api/sop/reference`

Upload a reference video to learn the correct SOP sequence.

#### Request

**Content-Type:** `multipart/form-data`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `video` | File | Yes | Reference video showing correct procedure |

#### Example Request

```javascript
const formData = new FormData();
formData.append("video", referenceVideoFile);

const response = await fetch("/api/sop/reference", {
  method: "POST",
  body: formData
});

const data = await response.json();
// { job_id: "sop_ref_abc123", status: "started" }
```

#### Response

```json
{
  "job_id": "sop_ref_abc123",
  "status": "started"
}
```

#### Error Responses

| Status | Error Message |
|--------|--------------|
| 400 | `{"error": "No video file provided"}` |
| 400 | `{"error": "Empty filename"}` |

---

### POST `/api/sop/validate`

Upload a test video to validate against the learned SOP sequence.

#### Prerequisites

Either:
- A reference video has been uploaded via `/api/sop/reference`, OR
- A classifier has been trained via `train_sop_classifier.py`

#### Request

**Content-Type:** `multipart/form-data`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `video` | File | Yes | Test video to validate |

#### Example Request

```javascript
const formData = new FormData();
formData.append("video", testVideoFile);

const response = await fetch("/api/sop/validate", {
  method: "POST",
  body: formData
});

const data = await response.json();
// { job_id: "sop_val_abc123", status: "started" }
```

#### Response

```json
{
  "job_id": "sop_val_abc123",
  "status": "started"
}
```

#### Error Responses

| Status | Error Message |
|--------|--------------|
| 400 | `{"error": "No video file provided"}` |
| 400 | `{"error": "Empty filename"}` |
| 400 | `{"error": "No classifier trained and no reference loaded..."}` |

---

### Polling SOP Jobs

Use the same `/api/status/<job_id>` endpoint to poll SOP jobs.

#### SOP Reference Result

```json
{
  "job_id": "sop_ref_abc123",
  "progress": 100,
  "message": "Reference learned! (5 steps)",
  "done": true,
  "result": {
    "type": "sop_reference",
    "segments": [
      {
        "start_frame": 0,
        "end_frame": 45,
        "duration_frames": 45,
        "predicted_task": "pick_item",
        "task_name": "Pick Item from Shelf",
        "confidence": 0.95,
        "keyframe_b64": "base64_encoded_jpeg",
        "skeleton_b64": "base64_encoded_jpeg"
      }
    ],
    "sop_steps": [
      {
        "step_num": 1,
        "task_name": "Pick Item from Shelf",
        "description": "Reach and grasp item from shelf"
      }
    ],
    "total_frames": 450,
    "fps": 30.0,
    "processing_time_s": 8.5,
    "segment_count": 5
  }
}
```

#### SOP Validate Result

```json
{
  "job_id": "sop_val_abc123",
  "progress": 100,
  "message": "Done!",
  "done": true,
  "result": {
    "type": "sop_validate",
    "passed": false,
    "step_results": [
      {
        "position": 1,
        "expected_task": "pick_item",
        "detected_task": "pick_item",
        "similarity": 0.92,
        "is_correct": true,
        "keyframe_b64": "base64_encoded_jpeg",
        "skeleton_b64": "base64_encoded_jpeg"
      },
      {
        "position": 2,
        "expected_task": "scan_barcode",
        "detected_task": "place_item",
        "similarity": 0.34,
        "is_correct": false,
        "keyframe_b64": "base64_encoded_jpeg",
        "skeleton_b64": "base64_encoded_jpeg"
      }
    ],
    "summary": "2 steps processed. Sequence violation detected at position 2.",
    "total_frames": 320,
    "fps": 30.0,
    "processing_time_s": 6.2
  }
}
```

---

## 3. Frontend Implementation Patterns

### Progress Polling with SSE (Recommended)

```javascript
async function processVideo(videoFile, query) {
  const formData = new FormData();
  formData.append("video", videoFile);
  formData.append("query", query);

  // Start job
  const response = await fetch("/api/process", {
    method: "POST",
    body: formData
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error);
  }
  
  const { job_id } = await response.json();
  
  // Connect to SSE stream
  return new Promise((resolve, reject) => {
    const eventSource = new EventSource(`/api/stream/${job_id}`);
    
    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      if (data.error) {
        eventSource.close();
        reject(new Error(data.error));
        return;
      }
      
      // Update progress UI
      updateProgress(data.progress, data.message);
      
      if (data.done) {
        eventSource.close();
        // Fetch full results
        fetch(`/api/status/${job_id}`)
          .then(r => r.json())
          .then(resolve)
          .catch(reject);
      }
    };
    
    eventSource.onerror = () => {
      eventSource.close();
      // Fall back to polling
      pollWithInterval(job_id).then(resolve).catch(reject);
    };
  });
}

// Fallback polling
async function pollWithInterval(jobId) {
  return new Promise((resolve, reject) => {
    const interval = setInterval(async () => {
      try {
        const response = await fetch(`/api/status/${jobId}`);
        const data = await response.json();
        
        updateProgress(data.progress, data.message);
        
        if (data.done) {
          clearInterval(interval);
          if (data.error) reject(new Error(data.error));
          else resolve(data);
        }
      } catch (err) {
        clearInterval(interval);
        reject(err);
      }
    }, 800);
  });
}
```

### File Upload with Drag & Drop

```javascript
const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');

// Click to browse
dropZone.addEventListener('click', () => fileInput.click());

fileInput.addEventListener('change', (e) => {
  if (e.target.files[0]) {
    handleFile(e.target.files[0]);
  }
});

// Drag & drop
dropZone.addEventListener('dragover', (e) => {
  e.preventDefault();
  dropZone.classList.add('drag-over');
});

dropZone.addEventListener('dragleave', () => {
  dropZone.classList.remove('drag-over');
});

dropZone.addEventListener('drop', (e) => {
  e.preventDefault();
  dropZone.classList.remove('drag-over');
  
  if (e.dataTransfer.files[0]) {
    handleFile(e.dataTransfer.files[0]);
  }
});

function handleFile(file) {
  if (!file.type.startsWith('video/')) {
    alert('Please select a video file');
    return;
  }
  // Store for upload
  selectedFile = file;
}
```

### Displaying Base64 Images

```javascript
// Key frames
result.key_frames.forEach((b64, index) => {
  const img = document.createElement('img');
  img.src = `data:image/jpeg;base64,${b64}`;
  img.alt = `Key frame ${index + 1}`;
  container.appendChild(img);
});

// Skeleton frames
result.skeleton_frames.forEach((b64) => {
  const img = document.createElement('img');
  img.src = `data:image/jpeg;base64,${b64}`;
  container.appendChild(img);
});

// Trajectory visualizations
if (result.finger_trajectory) {
  document.getElementById('finger-traj').src = 
    `data:image/jpeg;base64,${result.finger_trajectory}`;
}

if (result.trajectory) {
  document.getElementById('trajectory').src = 
    `data:image/jpeg;base64,${result.trajectory}`;
}
```

### SOP Validation Workflow

```javascript
// Check SOP status on load
async function checkSOPStatus() {
  const response = await fetch('/api/sop/status');
  const { has_reference, has_classifier } = await response.json();
  
  if (has_classifier) {
    // Can validate without reference
    showMessage('Trained classifier ready');
  } else if (has_reference) {
    showMessage('Reference loaded');
  } else {
    showMessage('Upload reference video first');
  }
}

// Upload reference
async function uploadReference(videoFile) {
  const formData = new FormData();
  formData.append('video', videoFile);
  
  const response = await fetch('/api/sop/reference', {
    method: 'POST',
    body: formData
  });
  
  const { job_id } = await response.json();
  return pollJob(job_id); // Use polling function from above
}

// Validate test video
async function validateVideo(testVideoFile) {
  const formData = new FormData();
  formData.append('video', testVideoFile);
  
  const response = await fetch('/api/sop/validate', {
    method: 'POST',
    body: formData
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error);
  }
  
  const { job_id } = await response.json();
  const result = await pollJob(job_id);
  
  // Display validation results
  displayValidationResults(result.result);
}

function displayValidationResults(result) {
  // Show pass/fail banner
  const passed = result.passed;
  document.getElementById('verdict').textContent = 
    passed ? 'SOP COMPLIANCE PASSED' : 'SOP VIOLATION DETECTED';
  
  // Show step-by-step results
  result.step_results.forEach(step => {
    console.log(`Step ${step.position}: ${step.is_correct ? '✅' : '❌'}`);
    console.log(`  Expected: ${step.expected_task}`);
    console.log(`  Detected: ${step.detected_task}`);
    console.log(`  Similarity: ${Math.round(step.similarity * 100)}%`);
  });
  
  // Show summary
  console.log(result.summary);
}
```

---

## 4. Data Types Reference

### Job Status Object

```typescript
interface JobStatus {
  job_id: string;
  progress: number;      // 0-100
  message: string;         // Human-readable status
  done: boolean;          // true when complete
  result: ActionResult | SOPReferenceResult | SOPValidateResult | null;
  error: string | null;
}
```

### Action Result Object

```typescript
interface ActionResult {
  action_detected: boolean;
  action_label: string;
  action_category: string;
  confidence: number;           // 0.0 - 1.0
  timestamp_range: [number, number];  // [start_frame, end_frame]
  evidence: string;
  key_frames: string[];          // Base64 JPEGs
  skeleton_frames: string[];   // Base64 JPEGs
  finger_trajectory: string;     // Base64 JPEG
  trajectory: string;            // Base64 JPEG
  motion_summary: MotionSummary;
  query_info: QueryInfo;
  total_frames: number;
  fps: number;
  processing_time_s: number;
  action_description: string;
  edge_stats: EdgeStats;
}

interface MotionSummary {
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

interface QueryInfo {
  raw: string;
  verb: string;
  category: string;
  object: string;
  tool: string | null;
}

interface EdgeStats {
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
```

### SOP Segment Object

```typescript
interface SOPSegment {
  start_frame: number;
  end_frame: number;
  duration_frames: number;
  predicted_task: string;
  task_name: string;
  confidence: number;
  keyframe_b64: string;
  skeleton_b64: string;
}

interface SOPStep {
  step_num: number;
  task_name: string;
  description: string;
}
```

### SOP Validate Step Result

```typescript
interface SOPStepResult {
  position: number;
  expected_task: string;
  detected_task: string;
  similarity: number;      // 0.0 - 1.0
  is_correct: boolean;
  keyframe_b64: string;
  skeleton_b64: string;
}
```

---

## 5. Pipeline Stages

When polling progress, these are the typical stage ranges:

| Stage | Progress Range | Description |
|-------|---------------|-------------|
| Parse Query | 0-15% | Parse natural language query |
| Detect | 15-45% | Object and hand detection |
| Track | 45-72% | Object tracking across frames |
| Infer | 72-85% | Action inference |
| Render | 85-100% | Generate visualizations |

---

## 6. Error Handling

Common errors and recommended handling:

| Error | Cause | Recommendation |
|-------|-------|----------------|
| `No video file provided` | Missing file in request | Show file selection prompt |
| `No query provided` | Empty query string | Show query input validation |
| `Job not found` | Invalid/expired job ID | Restart the process |
| `No classifier trained...` | SOP validation without setup | Prompt user to upload reference first |

---

## 7. Browser Compatibility

- **SSE Support**: All modern browsers support `EventSource`
- **Base64 Images**: All modern browsers support data URIs
- **File API**: Required for drag & drop, supported in all modern browsers
- **CORS**: Automatically handled by backend

---

## 8. Running the Backend

```bash
# From the web_app directory
cd web_app

# Install dependencies
pip install flask flask-cors

# Run the server
python app.py

# Server runs on http://localhost:5000
```

---

## 9. Complete Example: React Component

```jsx
import { useState, useCallback } from 'react';

function ActionSearch() {
  const [file, setFile] = useState(null);
  const [query, setQuery] = useState('');
  const [progress, setProgress] = useState(0);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = useCallback(async () => {
    if (!file || !query) return;
    
    setLoading(true);
    setProgress(0);
    
    const formData = new FormData();
    formData.append('video', file);
    formData.append('query', query);
    
    try {
      const response = await fetch('/api/process', {
        method: 'POST',
        body: formData
      });
      
      if (!response.ok) throw new Error(await response.text());
      
      const { job_id } = await response.json();
      
      // Connect to SSE
      const eventSource = new EventSource(`/api/stream/${job_id}`);
      
      eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data);
        setProgress(data.progress);
        
        if (data.done) {
          eventSource.close();
          fetch(`/api/status/${job_id}`)
            .then(r => r.json())
            .then(d => {
              setResult(d.result);
              setLoading(false);
            });
        }
      };
    } catch (err) {
      console.error(err);
      setLoading(false);
    }
  }, [file, query]);

  return (
    <div>
      <input
        type="file"
        accept="video/*"
        onChange={(e) => setFile(e.target.files[0])}
      />
      <input
        type="text"
        placeholder="Enter action query..."
        value={query}
        onChange={(e) => setQuery(e.target.value)}
      />
      <button onClick={handleSubmit} disabled={loading}>
        {loading ? `Processing (${progress}%)` : 'Analyze'}
      </button>
      
      {result && (
        <div>
          <h3>Action: {result.action_label}</h3>
          <p>Confidence: {Math.round(result.confidence * 100)}%</p>
          <p>Detected: {result.action_detected ? 'Yes' : 'No'}</p>
          {result.key_frames.map((frame, i) => (
            <img
              key={i}
              src={`data:image/jpeg;base64,${frame}`}
              alt={`Frame ${i + 1}`}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export default ActionSearch;
```
