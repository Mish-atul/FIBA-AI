# 🏗️ Architecture — Atul
## Module: Query Parser + Hand Detector + Object Detector
### FIBA AI | MIT Bangalore Hitachi Hackathon

---

## Your Role in the Pipeline

Atul owns **Stage 1, 2, and 3** — the front of the pipeline. Everything downstream (Tanishk's tracking/motion, Yash's web UI) depends on the quality of your outputs.

```
[NL Query] ──► [Query Parser] ──► (object_noun, action_verb, tool_noun)
                                         │
[Video Frame] ──► [Hand Detector] ──► hand_bbox, hand_keypoints (21pts)
                                         │
                  [Object Detector] ──► object_bbox, object_label, confidence
                  (text-grounded via     │
                   query object_noun)    ▼
                                   ──► TO TANISHK (tracker input)
```

---

## Stage 1: Query Parser (`pipeline/query_parser.py`)

### What it does
Parses a natural-language action query like `"cutting onion"` or `"opening a box"` into structured fields.

### Output contract (dict)
```python
{
  "action_verb": "cutting",        # the verb/action keyword
  "object_noun": "onion",          # primary manipulated object
  "tool_noun": "knife",            # optional tool (inferred or explicit)
  "raw_query": "cutting onion"
}
```

### Architecture Decision
- **No LLM required** — use spaCy `en_core_web_sm` (tiny, 12MB, runs offline)
- POS tagging: VERB → action_verb, NOUN → object_noun
- Verb-to-tool mapping dict for tool inference (e.g., cut → knife)
- Fallback: regex split if spaCy not available

### Verb → Action Category Map
```python
VERB_MAP = {
    "cut": "CUT", "cutting": "CUT", "chop": "CUT", "slice": "CUT",
    "open": "OPEN", "opening": "OPEN", "unscrew": "OPEN", "lift": "OPEN",
    "pour": "POUR", "pouring": "POUR", "fill": "POUR",
    "pick": "PICK", "grab": "PICK", "take": "PICK",
    "place": "PLACE", "put": "PLACE", "set": "PLACE",
    "mix": "MIX", "stir": "MIX", "shake": "MIX",
    "close": "CLOSE", "shut": "CLOSE", "cap": "CLOSE",
}
TOOL_MAP = {
    "CUT": "knife", "POUR": None, "MIX": "spoon", 
    "OPEN": None, "PICK": None, "PLACE": None, "CLOSE": None
}
```

---

## Stage 2: Hand Detector (`pipeline/hand_detector.py`)

### What it does
Detects hands in each video frame and returns bounding boxes + 21 landmark keypoints.

### Architecture Decision: **MediaPipe Hands**
✅ Zero training needed  
✅ < 10MB total model size  
✅ Real-time on CPU (runs ~30fps on laptop)  
✅ 21 3D keypoints per hand  
✅ Works offline  

### Output contract per frame
```python
{
  "hand_bbox": [x1, y1, x2, y2],          # pixel coords
  "hand_landmarks": [[x,y,z]*21],          # normalized 0-1 coords
  "handedness": "Right" | "Left",
  "confidence": float,
  "wrist_pos": [x, y],                     # landmark 0
  "index_tip": [x, y],                     # landmark 8
  "thumb_tip": [x, y],                     # landmark 4
}
```

### Key MediaPipe Landmark Indices (memorize these)
```
0: Wrist        4: Thumb tip     8: Index tip
12: Middle tip  16: Ring tip     20: Pinky tip
```

### Edge Notes
- Set `min_detection_confidence=0.6`, `min_tracking_confidence=0.5`
- Use `static_image_mode=False` for video (tracking mode, much faster)
- Resize frame to 640×480 before passing to MediaPipe

---

## Stage 3: Object Detector (`pipeline/object_detector.py`)

### What it does
Detects the query-relevant object in the frame. Uses YOLOv8n as the edge-deployed detector, with text-grounded filtering using the `object_noun` from the query parser.

### Architecture Decision: **YOLOv8n (nano)**
- 3.2M params, ~11MB, ~80ms CPU, ~15ms GPU
- COCO-pretrained: 80 classes (covers most kitchen/everyday objects)
- For out-of-COCO objects: use Grounding DINO offline to find, YOLOv8n fine-tuned on those objects

### Text-Grounding Strategy (Zero-Shot)
Since we cannot retrain for hackathon speed:
1. Run YOLOv8n on frame → get all detections with labels
2. Use **semantic similarity** (cosine sim on CLIP text embeddings) to match `object_noun` to detected class labels
3. Return bbox of the best-matching detection **nearest to the hand**

```python
# Proximity scoring: closest object to hand wrist that matches query
def score_detection(det, hand_wrist, query_object):
    label_sim = clip_similarity(det.label, query_object)  # 0-1
    dist = euclidean(det.center, hand_wrist)
    proximity_score = 1 / (1 + dist/100)
    return 0.6 * label_sim + 0.4 * proximity_score
```

### Fallback for Unknown Objects
If YOLO doesn't detect query object (out-of-distribution):
- Use **color/region heuristic**: segment region near hand, use that as proxy bbox
- Log as low-confidence detection

### Output contract per frame
```python
{
  "object_bbox": [x1, y1, x2, y2],
  "object_label": "onion",
  "detection_confidence": float,
  "grounding_confidence": float,   # how well it matched query
  "center": [cx, cy],
  "area": float,
}
```

---

## Performance Targets (Your Modules)
| Module | Target Latency | Model Size |
|--------|---------------|------------|
| Query Parser | < 5ms | ~12MB (spaCy) |
| Hand Detector | < 15ms/frame | ~8MB (MediaPipe) |
| Object Detector | < 50ms/frame | ~11MB (YOLOv8n) |
| **Total Stage 1-3** | **< 70ms/frame** | **< 35MB** |

---

## Interface to Tanishk
Your modules must export these to `integrator.py`:
```python
# Per frame call
result = {
    "frame_id": int,
    "timestamp_ms": float,
    "query": QueryResult,          # from query_parser
    "hand": HandDetectionResult,   # from hand_detector (None if no hand)
    "object": ObjectDetectionResult  # from object_detector (None if not found)
}
```

---

## Dev Notes for Hackathon Speed
1. Install: `pip install mediapipe ultralytics spacy` + `python -m spacy download en_core_web_sm`
2. Test each module standalone with a webcam frame before integration
3. Use `cv2.VideoCapture(0)` for webcam or load video file
4. Profile with `time.perf_counter()` around each call
5. If MediaPipe is slow: drop to every 2nd frame for hand detection, interpolate bbox between frames
