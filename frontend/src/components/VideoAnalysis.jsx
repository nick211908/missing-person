import React, { useState, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Film, UploadCloud, AlertTriangle, CheckCircle, Clock, Layers, X } from 'lucide-react';
import { useAuth, API_BASE } from '../context/AuthContext';

const VideoAnalysis = () => {
  const { authFetch } = useAuth();
  const fileInputRef = useRef(null);

  const [selectedFile, setSelectedFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [frameSkip, setFrameSkip] = useState(30);
  const [isProcessing, setIsProcessing] = useState(false);
  const [progress, setProgress] = useState(null); // null | 'uploading' | 'processing' | 'done'
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (!file) return;

    if (!file.type.startsWith('video/')) {
      setError('Please select a valid video file.');
      return;
    }

    setSelectedFile(file);
    setPreviewUrl(URL.createObjectURL(file));
    setResult(null);
    setError(null);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file) {
      // Simulate the same flow as file input
      const fakeEvent = { target: { files: [file] } };
      handleFileChange(fakeEvent);
    }
  };

  const handleAnalyze = async () => {
    if (!selectedFile || isProcessing) return;

    setIsProcessing(true);
    setError(null);
    setResult(null);
    setProgress('uploading');

    const formData = new FormData();
    formData.append('file', selectedFile);
    formData.append('camera_id', 'video_upload');
    formData.append('frame_skip', frameSkip);

    try {
      setProgress('processing');
      const res = await authFetch(
        `${API_BASE}/process-video?camera_id=video_upload&frame_skip=${frameSkip}`,
        {
          method: 'POST',
          body: formData,
          // Do NOT set Content-Type; browser sets it with the boundary for multipart
        }
      );

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'Video processing failed');
      }

      setResult(data);
      setProgress('done');
    } catch (err) {
      setError(err.message);
      setProgress(null);
    } finally {
      setIsProcessing(false);
    }
  };

  const clearAll = () => {
    setSelectedFile(null);
    setPreviewUrl(null);
    setResult(null);
    setError(null);
    setProgress(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const totalAlerts = result?.alerts?.length ?? 0;

  return (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -20 }}
      transition={{ duration: 0.5 }}
      style={{ display: 'flex', gap: '2rem', flexWrap: 'wrap' }}
    >
      {/* ── Left panel: upload + controls ── */}
      <div style={{ flex: '1 1 55%', minWidth: '360px' }}>
        <div style={{ marginBottom: '1.5rem' }}>
          <h2 style={{ fontSize: '1.75rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '12px' }}>
            <Film color="var(--accent-primary)" />
            Video Clip Analysis
          </h2>
          <p style={{ color: 'var(--text-secondary)' }}>
            Upload a recorded CCTV clip. Each sampled frame is preprocessed (CLAHE + denoising)
            exactly like the live feed before face detection.
          </p>
        </div>

        {/* Drop zone */}
        <div
          className="glass-panel"
          onClick={() => !selectedFile && fileInputRef.current?.click()}
          onDragOver={(e) => e.preventDefault()}
          onDrop={handleDrop}
          style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '1rem',
            padding: '2rem',
            minHeight: '220px',
            cursor: selectedFile ? 'default' : 'pointer',
            border: selectedFile
              ? '1px solid var(--accent-primary)'
              : '2px dashed var(--panel-border)',
            position: 'relative',
            transition: 'border-color 0.3s ease',
          }}
        >
          {!selectedFile ? (
            <>
              <motion.div
                animate={{ y: [0, -6, 0] }}
                transition={{ repeat: Infinity, duration: 2, ease: 'easeInOut' }}
              >
                <UploadCloud size={48} color="var(--accent-primary)" style={{ opacity: 0.7 }} />
              </motion.div>
              <p style={{ color: 'var(--text-secondary)', textAlign: 'center', margin: 0 }}>
                Drag &amp; drop a video file here, or{' '}
                <span style={{ color: 'var(--accent-primary)', textDecoration: 'underline' }}>
                  click to browse
                </span>
              </p>
              <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', margin: 0 }}>
                MP4, AVI, MOV, MKV — up to ~500 MB
              </p>
            </>
          ) : (
            <>
              {/* Clear button */}
              <button
                onClick={(e) => { e.stopPropagation(); clearAll(); }}
                style={{
                  position: 'absolute', top: '0.75rem', right: '0.75rem',
                  background: 'rgba(239,68,68,0.15)', border: '1px solid rgba(239,68,68,0.3)',
                  color: '#fca5a5', borderRadius: '50%', width: '28px', height: '28px',
                  display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer',
                }}
              >
                <X size={14} />
              </button>

              <video
                src={previewUrl}
                controls
                style={{ width: '100%', maxHeight: '260px', borderRadius: '8px', objectFit: 'contain', background: '#000' }}
              />
              <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', margin: 0 }}>
                {selectedFile.name} &nbsp;({(selectedFile.size / 1024 / 1024).toFixed(1)} MB)
              </p>
            </>
          )}
        </div>

        <input
          ref={fileInputRef}
          type="file"
          accept="video/*"
          style={{ display: 'none' }}
          onChange={handleFileChange}
        />

        {/* Controls */}
        <div
          className="glass-panel"
          style={{ marginTop: '1rem', padding: '1.25rem', display: 'flex', alignItems: 'center', gap: '1.5rem', flexWrap: 'wrap' }}
        >
          <div style={{ flex: 1, minWidth: '180px' }}>
            <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '0.4rem' }}>
              Sample every <strong style={{ color: 'white' }}>{frameSkip}</strong> frames
              &nbsp;<span style={{ color: 'var(--text-secondary)', fontSize: '0.72rem' }}>(lower = more thorough, slower)</span>
            </label>
            <input
              type="range"
              min={5}
              max={90}
              step={5}
              value={frameSkip}
              onChange={(e) => setFrameSkip(Number(e.target.value))}
              style={{ width: '100%', accentColor: 'var(--accent-primary)', cursor: 'pointer' }}
            />
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', color: 'var(--text-secondary)' }}>
              <span>Every 5 frames</span>
              <span>Every 90 frames</span>
            </div>
          </div>

          <motion.button
            className="btn-primary"
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.97 }}
            onClick={handleAnalyze}
            disabled={!selectedFile || isProcessing}
            style={{ display: 'flex', alignItems: 'center', gap: '8px', minWidth: '160px', justifyContent: 'center' }}
          >
            {isProcessing ? (
              <>
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ repeat: Infinity, duration: 1, ease: 'linear' }}
                >
                  <Layers size={18} />
                </motion.div>
                Analysing…
              </>
            ) : (
              <>
                <Film size={18} />
                Analyse Video
              </>
            )}
          </motion.button>
        </div>

        {/* Preprocessing badge */}
        <div
          style={{
            marginTop: '0.75rem',
            display: 'flex', alignItems: 'center', gap: '8px',
            padding: '0.5rem 1rem',
            background: 'rgba(59,130,246,0.08)', borderRadius: '10px',
            border: '1px solid rgba(59,130,246,0.2)', fontSize: '0.8rem',
            color: 'var(--accent-primary)',
          }}
        >
          <CheckCircle size={14} /> Preprocessing active: CLAHE brightness normalisation + CCTV denoising
        </div>
      </div>

      {/* ── Right panel: results ── */}
      <div style={{ flex: '1 1 38%', minWidth: '320px', display: 'flex', flexDirection: 'column' }}>
        <h3 style={{ fontSize: '1.25rem', fontWeight: 600, marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <AlertTriangle color="var(--warning)" />
          Analysis Results
        </h3>

        <div
          className="glass-panel"
          style={{ flex: 1, padding: '1.25rem', overflowY: 'auto', maxHeight: '620px', display: 'flex', flexDirection: 'column', gap: '1rem' }}
        >
          {/* Idle state */}
          {!isProcessing && !result && !error && (
            <div style={{ margin: 'auto', color: 'var(--text-secondary)', textAlign: 'center' }}>
              <Film size={40} style={{ opacity: 0.3, marginBottom: '0.75rem' }} />
              <p style={{ margin: 0 }}>Upload and analyse a video to see results here.</p>
            </div>
          )}

          {/* Processing animation */}
          {isProcessing && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              style={{ margin: 'auto', textAlign: 'center', color: 'var(--text-secondary)' }}
            >
              <motion.div
                animate={{ scale: [1, 1.1, 1] }}
                transition={{ repeat: Infinity, duration: 1.4 }}
                style={{ display: 'inline-block', marginBottom: '0.75rem' }}
              >
                <Layers size={40} color="var(--accent-primary)" />
              </motion.div>
              <p style={{ margin: 0 }}>
                {progress === 'uploading' ? 'Uploading video…' : 'Preprocessing frames & detecting faces…'}
              </p>
              <p style={{ fontSize: '0.75rem', marginTop: '0.4rem', color: 'var(--text-secondary)' }}>
                This may take a moment for longer clips.
              </p>
            </motion.div>
          )}

          {/* Error */}
          {error && (
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              style={{ padding: '1rem', borderRadius: '12px', background: 'rgba(239,68,68,0.1)', borderLeft: '4px solid var(--danger)' }}
            >
              <p style={{ color: '#fca5a5', margin: 0, fontWeight: 500 }}>{error}</p>
            </motion.div>
          )}

          {/* Summary stats */}
          {result && (
            <AnimatePresence>
              <motion.div
                key="summary"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem', marginBottom: '0.5rem' }}
              >
                {[
                  { label: 'Duration', value: `${result.video_duration_sec?.toFixed(1)}s`, icon: <Clock size={14} /> },
                  { label: 'Frames analysed', value: result.frames_analyzed, icon: <Layers size={14} /> },
                  {
                    label: 'Frames w/ faces',
                    value: result.frames_with_detections,
                    icon: <Film size={14} />,
                    highlight: result.frames_with_detections > 0
                  },
                  {
                    label: 'Alerts raised',
                    value: totalAlerts,
                    icon: <AlertTriangle size={14} />,
                    highlight: totalAlerts > 0,
                    danger: totalAlerts > 0
                  },
                ].map((stat, i) => (
                  <div
                    key={i}
                    style={{
                      background: stat.danger
                        ? 'rgba(239,68,68,0.1)'
                        : stat.highlight
                        ? 'rgba(59,130,246,0.1)'
                        : 'rgba(255,255,255,0.04)',
                      borderRadius: '10px',
                      padding: '0.75rem 1rem',
                      border: `1px solid ${stat.danger ? 'rgba(239,68,68,0.25)' : stat.highlight ? 'rgba(59,130,246,0.2)' : 'var(--panel-border)'}`,
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: stat.danger ? '#fca5a5' : 'var(--accent-primary)', fontSize: '0.75rem', marginBottom: '4px' }}>
                      {stat.icon} {stat.label}
                    </div>
                    <div style={{ fontSize: '1.4rem', fontWeight: 700, color: stat.danger ? '#fca5a5' : 'white' }}>{stat.value}</div>
                  </div>
                ))}
              </motion.div>

              {/* Alert list */}
              {totalAlerts > 0 && result.alerts.map((alert, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.06 }}
                  style={{ padding: '1rem', borderRadius: '12px', background: 'rgba(239,68,68,0.1)', borderLeft: '4px solid var(--danger)' }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '4px' }}>
                    <span>ALERT</span>
                    <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <Clock size={11} /> {alert.timestamp_sec}s into video
                    </span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontWeight: 600 }}>
                    <span style={{ color: 'var(--accent-primary)' }}>Person #{alert.person_id}</span>
                    <span style={{ color: '#fca5a5' }}>{(alert.confidence * 100).toFixed(1)}% match</span>
                  </div>
                </motion.div>
              ))}

              {/* Per-frame results */}
              {result.frame_results?.length > 0 && (
                <>
                  <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', margin: '0.5rem 0 0' }}>
                    Frames with detected faces:
                  </p>
                  {result.frame_results.map((fr, i) => (
                    <motion.div
                      key={i}
                      initial={{ opacity: 0, y: 6 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: i * 0.04 }}
                      style={{ padding: '0.875rem', borderRadius: '10px', background: 'rgba(255,255,255,0.03)', border: '1px solid var(--panel-border)' }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '6px' }}>
                        <span>Frame #{fr.frame_index}</span>
                        <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}><Clock size={11} /> {fr.timestamp_sec}s</span>
                      </div>
                      {fr.detections.map((det, j) => (
                        <div key={j} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', padding: '2px 0' }}>
                          {det.best_match_id ? (
                            <>
                              <span style={{ color: det.is_match ? '#fca5a5' : 'var(--accent-primary)' }}>
                                {det.is_match ? '🚨' : '🔵'} Person #{det.best_match_id}
                              </span>
                              <span style={{ color: 'var(--text-secondary)' }}>
                                {(det.similarity_score * 100).toFixed(1)}%
                              </span>
                            </>
                          ) : (
                            <span style={{ color: 'var(--text-secondary)' }}>Unknown face detected</span>
                          )}
                        </div>
                      ))}
                    </motion.div>
                  ))}
                </>
              )}

              {/* No faces found */}
              {result && result.frames_with_detections === 0 && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  style={{ margin: 'auto', textAlign: 'center', color: 'var(--text-secondary)' }}
                >
                  <CheckCircle size={36} style={{ opacity: 0.4, marginBottom: '0.5rem' }} />
                  <p style={{ margin: 0 }}>No faces detected in the analysed frames.</p>
                </motion.div>
              )}
            </AnimatePresence>
          )}
        </div>
      </div>
    </motion.div>
  );
};

export default VideoAnalysis;
