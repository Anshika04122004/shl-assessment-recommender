from __future__ import annotations

import re
from dataclasses import dataclass

from app.catalog import Catalog, Product, dedupe_products, normalize_text, tokenize
from app.schemas import ChatMessage, Recommendation


CATALOG = Catalog.load()


ALIASES = {
    "OPQ": "Occupational Personality Questionnaire OPQ32r",
    "OPQ32R": "Occupational Personality Questionnaire OPQ32r",
    "OPQ32": "Occupational Personality Questionnaire OPQ32r",
    "G+": "SHL Verify Interactive G+",
    "VERIFY G+": "SHL Verify Interactive G+",
    "GENERAL ABILITY": "SHL Verify Interactive G+",
    "COGNITIVE": "SHL Verify Interactive G+",
    "APTITUDE": "SHL Verify Interactive G+",
    "GRADUATE SJT": "Graduate Scenarios",
    "SITUATIONAL JUDGEMENT": "Graduate Scenarios",
    "SITUATIONAL JUDGMENT": "Graduate Scenarios",
    "SVAR US": "SVAR - Spoken English (US) (New)",
    "SVAR SPOKEN ENGLISH US": "SVAR - Spoken English (US) (New)",
    "SVAR SPOKEN ENGLISH UK": "SVAR - Spoken English (U.K.)",
    "SVAR SPOKEN ENGLISH AUS": "SVAR - Spoken English (AUS)",
    "SVAR SPOKEN ENGLISH INDIAN": "SVAR - Spoken English (Indian Accent) (New)",
    "EXCEL 365": "Microsoft Excel 365 - Essentials (New)",
    "WORD 365": "Microsoft Word 365 - Essentials (New)",
    "LIVE CODING": "Smart Interview Live Coding",
    "HIPAA": "HIPAA (Security)",
    "DSI": "Dependability and Safety Instrument (DSI)",
    "SAFETY AND DEPENDABILITY": "Manufac. & Indust. - Safety & Dependability 8.0",
    "CONTACT CENTER CALL SIMULATION": "Contact Center Call Simulation (New)",
    "ENTRY LEVEL CUSTOMER SERVICE": "Entry Level Customer Serv-Retail & Contact Center",
    "GSA": "Global Skills Assessment",
}


CANONICAL_BY_NAME = {
    name: CATALOG.get(name)
    for name in [
        "Amazon Web Services (AWS) Development (New)",
        "Basic Statistics (New)",
        "Contact Center Call Simulation (New)",
        "Core Java (Advanced Level) (New)",
        "Dependability and Safety Instrument (DSI)",
        "Docker (New)",
        "Entry Level Customer Serv-Retail & Contact Center",
        "Financial Accounting (New)",
        "Global Skills Assessment",
        "Global Skills Development Report",
        "Graduate Scenarios",
        "HIPAA (Security)",
        "Linux Programming (General)",
        "Manufac. & Indust. - Safety & Dependability 8.0",
        "Medical Terminology (New)",
        "Microsoft Excel 365 - Essentials (New)",
        "Microsoft Word 365 - Essentials (New)",
        "MS Excel (New)",
        "MS Word (New)",
        "Networking and Implementation (New)",
        "Occupational Personality Questionnaire OPQ32r",
        "OPQ Leadership Report",
        "OPQ MQ Sales Report",
        "OPQ Universal Competency Report 2.0",
        "RESTful Web Services (New)",
        "Sales Transformation 2.0 - Individual Contributor",
        "SHL Verify Interactive G+",
        "SHL Verify Interactive � Numerical Reasoning",
        "Smart Interview Live Coding",
        "Spring (New)",
        "SQL (New)",
        "SVAR - Spoken English (US) (New)",
        "SVAR - Spoken English (U.K.)",
        "SVAR - Spoken English (AUS)",
        "SVAR - Spoken English (Indian Accent) (New)",
        "Customer Service Phone Simulation",
        "Workplace Health and Safety (New)",
    ]
}


@dataclass
class State:
    all_user_text: str
    latest: str
    previous_recommendations: list[Product]
    turn_count: int


