"""Versioned financial semantics used by persistence, summaries, and ML snapshots."""
from __future__ import annotations

CATEGORY_CONTRACT_VERSION = "categories-v2"
SUMMARY_METHODOLOGY_VERSION = "summary-v2"
ML_FEATURE_CONTRACT_VERSION = "monthly-financial-v2"

EXPENSE_CATEGORY_CODES = (
    "food", "transport", "shopping", "bills", "housing", "health",
    "entertainment", "education", "debt", "other",
)
ML_CATEGORY_CODES = ("food", "transport", "shopping", "bills", "housing", "health", "entertainment")
ESSENTIAL_CATEGORY_CODES = frozenset(("food", "transport", "bills", "housing", "health", "education", "debt"))

# Exact normalized aliases. We intentionally do not use substring matching.
CATEGORY_ALIASES = {
    "food": "food", "groceries": "food", "طعام": "food", "الطعام": "food",
    "transport": "transport", "transportation": "transport", "المواصلات": "transport",
    "shopping": "shopping", "التسوق": "shopping",
    "bills": "bills", "utilities": "bills", "الفواتير": "bills",
    "housing": "housing", "rent": "housing", "mortgage": "housing", "السكن": "housing",
    "health": "health", "healthcare": "health", "الصحة": "health",
    "entertainment": "entertainment", "الترفيه": "entertainment",
    "education": "education", "التعليم": "education",
    "debt": "debt", "loan payment": "debt", "الديون": "debt",
    "salary": "income", "business": "income", "investment": "income", "دخل": "income",
    "other": "other", "أخرى": "other",
}

def normalize_category(name: str | None, kind: str) -> tuple[str, bool]:
    if kind == "income":
        return "income", False
    key = " ".join((name or "other").strip().lower().split())
    code = CATEGORY_ALIASES.get(key, "other")
    return code, code in ESSENTIAL_CATEGORY_CODES
