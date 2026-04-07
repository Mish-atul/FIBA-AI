# FIBA AI — Find it by Action

> **Edge-Ready · Zero-Shot · Explainable · SOP Compliance**

Real-time assembly task detection and SOP compliance validation system designed for edge deployment.

## Project Structure

```
FIBA AI/
├── web_app/                   # Flask web application
│   ├── app.py                 # Flask server
│   ├── pipeline/              # AI pipeline modules
│   │   ├── hand_detector.py   # MediaPipe hand detection
│   │   ├── hand_skeleton.py   # 21-joint skeleton visualization
│   │   ├── sop_validator.py   # SOP compliance engine (classifier + fingerprint)
│   │   ├── query_parser.py    # NLP query parsing
│   │   ├── action_inferencer.py # Action classification
│   │   └── ...
│   ├── weights/               # Trained model weights
│   │   └── sop_classifier.pt  # YOLOv8n-cls trained on 78 cycles
│   ├── static/                # Frontend (CSS, JS)
│   ├── templates/             # HTML templates
│   ├── train_sop_classifier.py # Training script for SOP classifier
│   └── requirements.txt       # Python dependencies
│
├── android_apk/               # React Native / Expo mobile app
│   ├── app/                   # Expo Router screens
│   │   └── (tabs)/
│   │       ├── index.tsx      # Action Search tab
│   │       ├── sop.tsx        # SOP Compliance tab
│   │       └── history.tsx    # Analysis history tab
│   ├── services/
│   │   └── fibaApi.ts         # API service (connects to Flask)
│   ├── context/
│   │   └── JobContext.tsx      # State management
│   ├── components/            # Reusable UI components
│   └── package.json
│
└── README.md
```

## Quick Start

### Web App (Backend)
```bash
cd web_app
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
.venv\Scripts\python.exe app.py
# Opens at http://localhost:5000
```

### Android App (Frontend)
```bash
cd android_apk
npm install
npx expo start
# Scan QR code with Expo Go app
```

> **Note:** The Android app connects to the Flask backend at `localhost:5000`. For mobile testing, update `FLASK_BASE` in `services/fibaApi.ts` to your computer's local IP address.

## Team
**MIT Bangalore × Hitachi Hackathon**
- Atul · Tanishk · Yash
