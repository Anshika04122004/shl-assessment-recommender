# Approach

I built a deterministic-first FastAPI recommender over the provided SHL catalog. The core design goal is to pass the evaluator's hard checks first: strict schema compliance, stateless operation, catalog-only recommendations, no hallucinated URLs, and reliable behavior under the 8-turn and 30-second limits.

The catalog is loaded from `shl_product_catalog.json` at startup using tolerant JSON parsing because the provided file contains raw control characters. Each product is normalized into an internal object with name, URL, description, job levels, languages, duration, keys, and a computed `test_type`. Multi-key products return comma-separated codes such as `K,S` or `P,C`. The loader validates required fields and ensures the catalog is not unexpectedly small.

Retrieval is currently BM25-like lexical scoring plus curated aliases and rule boosts derived from the public traces. I intentionally avoided a vector model in the first implementation to keep cold start and per-call latency low. The system has explicit associations for high-value products such as OPQ32r for personality, SHL Verify Interactive G+ for cognitive ability, Graduate Scenarios for graduate SJT, Smart Interview Live Coding for unsupported programming languages, DSI for dependability/safety, and SVAR variants for contact-center language screening.

Conversation state is reconstructed on every request from the full `messages` array. Because previous structured recommendations may not be resent by the evaluator, the assistant reply includes a compact `Shortlist:` line with product names. Later calls parse those names from assistant messages to support refinement and confirmation without server-side memory.

Policy logic classifies each request into clarify, recommend, refine, compare, confirm, refuse, or turn-limit commit. Vague first turns ask a clarifying question. Specific turns recommend immediately. Refinements apply add/drop/remove changes to the previous shortlist. Comparisons use only catalog data for the named products and return no recommendations unless the user is also asking to update the shortlist. Legal/compliance and prompt-injection attempts are refused before retrieval.

Evaluation uses unit tests for schema, URL validation, vague-query behavior, prompt-injection refusal, hybrid language handling, refinement, comparison, and final confirmation. A public-trace replay script computes Recall@10 over the 10 sample scenarios and prints missing products for iteration.

What did not work: a pure semantic/LLM-first plan would be riskier for this assignment because it can hallucinate products, miss exact catalog names, or exceed latency under cold starts. The safer first version uses code-controlled product selection and keeps LLM use optional for future wording or extraction improvements.

AI tools used: I used Codex as an agentic coding assistant to inspect the assignment, extract requirements, scaffold the FastAPI service, write tests, and iterate on failures. Final product selection, schema validation, and catalog checks are implemented in code rather than delegated to an LLM at runtime.
