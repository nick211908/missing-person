# Phone Camera Scan Backend

This module enables real-time face detection and missing person matching using mobile phone cameras.

## Features

- **WebSocket Streaming**: Real-time face detection with low latency
- **HTTP Snapshot**: Single image upload for quick checks
- **Session Management**: Track active scans with detailed metadata
- **Mobile-Friendly UI**: Built-in web interface optimized for phones
- **Scan History**: Historical record of all phone camera scans

## API Endpoints

### Session Management

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/phone-camera` | GET | Mobile-friendly web interface |
| `/phone-camera/scan/start` | POST | Start a new scan session |
| `/phone-camera/scan/{session_id}/stop` | POST | Stop an active scan session |
| `/phone-camera/sessions` | GET | List all active sessions |
| `/phone-camera/sessions/{session_id}` | GET | Get session details |
| `/phone-camera/history` | GET | View scan history |
| `/phone-camera/stats` | GET | Get overall statistics |
| `/phone-camera/status` | GET | Get connection status |
| `/phone-camera/cleanup` | POST | Clean up stale sessions |

### Frame Processing

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/ws/phone-camera/{session_id}` | WebSocket | Real-time frame streaming |
| `/phone-camera/scan/{session_id}/frame` | POST | Process single frame via HTTP |
| `/phone-camera/snapshot` | POST | Upload image snapshot |

## Usage Examples

### 1. Start a Scan Session

```bash
curl -X POST http://localhost:8000/phone-camera/scan/start \
  -H "Content-Type: application/json" \
  -d '{
    "camera_id": "officer-john-phone",
    "device_name": "John\\'s iPhone",
    "location": "Market Square",
    "scan_mode": "realtime"
  }'
```

Response:
```json
{
  "session_id": "uuid-string",
  "camera_id": "officer-john-phone",
  "websocket_url": "ws://localhost:8000/ws/phone-camera/uuid-string",
  "status": "started",
  "message": "Scan session started for camera officer-john-phone"
}
```

### 2. Connect via WebSocket

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/phone-camera/{session_id}');

ws.onopen = () => console.log('Connected');
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Detections:', data.detections);
  console.log('Alerts:', data.alerts);
};

// Send frame (base64 encoded JPEG)
ws.send(JSON.stringify({
  frame: base64EncodedImage,
  camera_id: 'officer-john-phone'
}));
```

### 3. Process Single Frame via HTTP

```bash
curl -X POST http://localhost:8000/phone-camera/scan/{session_id}/frame \
  -H "Content-Type: application/json" \
  -d '{
    "frame": "base64encodedimage...",
    "camera_id": "officer-john-phone",
    "location": "Market Square"
  }'
```

### 4. Upload Snapshot

```bash
curl -X POST http://localhost:8000/phone-camera/snapshot \
  -F "file=@photo.jpg" \
  -F "camera_id=officer-john-phone" \
  -F "location=Market Square"
```

### 5. Stop Scan Session

```bash
curl -X POST http://localhost:8000/phone-camera/scan/{session_id}/stop
```

## Web Interface

Access the mobile-friendly web interface at:
```
http://localhost:8000/phone-camera
```

The web interface provides:
- Camera selection
- Real-time streaming
- Face detection visualization
- Match alerts
- Scan statistics
- Snapshot capture

## Session States

- `connected`: Session created, waiting for first frame
- `streaming`: Actively receiving and processing frames
- `disconnected`: Session ended normally
- `error`: Session ended due to error

## Response Format

### Detection Result

```json
{
  "status": "success",
  "face_count": 2,
  "detections": [
    {
      "bbox": [100, 100, 200, 250],
      "best_match_id": 123,
      "person_name": "John Doe",
      "similarity_score": 0.89,
      "threshold_used": 0.75,
      "is_match": true
    }
  ],
  "alerts": [
    {
      "person_id": 123,
      "person_name": "John Doe",
      "confidence": 0.89,
      "camera_id": "officer-john-phone"
    }
  ],
  "timestamp": 1711234567.89,
  "processing_time_ms": 45.23
}
```

## Statistics

The system tracks:
- Active sessions count
- Total scans performed
- Frames processed
- Faces detected
- Matches found
- Processing times

## Mobile App Integration

To integrate with a mobile app:

1. **Start Session**: Call `/phone-camera/scan/start`
2. **Connect WebSocket**: Use the returned `websocket_url`
3. **Stream Frames**: Send base64-encoded JPEG frames
4. **Handle Responses**: Process detection results and alerts
5. **Stop Session**: Call `/phone-camera/scan/{session_id}/stop` when done

## Security Considerations

- All endpoints (except web interface) should use authentication
- Session IDs are UUID-based for security
- Sessions auto-expire after 5 minutes of inactivity
- IP addresses are logged for audit purposes

## Configuration

Session cleanup runs every 5 minutes. Adjust in `main.py`:

```python
# Cleanup interval (seconds)
await asyncio.sleep(300)

# Max idle time before cleanup (seconds)
phone_camera_service.cleanup_stale_sessions(max_idle_seconds=300)
```
