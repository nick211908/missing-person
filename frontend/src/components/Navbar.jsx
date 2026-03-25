import { Camera, LayoutDashboard, ShieldAlert, LogOut, Shield, User, Film, Smartphone } from 'lucide-react';
import { motion } from 'framer-motion';
import { useAuth } from '../context/AuthContext';

const Navbar = ({ activeTab, setActiveTab }) => {
  const { user, logout } = useAuth();

  const tabs = [
    { id: 'dashboard', label: 'Database', icon: <LayoutDashboard size={18} /> },
    { id: 'livestream', label: 'Live CCTV', icon: <Camera size={18} /> },
    { id: 'phonecamera', label: 'Phone Camera', icon: <Smartphone size={18} /> },
    { id: 'videoanalysis', label: 'Video Analysis', icon: <Film size={18} /> },
  ];

  return (
    <motion.nav
      initial={{ y: -20, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      className="glass-panel"
      style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: '0.875rem 1.75rem',
        marginBottom: '2rem',
        flexWrap: 'wrap',
        gap: '1rem',
      }}
    >
      {/* Logo */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <div style={{ background: 'rgba(59,130,246,0.2)', padding: '8px', borderRadius: '12px', color: '#3b82f6' }}>
          <ShieldAlert size={24} />
        </div>
        <div>
          <h1 style={{ fontSize: '1.1rem', fontWeight: 700, margin: 0 }} className="text-gradient">
            Missing Person AI
          </h1>
          <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', margin: 0 }}>CCTV Detection System</p>
        </div>
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: '0.5rem', background: 'rgba(0,0,0,0.2)', padding: '6px', borderRadius: '12px' }}>
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            style={{
              padding: '0.5rem 1rem',
              borderRadius: '8px',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              position: 'relative',
              color: activeTab === tab.id ? 'white' : 'var(--text-secondary)',
            }}
          >
            {activeTab === tab.id && (
              <motion.div
                layoutId="nav-pill"
                style={{ position: 'absolute', inset: 0, background: 'rgba(255,255,255,0.1)', borderRadius: '8px', zIndex: 0 }}
                transition={{ type: 'spring', bounce: 0.2, duration: 0.55 }}
              />
            )}
            <span style={{ position: 'relative', zIndex: 1, display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.875rem' }}>
              {tab.icon} {tab.label}
            </span>
          </button>
        ))}
      </div>

      {/* User info + logout */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
          background: 'rgba(255,255,255,0.05)',
          padding: '0.5rem 1rem',
          borderRadius: '10px',
          border: '1px solid var(--panel-border)',
        }}>
          <div style={{
            width: '32px', height: '32px', borderRadius: '50%',
            background: user?.role === 'admin' ? 'rgba(245,158,11,0.2)' : 'rgba(59,130,246,0.2)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            color: user?.role === 'admin' ? '#f59e0b' : '#3b82f6',
          }}>
            {user?.role === 'admin' ? <Shield size={16} /> : <User size={16} />}
          </div>
          <div>
            <p style={{ fontSize: '0.875rem', fontWeight: 600, margin: 0 }}>{user?.username}</p>
            <p style={{
              fontSize: '0.7rem', margin: 0, textTransform: 'capitalize',
              color: user?.role === 'admin' ? '#f59e0b' : 'var(--text-secondary)'
            }}>
              {user?.role}
            </p>
          </div>
        </div>

        <motion.button
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={logout}
          title="Sign out"
          style={{
            background: 'rgba(239,68,68,0.1)',
            border: '1px solid rgba(239,68,68,0.2)',
            color: '#fca5a5',
            padding: '0.6rem',
            borderRadius: '10px',
            display: 'flex',
            cursor: 'pointer',
          }}
        >
          <LogOut size={18} />
        </motion.button>
      </div>
    </motion.nav>
  );
};

export default Navbar;
