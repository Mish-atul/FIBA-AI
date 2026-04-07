# FIBA AI Frontend Website Generation Prompt

Use this prompt to generate a modern, responsive frontend website for the FIBA AI backend. Share this with Replit, Claude, ChatGPT, or any other AI code generator.

---

## Project Overview

**FIBA AI (Find-it-by-Action)** is an edge-ready, zero-shot action detection and SOP compliance validation system. The backend is a Flask server running on `localhost:5000` with computer vision pipelines for hand tracking, object detection, and action inference.

**Key Features:**
- **Action Search**: Upload a video + natural language query → get action detection results with explainable AI
- **SOP Compliance**: Upload reference video (correct procedure) → validate test videos against it
- **Real-time Processing**: SSE streams for progress updates
- **Edge Deployment**: Optimized for on-device processing

---

## MD Files to Share (Upload These First)

Before generating the website, provide these documentation files to the AI:

### Required Files:
1. **`FRONTEND_INTEGRATION.md`** - Complete API documentation with all endpoints, request/response schemas, and code examples
2. **`README.md`** - Project overview, structure, and quick start instructions
3. **`CONTRIBUTING.md`** - Development guidelines

### Optional (for reference):
4. **`web_app/templates/index.html`** - Current HTML structure
5. **`web_app/static/style.css`** - Current CSS styles
6. **`web_app/static/app.js`** - Current JavaScript implementation
7. **`web_app/app.py`** - Flask backend with API routes

---

## The Prompt (Copy and Paste This)

---

