"""
Phone Camera Connection Module.

Allows users to connect their phone camera to the system via:
1. WebSocket streaming for real-time face detection
2. HTTP endpoint for snapshot-based detection
3. Mobile-friendly web interface
4. Session management and scan history
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, UploadFile, File, Form, HTTPException, Request, Query
from fastapi.responses import HTMLResponse, JSONResponse
from app.services.face_detector import detect_faces
from app.services.matcher import matcher
from app.services.preprocessor import preprocess_frame
from app.services.phone_camera_service import phone_camera_service, PhoneCameraSession
from app.config import settings
from app.database.schemas import (
    PhoneCameraScanRequest, PhoneCameraScanResponse,
    PhoneCameraFrameRequest, PhoneCameraFrameResponse,
    PhoneCameraDetectionResult
)
import cv2
import numpy as np
import base64
import asyncio
import json
import time
from typing import Dict, Optional
from datetime import datetime

router = APIRouter()

# Active WebSocket connections
active_connections: Dict[str, WebSocket] = {}


def get_client_ip(request: Request) -> str:
    """Extract client IP from request."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.get("/phone-camera")
async def phone_camera_page():
    """
    Serve a mobile-friendly web page for phone camera connection.
    This page can be accessed from any device on the same network.
    """
    return HTMLResponse(content=get_phone_camera_html(), status_code=200)


@router.post("/phone-camera/scan/start", response_model=PhoneCameraScanResponse)
async def start_phone_scan(
    request: Request,
    scan_request: PhoneCameraScanRequest
):
    """
    Start a new phone camera scanning session.

    Returns session ID and WebSocket URL for streaming.
    """
    client_ip = get_client_ip(request)

    # Create session
    session = phone_camera_service.create_session(
        camera_id=scan_request.camera_id,
        device_info=scan_request.device_name,
        ip_address=client_ip,
        location=scan_request.location,
        scan_mode=scan_request.scan_mode
    )

    # Generate WebSocket URL
    ws_url = f"ws://{request.headers.get('host', 'localhost:8000')}/ws/phone-camera/{session.session_id}"

    return PhoneCameraScanResponse(
        session_id=session.session_id,
        camera_id=session.camera_id,
        websocket_url=ws_url,
        status="started",
        message=f"Scan session started for camera {scan_request.camera_id}"
    )


@router.post("/phone-camera/scan/{session_id}/stop")
async def stop_phone_scan(session_id: str):
    """
    Stop an active phone camera scanning session.
    """
    session = phone_camera_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    scan_record = phone_camera_service.end_session(session_id, "user_requested")

    return JSONResponse(content={
        "status": "stopped",
        "session_id": session_id,
        "camera_id": session.camera_id,
        "summary": {
            "duration_seconds": (datetime.utcnow() - session.connected_at).total_seconds() if scan_record else 0,
            "total_frames": session.frames_processed,
            "total_faces": session.faces_detected,
            "total_matches": session.matches_found
        }
    })


@router.get("/phone-camera/sessions")
async def list_active_sessions():
    """
    List all active phone camera scanning sessions.
    """
    sessions = phone_camera_service.get_active_sessions()

    return JSONResponse(content={
        "active_sessions": [
            {
                "session_id": s.session_id,
                "camera_id": s.camera_id,
                "device_info": s.device_info,
                "status": s.status,
                "connected_at": s.connected_at.isoformat(),
                "last_frame_at": s.last_frame_at.isoformat() if s.last_frame_at else None,
                "frames_processed": s.frames_processed,
                "faces_detected": s.faces_detected,
                "matches_found": s.matches_found,
                "location": s.location
            }
            for s in sessions
        ],
        "count": len(sessions)
    })


