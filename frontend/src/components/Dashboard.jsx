import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, MapPin, UserPlus, Trash2 } from 'lucide-react';
import UploadModal from './UploadModal';
import { useAuth, API_BASE } from '../context/AuthContext';

const Dashboard = () => {
  const { authFetch, user } = useAuth();
  const [persons, setPersons] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [deleting, setDeleting] = useState(null);

  const fetchPersons = async () => {
    try {
      setLoading(true);
      const res = await authFetch(`${API_BASE}/missing-persons`);
      if (res.ok) {
        const data = await res.json();
        setPersons(data);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPersons();
  }, []);

  const handleDelete = async (personId, personName) => {
    if (!confirm(`Are you sure you want to delete "${personName}"? This action cannot be undone.`)) {
      return;
    }

    try {
      setDeleting(personId);
      const res = await authFetch(`${API_BASE}/missing-persons/${personId}`, {
        method: 'DELETE',
      });

      if (res.ok) {
        setPersons(persons.filter(p => p.person_id !== personId));
      } else {
        const error = await res.json();
        alert(error.detail || 'Failed to delete person');
      }
    } catch (err) {
      console.error(err);
      alert('Failed to delete person');
    } finally {
      setDeleting(null);
    }
  };

  const filtered = persons.filter(p =>
    p.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    p.description?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    p.last_seen_location?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      transition={{ duration: 0.5 }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
        <div>
          <h2 style={{ fontSize: '1.75rem', fontWeight: 600, marginBottom: '0.5rem' }}>Missing Persons Database</h2>
          <p style={{ color: 'var(--text-secondary)' }}>{persons.length} registered profiles awaiting detection.</p>
        </div>
        
        <button 
          className="btn-primary" 
          onClick={() => setIsUploadOpen(true)}
          style={{ display: 'flex', alignItems: 'center', gap: '8px' }}
        >
          <UserPlus size={18} />
          Report Missing Person
        </button>
      </div>

      <div style={{ position: 'relative', marginBottom: '2rem' }}>
        <Search style={{ position: 'absolute', left: '1rem', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-secondary)' }} size={20} />
        <input 
          type="text" 
          placeholder="Search by name, description or location..." 
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          style={{ paddingLeft: '3rem', width: '100%', maxWidth: '500px' }}
        />
      </div>

      {loading ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: '4rem 0' }}>
          <div className="spinner">Loading database...</div>
        </div>
      ) : (
        <div style={{ 
          display: 'grid', 
          gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', 
          gap: '1.5rem' 
        }}>
          <AnimatePresence>
            {filtered.map((person, i) => (
              <motion.div
                key={person.person_id}
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.9 }}
                transition={{ duration: 0.3, delay: i * 0.05 }}
                className="glass-panel"
                style={{ overflow: 'hidden', display: 'flex', flexDirection: 'column' }}
                whileHover={{ y: -5, boxShadow: '0 20px 40px -10px rgba(0,0,0,0.6)' }}
              >
                <div style={{ height: '240px', background: 'rgba(0,0,0,0.3)', position: 'relative' }}>
                  {/* For MVP we assume we have an image URL. If none is returned, show generic */}
                  {person.image_path ? (
                    <img
                      src={`http://127.0.0.1:8000/images/${person.image_path.split('/').pop()}`}
                      alt={person.name}
                      style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                      onError={(e) => { e.target.style.display='none'; }}
                    />
                  ) : (
                    <div style={{ display: 'flex', height: '100%', alignItems: 'center', justifyContent: 'center' }}>
                      <span style={{ color: 'var(--text-secondary)' }}>No Image Provided</span>
                    </div>
                  )}

                  {/* Delete button - top left */}
                  <button
                    onClick={() => handleDelete(person.person_id, person.name)}
                    disabled={deleting === person.person_id}
                    style={{
                      position: 'absolute',
                      top: '1rem',
                      left: '1rem',
                      background: 'rgba(220, 38, 38, 0.8)',
                      backdropFilter: 'blur(4px)',
                      border: 'none',
                      borderRadius: '50%',
                      width: '36px',
                      height: '36px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      cursor: deleting === person.person_id ? 'not-allowed' : 'pointer',
                      opacity: deleting === person.person_id ? 0.5 : 1,
                      transition: 'all 0.2s ease',
                    }}
                    onMouseEnter={(e) => {
                      if (deleting !== person.person_id) {
                        e.target.style.background = 'rgba(220, 38, 38, 1)';
                        e.target.style.transform = 'scale(1.1)';
                      }
                    }}
                    onMouseLeave={(e) => {
                      e.target.style.background = 'rgba(220, 38, 38, 0.8)';
                      e.target.style.transform = 'scale(1)';
                    }}
                    title="Delete person"
                  >
                    {deleting === person.person_id ? (
                      <span style={{ color: 'white', fontSize: '12px' }}>...</span>
                    ) : (
                      <Trash2 size={18} color="white" />
                    )}
                  </button>

                  <div style={{
                    position: 'absolute',
                    top: '1rem',
                    right: '1rem',
                    background: 'rgba(0,0,0,0.6)',
                    backdropFilter: 'blur(4px)',
                    padding: '4px 12px',
                    borderRadius: '20px',
                    fontSize: '0.75rem',
                    fontWeight: 600,
                    color: person.status === 'Missing' ? '#fca5a5' : '#86efac',
                    border: `1px solid ${person.status === 'Missing' ? 'var(--danger-glow)' : 'var(--success)'}`
                  }}>
                    {person.status || 'Active'}
                  </div>
                </div>
                
                <div style={{ padding: '1.5rem', flex: 1, display: 'flex', flexDirection: 'column' }}>
                  <h3 style={{ fontSize: '1.25rem', fontWeight: 600, marginBottom: '0.5rem' }}>{person.name}</h3>
                  <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', lineHeight: 1.5, flex: 1 }}>
                    {person.description || 'No specific details provided.'}
                  </p>
                  
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '1.5rem', color: 'var(--text-secondary)', fontSize: '0.8rem' }}>
                    <MapPin size={16} />
                    <span>{person.last_seen_location || 'Location unknown'}</span>
                  </div>
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
          
          {filtered.length === 0 && (
            <div style={{ gridColumn: '1 / -1', textAlign: 'center', padding: '4rem', color: 'var(--text-secondary)' }}>
              <Search size={48} style={{ margin: '0 auto 1rem', opacity: 0.5 }} />
              <p>No missing persons found matching "{searchTerm}"</p>
            </div>
          )}
        </div>
      )}

      <UploadModal 
        isOpen={isUploadOpen} 
        onClose={() => setIsUploadOpen(false)}
        onSuccess={() => {
          fetchPersons();
        }}
      />
    </motion.div>
  );
};

export default Dashboard;
