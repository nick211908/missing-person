"""
Phone Camera Session Management Service.

Manages active phone camera sessions, scan history, and session persistence.
"""

from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, field
import uuid


@dataclass
class PhoneCameraSession:
    """Active phone camera session data."""
    session_id: str
    camera_id: str
    device_info: Optional[str] = None
    connected_at: datetime = field(default_factory=datetime.utcnow)
    last_frame_at: Optional[datetime] = None
    status: str = "connected"  # connected, streaming, disconnected, error
    frames_processed: int = 0
    faces_detected: int = 0
    matches_found: int = 0
    ip_address: Optional[str] = None
    location: Optional[str] = None
    scan_mode: str = "realtime"


@dataclass
class ScanSession:
    """Completed scan session record."""
    scan_id: str
    camera_id: str
    device_info: Optional[str]
    started_at: datetime
    ended_at: datetime
    total_frames: int
    total_faces: int
    total_matches: int
    location: Optional[str]
    snapshots: List[str] = field(default_factory=list)


class PhoneCameraService:
    """
    Service for managing phone camera sessions and scan history.
    """

    def __init__(self):
        self._active_sessions: Dict[str, PhoneCameraSession] = {}
        self._camera_to_session: Dict[str, str] = {}
        self._scan_history: List[ScanSession] = []

    def create_session(
        self,
        camera_id: str,
        device_info: Optional[str] = None,
        ip_address: Optional[str] = None,
        location: Optional[str] = None,
        scan_mode: str = "realtime"
    ) -> PhoneCameraSession:
        """
        Create a new phone camera session.

        Args:
            camera_id: Unique identifier for the camera
            device_info: Device information (model, OS, etc.)
            ip_address: Client IP address
            location: Physical location of the scan
            scan_mode: "realtime" or "snapshot"

        Returns:
            New session object
        """
        session_id = str(uuid.uuid4())

        # Disconnect existing session for this camera
        if camera_id in self._camera_to_session:
            old_session_id = self._camera_to_session[camera_id]
            self.end_session(old_session_id, "replaced_by_new")

        session = PhoneCameraSession(
            session_id=session_id,
            camera_id=camera_id,
            device_info=device_info,
            ip_address=ip_address,
            location=location,
            scan_mode=scan_mode,
            status="connected"
        )

        self._active_sessions[session_id] = session
        self._camera_to_session[camera_id] = session_id

        return session

    def get_session(self, session_id: str) -> Optional[PhoneCameraSession]:
        """Get session by ID."""
        return self._active_sessions.get(session_id)

    def get_session_by_camera(self, camera_id: str) -> Optional[PhoneCameraSession]:
        """Get active session for a camera."""
        session_id = self._camera_to_session.get(camera_id)
        if session_id:
            return self._active_sessions.get(session_id)
        return None

    def update_session_status(self, session_id: str, status: str) -> bool:
        """Update session status."""
        session = self._active_sessions.get(session_id)
        if session:
            session.status = status
            if status == "streaming":
                session.last_frame_at = datetime.utcnow()
            return True
        return False

    def record_frame_processed(
        self,
        session_id: str,
        faces_detected: int = 0,
        matches_found: int = 0
    ) -> bool:
        """Record frame processing statistics."""
        session = self._active_sessions.get(session_id)
        if session:
            session.frames_processed += 1
            session.faces_detected += faces_detected
            session.matches_found += matches_found
            session.last_frame_at = datetime.utcnow()
            return True
        return False

    def end_session(self, session_id: str, reason: str = "disconnected") -> Optional[ScanSession]:
        """
        End an active session and optionally save to history.

        Args:
            session_id: Session ID to end
            reason: Reason for ending (disconnected, error, replaced_by_new)

        Returns:
            ScanSession record if saved to history
        """
        session = self._active_sessions.get(session_id)
        if not session:
            return None

        # Create scan record
        scan_record = ScanSession(
            scan_id=session_id,
            camera_id=session.camera_id,
            device_info=session.device_info,
            started_at=session.connected_at,
            ended_at=datetime.utcnow(),
            total_frames=session.frames_processed,
            total_faces=session.faces_detected,
            total_matches=session.matches_found,
            location=session.location
        )

        self._scan_history.append(scan_record)

        # Cleanup active session
        self._active_sessions.pop(session_id, None)
        if session.camera_id in self._camera_to_session:
            if self._camera_to_session[session.camera_id] == session_id:
                del self._camera_to_session[session.camera_id]

        return scan_record

    def get_active_sessions(self) -> List[PhoneCameraSession]:
        """Get all active sessions."""
        return list(self._active_sessions.values())

    def get_scan_history(
        self,
        limit: int = 100,
        camera_id: Optional[str] = None
    ) -> List[ScanSession]:
        """Get scan history, optionally filtered by camera."""
        history = self._scan_history
        if camera_id:
            history = [s for s in history if s.camera_id == camera_id]
        return sorted(history, key=lambda x: x.started_at, reverse=True)[:limit]

    def get_stats(self) -> dict:
        """Get overall phone camera statistics."""
        return {
            "active_sessions": len(self._active_sessions),
            "total_scans": len(self._scan_history),
            "total_frames_processed": sum(s.total_frames for s in self._scan_history),
            "total_faces_detected": sum(s.total_faces for s in self._scan_history),
            "total_matches": sum(s.total_matches for s in self._scan_history),
            "active_cameras": list(self._camera_to_session.keys())
        }

    def cleanup_stale_sessions(self, max_idle_seconds: int = 300) -> int:
        """
        Remove sessions that haven't had activity.

        Args:
            max_idle_seconds: Maximum idle time before cleanup

        Returns:
            Number of sessions cleaned up
        """
        now = datetime.utcnow()
        stale_sessions = []

        for session_id, session in self._active_sessions.items():
            if session.last_frame_at:
                idle_time = (now - session.last_frame_at).total_seconds()
                if idle_time > max_idle_seconds:
                    stale_sessions.append(session_id)
            else:
                # No frames received since connection
                connect_time = (now - session.connected_at).total_seconds()
                if connect_time > max_idle_seconds:
                    stale_sessions.append(session_id)

        for session_id in stale_sessions:
            self.end_session(session_id, "stale_timeout")

        return len(stale_sessions)


# Global service instance
phone_camera_service = PhoneCameraService()
