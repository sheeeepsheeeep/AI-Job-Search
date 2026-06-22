import React, { useState, useEffect } from 'react';
import { getStats, getProfile, getJobs } from '../services/api.js';
import './Dashboard.css';

export default function Dashboard({ onNavigate }) {
  const [stats, setStats] = useState(null);
  const [profile, setProfile] = useState(null);
  const [recentJobs, setRecentJobs] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadDashboard() {
      setLoading(true);
      try {
        const [statsData, profileData, jobsData] = await Promise.allSettled([
          getStats(),
          getProfile(),
          getJobs({ limit: 5 }),
        ]);
        if (statsData.status === 'fulfilled') setStats(statsData.value);
        if (profileData.status === 'fulfilled') setProfile(profileData.value);
        if (jobsData.status === 'fulfilled') {
          const jobsList = Array.isArray(jobsData.value) ? jobsData.value : (jobsData.value.jobs || []);
          setRecentJobs(jobsList);
        }
      } catch (e) {
        console.error('Dashboard load error:', e);
      }
      setLoading(false);
    }
    loadDashboard();
  }, []);

  const statCards = [
    {
      label: 'Total Applications',
      value: stats?.total_applications ?? 0,
      icon: '📋',
      color: 'var(--accent-indigo)',
      gradient: 'linear-gradient(135deg, rgba(99,102,241,0.15), rgba(99,102,241,0.05))',
    },
    {
      label: 'Active Jobs',
      value: stats?.active_jobs_count ?? recentJobs.length ?? 0,
      icon: '💼',
      color: 'var(--accent-violet)',
      gradient: 'linear-gradient(135deg, rgba(139,92,246,0.15), rgba(139,92,246,0.05))',
    },
    {
      label: 'Avg Match Score',
      value: stats?.success_rate != null ? `${stats.success_rate.toFixed(0)}%` : '—',
      icon: '🎯',
      color: 'var(--accent-emerald)',
      gradient: 'linear-gradient(135deg, rgba(16,185,129,0.15), rgba(16,185,129,0.05))',
    },
    {
      label: 'Interviews',
      value: stats?.by_status?.interview_scheduled ?? 0,
      icon: '🎤',
      color: 'var(--accent-amber)',
      gradient: 'linear-gradient(135deg, rgba(245,158,11,0.15), rgba(245,158,11,0.05))',
    },
  ];

  const pipelineStages = [
    { label: 'Applied', count: stats?.by_status?.applied ?? 0, color: 'var(--accent-indigo)' },
    { label: 'In Review', count: stats?.by_status?.under_review ?? 0, color: 'var(--accent-violet)' },
    { label: 'Interview', count: stats?.by_status?.interview_scheduled ?? 0, color: 'var(--accent-amber)' },
    { label: 'Offer', count: stats?.by_status?.offer_received ?? 0, color: 'var(--accent-emerald)' },
    { label: 'Rejected', count: stats?.by_status?.rejected ?? 0, color: 'var(--accent-red)' },
  ];

  const maxPipeline = Math.max(...pipelineStages.map((s) => s.count), 1);

  const quickActions = [
    { label: 'Upload CV', icon: '📄', page: 'cv-upload' },
    { label: 'Search Jobs', icon: '🔍', page: 'job-search' },
    { label: 'Write Cover Letter', icon: '✉️', page: 'cover-letters' },
    { label: 'Practice Interview', icon: '🎤', page: 'interviews' },
  ];

  if (loading) {
    return (
      <div className="dashboard">
        <div className="dashboard-welcome skeleton-banner" />
        <div className="stats-grid">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="stat-card skeleton" style={{ height: 120 }} />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="dashboard">
      {/* Welcome Banner */}
      <div className="dashboard-welcome animate-fade-in-up">
        <div className="welcome-content">
          <h1>
            Welcome back
            {(profile?.name || profile?.full_name) ? `, ${(profile.name || profile.full_name).split(' ')[0]}` : ''}! 👋
          </h1>
          <p>Your AI-powered job search assistant is ready to help you land your dream job.</p>
          <div className="welcome-actions">
            <button className="btn btn-primary btn-lg" onClick={() => onNavigate('job-search')}>
              🔍 Find Jobs
            </button>
            <button className="btn btn-secondary btn-lg" onClick={() => onNavigate('cv-upload')}>
              📄 Upload CV
            </button>
          </div>
        </div>
        <div className="welcome-graphic">
          <div className="graphic-orb orb-1" />
          <div className="graphic-orb orb-2" />
          <div className="graphic-orb orb-3" />
        </div>
      </div>

      {/* Stats Cards */}
      <div className="stats-grid">
        {statCards.map((stat, i) => (
          <div
            key={stat.label}
            className="stat-card animate-fade-in-up"
            style={{ animationDelay: `${i * 0.1}s`, background: stat.gradient }}
          >
            <div className="stat-icon" style={{ color: stat.color }}>
              {stat.icon}
            </div>
            <div className="stat-info">
              <span className="stat-value" style={{ color: stat.color }}>
                {stat.value}
              </span>
              <span className="stat-label">{stat.label}</span>
            </div>
          </div>
        ))}
      </div>

      {/* Main Grid: Pipeline + Recent Activity */}
      <div className="dashboard-grid">
        {/* Application Pipeline */}
        <div className="card animate-fade-in-up delay-2">
          <h3 className="section-title">📊 Application Pipeline</h3>
          <div className="pipeline-chart">
            {pipelineStages.map((stage) => (
              <div key={stage.label} className="pipeline-bar-wrapper">
                <div className="pipeline-label">
                  <span>{stage.label}</span>
                  <span className="pipeline-count">{stage.count}</span>
                </div>
                <div className="pipeline-bar-track">
                  <div
                    className="pipeline-bar-fill"
                    style={{
                      width: `${(stage.count / maxPipeline) * 100}%`,
                      background: stage.color,
                      boxShadow: `0 0 10px ${stage.color}40`,
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Recent Activity */}
        <div className="card animate-fade-in-up delay-3">
          <h3 className="section-title">⚡ Recent Jobs</h3>
          {recentJobs.length > 0 ? (
            <div className="activity-list">
              {recentJobs.map((job, i) => (
                <div key={job.id || i} className="activity-item">
                  <div className="activity-icon">💼</div>
                  <div className="activity-info">
                    <span className="activity-title">{job.title}</span>
                    <span className="activity-meta">{job.company} • {job.location || 'Remote'}</span>
                  </div>
                  {job.match_score != null && (
                    <span className="badge badge-primary">{job.match_score}%</span>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <div className="empty-state" style={{ padding: 'var(--space-8)' }}>
              <p>No jobs found yet. Start searching!</p>
            </div>
          )}
        </div>
      </div>

      {/* Quick Actions */}
      <div className="quick-actions animate-fade-in-up delay-4">
        <h3 className="section-title">🚀 Quick Actions</h3>
        <div className="actions-grid">
          {quickActions.map((action) => (
            <button
              key={action.page}
              className="action-card"
              onClick={() => onNavigate(action.page)}
            >
              <span className="action-icon">{action.icon}</span>
              <span className="action-label">{action.label}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
