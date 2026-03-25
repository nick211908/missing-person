import React, { useState, useRef, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Smartphone, AlertTriangle, Activity, Camera, X, Power, MapPin, User, Scan, Clock } from 'lucide-react';
import { useAuth, API_BASE } from '../context/AuthContext';

const PhoneCamera = () => {
  const { authFetch } = useAuth();
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const wsRef = useRef(null);

  // Connection state
  const [sessionId, setSessionId] = useState(null);
  const [cameraId, setCameraId] = useState(`phone-${Math.random().toString(36).substr(2, 9)}`);
  const [isConnected, setIsConnected] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState('disconnected'); // disconnected, connecting, connected, error

  // Device info
  const [deviceName, setDeviceName] = useState('');
  const [location, setLocation] = useState('');
  const [selectedCamera, setSelectedCamera] = useState('');
  const [availableCameras, setAvailableCameras] = useState([]);

  // Stats
  const [frameCount, setFrameCount] = useState(0);
  const [faceCount, setFaceCount] = useState(0);
  const [matchCount, setMatchCount] = useState(0);
  const [processingTime, setProcessingTime] = useState(0);
  const [fps, setFps] = useState(0);

  // Logs and alerts
  const [logs, setLogs] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [detections, setDetections] = useState([]);

  // Add log helper
  const addLog = useCallback((message, type = 'info', metadata = null) => {
    setLogs(prev => [{
      id: Date.now() + Math.random(),
      time: new Date().toLocaleTimeString(),
      message,
      type,
      metadata
    }, ...prev].slice(0, 50));
  }, []);

  // Load available cameras
  useEffect(() => {
    const loadCameras = async () => {
      try {
        const devices = await navigator.mediaDevices.enumerateDevices();
        const videoDevices = devices.filter(d => d.kind === 'videoinput');
        setAvailableCameras(videoDevices);
        if (videoDevices.length > 0 && !selectedCamera) {
          setSelectedCamera(videoDevices[0].deviceId);
        }
      } catch (err) {
        console.error('Error loading cameras:', err);
        addLog('Failed to enumerate cameras', 'error');
      }
    };

    loadCameras();

    // Request permission to get device labels
    navigator.mediaDevices.getUserMedia({ video: true })
      .then(stream => {
        stream.getTracks().forEach(t => t.stop());
        loadCameras();
      })
      .catch(() => {});
  }, [addLog]);

  // Start camera stream
  const startCamera = async () => {
    try {
      const constraints = {
        video: {
          deviceId: selectedCamera ? { exact: selectedCamera } : undefined,
          facingMode: 'environment',
          width: { ideal: 1280 },
          height: { ideal: 720 }
        }
      };

      const stream = await navigator.mediaDevices.getUserMedia(constraints);
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }
      return stream;
    } catch (err) {
      console.error('Camera error:', err);
      addLog('Camera access denied or unavailable', 'error');
      throw err;
    }
  };

  // Start scan session
  const startSession = async () => {
    try {
      setConnectionStatus('connecting');
      addLog('Starting phone camera session...', 'info');

      const response = await authFetch(`${API_BASE}/phone-camera/scan/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          camera_id: cameraId,
          device_name: deviceName || undefined,
          location: location || undefined,
          scan_mode: 'realtime'
        })
      });

      const data = await response.json();
      if (response.ok && data.status === 'started') {
        setSessionId(data.session_id);
        setConnectionStatus('connected');
        addLog(`Session started: ${data.session_id}`, 'success');
        return data.websocket_url;
      } else {
        throw new Error(data.detail || 'Failed to start session');
      }
    } catch (err) {
      console.error('Session start error:', err);
      setConnectionStatus('error');
      addLog(`Failed to start session: ${err.message}`, 'error');
      throw err;
    }
  };

  // Connect WebSocket
  const connectWebSocket = (wsUrl) => {
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setIsConnected(true);
      setIsStreaming(true);
      setConnectionStatus('connected');
      addLog('WebSocket connected - streaming started', 'success');
    };

    ws.onclose = () => {
      setIsConnected(false);
      setIsStreaming(false);
      setConnectionStatus('disconnected');
      addLog('WebSocket disconnected', 'info');
    };

    ws.onerror = (err) => {
      console.error('WebSocket error:', err);
      setConnectionStatus('error');
      addLog('WebSocket error', 'error');
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.status === 'success') {
        setFrameCount(prev => prev + 1);
        setProcessingTime(data.processing_time_ms || 0);

        if (data.face_count > 0) {
          setFaceCount(prev => prev + data.face_count);
          setDetections(prev => [data, ...prev].slice(0, 10));
        }

        if (data.alerts && data.alerts.length > 0) {
          setMatchCount(prev => prev + data.alerts.length);
          setAlerts(prev => [...data.alerts.map(a => ({ ...a, timestamp: Date.now() })), ...prev].slice(0, 20));

          data.alerts.forEach(alert => {
            addLog(
              `MATCH: Person ${alert.person_name || alert.person_id} (${(alert.confidence * 100).toFixed(1)}%)`,
              'alert',
              alert
            );
          });
        }
      } else if (data.error) {
        addLog(`Server error: ${data.error}`, 'error');
      }
    };
  };

  // Send frame to server
  const sendFrame = useCallback(() => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN || !isStreaming) return;

    const canvas = canvasRef.current;
    const video = videoRef.current;
    if (!canvas || !video) return;

    const ctx = canvas.getContext('2d');
    canvas.width = video.videoWidth || 640;
    canvas.height = video.videoHeight || 480;
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    const imageData = canvas.toDataURL('image/jpeg', 0.7);
    const base64 = imageData.split(',')[1];

    wsRef.current.send(JSON.stringify({
      frame: base64,
      camera_id: cameraId
    }));
  }, [isStreaming, cameraId]);

  // Frame sending loop
  useEffect(() => {
    if (!isStreaming) return;

    const interval = setInterval(() => {
      sendFrame();
    }, 100); // 10 FPS

    // Calculate FPS
    const fpsInterval = setInterval(() => {
      setFps(prev => {
        // Approximate FPS based on frame count
        return 10;
      });
    }, 1000);

    return () => {
      clearInterval(interval);
      clearInterval(fpsInterval);
    };
  }, [isStreaming, sendFrame]);

  // Start streaming
  const startStreaming = async () => {
    try {
      await startCamera();
      const wsUrl = await startSession();
      connectWebSocket(wsUrl);
    } catch (err) {
      console.error('Start streaming error:', err);
    }
  };

  // Stop streaming
  const stopStreaming = async () => {
    setIsStreaming(false);

    if (sessionId) {
      try {
        await authFetch(`${API_BASE}/phone-camera/scan/${sessionId}/stop`, {
          method: 'POST'
        });
        addLog('Session stopped', 'info');
      } catch (err) {
        console.error('Error stopping session:', err);
      }
    }

    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    // Stop camera
    if (videoRef.current && videoRef.current.srcObject) {
      videoRef.current.srcObject.getTracks().forEach(track => track.stop());
      videoRef.current.srcObject = null;
    }

    setIsConnected(false);
    setConnectionStatus('disconnected');
    setSessionId(null);
  };

  // Clear stats
  const clearStats = () => {
    setFrameCount(0);
    setFaceCount(0);
    setMatchCount(0);
    setProcessingTime(0);
    setFps(0);
    setDetections([]);
    setAlerts([]);
    setLogs([]);
  };

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopStreaming();
    };
  }, []);

  return (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -20 }}
      transition={{ duration: 0.5 }}
      style={{ display: 'flex', gap: '2rem', flexWrap: 'wrap' }}
    >
      {/* Left panel: Camera feed */}
      <div style={{ flex: '1 1 60%', minWidth: '400px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
          <div>
            <h2 style={{ fontSize: '1.75rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '12px' }}>
              <Smartphone color="var(--accent-primary)" />
              Phone Camera CCTV
            </h2>
            <p style={{ color: 'var(--text-secondary)' }}>
              Use your phone camera as a portable CCTV for live face detection
            </p>
          </div>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            padding: '6px 16px',
            borderRadius: '20px',
            border: '1px solid',
            ...(
              connectionStatus === 'connected'
                ? { background: 'rgba(16, 185, 129, 0.1)', color: 'var(--success)', borderColor: 'rgba(16, 185, 129, 0.2)' }
                : connectionStatus === 'connecting'
                ? { background: 'rgba(59, 130, 246, 0.1)', color: 'var(--accent-primary)', borderColor: 'rgba(59, 130, 246, 0.2)' }
                : connectionStatus === 'error'
                ? { background: 'rgba(239, 68, 68, 0.1)', color: 'var(--danger)', borderColor: 'rgba(239, 68, 68, 0.2)' }
                : { background: 'rgba(107, 114, 128, 0.1)', color: 'var(--text-secondary)', borderColor: 'rgba(107, 114, 128, 0.2)' }
            )
          }}>
            <Activity size={16} className={isStreaming ? 'pulse' : ''} />
            {connectionStatus === 'connected' ? 'Live' : connectionStatus === 'connecting' ? 'Connecting...' : connectionStatus === 'error' ? 'Error' : 'Offline'}
          </div>
        </div>

        {/* Video feed */}
        <div className="glass-panel" style={{ overflow: 'hidden', position: 'relative', aspectRatio: '16/9', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#000' }}>
          <video
            ref={videoRef}
            autoPlay
            playsInline
            muted
            style={{ width: '100%', height: '100%', objectFit: 'cover' }}
          />
          <canvas ref={canvasRef} style={{ display: 'none' }} />

          {/* Scanning line */}
          {isProcessing && (
            <motion.div
              initial={{ scaleY: 0 }}
              animate={{ scaleY: [0, 1, 0] }}
              transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
              style={{
                position: 'absolute',
                top: 0, bottom: 0, left: '20%',
                width: '4px',
                background: 'var(--accent-primary)',
                boxShadow: '0 0 20px 4px var(--accent-glow)',
                transformOrigin: 'top'
              }}
            />
          )}

          {/* Overlays */}
          <div style={{ position: 'absolute', inset: 0, boxShadow: 'inset 0 0 0 1px var(--panel-border)', pointerEvents: 'none' }} />

          {/* Alert badges */}
          <AnimatePresence>
            {alerts.slice(0, 3).map((alert, i) => (
              <motion.div
                key={`${alert.person_id}-${alert.timestamp}`}
                initial={{ opacity: 0, y: -20, scale: 0.8 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, scale: 0.8 }}
                transition={{ delay: i * 0.1 }}
                style={{
                  position: 'absolute',
                  top: `${60 + i * 50}px`,
                  left: '20px',
                  background: 'rgba(239, 68, 68, 0.9)',
                  padding: '8px 16px',
                  borderRadius: '8px',
                  color: 'white',
                  fontWeight: 600,
                  fontSize: '0.875rem',
                  zIndex: 10,
                  boxShadow: '0 4px 12px rgba(239, 68, 68, 0.4)'
                }}
              >
                ⚠️ MATCH: {alert.person_name || `Person #${alert.person_id}`}
              </motion.div>
            ))}
          </AnimatePresence>

          {/* Camera controls overlay */}
          <div style={{ position: 'absolute', bottom: '1rem', left: '1rem', right: '1rem', display: 'flex', gap: '8px', justifyContent: 'center' }}>
            {!isStreaming ? (
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={startStreaming}
                className="btn-primary"
                style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '0.75rem 1.5rem' }}
              >
                <Power size={18} />
                Start CCTV Stream
              </motion.button>
            ) : (
              <>
                <motion.button
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={stopStreaming}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    padding: '0.75rem 1.5rem',
                    background: 'rgba(239, 68, 68, 0.9)',
                    border: 'none',
                    borderRadius: '8px',
                    color: 'white',
                    fontWeight: 600,
                    cursor: 'pointer'
                  }}
                >
                  <X size={18} />
                  Stop Stream
                </motion.button>
                <motion.button
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={clearStats}
                  className="btn-secondary"
                  style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '0.75rem 1.5rem' }}
                >
                  <Scan size={18} />
                  Clear Stats
                </motion.button>
              </>
            )}
          </div>
        </div>

        {/* Controls */}
        <div className="glass-panel" style={{ marginTop: '1rem', padding: '1.25rem' }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
            {/* Camera selection */}
            <div>
              <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>
                <Camera size={14} /> Camera
              </label>
              <select
                value={selectedCamera}
                onChange={(e) => setSelectedCamera(e.target.value)}
                disabled={isStreaming}
                style={{ width: '100%', padding: '0.5rem', borderRadius: '6px', background: 'rgba(255,255,255,0.05)', border: '1px solid var(--panel-border)', color: 'white' }}
              >
                <option value="">Default Camera</option>
                {availableCameras.map((cam, i) => (
                  <option key={cam.deviceId} value={cam.deviceId}>{cam.label || `Camera ${i + 1}`}</option>
                ))}
              </select>
            </div>

            {/* Device name */}
            <div>
              <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>
                <User size={14} /> Device Name
              </label>
              <input
                type="text"
                value={deviceName}
                onChange={(e) => setDeviceName(e.target.value)}
                placeholder="e.g., Officer John's Phone"
                disabled={isStreaming}
                style={{ width: '100%', padding: '0.5rem', borderRadius: '6px', background: 'rgba(255,255,255,0.05)', border: '1px solid var(--panel-border)', color: 'white' }}
              />
            </div>

            {/* Location */}
            <div>
              <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>
                <MapPin size={14} /> Location
              </label>
              <input
                type="text"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                placeholder="e.g., Market Square"
                disabled={isStreaming}
                style={{ width: '100%', padding: '0.5rem', borderRadius: '6px', background: 'rgba(255,255,255,0.05)', border: '1px solid var(--panel-border)', color: 'white' }}
              />
            </div>

            {/* Camera ID */}
            <div>
              <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>
                <Scan size={14} /> Camera ID
              </label>
              <input
                type="text"
                value={cameraId}
                onChange={(e) => setCameraId(e.target.value)}
                disabled={isStreaming}
                style={{ width: '100%', padding: '0.5rem', borderRadius: '6px', background: 'rgba(255,255,255,0.05)', border: '1px solid var(--panel-border)', color: 'white', fontFamily: 'monospace', fontSize: '0.8rem' }}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Right panel: Stats and logs */}
      <div style={{ flex: '1 1 35%', minWidth: '350px', display: 'flex', flexDirection: 'column' }}>
        {/* Stats grid */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1.5rem' }}>
          <div className="glass-panel" style={{ padding: '1rem', textAlign: 'center' }}>
            <div style={{ fontSize: '1.75rem', fontWeight: 700, color: 'var(--accent-primary)' }}>{frameCount}</div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '4px' }}>Frames Sent</div>
          </div>
          <div className="glass-panel" style={{ padding: '1rem', textAlign: 'center' }}>
            <div style={{ fontSize: '1.75rem', fontWeight: 700, color: 'var(--accent-primary)' }}>{faceCount}</div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '4px' }}>Faces Detected</div>
          </div>
          <div className="glass-panel" style={{ padding: '1rem', textAlign: 'center', border: matchCount > 0 ? '1px solid var(--danger)' : undefined }}>
            <div style={{ fontSize: '1.75rem', fontWeight: 700, color: matchCount > 0 ? 'var(--danger)' : 'var(--success)' }}>{matchCount}</div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '4px' }}>Matches Found</div>
          </div>
          <div className="glass-panel" style={{ padding: '1rem', textAlign: 'center' }}>
            <div style={{ fontSize: '1.75rem', fontWeight: 700, color: 'var(--accent-primary)' }}>{processingTime}ms</div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '4px' }}>Processing Time</div>
          </div>
        </div>

        {/* Recent detections */}
        <h3 style={{ fontSize: '1.25rem', fontWeight: 600, marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Scan color="var(--accent-primary)" />
          Recent Detections
        </h3>

        <div className="glass-panel" style={{ flex: 1, padding: '1rem', overflowY: 'auto', maxHeight: '400px', display: 'flex', flexDirection: 'column', gap: '0.75rem', marginBottom: '1.5rem' }}>
          {detections.length === 0 ? (
            <div style={{ margin: 'auto', color: 'var(--text-secondary)', textAlign: 'center' }}>
              <Scan size={40} style={{ opacity: 0.3, marginBottom: '0.5rem' }} />
              <p>No detections yet</p>
            </div>
          ) : (
            detections.map((det, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                style={{
                  padding: '0.75rem',
                  borderRadius: '10px',
                  background: det.alerts?.length > 0 ? 'rgba(239, 68, 68, 0.1)' : 'rgba(255, 255, 255, 0.03)',
                  borderLeft: `3px solid ${det.alerts?.length > 0 ? 'var(--danger)' : 'var(--accent-primary)'}`,
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '4px' }}>
                  <span>{det.face_count} faces</span>
                  <span>{det.processing_time_ms}ms</span>
                </div>
                {det.detections?.map((d, j) => (
                  <div key={j} style={{ fontSize: '0.8rem', marginTop: '4px' }}>
                    {d.is_match ? (
                      <span style={{ color: 'var(--danger)', fontWeight: 600 }}>
                        🚨 MATCH: {d.person_name || `Person #${d.best_match_id}`} ({(d.similarity_score * 100).toFixed(1)}%)
                      </span>
                    ) : d.best_match_id ? (
                      <span style={{ color: 'var(--accent-primary)' }}>
                        Person #{d.best_match_id} ({(d.similarity_score * 100).toFixed(1)}%)
                      </span>
                    ) : (
                      <span style={{ color: 'var(--text-secondary)' }}>Unknown face</span>
                    )}
                  </div>
                ))}
              </motion.div>
            ))
          )}
        </div>

        {/* Logs */}
        <h3 style={{ fontSize: '1.25rem', fontWeight: 600, marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Clock color="var(--warning)" />
          Connection Logs
        </h3>

        <div className="glass-panel" style={{ flex: 1, padding: '1rem', overflowY: 'auto', maxHeight: '300px', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          {logs.length === 0 ? (
            <div style={{ margin: 'auto', color: 'var(--text-secondary)', textAlign: 'center' }}>
              Waiting for events...
            </div>
          ) : (
            logs.map((log) => (
              <motion.div
                key={log.id}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                style={{
                  padding: '0.625rem',
                  borderRadius: '8px',
                  background: log.type === 'alert' ? 'rgba(239, 68, 68, 0.1)'
                    : log.type === 'success' ? 'rgba(16, 185, 129, 0.05)'
                    : log.type === 'error' ? 'rgba(239, 68, 68, 0.05)'
                    : 'rgba(255, 255, 255, 0.03)',
                  borderLeft: `3px solid ${
                    log.type === 'alert' ? 'var(--danger)'
                    : log.type === 'success' ? 'var(--success)'
                    : log.type === 'error' ? 'var(--danger)'
                    : 'var(--accent-primary)'
                  }`,
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', color: 'var(--text-secondary)', marginBottom: '2px' }}>
                  <span>{log.type.toUpperCase()}</span>
                  <span>{log.time}</span>
                </div>
                <div style={{ fontSize: '0.8rem', fontWeight: 500, color: log.type === 'alert' ? 'var(--danger)' : 'white' }}>
                  {log.message}
                </div>
              </motion.div>
            ))
          )}
        </div>
      </div>
    </motion.div>
  );
};

export default PhoneCamera;
