# AI-Powered Job Search & Interview Prep Agent

A premium, full-stack multi-agent AI system that automates the job search lifecycle. From CV parsing and intelligent job discovery to personalized cover letter generation, automated email outreach, interactive mock interviews, and strategic job tracking.

---

## 🚀 Key Features by Agent

- **💼 Agent 1: CV Analysis**: Parse CV files (PDF/DOCX), extract structured profile data (skills, experience, education, certifications), and generate career recommendations.
- **🔍 Agent 2: Job Discovery**: Fetch real-time job listings from **WeWorkRemotely RSS** and **The Muse Public API**, ranking them by relevance.
- **🎯 Agent 3: Job Matching**: Compare candidate profiles with job listings to output a 0-100 compatibility score, identify skill gaps, and suggest improvements.
- **✉️ Agent 4: Cover Letter Generator**: Generate professional, targeted cover letters and email templates tailored to specific jobs with selectable tones.
- **📧 Agent 5: Email Automation**: Send applications with attachments via SMTP, track emails, prevent duplicates, and schedule follow-up reminders.
- **🎤 Agent 6: Interview Preparation**: Practice with simulated HR or Technical interview sessions, receive real-time scoring (1-10), and get comprehensive strengths/weaknesses feedback.
- **📊 Agent 7: Application Tracking**: Manage your pipeline using an interactive Kanban board and gain strategic, AI-generated job-search insights.

---

## 🔒 Security & User System

- **Multi-User Account Isolation**: Data is separated on the database level, ensuring your CVs, applications, and logs are visible only to you.
- **Session Tokens**: Authenticates requests using SQLite-backed active UUID session tokens.
- **Secure Password Hashing**: Leverages PBKDF2-SHA256 with unique cryptographic salts to secure accounts.
- **Interactive UI**: Sleek, glassmorphism-themed Login and Register screens.

---

## 🛠️ Technology Stack

- **Frontend**: React 18, Vite 6, Custom HSL Styling (Soft UI, Bento layout).
- **Backend**: FastAPI, Async SQLAlchemy, Pydantic, Python-Multipart.
- **Database / Vector Store**: SQLite (relational records), ChromaDB (vector embeddings for semantics).
- **LLM & Orchestration**: Groq API (`llama-3.1-8b-instant`), LangChain, CrewAI orchestration.

---

## ⚙️ Setup & Installation

### Prerequisites
- Python 3.11+
- Node.js 18+
- Groq API Key

### 1. Backend Setup
1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   # Windows:
   .\venv\Scripts\activate
   # macOS/Linux:
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   pip install email-validator
   ```
4. Create your `.env` file from the template:
   ```bash
   copy .env.example .env
   ```
5. Configure your environment variables in `.env` (add your `GROQ_API_KEY`, and optional SMTP credentials for real email sending).

### 2. Frontend Setup
1. Navigate to the frontend directory:
   ```bash
   cd ../frontend
   ```
2. Install node dependencies:
   ```bash
   npm install
   ```

---

## 🚀 Running the Application

### Start Backend Server
From the `backend` folder with your virtual environment active:
```bash
python -m uvicorn main:app --reload --port 8000
```
*API docs will be available at: http://localhost:8000/docs*

### Start Frontend Server
From the `frontend` folder:
```bash
npm run dev
```
*Frontend interface will be available at: http://localhost:5173*

---

## 🧪 Verification & Testing

You can verify the backend authentication and job discovery endpoints using programmatic scripts located in `scratch/`:
- **Auth Flow & Data Isolation**: `.\venv\Scripts\python "backend/scratch/test_auth_flow.py"`
- **Scraper Connectivity (The Muse / WWR)**: `.\venv\Scripts\python "backend/scratch/test_muse_scraper.py"`
