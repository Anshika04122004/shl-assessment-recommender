# SHL Conversational Assessment Recommender Pipeline Plan

## 1. What This Assignment Is Asking For

The assignment is to build a conversational API that helps recruiters and hiring managers choose SHL assessments from the SHL Individual Test Solutions catalog.

The user may begin with something vague, such as:

> I need an assessment.

Or something detailed, such as:

> I am hiring a senior Java engineer who uses Spring, SQL, AWS, and Docker.

The system must talk with the user, ask clarifying questions when needed, recommend a shortlist when enough information is available, refine the shortlist when the user changes constraints, compare assessments when asked, and refuse anything outside SHL assessment selection.

The most important rule: every recommendation must come from the provided SHL catalog. The model must never invent an assessment or URL.

## 2. Exact Required API

The submitted service must be a public FastAPI app with two endpoints.

### GET `/health`

Returns:

```json
{"status": "ok"}
```

It must return HTTP 200.

### POST `/chat`

Request:

```json
{
  "messages": [
    {"role": "user", "content": "Hiring a Java developer who works with stakeholders"},
    {"role": "assistant", "content": "Sure. What is seniority level?"},
    {"role": "user", "content": "Mid-level, around 4 years"}
  ]
}
```

Response:

```json
{
  "reply": "Got it. Here are 5 assessments that fit a mid-level Java dev with stakeholder needs.",
  "recommendations": [
    {
      "name": "Java 8 (New)",
      "url": "https://www.shl.com/...",
      "test_type": "K"
    }
  ],
  "end_of_conversation": false
}
```

Strict schema rules:

- `reply` is always a string.
- `recommendations` is always an array.
- `recommendations` is empty when clarifying, comparing without recommitting, or refusing.
- `recommendations` contains 1 to 10 items when the agent commits to a shortlist.
- Every recommendation must have exactly `name`, `url`, and `test_type`.
- `end_of_conversation` is true only when the user has accepted or finalized the recommendation.
- The API is stateless. Every call receives the full conversation history. The server must not depend on stored chat state.
- The evaluator caps conversations at 8 total turns and each API call at 30 seconds.

## 3. Research Findings From The Assignment Files

The PDF contains three important hidden links:

- SHL product catalog page: `https://www.shl.com/solutions/products/product-catalog/`
- Provided catalog JSON: `https://tcp-us-prod-rnd.shl.com/voiceRater/shl-ai-hiring/shl_product_catalog.json`
- Public sample conversations: `https://tcp-us-prod-rnd.shl.com/voiceRater/shl-ai-hiring/sample_conversations.zip`

The provided catalog currently contains 377 products. Each product has these fields:

- `entity_id`
- `name`
- `link`
- `scraped_at`
- `job_levels`
- `job_levels_raw`
- `languages`
- `languages_raw`
- `duration`
- `duration_raw`
- `status`
- `remote`
- `adaptive`
- `description`
- `keys`

Important catalog categories:

- `Knowledge & Skills`: 240 products
- `Personality & Behavior`: 67 products
- `Simulations`: 43 products
- `Ability & Aptitude`: 32 products
- `Competencies`: 19 products
- `Biodata & Situational Judgment`: 17 products
- `Development & 360`: 7 products
- `Assessment Exercises`: 2 products

Important test type mapping for API output:

| Catalog Key | API `test_type` |
|---|---|
| Ability & Aptitude | A |
| Biodata & Situational Judgment | B |
| Competencies | C |
| Development & 360 | D |
| Knowledge & Skills | K |
| Personality & Behavior | P |
| Simulations | S |
| Assessment Exercises | E, inferred only |

Some products have multiple categories, so `test_type` can be comma-separated, for example `K,S` or `P,C`.

Most mappings above are confirmed by the public traces. `Assessment Exercises` does not appear as a standalone recommendation in the traces, so treat `E` as an implementation convention. If possible, avoid recommending those two products unless they are clearly the best catalog match, or verify the expected code before final submission.

The catalog JSON has raw control characters, so ingestion should parse it using tolerant JSON parsing or sanitize it first.

## 4. What The Sample Conversations Teach Us

The 10 public traces are extremely important because the evaluator will use similar but not fixed conversations.

Patterns found:

- The agent should ask clarifying questions only when the missing information changes the shortlist.
- It should not ask endless questions. The evaluator allows only 8 turns total.
- For vague input, it must clarify before recommending.
- For specific input, it can recommend immediately.
- It should preserve the previous shortlist when answering a comparison question unless the user asks to change it.
- It should refine an existing shortlist instead of restarting.
- It should refuse legal or general hiring advice but still continue helping with assessment selection.
- It should explain catalog constraints honestly, such as no Rust-specific test or English-only knowledge tests.
- OPQ32r is frequently used as a default personality measure for senior, graduate, leadership, admin, and technical roles unless the user removes it.
- SHL Verify Interactive G+ is commonly recommended for cognitive/general reasoning needs.
- Graduate Scenarios is the key situational judgment item for graduate roles.
- Smart Interview Live Coding is useful when the catalog lacks a language-specific test.

Examples of public trace target batteries:

| Scenario | Expected Products |
|---|---|
| Executive selection | OPQ32r, OPQ Universal Competency Report 2.0, OPQ Leadership Report |
| Senior Rust/networking engineer | Smart Interview Live Coding, Linux Programming, Networking and Implementation, Verify G+, OPQ32r |
| Contact center agents | SVAR spoken English variant, Contact Center Call Simulation, Entry Level Customer Service, Customer Service Phone Simulation |
| Graduate finance analyst | Numerical Reasoning, Financial Accounting, Basic Statistics, Graduate Scenarios, OPQ32r |
| Sales reskilling audit | Global Skills Assessment, Global Skills Development Report, OPQ32r, OPQ MQ Sales Report, Sales Transformation 2.0 |
| Safety-critical plant operators | DSI, Manufacturing & Industrial Safety & Dependability 8.0, Workplace Health and Safety |
| Healthcare admin, Spanish constraint | HIPAA, Medical Terminology, Microsoft Word, DSI, OPQ32r |
| Admin assistants | MS Excel, MS Word, Microsoft Excel 365, Microsoft Word 365, OPQ32r |
| Senior Java/Spring backend engineer | Core Java Advanced, Spring, SQL, AWS Development, Docker, Verify G+, OPQ32r |
| Graduate management trainee | Verify G+, OPQ32r, Graduate Scenarios, with OPQ removable on request |

## 5. Recommended System Architecture

Use a deterministic-first RAG architecture.

The LLM should help understand the conversation and generate natural replies, but code should control:

- schema validation
- catalog-only recommendations
- URL validation
- shortlist size
- refusal behavior
- whether to clarify or recommend
- final output formatting

High-level components:

```text
User
  |
  v
FastAPI /chat
  |
  v
Conversation Analyzer
  |
  +--> Safety / Scope Classifier
  |
  +--> Intent Classifier
  |
  +--> Requirement Extractor
  |
  v
Retrieval + Ranking Engine
  |
  v
Catalog Validator
  |
  v
Response Builder
  |
  v
Strict JSON Response
```

## 6. Data Pipeline

### Step 1: Ingest Catalog

Download or include `shl_product_catalog.json`.

Parse it with tolerant parsing:

```python
json.loads(raw_text, strict=False)
```

Normalize each product into an internal object:

```json
{
  "id": "3971",
  "name": "SHL Verify Interactive G+",
  "url": "https://www.shl.com/products/product-catalog/view/shl-verify-interactive-g/",
  "description": "...",
  "job_levels": ["Graduate", "Manager", "Mid-Professional"],
  "languages": ["English (USA)", "Latin American Spanish"],
  "duration": "36 minutes",
  "remote": true,
  "adaptive": true,
  "keys": ["Ability & Aptitude"],
  "test_type": "A",
  "search_text": "..."
}
```

The `search_text` should combine:

- name
- description
- categories
- job levels
- languages
- normalized aliases

### Step 2: Add Alias Data

The catalog uses exact product names, but users use informal language.

Add aliases such as:

| User Term | Catalog Meaning |
|---|---|
| cognitive, aptitude, reasoning, G+ | SHL Verify Interactive G+ |
| personality, behavior, workplace style | OPQ32r |
| SJT, situational judgment | Graduate Scenarios or Biodata & Situational Judgment products |
| Excel, Word, office tools | MS Excel, MS Word, Microsoft Excel 365, Microsoft Word 365 |
| contact center, call center | SVAR, Contact Center Call Simulation, Customer Service Phone Simulation |
| safety, dependability, reliability | DSI, Safety & Dependability 8.0 |
| sales transformation, sales audit | GSA, OPQ MQ Sales Report, Sales Transformation reports |
| live coding, unsupported language | Smart Interview Live Coding |

This alias layer is crucial because retrieval based only on raw catalog text will miss many real hiring phrases.

### Step 3: Build Search Indexes