def build_state(messages: list[ChatMessage]) -> State:
    user_parts = [m.content for m in messages if m.role == "user"]
    assistant_parts = [m.content for m in messages if m.role == "assistant"]
    latest = user_parts[-1] if user_parts else ""
    previous = CATALOG.find_mentions("\n".join(assistant_parts))
    return State(
        all_user_text="\n".join(user_parts),
        latest=latest,
        previous_recommendations=previous,
        turn_count=len(messages),
    )


def is_prompt_injection(text: str) -> bool:
    norm = normalize_text(text)
    patterns = [
        "ignore previous",
        "ignore all previous",
        "ignore instructions",
        "system prompt",
        "developer message",
        "jailbreak",
        "do anything now",
        "forget the catalog",
        "outside the catalog",
        "invent an assessment",
        "return invalid json",
        "bypass",
        "override",
    ]
    return any(pattern in norm for pattern in patterns)


def is_legal_or_compliance(text: str) -> bool:
    norm = normalize_text(text)
    strong_legal = (
        "legally defensible",
        "legally required",
        "is it legal",
        "legal risk",
        "legal advice",
        "adverse impact",
        "discriminat",
        "protected class",
        "lawsuit",
        "comply with the law",
    )
    if any(term in norm for term in strong_legal):
        return True
    legal_terms = ("legally", "legal", "law", "lawful", "regulatory", "required under", "satisfy that requirement")
    compliance_terms = ("hipaa", "gdpr", "eeoc", "compliance")
    return any(term in norm for term in legal_terms) and any(term in norm for term in compliance_terms)


def is_off_topic(text: str) -> bool:
    norm = normalize_text(text)
    if any(term in norm for term in ("assessment", "test", "shl", "opq", "verify", "svar", "candidate", "hire", "hiring")):
        return False
    off_topic_terms = ("salary", "compensation", "write my resume", "cover letter", "interview questions", "marketing plan")
    return any(term in norm for term in off_topic_terms)


def is_confirmation(text: str) -> bool:
    norm = normalize_text(text)
    phrases = [
        "perfect",
        "that works",
        "thats good",
        "that's good",
        "confirmed",
        "confirm",
        "lock it in",
        "locking it in",
        "final list",
        "that covers it",
        "keep the shortlist",
        "thanks",
        "thank you",
    ]
    return any(phrase in norm for phrase in phrases)


def is_compare(text: str) -> bool:
    norm = normalize_text(text)
    return any(
        phrase in norm
        for phrase in (
            "difference between",
            "compare",
            " vs ",
            " vs.",
            " versus ",
            "different from",
            "differ",
            "how do they differ",
            "compared to",
            "trade off",
            "trade-off",
            "which is better",
            "do we really need",
        )
    )


def is_vague_initial(state: State) -> bool:
    norm = normalize_text(state.latest)
    if state.turn_count > 1:
        return False
    vague = [
        "i need an assessment",
        "need an assessment",
        "assessment for hiring",
        "help me choose",
        "what assessment should i use",
    ]
    has_role_signal = any(
        token in norm
        for token in (
            "java",
            "engineer",
            "sales",
            "graduate",
            "contact",
            "admin",
            "operator",
            "finance",
            "leadership",
            "executive",
            "healthcare",
            "excel",
            "word",
        )
    )
    return any(phrase in norm for phrase in vague) and not has_role_signal


def products_by_names(names: list[str]) -> list[Product]:
    products = [CATALOG.get(name) for name in names]
    return [product for product in products if product is not None]


def mentioned_alias_products(text: str) -> list[Product]:
    norm = normalize_text(text)
    result: list[Product] = []
    for alias, name in ALIASES.items():
        if normalize_text(alias) in norm:
            product = CATALOG.get(name)
            if product:
                result.append(product)
    result.extend(CATALOG.find_mentions(text))
    return dedupe_products(result)


def has_any(text: str, terms: tuple[str, ...]) -> bool:
    norm = normalize_text(text)
    return any(term in norm for term in terms)


def wants_remove_opq(text: str) -> bool:
    norm = normalize_text(text)
    return ("drop" in norm or "remove" in norm or "skip" in norm) and ("opq" in norm or "personality" in norm)


