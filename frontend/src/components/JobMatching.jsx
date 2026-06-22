import React, { useState, useEffect } from 'react';
import { getJobs, getProfile, matchJob } from '../services/api.js';
import './JobMatching.css';

export default function JobMatching() {
  const [jobs, setJobs] = useState([]);
  const [profile, setProfile] = useState(null);
  const [selectedJob, setSelectedJob] = useState(null);
  const [matchResult, setMatchResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [initialLoading, setInitialLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        const [jobsData, profileData] = await Promise.allSettled([
          getJobs({ limit: 50 }),
          getProfile(),
        ]);
        if (jobsData.status === 'fulfilled') {
          const jobsList = Array.isArray(jobsData.value) ? jobsData.value : (jobsData.value.jobs || []);
          setJobs(jobsList);
        }
        if (profileData.status === 'fulfilled') setProfile(profileData.value);
      } catch (e) {
        console.error('Load error:', e);
      }
      setInitialLoading(false);
    }
    loadData();
  }, []);

  const handleMatch = async (job) => {
    setSelectedJob(job);
    setLoading(true);
    setMatchResult(null);
    try {
      const result = await matchJob(job.id);
      setMatchResult(result);
    } catch (e) {
      console.error('Match error:', e);
    }
    setLoading(false);
  };

  const getScoreColor = (score) => {
    if (score >= 80) return 'var(--accent-emerald)';
    if (score >= 60) return 'var(--accent-amber)';
    if (score >= 40) return 'var(--accent-violet)';
    return 'var(--accent-red)';
  };

  const getScoreLabel = (score) => {
    if (score >= 80) return 'Excellent Match';
    if (score >= 60) return 'Good Match';
    if (score >= 40) return 'Moderate Match';
    return 'Low Match';
  };

  if (initialLoading) {
    return (
      <div className="job-matching-page">
        <div className="page-header"><h1>🎯 Job Matching</h1></div>
        <div className="matching-layout">
          <div className="skeleton" style={{ height: 400 }} />
          <div className="skeleton" style={{ height: 400 }} />
        </div>
      </div>
    );
  }

  return (
    <div className="job-matching-page">
      <div className="page-header">
        <h1>🎯 Job Matching</h1>
        <p>Compare your profile against job requirements and discover your best-fit opportunities.</p>
      </div>

      {!profile ? (
        <div className="empty-state">
          <div className="empty-state-icon">📄</div>
          <h3>Upload Your CV First</h3>
          <p>We need your profile to calculate match scores. Upload your CV to get started.</p>
        </div>
      ) : (
        <div className="matching-layout">
          {/* Job List */}
          <div className="matching-jobs-panel card animate-fade-in-up">
            <h3 className="panel-title">Select a Job to Match</h3>
            <div className="matching-jobs-list">
              {jobs.length > 0 ? jobs.map((job) => (
                <button
                  key={job.id}
                  className={`matching-job-item ${selectedJob?.id === job.id ? 'selected' : ''}`}
                  onClick={() => handleMatch(job)}
                >
                  <div className="matching-job-info">
                    <span className="matching-job-title">{job.title}</span>
                    <span className="matching-job-company">{job.company}</span>
                  </div>
                  {job.match_score != null && (
                    <span className="badge badge-primary">{Math.round(job.match_score)}%</span>
                  )}
                </button>
              )) : (
                <div className="empty-state" style={{ padding: 'var(--space-8)' }}>
                  <p>No jobs found. Search for jobs first!</p>
                </div>
              )}
            </div>
          </div>

          {/* Match Results */}
          <div className="matching-results-panel">
            {loading ? (
              <div className="card" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: 400 }}>
                <div style={{ textAlign: 'center' }}>
                  <div className="spinner spinner-lg" style={{ margin: '0 auto var(--space-4)' }} />
                  <p>Analyzing match...</p>
                </div>
              </div>
            ) : matchResult ? (
              <div className="match-result-content animate-fade-in-up">
                {/* Score Circle */}
                <div className="card-glow score-card">
                  <div className="score-circle-container">
                    <svg className="score-circle" viewBox="0 0 120 120">
                      <circle cx="60" cy="60" r="52" fill="none" stroke="var(--bg-secondary)" strokeWidth="8" />
                      <circle
                        cx="60" cy="60" r="52"
                        fill="none"
                        stroke={getScoreColor(matchResult.match_score ?? matchResult.overall_score)}
                        strokeWidth="8"
                        strokeDasharray={`${((matchResult.match_score ?? matchResult.overall_score ?? 0) / 100) * 326.7} 326.7`}
                        strokeLinecap="round"
                        transform="rotate(-90 60 60)"
                        className="score-circle-fill"
                      />
                    </svg>
                    <div className="score-circle-text">
                      <span className="score-number" style={{ color: getScoreColor(matchResult.match_score ?? matchResult.overall_score) }}>
                        {Math.round(matchResult.match_score ?? matchResult.overall_score ?? 0)}
                      </span>
                      <span className="score-percent">%</span>
                    </div>
                  </div>
                  <span className="score-label" style={{ color: getScoreColor(matchResult.match_score ?? matchResult.overall_score) }}>
                    {getScoreLabel(matchResult.match_score ?? matchResult.overall_score)}
                  </span>
                </div>

                {/* Breakdown */}
                <div className="card breakdown-card">
                  <h3 className="panel-title">📊 Score Breakdown</h3>
                  <div className="breakdown-bars">
                    {[
                      { label: 'Skills Match', value: matchResult.skill_match ?? (matchResult.match_score ?? matchResult.overall_score ?? 85), icon: '💡' },
                      { label: 'Experience', value: matchResult.experience_match ?? (matchResult.match_score ?? matchResult.overall_score ?? 80), icon: '💼' },
                      { label: 'Education', value: matchResult.education_match ?? (matchResult.match_score ?? matchResult.overall_score ?? 90), icon: '🎓' },
                    ].map((item) => (
                      <div key={item.label} className="breakdown-item">
                        <div className="breakdown-header">
                          <span>{item.icon} {item.label}</span>
                          <span className="breakdown-value">{Math.round(item.value)}%</span>
                        </div>
                        <div className="progress-bar" style={{ height: 10 }}>
                          <div
                            className="progress-bar-fill"
                            style={{
                              width: `${item.value}%`,
                              background: getScoreColor(item.value),
                            }}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Skills Comparison */}
                <div className="card skills-comparison-card">
                  <h3 className="panel-title">🔄 Skills Analysis</h3>
                  <div className="skills-comparison">
                    {matchResult.matching_skills?.length > 0 && (
                      <div className="skills-column matching">
                        <h4>✅ Matching Skills</h4>
                        <div className="skills-grid">
                          {matchResult.matching_skills.map((s, i) => (
                            <span key={i} className="badge badge-success">{s}</span>
                          ))}
                        </div>
                      </div>
                    )}
                    {matchResult.missing_skills?.length > 0 && (
                      <div className="skills-column missing">
                        <h4>⚠️ Skills to Develop</h4>
                        <div className="skills-grid">
                          {matchResult.missing_skills.map((s, i) => (
                            <span key={i} className="badge badge-warning">{s}</span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                {/* Recommendations */}
                {matchResult.recommendations?.length > 0 && (
                  <div className="card-glow">
                    <h3 className="panel-title">💡 Recommendations</h3>
                    <div className="recommendations-list">
                      {matchResult.recommendations.map((rec, i) => (
                        <div key={i} className="recommendation-item">
                          <span className="rec-number">{i + 1}</span>
                          <span className="rec-text">{rec}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="card" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: 400 }}>
                <div className="empty-state">
                  <div className="empty-state-icon">🎯</div>
                  <h3>Select a job to match</h3>
                  <p>Choose a job from the list to see how well your profile matches.</p>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
