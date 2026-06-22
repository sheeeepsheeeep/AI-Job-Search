import React, { useState, useCallback, useEffect } from 'react';
import Sidebar from './components/Sidebar.jsx';
import Dashboard from './components/Dashboard.jsx';
import CVUpload from './components/CVUpload.jsx';
import JobSearch from './components/JobSearch.jsx';
import JobMatching from './components/JobMatching.jsx';
import CoverLetterGen from './components/CoverLetterGen.jsx';
import EmailManager from './components/EmailManager.jsx';
import InterviewPrep from './components/InterviewPrep.jsx';
import ApplicationTracker from './components/ApplicationTracker.jsx';
import Login from './components/Login.jsx';
import Register from './components/Register.jsx';
import { getCurrentUser, logout } from './services/api.js';
import './App.css';

const PAGES = {
  dashboard: { component: Dashboard, label: 'Dashboard', icon: '🏠' },
  'cv-upload': { component: CVUpload, label: 'CV Upload', icon: '📄' },
  'job-search': { component: JobSearch, label: 'Job Search', icon: '🔍' },
  'job-matching': { component: JobMatching, label: 'Job Matching', icon: '🎯' },
  'cover-letters': { component: CoverLetterGen, label: 'Cover Letters', icon: '✉️' },
  emails: { component: EmailManager, label: 'Emails', icon: '📧' },
  interviews: { component: InterviewPrep, label: 'Interviews', icon: '🎤' },
  applications: { component: ApplicationTracker, label: 'Applications', icon: '📊' },
};

export default function App() {
  const [currentUser, setCurrentUser] = useState(null);
  const [authScreen, setAuthScreen] = useState('login'); // 'login' | 'register'
  const [loadingUser, setLoadingUser] = useState(true);
  const [currentPage, setCurrentPage] = useState('dashboard');
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  useEffect(() => {
    async function checkAuth() {
      const token = localStorage.getItem('token');
      if (token) {
        try {
          const user = await getCurrentUser();
          setCurrentUser(user);
        } catch (e) {
          console.error('Failed to get current user on mount:', e);
          localStorage.removeItem('token');
        }
      }
      setLoadingUser(false);
    }
    checkAuth();
  }, []);

  const handleLoginSuccess = useCallback((user) => {
    setCurrentUser(user);
    setCurrentPage('dashboard');
  }, []);

  const handleRegisterSuccess = useCallback(() => {
    setAuthScreen('login');
  }, []);

  const handleLogout = useCallback(async () => {
    await logout();
    setCurrentUser(null);
    setCurrentPage('dashboard');
  }, []);

  const navigate = useCallback((page) => {
    setCurrentPage(page);
  }, []);

  const toggleSidebar = useCallback(() => {
    setSidebarCollapsed((prev) => !prev);
  }, []);

  if (loadingUser) {
    return (
      <div className="auth-container" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '100vh', background: '#0a0a1a' }}>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 'var(--space-4)' }}>
          <div className="spinner spinner-lg" />
          <p style={{ color: 'var(--text-secondary)', fontSize: 'var(--font-sm)' }}>Loading application...</p>
        </div>
      </div>
    );
  }

  if (!currentUser) {
    if (authScreen === 'register') {
      return (
        <Register
          onRegisterSuccess={handleRegisterSuccess}
          onToggleLogin={() => setAuthScreen('login')}
        />
      );
    }
    return (
      <Login
        onLoginSuccess={handleLoginSuccess}
        onToggleRegister={() => setAuthScreen('register')}
      />
    );
  }

  const PageComponent = PAGES[currentPage]?.component || Dashboard;

  return (
    <div className={`app-layout ${sidebarCollapsed ? 'sidebar-collapsed' : ''}`}>
      <Sidebar
        pages={PAGES}
        currentPage={currentPage}
        onNavigate={navigate}
        collapsed={sidebarCollapsed}
        onToggle={toggleSidebar}
        currentUser={currentUser}
        onLogout={handleLogout}
      />
      <main className="main-content">
        <div className="main-content-inner">
          <PageComponent onNavigate={navigate} />
        </div>
      </main>
    </div>
  );
}