@router.get("/phone-camera/sessions/{session_id}")
async def get_session_details(session_id: str):
    """
    Get details of a specific phone camera session.
    """
    session = phone_camera_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return JSONResponse(content={
        "session_id": session.session_id,
        "camera_id": session.camera_id,
        "device_info": session.device_info,
        "status": session.status,
        "connected_at": session.connected_at.isoformat(),
        "last_frame_at": session.last_frame_at.isoformat() if session.last_frame_at else None,
        "frames_processed": session.frames_processed,
        "faces_detected": session.faces_detected,
        "matches_found": session.matches_found,
        "ip_address": session.ip_address,
        "location": session.location,
        "scan_mode": session.scan_mode
    })


@router.get("/phone-camera/history")
async def get_scan_history(
    limit: int = Query(100, ge=1, le=1000),
    camera_id: Optional[str] = Query(None)
):
    """
    Get scan history for phone cameras.

    Args:
        limit: Maximum number of records to return
        camera_id: Filter by specific camera ID
    """
    history = phone_camera_service.get_scan_history(limit=limit, camera_id=camera_id)

    return JSONResponse(content={
        "history": [
            {
                "scan_id": h.scan_id,
                "camera_id": h.camera_id,
                "device_info": h.device_info,
                "started_at": h.started_at.isoformat(),
                "ended_at": h.ended_at.isoformat(),
                "duration_seconds": (h.ended_at - h.started_at).total_seconds(),
                "total_frames": h.total_frames,
                "total_faces": h.total_faces,
                "total_matches": h.total_matches,
                "location": h.location
            }
            for h in history
        ],
        "count": len(history)
    })


@router.get("/phone-camera/stats")
async def get_phone_camera_stats():
    """
    Get overall phone camera statistics.
    """
    stats = phone_camera_service.get_stats()
    return JSONResponse(content=stats)