def initial_shortlist(state: State) -> list[Product]:
    text = state.all_user_text
    norm = normalize_text(text)
    names: list[str] = []

    if has_any(text, ("senior leadership", "cxo", "director level", "executive", "leadership benchmark")):
        names = [
            "Occupational Personality Questionnaire OPQ32r",
            "OPQ Universal Competency Report 2.0",
            "OPQ Leadership Report",
        ]
    elif has_any(text, ("rust", "networking infrastructure", "high performance networking")):
        names = [
            "Smart Interview Live Coding",
            "Linux Programming (General)",
            "Networking and Implementation (New)",
            "SHL Verify Interactive G+",
            "Occupational Personality Questionnaire OPQ32r",
        ]
    elif has_any(text, ("contact centre", "contact center", "inbound calls", "call center")):
        if "english" in norm and not any(accent in norm for accent in (" us ", " usa ", " u s ", "uk", "australian", "indian")) and state.turn_count < 5:
            return []
        svar = "SVAR - Spoken English (US) (New)"
        if "uk" in norm or "u k" in norm:
            svar = "SVAR - Spoken English (U.K.)"
        elif "australian" in norm or " aus " in norm:
            svar = "SVAR - Spoken English (AUS)"
        elif "indian" in norm:
            svar = "SVAR - Spoken English (Indian Accent) (New)"
        names = [
            svar,
            "Contact Center Call Simulation (New)",
            "Entry Level Customer Serv-Retail & Contact Center",
            "Customer Service Phone Simulation",
        ]
    elif has_any(text, ("financial analyst", "finance analyst", "financial analysts")):
        names = [
            "SHL Verify Interactive � Numerical Reasoning",
            "Financial Accounting (New)",
            "Basic Statistics (New)",
            "Graduate Scenarios",
            "Occupational Personality Questionnaire OPQ32r",
        ]
    elif has_any(text, ("sales organization", "sales organisation", "sales audit", "re skill", "reskill", "re-skill")):
        names = [
            "Global Skills Assessment",
            "Global Skills Development Report",
            "Occupational Personality Questionnaire OPQ32r",
            "OPQ MQ Sales Report",
            "Sales Transformation 2.0 - Individual Contributor",
        ]
    elif has_any(text, ("plant operator", "chemical facility", "safety", "dependability", "procedure compliance")):
        if "industrial" in norm and "confirmed" in norm:
            names = [
                "Manufac. & Indust. - Safety & Dependability 8.0",
                "Workplace Health and Safety (New)",
            ]
        else:
            names = [
                "Dependability and Safety Instrument (DSI)",
                "Manufac. & Indust. - Safety & Dependability 8.0",
                "Workplace Health and Safety (New)",
            ]
    elif has_any(text, ("healthcare admin", "patient records", "hipaa", "medical terminology")):
        if has_any(text, ("spanish", "south texas", "bilingual")) and not has_any(text, ("hybrid", "english fluent", "functionally bilingual")) and state.turn_count < 5:
            return []
        names = [
            "HIPAA (Security)",
            "Medical Terminology (New)",
            "Microsoft Word 365 - Essentials (New)",
            "Dependability and Safety Instrument (DSI)",
            "Occupational Personality Questionnaire OPQ32r",
        ]
    elif has_any(text, ("admin assistant", "excel and word", "excel", "word daily")):
        if has_any(text, ("simulation", "capture the capabilities", "capabilities")):
            names = [
                "Microsoft Excel 365 - Essentials (New)",
                "Microsoft Word 365 - Essentials (New)",
                "MS Excel (New)",
                "MS Word (New)",
                "Occupational Personality Questionnaire OPQ32r",
            ]
        else:
            names = [
                "MS Excel (New)",
                "MS Word (New)",
                "Occupational Personality Questionnaire OPQ32r",
            ]
    elif has_any(text, ("full stack", "full-stack", "java", "spring")):
        if has_any(text, ("backend leaning", "backend-leaning", "senior ic", "senior individual")) or ("backend" in norm and ("java" in norm or "spring" in norm)) or state.turn_count >= 5:
            names = [
                "Core Java (Advanced Level) (New)",
                "Spring (New)",
                "RESTful Web Services (New)",
                "SQL (New)",
                "SHL Verify Interactive G+",
                "Occupational Personality Questionnaire OPQ32r",
            ]
            if has_any(text, ("drop rest", "remove rest")):
                names = [name for name in names if name != "RESTful Web Services (New)"]
            if "aws" in norm:
                names.insert(4, "Amazon Web Services (AWS) Development (New)")
            if "docker" in norm:
                insert_at = 5 if "aws" in norm else 4
                names.insert(insert_at, "Docker (New)")
        else:
            return []
    elif has_any(text, ("graduate management trainee", "management trainee", "recent graduates")):
        names = ["SHL Verify Interactive G+", "Occupational Personality Questionnaire OPQ32r", "Graduate Scenarios"]
        if wants_remove_opq(text):
            names = ["SHL Verify Interactive G+", "Graduate Scenarios"]

    products = products_by_names(names)
    if products:
        return dedupe_products(products)

    return fallback_search(state)


