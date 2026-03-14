import React, { useState, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Upload, X, Loader2, Image as ImageIcon, Plus, MapPin, Navigation } from 'lucide-react';
import { useAuth, API_BASE } from '../context/AuthContext';

const UploadModal = ({ isOpen, onClose, onSuccess }) => {
  const { authFetch } = useAuth();
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [location, setLocation] = useState('');
  const [locationLoading, setLocationLoading] = useState(false);
  const [locationError, setLocationError] = useState('');
  const [files, setFiles] = useState([]);
  const [previews, setPreviews] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const fileInputRef = useRef(null);

  if (!isOpen) return null;

  const handleFileChange = (e) => {
    const selected = Array.from(e.target.files);
    if (!selected.length) return;

    // Cap at 5 files total
    const combined = [...files, ...selected].slice(0, 5);
    setFiles(combined);

    // Generate previews for new files
    combined.forEach((f, i) => {
      if (previews[i]) return; // already have preview
      const reader = new FileReader();
      reader.onloadend = () => {
        setPreviews(prev => {
          const next = [...prev];
          next[i] = reader.result;
          return next;
        });
      };
      reader.readAsDataURL(f);
    });
  };

  const removeFile = (index) => {
    setFiles(prev => prev.filter((_, i) => i !== index));
    setPreviews(prev => prev.filter((_, i) => i !== index));
  };

  const detectLocation = () => {
    if (!navigator.geolocation) {
      setLocationError('Geolocation is not supported by your browser.');
      return;
    }
    setLocationLoading(true);
    setLocationError('');
    navigator.geolocation.getCurrentPosition(
      async ({ coords }) => {
        try {
          const res = await fetch(
            `https://nominatim.openstreetmap.org/reverse?lat=${coords.latitude}&lon=${coords.longitude}&format=json`,
            { headers: { 'Accept-Language': 'en' } }
          );
          const data = await res.json();
          // Build a short readable address
          const addr = data.address || {};
          const parts = [
            addr.road || addr.suburb,
            addr.city || addr.town || addr.village || addr.county,
            addr.state,
            addr.country
          ].filter(Boolean);
          setLocation(parts.join(', ') || data.display_name);
        } catch {
          setLocation(`${coords.latitude.toFixed(5)}, ${coords.longitude.toFixed(5)}`);
        } finally {
          setLocationLoading(false);
        }
      },
      (err) => {
        setLocationLoading(false);
        setLocationError(
          err.code === 1 ? 'Location access denied. Please allow in browser settings.'
          : 'Unable to determine location. Try again.'
        );
      },
      { timeout: 10000 }
    );
  };

  const reset = () => {
    setName(''); setDescription(''); setLocation('');
    setFiles([]); setPreviews([]);
    setError(''); setLocationError('');
  };

  const handleClose = () => { reset(); onClose(); };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!name || files.length === 0) {
      setError('Name and at least one image are required.');
      return;
    }

    setLoading(true);
    setError('');

    const formData = new FormData();
    formData.append('name', name);
    if (description) formData.append('description', description);
    if (location) formData.append('last_seen_location', location);
    files.forEach(f => formData.append('files', f));

    try {
      const res = await authFetch(`${API_BASE}/upload-missing-person`, {
        method: 'POST',
        body: formData,
      });

      const data = await res.json();
      if (!res.ok) throw new Error(Array.isArray(data.detail) ? data.detail[0].msg : (data.detail || 'Upload failed'));
      onSuccess(data);
      reset();
      onClose();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        style={{
          position: 'fixed', inset: 0,
          background: 'rgba(0,0,0,0.75)',
          backdropFilter: 'blur(8px)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          zIndex: 1000, padding: '1rem'
        }}
        onClick={handleClose}
      >
        <motion.div
          initial={{ scale: 0.95, opacity: 0, y: 20 }}
          animate={{ scale: 1, opacity: 1, y: 0 }}
          exit={{ scale: 0.95, opacity: 0, y: 20 }}
          className="glass-panel"
          style={{ width: '100%', maxWidth: '540px', padding: '2rem', position: 'relative' }}
          onClick={(e) => e.stopPropagation()}
        >
          <button onClick={handleClose} style={{ position: 'absolute', top: '1rem', right: '1rem', color: 'var(--text-secondary)' }}>
            <X size={24} />
          </button>

          <h2 style={{ fontSize: '1.5rem', marginBottom: '0.25rem' }} className="title-glow">Add Missing Person</h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', marginBottom: '1.5rem' }}>
            Upload up to <strong style={{ color: 'white' }}>5 photos</strong> for best accuracy (front, left, right angles)
          </p>

          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
            {error && (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                style={{ background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)', color: '#fca5a5', padding: '1rem', borderRadius: '8px', fontSize: '0.875rem' }}>
                {error}
              </motion.div>
            )}

            <div>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.875rem', color: 'var(--text-secondary)' }}>Full Name *</label>
              <input type="text" value={name} onChange={e => setName(e.target.value)} placeholder="Ex: John Doe" required />
            </div>

            <div>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.875rem', color: 'var(--text-secondary)' }}>Description / Context</label>
              <textarea value={description} onChange={e => setDescription(e.target.value)}
                placeholder="Age, last seen wearing, physical traits..." rows={2} />
            </div>

            {/* Live Location Detection */}
            <div>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
                Last Seen Location
              </label>
              <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                <div style={{ flex: 1, position: 'relative' }}>
                  <MapPin size={16} style={{ position: 'absolute', left: '0.75rem', top: '50%', transform: 'translateY(-50%)', color: location ? '#22c55e' : 'var(--text-secondary)', pointerEvents: 'none' }} />
                  <input
                    type="text"
                    value={location}
                    onChange={e => setLocation(e.target.value)}
                    placeholder="Click 'Detect' or type manually"
                    style={{ paddingLeft: '2.25rem', color: location ? 'white' : undefined }}
                  />
                </div>
                <motion.button
                  type="button"
                  whileTap={{ scale: 0.95 }}
                  onClick={detectLocation}
                  disabled={locationLoading}
                  style={{
                    background: locationLoading ? 'rgba(59,130,246,0.1)' : 'rgba(59,130,246,0.2)',
                    border: '1px solid rgba(59,130,246,0.3)',
                    color: '#60a5fa',
                    padding: '0.6rem 1rem',
                    borderRadius: '10px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.4rem',
                    cursor: locationLoading ? 'not-allowed' : 'pointer',
                    whiteSpace: 'nowrap',
                    fontSize: '0.875rem',
                    minWidth: '100px',
                  }}
                >
                  {locationLoading
                    ? <><Loader2 size={16} className="spin" /> Detecting...</>
                    : <><Navigation size={16} /> Detect</>}
                </motion.button>
              </div>
              {locationError && (
                <p style={{ color: '#fca5a5', fontSize: '0.75rem', marginTop: '0.4rem' }}>{locationError}</p>
              )}
              {location && !locationLoading && (
                <p style={{ color: '#22c55e', fontSize: '0.75rem', marginTop: '0.4rem' }}>
                  ✓ Location detected — you can edit it above if needed
                </p>
              )}
            </div>

            {/* Image upload zone */}
            <div>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
                Reference Photos * ({files.length}/5)
              </label>

              {/* Thumbnail row */}
              {previews.length > 0 && (
                <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', marginBottom: '0.75rem' }}>
                  {previews.map((src, i) => (
                    <div key={i} style={{ position: 'relative', width: '72px', height: '72px' }}>
                      <img src={src} alt={`photo ${i+1}`} style={{ width: '100%', height: '100%', objectFit: 'cover', borderRadius: '8px', border: '2px solid var(--panel-border)' }} />
                      <button type="button" onClick={() => removeFile(i)}
                        style={{ position: 'absolute', top: '-8px', right: '-8px', background: 'var(--danger)', color: 'white', border: 'none', borderRadius: '50%', width: '20px', height: '20px', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer', fontSize: '12px' }}>
                        ×
                      </button>
                      {i === 0 && <div style={{ position: 'absolute', bottom: 0, left: 0, right: 0, background: 'rgba(0,0,0,0.6)', fontSize: '0.6rem', textAlign: 'center', borderRadius: '0 0 6px 6px', color: '#60a5fa' }}>MAIN</div>}
                    </div>
                  ))}
                  {files.length < 5 && (
                    <button type="button" onClick={() => fileInputRef.current?.click()}
                      style={{ width: '72px', height: '72px', border: '2px dashed var(--panel-border)', borderRadius: '8px', background: 'rgba(0,0,0,0.2)', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-secondary)' }}>
                      <Plus size={20} />
                    </button>
                  )}
                </div>
              )}

              {files.length === 0 && (
                <div onClick={() => fileInputRef.current?.click()}
                  style={{ border: '2px dashed var(--panel-border)', borderRadius: '12px', padding: '2rem', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.75rem', cursor: 'pointer', background: 'rgba(0,0,0,0.2)' }}>
                  <ImageIcon size={40} color="var(--text-secondary)" />
                  <div style={{ textAlign: 'center' }}>
                    <span style={{ color: 'var(--accent-primary)', fontWeight: 500 }}>Click to upload photos</span>
                    <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '4px' }}>PNG, JPG — Select multiple at once or add one by one</p>
                  </div>
                </div>
              )}

              <input
                type="file"
                ref={fileInputRef}
                onChange={handleFileChange}
                accept="image/jpeg,image/png"
                multiple
                style={{ display: 'none' }}
              />
            </div>

            <button type="submit" className="btn-primary" disabled={loading}
              style={{ display: 'flex', justifyContent: 'center', gap: '0.5rem', alignItems: 'center', padding: '0.875rem' }}>
              {loading ? <Loader2 size={20} className="spin" /> : <Upload size={20} />}
              {loading ? 'Processing faces...' : `Register Person (${files.length} photo${files.length !== 1 ? 's' : ''})`}
            </button>
          </form>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
};

export default UploadModal;
