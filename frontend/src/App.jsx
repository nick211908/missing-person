import { useState } from 'react';
import { AnimatePresence } from 'framer-motion';
import { AuthProvider, useAuth } from './context/AuthContext';
import Navbar from './components/Navbar';
import Dashboard from './components/Dashboard';
import LiveStream from './components/LiveStream';
import LoginPage from './pages/LoginPage';
import SignupPage from './pages/SignupPage';

// Inner component has access to auth context
function AppInner() {
  const { user, loading } = useAuth();
  const [activeTab, setActiveTab] = useState('dashboard');
  const [authView, setAuthView] = useState('login'); // 'login' | 'signup'

  if (loading) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ color: 'var(--text-secondary)' }}>Loading...</div>
      </div>
    );
  }

  if (!user) {
    return (
      <AnimatePresence mode="wait">
        {authView === 'login' ? (
          <LoginPage key="login" onSwitchToSignup={() => setAuthView('signup')} />
        ) : (
          <SignupPage key="signup" onSwitchToLogin={() => setAuthView('login')} />
        )}
      </AnimatePresence>
    );
  }

  return (
    <div className="app-container">
      <Navbar activeTab={activeTab} setActiveTab={setActiveTab} />
      <main>
        <AnimatePresence mode="wait">
          {activeTab === 'dashboard' ? (
            <Dashboard key="dashboard" />
          ) : (
            <LiveStream key="livestream" />
          )}
        </AnimatePresence>
      </main>
      <footer style={{ marginTop: 'auto', paddingTop: '3rem', textAlign: 'center', color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
        <p>Missing Person AI MVP • Hackathon Demo</p>
      </footer>
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <AppInner />
    </AuthProvider>
  );
}
