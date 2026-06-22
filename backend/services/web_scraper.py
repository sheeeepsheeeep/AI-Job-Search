"""
Job scraping service.

Provides a SIMULATED job database for development / demo and a real scraper
skeleton (disabled by default) that can be swapped in when needed.
"""

import logging
import re
from datetime import datetime, timedelta
from typing import Any

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Simulated job database (~15 realistic listings)
# ---------------------------------------------------------------------------

SIMULATED_JOBS: list[dict[str, Any]] = [
    {
        "title": "Senior Software Engineer",
        "company": "Google",
        "location": "Mountain View, CA",
        "salary_range": "$160,000 - $220,000",
        "description": (
            "Design and build scalable distributed systems powering Google Cloud. "
            "Collaborate with cross-functional teams to define and ship new features. "
            "Mentor junior engineers and conduct code reviews. "
            "Optimize performance and reliability of backend services."
        ),
        "requirements": [
            "5+ years of experience in software engineering",
            "Proficiency in Python, Java, or Go",
            "Experience with distributed systems and microservices",
            "Strong understanding of data structures and algorithms",
            "BS/MS in Computer Science or equivalent",
        ],
        "url": "https://careers.google.com/jobs/senior-swe-12345",
        "source": "Google Careers",
        "remote_status": "hybrid",
        "industry": "Technology",
        "experience_level": "Senior",
    },
    {
        "title": "Data Scientist",
        "company": "Meta",
        "location": "Menlo Park, CA",
        "salary_range": "$140,000 - $200,000",
        "description": (
            "Analyze large-scale datasets to drive product decisions. "
            "Build and deploy machine learning models for user behaviour prediction. "
            "Design A/B tests and interpret results. "
            "Present findings to stakeholders and leadership."
        ),
        "requirements": [
            "3+ years of experience in data science or machine learning",
            "Proficiency in Python, SQL, and statistical modelling",
            "Experience with TensorFlow, PyTorch, or scikit-learn",
            "Strong communication and data visualization skills",
            "MS/PhD in Statistics, CS, or related field preferred",
        ],
        "url": "https://www.metacareers.com/jobs/data-scientist-67890",
        "source": "Meta Careers",
        "remote_status": "hybrid",
        "industry": "Technology",
        "experience_level": "Mid-Senior",
    },
    {
        "title": "Product Manager",
        "company": "Amazon",
        "location": "Seattle, WA",
        "salary_range": "$130,000 - $185,000",
        "description": (
            "Own the product roadmap for a key AWS service. "
            "Gather and prioritize customer requirements. "
            "Work with engineering teams to deliver features on time. "
            "Analyse market trends and competitive landscape."
        ),
        "requirements": [
            "4+ years of product management experience",
            "Experience with cloud computing or SaaS products",
            "Strong analytical and problem-solving skills",
            "Excellent written and verbal communication",
            "MBA or technical degree preferred",
        ],
        "url": "https://amazon.jobs/product-manager-11111",
        "source": "Amazon Jobs",
        "remote_status": "onsite",
        "industry": "Technology / Cloud",
        "experience_level": "Mid-Senior",
    },
    {
        "title": "DevOps Engineer",
        "company": "Netflix",
        "location": "Los Gatos, CA",
        "salary_range": "$150,000 - $210,000",
        "description": (
            "Build and maintain CI/CD pipelines for streaming infrastructure. "
            "Automate cloud deployments on AWS. "
            "Monitor system health and respond to incidents. "
            "Implement infrastructure-as-code using Terraform and Kubernetes."
        ),
        "requirements": [
            "3+ years of DevOps or SRE experience",
            "Strong knowledge of AWS services",
            "Experience with Docker, Kubernetes, and Terraform",
            "Scripting skills in Python or Bash",
            "Understanding of networking and security best practices",
        ],
        "url": "https://jobs.netflix.com/devops-22222",
        "source": "Netflix Jobs",
        "remote_status": "remote",
        "industry": "Entertainment / Technology",
        "experience_level": "Mid-Senior",
    },
    {
        "title": "Frontend Developer",
        "company": "Shopify",
        "location": "Toronto, Canada",
        "salary_range": "$100,000 - $150,000",
        "description": (
            "Build responsive, accessible e-commerce UI components using React. "
            "Collaborate with designers to translate Figma mockups into code. "
            "Optimize web performance and Core Web Vitals. "
            "Write unit and integration tests."
        ),
        "requirements": [
            "2+ years of frontend development experience",
            "Proficiency in React, TypeScript, and modern CSS",
            "Experience with GraphQL or REST APIs",
            "Knowledge of accessibility standards (WCAG)",
            "Familiarity with testing frameworks (Jest, Cypress)",
        ],
        "url": "https://shopify.com/careers/frontend-33333",
        "source": "Shopify Careers",
        "remote_status": "remote",
        "industry": "E-Commerce / Technology",
        "experience_level": "Mid",
    },
    {
        "title": "Machine Learning Engineer",
        "company": "OpenAI",
        "location": "San Francisco, CA",
        "salary_range": "$200,000 - $350,000",
        "description": (
            "Research and develop state-of-the-art large language models. "
            "Build training and evaluation pipelines at scale. "
            "Optimize model inference for production workloads. "
            "Contribute to safety and alignment research."
        ),
        "requirements": [
            "5+ years ML/AI experience",
            "Deep understanding of transformer architectures",
            "Proficiency in Python, PyTorch, and CUDA",
            "Experience training models on large GPU clusters",
            "Publications in top ML venues preferred",
        ],
        "url": "https://openai.com/careers/ml-engineer-44444",
        "source": "OpenAI Careers",
        "remote_status": "onsite",
        "industry": "Artificial Intelligence",
        "experience_level": "Senior",
    },
    {
        "title": "Full Stack Developer",
        "company": "Stripe",
        "location": "San Francisco, CA",
        "salary_range": "$140,000 - $190,000",
        "description": (
            "Develop payment processing features end-to-end. "
            "Build APIs consumed by millions of developers. "
            "Work on both React frontend and Ruby/Python backend. "
            "Ensure PCI-DSS compliance across services."
        ),
        "requirements": [
            "3+ years of full-stack development",
            "Experience with React and Node.js or Python",
            "Knowledge of payment systems or financial APIs",
            "Strong database design skills (PostgreSQL)",
            "Experience with security best practices",
        ],
        "url": "https://stripe.com/jobs/fullstack-55555",
        "source": "Stripe Jobs",
        "remote_status": "hybrid",
        "industry": "FinTech",
        "experience_level": "Mid",
    },
    {
        "title": "Cloud Architect",
        "company": "Microsoft",
        "location": "Redmond, WA",
        "salary_range": "$170,000 - $240,000",
        "description": (
            "Design enterprise-scale Azure solutions for Fortune 500 clients. "
            "Lead technical workshops and architecture reviews. "
            "Develop reference architectures and best-practice guides. "
            "Drive cloud adoption strategy."
        ),
        "requirements": [
            "7+ years of experience in cloud architecture",
            "Azure certifications (Solutions Architect Expert preferred)",
            "Experience with hybrid cloud and multi-cloud environments",
            "Strong knowledge of networking, security, and identity",
            "Excellent presentation and stakeholder management skills",
        ],
        "url": "https://careers.microsoft.com/cloud-architect-66666",
        "source": "Microsoft Careers",
        "remote_status": "hybrid",
        "industry": "Technology / Cloud",
        "experience_level": "Senior",
    },
    {
        "title": "Backend Engineer (Python)",
        "company": "Spotify",
        "location": "Stockholm, Sweden",
        "salary_range": "$120,000 - $170,000",
        "description": (
            "Build microservices powering Spotify's recommendation engine. "
            "Design event-driven systems with Kafka and gRPC. "
            "Collaborate with data and ML teams. "
            "Participate in on-call rotations."
        ),
        "requirements": [
            "3+ years of backend development in Python",
            "Experience with FastAPI, Flask, or Django",
            "Knowledge of message queues (Kafka, RabbitMQ)",
            "Familiarity with PostgreSQL and Redis",
            "Experience with containerised deployments",
        ],
        "url": "https://lifeatspotify.com/backend-77777",
        "source": "Spotify Careers",
        "remote_status": "hybrid",
        "industry": "Music / Technology",
        "experience_level": "Mid",
    },
    {
        "title": "Cybersecurity Analyst",
        "company": "CrowdStrike",
        "location": "Austin, TX",
        "salary_range": "$110,000 - $155,000",
        "description": (
            "Monitor and analyse security events across enterprise environments. "
            "Conduct threat hunting and incident response. "
            "Develop detection rules and playbooks. "
            "Collaborate with engineering to harden systems."
        ),
        "requirements": [
            "3+ years of cybersecurity experience",
            "Knowledge of SIEM tools (Splunk, Elastic)",
            "Familiarity with MITRE ATT&CK framework",
            "Experience with endpoint detection and response (EDR)",
            "Security certifications (CISSP, CEH, or equivalent)",
        ],
        "url": "https://crowdstrike.com/careers/analyst-88888",
        "source": "CrowdStrike Careers",
        "remote_status": "remote",
        "industry": "Cybersecurity",
        "experience_level": "Mid",
    },
    {
        "title": "UX/UI Designer",
        "company": "Figma",
        "location": "San Francisco, CA",
        "salary_range": "$130,000 - $175,000",
        "description": (
            "Design intuitive user experiences for collaborative design tools. "
            "Conduct user research and usability testing. "
            "Create high-fidelity prototypes and design systems. "
            "Partner closely with product and engineering."
        ),
        "requirements": [
            "3+ years of UX/UI design experience",
            "Proficiency in Figma (naturally!)",
            "Strong portfolio demonstrating end-to-end design process",
            "Experience with design systems and component libraries",
            "Knowledge of accessibility and inclusive design",
        ],
        "url": "https://figma.com/careers/ux-designer-99999",
        "source": "Figma Careers",
        "remote_status": "hybrid",
        "industry": "Design / Technology",
        "experience_level": "Mid",
    },
    {
        "title": "Junior Software Developer",
        "company": "Accenture",
        "location": "New York, NY",
        "salary_range": "$70,000 - $95,000",
        "description": (
            "Join a consulting team building enterprise applications. "
            "Develop features in Java, Python, or .NET. "
            "Participate in Agile sprints and daily stand-ups. "
            "Learn from senior engineers through mentorship."
        ),
        "requirements": [
            "0-2 years of software development experience",
            "BS in Computer Science or related field",
            "Knowledge of at least one programming language",
            "Understanding of SQL and relational databases",
            "Strong willingness to learn and adapt",
        ],
        "url": "https://accenture.com/careers/junior-dev-10101",
        "source": "Accenture Careers",
        "remote_status": "hybrid",
        "industry": "Consulting / Technology",
        "experience_level": "Entry",
    },
    {
        "title": "Data Engineer",
        "company": "Airbnb",
        "location": "San Francisco, CA",
        "salary_range": "$145,000 - $200,000",
        "description": (
            "Build and maintain data pipelines processing billions of events daily. "
            "Design data warehouse schemas and ETL workflows. "
            "Ensure data quality and governance across the platform. "
            "Partner with analytics and ML teams."
        ),
        "requirements": [
            "4+ years of data engineering experience",
            "Proficiency in Python and SQL",
            "Experience with Spark, Airflow, or dbt",
            "Knowledge of cloud data warehouses (BigQuery, Snowflake, Redshift)",
            "Understanding of data modelling best practices",
        ],
        "url": "https://airbnb.com/careers/data-engineer-12121",
        "source": "Airbnb Careers",
        "remote_status": "hybrid",
        "industry": "Travel / Technology",
        "experience_level": "Mid-Senior",
    },
    {
        "title": "iOS Developer",
        "company": "Apple",
        "location": "Cupertino, CA",
        "salary_range": "$155,000 - $220,000",
        "description": (
            "Develop features for flagship iOS applications. "
            "Write clean, testable Swift code following MVVM architecture. "
            "Collaborate with design and QA teams. "
            "Optimize app performance and battery usage."
        ),
        "requirements": [
            "4+ years of iOS development experience",
            "Expert-level Swift and UIKit/SwiftUI knowledge",
            "Experience with Core Data, Combine, and async/await",
            "Understanding of Apple's Human Interface Guidelines",
            "App Store publication experience",
        ],
        "url": "https://apple.com/careers/ios-dev-13131",
        "source": "Apple Careers",
        "remote_status": "onsite",
        "industry": "Technology / Consumer Electronics",
        "experience_level": "Mid-Senior",
    },
    {
        "title": "Technical Project Manager",
        "company": "Atlassian",
        "location": "Sydney, Australia",
        "salary_range": "$120,000 - $160,000",
        "description": (
            "Lead cross-functional engineering projects from inception to launch. "
            "Manage timelines, risks, and stakeholder communications. "
            "Drive Agile ceremonies and continuous improvement. "
            "Coordinate with distributed teams across time zones."
        ),
        "requirements": [
            "5+ years of technical project management experience",
            "PMP or Agile certifications preferred",
            "Strong understanding of software development lifecycle",
            "Experience with Jira, Confluence, and project management tools",
            "Excellent communication and leadership skills",
        ],
        "url": "https://atlassian.com/careers/tpm-14141",
        "source": "Atlassian Careers",
        "remote_status": "remote",
        "industry": "Technology / SaaS",
        "experience_level": "Senior",
    },
]


