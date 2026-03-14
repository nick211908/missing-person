import { useState } from 'react';
import { motion } from 'framer-motion';
import { ShieldAlert, Eye, EyeOff, LogIn, Loader2 } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export default function LoginPage({ onSwitchToSignup }) {
  const { login } = useAuth();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      await login(username, password);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={styles.page}>

      {/* Background blobs */}
      <div style={{ ...styles.blob, top: '-100px', left: '-100px', background: 'rgba(59,130,246,0.15)' }} />
      <div style={{ ...styles.blob, bottom: '-100px', right: '-100px', background: 'rgba(139,92,246,0.15)' }} />

      <motion.div
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="glass-panel"
        style={styles.card}
      >
        {/* Logo */}
        <div style={styles.logoBlock}>
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ type: 'spring', delay: 0.1 }}
            style={styles.logoIcon}
          >
            <ShieldAlert size={32} />
          </motion.div>
          <h1 className="text-gradient" style={{ fontSize: '1.75rem', fontWeight: 700 }}>Missing Person AI</h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>Sign in to access the system</p>
        </div>

        <form onSubmit={handleSubmit} style={styles.form}>
          {error && (
            <motion.div
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              style={styles.errorBox}
            >
              {error}
            </motion.div>
          )}

          <div style={styles.field}>
            <label style={styles.label}>Username</label>
            <input
              type="text"
              value={username}
              onChange={e => setUsername(e.target.value)}
              placeholder="Enter your username"
              required
              autoFocus
            />
          </div>

          <div style={styles.field}>
            <label style={styles.label}>Password</label>
            <div style={{ position: 'relative' }}>
              <input
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={e => setPassword(e.target.value)}
                placeholder="Enter your password"
                required
                style={{ paddingRight: '3rem' }}
              />
              <button
                type="button"
                onClick={() => setShowPassword(v => !v)}
                style={styles.eyeBtn}
              >
                {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </div>
          </div>

          <motion.button
            whileTap={{ scale: 0.97 }}
            type="submit"
            className="btn-primary"
            style={styles.submitBtn}
            disabled={loading}
          >
            {loading ? <Loader2 size={20} className="spin" /> : <LogIn size={20} />}
            {loading ? 'Signing in...' : 'Sign In'}
          </motion.button>
        </form>

        <p style={styles.switchText}>
          Don't have an account?{' '}
          <button onClick={onSwitchToSignup} style={styles.linkBtn}>
            Create account
          </button>
        </p>
      </motion.div>
    </div>
  );
}

const styles = {
  page: {
    minHeight: '100vh',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '1.5rem',
    position: 'relative',
    overflow: 'hidden',
  },
  blob: {
    position: 'fixed',
    width: '500px',
    height: '500px',
    borderRadius: '50%',
    filter: 'blur(80px)',
    zIndex: 0,
  },
  card: {
    width: '100%',
    maxWidth: '440px',
    padding: '2.5rem',
    position: 'relative',
    zIndex: 1,
  },
  logoBlock: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: '0.75rem',
    marginBottom: '2rem',
    textAlign: 'center',
  },
  logoIcon: {
    background: 'rgba(59,130,246,0.2)',
    color: '#3b82f6',
    padding: '14px',
    borderRadius: '16px',
    display: 'flex',
  },
  form: { display: 'flex', flexDirection: 'column', gap: '1.25rem' },
  field: { display: 'flex', flexDirection: 'column', gap: '0.5rem' },
  label: { fontSize: '0.875rem', color: 'var(--text-secondary)' },
  errorBox: {
    background: 'rgba(239,68,68,0.1)',
    border: '1px solid rgba(239,68,68,0.3)',
    color: '#fca5a5',
    padding: '0.875rem 1rem',
    borderRadius: '8px',
    fontSize: '0.875rem',
  },
  eyeBtn: {
    position: 'absolute',
    right: '0.75rem',
    top: '50%',
    transform: 'translateY(-50%)',
    color: 'var(--text-secondary)',
    cursor: 'pointer',
    background: 'none',
    border: 'none',
    display: 'flex',
  },
  submitBtn: {
    marginTop: '0.5rem',
    width: '100%',
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    gap: '0.5rem',
    padding: '0.875rem',
    fontSize: '1rem',
  },
  switchText: {
    textAlign: 'center',
    marginTop: '1.5rem',
    color: 'var(--text-secondary)',
    fontSize: '0.875rem',
  },
  linkBtn: {
    background: 'none',
    border: 'none',
    color: 'var(--accent-primary)',
    cursor: 'pointer',
    fontWeight: 600,
    padding: 0,
  },
};
