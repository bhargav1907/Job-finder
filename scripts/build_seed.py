#!/usr/bin/env python3
"""Build data/seed_jobs.json.

Deterministic, offline, and clearly synthetic: every listing points at
demo.example and is labelled source="demo". Real providers are added later
behind backend/app/sources/base.py; this file is only demo material.
"""

import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "seed_jobs.json"

COMPANIES = [
    "Aurora Labs", "Nimbus AI", "Kalyani Systems", "Meridian Tech", "Saffron Data",
    "Vertex Solutions", "Bluewave Analytics", "Tessellate", "Coral Cloud", "Indus Robotics",
    "Orbit Software", "Pragati AI", "Lumen Works", "Mosaic Health", "Kite Graph",
    "Silverline Tech", "Northstar Analytics", "Rivet Labs", "Cascade AI", "Anvaya Systems",
    "Harbor Stack", "Kaveri Tech", "Polaris Data", "Trellis AI",
]

LOCATIONS = [
    ("Bengaluru, India", False), ("Hyderabad, India", False), ("Pune, India", False),
    ("Chennai, India", False), ("Mumbai, India", False), ("Gurugram, India", False),
    ("Noida, India", False), ("Remote, India", True),
]

ROLES = [
    ("AI Engineer", "ai_ml", ["python", "pytorch", "llm", "rag", "fastapi", "docker"]),
    ("Machine Learning Engineer", "ai_ml", ["python", "pytorch", "scikit-learn", "mlops", "docker", "kubernetes"]),
    ("Data Scientist", "data", ["python", "pandas", "numpy", "scikit-learn", "sql"]),
    ("Data Engineer", "data", ["python", "sql", "spark", "airflow", "kafka", "aws"]),
    ("NLP Engineer", "ai_ml", ["python", "transformers", "nlp", "huggingface", "pytorch"]),
    ("Computer Vision Engineer", "ai_ml", ["python", "pytorch", "computer-vision", "opencv", "docker"]),
    ("MLOps Engineer", "devops", ["python", "docker", "kubernetes", "mlops", "aws", "airflow"]),
    ("GenAI Engineer", "ai_ml", ["python", "llm", "langchain", "rag", "embeddings", "vector-db"]),
    ("LLM Engineer", "ai_ml", ["python", "llm", "fine-tuning", "transformers", "prompt-engineering"]),
    ("Backend Engineer", "backend", ["python", "fastapi", "sql", "postgresql", "docker", "redis"]),
    ("Full Stack Engineer", "fullstack", ["typescript", "react", "node.js", "postgresql", "docker"]),
    ("Frontend Engineer", "frontend", ["typescript", "react", "next.js", "tailwind", "javascript"]),
    ("DevOps Engineer", "devops", ["docker", "kubernetes", "aws", "git", "airflow"]),
    ("QA Automation Engineer", "qa", ["python", "pytest", "docker", "git", "sql"]),
    ("AI Solutions Architect", "ai_ml", ["python", "llm", "aws", "azure", "docker"]),
    ("Research Engineer", "ai_ml", ["python", "pytorch", "transformers", "nlp", "scikit-learn"]),
    ("Prompt Engineer", "ai_ml", ["llm", "prompt-engineering", "python", "rag"]),
    ("AI Product Engineer", "ai_ml", ["python", "llm", "react", "fastapi", "embeddings"]),
]

PREFIXES = [
    ("", "mid", 3, (1_400_000, 2_600_000)),
    ("Junior ", "junior", 1, (700_000, 1_400_000)),
    ("Senior ", "senior", 5, (2_600_000, 4_500_000)),
    ("Lead ", "lead", 8, (4_500_000, 7_000_000)),
]

TEAMS = ["Applied AI", "Platform", "Data", "GenAI Products", "Core Engineering", "Growth"]
FOCUS = [
    "retrieval systems for enterprise search",
    "agentic workflows for customer support",
    "real-time recommendation infrastructure",
    "document understanding pipelines",
    "evaluation tooling for language models",
    "a multi-tenant analytics platform",
    "conversational products for Indian languages",
    "internal developer platforms",
]
RESPONSIBILITIES = [
    "design and ship production services end to end",
    "own model evaluation and regression testing",
    "partner with product on scoping and trade-offs",
    "improve latency, cost, and reliability of the stack",
    "write clear design docs and review code",
    "mentor engineers and raise the technical bar",
]
NICE_TO_HAVE = ["langgraph", "mqtt", "terraform", "gcp", "ragas", "langsmith", "streamlit", "mcp"]


def slugify(value: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "-" for ch in value).strip("-")


def build() -> list[dict]:
    rng = random.Random(42)
    now = datetime.now(timezone.utc)
    rows: list[dict] = []

    for index in range(100):
        title_base, role_family, skills = ROLES[index % len(ROLES)]
        prefix, seniority, years, (low, high) = PREFIXES[index % len(PREFIXES)]
        company = COMPANIES[index % len(COMPANIES)]
        location, remote = LOCATIONS[(index * 3) % len(LOCATIONS)]
        title = f"{prefix}{title_base}"
        team = TEAMS[index % len(TEAMS)]
        focus = FOCUS[(index * 5) % len(FOCUS)]

        salary_min = rng.randrange(low, high)
        salary_max = min(salary_min + rng.randrange(200_000, 900_000), high + 500_000)
        r1, r2 = rng.sample(RESPONSIBILITIES, 2)
        extra = rng.sample(NICE_TO_HAVE, 2)

        description = (
            f"{company} is hiring a {title} for the {team} team in {location}. "
            f"Our team is building {focus}.\n\n"
            f"You will {r1}, {r2}, and collaborate closely with product and design.\n\n"
            f"Requirements:\n"
            f"- {years}+ years of professional software or ML experience\n"
            f"- Strong hands-on experience with {', '.join(skills[:3])}\n"
            f"- Working knowledge of {', '.join(skills[3:])}\n"
            f"- Clear written communication and a bias for shipping\n\n"
            f"Nice to have: {', '.join(extra)}.\n\n"
            f"{'This role is fully remote within India.' if remote else 'Hybrid role, three days a week in office.'} "
            f"Annual compensation: {salary_min // 100_000} to {salary_max // 100_000} LPA."
        )

        rows.append({
            "id": f"demo-{index + 1:03d}",
            "source": "demo",
            "title": title,
            "company": company,
            "location": location,
            "remote": remote,
            "description": description,
            "url": f"https://demo.example/jobs/{slugify(title)}-{slugify(company)}-{index + 1:03d}",
            "salary_min": salary_min,
            "salary_max": salary_max,
            "currency": "INR",
            "posted_at": (now - timedelta(days=rng.randrange(0, 60))).isoformat(),
        })

    return rows


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    rows = build()
    OUT.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(rows)} listings to {OUT}")


if __name__ == "__main__":
    main()
