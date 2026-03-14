import { useState } from 'react';
import { motion } from 'framer-motion';
import { ShieldAlert, Eye, EyeOff, UserPlus, Loader2, CheckCircle } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export default function SignupPage({ onSwitchToLogin }) {
  const { register } = useAuth();
  const [form, setForm] = useState({ username: '', email: '', password: '', confirm: '' });
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  const set = (key) => (e) => setForm(f => ({ ...f, [key]: e.target.value }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (form.password !== form.confirm) {
      setError('Passwords do not match.');
      return;
    }
    if (form.password.length < 6) {
      setError('Password must be at least 6 characters.');
      return;
    }
    setLoading(true);
    setError('');
    try {
      await register(form.username, form.email, form.password);
      setSuccess(true);
      setTimeout(onSwitchToLogin, 2000);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <div style={styles.page}>
        <motion.div
          initial={{ scale: 0.8, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          className="glass-panel"
          style={{ ...styles.card, textAlign: 'center', padding: '3rem' }}
        >
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ type: 'spring', delay: 0.1 }}
            style={{ color: 'var(--success)', display: 'flex', justifyContent: 'center', marginBottom: '1rem' }}
          >
            <CheckCircle size={64} />
          </motion.div>
          <h2 style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: '0.5rem' }}>Account Created!</h2>
          <p style={{ color: 'var(--text-secondary)' }}>Redirecting you to login...</p>
        </motion.div>
      </div>
    );
  }

  return (
    <div style={styles.page}>
      <div style={{ ...styles.blob, top: '-100px', right: '-100px', background: 'rgba(139,92,246,0.15)' }} />
      <div style={{ ...styles.blob, bottom: '-100px', left: '-100px', background: 'rgba(59,130,246,0.15)' }} />

      <motion.div
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="glass-panel"
        style={styles.card}
      >
        <div style={styles.logoBlock}>
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ type: 'spring', delay: 0.1 }}
            style={styles.logoIcon}
          >
            <ShieldAlert size={32} />
          </motion.div>
          <h1 className="text-gradient" style={{ fontSize: '1.75rem', fontWeight: 700 }}>Create Account</h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
            First registered user becomes <strong style={{ color: '#f59e0b' }}>admin</strong>
          </p>
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

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
            <div style={styles.field}>
              <label style={styles.label}>Username</label>
              <input type="text" value={form.username} onChange={set('username')} placeholder="johndoe" required />
            </div>
            <div style={styles.field}>
              <label style={styles.label}>Email</label>
              <input type="email" value={form.email} onChange={set('email')} placeholder="john@police.gov" required />
            </div>
          </div>

          <div style={styles.field}>
            <label style={styles.label}>Password</label>
            <div style={{ position: 'relative' }}>
              <input
                type={showPassword ? 'text' : 'password'}
                value={form.password}
                onChange={set('password')}
                placeholder="Min 6 characters"
                required
                style={{ paddingRight: '3rem' }}
              />
              <button type="button" onClick={() => setShowPassword(v => !v)} style={styles.eyeBtn}>
                {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </div>
          </div>

          <div style={styles.field}>
            <label style={styles.label}>Confirm Password</label>
            <input
              type={showPassword ? 'text' : 'password'}
              value={form.confirm}
              onChange={set('confirm')}
              placeholder="Repeat password"
              required
              style={{
                borderColor: form.confirm && form.password !== form.confirm ? 'var(--danger)' : undefined
              }}
            />
          </div>

          <motion.button
            whileTap={{ scale: 0.97 }}
            type="submit"
            className="btn-primary"
            style={styles.submitBtn}
            disabled={loading}
          >
            {loading ? <Loader2 size={20} className="spin" /> : <UserPlus size={20} />}
            {loading ? 'Creating Account...' : 'Create Account'}
          </motion.button>
        </form>

        <p style={styles.switchText}>
          Already have an account?{' '}
          <button onClick={onSwitchToLogin} style={styles.linkBtn}>Sign in</button>
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
    maxWidth: '540px',
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
