# 🔗 Common Integration Guide
## Atul + Tanishk + Yash — FIBA AI
### MIT Bangalore Hitachi Hackathon

---

## Project Structure

```
fiba_ai/
├── app.py                          ← Yash: Flask server
├── requirements.txt                ← All deps
├── pipeline/
│   ├── __init__.py
│   ├── query_parser.py             ← Atul: NL query parsing
│   ├── hand_detector.py            ← Atul: MediaPipe hand tracking
│   ├── object_detector.py          ← Atul: YOLOv8n + text grounding
│   ├── tracker.py                  ← Tanishk: IoU + Kalman tracking
│   ├── motion_engine.py            ← Tanishk: Motion feature extraction
│   ├── action_inferencer.py        ← Tanishk: Rule-based action inference
│   ├── segmentor.py                ← Tanishk: MobileSAM / GrabCut segmentation
│   └── integrator.py               ← Yash: Full pipeline orchestration
├── templates/
│   └── index.html                  ← Yash: Web UI
├── static/
│   ├── style.css                   ← Yash: Styles
│   └── app.js                      ← Yash: Frontend logic
├── weights/
│   └── mobile_sam.pt               ← Download separately (optional)
├── uploads/                        ← Auto-created: uploaded videos
└── outputs/                        ← Auto-created: result clips
```

---

## Interface Contracts Between Modules

### Atul → Tanishk

```python
# hand_detector.py exports:
class HandDetectionResult:
    detected: bool
    hand_bbox: Optional[List[float]]    # [x1, y1, x2, y2]
    wrist_pos: Optional[Tuple[float, float]]
    landmarks: Optional[List[List[float]]]   # 21 x [x,y,z]
    handedness: str
    confidence: float

# object_detector.py exports:
class ObjectDetectionResult:
    detected: bool
    object_bbox: Optional[List[float]]  # [x1, y1, x2, y2]
    object_label: Optional[str]
    detection_confidence: float
    grounding_score: float
    center: Optional[Tuple[float, float]]
    area: float
```

### Tanishk → Yash

```python
# tracker.py exports:
class TrackResult:
    tracked: bool
    bbox: Optional[List[float]]
    center: Optional[Tuple[float, float]]
    area: float
    tracking_confidence: float
    trajectory: List[Tuple[float, float]]
    bbox_history: List[List[float]]
    area_history: List[float]

# action_inferencer.py exports:
class ActionResult:
    action_label: str
    is_detected: bool
    confidence: float
    evidence: str
    timestamp_range: Tuple[float, float]
    motion_summary: dict

# segmentor.py exports:
def encode_frame_b64(frame) -> str         # base64 JPEG string
def draw_annotated_frame(...) -> np.ndarray
def draw_trajectory(...) -> np.ndarray
```

### Yash's Integrator (Final Output)

```python
class PipelineResult:
    success: bool
    action_detected: bool
    action_label: str
    confidence: float
    evidence: str
    timestamp_range: tuple
    key_frames_b64: List[str]     # 3 base64-encoded annotated frames
    trajectory_b64: str            # base64-encoded trajectory image
    motion_summary: dict
    query_info: dict
```

---

## Setup Instructions (Run ONCE Together)

```bash
# 1. Clone/create the project folder
mkdir fiba_ai && cd fiba_ai

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate          # Linux/Mac
# venv\Scripts\activate           # Windows

# 3. Install all dependencies
pip install -r requirements.txt

# 4. Download YOLOv8n weights (auto on first run, but pre-download for offline)
python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"

# 5. (Optional) Download MobileSAM weights
mkdir weights
wget -O weights/mobile_sam.pt https://github.com/ChaoningZhang/MobileSAM/raw/master/weights/mobile_sam.pt

# 6. Start the server
python app.py
# → Open http://localhost:5000
```

---

## `requirements.txt`

```
flask>=2.3.0
flask-cors>=4.0.0
opencv-python-headless>=4.8.0
mediapipe>=0.10.0
ultralytics>=8.0.0
numpy>=1.24.0
scipy>=1.11.0
filterpy>=1.4.5
Pillow>=9.0.0
# Optional (MobileSAM):
# mobile-sam
# torch>=2.0.0
# torchvision>=0.15.0
```

