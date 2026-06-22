import React, { useState, useEffect } from 'react';
import { getApplications, sendEmail, getEmailHistory, sendFollowUp } from '../services/api.js';
import './EmailManager.css';

export default function EmailManager() {
  const [applications, setApplications] = useState([]);
  const [history, setHistory] = useState([]);
  const [filter, setFilter] = useState('all');
  const [composeOpen, setComposeOpen] = useState(true);
  const [sending, setSending] = useState(false);
  const [toast, setToast] = useState(null);

  // Compose form
  const [selectedApp, setSelectedApp] = useState('');
  const [recipientEmail, setRecipientEmail] = useState('');
  const [subject, setSubject] = useState('');
  const [body, setBody] = useState('');
  const [emailType, setEmailType] = useState('application');

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    try {
      const [appsData, historyData] = await Promise.allSettled([
        getApplications(),
        getEmailHistory(),
      ]);
      if (appsData.status === 'fulfilled') {
        setApplications(appsData.value.applications || appsData.value || []);
      }
      if (historyData.status === 'fulfilled') {
        setHistory(historyData.value.emails || historyData.value || []);
      }
    } catch (e) {
      console.error('Load error:', e);
    }
  }

  // Compute stats from history
  const stats = {
    total: history.length,
    sent: history.filter(e => e.status === 'sent' || e.status === 'Sent').length,
    delivered: history.filter(e => e.status === 'delivered' || e.status === 'Delivered').length,
    failed: history.filter(e => e.status === 'failed' || e.status === 'Failed').length,
    pending: history.filter(e => e.status === 'pending' || e.status === 'Pending').length,
  };

  // Check duplicate
  const isDuplicate = recipientEmail && subject &&
    history.some(h =>
      h.recipient_email === recipientEmail &&
      h.subject === subject
    );

  const handleSend = async () => {
    if (!recipientEmail || !subject || !body) {
      showToast('Please fill all required fields', 'error');
      return;
    }
    if (isDuplicate) {
      showToast('Warning: This appears to be a duplicate email', 'error');
      return;
    }
    setSending(true);
    try {
      await sendEmail(
        selectedApp ? parseInt(selectedApp) : null,
        recipientEmail,
        subject,
        body,
        emailType
      );
      showToast('Email sent successfully!', 'success');
      setRecipientEmail('');
      setSubject('');
      setBody('');
      setSelectedApp('');
      await loadData();
    } catch (e) {
      showToast(e.message || 'Failed to send email', 'error');
    }
    setSending(false);
  };

  const handleFollowUp = async (appId) => {
    try {
      await sendFollowUp(appId);
      showToast('Follow-up email sent!', 'success');
      await loadData();
    } catch (e) {
      showToast(e.message || 'Failed to send follow-up', 'error');
    }
  };

  const showToast = (msg, type) => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 3000);
  };

  const filteredHistory = filter === 'all'
    ? history
    : history.filter(h => h.status?.toLowerCase() === filter);

  const getStatusClass = (status) => {
    if (!status) return 'pending';
    const s = status.toLowerCase();
    if (s === 'delivered') return 'delivered';
    if (s === 'failed') return 'failed';
    if (s === 'pending') return 'pending';
    return 'sent';
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '—';
    const d = new Date(dateStr);
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  };

  return (
    <div className="email-page">
      <div className="page-header">
        <div>
          <h1>📧 Email Manager</h1>
          <p>Send application emails, track delivery, and manage follow-ups</p>
        </div>
      </div>

      {/* Stats */}
      <div className="email-stats">
        <div className="email-stat-card">
          <div className="email-stat-icon sent">📨</div>
          <div className="email-stat-info">
            <h4>{stats.total}</h4>
            <p>Total Emails</p>
          </div>
        </div>
        <div className="email-stat-card">
          <div className="email-stat-icon delivered">✅</div>
          <div className="email-stat-info">
            <h4>{stats.delivered + stats.sent}</h4>
            <p>Sent / Delivered</p>
          </div>
        </div>
        <div className="email-stat-card">
          <div className="email-stat-icon failed">❌</div>
          <div className="email-stat-info">
            <h4>{stats.failed}</h4>
            <p>Failed</p>
          </div>
        </div>
        <div className="email-stat-card">
          <div className="email-stat-icon pending">⏳</div>
          <div className="email-stat-info">
            <h4>{stats.pending}</h4>
            <p>Pending</p>
          </div>
        </div>
      </div>

      {/* Compose */}
      <div className="email-compose-card">
        <div
          className="email-compose-header"
          onClick={() => setComposeOpen(!composeOpen)}
        >
          <h3>✏️ Compose Email</h3>
          <span className={`email-compose-toggle ${composeOpen ? 'open' : ''}`}>▼</span>
        </div>
        {composeOpen && (
          <div className="email-compose-body">
            <div className="email-compose-row">
              <div className="input-group">
                <label>Application (optional)</label>
                <select value={selectedApp} onChange={e => setSelectedApp(e.target.value)}>
                  <option value="">— Link to application —</option>
                  {applications.map(app => (
                    <option key={app.id} value={app.id}>
                      {app.job_title} @ {app.company_name}
                    </option>
                  ))}
                </select>
              </div>
              <div className="input-group">
                <label>Email Type</label>
                <select value={emailType} onChange={e => setEmailType(e.target.value)}>
                  <option value="application">Application</option>
                  <option value="follow_up">Follow-up</option>
                  <option value="thank_you">Thank You</option>
                  <option value="inquiry">Inquiry</option>
                </select>
              </div>
            </div>

            <div className="input-group">
              <label>Recipient Email *</label>
              <input
                type="email"
                placeholder="hiring@company.com"
                value={recipientEmail}
                onChange={e => setRecipientEmail(e.target.value)}
              />
            </div>

            {isDuplicate && (
              <div className="email-duplicate-warning">
                ⚠️ A similar email has already been sent to this address with the same subject. Sending may result in a duplicate.
              </div>
            )}

            <div className="input-group">
              <label>Subject *</label>
              <input
                type="text"
                placeholder="Application for Software Engineer position"
                value={subject}
                onChange={e => setSubject(e.target.value)}
              />
            </div>

            <div className="input-group">
              <label>Body *</label>
              <textarea
                placeholder="Dear Hiring Manager,&#10;&#10;I am writing to express my interest in..."
                value={body}
                onChange={e => setBody(e.target.value)}
                rows={6}
              />
            </div>

            <div className="email-compose-actions">
              <button
                className="email-send-btn"
                onClick={handleSend}
                disabled={sending || !recipientEmail || !subject || !body}
              >
                {sending ? (
                  <><span className="spinner" /> Sending...</>
                ) : (
                  <>🚀 Send Email</>
                )}
              </button>
              <button
                className="btn btn-ghost"
                onClick={() => { setRecipientEmail(''); setSubject(''); setBody(''); setSelectedApp(''); }}
              >
                Clear
              </button>
            </div>
          </div>
        )}
      </div>

      {/* History */}
      <div className="email-history-card">
        <div className="email-history-header">
          <h3>📋 Email History</h3>
          <div className="email-filter-btns">
            {['all', 'sent', 'delivered', 'failed', 'pending'].map(f => (
              <button
                key={f}
                className={`email-filter-btn ${filter === f ? 'active' : ''}`}
                onClick={() => setFilter(f)}
              >
                {f.charAt(0).toUpperCase() + f.slice(1)}
              </button>
            ))}
          </div>
        </div>

        {filteredHistory.length > 0 ? (
          <div className="email-table-wrap">
            <table className="email-table">
              <thead>
                <tr>
                  <th>Recipient</th>
                  <th>Subject</th>
                  <th>Type</th>
                  <th>Date</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredHistory.map((item, idx) => (
                  <tr key={item.id || idx}>
                    <td style={{ color: 'var(--text-primary)', fontWeight: 500 }}>
                      {item.recipient_email || item.email_address || '—'}
                    </td>
                    <td>{item.subject || '—'}</td>
                    <td>
                      <span className="badge badge-purple">
                        {item.email_type || item.type || 'Application'}
                      </span>
                    </td>
                    <td style={{ color: 'var(--text-tertiary)', fontSize: 'var(--font-sm)' }}>
                      {formatDate(item.sent_at || item.date_sent)}
                    </td>
                    <td>
                      <span className={`email-status ${getStatusClass(item.status)}`}>
                        {item.status || 'Sent'}
                      </span>
                    </td>
                    <td>
                      {item.application_id && (
                        <button
                          className="email-follow-up-btn"
                          onClick={() => handleFollowUp(item.application_id)}
                        >
                          📩 Follow Up
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="empty-state">
            <div className="empty-state-icon">📭</div>
            <h3>No Emails Yet</h3>
            <p>Send your first application email to get started</p>
          </div>
        )}
      </div>

      {/* Toast */}
      {toast && (
        <div className={`email-toast ${toast.type}`}>
          {toast.type === 'success' ? '✅' : '❌'} {toast.msg}
        </div>
      )}
    </div>
  );
}