```
Generate a modern, responsive frontend website for FIBA AI - an action detection and SOP compliance system.

## Backend API (Base URL: http://localhost:5000)

The backend provides these endpoints:

### Action Search Endpoints:
1. POST /api/process - Upload video + query, returns job_id
2. GET /api/status/<job_id> - Poll for results
3. GET /api/stream/<job_id> - SSE for real-time progress

### SOP Compliance Endpoints:
4. POST /api/sop/reference - Upload reference video to learn correct procedure
5. POST /api/sop/validate - Validate test video against reference
6. GET /api/sop/status - Check if classifier/reference is loaded

## Response Data Structures:

### Action Search Result:
{
  action_detected: boolean,
  action_label: string,          // e.g., "picking up"
  action_category: string,       // e.g., "grasp"
  confidence: number,            // 0.0 - 1.0
  timestamp_range: [number, number], // [start_frame, end_frame]
  evidence: string,              // Human-readable explanation
  key_frames: string[],          // Base64 JPEG images
  skeleton_frames: string[],     // Base64 hand skeleton visualizations
  finger_trajectory: string,     // Base64 trajectory plot
  trajectory: string,            // Base64 object trajectory
  motion_summary: {
    rotation_deg: number,
    displacement_px: number,
    contact_events: number,
    area_change_ratio: number,
    state_change: string,
    vertical_motion: string,
    motion_speed_px_per_frame: number,
    contact_frequency: string,
    approach_score: number,
    grasp_change: string,
    area_growth_trend: string
  },
  query_info: {
    raw: string,
    verb: string,
    category: string,
    object: string,
    tool: string | null
  },
  total_frames: number,
  fps: number,
  processing_time_s: number,
  action_description: string,
  edge_stats: {
    edge_ready: boolean,
    zero_shot: boolean,
    pipeline_latency_s: number,
    frame_processing_s: number,
    inference_latency_s: number,
    effective_fps: number,
    processed_frames: number,
    total_frames: number,
    frame_skip: number,
    resolution: string,
    models_used: string
  }
}

### SOP Validate Result:
{
  type: "sop_validate",
  passed: boolean,
  step_results: [
    {
      position: number,
      expected_task: string,
      detected_task: string,
      similarity: number,      // 0.0 - 1.0
      is_correct: boolean,
      keyframe_b64: string,
      skeleton_b64: string
    }
  ],
  summary: string,
  total_frames: number,
  fps: number,
  processing_time_s: number
}

## Design Requirements:

### Visual Style:
- Modern dark theme with premium feel
- Primary colors: Deep purple (#6c5ce7), Teal (#00cec9), Soft lavender (#a29bfe)
- Background: Very dark (#0a0b10) with subtle animated gradients
- Glassmorphism cards with backdrop blur
- Inter font family
- Smooth animations and transitions

### Layout Structure:

1. **Navigation Bar**
   - Brand: "FIBA AI" with accent on "AI"
   - Badge: "Edge · Zero-Shot · SOP Compliance" with animated pulse dot
   - Sticky with blur backdrop

2. **Hero Section**
   - Large gradient title: "Find it by Action"
   - Subtitle about egocentric video analysis
   - Animated gradient background

3. **Mode Selector Tabs**
   - Tab 1: "Action Search" (with search icon)
   - Tab 2: "SOP Compliance" (with clipboard icon)
   - Active tab has gradient background

4. **Action Search Mode:**
   
   a) **Upload Card**
   - Drag & drop zone with video icon
   - File browser fallback
   - File info display (name, size) with remove button
   - "MP4, AVI, MOV · max ~100 MB recommended"
   
   b) **Query Input Row**
   - Search icon in input
   - Placeholder: "Describe the action — e.g., cutting onion, opening box, pouring water"
   - Process button (gradient, with arrow icon)
   
   c) **Example Chips**
   - Quick query buttons: "🔪 cutting onion", "📦 opening box", "🫗 pouring water", "🌭 picking up hotdog", "🥣 mixing ingredients"

5. **Progress Section (shown during processing)**
   - Animated spinner + "Processing pipeline" title
   - Progress bar with percentage
   - Current status message
   - 5 pipeline stages with visual indicators:
     - Parse query (0-15%)
     - Detect objects (15-45%)
     - Track & motion (45-72%)
     - Infer action (72-85%)
     - Render output (85-100%)
   - Use SSE (EventSource) for real-time updates

6. **Results Section (Action Search)**
   
   a) **Result Banner**
   - Green gradient for detected, red gradient for not-detected
   - Large emoji icon (✅ or ❌)
   - Title: "Action Detected" / "Not Detected"
   - Subtitle: "query → action_label (category)"
   - Confidence ring (SVG circle with animated stroke-dashoffset)
   
   b) **Action Description Card**
   - Title with message icon
   - Description text with highlighted keywords
   
   c) **Explainable Evidence Card**
   - Title with lightbulb icon
   - Evidence text in colored box with left border
   
   d) **Key Frames Grid**
   - Title with monitor icon
   - Grid of clickable images (opens lightbox)
   - Each frame labeled "Key Frame 1", etc.
   
   e) **Hand Skeleton Grid**
   - Title with hand icon
   - Color legend: Thumb (blue), Index (green), Middle (orange), Ring (cyan), Pinky (magenta)
   - Grid of skeleton visualizations
   
   f) **Finger Trajectory Card**
   - Title with chart icon
   - Large image showing finger movement paths
   
   g) **Object Trajectory Card**
   - Title with chart icon
   - Object movement visualization
   
   h) **Motion Statistics Grid**
   - Title with bar chart icon
   - Grid of stat cards showing: Rotation, Displacement, Contact Events, Area Change, etc.
   - Each stat: label (uppercase, small) + value (large, bold) + unit
   
   i) **Edge Deployment Profile Card**
   - Title with document icon
   - Badges: Edge Ready, Zero-Shot, No Cloud, Explainable
   - Stats: Pipeline Latency, Frame Processing, Inference, Effective FPS, etc.
   
   j) **Query Analysis Card**
   - Title with clipboard icon
   - Grid showing: Query, Verb, Category, Object, Tool
   
   k) **Metadata**
   - Centered text: "frames · FPS · processed in Xs"
   
   l) **New Analysis Button**
   - Secondary style, with refresh icon

7. **SOP Compliance Mode:**
   
   a) **SOP Definition Timeline**
   - Card showing predefined SOP steps (7 steps for seat assembly)
   - Each step: number badge, title, description
   - Timeline connector lines between steps
   - Steps highlight when reference is loaded
   
   b) **Upload Section**
   - Two columns:
     - Left: Reference upload ("1. Set Reference")
       - Drop zone with plus icon
       - "Learn Reference" button
       - Status indicator when learned
     - Right: Test upload ("2. Validate Test Video")
       - Drop zone with plus icon
       - "Validate" button (disabled until reference loaded)
   
   c) **SOP Progress Card**
   - Similar to Action Search progress
   - Shows "Learning..." or "Validating..."
   
   d) **SOP Results**
   - Verdict banner (green for PASS, red for FAIL)
     - Large icon, title, description
   - Step-by-step results
     - Each step: icon (✅/❌), position, similarity percentage
     - Expected vs Detected task names
     - Keyframe thumbnails
   - Summary text with processing metadata

8. **Error Section**
   - Warning icon
   - "Pipeline Error" title
   - Error message
   - "Try Again" button

9. **Footer**
   - "FIBA AI · MIT Bangalore Hitachi Hackathon · Team: Atul · Tanishk · Yash"
   - Tagline: "Zero-shot · Edge-friendly · Explainable action retrieval · SOP Compliance"

10. **Lightbox**
    - Full-screen overlay for enlarged images
    - Close button (X)
    - Click outside to close
    - Escape key to close

### Technical Requirements:

1. **Responsive Design**
   - Mobile-first approach
   - Breakpoints: 640px, 768px, 960px+
   - Stack grids on mobile
   - Full-width buttons on mobile

2. **File Upload**
   - Support drag & drop
   - Visual feedback on drag (border color change)
   - File type validation (video/*)
   - File size display (B, KB, MB)
   - Remove file button

3. **Progress Handling**
   - Use EventSource for SSE streaming
   - Fallback to polling if SSE fails
   - Animate progress bar smoothly
   - Update stage indicators based on progress ranges

4. **Image Display**
   - Base64 images: `data:image/jpeg;base64,${data}`
   - Lazy loading for grid images
   - Click to open in lightbox

5. **State Management**
   - Track current mode (action/sop)
   - Track selected files
   - Track job status
   - Disable/enable buttons based on state

6. **Error Handling**
   - Show user-friendly error messages
   - Allow retry after errors
   - Handle network failures gracefully

7. **Animations**
   - Fade in results section
   - Progress bar smooth transition
   - Confidence ring animation
   - Hover effects on cards and buttons
   - Spinner animation for loading states

8. **Accessibility**
   - Proper heading hierarchy
   - ARIA labels for interactive elements
   - Keyboard navigation support
   - Focus states

### File Structure:

```
├── index.html          # Main HTML file
├── css/
│   └── styles.css      # All styles (no external frameworks)
├── js/
│   └── app.js          # All JavaScript logic
└── assets/
    └── (any images/icons if needed)
