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

        import supervision as sv
        tracker = sv.ByteTrack()
        tracklet_history = {} # track_id -> {'person_id': ..., 'scores': []}
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            
            frame_count += 1
            if frame_count % skip_frames != 0:
                continue

            faces = detect_faces(frame)
            
            if len(faces) == 0:
                continue
                
            xyxy = np.array([face.bbox for face in faces])
            confidence = np.array([face.confidence for face in faces])
            class_id = np.arange(len(faces))
            detections = sv.Detections(xyxy=xyxy, confidence=confidence, class_id=class_id)
            tracks = tracker.update_with_detections(detections=detections)
            
            db = SessionLocal()
            for i in range(len(tracks.xyxy)):
                track_id = tracks.tracker_id[i]
                original_idx = tracks.class_id[i]
                face = faces[original_idx]
                
                if face.embedding is None:
                    continue
                    
                best_match_id, sim_score = matcher.match(face.embedding)
                
                if best_match_id is not None:
                    threshold = 0.55
                    person = db.query(MissingPerson).filter(MissingPerson.person_id == best_match_id).first()
                    if person and person.match_threshold:
                        threshold = person.match_threshold
                        
                    if track_id not in tracklet_history:
                        tracklet_history[track_id] = {'person_id': best_match_id, 'scores': []}
                        
                    if tracklet_history[track_id]['person_id'] != best_match_id:
                        tracklet_history[track_id] = {'person_id': best_match_id, 'scores': [sim_score]}
                    else:
                        tracklet_history[track_id]['scores'].append(sim_score)
                        
                    avg_score = sum(tracklet_history[track_id]['scores']) / len(tracklet_history[track_id]['scores'])
                    
                    # Require at least 2 consecutive positive evaluations over a tracklet to trigger alert
                    if avg_score >= threshold and len(tracklet_history[track_id]['scores']) >= 2:
                        snapshot_filename = f"data/snapshots/{uuid.uuid4().hex}.jpg"
                        
                        # Draw bbox
                        bbox = face.bbox.astype(int)
                        cv2.rectangle(frame, (bbox[0], bbox[1]), (bbox[2], bbox[3]), (0, 0, 255), 2)
                        cv2.putText(frame, f"ID: {track_id} Match: {avg_score:.2f}", (bbox[0], bbox[1]-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,0,255), 2)
                        cv2.imwrite(snapshot_filename, frame)
                        
                        event = DetectionEvent(
                            person_id=best_match_id,
                            camera_id=camera_id,
                            similarity_score=float(avg_score),
                            snapshot_path=snapshot_filename
                        )
                        db.add(event)
                        db.commit()
                        print(f"ALERT! Person {best_match_id} detected on camera {camera_id} with avg similarity {avg_score:.2f}")
                        
                        # Reset scores to prevent immediate duplicate alerts for same track
                        tracklet_history[track_id]['scores'] = []

            db.close()
            
        cap.release()
        if camera_id in self.active_streams:
            del self.active_streams[camera_id]

stream_processor = StreamProcessor()