# ---------------------------------------------------------------------------
# Filtering helpers
# ---------------------------------------------------------------------------

def _matches_query(job: dict[str, Any], query: str) -> bool:
    """Return True if the job matches the search query (case-insensitive)."""
    if not query:
        return True
    q = query.lower()
    searchable = " ".join(
        [
            job.get("title", ""),
            job.get("company", ""),
            job.get("description", ""),
            job.get("industry", ""),
            " ".join(job.get("requirements", [])),
        ]
    ).lower()
    # Support multi-word queries by checking each word
    return all(word in searchable for word in q.split())


def _matches_location(job: dict[str, Any], location: str) -> bool:
    """Return True if the job matches the requested location."""
    if not location:
        return True
    return location.lower() in (job.get("location", "") or "").lower()


def _matches_filters(job: dict[str, Any], filters: dict[str, Any]) -> bool:
    """Apply optional filters: remote_status, experience_level, industry, company."""
    if not filters:
        return True

    remote = filters.get("remote_status")
    if remote and job.get("remote_status", "").lower() != remote.lower():
        return False

    level = filters.get("experience_level")
    if level and level.lower() not in (job.get("experience_level", "") or "").lower():
        return False

    industry = filters.get("industry")
    if industry and industry.lower() not in (job.get("industry", "") or "").lower():
        return False

    company = filters.get("company")
    if company and company.lower() not in (job.get("company", "") or "").lower():
        return False

    return True


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def scrape_jobs(
    query: str = "",
    location: str = "",
    filters: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Search job listings using query, location, and optional filters.

    Attempts to pull real-life remote programming jobs from WeWorkRemotely RSS feed.
    Falls back to simulated job listings if no matches are found or if the network call fails.

    Args:
        query: Free-text search string (e.g. "Python developer", "Data Scientist").
        location: Location filter (e.g. "San Francisco", "Remote").
        filters: Optional dict with keys like remote_status, experience_level,
                 industry, company.

    Returns:
        List of matching job dicts.
    """
    import xml.etree.ElementTree as ET

    filters = filters or {}
    results: list[dict[str, Any]] = []

    # 1. Attempt to fetch live remote jobs from WeWorkRemotely
    try:
        logger.info("Attempting to fetch live jobs from WeWorkRemotely RSS feed...")
        response = requests.get("https://weworkremotely.com/categories/remote-programming-jobs.rss", timeout=10)
        if response.status_code == 200:
            root = ET.fromstring(response.content)
            items = root.findall(".//item")
            for item in items:
                title_text = item.find("title").text or ""
                company = "Unknown"
                title = title_text
                if ":" in title_text:
                    parts = title_text.split(":", 1)
                    company = parts[0].strip()
                    title = parts[1].strip()

                link = item.find("link").text or ""
                description_html = item.find("description").text or ""
                description = BeautifulSoup(description_html, "html.parser").get_text(separator=" ")

                requirements = [
                    "Strong background in software development",
                    "Experience working in remote environments",
                    "Self-motivated and excellent communicator",
                ]

                job_data = {
                    "title": title,
                    "company": company,
                    "location": "Remote",
                    "salary_range": "Not specified",
                    "description": description[:2000],  # limit description length
                    "requirements": requirements,
                    "url": link,
                    "source": "WeWorkRemotely",
                    "remote_status": "remote",
                    "industry": "Technology",
                    "experience_level": "Mid-Senior",
                    "date_found": datetime.utcnow().isoformat(),
                }

                # Location matching: WWR jobs are always remote, so any location filter containing "remote"
                # (or no location filter) matches them.
                loc_matches = not location or "remote" in location.lower() or location.lower() in "remote"

                if _matches_query(job_data, query) and loc_matches:
                    results.append(job_data)

            logger.info("Successfully fetched and filtered %d live jobs from WeWorkRemotely.", len(results))
    except Exception as exc:
        logger.error("Failed to fetch live jobs from WeWorkRemotely: %s. Falling back to simulated jobs.", exc)

    # 2. Fallback to simulated jobs if no live jobs matched
    if not results:
        logger.info("No live jobs matched or fetch failed. Falling back to simulated jobs...")
        for job in SIMULATED_JOBS:
            if (
                _matches_query(job, query)
                and _matches_location(job, location)
                and _matches_filters(job, filters)
            ):
                # Attach a synthetic date_found
                result = {**job, "date_found": datetime.utcnow().isoformat()}
                results.append(result)

    logger.info(
        "scrape_jobs(query='%s', location='%s', filters=%s) → %d results",
        query,
        location,
        filters,
        len(results),
    )
    return results


# ---------------------------------------------------------------------------
# Real scraper skeleton (BeautifulSoup) – for future use
# ---------------------------------------------------------------------------

def scrape_jobs_real(
    url: str,
    query: str = "",
    headers: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    """Skeleton for a real web scraper using BeautifulSoup.

    This is intentionally NOT called by the main code path. Enable it when
    you have a target job board URL and the legal right to scrape it.

    Args:
        url: The job board URL to scrape.
        query: Search query to append as a URL parameter.
        headers: Optional HTTP headers (User-Agent, etc.).

    Returns:
        List of extracted job dicts.
    """
    default_headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
    }
    headers = headers or default_headers

    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
    except requests.RequestException as exc:
        logger.error("Failed to fetch %s: %s", url, exc)
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    jobs: list[dict[str, Any]] = []

    # Example: iterate over job card elements (selectors depend on target site)
    job_cards = soup.select(".job-card, .job-listing, article.job")
    for card in job_cards:
        title_el = card.select_one(".job-title, h2, h3")
        company_el = card.select_one(".company-name, .employer")
        location_el = card.select_one(".location, .job-location")
        link_el = card.select_one("a[href]")

        jobs.append(
            {
                "title": title_el.get_text(strip=True) if title_el else "Unknown",
                "company": company_el.get_text(strip=True) if company_el else "Unknown",
                "location": location_el.get_text(strip=True) if location_el else "",
                "url": link_el["href"] if link_el else "",
                "source": url,
                "description": card.get_text(strip=True)[:500],
                "requirements": [],
                "salary_range": "",
                "remote_status": "",
                "industry": "",
                "experience_level": "",
                "date_found": datetime.utcnow().isoformat(),
            }
        )

    logger.info("Real scraper extracted %d jobs from %s", len(jobs), url)
    return jobs
