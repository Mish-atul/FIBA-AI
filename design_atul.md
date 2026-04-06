# 🎨 Design — Atul
## Implementation Spec: Query Parser + Hand Detector + Object Detector
### FIBA AI | MIT Bangalore Hitachi Hackathon

---

## Complete Source Code

### `pipeline/query_parser.py`

```python
"""
Query Parser — Atul
Parses natural language action queries into structured components.
No model training needed. Uses spaCy (lightweight, offline).
"""

import re
from dataclasses import dataclass
from typing import Optional

@dataclass
class QueryResult:
    raw_query: str
    action_verb: str
    action_category: str      # CUT, OPEN, POUR, PICK, PLACE, MIX, CLOSE
    object_noun: str
    tool_noun: Optional[str]

# Action verb mappings
VERB_CATEGORY_MAP = {
    "cut": "CUT", "cutting": "CUT", "chop": "CUT", "chopping": "CUT",
    "slice": "CUT", "slicing": "CUT", "dice": "CUT", "dicing": "CUT",
    "open": "OPEN", "opening": "OPEN", "unscrew": "OPEN", "unscrewing": "OPEN",
    "unlock": "OPEN", "lift": "OPEN", "peel": "OPEN", "peeling": "OPEN",
    "pour": "POUR", "pouring": "POUR", "fill": "POUR", "filling": "POUR",
    "drain": "POUR", "draining": "POUR",
    "pick": "PICK", "picking": "PICK", "grab": "PICK", "grabbing": "PICK",
    "take": "PICK", "taking": "PICK", "lift": "PICK",
    "place": "PLACE", "placing": "PLACE", "put": "PLACE", "putting": "PLACE",
    "set": "PLACE", "drop": "PLACE", "dropping": "PLACE",
    "mix": "MIX", "mixing": "MIX", "stir": "MIX", "stirring": "MIX",
    "shake": "MIX", "shaking": "MIX", "blend": "MIX",
    "close": "CLOSE", "closing": "CLOSE", "shut": "CLOSE", "cap": "CLOSE",
    "cover": "CLOSE", "covering": "CLOSE", "seal": "CLOSE",
}

CATEGORY_TOOL_MAP = {
    "CUT": "knife", "OPEN": None, "POUR": None,
    "PICK": None, "PLACE": None, "MIX": "spoon", "CLOSE": None,
}

# Common stop words to filter
STOP_WORDS = {"a", "an", "the", "some", "my", "with", "using", "from",
              "into", "onto", "off", "up", "down", "is", "are", "be"}

def parse_query(query_text: str) -> QueryResult:
    """
    Parse a natural language query like 'cutting onion' or 'opening a box'.
    
    Args:
        query_text: Raw user query string
    Returns:
        QueryResult with extracted components
    """
    text = query_text.lower().strip()
    tokens = re.findall(r'\b[a-zA-Z]+\b', text)
    tokens = [t for t in tokens if t not in STOP_WORDS]
    
    action_verb = None
    action_category = None
    object_noun = None
    tool_noun = None
    
    # Find verb (first token that matches verb map)
    verb_idx = -1
    for i, token in enumerate(tokens):
        if token in VERB_CATEGORY_MAP:
            action_verb = token
            action_category = VERB_CATEGORY_MAP[token]
            verb_idx = i
            break
    
    # If no verb found, try first token as verb
    if action_verb is None and tokens:
        action_verb = tokens[0]
        action_category = "UNKNOWN"
        verb_idx = 0
    
    # Find object noun (first noun after verb)
    remaining = tokens[verb_idx+1:] if verb_idx >= 0 else tokens
    if remaining:
        object_noun = remaining[0]
    else:
        object_noun = "object"  # fallback
    
    # Infer tool if not explicitly stated
    tool_noun = CATEGORY_TOOL_MAP.get(action_category)
    
    # Check if tool explicitly mentioned
    for token in remaining[1:]:
        if token in ["knife", "spoon", "fork", "scissors", "hand", "finger"]:
            tool_noun = token
    
    return QueryResult(
        raw_query=query_text,
        action_verb=action_verb or "unknown",
        action_category=action_category or "UNKNOWN",
        object_noun=object_noun,
        tool_noun=tool_noun,
    )


if __name__ == "__main__":
    # Test
    queries = [
        "cutting onion",
        "opening a box",
        "pouring water into cup",
        "picking up the bottle",
        "mixing ingredients",
    ]
    for q in queries:
        r = parse_query(q)
        print(f"Query: '{q}'")
        print(f"  → verb={r.action_verb} ({r.action_category}), object={r.object_noun}, tool={r.tool_noun}")
        print()
```

---

### `pipeline/hand_detector.py`