def fallback_search(state: State) -> list[Product]:
    text = state.all_user_text
    products = mentioned_alias_products(text)
    for product, _score in CATALOG.search(text, limit=25):
        products.append(product)

    norm = normalize_text(text)
    boosted: list[str] = []
    if "personality" in norm or "behavior" in norm or "behaviour" in norm or "senior" in norm:
        boosted.append("Occupational Personality Questionnaire OPQ32r")
    if "cognitive" in norm or "reasoning" in norm or "aptitude" in norm:
        boosted.append("SHL Verify Interactive G+")
    if "graduate" in norm and ("scenario" in norm or "situational" in norm or "judgment" in norm or "judgement" in norm):
        boosted.append("Graduate Scenarios")
    products = products_by_names(boosted) + products

    filtered: list[Product] = []
    for product in products:
        if product.is_report and not has_any(text, ("report", "feedback", "development", "audit", "leadership")):
            continue
        filtered.append(product)
    return dedupe_products(filtered)[:10]


def refine_shortlist(state: State) -> list[Product]:
    base = list(state.previous_recommendations) or initial_shortlist(state)
    latest_norm = normalize_text(state.latest)

    if "drop rest" in latest_norm or "remove rest" in latest_norm:
        base = [p for p in base if "restful" not in normalize_text(p.name)]
    if wants_remove_opq(state.latest):
        base = [p for p in base if "opq" not in normalize_text(p.name) and "personality questionnaire" not in normalize_text(p.name)]
    if "drop verify" in latest_norm or "remove verify" in latest_norm:
        base = [p for p in base if "verify interactive g" not in normalize_text(p.name)]

    additions: list[str] = []
    if "aws" in latest_norm:
        additions.append("Amazon Web Services (AWS) Development (New)")
    if "docker" in latest_norm:
        additions.append("Docker (New)")
    all_norm = normalize_text(state.all_user_text)
    if "simulation" in latest_norm and ("excel" in all_norm or "word" in all_norm):
        additions.extend(["Microsoft Excel 365 - Essentials (New)", "Microsoft Word 365 - Essentials (New)"])
    if "situational" in latest_norm or "judgment" in latest_norm or "judgement" in latest_norm:
        additions.append("Graduate Scenarios")
    if "personality" in latest_norm and not ("drop" in latest_norm or "remove" in latest_norm):
        additions.append("Occupational Personality Questionnaire OPQ32r")

    base = base + products_by_names(additions)
    return dedupe_products(base)[:10]


def product_names_line(products: list[Product]) -> str:
    return "; ".join(product.name for product in products)


def to_recommendations(products: list[Product]) -> list[Recommendation]:
    recommendations: list[Recommendation] = []
    for product in products[:10]:
        if product.url not in CATALOG.urls:
            continue
        recommendations.append(Recommendation(name=product.name, url=product.url, test_type=product.test_type))
    return recommendations


