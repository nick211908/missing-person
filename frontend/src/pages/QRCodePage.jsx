import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { QrCode, Smartphone, Wifi, Info } from 'lucide-react';
import { useAuth, API_BASE } from '../context/AuthContext';

const QRCodePage = () => {
  const { authFetch } = useAuth();
  const [qrData, setQrData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchQRCode();
  }, []);

  const fetchQRCode = async () => {
    try {
      const response = await authFetch(`${API_BASE}/network/discovery/qrcode`);
      const data = await response.json();
      setQrData(data);
      setLoading(false);
    } catch (err) {
      setError(err.message);
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-secondary)' }}>
        <div>
          <div style={{ textAlign: 'center', fontSize: '2rem', marginBottom: '1rem' }}>⏳</div>
          <div>Generating QR code...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div className="glass-panel" style={{ padding: '2rem', maxWidth: '500px', textAlign: 'center' }}>
          <div style={{ color: 'var(--danger)', fontSize: '3rem', marginBottom: '1rem' }}>⚠️</div>
          <h2 style={{ color: 'var(--danger)', marginBottom: '1rem' }}>Error Loading QR Code</h2>
          <p style={{ color: 'var(--text-secondary)', marginBottom: '2rem' }}>{error}</p>
          <button onClick={fetchQRCode} className="btn-primary" style={{ padding: '0.75rem 1.5rem' }}>
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.5 }}
      style={{ maxWidth: '500px', margin: '0 auto', padding: '2rem' }}
    >
      {/* Back button */}
      <a href="/" style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', color: 'var(--text-secondary)', textDecoration: 'none', marginBottom: '1rem' }}>
        ← Back to Dashboard
      </a>

      <div className="glass-panel" style={{ padding: '2rem', textAlign: 'center' }}>
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ type: 'spring', stiffness: 260, damping: 20 }}
          style={{ marginBottom: '2rem' }}
        >
          <QrCode size={48} color="var(--accent-primary)" />
        </motion.div>

        <h1 style={{ fontSize: '1.75rem', marginBottom: '0.5rem' }}>Connect Your Phone</h1>
        <p style={{ color: 'var(--text-secondary)', marginBottom: '2rem' }}>
          Scan the QR code below to connect your phone camera
        </p>

        <motion.div
          initial={{ scale: 0.8, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ delay: 0.3, type: 'spring', stiffness: 200 }}
          style={{ background: 'white', padding: '2rem', borderRadius: '12px', marginBottom: '2rem', display: 'inline-block' }}
        >
          {qrData?.qrcode_base64 ? (
            <img
              src={qrData.qrcode_base64}
              alt="QR Code"
              style={{ width: '250px', height: '250px', display: 'block' }}
            />
          ) : (
            <div style={{ width: '250px', height: '250px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#333' }}>
              QR Code Not Available
            </div>
          )}
        </motion.div>

        <div style={{ marginBottom: '2rem' }}>
          <motion.div
            initial={{ x: -20, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            transition={{ delay: 0.5 }}
            style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '1rem', justifyContent: 'center' }}
          >
            <Smartphone size={16} color="var(--accent-primary)" />
            <span style={{ fontWeight: 600 }}>Phone Camera URL:</span>
          </motion.div>

          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.7 }}
            style={{ background: 'rgba(0,0,0,0.2)', padding: '1rem', borderRadius: '8px', fontFamily: 'monospace', fontSize: '0.875rem', wordBreak: 'break-all' }}
          >
            {qrData?.connection_url || 'Loading...'}
          </motion.div>
        </div>

        <motion.div
          initial={{ y: 20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 0.9 }}
          className="gradient-panel"
          style={{ padding: '1.5rem', borderRadius: '12px', marginBottom: '2rem' }}
        >
          <h3 style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '1rem' }}>
            <Info size={18} color="#3b82f6" />
            How to Connect
          </h3>
          <ol style={{ textAlign: 'left', paddingLeft: '1.5rem', color: 'var(--text-secondary)' }}>
            <li style={{ marginBottom: '0.5rem' }}>Ensure your phone and computer are on the same WiFi network</li>
            <li style={{ marginBottom: '0.5rem' }}>Open your phone's camera and scan the QR code above</li>
            <li style={{ marginBottom: '0.5rem' }}>Tap the notification to open the link in your browser</li>
            <li style={{ marginBottom: '0.5rem' }}>Allow camera access when prompted</li>
            <li style={{ marginBottom: '0.5rem' }}>Click "Start Scan" to begin live face detection</li>
          </ol>
        </motion.div>

        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1.1 }}
          style={{ display: 'flex', gap: '1rem', justifyContent: 'center' }}
        >
          <button
            onClick={fetchQRCode}
            className="btn-secondary"
            style={{ padding: '0.75rem 1.5rem', display: 'flex', alignItems: 'center', gap: '8px' }}
          >
            Refresh
          </button>
          <a href="/" className="btn-primary" style={{ padding: '0.75rem 1.5rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
            Back to Dashboard
          </a>
        </motion.div>
      </div>
    </motion.div>
  );
};

export default QRCodePage;
