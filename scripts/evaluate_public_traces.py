from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.recommender import chat
from app.schemas import ChatMessage


SCENARIOS = [
    {
        "id": "C1",
        "messages": [
            ("user", "We need a solution for senior leadership."),
            ("assistant", "Who is this meant for?"),
            ("user", "The pool consists of CXOs, director-level positions; people with more than 15 years of experience."),
            ("assistant", "Is this selection or development?"),
            ("user", "Selection - comparing candidates against a leadership benchmark."),
        ],
        "expected": [
            "Occupational Personality Questionnaire OPQ32r",
            "OPQ Universal Competency Report 2.0",
            "OPQ Leadership Report",
        ],
    },
    {
        "id": "C2",
        "messages": [
            ("user", "I am hiring a senior Rust engineer for high-performance networking infrastructure."),
            ("assistant", "Want me to build a shortlist?"),
            ("user", "Yes, go ahead. Should I also add a cognitive test for this level?"),
        ],
        "expected": [
            "Smart Interview Live Coding",
            "Linux Programming (General)",
            "Networking and Implementation (New)",
            "SHL Verify Interactive G+",
            "Occupational Personality Questionnaire OPQ32r",
        ],
    },
    {
        "id": "C3",
        "messages": [
            ("user", "We are screening 500 entry-level contact center agents. Inbound calls, customer service focus."),
            ("assistant", "What language?"),
            ("user", "English."),
            ("assistant", "Which English accent?"),
            ("user", "US."),
        ],
        "expected": [
            "SVAR - Spoken English (US) (New)",
            "Contact Center Call Simulation (New)",
            "Entry Level Customer Serv-Retail & Contact Center",
            "Customer Service Phone Simulation",
        ],
    },
    {
        "id": "C4",
        "messages": [
            ("user", "Hiring graduate financial analysts - final-year students, no work experience. We need numerical reasoning and a finance knowledge test."),
            ("assistant", "Shortlist ready."),
            ("user", "Add a situational judgement element for graduates."),
        ],
        "expected": [
            "SHL Verify Interactive \u2013 Numerical Reasoning",
            "Financial Accounting (New)",
            "Basic Statistics (New)",
            "Graduate Scenarios",
            "Occupational Personality Questionnaire OPQ32r",
        ],
    },
    {
        "id": "C5",
        "messages": [
            ("user", "As part of restructuring and annual talent audit, we need to re-skill our Sales organization."),
        ],
        "expected": [
            "Global Skills Assessment",
            "Global Skills Development Report",
            "Occupational Personality Questionnaire OPQ32r",
            "OPQ MQ Sales Report",
            "Sales Transformation 2.0 - Individual Contributor",
        ],
    },
    {
        "id": "C6",
        "messages": [
            ("user", "We are hiring plant operators for a chemical facility. Safety is top priority - reliability, procedure compliance, never cutting corners."),
        ],
        "expected": [
            "Dependability and Safety Instrument (DSI)",
            "Manufac. & Indust. - Safety & Dependability 8.0",
            "Workplace Health and Safety (New)",
        ],
    },
    {
        "id": "C7",
        "messages": [
            ("user", "We are hiring bilingual healthcare admin staff in South Texas. Patient records, assessed in Spanish. HIPAA compliance is critical."),
            ("assistant", "Are they functionally bilingual enough for a hybrid battery?"),
            ("user", "They are functionally bilingual. English fluent for written work. Go with the hybrid."),
        ],
        "expected": [
            "HIPAA (Security)",
            "Medical Terminology (New)",
            "Microsoft Word 365 - Essentials (New)",
            "Dependability and Safety Instrument (DSI)",
            "Occupational Personality Questionnaire OPQ32r",
        ],
    },
    {
        "id": "C8",
        "messages": [
            ("user", "I need to quickly screen admin assistants for Excel and Word daily."),
            ("assistant", "Shortlist: MS Excel (New); MS Word (New); Occupational Personality Questionnaire OPQ32r."),
            ("user", "I am OK with adding a simulation - we want to capture the capabilities."),
        ],
        "expected": [
            "Microsoft Excel 365 - Essentials (New)",
            "Microsoft Word 365 - Essentials (New)",
            "MS Excel (New)",
            "MS Word (New)",
            "Occupational Personality Questionnaire OPQ32r",
        ],
    },
    {
        "id": "C9",
        "messages": [
            ("user", "Senior Full-Stack Engineer - Core Java, Spring, REST API design, Angular, SQL, AWS deployment, and Docker."),
            ("assistant", "Backend or frontend?"),
            ("user", "Backend-leaning. Core Java, Spring and SQL are primary."),
            ("assistant", "Senior IC or tech lead?"),
            ("user", "Senior IC."),
            ("assistant", "Shortlist: Core Java (Advanced Level) (New); Spring (New); RESTful Web Services (New); SQL (New); SHL Verify Interactive G+; Occupational Personality Questionnaire OPQ32r."),
            ("user", "Add AWS and Docker. Drop REST."),
        ],
        "expected": [
            "Core Java (Advanced Level) (New)",
            "Spring (New)",
            "SQL (New)",
            "Amazon Web Services (AWS) Development (New)",
            "Docker (New)",
            "SHL Verify Interactive G+",
            "Occupational Personality Questionnaire OPQ32r",
        ],
    },
    {
        "id": "C10",
        "messages": [
            ("user", "We run a graduate management trainee scheme. We need a full battery - cognitive, personality, and situational judgement. All recent graduates."),
        ],
        "expected": [
            "SHL Verify Interactive G+",
            "Occupational Personality Questionnaire OPQ32r",
            "Graduate Scenarios",
        ],
    },
]


def recall_at_10(actual: list[str], expected: list[str]) -> float:
    top_10 = set(actual[:10])
    return len(top_10 & set(expected)) / len(expected)


def main() -> None:
    scores: list[float] = []
    for scenario in SCENARIOS:
        messages = [ChatMessage(role=role, content=content) for role, content in scenario["messages"]]
        _reply, recommendations, _end = chat(messages)
        actual = [rec.name for rec in recommendations]
        score = recall_at_10(actual, scenario["expected"])
        scores.append(score)
        missing = [name for name in scenario["expected"] if name not in actual[:10]]
        print(f"{scenario['id']}: Recall@10={score:.2f} recommendations={len(actual)}")
        if missing:
            print(f"  Missing: {missing}")
        print(f"  Actual: {actual}")
    print(f"Mean Recall@10={sum(scores) / len(scores):.2f}")


if __name__ == "__main__":
    main()