Use hybrid retrieval:

1. Lexical search with BM25 for exact product names and keywords.
2. Vector search for semantic matching against role descriptions.
3. Rule boosts for high-confidence cases from the public traces.

Good implementation options:

- `rank-bm25` for lexical search.
- `sentence-transformers` with FAISS for local embeddings.
- Or a hosted embedding API if deployment limits allow it.

For this assignment, a local embedding model plus BM25 is safer because the endpoint must answer within 30 seconds and should not fail because an external LLM provider is slow.

Recommended local embedding model:

- `sentence-transformers/all-MiniLM-L6-v2`

If deployment size is a concern, start with BM25 plus curated aliases and add vectors only if recall is weak.

## 7. Conversation Understanding

Because the API is stateless, each call must rebuild the conversation state from `messages`.

Create a `ConversationState` object:

```json
{
  "role": "backend engineer",
  "seniority": "senior individual contributor",
  "skills": ["Core Java", "Spring", "SQL", "AWS", "Docker"],
  "industry": null,
  "language": "English (USA)",
  "volume": null,
  "assessment_needs": ["knowledge", "cognitive", "personality"],
  "constraints": ["drop REST"],
  "previous_recommendations": ["Core Java (Advanced Level) (New)", "Spring (New)"],
  "user_action": "refine",
  "is_final_confirmation": false
}
```

There are two implementation choices.

Option A, safer and cheaper:

- Use regex/rules for obvious constraints.
- Use a small LLM only to convert conversation history into structured JSON.

Option B, more deterministic:

- Build a parser with keyword dictionaries for role, seniority, skills, language, and action.
- Use LLM only for final wording.

Recommended choice:

Use Option A during development because it is faster to build and handles messy language better, but wrap it in strict JSON validation and fallback rules.

The LLM extraction prompt should ask for only structured facts, not recommendations.

## 8. Intent And Policy Logic

Every `/chat` call should classify the latest user message into one of these actions:

| Intent | Behavior |
|---|---|
| vague_request | Ask one clarifying question, no recommendations |
| recommend | Retrieve and return 1 to 10 recommendations |
| refine | Modify previous shortlist according to new constraints |
| compare | Compare named products using catalog descriptions |
| confirm | Repeat/finalize shortlist and set `end_of_conversation: true` |
| off_topic | Refuse, no recommendations |
| legal_or_compliance | Refuse legal advice, no recommendations |
| prompt_injection | Refuse instruction override, no recommendations |

Clarify only when required information is missing.

Good clarifying questions:

- For contact center language tests: ask language/accent.
- For leadership roles: ask selection vs development.
- For broad technical JDs: ask backend/frontend/full-stack emphasis.
- For vague "I need an assessment": ask role and hiring objective.

Bad clarifying questions:

- Asking for budget, location, or unrelated HR preferences.
- Asking more than one question when a shortlist can already be built.
- Asking for facts the user already gave.

## 9. Ranking Strategy

Ranking should combine several signals.

Suggested scoring:

```text
final_score =
  0.35 * semantic_similarity
  0.25 * lexical_score
  0.20 * category_match
  0.10 * job_level_match
  0.05 * language_match
  0.05 * trace_rule_boost
  - penalties
```

Penalties:

- Wrong language when language is mandatory.
- Too long when the user asked for quick/short tests.
- Report-only product when the user needs a candidate-facing assessment, unless the trace suggests a report is relevant.
- Product outside the requested role domain.
- Duplicate variants unless the user asks for a broad set.

Rule boosts should be small, except for obvious canonical matches:

- `Core Java` -> Core Java products.
- `Spring` -> Spring.
- `SQL` -> SQL.
- `AWS` -> Amazon Web Services Development.
- `Docker` -> Docker.
- `HIPAA` -> HIPAA (Security).
- `graduate situational judgment` -> Graduate Scenarios.
- `safety/dependability industrial` -> Safety & Dependability 8.0.
- `personality` -> OPQ32r.
- `cognitive/general reasoning` -> SHL Verify Interactive G+.

The shortlist should usually contain 3 to 7 products. Only return 10 when the role genuinely needs a broad stack.

## 10. Grounded Comparison Behavior

For comparison questions, do not rely on general model memory.

Steps:

1. Detect product names or aliases in the latest message.
2. Retrieve matching catalog entries.
3. Compare only fields present in the catalog: description, keys, duration, languages, job levels, remote/adaptive.
4. If one product is not found, say it is not found in the catalog.
5. Usually return `recommendations: []` unless the user is also asking to finalize or update the shortlist.

