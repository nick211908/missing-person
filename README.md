# Missing Person AI

A full-stack, AI-powered system designed to locate missing persons using facial recognition. The system allows users to upload missing person records with reference images and uses DeepFace and OpenCV to detect and match faces from live camera feeds or uploaded video streams via a React dashboard.

## 🚀 Features

- **Profile Registration:** Upload missing persons with reference images.
- **Automated Augmentation:** System calculates per-profile and intra-person self-similarity cosine thresholds dynamically to optimize match accuracy using K-Nearest Neighbors (KNN).
- **Video Processors:** Upload CCTV footage/videos and process bounding boxes seamlessly. 
- **Real-Time Livestreaming Tracking:** Hook into ONVIF / RTSP camera URLs and track multiple subjects dynamically leveraging ByteTrack and Supervision AI trackers.
- **RESTful Architecture:** Python FastAPI backend integrated with a SQLite datastore and `scikit-learn` memory vectors.
- **Beautiful Dashboard:** React dashboard built for easy querying and registration of individuals with real-time detection alerts.

## 📁 Repository Structure

```
missing-person-ai/
│
├── backend/               # FastAPI Backend Service
│   ├── app/
│   │   ├── api/           # Router Endpoints (Detection, Missing Persons, Stream)
│   │   ├── auth/          # JWT/Bcrypt Authentication
│   │   ├── database/      # SQLAlchemy Config & Pydantic Schemas
│   │   ├── models/        # Database Entities
│   │   └── services/      # Core AI Logic (Matcher, Face Detector, Quality Assessment, Stream Processing)
│   ├── data/              # Ephemeral snapshot & storage directory
│   ├── missing_persons.db # Primary SQLite Storage
│   └── requirements.txt   # Python Dependencies
│   
├── frontend/              # React.js Service
│   ├── src/
│   │   ├── components/    # Reusable UI Blocks (Dashboard, Upload Modal)
│   │   └── context/       # Auth Context & State Management
│   └── package.json       # Node Dependencies
│
└── docker-compose.yml     # Multi-Container configuration
```

## 🛠 Prerequisites

Ensure you have the following installed on your local development machine:

- **Python 3.10+** (Virtual environment recommended)
- **Node.js 18+** & `npm`
- **Git**
- **Docker & Docker Compose** (Optional for containerized deployments)

## 💻 Local Setup & Installation

### 1. Setting Up the Backend

The backend utilizes `FastAPI` and `DeepFace` for AI processing.

```bash
# 1. Navigate to the backend directory
cd backend

# 2. Create a virtual environment (if not already done)
python -m venv venv

# 3. Activate the virtual environment
# On Windows:
.\venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Start the underlying Uvicorn server in Development Mode
uvicorn app.main:app --reload --port 8000
```
> The API will now be accessible via `http://localhost:8000`. You can test endpoints via the Swagger UI available at `http://localhost:8000/docs`.

### 2. Setting Up the Frontend

The frontend empowers officers with a quick graphical view. It connects to the FastAPI process directly.

```bash
# 1. Navigate to the frontend directory
cd frontend

# 2. Install Node dependencies
npm install

# 3. Start the Vite development script
npm run dev
```
> The dashboard will typically launch on `http://localhost:5173`. 


## 📝 Usage Guide

1. **Dashboard Overview:** Open the UI link in your browser and you'll be greeted with the Database overview representing all missing victims.
2. **Uploading a Profile:** Click "Report Missing Person" to upload basic details (Name, Last Seen Location, Physical descriptions). Include 2-3 clear pictures. The backend will index their facial embeddings in real-time.
3. **Tracking & Analysis:** The internal Stream processor loops into available cameras or uploaded videos and matches `ByteTrack` coordinate tracks against `.get_person_embeddings()`.


## 🛡 Security and Environment Variables

You can configure secrets directly inside `.env` configurations depending on your deployment target. The authentication handles custom symmetric JWT encryption hashing with `passlib[bcrypt]`.


## 🐳 Docker Production Deployment

To run entirely via Docker images with abstracted networking configurations:

```bash
docker-compose --env-file .env build
docker-compose up -d
```

---
*Created carefully to track our most vulnerable demographics with rapid AI facial mapping pipelines.*