```

### CSS Guidelines:

- CSS variables for colors and sizing
- No external CSS frameworks (Bootstrap, Tailwind, etc.)
- Glassmorphism: `backdrop-filter: blur()`
- Gradients using custom properties
- Smooth transitions (0.2s-0.3s)
- Grid and Flexbox layouts
- Mobile-responsive with media queries

### JavaScript Guidelines:

- Vanilla JavaScript (no frameworks like React/Vue)
- Modular functions:
  - `startProcessing()` - Start action search
  - `pollProgress(jobId)` - Connect to SSE
  - `renderResults(result)` - Display action results
  - `uploadReference()` - SOP reference upload
  - `validateSOP()` - SOP validation
  - `renderSOPResults(result)` - Display SOP results
- Event delegation for dynamic elements
- Clean up EventSource on completion/error
- Format utilities (bytes, percentages)

### Example Queries for Testing:

- "person picking up a cup"
- "cutting onion"
- "opening box"
- "pouring water"
- "picking up hotdog"
- "mixing ingredients"
- "screwing with screwdriver"
- "assembling spring with pliers"

Generate complete, production-ready HTML, CSS, and JavaScript files. Include all icons as inline SVG. Make it visually stunning with smooth animations. Ensure the code is well-commented and follows modern web development best practices.
```

---

## Generated Files Expected

The AI should generate:

1. **`index.html`** - Complete HTML structure with all sections
2. **`css/styles.css`** - Complete CSS with variables, animations, responsive design
3. **`js/app.js`** - Complete JavaScript with API integration, event handlers, UI updates

---

## Post-Generation Instructions

After the website is generated:

1. **Test API Connectivity**
   - Ensure Flask backend is running on `localhost:5000`
   - Test file upload and query submission
   - Verify SSE progress streaming

2. **Test Both Modes**
   - Action Search with sample video
   - SOP Compliance with reference + test videos

3. **Verify Responsive Design**
   - Test on mobile viewport
   - Test on tablet
   - Test on desktop

4. **Check Error Handling**
   - Test with no file selected
   - Test with invalid file type
   - Test network disconnection

---

## Quick Deployment Options

### Option 1: Static Hosting (HTML/CSS/JS)
- Works with backend on separate server
- Update API_BASE_URL in JS to point to backend

### Option 2: Integrated with Flask
- Place files in `web_app/static/` and `web_app/templates/`
- Backend serves frontend directly

### Option 3: Replit
- Upload generated files
- Use Replit's webview for preview
- Configure backend URL

---

## Need Help?

Refer to the API documentation in `FRONTEND_INTEGRATION.md` for:
- Complete endpoint specifications
- Request/response examples
- Error handling patterns
- TypeScript interfaces
