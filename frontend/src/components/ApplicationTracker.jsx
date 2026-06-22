import React, { useState, useEffect } from 'react';
import { getApplications, updateApplicationStatus, getStats, getInsights } from '../services/api.js';
import './ApplicationTracker.css';

const STATUSES = [
  { key: 'Applied', label: 'Applied', icon: '📨', colClass: 'applied' },
  { key: 'Under Review', label: 'Under Review', icon: '🔍', colClass: 'review' },
  { key: 'Interview Scheduled', label: 'Interview', icon: '📅', colClass: 'interview' },
  { key: 'Rejected', label: 'Rejected', icon: '❌', colClass: 'rejected' },
  { key: 'Offer Received', label: 'Offer', icon: '🎉', colClass: 'offer' },
];

export default function ApplicationTracker() {
  const [applications, setApplications] = useState([]);
  const [stats, setStats] = useState(null);
  const [insights, setInsights] = useState(null);
  const [view, setView] = useState('board'); // 'board' or 'list'
  const [filterStatus, setFilterStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [expandedCard, setExpandedCard] = useState(null);

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    setLoading(true);
    try {
      const [appsData, statsData, insightsData] = await Promise.allSettled([
        getApplications(),
        getStats(),
        getInsights(),
      ]);
      if (appsData.status === 'fulfilled') {
        setApplications(appsData.value.applications || appsData.value || []);
      }
      if (statsData.status === 'fulfilled') {
        setStats(statsData.value);
      }
      if (insightsData.status === 'fulfilled') {
        setInsights(insightsData.value);
      }
    } catch (e) {
      console.error('Load error:', e);
    }
    setLoading(false);
  }

  const handleStatusChange = async (appId, newStatus) => {
    try {
      await updateApplicationStatus(appId, newStatus);
      setApplications(prev =>
        prev.map(app =>
          app.id === appId ? { ...app, status: newStatus } : app
        )
      );
    } catch (e) {
      console.error('Status update error:', e);
    }
  };

  const getAppsByStatus = (status) => {
    return applications.filter(app => app.status === status);
  };

  const getStatusCounts = () => {
    const counts = {};
    STATUSES.forEach(s => {
      counts[s.key] = applications.filter(a => a.status === s.key).length;
    });
    return counts;
  };

  const counts = getStatusCounts();
  const totalApps = applications.length;

  const formatDate = (dateStr) => {
    if (!dateStr) return '—';
    const d = new Date(dateStr);
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };

  const responseRate = stats?.response_rate
    ? `${Number(stats.response_rate).toFixed(0)}%`
    : totalApps > 0
      ? `${(((counts['Under Review'] || 0) + (counts['Interview Scheduled'] || 0) + (counts['Offer Received'] || 0)) / totalApps * 100).toFixed(0)}%`
      : '0%';

  const filteredApps = filterStatus
    ? applications.filter(a => a.status === filterStatus)
    : applications;

  return (
    <div className="tracker-page">
      <div className="page-header">
        <div>
          <h1>📊 Application Tracker</h1>
          <p>Track all your job applications through the hiring pipeline</p>
        </div>
        <div className="tracker-filters">
          <div className="tracker-view-btns">
            <button
              className={`tracker-view-btn ${view === 'board' ? 'active' : ''}`}
              onClick={() => setView('board')}
            >
              📋 Board
            </button>
            <button
              className={`tracker-view-btn ${view === 'list' ? 'active' : ''}`}
              onClick={() => setView('list')}
            >
              📝 List
            </button>
          </div>
        </div>
      </div>

      {/* Stats Row */}
      <div className="tracker-stats">
        {STATUSES.map(status => (
          <div
            key={status.key}
            className={`tracker-stat ${status.colClass} ${filterStatus === status.key ? 'active' : ''}`}
            onClick={() => setFilterStatus(filterStatus === status.key ? null : status.key)}
          >
            <div className="tracker-stat-value">{counts[status.key] || 0}</div>
            <div className="tracker-stat-label">{status.label}</div>
          </div>
        ))}
      </div>

      {/* Kanban Board View */}
      {view === 'board' && (
        <div className="tracker-board">
          {STATUSES.map(status => {
            const statusApps = getAppsByStatus(status.key);
            return (
              <div key={status.key} className={`tracker-column ${status.colClass}`}>
                <div className="tracker-column-header">
                  <span className="tracker-column-title">
                    {status.icon} {status.label}
                  </span>
                  <span className="tracker-column-count">{statusApps.length}</span>
                </div>
                <div className="tracker-column-body">
                  {statusApps.length > 0 ? (
                    statusApps.map(app => (
                      <div
                        key={app.id}
                        className="tracker-card"
                        onClick={() => setExpandedCard(expandedCard === app.id ? null : app.id)}
                      >
                        <div className="tracker-card-company">{app.company_name}</div>
                        <div className="tracker-card-title">{app.job_title}</div>
                        <div className="tracker-card-meta">
                          <span className="tracker-card-date">
                            📅 {formatDate(app.date_sent || app.created_at)}
                          </span>
                          {app.email_address && (
                            <span title={app.email_address}>✉️</span>
                          )}
                        </div>

                        {expandedCard === app.id && (
                          <div className="tracker-card-actions">
                            {STATUSES.filter(s => s.key !== app.status).map(s => (
                              <button
                                key={s.key}
                                className="tracker-card-action"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleStatusChange(app.id, s.key);
                                }}
                              >
                                {s.icon} {s.label}
                              </button>
                            ))}
                          </div>
                        )}
                      </div>
                    ))
                  ) : (
                    <div className="tracker-column-empty">
                      <div className="tracker-column-empty-icon">{status.icon}</div>
                      <span>No applications</span>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* List View */}
      {view === 'list' && (
        <div className="tracker-list">
          {filteredApps.length > 0 ? (
            <div className="table-container">
              <table>
                <thead>
                  <tr>
                    <th>Company</th>
                    <th>Position</th>
                    <th>Status</th>
                    <th>Date Applied</th>
                    <th>Follow-up</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredApps.map(app => {
                    const statusInfo = STATUSES.find(s => s.key === app.status) || STATUSES[0];
                    return (
                      <tr key={app.id}>
                        <td style={{ color: 'var(--text-primary)', fontWeight: 600 }}>
                          {app.company_name}
                        </td>
                        <td>{app.job_title}</td>
                        <td>
                          <span className={`badge badge-${
                            statusInfo.colClass === 'applied' ? 'primary' :
                            statusInfo.colClass === 'review' ? 'info' :
                            statusInfo.colClass === 'interview' ? 'success' :
                            statusInfo.colClass === 'rejected' ? 'danger' : 'warning'
                          }`}>
                            {statusInfo.icon} {statusInfo.label}
                          </span>
                        </td>
                        <td style={{ color: 'var(--text-tertiary)', fontSize: 'var(--font-sm)' }}>
                          {formatDate(app.date_sent || app.created_at)}
                        </td>
                        <td style={{ color: 'var(--text-tertiary)', fontSize: 'var(--font-sm)' }}>
                          {app.follow_up_date ? formatDate(app.follow_up_date) : '—'}
                        </td>
                        <td>
                          <select
                            value={app.status}
                            onChange={e => handleStatusChange(app.id, e.target.value)}
                            style={{
                              padding: '4px 8px',
                              fontSize: 'var(--font-xs)',
                              background: 'var(--bg-secondary)',
                              border: '1px solid var(--glass-border)',
                              borderRadius: 'var(--radius-md)',
                              color: 'var(--text-secondary)',
                              cursor: 'pointer',
                            }}
                          >
                            {STATUSES.map(s => (
                              <option key={s.key} value={s.key}>{s.label}</option>
                            ))}
                          </select>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="empty-state">
              <div className="empty-state-icon">📭</div>
              <h3>No Applications Yet</h3>
              <p>Start applying to jobs to track your progress here</p>
            </div>
          )}
        </div>
      )}

      {/* Insights */}
      <div className="tracker-insights">
        <h3>📈 Analytics & Insights</h3>
        <div className="insights-grid">
          <div className="insight-card">
            <h4>📊 Total Applications</h4>
            <div className="insight-value">{totalApps}</div>
            <p>Across all stages</p>
          </div>
          <div className="insight-card">
            <h4>📈 Response Rate</h4>
            <div className="insight-value" style={{ color: 'var(--accent-emerald)' }}>
              {responseRate}
            </div>
            <p>Applications that progressed</p>
          </div>
          <div className="insight-card">
            <h4>🎯 Interview Rate</h4>
            <div className="insight-value" style={{ color: 'var(--accent-cyan)' }}>
              {totalApps > 0
                ? `${(((counts['Interview Scheduled'] || 0) / totalApps) * 100).toFixed(0)}%`
                : '0%'}
            </div>
            <p>Applications reaching interview</p>
          </div>
        </div>

        {/* Pipeline Visualization */}
        {totalApps > 0 && (
          <div style={{ marginTop: 'var(--space-6)' }}>
            <h4 style={{
              fontSize: 'var(--font-sm)',
              color: 'var(--text-tertiary)',
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
              marginBottom: 'var(--space-3)',
            }}>
              Pipeline Distribution
            </h4>
            <div style={{
              display: 'flex',
              height: '32px',
              borderRadius: 'var(--radius-full)',
              overflow: 'hidden',
              background: 'var(--bg-secondary)',
            }}>
              {STATUSES.map(status => {
                const count = counts[status.key] || 0;
                const pct = (count / totalApps) * 100;
                if (pct === 0) return null;
                const colors = {
                  applied: 'var(--accent-indigo)',
                  review: 'var(--accent-cyan)',
                  interview: 'var(--accent-emerald)',
                  rejected: 'var(--accent-red)',
                  offer: 'var(--accent-amber)',
                };
                return (
                  <div
                    key={status.key}
                    title={`${status.label}: ${count} (${pct.toFixed(0)}%)`}
                    style={{
                      width: `${pct}%`,
                      background: colors[status.colClass],
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontSize: 'var(--font-xs)',
                      fontWeight: 'var(--weight-bold)',
                      color: 'white',
                      minWidth: pct > 8 ? 'auto' : '0',
                      transition: 'width var(--transition-slow)',
                    }}
                  >
                    {pct > 12 && `${status.label} ${count}`}
                  </div>
                );
              })}
            </div>
            <div style={{
              display: 'flex',
              gap: 'var(--space-4)',
              marginTop: 'var(--space-3)',
              flexWrap: 'wrap',
            }}>
              {STATUSES.map(status => {
                const count = counts[status.key] || 0;
                if (count === 0) return null;
                const colors = {
                  applied: 'var(--accent-indigo)',
                  review: 'var(--accent-cyan)',
                  interview: 'var(--accent-emerald)',
                  rejected: 'var(--accent-red)',
                  offer: 'var(--accent-amber)',
                };
                return (
                  <div key={status.key} style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 'var(--space-2)',
                    fontSize: 'var(--font-xs)',
                    color: 'var(--text-tertiary)',
                  }}>
                    <span style={{
                      width: '10px',
                      height: '10px',
                      borderRadius: 'var(--radius-full)',
                      background: colors[status.colClass],
                    }} />
                    {status.label}: {count}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* AI Insights */}
        {insights && insights.analysis && (
          <div style={{
            marginTop: 'var(--space-6)',
            padding: 'var(--space-4)',
            background: 'rgba(139, 92, 246, 0.05)',
            border: '1px solid rgba(139, 92, 246, 0.1)',
            borderRadius: 'var(--radius-lg)',
          }}>
            <h4 style={{
              fontSize: 'var(--font-sm)',
              color: 'var(--accent-violet)',
              marginBottom: 'var(--space-2)',
              display: 'flex',
              alignItems: 'center',
              gap: 'var(--space-2)',
            }}>
              🤖 AI Insights
            </h4>
            <p style={{
              color: 'var(--text-secondary)',
              fontSize: 'var(--font-sm)',
              lineHeight: 'var(--leading-relaxed)',
            }}>
              {typeof insights.analysis === 'string' ? insights.analysis : JSON.stringify(insights.analysis)}
            </p>
          </div>
        )}
      </div>

      {/* Loading Overlay */}
      {loading && (
        <div style={{
          display: 'flex',
          justifyContent: 'center',
          padding: 'var(--space-16)',
        }}>
          <div className="spinner spinner-lg" />
        </div>
      )}
    </div>
  );
}
