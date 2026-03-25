import React, { useState, useRef, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Camera, AlertTriangle, Video, Activity } from 'lucide-react';
import { useAuth, API_BASE } from '../context/AuthContext';

const LiveStream = () => {
  const { authFetch } = useAuth();
  const [logs, setLogs] = useState([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const bestAccuracies = useRef({}); // Track highest confidence per person_id

  // Simulated WebCam Hookup for MVP demo
  useEffect(() => {
    let stream = null;
    const startCamera = async () => {
      try {
        stream = await navigator.mediaDevices.getUserMedia({ video: true });
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
        }
      } catch (err) {
        console.error("Camera access denied:", err);
        addLog("Camera access denied or unavailable. You can manually upload a frame to simulate CCTV.", "error");
      }
    };
    startCamera();

    return () => {
      if (stream) {
        stream.getTracks().forEach(track => track.stop());
      }
    };
  }, []);

  const addLog = (message, type = 'info', metadata = null) => {
    setLogs(prev => [{
      id: Date.now() + Math.random(),
      time: new Date().toLocaleTimeString(),
      message,
      type,
      metadata
    }, ...prev].slice(0, 50));
  };

  const captureAndProcess = async () => {
    if (!videoRef.current || isProcessing) return;
    
    setIsProcessing(true);
    addLog("Capturing frame for analysis...", "info");

    const canvas = canvasRef.current;
    const context = canvas.getContext('2d');
    
    canvas.width = videoRef.current.videoWidth || 640;
    canvas.height = videoRef.current.videoHeight || 480;
    context.drawImage(videoRef.current, 0, 0, canvas.width, canvas.height);
    
    try {
      const base64Image = canvas.toDataURL('image/jpeg', 0.8).split(',')[1];
      
      const res = await authFetch(`${API_BASE}/process-frame`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          camera_id: 'cctv_main_gate',
          timestamp: new Date().toISOString(),
          frame: base64Image
        })
      });

      const data = await res.json();
      
      if (res.ok && data.alerts && data.alerts.length > 0) {
        // Track the absolute best frame accuracy across time for each person
        const processedAlerts = data.alerts.map(alert => {
          const currentBest = bestAccuracies.current[alert.person_id] || 0;
          const bestScore = Math.max(currentBest, alert.confidence);
          bestAccuracies.current[alert.person_id] = bestScore;
          return { ...alert, confidence: bestScore };
        });
        
        addLog(`ALERT! Missing person(s) detected.`, "alert", processedAlerts);
      } else if (res.ok) {
        addLog("Frame processed: No matches found.", "success");
      } else {
        throw new Error(data.detail || "Processing failed");
      }
    } catch (err) {
      addLog(`Error processing frame: ${err.message}`, "error");
    } finally {
      setIsProcessing(false);
    }
  };

  // Automated MVP sampling loop
  useEffect(() => {
    let interval;
    if (!isProcessing && videoRef.current?.srcObject) {
      interval = setInterval(() => {
        captureAndProcess();
      }, 5000); // Sample every 5 seconds for MVP 
    }
    return () => clearInterval(interval);
  }, [isProcessing]);

  return (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -20 }}
      transition={{ duration: 0.5 }}
      style={{ display: 'flex', gap: '2rem', flexWrap: 'wrap' }}
    >
      <div style={{ flex: '1 1 60%', minWidth: '400px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
          <div>
            <h2 style={{ fontSize: '1.75rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '12px' }}>
              <Video color="var(--accent-primary)" />
              Live Feed Analysis
            </h2>
            <p style={{ color: 'var(--text-secondary)' }}>Monitoring CCTV Camera: Main Gate Node 01</p>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '6px 16px', background: 'rgba(16, 185, 129, 0.1)', borderRadius: '20px', color: 'var(--success)', border: '1px solid rgba(16, 185, 129, 0.2)' }}>
            <Activity size={16} className="pulse" /> Live
          </div>
        </div>

        <div className="glass-panel" style={{ overflow: 'hidden', position: 'relative', aspectRatio: '16/9', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <video 
            ref={videoRef} 
            autoPlay 
            playsInline 
            muted 
            style={{ width: '100%', height: '100%', objectFit: 'cover' }}
          />
          <canvas ref={canvasRef} style={{ display: 'none' }} />
          
          <div style={{ position: 'absolute', inset: 0, boxShadow: 'inset 0 0 0 1px var(--panel-border)', pointerEvents: 'none' }} />

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

          <div style={{ position: 'absolute', bottom: '1rem', right: '1rem', display: 'flex', gap: '8px' }}>
            <button className="btn-secondary" onClick={captureAndProcess} disabled={isProcessing} style={{ padding: '0.5rem 1rem', fontSize: '0.875rem' }}>
              {isProcessing ? 'SCANNING...' : 'FORCE SCAN'}
            </button>
          </div>
        </div>
      </div>

      <div style={{ flex: '1 1 35%', minWidth: '350px', display: 'flex', flexDirection: 'column' }}>
        <h3 style={{ fontSize: '1.25rem', fontWeight: 600, marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <AlertTriangle color="var(--warning)" />
          Detection Logs
        </h3>

        <div className="glass-panel" style={{ flex: 1, padding: '1rem', overflowY: 'auto', maxHeight: '600px', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {logs.length === 0 ? (
            <div style={{ margin: 'auto', color: 'var(--text-secondary)', textAlign: 'center' }}>
              Waiting for network events...
            </div>
          ) : (
            logs.map((log) => (
              <motion.div 
                key={log.id}
                initial={{ opacity: 0, y: 10, scale: 0.98 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                style={{
                  padding: '1rem',
                  borderRadius: '12px',
                  background: log.type === 'alert' ? 'rgba(239, 68, 68, 0.1)' 
                            : log.type === 'success' ? 'rgba(16, 185, 129, 0.05)'
                            : 'rgba(255, 255, 255, 0.03)',
                  borderLeft: `4px solid ${
                    log.type === 'alert' ? 'var(--danger)' 
                    : log.type === 'success' ? 'var(--success)'
                    : 'var(--accent-primary)'
                  }`
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px', fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                  <span>{log.type.toUpperCase()}</span>
                  <span>{log.time}</span>
                </div>
                <div style={{ fontWeight: 500, color: log.type === 'alert' ? '#fca5a5' : 'white' }}>
                  {log.message}
                </div>
                
                {log.metadata && log.type === 'alert' && (
                  <div style={{ marginTop: '0.5rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                    {log.metadata.map((alert, i) => (
                      <div key={i} style={{ background: 'rgba(0,0,0,0.4)', padding: '0.5rem', borderRadius: '8px', fontSize: '0.875rem' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                          <span style={{ color: 'var(--accent-primary)' }}>Matched Person {alert.person_id}</span>
                          <span style={{ color: 'var(--danger)' }}>{(alert.confidence * 100).toFixed(1)}% Max Match</span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </motion.div>
            ))
          )}
        </div>
      </div>
    </motion.div>
  );
};

export default LiveStream;