```python
"""
Hand Detector — Atul
Uses MediaPipe Hands for real-time 21-keypoint hand tracking.
Zero training required. Edge-optimized.
"""

import cv2
import mediapipe as mp
import numpy as np
from dataclasses import dataclass, field
from typing import Optional, List, Tuple

@dataclass
class HandDetectionResult:
    detected: bool
    hand_bbox: Optional[List[float]] = None      # [x1, y1, x2, y2] in pixels
    landmarks: Optional[List[List[float]]] = None # 21 x [x,y,z] normalized
    handedness: Optional[str] = None              # "Left" or "Right"
    confidence: float = 0.0
    wrist_pos: Optional[Tuple[float, float]] = None   # pixels (x, y)
    index_tip: Optional[Tuple[float, float]] = None
    thumb_tip: Optional[Tuple[float, float]] = None


class HandDetector:
    def __init__(self,
                 min_detection_confidence: float = 0.6,
                 min_tracking_confidence: float = 0.5,
                 max_num_hands: int = 2):
        
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=max_num_hands,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
        )
        self.mp_draw = mp.solutions.drawing_utils
    
    def detect(self, frame: np.ndarray) -> HandDetectionResult:
        """
        Detect hands in a single BGR frame.
        Returns HandDetectionResult (detected=False if no hand found).
        """
        h, w = frame.shape[:2]
        
        # Convert to RGB for MediaPipe
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.hands.process(rgb)
        
        if not results.multi_hand_landmarks:
            return HandDetectionResult(detected=False)
        
        # Take the first/most confident hand
        hand_landmarks = results.multi_hand_landmarks[0]
        handedness = results.multi_handedness[0].classification[0].label
        conf = results.multi_handedness[0].classification[0].score
        
        # Extract landmarks as pixel coords
        lm_list = []
        x_coords, y_coords = [], []
        for lm in hand_landmarks.landmark:
            px, py = int(lm.x * w), int(lm.y * h)
            lm_list.append([px, py, lm.z])
            x_coords.append(px)
            y_coords.append(py)
        
        # Bounding box from landmarks
        x1, y1 = max(0, min(x_coords) - 20), max(0, min(y_coords) - 20)
        x2, y2 = min(w, max(x_coords) + 20), min(h, max(y_coords) + 20)
        
        # Key landmarks (pixel coords)
        wrist = (lm_list[0][0], lm_list[0][1])
        index_tip = (lm_list[8][0], lm_list[8][1])
        thumb_tip = (lm_list[4][0], lm_list[4][1])
        
        return HandDetectionResult(
            detected=True,
            hand_bbox=[x1, y1, x2, y2],
            landmarks=lm_list,
            handedness=handedness,
            confidence=conf,
            wrist_pos=wrist,
            index_tip=index_tip,
            thumb_tip=thumb_tip,
        )
    
    def draw(self, frame: np.ndarray, result: HandDetectionResult) -> np.ndarray:
        """Draw hand landmarks and bbox on frame (for visualization)."""
        if not result.detected:
            return frame
        out = frame.copy()
        x1, y1, x2, y2 = [int(c) for c in result.hand_bbox]
        cv2.rectangle(out, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(out, f"Hand {result.handedness} {result.confidence:.2f}",
                    (x1, y1-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,0), 1)
        # Draw wrist point
        if result.wrist_pos:
            cv2.circle(out, result.wrist_pos, 6, (255, 0, 0), -1)
        return out
    
    def release(self):
        self.hands.close()


if __name__ == "__main__":
    cap = cv2.VideoCapture(0)
    detector = HandDetector()
    while True:
        ret, frame = cap.read()
        if not ret: break
        result = detector.detect(frame)
        frame = detector.draw(frame, result)
        if result.detected:
            print(f"Hand at {result.hand_bbox}, wrist={result.wrist_pos}")
        cv2.imshow("Hand Detection", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'): break
    cap.release()
    detector.release()
    cv2.destroyAllWindows()
```

---

### `pipeline/object_detector.py`