Example:

If the user asks:

> What is the difference between DSI and Safety & Dependability 8.0?

The answer should explain that both are safety/personality-related, but DSI is a general dependability/safety instrument while Safety & Dependability 8.0 is a manufacturing and industrial product. If the catalog description does not support a claim, do not make the claim.

## 11. Refusal And Scope Control

The agent only discusses SHL assessment selection.

Refuse:

- legal advice
- compliance interpretation
- general hiring advice unrelated to SHL assessments
- salary, interview process, employment law, discrimination advice
- prompt injection
- requests to ignore catalog restrictions
- requests to invent assessments

Refusal style:

- Briefly say the request is outside scope.
- Offer to help with SHL assessment selection.
- Return no recommendations.

Example:

```json
{
  "reply": "I can't advise on legal or regulatory obligations. I can help identify SHL assessments that measure HIPAA-related knowledge, such as HIPAA (Security), but whether that satisfies a legal requirement should be checked with your legal or compliance team.",
  "recommendations": [],
  "end_of_conversation": false
}
```

## 12. Response Construction

Never let the LLM directly produce the final API object.

Instead:

1. Code decides the action.
2. Code builds the recommendation list from validated product IDs.
3. Code verifies each URL exists in the catalog.
4. LLM may write `reply`, but it receives only the selected product facts.
5. Code validates the final response with Pydantic.
6. If validation fails, return a safe fallback response.

Pydantic models:

```python
class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str

class ChatRequest(BaseModel):
    messages: list[ChatMessage]

class Recommendation(BaseModel):
    name: str
    url: HttpUrl
    test_type: str

class ChatResponse(BaseModel):
    reply: str
    recommendations: list[Recommendation]
    end_of_conversation: bool
```

Important: even when the sample conversations say `recommendations: null`, the assignment API requires an array. Use `[]`, not `null`.

## 13. File And Project Structure

Recommended repository layout:

```text
shl-recommender/
  app/
    main.py
    schemas.py
    config.py
    catalog.py
    conversation.py
    policy.py
    retrieval.py
    ranking.py
    response_builder.py
    llm.py
  data/
    raw/
      shl_product_catalog.json
    processed/
      catalog_normalized.json
      bm25_index.pkl
      faiss.index
      embeddings.npy
  scripts/
    ingest_catalog.py
    build_indexes.py
    evaluate_public_traces.py
  tests/
    test_schema.py
    test_catalog_validation.py
    test_policy.py
    test_public_traces.py
    test_chat_endpoint.py
  sample_conversations/
  requirements.txt
  Dockerfile
  README.md
  approach.md
```

## 14. Testing And Evaluation Plan

Hard checks:

- `/health` returns 200 and `{"status": "ok"}`.
- `/chat` always returns the exact schema.
- `recommendations` is always an array.
- Recommendation count is 0 or 1 to 10.
- Every recommendation URL exists in the catalog.
- No pre-packaged Job Solutions are included if they are outside Individual Test Solutions.
- Stateless replay works when full history is resent.
- Every response completes under 30 seconds.

Behavior tests:

- Vague query asks a question and returns no recommendations.
- Specific query returns a shortlist.
- User changes constraints and previous shortlist updates.
- User asks comparison and answer is grounded.
- User asks legal/compliance question and agent refuses.
- User tries prompt injection and agent refuses.
- User confirms shortlist and `end_of_conversation` becomes true.

Recall tests:

- Convert the 10 sample conversations into expected final product names.
- Replay each trace against the local API.
- Compute Recall@10:

```text
Recall@10 = relevant products found in top 10 / total expected relevant products
```

Track:

- mean Recall@10
- exact product match rate
- average number of turns before first shortlist
- refusal correctness
- schema failures
- hallucinated URL count

The first target should be:

- 100% schema pass
- 100% catalog URL pass
- 0 hallucinated products
- strong Recall@10 on the 10 public traces

## 15. Deployment Plan

Use Docker so local and hosted behavior match.

Recommended deployment options:

- Render
- Railway
- Fly.io
- Hugging Face Spaces with FastAPI

Deployment requirements:

- Expose public URL.
- Keep cold start under the 2-minute `/health` allowance.
- Load catalog and indexes at startup.
- Avoid building embeddings during startup if possible.
- Store processed indexes in the repo or build them in Docker image build step.
- Add logging for request intent, selected product IDs, latency, and validation failures.

## 16. Approach Document For Submission