---

## Integration Testing Protocol

### Step 1: Test each module independently
```bash
# Atul tests his modules:
python pipeline/query_parser.py          # should parse 5 queries
python pipeline/hand_detector.py         # should open webcam, show hand boxes
python pipeline/object_detector.py cup  # should detect cups

# Tanishk tests his modules:
python -c "from pipeline.tracker import ObjectTracker; print('Tracker OK')"
python -c "from pipeline.motion_engine import MotionEngine; print('Motion OK')"
python -c "from pipeline.segmentor import MobileSAMSegmentor; print('SAM OK')"

# Yash tests integration:
python -c "from pipeline.integrator import FIBAPipeline; print('Pipeline OK')"
```

### Step 2: Run on a test video
```bash
# Record a 10-second clip of yourself cutting something
# Then test:
python -c "
from pipeline.integrator import FIBAPipeline
p = FIBAPipeline()
result = p.run('test_video.mp4', 'cutting onion')
print('Detected:', result.action_detected)
print('Confidence:', result.confidence)
print('Evidence:', result.evidence)
"
```

### Step 3: Full stack test
```bash
python app.py
# → Open browser at http://localhost:5000
# → Upload test video
# → Type 'cutting onion'
# → Click Process
```

---

## Division of Work Summary

| Person | Owns | Files |
|--------|------|-------|
| **Atul** | Query Parser + Hand Detector + Object Detector | `pipeline/query_parser.py`, `pipeline/hand_detector.py`, `pipeline/object_detector.py` |
| **Tanishk** | Tracker + Motion Engine + Action Inferencer + Segmentor | `pipeline/tracker.py`, `pipeline/motion_engine.py`, `pipeline/action_inferencer.py`, `pipeline/segmentor.py` |
| **Yash** | Integrator + Web App + Frontend | `pipeline/integrator.py`, `app.py`, `templates/index.html`, `static/` |

---

## Claude Opus Integration Instructions
When you feed each file to Claude Opus in the IDE:

1. Feed `design_atul.md` → Claude Opus generates `query_parser.py`, `hand_detector.py`, `object_detector.py`
2. Feed `design_tanishk.md` → Claude Opus generates `tracker.py`, `motion_engine.py`, `action_inferencer.py`, `segmentor.py`
3. Feed `design_yash.md` → Claude Opus generates `integrator.py`, `app.py`
4. Feed `common_integration.md` → Claude Opus verifies interfaces match and resolves any conflicts
5. Feed all 4 files → Claude Opus writes unit tests for each module

**Prompt template for Claude Opus:**
```
Here is the design spec for [Atul/Tanishk/Yash]'s module in the FIBA AI system.
The interface contracts are defined in common_integration.md.
Please implement all the code exactly as specced, following the interface contracts.
Ensure all imports are correct and the code is production-ready.
```

---

## Hackathon Demo Flow

1. Open web app at `http://localhost:5000`
2. Demo Query 1: Upload cooking video → type "cutting onion" → show key frames + evidence
3. Demo Query 2: Upload box video → type "opening box" → show rotation trace + trajectory
4. Demo Query 3: Upload pouring video → type "pouring water" → show tilt analysis
5. Show offline badge: "Running entirely on local CPU, no cloud, edge-ready"
6. Show latency: display per-frame processing time in UI

---

## Evaluation Criteria → Our Coverage

| Criterion | How We Address It |
|-----------|------------------|
| **Zero-shot** | No fine-tuning; YOLO pretrained + text grounding |
| **Edge-friendly** | <35MB total models, <100ms/frame on CPU |
| **Explainable** | Rule-based evidence text + key frames |
| **Working demo** | Flask web app, drag-drop video |
| **Visual output** | Annotated key frames + trajectory map |
| **Object bbox/mask** | YOLOv8n bbox + GrabCut/MobileSAM mask |
| **Key frames** | Top-3 selected by motion activity score |
| **Trajectory** | Color-coded centroid path visualization |
| **Inferred motion** | "Rotation=45°, area fragmented → cutting inferred" |
