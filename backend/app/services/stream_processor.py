import cv2
import threading
from app.services.face_detector import detect_faces
from app.services.matcher import matcher
from app.database.db import SessionLocal, DetectionEvent
import os
import uuid

class StreamProcessor:
    def __init__(self):
        self.active_streams = {} # camera_id -> Thread

    def start_stream(self, camera_url: str, camera_id: str):
        if camera_id in self.active_streams:
            return False

        thread = threading.Thread(target=self._process_stream, args=(camera_url, camera_id), daemon=True)
        thread.start()
        self.active_streams[camera_id] = thread
        return True

    def _process_stream(self, camera_url: str, camera_id: str):
        # Allow passing an integer for local webcam via URL
        if camera_url.isdigit():
            camera_url = int(camera_url)
            
        cap = cv2.VideoCapture(camera_url)
        frame_count = 0
        skip_frames = 5 # Process every 5th frame for MVP

        os.makedirs("data/snapshots", exist_ok=True)

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            
            frame_count += 1
            if frame_count % skip_frames != 0:
                continue

            faces = detect_faces(frame)
            
            db = SessionLocal()
            for face in faces:
                if face.embedding is None:
                    continue
                    
                best_match_id, sim_score = matcher.match(face.embedding)
                
                if best_match_id is not None:
                    snapshot_filename = f"data/snapshots/{uuid.uuid4().hex}.jpg"
                    
                    # Draw bbox
                    bbox = face.bbox.astype(int)
                    cv2.rectangle(frame, (bbox[0], bbox[1]), (bbox[2], bbox[3]), (0, 0, 255), 2)
                    cv2.imwrite(snapshot_filename, frame)
                    
                    event = DetectionEvent(
                        person_id=best_match_id,
                        camera_id=camera_id,
                        similarity_score=float(sim_score),
                        snapshot_path=snapshot_filename
                    )
                    db.add(event)
                    db.commit()
                    print(f"ALERT! Person {best_match_id} detected on camera {camera_id} with similarity {sim_score:.2f}")

            db.close()
            
        cap.release()
        if camera_id in self.active_streams:
            del self.active_streams[camera_id]

stream_processor = StreamProcessor()
