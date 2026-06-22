import React, { useState, useEffect } from 'react';
import { searchJobs, getJobs, matchJob, getProfile } from '../services/api.js';
import './JobSearch.css';

export default function JobSearch({ onNavigate }) {
  const [query, setQuery] = useState('');
  const [location, setLocation] = useState('');
  const [jobs, setJobs] = useState([]);
  const [searching, setSearching] = useState(false);
  const [expandedJob, setExpandedJob] = useState(null);
  const [matchingJob, setMatchingJob] = useState(null);
  const [matchScores, setMatchScores] = useState({});
  const [error, setError] = useState('');

  const [filters, setFilters] = useState({
    remote: null,
    experience_level: '',
    job_type: '',
  });

  useEffect(() => {
    loadExistingJobs();
    loadProfileAndPrefill();
  }, []);

  const loadExistingJobs = async () => {
    try {
      const data = await getJobs({ limit: 20 });
      const jobsList = Array.isArray(data) ? data : (data.jobs || []);
      if (jobsList.length > 0) setJobs(jobsList);
    } catch (e) {
      console.error('Failed to load jobs:', e);
    }
  };

  const loadProfileAndPrefill = async () => {
    try {
      const profile = await getProfile();
      if (profile) {
        // Pre-fill query with experience[0].title or first skill
        let prefillQuery = '';
        if (profile.experience && profile.experience.length > 0) {
          prefillQuery = profile.experience[0].title;
        } else if (profile.skills && profile.skills.length > 0) {
          prefillQuery = profile.skills[0];
        }
        
        const defaultLoc = '';
        
        if (prefillQuery) {
          setQuery(prefillQuery);
          setLocation(defaultLoc);
          
          // Auto-trigger search
          setSearching(true);
          setError('');
          try {
            const data = await searchJobs(prefillQuery, defaultLoc, filters);
            const jobsList = Array.isArray(data) ? data : (data.jobs || []);
            setJobs(jobsList);
          } catch (err) {
            setError(err.message || 'Auto-search failed');
          } finally {
            setSearching(false);
          }
        } else {
          setLocation(defaultLoc);
        }
      }
    } catch (e) {
      console.error('Failed to load profile for prefill:', e);
    }
  };

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!query.trim()) return;
    setSearching(true);
    setError('');

    try {
      const data = await searchJobs(query, location || null, filters);
      const jobsList = Array.isArray(data) ? data : (data.jobs || []);
      setJobs(jobsList);
    } catch (e) {
      setError(e.message || 'Search failed');
    }
    setSearching(false);
  };

  const handleMatch = async (jobId) => {
    setMatchingJob(jobId);
    try {
      const result = await matchJob(jobId);
      setMatchScores((prev) => ({ ...prev, [jobId]: result }));
    } catch (e) {
      console.error('Match failed:', e);
    }
    setMatchingJob(null);
  };

  const filterPills = [
    { key: 'remote', label: '🏠 Remote', values: [{ v: true, l: 'Remote' }, { v: false, l: 'On-site' }] },
    { key: 'experience_level', label: '📊 Level', values: [
      { v: 'junior', l: 'Junior' }, { v: 'mid', l: 'Mid' }, { v: 'senior', l: 'Senior' }, { v: 'lead', l: 'Lead' },
    ]},
    { key: 'job_type', label: '📋 Type', values: [
      { v: 'full-time', l: 'Full-time' }, { v: 'part-time', l: 'Part-time' }, { v: 'contract', l: 'Contract' },
    ]},
  ];

  return (
    <div className="job-search-page">
      <div className="page-header">
        <h1>🔍 Job Search</h1>
        <p>Discover opportunities matched to your skills and preferences with AI-powered search.</p>
      </div>

      {/* Search Bar */}
      <form className="search-form animate-fade-in-up" onSubmit={handleSearch}>
        <div className="search-bar">
          <div className="search-input-wrapper">
            <span className="search-icon">🔍</span>
            <input
              type="text"
              placeholder="Job title, skills, or keywords..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="search-input"
            />
          </div>
          <div className="search-location-wrapper">
            <span className="search-icon">📍</span>
            <input
              type="text"
              placeholder="Location..."
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              className="search-input"
            />
          </div>
          <button
            type="submit"
            className="btn btn-primary search-submit"
            disabled={searching || !query.trim()}
          >
            {searching ? <span className="spinner" /> : '🔍'} Search
          </button>
        </div>
      </form>

      {/* Filters */}
      <div className="filters-section animate-fade-in-up delay-1">
        {filterPills.map((filter) => (
          <div key={filter.key} className="filter-group">
            <span className="filter-label">{filter.label}</span>
            <div className="filter-pills">
              {filter.values.map(({ v, l }) => (
                <button
                  key={String(v)}
                  className={`filter-pill ${filters[filter.key] === v ? 'active' : ''}`}
                  onClick={() =>
                    setFilters((f) => ({ ...f, [filter.key]: f[filter.key] === v ? (filter.key === 'remote' ? null : '') : v }))
                  }
                >
                  {l}
                </button>
              ))}
            </div>
          </div>
        ))}
      </div>

      {error && (
        <div className="upload-error animate-scale-in">
          <span>⚠️ {error}</span>
        </div>
      )}


      {/* Job Listings */}
      <div className="jobs-list">
        {searching ? (
          <div className="jobs-loading">
            {[1, 2, 3].map((i) => (
              <div key={i} className="job-card skeleton" style={{ height: 180 }} />
            ))}
          </div>
        ) : jobs.length > 0 ? (
          jobs.map((job, i) => (
            <div
              key={job.id || i}
              className={`job-card animate-fade-in-up ${expandedJob === job.id ? 'expanded' : ''}`}
              style={{ animationDelay: `${i * 0.05}s` }}
            >
              <div className="job-card-header" onClick={() => setExpandedJob(expandedJob === job.id ? null : job.id)}>
                <div className="job-main-info">
                  <h3 className="job-title">{job.title}</h3>
                  <div className="job-company-line">
                    <span className="job-company">🏢 {job.company}</span>
                    <span className="job-location">📍 {job.location || 'Not specified'}</span>
                    {job.remote && <span className="badge badge-success">🏠 Remote</span>}
                  </div>
                  <div className="job-tags">
                    {job.salary_range && <span className="badge badge-success">💰 {job.salary_range}</span>}
                    {job.experience_level && <span className="badge badge-primary">{job.experience_level}</span>}
                    {job.job_type && <span className="badge badge-info">{job.job_type}</span>}
                  </div>
                </div>
                <div className="job-actions">
                  {(matchScores[job.id] || job.match_score != null) && (
                    <div className="match-indicator">
                      <svg width="56" height="56" viewBox="0 0 56 56">
                        <circle cx="28" cy="28" r="24" fill="none" stroke="var(--bg-secondary)" strokeWidth="4" />
                        <circle
                          cx="28" cy="28" r="24"
                          fill="none"
                          stroke="var(--accent-emerald)"
                          strokeWidth="4"
                          strokeDasharray={`${((matchScores[job.id]?.match_score ?? matchScores[job.id]?.overall_score ?? job.match_score ?? 0) / 100) * 150.8} 150.8`}
                          strokeLinecap="round"
                          transform="rotate(-90 28 28)"
                          style={{ transition: 'stroke-dasharray 1s ease' }}
                        />
                      </svg>
                      <span className="match-value">
                        {Math.round(matchScores[job.id]?.match_score ?? matchScores[job.id]?.overall_score ?? job.match_score ?? 0)}%
                      </span>
                    </div>
                  )}
                  <span className="expand-arrow">{expandedJob === job.id ? '▲' : '▼'}</span>
                </div>
              </div>

              {expandedJob === job.id && (
                <div className="job-card-details animate-fade-in">
                  {job.description && (
                    <div className="job-description">
                      <h4>Description</h4>
                      <p>{job.description}</p>
                    </div>
                  )}
                  {job.requirements?.length > 0 && (
                    <div className="job-requirements">
                      <h4>Requirements</h4>
                      <ul>
                        {job.requirements.map((req, j) => (
                          <li key={j}>{req}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {matchScores[job.id] && (
                    <div className="match-details">
                      <h4>Match Analysis</h4>
                      <div className="match-bars">
                        <div className="match-bar-item">
                          <span>Skills</span>
                          <div className="progress-bar"><div className="progress-bar-fill" style={{ width: `${matchScores[job.id].skill_match}%` }} /></div>
                          <span>{matchScores[job.id].skill_match}%</span>
                        </div>
                        <div className="match-bar-item">
                          <span>Experience</span>
                          <div className="progress-bar"><div className="progress-bar-fill" style={{ width: `${matchScores[job.id].experience_match}%` }} /></div>
                          <span>{matchScores[job.id].experience_match}%</span>
                        </div>
                        <div className="match-bar-item">
                          <span>Education</span>
                          <div className="progress-bar"><div className="progress-bar-fill" style={{ width: `${matchScores[job.id].education_match}%` }} /></div>
                          <span>{matchScores[job.id].education_match}%</span>
                        </div>
                      </div>
                      {matchScores[job.id].matching_skills?.length > 0 && (
                        <div className="match-skills">
                          <span className="match-skills-label">✅ Matching:</span>
                          {matchScores[job.id].matching_skills.map((s, j) => (
                            <span key={j} className="badge badge-success">{s}</span>
                          ))}
                        </div>
                      )}
                      {matchScores[job.id].missing_skills?.length > 0 && (
                        <div className="match-skills">
                          <span className="match-skills-label">⚠️ Missing:</span>
                          {matchScores[job.id].missing_skills.map((s, j) => (
                            <span key={j} className="badge badge-warning">{s}</span>
                          ))}
                        </div>
                      )}
                    </div>
                  )}

                  <div className="job-card-actions">
                    <button
                      className="btn btn-primary btn-sm"
                      onClick={() => handleMatch(job.id)}
                      disabled={matchingJob === job.id}
                    >
                      {matchingJob === job.id ? <><span className="spinner" /> Matching...</> : '🎯 Match Score'}
                    </button>
                    <button className="btn btn-secondary btn-sm" onClick={() => onNavigate('cover-letters')}>
                      ✉️ Cover Letter
                    </button>
                    {job.url && (
                      <a href={job.url} target="_blank" rel="noopener noreferrer" className="btn btn-ghost btn-sm">
                        🔗 View Original
                      </a>
                    )}
                  </div>
                </div>
              )}
            </div>
          ))
        ) : (
          <div className="empty-state">
            <div className="empty-state-icon">🔍</div>
            <h3>Search for your dream job</h3>
            <p>Enter keywords, job titles, or skills to discover AI-matched opportunities.</p>
          </div>
        )}
      </div>
    </div>
  );
}