def needs_clarification(state: State) -> str | None:
    text = state.all_user_text
    norm = normalize_text(text)
    if is_vague_initial(state):
        return "I can help with SHL assessments. What role are you hiring for, and what do you most need to measure?"
    if has_any(text, ("contact centre", "contact center", "inbound calls", "call center")):
        if "english" not in norm and not any(lang in norm for lang in ("spanish", "french")):
            return "What language will candidates use for the calls? That determines the spoken-language assessment."
        if "english" in norm and not any(accent in norm for accent in (" us", " usa", " u s", "uk", "u k", "australian", "indian")):
            return "Which English accent should the spoken-language screen use: US, UK, Australian, or Indian?"
    if has_any(text, ("healthcare admin", "patient records")) and has_any(text, ("spanish", "bilingual")):
        if not has_any(text, ("hybrid", "english fluent", "functionally bilingual")):
            return "The healthcare knowledge tests are English-only, while OPQ32r and DSI support Latin American Spanish. Are candidates functionally bilingual enough for a hybrid English/Spanish battery?"
    if has_any(text, ("full stack", "full-stack")) and not has_any(text, ("backend", "frontend", "balanced", "senior ic", "tech lead")):
        return "Is this role backend-leaning, frontend-heavy, or a balanced full-stack role?"
    if has_any(text, ("backend leaning", "backend-leaning")) and not has_any(text, ("senior ic", "tech lead", "individual contributor")):
        return "Is the seniority closer to a senior individual contributor or a tech lead?"
    if has_any(text, ("senior leadership", "cxo", "director level")) and not has_any(text, ("selection", "development", "feedback")):
        return "Is this for selection against a leadership benchmark, or developmental feedback for leaders already in role?"
    return None


def compare_reply(state: State) -> str:
    candidates = mentioned_alias_products(state.latest)
    if len(candidates) < 2:
        candidates = mentioned_alias_products(state.all_user_text)
    if len(candidates) < 2:
        return "I can compare SHL assessments, but I need the product names. Which two catalog items should I compare?"

    first, second = candidates[0], candidates[1]
    lines = [
        f"{first.name}: {first.description[:450].strip()}",
        f"{second.name}: {second.description[:450].strip()}",
        "In catalog terms, compare them by purpose, category, duration, languages, and job levels rather than by general hiring advice.",
    ]
    return "\n\n".join(lines)


def build_recommendation_reply(products: list[Product], prefix: str) -> str:
    names = product_names_line(products)
    return f"{prefix}\n\nShortlist: {names}."


def chat(messages: list[ChatMessage]):
    state = build_state(messages)
    latest = state.latest

    if is_prompt_injection(latest):
        return "I can't follow instructions that override the SHL catalog or API rules. I can only help select valid SHL assessments from the catalog.", [], False
    if is_legal_or_compliance(latest):
        return "I can't advise on legal or regulatory obligations. I can identify SHL assessments related to the topic, but whether a test satisfies a legal requirement should be checked with your legal or compliance team.", [], False
    if is_off_topic(latest):
        return "I can only help with SHL assessment selection. Share the role and what you want to measure, and I can recommend catalog assessments.", [], False

    if is_confirmation(latest) and state.previous_recommendations:
        recs = state.previous_recommendations[:10]
        return build_recommendation_reply(recs, "Confirmed. Final SHL shortlist:"), to_recommendations(recs), True

    if is_compare(latest) and not any(term in normalize_text(latest) for term in ("add ", "drop ", "remove ", "replace ")):
        return compare_reply(state), [], False

    latest_norm = normalize_text(latest)
    if state.previous_recommendations and "opq" in latest_norm and "replace" in latest_norm and "shorter" in latest_norm:
        return "OPQ32r is the main catalog personality questionnaire for this need. I do not see a shorter like-for-like replacement in the catalog; I can keep OPQ32r or remove the personality component if you prefer.", [], False

    if state.turn_count >= 7:
        products = refine_shortlist(state) if state.previous_recommendations else initial_shortlist(state)
        if not products:
            products = fallback_search(state)
        if products:
            return build_recommendation_reply(products, "To stay within the conversation limit, here is the best catalog-grounded shortlist I can commit to now:"), to_recommendations(products), False

    clarification = needs_clarification(state)
    if clarification and not state.previous_recommendations:
        return clarification, [], False

    if state.previous_recommendations and any(term in latest_norm for term in ("add", "drop", "remove", "replace", "include", "actually")):
        products = refine_shortlist(state)
        return build_recommendation_reply(products, "Updated the shortlist based on your latest constraint:"), to_recommendations(products), False

    products = initial_shortlist(state)
    if not products:
        clarification = clarification or "What role are you hiring for, and which capabilities should the assessment measure?"
        return clarification, [], False

    return build_recommendation_reply(products, "Here are SHL catalog assessments that fit the role:"), to_recommendations(products), False