```python
"""
Object Detector — Atul
Text-grounded object detection using YOLOv8n + semantic filtering.
Finds the query-relevant object nearest to the detected hand.
"""

import cv2
import numpy as np
from dataclasses import dataclass
from typing import Optional, List, Tuple
from ultralytics import YOLO

@dataclass
class ObjectDetectionResult:
    detected: bool
    object_bbox: Optional[List[float]] = None    # [x1, y1, x2, y2]
    object_label: Optional[str] = None
    detection_confidence: float = 0.0
    grounding_score: float = 0.0
    center: Optional[Tuple[float, float]] = None
    area: float = 0.0


# Simple text matching: cosine-like overlap on character n-grams
def text_similarity(a: str, b: str) -> float:
    """Simple token overlap similarity between two strings."""
    a_tokens = set(a.lower().split())
    b_tokens = set(b.lower().split())
    # Also check substring match
    if a.lower() in b.lower() or b.lower() in a.lower():
        return 1.0
    if not a_tokens or not b_tokens:
        return 0.0
    intersection = len(a_tokens & b_tokens)
    union = len(a_tokens | b_tokens)
    return intersection / union


class ObjectDetector:
    def __init__(self, query_object: str, model_path: str = "yolov8n.pt"):
        """
        Args:
            query_object: The object noun from query parser (e.g., "onion")
            model_path: Path to YOLOv8 weights
        """
        self.query_object = query_object.lower()
        self.model = YOLO(model_path)
        self.conf_threshold = 0.25
        print(f"[ObjectDetector] Initialized for object: '{query_object}'")
    
    def detect(self, frame: np.ndarray, 
               hand_result=None) -> ObjectDetectionResult:
        """
        Detect the query-relevant object in frame.
        Uses hand position to disambiguate if multiple candidates exist.
        """
        # Run YOLO
        results = self.model(frame, conf=self.conf_threshold, verbose=False)
        
        if not results or len(results[0].boxes) == 0:
            return ObjectDetectionResult(detected=False)
        
        boxes = results[0].boxes
        h, w = frame.shape[:2]
        frame_diag = np.sqrt(h**2 + w**2)
        
        # Get hand wrist for proximity scoring
        hand_wrist = None
        if hand_result and hand_result.detected and hand_result.wrist_pos:
            hand_wrist = np.array(hand_result.wrist_pos, dtype=float)
        
        # Score each detection
        best_score = -1
        best_det = None
        
        for i in range(len(boxes)):
            x1, y1, x2, y2 = boxes.xyxy[i].cpu().numpy()
            conf = float(boxes.conf[i])
            cls_id = int(boxes.cls[i])
            label = self.model.names[cls_id]
            
            # Text grounding score
            label_score = text_similarity(self.query_object, label)
            
            # Proximity score (closer to hand = higher score)
            cx = (x1 + x2) / 2
            cy = (y1 + y2) / 2
            if hand_wrist is not None:
                dist = np.linalg.norm(np.array([cx, cy]) - hand_wrist)
                proximity_score = 1.0 / (1.0 + dist / (frame_diag * 0.3))
            else:
                proximity_score = 0.5  # neutral if no hand
            
            # Combined score
            total_score = (0.5 * label_score + 
                          0.3 * proximity_score + 
                          0.2 * conf)
            
            if total_score > best_score:
                best_score = total_score
                best_det = {
                    "bbox": [float(x1), float(y1), float(x2), float(y2)],
                    "label": label,
                    "conf": conf,
                    "grounding": label_score,
                    "center": (cx, cy),
                    "area": (x2-x1) * (y2-y1),
                }
        
        if best_det is None or best_score < 0.1:
            return ObjectDetectionResult(detected=False)
        
        return ObjectDetectionResult(
            detected=True,
            object_bbox=best_det["bbox"],
            object_label=best_det["label"],
            detection_confidence=best_det["conf"],
            grounding_score=best_det["grounding"],
            center=best_det["center"],
            area=best_det["area"],
        )
    
    def draw(self, frame: np.ndarray, result: ObjectDetectionResult) -> np.ndarray:
        """Draw object detection on frame."""
        if not result.detected:
            return frame
        out = frame.copy()
        x1, y1, x2, y2 = [int(c) for c in result.object_bbox]
        cv2.rectangle(out, (x1, y1), (x2, y2), (0, 0, 255), 2)
        label = f"{result.object_label} ({result.detection_confidence:.2f})"
        cv2.putText(out, label, (x1, y1-5), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,0,255), 1)
        return out


if __name__ == "__main__":
    import sys
    query_obj = sys.argv[1] if len(sys.argv) > 1 else "cup"
    cap = cv2.VideoCapture(0)
    detector = ObjectDetector(query_obj)
    while True:
        ret, frame = cap.read()
        if not ret: break
        result = detector.detect(frame)
        frame = detector.draw(frame, result)
        cv2.imshow(f"Object: {query_obj}", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'): break
    cap.release()
    cv2.destroyAllWindows()
```

---

## Test Script for Atul's Modules

```bash
# Install deps
pip install mediapipe ultralytics spacy
python -m spacy download en_core_web_sm

# Test query parser
python pipeline/query_parser.py

# Test hand detector (needs webcam)
python pipeline/hand_detector.py

# Test object detector (needs webcam)
python pipeline/object_detector.py onion
```