@router.post("/phone-camera/scan/{session_id}/frame", response_model=PhoneCameraFrameResponse)
async def process_phone_frame(
    session_id: str,
    frame_request: PhoneCameraFrameRequest
):
    """
    Process a single frame from phone camera via HTTP.

    Alternative to WebSocket for clients that prefer request/response model.
    """
    session = phone_camera_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    start_time = time.time()

    try:
        # Decode base64 image
        image_base64 = frame_request.frame
        img_bytes = base64.b64decode(image_base64)
        nparr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is None:
            raise HTTPException(status_code=400, detail="Could not decode image")

        # Preprocess and detect
        processed = preprocess_frame(img)
        faces = detect_faces(processed)

        results = []
        alerts = []
        match_count = 0

        for face in faces:
            if face.embedding is not None:
                best_match_id, sim_score = matcher.match(face.embedding)

                # Get person details if matched
                person_name = None
                threshold = settings.THRESHOLD_LOW_VARIANCE_DEFAULT

                if best_match_id:
                    from app.database.db import get_db, MissingPerson
                    db = next(get_db())
                    try:
                        person = db.query(MissingPerson).filter(
                            MissingPerson.person_id == best_match_id
                        ).first()
                        if person:
                            person_name = person.name
                            threshold = person.match_threshold or threshold
                    finally:
                        db.close()

                is_match = best_match_id is not None and sim_score >= threshold

                if is_match:
                    match_count += 1

                results.append(PhoneCameraDetectionResult(
                    bbox=face.bbox.astype(int).tolist(),
                    best_match_id=best_match_id,
                    similarity_score=round(float(sim_score), 4),
                    threshold_used=round(float(threshold), 4),
                    is_match=is_match,
                    person_name=person_name
                ))

                if is_match:
                    alerts.append({
                        "person_id": best_match_id,
                        "person_name": person_name,
                        "confidence": round(float(sim_score), 4),
                        "camera_id": frame_request.camera_id
                    })

        # Update session stats
        phone_camera_service.record_frame_processed(
            session_id,
            faces_detected=len(faces),
            matches_found=match_count
        )

        processing_time = (time.time() - start_time) * 1000

        return PhoneCameraFrameResponse(
            status="success",
            face_count=len(faces),
            detections=results,
            alerts=alerts,
            timestamp=time.time(),
            processing_time_ms=round(processing_time, 2)
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")


@router.websocket("/ws/phone-camera/{session_id}")
async def phone_camera_websocket(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for real-time phone camera streaming.

    Client sends: JSON with base64 encoded JPEG frame
    Server responds: Face detection results with match information
    """
    session = phone_camera_service.get_session(session_id)

    # If no session exists, create one on-the-fly (backward compatibility)
    if not session:
        session = phone_camera_service.create_session(
            camera_id=f"ws-{session_id[:8]}",
            scan_mode="realtime"
        )
        # Map the URL param to the new session
        phone_camera_service._camera_to_session[session_id] = session.session_id

    await websocket.accept()
    active_connections[session_id] = websocket
    phone_camera_service.update_session_status(session.session_id, "streaming")

    print(f"Phone camera connected: {session_id} (Camera: {session.camera_id})")

    try:
        while True:
            # Receive frame from client
            data = await websocket.receive_text()

            start_time = time.time()

            try:
                # Parse JSON message with base64 image
                message = json.loads(data)
                image_base64 = message.get("frame")

                if not image_base64:
                    await websocket.send_json({"error": "No frame data"})
                    continue

                # Decode base64 image
                img_bytes = base64.b64decode(image_base64)
                nparr = np.frombuffer(img_bytes, np.uint8)
                img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

                if img is None:
                    await websocket.send_json({"error": "Could not decode image"})
                    continue

                # Preprocess frame
                processed = preprocess_frame(img)

                # Detect faces
                faces = detect_faces(processed)

                results = []
                alerts = []
                match_count = 0

                for face in faces:
                    if face.embedding is not None:
                        # Match against database
                        best_match_id, sim_score = matcher.match(face.embedding)

                        # Get per-person threshold
                        threshold = settings.THRESHOLD_LOW_VARIANCE_DEFAULT
                        person_name = None
                        if best_match_id:
                            from app.database.db import get_db, MissingPerson
                            db = next(get_db())
                            try:
                                person = db.query(MissingPerson).filter(
                                    MissingPerson.person_id == best_match_id
                                ).first()
                                if person:
                                    threshold = person.match_threshold or threshold
                                    person_name = person.name
                            finally:
                                db.close()

                        is_match = best_match_id is not None and sim_score >= threshold

                        if is_match:
                            match_count += 1

                        results.append({
                            "bbox": face.bbox.astype(int).tolist(),
                            "best_match_id": best_match_id,
                            "similarity_score": round(float(sim_score), 4),
                            "threshold_used": round(float(threshold), 4),
                            "is_match": is_match,
                            "person_name": person_name
                        })

                        if is_match:
                            alerts.append({
                                "person_id": best_match_id,
                                "person_name": person_name,
                                "confidence": round(float(sim_score), 4),
                                "camera_id": session.camera_id
                            })

                # Update session stats
                phone_camera_service.record_frame_processed(
                    session.session_id,
                    faces_detected=len(faces),
                    matches_found=match_count
                )

                processing_time = (time.time() - start_time) * 1000

                # Send results back
                await websocket.send_json({
                    "status": "success",
                    "face_count": len(faces),
                    "detections": results,
                    "alerts": alerts,
                    "timestamp": time.time(),
                    "processing_time_ms": round(processing_time, 2)
                })

            except json.JSONDecodeError:
                await websocket.send_json({"error": "Invalid JSON format"})
            except Exception as e:
                await websocket.send_json({"error": str(e)})

    except WebSocketDisconnect:
        print(f"Phone camera disconnected: {session_id}")
    finally:
        active_connections.pop(session_id, None)
        phone_camera_service.end_session(session.session_id, "disconnected")


@router.post("/phone-camera/snapshot")
async def phone_camera_snapshot(
    file: UploadFile = File(...),
    camera_id: str = Form("phone"),
    location: Optional[str] = Form(None),
    device_info: Optional[str] = Form(None)
):
    """
    Upload a single snapshot from phone camera for face detection.

    Usage from phone:
    ```
    const formData = new FormData();
    formData.append('file', imageBlob);
    formData.append('camera_id', 'my-phone');

    fetch('http://server-ip:8000/phone-camera/snapshot', {
        method: 'POST',
        body: formData
    })
    ```
    """
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    # Create temporary session for snapshot
    session = phone_camera_service.create_session(
        camera_id=camera_id,
        device_info=device_info,
        location=location,
        scan_mode="snapshot"
    )

    try:
        # Read uploaded image
        contents = await file.read()
        nparr = np.frombuffer(contents, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is None:
            raise HTTPException(status_code=400, detail="Could not decode image")

        # Preprocess and detect
        processed = preprocess_frame(img)
        faces = detect_faces(processed)

        results = []
        alerts = []
        match_count = 0

        for face in faces:
            if face.embedding is not None:
                best_match_id, sim_score = matcher.match(face.embedding)

                threshold = settings.THRESHOLD_LOW_VARIANCE_DEFAULT
                person_name = None

                if best_match_id:
                    from app.database.db import get_db, MissingPerson
                    db = next(get_db())
                    try:
                        person = db.query(MissingPerson).filter(
                            MissingPerson.person_id == best_match_id
                        ).first()
                        if person:
                            threshold = person.match_threshold or threshold
                            person_name = person.name
                    finally:
                        db.close()

                is_match = best_match_id is not None and sim_score >= threshold

                if is_match:
                    match_count += 1

                results.append({
                    "bbox": face.bbox.astype(int).tolist(),
                    "best_match_id": best_match_id,
                    "person_name": person_name,
                    "similarity_score": round(float(sim_score), 4),
                    "threshold_used": round(float(threshold), 4),
                    "is_match": is_match
                })

                if is_match:
                    alerts.append({
                        "person_id": best_match_id,
                        "person_name": person_name,
                        "confidence": round(float(sim_score), 4)
                    })

        # Update session
        phone_camera_service.record_frame_processed(
            session.session_id,
            faces_detected=len(faces),
            matches_found=match_count
        )

        return JSONResponse(content={
            "session_id": session.session_id,
            "camera_id": camera_id,
            "face_count": len(faces),
            "detections": results,
            "alerts": alerts,
            "location": location
        })

    finally:
        # End snapshot session immediately
        phone_camera_service.end_session(session.session_id, "snapshot_complete")


@router.get("/phone-camera/status")
async def phone_camera_status():
    """Get status of active phone camera connections."""
    stats = phone_camera_service.get_stats()
    return JSONResponse(content={
        **stats,
        "websocket_connections": len(active_connections),
        "connected_cameras": list(active_connections.keys())
    })


@router.post("/phone-camera/cleanup")
async def cleanup_stale_sessions(max_idle_seconds: int = 300):
    """
    Clean up stale phone camera sessions.

    Args:
        max_idle_seconds: Maximum idle time before cleanup (default: 5 minutes)
    """
    cleaned = phone_camera_service.cleanup_stale_sessions(max_idle_seconds)
    return JSONResponse(content={
        "cleaned_sessions": cleaned,
        "remaining_sessions": len(phone_camera_service.get_active_sessions())
    })


def get_phone_camera_html():
    """Generate mobile-friendly HTML page for phone camera."""
    return '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <meta name="mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <title>Phone Camera - Missing Person AI</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            color: #fff;
            padding: 20px;
        }

        .container {
            max-width: 500px;
            margin: 0 auto;
        }

        h1 {
            text-align: center;
            margin-bottom: 10px;
            font-size: 1.5rem;
            color: #00d9ff;
        }

        .subtitle {
            text-align: center;
            color: #aaa;
            font-size: 0.85rem;
            margin-bottom: 20px;
        }

        .status-bar {
            background: rgba(255,255,255,0.1);
            border-radius: 12px;
            padding: 15px;
            margin-bottom: 20px;
            backdrop-filter: blur(10px);
        }

        .status-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }

        .status-item:last-child {
            margin-bottom: 0;
        }

        .status-label {
            color: #aaa;
            font-size: 0.9rem;
        }

        .status-value {
            font-weight: 600;
        }

        .status-value.connected {
            color: #00ff88;
        }

        .status-value.disconnected {
            color: #ff4757;
        }

        .status-value.streaming {
            color: #00d9ff;
            animation: pulse 1s infinite;
        }

        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }

        .video-container {
            position: relative;
            background: #000;
            border-radius: 16px;
            overflow: hidden;
            margin-bottom: 20px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.5);
        }

        #video {
            width: 100%;
            display: block;
        }

        #canvas {
            display: none;
        }

        .overlay {
            position: absolute;
            top: 10px;
            left: 10px;
            right: 10px;
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }

        .badge {
            background: rgba(0,0,0,0.7);
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 0.75rem;
            backdrop-filter: blur(5px);
        }

        .badge.alert {
            background: rgba(255,71,87,0.9);
            animation: pulse 1s infinite;
        }

        .badge.match {
            background: rgba(0,255,136,0.9);
            color: #1a1a2e;
        }

        .controls {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
            justify-content: center;
        }

        button {
            flex: 1;
            min-width: 120px;
            padding: 16px 24px;
            border: none;
            border-radius: 12px;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        button:active {
            transform: scale(0.98);
        }

        #startBtn {
            background: linear-gradient(135deg, #00d9ff, #00ff88);
            color: #1a1a2e;
        }

        #startBtn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }

        #stopBtn {
            background: rgba(255,255,255,0.1);
            color: #fff;
            border: 2px solid rgba(255,255,255,0.3);
        }

        #snapshotBtn {
            background: rgba(255,255,255,0.1);
            color: #fff;
            border: 2px solid rgba(255,255,255,0.3);
        }

        .input-group {
            margin-bottom: 15px;
        }

        .input-group label {
            display: block;
            color: #aaa;
            font-size: 0.85rem;
            margin-bottom: 5px;
        }

        .input-group input, .input-group select {
            width: 100%;
            padding: 12px;
            border-radius: 8px;
            border: 1px solid rgba(255,255,255,0.2);
            background: rgba(255,255,255,0.1);
            color: #fff;
            font-size: 0.9rem;
        }

        .input-group input::placeholder {
            color: #666;
        }

        .input-group option {
            background: #1a1a2e;
            color: #fff;
        }

        .results-panel {
            background: rgba(255,255,255,0.05);
            border-radius: 12px;
            padding: 15px;
            margin-top: 20px;
            max-height: 250px;
            overflow-y: auto;
        }

        .results-panel h3 {
            margin-bottom: 10px;
            font-size: 0.9rem;
            color: #00d9ff;
        }

        .result-item {
            background: rgba(255,255,255,0.05);
            padding: 10px;
            border-radius: 8px;
            margin-bottom: 8px;
            font-size: 0.85rem;
        }

        .result-item.match {
            background: rgba(0,255,136,0.2);
            border: 1px solid #00ff88;
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 10px;
            margin-top: 15px;
        }

        .stat-card {
            background: rgba(255,255,255,0.05);
            padding: 10px;
            border-radius: 8px;
            text-align: center;
        }

        .stat-value {
            font-size: 1.25rem;
            font-weight: bold;
            color: #00d9ff;
        }

        .stat-label {
            font-size: 0.75rem;
            color: #aaa;
            margin-top: 4px;
        }

        .fps-counter {
            text-align: center;
            font-size: 0.8rem;
            color: #666;
            margin-top: 15px;
        }

        .session-info {
            background: rgba(0,217,255,0.1);
            border: 1px solid rgba(0,217,255,0.3);
            border-radius: 8px;
            padding: 10px;
            margin-bottom: 15px;
            font-size: 0.8rem;
            word-break: break-all;
        }

        .session-info strong {
            color: #00d9ff;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📱 Phone Camera</h1>
        <p class="subtitle">Scan for missing persons using your phone camera</p>

        <div class="status-bar">
            <div class="status-item">
                <span class="status-label">Connection</span>
                <span class="status-value disconnected" id="connectionStatus">Disconnected</span>
            </div>
            <div class="status-item">
                <span class="status-label">Session</span>
                <span class="status-value" id="sessionStatus">--</span>
            </div>
            <div class="status-item">
                <span class="status-label">Processing</span>
                <span class="status-value" id="processingStatus">--</span>
            </div>
        </div>

        <div class="video-container">
            <video id="video" autoplay playsinline muted></video>
            <canvas id="canvas"></canvas>
            <div class="overlay" id="overlay"></div>
        </div>

        <div class="input-group">
            <label>Camera</label>
            <select id="cameraSelect">
                <option value="">Select Camera</option>
            </select>
        </div>

        <div class="input-group">
            <label>Device Name (optional)</label>
            <input type="text" id="deviceName" placeholder="e.g., Officer John's Phone">
        </div>

        <div class="input-group">
            <label>Location (optional)</label>
            <input type="text" id="locationInput" placeholder="e.g., Market Square">
        </div>

        <div id="sessionInfo" class="session-info" style="display: none;"></div>

        <div class="controls">
            <button id="startBtn">▶ Start Scan</button>
            <button id="stopBtn" disabled>⏹ Stop</button>
            <button id="snapshotBtn">📸 Snapshot</button>
        </div>

        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value" id="frameCount">0</div>
                <div class="stat-label">Frames</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="faceCount">0</div>
                <div class="stat-label">Faces</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="matchCount">0</div>
                <div class="stat-label">Matches</div>
            </div>
        </div>

        <div class="results-panel" id="resultsPanel" style="display: none;">
            <h3>🔍 Recent Detections</h3>
            <div id="resultsContent"></div>
        </div>

        <div class="fps-counter" id="fpsCounter"></div>
    </div>

    <script>
        const API_URL = window.location.origin;

        let ws = null;
        let stream = null;
        let video = document.getElementById('video');
        let canvas = document.getElementById('canvas');
        let ctx = canvas.getContext('2d');
        let cameraId = 'phone-' + Math.random().toString(36).substr(2, 9);
        let sessionId = null;
        let isStreaming = false;
        let frameCount = 0;
        let lastFpsTime = Date.now();
        let totalFaces = 0;
        let totalMatches = 0;

        const connectionStatus = document.getElementById('connectionStatus');
        const sessionStatus = document.getElementById('sessionStatus');
        const processingStatus = document.getElementById('processingStatus');
        const overlay = document.getElementById('overlay');
        const resultsPanel = document.getElementById('resultsPanel');
        const resultsContent = document.getElementById('resultsContent');
        const fpsCounter = document.getElementById('fpsCounter');
        const startBtn = document.getElementById('startBtn');
        const stopBtn = document.getElementById('stopBtn');
        const snapshotBtn = document.getElementById('snapshotBtn');
        const cameraSelect = document.getElementById('cameraSelect');
        const deviceName = document.getElementById('deviceName');
        const locationInput = document.getElementById('locationInput');
        const sessionInfo = document.getElementById('sessionInfo');

        // Load available cameras
        async function loadCameras() {
            try {
                const devices = await navigator.mediaDevices.enumerateDevices();
                const videoDevices = devices.filter(d => d.kind === 'videoinput');

                cameraSelect.innerHTML = '<option value="">Select Camera</option>';
                videoDevices.forEach((device, index) => {
                    const option = document.createElement('option');
                    option.value = device.deviceId;
                    option.text = device.label || `Camera ${index + 1}`;
                    cameraSelect.appendChild(option);
                });
            } catch (err) {
                console.error('Error loading cameras:', err);
            }
        }

        // Start camera stream
        async function startCamera() {
            try {
                const constraints = {
                    video: {
                        deviceId: cameraSelect.value ? { exact: cameraSelect.value } : undefined,
                        facingMode: 'environment',
                        width: { ideal: 1280 },
                        height: { ideal: 720 }
                    }
                };

                stream = await navigator.mediaDevices.getUserMedia(constraints);
                video.srcObject = stream;

                return new Promise((resolve) => {
                    video.onloadedmetadata = () => {
                        canvas.width = video.videoWidth;
                        canvas.height = video.videoHeight;
                        resolve();
                    };
                });
            } catch (err) {
                console.error('Camera error:', err);
                throw err;
            }
        }

        // Start scan session
        async function startScanSession() {
            try {
                const response = await fetch(`${API_URL}/phone-camera/scan/start`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        camera_id: cameraId,
                        device_name: deviceName.value || undefined,
                        location: locationInput.value || undefined,
                        scan_mode: 'realtime'
                    })
                });

                const data = await response.json();
                if (data.status === 'started') {
                    sessionId = data.session_id;
                    sessionStatus.textContent = 'Active';
                    sessionInfo.style.display = 'block';
                    sessionInfo.innerHTML = `<strong>Session ID:</strong> ${sessionId}<br><strong>Camera ID:</strong> ${data.camera_id}`;
                    return data.websocket_url;
                }
                throw new Error('Failed to start session');
            } catch (err) {
                console.error('Session start error:', err);
                throw err;
            }
        }

        // Connect WebSocket
        function connectWebSocket(wsUrl) {
            ws = new WebSocket(wsUrl);

            ws.onopen = () => {
                connectionStatus.textContent = 'Connected';
                connectionStatus.className = 'status-value connected';
            };

            ws.onclose = () => {
                connectionStatus.textContent = 'Disconnected';
                connectionStatus.className = 'status-value disconnected';
            };

            ws.onerror = (err) => {
                console.error('WebSocket error:', err);
                connectionStatus.textContent = 'Error';
            };

            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);

                if (data.status === 'success') {
                    processingStatus.textContent = `${data.processing_time_ms}ms`;

                    if (data.face_count > 0) {
                        totalFaces += data.face_count;
                        document.getElementById('faceCount').textContent = totalFaces;
                    }

                    if (data.alerts && data.alerts.length > 0) {
                        totalMatches += data.alerts.length;
                        document.getElementById('matchCount').textContent = totalMatches;
                        showAlerts(data.alerts);
                    }

                    // Update results panel
                    if (data.detections.length > 0) {
                        updateResults(data.detections);
                    }
                }
            };
        }

        // Show alert badges
        function showAlerts(alerts) {
            alerts.forEach(alert => {
                const badge = document.createElement('div');
                badge.className = 'badge alert';
                badge.textContent = `⚠️ MATCH: ${alert.person_name || alert.person_id}`;
                overlay.appendChild(badge);

                setTimeout(() => badge.remove(), 5000);
            });
        }

        // Update results panel
        function updateResults(detections) {
            resultsPanel.style.display = 'block';

            const html = detections.map(d => `
                <div class="result-item ${d.is_match ? 'match' : ''}">
                    <strong>${d.is_match ? '✅ MATCH FOUND' : '❌ No Match'}</strong><br>
                    ${d.person_name ? `Name: ${d.person_name}<br>` : ''}
                    Confidence: ${(d.similarity_score * 100).toFixed(1)}%<br>
                    ${d.best_match_id ? `Person ID: ${d.best_match_id}` : ''}
                </div>
            `).join('');

            resultsContent.innerHTML = html + resultsContent.innerHTML;

            // Keep only last 10 results
            const items = resultsContent.querySelectorAll('.result-item');
            if (items.length > 10) {
                for (let i = 10; i < items.length; i++) {
                    items[i].remove();
                }
            }
        }

        // Send frame to server
        function sendFrame() {
            if (!ws || ws.readyState !== WebSocket.OPEN || !isStreaming) return;

            ctx.drawImage(video, 0, 0);
            const imageData = canvas.toDataURL('image/jpeg', 0.7);
            const base64 = imageData.split(',')[1];

            ws.send(JSON.stringify({
                frame: base64,
                camera_id: cameraId
            }));

            frameCount++;
            document.getElementById('frameCount').textContent = frameCount;

            // Calculate FPS
            const now = Date.now();
            if (now - lastFpsTime >= 1000) {
                fpsCounter.textContent = `FPS: ${frameCount} | Resolution: ${video.videoWidth}x${video.videoHeight}`;
                frameCount = 0;
                lastFpsTime = now;
            }
        }

        // Take snapshot
        async function takeSnapshot() {
            ctx.drawImage(video, 0, 0);

            canvas.toBlob(async (blob) => {
                const formData = new FormData();
                formData.append('file', blob, 'snapshot.jpg');
                formData.append('camera_id', cameraId);
                formData.append('location', locationInput.value);
                formData.append('device_info', deviceName.value);

                try {
                    const response = await fetch(`${API_URL}/phone-camera/snapshot`, {
                        method: 'POST',
                        body: formData
                    });

                    const data = await response.json();

                    document.getElementById('faceCount').textContent =
                        parseInt(document.getElementById('faceCount').textContent) + data.face_count;

                    if (data.alerts && data.alerts.length > 0) {
                        document.getElementById('matchCount').textContent =
                            parseInt(document.getElementById('matchCount').textContent) + data.alerts.length;
                        showAlerts(data.alerts);
                    }

                    if (data.detections.length > 0) {
                        updateResults(data.detections);
                    }
                } catch (err) {
                    console.error('Snapshot error:', err);
                }
            }, 'image/jpeg', 0.9);
        }

        // Start streaming
        async function startStreaming() {
            try {
                await startCamera();
                const wsUrl = await startScanSession();
                connectWebSocket(wsUrl);
                isStreaming = true;

                startBtn.disabled = true;
                stopBtn.disabled = false;
                snapshotBtn.disabled = false;
                connectionStatus.textContent = 'Connecting...';
                connectionStatus.className = 'status-value streaming';

                // Send frames at ~10 FPS
                setInterval(sendFrame, 100);
            } catch (err) {
                alert('Error starting scan: ' + err.message);
                console.error(err);
            }
        }

        // Stop streaming
        async function stopStreaming() {
            isStreaming = false;

            if (sessionId) {
                try {
                    await fetch(`${API_URL}/phone-camera/scan/${sessionId}/stop`, {
                        method: 'POST'
                    });
                } catch (err) {
                    console.error('Error stopping session:', err);
                }
            }

            if (stream) {
                stream.getTracks().forEach(track => track.stop());
                stream = null;
            }

            if (ws) {
                ws.close();
                ws = null;
            }

            video.srcObject = null;

            startBtn.disabled = false;
            stopBtn.disabled = true;
            snapshotBtn.disabled = true;

            connectionStatus.textContent = 'Disconnected';
            connectionStatus.className = 'status-value disconnected';
            sessionStatus.textContent = '--';
            processingStatus.textContent = '--';
            sessionInfo.style.display = 'none';
            overlay.innerHTML = '';
        }

        // Event listeners
        startBtn.addEventListener('click', startStreaming);
        stopBtn.addEventListener('click', stopStreaming);
        snapshotBtn.addEventListener('click', takeSnapshot);
        cameraSelect.addEventListener('change', () => {
            if (isStreaming) {
                stopStreaming();
                setTimeout(startStreaming, 100);
            }
        });

        // Initialize
        loadCameras();
        snapshotBtn.disabled = true;

        // Request camera permission on load
        navigator.mediaDevices.getUserMedia({ video: true })
            .then(s => { s.getTracks().forEach(t => t.stop()); })
            .catch(() => {});
    </script>
</body>
</html>
'''