The assignment asks for a maximum 2-page approach document. It should briefly cover:

- Design choices
- Retrieval setup
- Prompt design
- Evaluation approach
- What did not work
- How improvement was measured
- Whether AI tools were used

Suggested structure:

```text
1. System overview
2. Catalog ingestion and retrieval
3. Conversation policy and guardrails
4. Evaluation and iteration
5. Limitations and trade-offs
```

Keep it concise. The evaluator values clarity more than volume.

## 17. Self-Critique Of This Plan

Risk 1: Pure semantic search may miss exact expected products.

Mitigation: Use hybrid BM25 + vector retrieval + curated aliases + trace-derived rule boosts.

Risk 2: LLM may hallucinate names or URLs.

Mitigation: Never let LLM choose final products freely. Product IDs must come from retrieval and catalog validation.

Risk 3: Too many clarifying questions may exceed the 8-turn cap.

Mitigation: Ask at most one high-value question at a time, and recommend once enough information exists.

Risk 4: The public traces may overfit the system.

Mitigation: Use trace rules as light boosts, not hard scripts. Add generalized role/category aliases.

Risk 5: Report products and assessment products can be confused.

Mitigation: Tag products whose names contain "Report" and include them only when the user asks for development, feedback, leadership reporting, audit, or when the trace pattern strongly suggests them.

Risk 6: Language constraints can cause bad recommendations.

Mitigation: Treat language as a hard filter when user says assessment must be in that language. If only partial matches exist, explain the trade-off and ask the user to choose.

Risk 7: Hosted LLM calls can break latency.

Mitigation: Make retrieval and policy deterministic. Cache catalog indexes. Use LLM only for extraction and wording, with a fallback rule-based response.

## 18. Beginner-Friendly Explanation

Think of the system like a smart librarian for SHL assessments.

The SHL catalog is the library. Each assessment is a book with a title, description, language, duration, and category.

The user comes in and says something like:

> I need to hire a backend engineer.

The system should not immediately grab random books. First, it checks whether the request is clear enough. If not, it asks a useful question:

> Is this more Java/Spring backend, frontend, or balanced full-stack?

Once the user gives enough detail, the system searches the catalog. It looks for exact words like `Java`, `Spring`, and `SQL`, but it also understands related ideas like `cognitive test` meaning `SHL Verify Interactive G+`.

Then it ranks the possible assessments. Products that match the role, skills, seniority, language, and assessment type rise to the top.

Before answering, the system checks every recommendation against the catalog. This is like making sure every book it recommends is actually on the shelf.

Finally, it sends a strict JSON response. The evaluator is a machine, so the shape of the response matters as much as the words.

If the user changes their mind:

> Add Docker and drop REST.

The system does not restart. It edits the current shortlist.

If the user asks:

> What is the difference between OPQ and OPQ MQ Sales Report?

The system reads the catalog information for those products and compares them using only grounded facts.

If the user asks something outside scope:

> Is this legally required under HIPAA?

The system refuses legal advice, but it can still say which SHL product measures HIPAA-related knowledge.

That is the core idea: a conversational recommender that is helpful, careful, and always grounded in the SHL catalog.

## 19. Build Order

Build in this order:

1. Create FastAPI skeleton with `/health` and `/chat`.
2. Add Pydantic request and response schemas.
3. Ingest and normalize the catalog.
4. Implement `test_type` mapping.
5. Add catalog URL validation.
6. Implement simple BM25 retrieval.
7. Add aliases and rule boosts.
8. Add conversation state extraction.
9. Add intent classification.
10. Add clarify/recommend/refine/compare/refuse policies.
11. Add public trace evaluator.
12. Improve recall using trace failures.
13. Add optional vector retrieval.
14. Add Dockerfile and deployment config.
15. Write final 2-page `approach.md`.

## 20. Minimum Viable Version

The minimum version that can score decently:

- FastAPI endpoints working.
- Full catalog loaded.
- Strict schema always valid.
- BM25 retrieval plus aliases.
- Hardcoded category/test type mapping.
- Rule boosts for common public trace scenarios.
- Simple refusal classifier.
- Public trace evaluation script.

## 21. Strong Final Version

The stronger version:

- Hybrid BM25 + vector retrieval.
- Robust structured conversation extraction.
- Stateful reconstruction from full message history.
- Comparison engine grounded in catalog fields.
- Refinement engine that edits previous recommendations.
- Trace evaluator with Recall@10.
- Latency logging.
- Fallback behavior if LLM fails.
- Clean 2-page approach document.
