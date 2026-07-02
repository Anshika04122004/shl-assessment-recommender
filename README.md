# SHL Conversational Assessment Recommender

FastAPI implementation for the SHL AI Intern take-home assignment.

## What You Submit

The assignment form asks for two things:

1. A public API endpoint URL for the deployed FastAPI service.
2. The approach document, `approach.md`, maximum 2 pages.

The local URL `http://127.0.0.1:8000` is only for your machine. It is not a valid submission URL because SHL's evaluator cannot reach it. Deploy this project to Render, Railway, Fly.io, Hugging Face Spaces, or another public host, then submit the public base URL.

Required deployed endpoints:

- `GET <PUBLIC_BASE_URL>/health`
- `POST <PUBLIC_BASE_URL>/chat`

Optional browser-friendly endpoints:

- `GET <PUBLIC_BASE_URL>/`
- `GET <PUBLIC_BASE_URL>/docs`

## Run Locally

```powershell
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Health check:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

Chat:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/chat `
  -Method Post `
  -ContentType "application/json" `
  -Body '{"messages":[{"role":"user","content":"We run a graduate management trainee scheme. We need cognitive, personality, and situational judgement."}]}'
```

## Test

```powershell
python -m pytest -q
python scripts/evaluate_public_traces.py
```

Current verification results:

- Unit tests: `8 passed`
- Public sample replay: `Mean Recall@10=1.00`

## Simple Walkthrough

1. The service starts and loads `shl_product_catalog.json`.
2. `GET /health` returns `{"status":"ok"}` for readiness checks.
3. `POST /chat` receives the full conversation history in `messages`.
4. The app reconstructs state from the messages because the API is stateless.
5. The policy layer decides whether to clarify, recommend, refine, compare, confirm, or refuse.
6. The retrieval layer selects products only from the SHL catalog.
7. The validator ensures every returned URL exists in the catalog.
8. The response builder returns the exact required schema: `reply`, `recommendations`, and `end_of_conversation`.

## Deployment Notes

The included `Dockerfile` is the easiest deployment path. On most platforms:

1. Push this folder to a GitHub repository.
2. Create a new web service.
3. Select Docker deployment.
4. Expose port `8000`.
5. After deployment, test `/health` and `/chat`.
6. Submit the public base URL and `approach.md`.

## Implementation Notes

- The API is stateless; every call reconstructs state from the `messages` array.
- `/health` is lightweight and does not perform network calls.
- Recommendations are always validated against `shl_product_catalog.json`.
- The response schema always uses `recommendations: []` when clarifying, refusing, or comparing without recommitting.
- Turn count is `len(messages)`; at 7 or more messages, the agent commits to the best available shortlist instead of asking more clarifying questions.
- Missing product fields such as duration or languages are tolerated because the API response only requires `name`, `url`, and `test_type`.
- Prompt-injection and legal/compliance requests are refused before retrieval.
- The current implementation is deterministic and does not require a Groq/OpenAI key.
