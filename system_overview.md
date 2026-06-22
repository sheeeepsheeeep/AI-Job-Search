# AI Job Search & Interview Preparation Agent — System Overview

This document provides a detailed technical breakdown of the architecture, data models, components, services, and workflows of the AI Job Search & Interview Prep Agent system.

---

## 🏗️ System Architecture

The application is built on a modern **three-tier architecture** designed to be lightweight, modular, and fast.

```
┌────────────────────────────────────────────────────────────────────────┐
│                        React Frontend (Vite)                           │
│  • CSS Design Tokens  • Single Page Routing  • Glassmorphism Bento UI  │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │ HTTP (REST JSON)
┌──────────────────────────────────▼─────────────────────────────────────┐
│                        FastAPI Backend                                 │
│  • Pydantic Schemas    • Endpoint Routers   • CORS Middleware          │
├────────────────────────────────────────────────────────────────────────┤
│                        AI Agents Layer (Groq)                          │
│  • CV Analysis Agent   • Job Discovery Agent  • Job Matching Agent     │
│  • Cover Letter Agent  • Email Automation     • Interview Prep Agent   │
│  • Application Tracking Agent (CrewAI / fallback pipeline)            │
├────────────────────────────────────────────────────────────────────────┤
│                        Services Layer                                  │
│  • CV Text Extraction  • BeautifulSoup/RSS   • ChromaDB Vector Store   │
│  • SMTP Email Service  • ReportLab PDF Generator                       │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │ SQLite & Filesystem
┌──────────────────────────────────▼─────────────────────────────────────┐
│                        Data Storage Layer                              │
│  • SQLite (database/job_search.db via Async SQLAlchemy)                │
│  • Vector Embeddings Database (backend/chroma_db)                      │
│  • Uploaded CV Files Store (backend/uploads)                           │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 📂 Core Directories & Inventory

### 1. Backend (`/backend`)
*   `config.py`: Loads environment configurations (Groq key, SMTP, directories) using Pydantic Settings.
*   `main.py`: Entry point configuring CORS, initializing the databases, and registering api routers.
*   `requirements.txt`: Defines all python packages (`fastapi`, `sqlalchemy`, `langchain-groq`, `chromadb`, etc.).
*   `database/`
    *   `database.py`: Establishes async engine, session factory, database dependencies, and table creation hooks.
    *   `models.py`: Defines the database tables and SQLAlchemy relationships.
*   `services/`
    *   `cv_parser.py`: Extracts text contents from `.pdf`, `.docx`, and `.txt` files.
    *   `vector_store.py`: Wraps ChromaDB collection methods for adding and querying semantic content.
    *   `web_scraper.py`: Extracts remote listings from WeWorkRemotely RSS feed with fallback to a simulated jobs database.
    *   `pdf_generator.py`: Formats and writes PDF files for generated cover letters using ReportLab.
    *   `email_service.py`: Handles async SMTP email composition and attachments.
*   `agents/`
    *   Contains the definitions for the 7 independent AI Agent classes communicating with the Groq API (`llama-3.1-8b-instant`).
    *   `crew.py`: Integrates agents into a structured multi-agent CrewAI pipeline (with a fallback orchestrator).
*   `routers/`
    *   FastAPI endpoints handling candidate profile uploads, job searches, match scores, cover letters, SMTP operations, and mock interview state machines.

### 2. Frontend (`/frontend`)
*   `src/index.css`: Defines the global design system (variables for glassmorphism, HSL color blocking, radii, micro-animations, and scrollbars).
*   `src/App.jsx` & `App.css`: Controls sidebar grid layout and page navigation.
*   `src/services/api.js`: Communicates with FastAPI endpoints via async `fetch` queries.
*   `src/components/`:
    *   Dashboard, CV Upload, Job Search, Job Matching, Cover Letter Generator, Email Manager, Interview Prep, Sidebar, and Kanban Application Tracker.

---

## 🗄️ Database Schema & Models

The SQLite database (`job_search.db`) contains 6 tables mapped via Async SQLAlchemy:

### 1. `CandidateProfile`
Stores parsed candidate information:
*   `id` (Integer, Primary Key)
*   `name` (String, default "Unknown")
*   `email` (String, Nullable)
*   `phone` (String, Nullable)
*   `skills` (JSON array of strings)
*   `education` (JSON array of dicts: degree, institution, year, GPA)
*   `certifications` (JSON array of strings)
*   `experience` (JSON array of dicts: title, company, dates, description)
*   `experience_years` (Integer)
*   `summary` (Text, summary of qualifications)
*   `cv_file_path` (String, absolute local path to uploaded document)

### 2. `JobListing`
Stores crawled or simulated job details:
*   `id` (Integer, Primary Key)
*   `title` (String, name of role)
*   `company` (String, name of company)
*   `location` (String)
*   `salary_range` (String, salary details)
*   `description` (Text)
*   `requirements` (JSON array of skill requirements)
*   `url` (String, original portal link)
*   `source` (String, e.g. "WeWorkRemotely", "Simulated")
*   `remote_status` (String, "remote" / "hybrid" / "onsite")
*   `experience_level` (String)
*   `date_found` (DateTime, timestamp)

### 3. `JobMatch`
Saves calculations comparing a candidate to a specific job listing:
*   `id` (Integer, Primary Key)
*   `candidate_id` (Integer, Foreign Key)
*   `job_id` (Integer, Foreign Key)
*   `match_score` (Float, compatibility 0-100)
*   `matching_skills` (JSON array of strings)
*   `missing_skills` (JSON array of strings)
*   `recommendations` (JSON array of upskilling recommendations)

### 4. `CoverLetter`
Stores AI-generated application letters:
*   `id` (Integer, Primary Key)
*   `candidate_id` (Integer, Foreign Key)
*   `job_id` (Integer, Foreign Key)
*   `content` (Text, main body text)
*   `email_template` (Text, formatted email introduction)
*   `pdf_path` (String, path to generated ReportLab PDF)

### 5. `Application`
Tracks application pipelines:
*   `id` (Integer, Primary Key)
*   `candidate_id` (Integer, Foreign Key)
*   `job_id` (Integer, Foreign Key)
*   `cover_letter_id` (Integer, Foreign Key, Nullable)
*   `company_name` (String)
*   `job_title` (String)
*   `email_address` (String, contact email for application)
*   `status` (String, default "Applied" - columns: Applied, Under Review, Interview Scheduled, Rejected, Offer Received)
*   `notes` (Text)
*   `follow_up_date` (DateTime, Nullable)

### 6. `EmailLog`
Logs SMTP emails dispatched through the system:
*   `id` (Integer, Primary Key)
*   `application_id` (Integer, Foreign Key, Nullable)
*   `email_type` (String, e.g., "application" or "follow_up")
*   `recipient` (String)
*   `subject` (String)
*   `body` (Text)
*   `status` (String, e.g. "sent", "failed", "pending")
*   `sent_at` (DateTime, Nullable)

### 7. `InterviewSession` & `InterviewAnswer`
Maintains conversational state and question-by-question scoring for mock interviews.

---

## 🎨 UI Components (Frontend)

All components follow a **Bento Box** layout with Soft UI gradients, glassmorphism containers, custom typography (Inter font), and responsive grid scaling.

### 1. `CVUpload` (`CVUpload.jsx` & `CVUpload.css`)
*   **Purpose**: CV ingestion and analysis overview.
*   **Behavior**:
    *   Features a drag-and-drop container accepting PDF, DOCX, and TXT files.
    *   On component mount, it triggers a `getProfile` query. If a parsed profile already exists in SQLite, it loads it instantly so details aren't lost when refreshing the tab or restarting the server.
    *   Provides an "Upload New CV" button to clear current profile state and let you drag-and-drop a new resume.
    *   Displays name, contact metadata, formatted timeline, skills tags, and career recommendations with upskilling recommendations.

### 2. `JobSearch` (`JobSearch.jsx` & `JobSearch.css`)
*   **Purpose**: Job listing discovery and filters.
*   **Behavior**:
    *   Auto-loads candidate CV details on mount, prefilling search keyword fields with their latest job title or skill, and sets Location defaults to `Malaysia`.
    *   Allows text queries, location queries, and filtering pills (Remote/Onsite, Experience Levels, Job Type).
    *   Pulls job listings matching search criteria, showing title, company, location, tags, and match score indicators. Clicking expanded cards reveals job descriptions, requirements list, and quick actions ("Match Score", "Cover Letter").

### 3. `JobMatching` (`JobMatching.jsx` & `JobMatching.css`)
*   **Purpose**: Granular skill gaps analysis.
*   **Behavior**:
    *   Displays an animated circular compatibility score gauge.
    *   Renders a side-by-side comparative table of skills (in green badges) versus missing requirements (in red/orange badges).
    *   Lists key development tips to bridge qualifications gaps.

### 4. `CoverLetterGen` (`CoverLetterGen.jsx` & `CoverLetterGen.css`)
*   **Purpose**: Personalization and PDF generation.
*   **Behavior**:
    *   Lets the user select an active job profile and choose writing parameters:
        *   **Tone**: Professional, Enthusiastic, Creative, Bold.
        *   **Focus Areas**: Mention projects, highlight leadership, keep it brief.
        *   **Additional Notes**: Custom texts to append to the generation prompt.
    *   Generates a letter content layout, featuring a quick clipboard copy, email subject formatting, and a direct download trigger for the professional ReportLab-formatted PDF file.

### 5. `EmailManager` (`EmailManager.jsx` & `EmailManager.css`)
*   **Purpose**: Outbox control and email dispatching.
*   **Behavior**:
    *   Features a compose interface pre-filled with the candidate's CV and the generated cover letter.
    *   Performs database checks before sending to prevent duplicate applications.
    *   Dispatches the email asynchronously via SMTP.
    *   Lists historical outbox logs with status badges (Sent, Delivered, Failed) and allows sending follow-ups.

### 6. `InterviewPrep` (`InterviewPrep.jsx` & `InterviewPrep.css`)
*   **Purpose**: Dynamic interactive interview training.
*   **Behavior**:
    *   Prompts the user to pick an interview focus (HR Behavior or technical domain expertise), difficulty (easy, medium, hard), and quantity of questions.
    *   Renders a chat interface simulating an interviewer asking questions sequentially.
    *   Evaluates answers in real-time, providing feedback, ideal structures, and scores.
    *   Completes the loop by displaying an overall scorecard summary of strengths, weaknesses, and key tips.

### 7. `ApplicationTracker` (`ApplicationTracker.jsx` & `ApplicationTracker.css`)
*   **Purpose**: Pipelines visual tracking.
*   **Behavior**:
    *   Renders a 5-column Kanban board (Applied, Under Review, Interview Scheduled, Rejected, Offer Received) populated with cards representing active applications.
    *   Includes a pipeline distribution chart.
    *   Queries the `ApplicationTrackingAgent` to generate high-level strategical suggestions (e.g. "You have 3 applications in Interview status. Make sure to schedule mock sessions!").

---

## 🛠️ Backend Services & Utilities

### 1. CV Text Extraction (`services/cv_parser.py`)
Parses uploaded binary files using target libraries:
*   **PDFs**: Uses `PyPDF2.PdfReader` to extract textual components.
*   **DOCX**: Uses `docx.Document` to iterate over document paragraphs.
*   **TXT**: Decodes raw text content.

### 2. Job Search Web Scraper (`services/web_scraper.py`)
Queries remote RSS data feeds or uses a local fallback database:
*   Calls WeWorkRemotely category RSS feeds and uses `BeautifulSoup` to parse raw HTML descriptions.
*   Applies helper regex queries to filter by title, company, location, and metadata fields.
*   Maintains a list of simulated jobs for offline/local testing.

### 3. PDF Generator (`services/pdf_generator.py`)
Draws highly structured documents using **ReportLab Flowables**:
*   Uses `SimpleDocTemplate` to compile paragraphs, spaces, and margins.
*   Injects headers containing candidate names, contact details, date, and company addresses.
*   Saves the resulting PDF in a structured backend storage folder.

### 4. Email Service (`services/email_service.py`)
Provides async email transport handlers:
*   Initializes SMTP connections over SSL (port 465) or TLS (port 587).
*   Formats multi-part MIME messages.
*   Safely appends file attachments (e.g., CV files and ReportLab PDF cover letters).
*   Operates in `DRY_RUN` mode (which logs email outputs rather than sending them) when SMTP keys are unconfigured.

---

## 🤖 AI Agents & Reasoning Loops (Groq API)

The system deploys 7 specialized AI agents using the **Groq API** (`llama-3.1-8b-instant`) for natural language tasks.

### 1. `CVAnalysisAgent`
*   **Job**: CV Parsing.
*   **Prompting**: Instructs the LLM to output a clean, validated JSON structure matching database profile schemas, separating contact information, structured education lists, experience details, and skill tags. Also generates customized career path recommendations.

### 2. `JobDiscoveryAgent`
*   **Job**: Search result enhancement and relevance ranking.
*   **Prompting**: Evaluates search results, enhances summary notes, and ranks matching opportunities based on their proximity to the candidate's career level and skills.

### 3. `JobMatchingAgent`
*   **Job**: Competency alignment check.
*   **Prompting**: Conducts side-by-side assessments, outputting a precise compatibility rating, matching/missing keywords, and actionable tips to fix skill gaps.

### 4. `CoverLetterAgent`
*   **Job**: Application letter composition.
*   **Prompting**: Formulates professional cover letters and complementary emails. Fully parameterized to adapt to user-selected writing styles (e.g., Bold, Professional), project callouts, and notes.

### 5. `EmailAutomationAgent`
*   **Job**: Correspondence tracking.
*   **Prompting**: Inspects email content, flags potential duplicate applications, and scans database records to remind candidates of pending follow-up deadlines.

### 6. `InterviewPrepAgent`
*   **Job**: Interactive interview loop.
*   **Prompting**: Generates technical coding/system design challenges or HR situational questions based on the candidate's CV. Scores replies on a 1-10 scale and gives comprehensive feedback.

### 7. `ApplicationTrackingAgent`
*   **Job**: Strategic pipeline advising.
*   **Prompting**: Analyzes dashboard metrics and Kanban states to offer feedback on progress (e.g., identifying gaps in application volume or high failure rates in review stages).

---

## 🔄 Core User Workflows

```
┌─────────────────┐      ┌────────────────────────┐      ┌────────────────────────┐
│ 1. Upload CV   │ ────> │ 2. Extract Profile     │ ────> │ 3. View Dashboard      │
│  (pdf/docx)     │      │  (Agent 1 parses JSON) │      │  (Career suggestions)  │
└─────────────────┘      └────────────────────────┘      └───────────┬────────────┘
                                                                     │
