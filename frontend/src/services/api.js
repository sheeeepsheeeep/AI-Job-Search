/* ═══════════════════════════════════════════════════════════════════════════════
   API Service — All endpoint functions for the AI Job Search Agent
   ═══════════════════════════════════════════════════════════════════════════════ */

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

class ApiError extends Error {
  constructor(message, status, data) {
    super(message);
    this.status = status;
    this.data = data;
    this.name = 'ApiError';
  }
}

async function request(endpoint, options = {}) {
  const url = `${BASE_URL}${endpoint}`;
  
  const token = localStorage.getItem('token');
  const authHeaders = token ? { 'Authorization': `Bearer ${token}` } : {};

  const config = {
    headers: {
      'Content-Type': 'application/json',
      ...authHeaders,
      ...options.headers,
    },
    ...options,
  };

  // Remove Content-Type for FormData (file uploads)
  if (options.body instanceof FormData) {
    delete config.headers['Content-Type'];
  }

  try {
    const response = await fetch(url, config);

    if (!response.ok) {
      let errorData;
      try {
        errorData = await response.json();
      } catch {
        errorData = { detail: response.statusText };
      }
      
      let message = `HTTP ${response.status}`;
      if (typeof errorData.detail === 'string') {
        message = errorData.detail;
      } else if (Array.isArray(errorData.detail)) {
        message = errorData.detail
          .map(err => {
            const field = err.loc ? err.loc.filter(loc => loc !== 'body').join('.') : '';
            return `${field ? field + ': ' : ''}${err.msg}`;
          })
          .join(', ');
      } else if (errorData.message) {
        message = errorData.message;
      }

      throw new ApiError(
        message,
        response.status,
        errorData
      );
    }

    // Handle file downloads
    const contentType = response.headers.get('content-type');
    if (contentType && contentType.includes('application/pdf')) {
      return response.blob();
    }

    return response.json();
  } catch (error) {
    if (error instanceof ApiError) throw error;
    throw new ApiError(
      error.message || 'Network error. Please check your connection.',
      0,
      null
    );
  }
}

// ── CV & Profile ──────────────────────────────────────────────────────────────

export async function uploadCV(file) {
  const formData = new FormData();
  formData.append('file', file);
  return request('/cv/upload', {
    method: 'POST',
    body: formData,
  });
}

export async function getProfile() {
  return request('/cv/profile');
}

export async function getProfileById(id) {
  return request(`/cv/profile/${id}`);
}

export async function getRecommendations(profileId) {
  return request(`/cv/recommendations/${profileId}`);
}

// ── Job Search & Matching ─────────────────────────────────────────────────────

export async function searchJobs(query, location, filters = {}) {
  return request('/jobs/search', {
    method: 'POST',
    body: JSON.stringify({ query, location, filters }),
  });
}

export async function getJobs(params = {}) {
  const query = new URLSearchParams();
  if (params.location) query.append('location', params.location);
  if (params.remote !== undefined) query.append('remote', params.remote);
  if (params.experience_level) query.append('experience_level', params.experience_level);
  if (params.job_type) query.append('job_type', params.job_type);
  if (params.limit) query.append('limit', params.limit);
  if (params.offset) query.append('offset', params.offset);
  const qs = query.toString();
  return request(`/jobs/${qs ? `?${qs}` : ''}`);
}

export async function getJob(id) {
  return request(`/jobs/${id}`);
}

export async function matchJob(jobId, profileId) {
  const query = profileId ? `?profile_id=${profileId}` : '';
  return request(`/jobs/${jobId}/match${query}`, { method: 'POST' });
}

// ── Cover Letters ─────────────────────────────────────────────────────────────

export async function generateCoverLetter(jobId, profileId, tone = 'professional', focusAreas, additionalNotes) {
  return request('/cover-letters/generate', {
    method: 'POST',
    body: JSON.stringify({
      job_id: jobId,
      profile_id: profileId,
      tone,
      focus_areas: focusAreas,
      additional_notes: additionalNotes,
    }),
  });
}

export async function getCoverLetter(id) {
  return request(`/cover-letters/${id}`);
}

export async function downloadCoverLetterPdf(id) {
  return request(`/cover-letters/${id}/pdf`);
}

// ── Applications ──────────────────────────────────────────────────────────────

export async function getApplications(statusFilter) {
  const query = statusFilter ? `?status=${statusFilter}` : '';
  return request(`/applications/${query}`);
}

export async function createApplication(jobId, profileId, notes) {
  return request('/applications/', {
    method: 'POST',
    body: JSON.stringify({
      job_id: jobId,
      profile_id: profileId,
      notes,
    }),
  });
}

export async function updateApplicationStatus(id, newStatus, notes) {
  return request(`/applications/${id}/status`, {
    method: 'PUT',
    body: JSON.stringify({ status: newStatus, notes }),
  });
}

export async function getStats() {
  return request('/applications/stats');
}

export async function getInsights() {
  return request('/applications/insights');
}

// ── Emails ────────────────────────────────────────────────────────────────────

export async function sendEmail(applicationId, recipientEmail, subject, body, emailType = 'application') {
  return request('/emails/send', {
    method: 'POST',
    body: JSON.stringify({
      application_id: applicationId,
      recipient_email: recipientEmail,
      subject,
      body,
      email_type: emailType,
    }),
  });
}

export async function getEmailHistory(applicationId) {
  const query = applicationId ? `?application_id=${applicationId}` : '';
  return request(`/emails/history${query}`);
}

export async function sendFollowUp(applicationId) {
  return request(`/emails/follow-up/${applicationId}`, { method: 'POST' });
}

// ── Interviews ────────────────────────────────────────────────────────────────

export async function startInterview(interviewType = 'hr', numQuestions = 5, difficulty = 'medium', jobId, profileId) {
  return request('/interviews/start', {
    method: 'POST',
    body: JSON.stringify({
      job_id: jobId,
      profile_id: profileId,
      interview_type: interviewType,
      num_questions: numQuestions,
      difficulty,
    }),
  });
}

export async function submitAnswer(sessionId, questionIndex, answer) {
  return request(`/interviews/${sessionId}/answer`, {
    method: 'POST',
    body: JSON.stringify({
      question_index: questionIndex,
      answer,
    }),
  });
}

export async function getInterviewResults(sessionId) {
  return request(`/interviews/${sessionId}/results`);
}

export async function getInterviewHistory() {
  return request('/interviews/history');
}

// ── Authentication ────────────────────────────────────────────────────────────

export async function login(email, password) {
  const result = await request('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
  if (result && result.access_token) {
    localStorage.setItem('token', result.access_token);
  }
  return result;
}

export async function register(email, password) {
  return request('/auth/register', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
}

export async function logout() {
  try {
    await request('/auth/logout', { method: 'POST' });
  } catch (e) {
    console.error('Logout request failed:', e);
  } finally {
    localStorage.removeItem('token');
  }
}

export async function getCurrentUser() {
  return request('/auth/me');
}
