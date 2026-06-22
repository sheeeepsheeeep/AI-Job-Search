import React, { useState, useCallback, useRef, useEffect } from 'react';
import { uploadCV, getRecommendations, getProfile } from '../services/api.js';
import './CVUpload.css';

export default function CVUpload() {
  const [file, setFile] = useState(null);
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [profile, setProfile] = useState(null);
  const [recommendations, setRecommendations] = useState(null);
  const [error, setError] = useState('');
  const fileInputRef = useRef(null);

  useEffect(() => {
    loadExistingProfile();
  }, []);

  const loadExistingProfile = async () => {
    try {
      const existingProfile = await getProfile();
      if (existingProfile && existingProfile.id) {
        setProfile(existingProfile);
        try {
          const recs = await getRecommendations(existingProfile.id);
          setRecommendations(recs);
        } catch (e) {
          console.error('Failed to load recommendations for existing profile:', e);
        }
      }
    } catch (e) {
      if (e.status === 404) {
        console.log('No profile uploaded yet (404)');
      } else {
        console.error('Failed to load existing profile:', e);
      }
    }
  };

  const handleDragOver = useCallback((e) => {
    e.preventDefault();
    setDragging(true);
  }, []);

  const handleDragLeave = useCallback((e) => {
    e.preventDefault();
    setDragging(false);
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setDragging(false);
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile) validateAndSetFile(droppedFile);
  }, []);

  const handleFileSelect = useCallback((e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) validateAndSetFile(selectedFile);
  }, []);

  const validateAndSetFile = (f) => {
    const validTypes = [
      'application/pdf',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'application/msword',
      'text/plain',
    ];
    if (!validTypes.includes(f.type)) {
      setError('Please upload a PDF, DOCX, DOC, or TXT file.');
      return;
    }
    if (f.size > 10 * 1024 * 1024) {
      setError('File size must be under 10MB.');
      return;
    }
    setFile(f);
    setError('');
    setProfile(null);
    setRecommendations(null);
  };

  const getFileIcon = (type) => {
    if (type?.includes('pdf')) return '📕';
    if (type?.includes('word') || type?.includes('document')) return '📘';
    return '📄';
  };

  const formatFileSize = (bytes) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    setError('');
    setProgress(0);

    // Simulate progress
    const progressInterval = setInterval(() => {
      setProgress((p) => (p < 90 ? p + Math.random() * 15 : p));
    }, 300);

    try {
      const result = await uploadCV(file);
      setProgress(100);
      setProfile(result);

      // Fetch recommendations
      if (result.id) {
        try {
          const recs = await getRecommendations(result.id);
          setRecommendations(recs);
        } catch (e) {
          console.error('Failed to load recommendations:', e);
        }
      }
    } catch (e) {
      setError(e.message || 'Upload failed. Please try again.');
    } finally {
      clearInterval(progressInterval);
      setUploading(false);
    }
  };

  const skillColors = [
    'badge-primary', 'badge-purple', 'badge-info', 'badge-success',
    'badge-warning', 'badge-pink', 'badge-danger',
  ];

  return (
    <div className="cv-upload-page">
      <div className="page-header">
        <h1>📄 CV Upload & Analysis</h1>
        <p>Upload your resume to get AI-powered insights, skill extraction, and career recommendations.</p>
      </div>

      {/* Upload Zone */}
      {!profile && (
        <div className="upload-section animate-fade-in-up">
          <div
            className={`upload-zone ${dragging ? 'dragging' : ''} ${file ? 'has-file' : ''}`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => !file && fileInputRef.current?.click()}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.docx,.doc,.txt"
              onChange={handleFileSelect}
              style={{ display: 'none' }}
            />

            {!file ? (
              <div className="upload-prompt">
                <div className="upload-icon animate-float">📁</div>
                <h3>Drop your CV here</h3>
                <p>or click to browse files</p>
                <div className="upload-types">
                  <span className="badge badge-primary">PDF</span>
                  <span className="badge badge-info">DOCX</span>
                  <span className="badge badge-purple">DOC</span>
                  <span className="badge badge-success">TXT</span>
                </div>
                <p className="upload-size-hint">Max file size: 10MB</p>
              </div>
            ) : (
              <div className="file-preview">
                <div className="file-icon">{getFileIcon(file.type)}</div>
                <div className="file-details">
                  <span className="file-name">{file.name}</span>
                  <span className="file-size">{formatFileSize(file.size)}</span>
                </div>
                <button
                  className="btn btn-ghost btn-sm"
                  onClick={(e) => { e.stopPropagation(); setFile(null); }}
                >
                  ✕
                </button>
              </div>
            )}
          </div>

          {uploading && (
            <div className="upload-progress">
              <div className="progress-bar">
                <div className="progress-bar-fill" style={{ width: `${progress}%` }} />
              </div>
              <span className="progress-text">
                {progress < 30 ? 'Uploading file...' : progress < 60 ? 'Parsing CV...' : progress < 90 ? 'AI Analysis...' : 'Complete!'} {Math.round(progress)}%
              </span>
            </div>
          )}

          {error && (
            <div className="upload-error animate-scale-in">
              <span>⚠️ {error}</span>
            </div>
          )}

          {file && !uploading && (
            <button className="btn btn-primary btn-lg upload-btn" onClick={handleUpload}>
              🚀 Analyze My CV
            </button>
          )}
        </div>
      )}

      {/* Profile Results */}
      {profile && (
        <div className="profile-results animate-fade-in-up">
          {/* Profile Header */}
          <div className="profile-header card-glow">
            <div className="profile-avatar">
              <span>{(profile.name || profile.full_name)?.[0] || '?'}</span>
            </div>
            <div className="profile-info">
              <h2>{profile.name || profile.full_name}</h2>
              <div className="profile-meta">
                {profile.email && <span>📧 {profile.email}</span>}
                {profile.phone && <span>📱 {profile.phone}</span>}
                {profile.location && <span>📍 {profile.location}</span>}
              </div>
              {profile.career_level && (
                <span className="badge badge-primary" style={{ marginTop: 'var(--space-2)' }}>
                  {profile.career_level}
                </span>
              )}
            </div>
            <button className="btn btn-secondary" onClick={() => { setProfile(null); setFile(null); }}>
              Upload New CV
            </button>
          </div>

          {/* Summary */}
          {profile.summary && (
            <div className="card animate-fade-in-up delay-1">
              <h3 className="section-title">📝 Professional Summary</h3>
              <p className="profile-summary">{profile.summary}</p>
            </div>
          )}

          {/* Skills */}
          {profile.skills?.length > 0 && (
            <div className="card animate-fade-in-up delay-2">
              <h3 className="section-title">💡 Skills</h3>
              <div className="skills-grid">
                {profile.skills.map((skill, i) => (
                  <span key={i} className={`badge ${skillColors[i % skillColors.length]}`}>
                    {typeof skill === 'string' ? skill : skill.name}
                    {skill.level && <span className="skill-level"> • {skill.level}</span>}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Experience Timeline */}
          {profile.experience?.length > 0 && (
            <div className="card animate-fade-in-up delay-3">
              <h3 className="section-title">💼 Experience</h3>
              <div className="timeline">
                {profile.experience.map((exp, i) => (
                  <div key={i} className="timeline-item">
                    <div className="timeline-dot" />
                    <div className="timeline-content">
                      <h4>{exp.title}</h4>
                      <span className="timeline-company">{exp.company}</span>
                      <span className="timeline-date">
                        {exp.start_date}{exp.end_date ? ` — ${exp.end_date}` : ' — Present'}
                        {exp.location && ` • ${exp.location}`}
                      </span>
                      {exp.description && <p className="timeline-desc">{exp.description}</p>}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Education */}
          {profile.education?.length > 0 && (
            <div className="card animate-fade-in-up delay-4">
              <h3 className="section-title">🎓 Education</h3>
              <div className="timeline">
                {profile.education.map((edu, i) => (
                  <div key={i} className="timeline-item">
                    <div className="timeline-dot education" />
                    <div className="timeline-content">
                      <h4>{edu.degree}</h4>
                      <span className="timeline-company">{edu.institution}</span>
                      {edu.field_of_study && <span className="timeline-date">{edu.field_of_study}</span>}
                      {edu.graduation_year && <span className="timeline-date">Graduated: {edu.graduation_year}</span>}
                      {edu.gpa && <span className="badge badge-success" style={{ marginTop: 4 }}>GPA: {edu.gpa}</span>}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Recommendations */}
          {(recommendations || profile.recommendations?.length > 0) && (
            <div className="card-glow animate-fade-in-up delay-5">
              <h3 className="section-title">🎯 Career Recommendations</h3>
              <div className="recommendations-list">
                {(recommendations?.recommendations || profile.recommendations || []).map((rec, i) => (
                  <div key={i} className="recommendation-item" style={{ display: 'block', marginBottom: 'var(--space-4)' }}>
                    {typeof rec === 'object' ? (
                      <>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', flexWrap: 'wrap' }}>
                          <span className="rec-number">{i + 1}</span>
                          <strong style={{ fontSize: 'var(--font-lg)', color: 'var(--color-primary)' }}>
                            {rec.role}
                          </strong>
                          {rec.growth_potential && (
                            <span className={`badge ${rec.growth_potential.toLowerCase() === 'high' ? 'badge-success' : rec.growth_potential.toLowerCase() === 'medium' ? 'badge-info' : 'badge-warning'}`}>
                              {rec.growth_potential} Growth
                            </span>
                          )}
                        </div>
                        {rec.reason && (
                          <p style={{ marginTop: 'var(--space-1)', marginLeft: '36px', color: 'var(--color-text-muted)' }}>
                            {rec.reason}
                          </p>
                        )}
                        {rec.required_upskilling?.length > 0 && (
                          <div style={{ marginTop: 'var(--space-2)', marginLeft: '36px' }}>
                            <span style={{ fontSize: 'var(--font-xs)', color: 'var(--color-text-muted)', display: 'block', marginBottom: 'var(--space-1)' }}>Upskilling required:</span>
                            <div className="skills-grid" style={{ gap: 'var(--space-1)' }}>
                              {rec.required_upskilling.map((skill, si) => (
                                <span key={si} className="badge badge-purple" style={{ fontSize: 'var(--font-xs)', padding: '2px 8px' }}>
                                  {skill}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}
                      </>
                    ) : (
                      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                        <span className="rec-number">{i + 1}</span>
                        <span className="rec-text">{rec}</span>
                      </div>
                    )}
                  </div>
                ))}
              </div>
              {recommendations?.suggested_roles?.length > 0 && (
                <div style={{ marginTop: 'var(--space-4)' }}>
                  <h4 style={{ marginBottom: 'var(--space-2)', fontSize: 'var(--font-base)' }}>Suggested Roles:</h4>
                  <div className="skills-grid">
                    {recommendations.suggested_roles.map((role, i) => (
                      <span key={i} className="badge badge-success">{role}</span>
                    ))}
                  </div>
                </div>
              )}
              {recommendations?.skill_gaps?.length > 0 && (
                <div style={{ marginTop: 'var(--space-4)' }}>
                  <h4 style={{ marginBottom: 'var(--space-2)', fontSize: 'var(--font-base)' }}>Skill Gaps to Address:</h4>
                  <div className="skills-grid">
                    {recommendations.skill_gaps.map((gap, i) => (
                      <span key={i} className="badge badge-warning">{gap}</span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