┌─────────────────┐      ┌────────────────────────┐      ┌───────────▼────────────┐
│ 6. Apply & Track│ <────│ 5. Gen Cover Letter    │ <────│ 4. Search Jobs         │
│  (Kanban/SMTP)  │      │  (Agent 4 builds PDF)  │      │  (Agent 2 pre-fills)   │
└────────┬────────┘      └────────────────────────┘      └────────────────────────┘
         │
┌────────▼────────┐
│ 7. Mock Interview│
│  (Agent 6 loop) │
└─────────────────┘
```

1.  **Ingestion & Parsing**:
    The user uploads their CV file. The file is saved in the `/uploads` directory. The backend extracts raw text content and sends it to the `CVAnalysisAgent`, which returns a structured JSON payload containing skills, education, and experience.
2.  **Dashboard Load**:
    The structured profile is written to the SQLite database. The user views their dashboard, which shows career suggestions, active pipelines, and key stats.
3.  **Job Search**:
    When the user navigates to the Job Search tab, the page pre-fills search fields using the profile details from SQLite. Results matching the query are returned.
4.  **Matching & Letter Generation**:
    Selecting a job triggers the `JobMatchingAgent` to show skill gaps. If details look correct, the user clicks "Cover Letter" to generate a personalized application letter in the selected tone (e.g. bold, professional).
5.  **Sending & Tracking**:
    The user creates an application, generating a PDF copy of the letter using ReportLab. The `EmailAutomationAgent` checks for duplicate entries and dispatches the email via SMTP. The application is added to the Kanban board, where its status can be tracked and updated.
6.  **Interview Simulator**:
    Before the interview, the candidate starts a mock interview session. The `InterviewPrepAgent` generates role-specific questions. The candidate answers each question, receiving immediate scores and improvements, ending in a final performance report card.
