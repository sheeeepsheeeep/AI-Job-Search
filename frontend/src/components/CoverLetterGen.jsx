import React, { useState, useEffect } from 'react';
import { getJobs, getProfile, generateCoverLetter, downloadCoverLetterPdf } from '../services/api.js';
import './CoverLetterGen.css';

export default function CoverLetterGen() {
  const [jobs, setJobs] = useState([]);
  const [profile, setProfile] = useState(null);
  const [selectedJob, setSelectedJob] = useState('');
  const [tone, setTone] = useState('professional');
  const [focusAreas, setFocusAreas] = useState('');
  const [additionalNotes, setAdditionalNotes] = useState('');
  const [generating, setGenerating] = useState(false);
  const [result, setResult] = useState(null);
  const [toast, setToast] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    async function loadData() {
      try {
        const [jobsData, profileData] = await Promise.allSettled([
          getJobs(),
          getProfile(),
        ]);
        if (jobsData.status === 'fulfilled') {
          const j = jobsData.value.jobs || jobsData.value || [];
          setJobs(j);
        }
        if (profileData.status === 'fulfilled') {
          setProfile(profileData.value);
        }
      } catch (e) {
        console.error('Load error:', e);
      }
    }
    loadData();
  }, []);

  const tones = [
    { value: 'professional', label: '💼 Professional' },
    { value: 'enthusiastic', label: '🔥 Enthusiastic' },
    { value: 'conversational', label: '💬 Conversational' },
    { value: 'formal', label: '🎩 Formal' },
    { value: 'creative', label: '🎨 Creative' },
  ];

  const handleGenerate = async () => {
    if (!selectedJob) {
      setError('Please select a job first');
      return;
    }
    setGenerating(true);
    setError('');
    setResult(null);
    try {
      const data = await generateCoverLetter(
        parseInt(selectedJob),
        profile?.id,
        tone,
        focusAreas ? focusAreas.split(',').map(s => s.trim()) : undefined,
        additionalNotes || undefined
      );
      setResult(data);
    } catch (e) {
      setError(e.message || 'Failed to generate cover letter');
    }
    setGenerating(false);
  };

  const handleCopy = (text, label) => {
    navigator.clipboard.writeText(text).then(() => {
      setToast(`${label} copied to clipboard!`);
      setTimeout(() => setToast(''), 2500);
    });
  };

  const handleDownloadPdf = async () => {
    const clId = result?.cover_letter?.id || result?.id;
    if (!clId) return;
    try {
      const blob = await downloadCoverLetterPdf(clId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `cover_letter_${clId}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
      setToast('PDF downloaded!');
      setTimeout(() => setToast(''), 2500);
    } catch (e) {
      setError('Failed to download PDF');
    }
  };

  const selectedJobData = jobs.find(j => String(j.id) === String(selectedJob));

  return (
    <div className="cover-letter-page">
      <div className="page-header">
        <div>
          <h1>✉️ Cover Letter Generator</h1>
          <p>Generate personalized cover letters and email templates powered by AI</p>
        </div>
      </div>

      {/* Config Panel */}
      <div className="cl-config-panel">
        <div className="cl-config-card">
          <h3>📋 Job Selection</h3>
          <div className="cl-form-group">
            <label>
              Select a job to write for
              <select
                value={selectedJob}
                onChange={e => setSelectedJob(e.target.value)}
              >
                <option value="">— Choose a job —</option>
                {jobs.map(job => (
                  <option key={job.id} value={job.id}>
                    {job.title} @ {job.company}
                  </option>
                ))}
              </select>
            </label>

            {selectedJobData && (
              <div className="cl-selected-job-info" style={{
                padding: 'var(--space-3)',
                background: 'rgba(99, 102, 241, 0.05)',
                borderRadius: 'var(--radius-md)',
                border: '1px solid rgba(99, 102, 241, 0.1)',
              }}>
                <p style={{ color: 'var(--text-primary)', fontWeight: 600, fontSize: 'var(--font-sm)' }}>
                  {selectedJobData.title}
                </p>
                <p style={{ color: 'var(--text-tertiary)', fontSize: 'var(--font-xs)', marginTop: '4px' }}>
                  {selectedJobData.company} • {selectedJobData.location} • {selectedJobData.remote_status}
                </p>
              </div>
            )}

            <label>
              Focus areas (comma-separated)
              <input
                type="text"
                placeholder="e.g., leadership, problem-solving, Python"
                value={focusAreas}
                onChange={e => setFocusAreas(e.target.value)}
              />
            </label>
          </div>
        </div>

        <div className="cl-config-card">
          <h3>🎨 Tone & Style</h3>
          <div className="cl-form-group">
            <label>Select writing tone</label>
            <div className="cl-tone-options">
              {tones.map(t => (
                <button
                  key={t.value}
                  className={`cl-tone-btn ${tone === t.value ? 'active' : ''}`}
                  onClick={() => setTone(t.value)}
                >
                  {t.label}
                </button>
              ))}
            </div>

            <label>
              Additional notes for the AI
              <textarea
                placeholder="Any special instructions, achievements to highlight, or specific company details..."
                value={additionalNotes}
                onChange={e => setAdditionalNotes(e.target.value)}
                rows={3}
              />
            </label>
          </div>
        </div>
      </div>

      {/* Generate Button */}
      <div className="cl-generate-section">
        <button
          className="cl-generate-btn"
          onClick={handleGenerate}
          disabled={generating || !selectedJob}
        >
          {generating ? (
            <>
              <span className="spinner" /> Generating...
            </>
          ) : (
            <>✨ Generate Cover Letter</>
          )}
        </button>
        {error && (
          <span style={{ color: 'var(--accent-red)', fontSize: 'var(--font-sm)' }}>
            ⚠️ {error}
          </span>
        )}
        {!profile && (
          <span style={{ color: 'var(--accent-amber)', fontSize: 'var(--font-sm)' }}>
            💡 Upload your CV first for best results
          </span>
        )}
      </div>

      {/* Preview Section */}
      {result ? (
        <div className="cl-preview-section">
          {/* Cover Letter Preview */}
          <div className="cl-preview-card">
            <div className="cl-preview-header">
              <h3>📝 Cover Letter</h3>
              <div className="cl-preview-actions">
                <button
                  className="cl-action-btn"
                  onClick={() => handleCopy(
                    typeof result.cover_letter === 'object' ? result.cover_letter.content : (result.cover_letter || result.content),
                    'Cover letter'
                  )}
                >
                  📋 Copy
                </button>
                <button
                  className="cl-action-btn download-btn"
                  onClick={handleDownloadPdf}
                >
                  📥 Download PDF
                </button>
              </div>
            </div>
            <div className="cl-preview-body">
              <div className="cl-letter-content">
                {typeof result.cover_letter === 'object' ? result.cover_letter.content : (result.cover_letter || result.content || 'No content generated.')}
              </div>
            </div>
          </div>

          {/* Email Template Preview */}
          <div className="cl-preview-card">
            <div className="cl-preview-header">
              <h3>📧 Email Template</h3>
              <div className="cl-preview-actions">
                <button
                  className="cl-action-btn"
                  onClick={() => handleCopy(
                    `Subject: ${result.email_subject || ''}\n\n${result.email_body || result.email_template || ''}`,
                    'Email template'
                  )}
                >
                  📋 Copy All
                </button>
              </div>
            </div>
            <div className="cl-preview-body">
              {result.email_subject && (
                <div className="cl-email-subject">
                  <span>Subject</span>
                  <p>{result.email_subject}</p>
                </div>
              )}
              <div className="cl-email-body">
                {result.email_body || result.email_template || 'No email template generated.'}
              </div>
            </div>
          </div>
        </div>
      ) : (
        !generating && (
          <div className="cl-preview-card" style={{ gridColumn: '1 / -1' }}>
            <div className="cl-empty-state">
              <div className="cl-empty-icon">✉️</div>
              <h3>No Cover Letter Yet</h3>
              <p>Select a job and click "Generate" to create a personalized cover letter and email template</p>
            </div>
          </div>
        )
      )}

      {/* Loading State */}
      {generating && (
        <div className="cl-preview-section">
          <div className="cl-preview-card">
            <div className="cl-preview-body" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', padding: 'var(--space-16)' }}>
              <div className="spinner spinner-lg" style={{ marginBottom: 'var(--space-4)' }} />
              <h3 style={{ marginBottom: 'var(--space-2)' }}>Crafting Your Cover Letter...</h3>
              <p style={{ color: 'var(--text-tertiary)' }}>Our AI is personalizing your letter for this role</p>
            </div>
          </div>
          <div className="cl-preview-card">
            <div className="cl-preview-body" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', padding: 'var(--space-16)' }}>
              <div className="spinner spinner-lg" style={{ marginBottom: 'var(--space-4)' }} />
              <h3 style={{ marginBottom: 'var(--space-2)' }}>Writing Email Template...</h3>
              <p style={{ color: 'var(--text-tertiary)' }}>Creating a concise, professional email</p>
            </div>
          </div>
        </div>
      )}

      {/* Toast */}
      {toast && <div className="cl-toast">{toast}</div>}
    </div>
  );
}
