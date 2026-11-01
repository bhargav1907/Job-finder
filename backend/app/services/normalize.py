"""Deterministic, dependency-free normalization.

Everything here is cheap and testable. The LLM is not used for parsing fields
we can derive reliably; it is reserved for judgement (matching, resume parsing).
"""

import hashlib
import re

# canonical skill -> aliases found in job text
SKILL_ALIASES: dict[str, tuple[str, ...]] = {
    "python": ("python",),
    "pandas": ("pandas",),
    "numpy": ("numpy",),
    "pytorch": ("pytorch", "torch"),
    "tensorflow": ("tensorflow",),
    "scikit-learn": ("scikit-learn", "sklearn"),
    "langchain": ("langchain",),
    "langgraph": ("langgraph",),
    "rag": ("rag", "retrieval augmented generation", "retrieval-augmented generation"),
    "llm": ("llm", "llms", "large language model", "large language models"),
    "prompt-engineering": ("prompt engineering",),
    "fine-tuning": ("fine-tuning", "fine tuning", "finetuning"),
    "fastapi": ("fastapi",),
    "django": ("django",),
    "flask": ("flask",),
    "sql": ("sql",),
    "postgresql": ("postgresql", "postgres"),
    "mysql": ("mysql",),
    "mongodb": ("mongodb", "mongo")
    ,
    "redis": ("redis",),
    "docker": ("docker",),
    "kubernetes": ("kubernetes", "k8s"),
    "aws": ("aws", "amazon web services"),
    "azure": ("azure",),
    "gcp": ("gcp", "google cloud"),
    "git": ("git",),
    "javascript": ("javascript",),
    "typescript": ("typescript",),
    "react": ("react", "react.js", "reactjs"),
    "next.js": ("next.js", "nextjs"),
    "node.js": ("node.js", "nodejs"),
    "java": ("java",),
    "spring": ("spring boot", "spring"),
    "go": ("golang",),
    "rust": ("rust",),
    "c++": ("c++", "cpp"),
    "spark": ("spark", "pyspark"),
    "airflow": ("airflow",),
    "kafka": ("kafka",),
    "mlops": ("mlops", "ml ops"),
    "huggingface": ("huggingface", "hugging face"),
    "transformers": ("transformers",),
    "nlp": ("nlp", "natural language processing"),
    "computer-vision": ("computer vision", "opencv"),
    "embeddings": ("embeddings", "embedding"),
    "vector-db": ("vector database", "vector db", "pinecone", "faiss", "weaviate", "chroma"),
    "mcp": ("mcp", "model context protocol"),
    "streamlit": ("streamlit",),
    "tailwind": ("tailwind",),
    "langsmith": ("langsmith",),
    "ragas": ("ragas",),
    "pytest": ("pytest",),
}

_SKILL_PATTERNS: list[tuple[str, re.Pattern[str]]] = []
for _canonical, _aliases in SKILL_ALIASES.items():
    _parts = [
        r"(?<![\w])" + re.escape(alias).replace(r"\ ", r"[\s\-]+") + r"(?![\w])"
        for alias in _aliases
    ]
    _SKILL_PATTERNS.append((_canonical, re.compile("|".join(_parts), re.IGNORECASE)))


def normalize_ws(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def fingerprint(title: str, company: str, location: str, url: str) -> str:
    """Stable identity across feeds. Same job from two sources -> same hash."""
    key = "|".join(normalize_ws(part).lower() for part in (title, company, location, url))
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def extract_skills(text: str) -> list[str]:
    return sorted({name for name, pattern in _SKILL_PATTERNS if pattern.search(text or "")})


def detect_seniority(title: str) -> str:
    t = (title or "").lower()
    if re.search(r"\b(intern|internship|trainee)\b", t):
        return "intern"
    if re.search(r"\b(principal|staff|lead|head|architect)\b", t):
        return "lead"
    if re.search(r"\b(senior|sr\.?)\b", t):
        return "senior"
    if re.search(r"\b(junior|jr\.?|entry.level|associate|fresher|graduate)\b", t):
        return "junior"
    return "mid"


ROLE_FAMILIES: list[tuple[str, tuple[str, ...]]] = [
    ("fullstack", ("full stack", "fullstack", "full-stack")),
    ("ai_ml", (
        "machine learning", "ml engineer", "ai engineer", "artificial intelligence",
        "deep learning", "nlp", "computer vision", "research engineer", "applied scientist",
        "genai", "llm engineer", "prompt engineer", "rag engineer", "ai ",
    )),
    ("data", ("data scientist", "data engineer", "data analyst", "analytics")),
    ("devops", ("devops", "sre", "site reliability", "platform engineer", "mlops", "infrastructure", "cloud engineer")),
    ("qa", ("qa", "test engineer", "automation engineer", "quality assurance")),
    ("mobile", ("android", "ios", "mobile")),
    ("frontend", ("frontend", "front-end", "react", "ui engineer", "web developer")),
    ("backend", ("backend", "back-end", "api engineer", "server-side", "python engineer", "java engineer")),
    ("product", ("product manager", "product owner")),
]


def infer_role_family(title: str, description: str = "") -> str:
    text = f"{title} {description[:300]}".lower()
    for family, needles in ROLE_FAMILIES:
        if any(needle in text for needle in needles):
            return family
    return "other"


_LPA_RANGE = re.compile(r"(\d+(?:\.\d+)?)\s*(?:-|to|–)\s*(\d+(?:\.\d+)?)\s*(lpa|lakhs?|lakh)", re.I)
_LPA_SINGLE = re.compile(r"(\d+(?:\.\d+)?)\s*(lpa|lakhs?|lakh)", re.I)


def parse_salary(text: str) -> tuple[int | None, int | None, str]:
    """Returns (annual_min, annual_max, currency). Understands Indian LPA."""
    text = text or ""
    currency = "USD" if re.search(r"(\$|usd)", text, re.I) else "INR"

    match = _LPA_RANGE.search(text)
    if match:
        low, high = float(match.group(1)), float(match.group(2))
        return int(low * 100_000), int(high * 100_000), currency

    match = _LPA_SINGLE.search(text)
    if match:
        value = int(float(match.group(1)) * 100_000)
        return value, value, currency

    return None, None, currency
