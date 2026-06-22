import React, { useState, useEffect, useRef } from 'react';
import { startInterview, submitAnswer, getInterviewResults, getInterviewHistory } from '../services/api.js';
import './InterviewPrep.css';

export default function InterviewPrep() {
  const [interviewType, setInterviewType] = useState('hr');
  const [difficulty, setDifficulty] = useState('medium');
  const [numQuestions, setNumQuestions] = useState(5);
  const [session, setSession] = useState(null);
  const [currentQ, setCurrentQ] = useState(0);
  const [answer, setAnswer] = useState('');
  const [messages, setMessages] = useState([]);
  const [scores, setScores] = useState([]);
  const [overallScore, setOverallScore] = useState(null);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [results, setResults] = useState(null);
  const [history, setHistory] = useState([]);
  const [finished, setFinished] = useState(false);
  const chatEndRef = useRef(null);

  useEffect(() => {
    loadHistory();
  }, []);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  async function loadHistory() {
    try {
      const data = await getInterviewHistory();
      setHistory(data.sessions || data || []);
    } catch (e) {
      console.error('History load error:', e);
    }
  }

  const avgScore = scores.length > 0
    ? (scores.reduce((a, b) => a + b, 0) / scores.length).toFixed(1)
    : 0;

  const scoreColor = (score) => {
    if (score >= 7) return 'high';
    if (score >= 4) return 'medium';
    return 'low';
  };

  const handleStart = async () => {
    setLoading(true);
    setMessages([]);
    setScores([]);
    setCurrentQ(0);
    setResults(null);
    setFinished(false);
    setOverallScore(null);
    try {
      const data = await startInterview(interviewType, numQuestions, difficulty);
      setSession(data);
      const questions = data.questions || [];
      if (questions.length > 0) {
        setMessages([
          {
            type: 'system',
            text: `🎤 ${interviewType.toUpperCase()} Interview Started — ${difficulty} difficulty, ${questions.length} questions`
          },
          {
            type: 'interviewer',
            text: questions[0].question || questions[0],
            meta: questions[0].category ? `${questions[0].category} • ${questions[0].difficulty || difficulty}` : null,
            tip: questions[0].tips
          }
        ]);
      }
    } catch (e) {
      setMessages([{ type: 'system', text: `❌ Error: ${e.message}` }]);
    }
    setLoading(false);
  };

  const handleSubmitAnswer = async () => {
    if (!answer.trim() || !session) return;
    setSubmitting(true);

    // Add candidate message
    const newMessages = [...messages, {
      type: 'candidate',
      text: answer
    }];
    setMessages(newMessages);
    const currentAnswer = answer;
    setAnswer('');

    try {
      const evaluation = await submitAnswer(session.session_id || session.id, currentQ, currentAnswer);

      const score = evaluation.score || evaluation.evaluation?.score || 5;
      setScores(prev => [...prev, score]);

      // Add score card
      newMessages.push({
        type: 'score',
        score,
        feedback: evaluation.feedback || evaluation.evaluation?.feedback || 'Good answer.',
        strengths: evaluation.strengths || evaluation.evaluation?.strengths || [],
        improvements: evaluation.improvements || evaluation.evaluation?.improvements || []
      });

      const questions = session.questions || [];
      const nextQ = currentQ + 1;

      if (nextQ < questions.length) {
        // Next question
        newMessages.push({
          type: 'interviewer',
          text: questions[nextQ].question || questions[nextQ],
          meta: questions[nextQ].category ? `${questions[nextQ].category} • ${questions[nextQ].difficulty || difficulty}` : null,
          tip: questions[nextQ].tips
        });
        setCurrentQ(nextQ);
      } else {
        // Interview complete
        setFinished(true);
        newMessages.push({
          type: 'system',
          text: '🎉 Interview Complete! Great job. Loading your results...'
        });

        try {
          const resultsData = await getInterviewResults(session.session_id || session.id);
          setResults(resultsData);
          setOverallScore(resultsData.overall_score);
        } catch {
          // Calculate from local scores
          const avg = (scores.concat(score).reduce((a, b) => a + b, 0) / (scores.length + 1));
          setOverallScore(avg);
        }
        loadHistory();
      }

      setMessages([...newMessages]);
    } catch (e) {
      newMessages.push({ type: 'system', text: `❌ Error evaluating answer: ${e.message}` });
      setMessages([...newMessages]);
    }
    setSubmitting(false);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmitAnswer();
    }
  };

  const circumference = 2 * Math.PI * 56;
  const scoreOffset = circumference - (circumference * (avgScore / 10));

  const questions = session?.questions || [];

  return (
    <div className="interview-page">
      <div className="page-header">
        <h1>🎤 Interview Preparation</h1>
        <p>Practice with AI-powered mock interviews and get instant feedback</p>
      </div>

      {/* Setup (show when no session active) */}
      {!session && (
        <>
          <div className="interview-setup">
            <div className="interview-setup-card">
              <h3>📋 Interview Type</h3>
              <div className="interview-type-btns">
                <button
                  className={`interview-type-btn ${interviewType === 'hr' ? 'active' : ''}`}
                  onClick={() => setInterviewType('hr')}
                >
                  <span className="type-icon">💼</span>
                  <span className="type-label">HR Interview</span>
                  <span className="type-desc">Behavioral & cultural fit</span>
                </button>
                <button
                  className={`interview-type-btn ${interviewType === 'technical' ? 'active' : ''}`}
                  onClick={() => setInterviewType('technical')}
                >
                  <span className="type-icon">💻</span>
                  <span className="type-label">Technical</span>
                  <span className="type-desc">Skills & problem-solving</span>
                </button>
              </div>
            </div>

            <div className="interview-setup-card">
              <h3>⚡ Difficulty</h3>
              <div className="cl-form-group">
                <select value={difficulty} onChange={e => setDifficulty(e.target.value)}>
                  <option value="easy">Easy — Entry Level</option>
                  <option value="medium">Medium — Mid Level</option>
                  <option value="hard">Hard — Senior Level</option>
                </select>
              </div>
              <div className="cl-form-group" style={{ marginTop: 'var(--space-4)' }}>
                <label style={{ fontSize: 'var(--font-sm)', color: 'var(--text-secondary)' }}>
                  Number of Questions
                </label>
                <select value={numQuestions} onChange={e => setNumQuestions(parseInt(e.target.value))}>
                  <option value={3}>3 Questions (Quick)</option>
                  <option value={5}>5 Questions (Standard)</option>
                  <option value={8}>8 Questions (Thorough)</option>
                  <option value={10}>10 Questions (Full)</option>
                </select>
              </div>
            </div>

            <div className="interview-setup-card">
              <h3>🚀 Ready?</h3>
              <p style={{ color: 'var(--text-tertiary)', fontSize: 'var(--font-sm)', marginBottom: 'var(--space-4)' }}>
                The AI interviewer will ask you questions one by one. Type your answers naturally and receive instant scoring and feedback.
              </p>
              <button
                className="interview-start-btn"
                onClick={handleStart}
                disabled={loading}
              >
                {loading ? (
                  <><span className="spinner" /> Preparing Interview...</>
                ) : (
                  <>🎤 Start Interview</>
                )}
              </button>
            </div>
          </div>

          {/* History */}
          {history.length > 0 && (
            <div className="interview-history">
              <div className="interview-history-header">
                <h3>📜 Past Interviews</h3>
              </div>
              <div className="interview-history-list">
                {history.slice(0, 5).map((item, idx) => (
                  <div key={item.id || idx} className="interview-history-item">
                    <div className="interview-history-info">
                      <h4>{item.interview_type?.toUpperCase() || 'Interview'} Session</h4>
                      <p>
                        {item.questions?.length || '?'} questions •{' '}
                        {item.created_at ? new Date(item.created_at).toLocaleDateString() : 'Recent'}
                      </p>
                    </div>
                    <div className={`interview-history-score ${scoreColor(item.overall_score || 0)}`}>
                      {item.overall_score ? `${Number(item.overall_score).toFixed(1)}/10` : '—'}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}

      {/* Active Session */}
      {session && (
        <div className="interview-session">
          <div className="interview-chat">
            <div className="interview-chat-header">
              <h3>💬 {interviewType.toUpperCase()} Interview</h3>
              <div className="interview-progress">
                <span className="interview-progress-text">
                  Q{Math.min(currentQ + 1, questions.length)}/{questions.length}
                </span>
                <div className="interview-progress-bar">
                  <div
                    className="interview-progress-fill"
                    style={{ width: `${((finished ? questions.length : currentQ) / questions.length) * 100}%` }}
                  />
                </div>
              </div>
            </div>

            <div className="interview-chat-body">
              {messages.map((msg, idx) => {
                if (msg.type === 'system') {
                  return (
                    <div key={idx} style={{
                      textAlign: 'center',
                      padding: 'var(--space-3)',
                      color: 'var(--text-tertiary)',
                      fontSize: 'var(--font-sm)',
                      fontStyle: 'italic'
                    }}>
                      {msg.text}
                    </div>
                  );
                }
                if (msg.type === 'interviewer') {
                  return (
                    <div key={idx} className="chat-bubble interviewer">
                      <div className="bubble-label">🤖 Interviewer</div>
                      <div className="bubble-text">{msg.text}</div>
                      {msg.meta && <div className="bubble-meta">{msg.meta}</div>}
                    </div>
                  );
                }
                if (msg.type === 'candidate') {
                  return (
                    <div key={idx} className="chat-bubble candidate">
                      <div className="bubble-label">👤 You</div>
                      <div className="bubble-text">{msg.text}</div>
                    </div>
                  );
                }
                if (msg.type === 'score') {
                  return (
                    <div key={idx} className="chat-score-card">
                      <div className="chat-score-header">
                        <span className={`chat-score-value ${scoreColor(msg.score)}`}>
                          {msg.score}/10
                        </span>
                        <span style={{ color: 'var(--text-tertiary)', fontSize: 'var(--font-sm)' }}>
                          Score
                        </span>
                      </div>
                      <div className="chat-score-feedback">{msg.feedback}</div>
                      {msg.strengths?.length > 0 && (
                        <div style={{ marginTop: 'var(--space-2)' }}>
                          <span style={{ fontSize: 'var(--font-xs)', color: 'var(--accent-emerald)' }}>
                            ✅ {msg.strengths.join(' • ')}
                          </span>
                        </div>
                      )}
                      {msg.improvements?.length > 0 && (
                        <div style={{ marginTop: 'var(--space-1)' }}>
                          <span style={{ fontSize: 'var(--font-xs)', color: 'var(--accent-amber)' }}>
                            💡 {msg.improvements.join(' • ')}
                          </span>
                        </div>
                      )}
                    </div>
                  );
                }
                return null;
              })}
              <div ref={chatEndRef} />
            </div>

            {!finished && (
              <div className="interview-input-area">
                <textarea
                  value={answer}
                  onChange={e => setAnswer(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Type your answer here... (Enter to submit, Shift+Enter for new line)"
                  disabled={submitting || finished}
                />
                <button
                  className="interview-submit-btn"
                  onClick={handleSubmitAnswer}
                  disabled={submitting || !answer.trim()}
                >
                  {submitting ? <span className="spinner" /> : '📤'} Submit
                </button>
              </div>
            )}

            {finished && (
              <div style={{ padding: 'var(--space-4) var(--space-6)', borderTop: '1px solid var(--glass-border)' }}>
                <button
                  className="interview-start-btn"
                  onClick={() => { setSession(null); setMessages([]); setScores([]); setFinished(false); setResults(null); }}
                >
                  🔄 Start New Interview
                </button>
              </div>
            )}
          </div>

          {/* Sidebar */}
          <div className="interview-sidebar">
            <div className="interview-score-card">
              <h4>Average Score</h4>
              <div className="score-ring">
                <svg viewBox="0 0 120 120">
                  <circle className="score-ring-bg" cx="60" cy="60" r="56" />
                  <circle
                    className="score-ring-fill"
                    cx="60" cy="60" r="56"
                    stroke={avgScore >= 7 ? 'var(--accent-emerald)' : avgScore >= 4 ? 'var(--accent-amber)' : 'var(--accent-red)'}
                    strokeDasharray={circumference}
                    strokeDashoffset={scoreOffset}
                  />
                </svg>
                <span className={`score-ring-text ${scoreColor(avgScore)}`}>
                  {avgScore > 0 ? avgScore : '—'}
                </span>
              </div>
              <p style={{ color: 'var(--text-tertiary)', fontSize: 'var(--font-sm)' }}>
                {scores.length} of {questions.length} answered
              </p>
            </div>

            <div className="interview-tips-card">
              <h4>💡 Tips</h4>
              <ul className="tips-list">
                {interviewType === 'hr' ? (
                  <>
                    <li>Use the STAR method for behavioral questions</li>
                    <li>Show enthusiasm for the company culture</li>
                    <li>Prepare specific examples from your experience</li>
                    <li>Ask thoughtful questions at the end</li>
                  </>
                ) : (
                  <>
                    <li>Think out loud — explain your reasoning</li>
                    <li>Consider edge cases and trade-offs</li>
                    <li>Start with a brute force approach, then optimize</li>
                    <li>Mention time/space complexity</li>
                  </>
                )}
              </ul>
            </div>

            {/* Individual Scores */}
            {scores.length > 0 && (
              <div className="interview-tips-card">
                <h4>📊 Question Scores</h4>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
                  {scores.map((s, i) => (
                    <div key={i} style={{
                      display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                      padding: 'var(--space-2) var(--space-3)',
                      background: 'rgba(255,255,255,0.02)',
                      borderRadius: 'var(--radius-md)'
                    }}>
                      <span style={{ fontSize: 'var(--font-sm)', color: 'var(--text-secondary)' }}>Q{i + 1}</span>
                      <span className={`chat-score-value ${scoreColor(s)}`} style={{ fontSize: 'var(--font-base)' }}>
                        {s}/10
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Overall Results */}
      {finished && results && (
        <div className="interview-results">
          <h3>🏆 Interview Results</h3>
          <div className="results-grid">
            <div className="results-section strengths">
              <h4>✅ Strengths</h4>
              <ul>
                {(results.strengths || results.recommendations?.strengths || ['Good communication']).map((s, i) => (
                  <li key={i}>{s}</li>
                ))}
              </ul>
            </div>
            <div className="results-section improvements">
              <h4>💡 Areas for Improvement</h4>
              <ul>
                {(results.weaknesses || results.recommendations?.improvements || results.improvements || ['Practice more specific examples']).map((s, i) => (
                  <li key={i}>{s}</li>
                ))}
              </ul>
            </div>
          </div>
          {results.summary && (
            <div style={{ marginTop: 'var(--space-6)', padding: 'var(--space-4)', background: 'rgba(255,255,255,0.02)', borderRadius: 'var(--radius-lg)' }}>
              <h4 style={{ fontSize: 'var(--font-sm)', color: 'var(--text-tertiary)', marginBottom: 'var(--space-2)' }}>Summary</h4>
              <p style={{ color: 'var(--text-secondary)', lineHeight: 'var(--leading-relaxed)' }}>{results.summary}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
