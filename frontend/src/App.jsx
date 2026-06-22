import React, { useState, useCallback } from 'react';
import Sidebar from './components/Sidebar.jsx';
import Dashboard from './components/Dashboard.jsx';
import CVUpload from './components/CVUpload.jsx';
import JobSearch from './components/JobSearch.jsx';
import JobMatching from './components/JobMatching.jsx';
import CoverLetterGen from './components/CoverLetterGen.jsx';
import EmailManager from './components/EmailManager.jsx';
import InterviewPrep from './components/InterviewPrep.jsx';
import ApplicationTracker from './components/ApplicationTracker.jsx';
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
  const [currentPage, setCurrentPage] = useState('dashboard');
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  const navigate = useCallback((page) => {
    setCurrentPage(page);
  }, []);

  const toggleSidebar = useCallback(() => {
    setSidebarCollapsed((prev) => !prev);
  }, []);

  const PageComponent = PAGES[currentPage]?.component || Dashboard;

  return (
    <div className={`app-layout ${sidebarCollapsed ? 'sidebar-collapsed' : ''}`}>
      <Sidebar
        pages={PAGES}
        currentPage={currentPage}
        onNavigate={navigate}
        collapsed={sidebarCollapsed}
        onToggle={toggleSidebar}
      />
      <main className="main-content">
        <div className="main-content-inner">
          <PageComponent onNavigate={navigate} />
        </div>
      </main>
    </div>
  );
}
