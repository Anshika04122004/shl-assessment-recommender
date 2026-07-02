# Submission Checklist

## What SHL Requires

Submit these two items in the assignment form:

1. Public API endpoint URL
2. Approach document, maximum 2 pages

## Public API Endpoint URL

Do not submit:

```text
http://127.0.0.1:8000
```

That is only your local machine.

Submit a deployed public base URL, for example:

```text
https://your-shl-recommender.onrender.com
```

Before submitting, verify:

```text
GET  https://your-shl-recommender.onrender.com/health
POST https://your-shl-recommender.onrender.com/chat
```

Expected `/health` response:

```json
{"status":"ok"}
```

Expected `/chat` response shape:

```json
{
  "reply": "...",
  "recommendations": [],
  "end_of_conversation": false
}
```

## Approach Document

Submit:

```text
approach.md
```

It covers:

- design choices
- retrieval setup
- prompt/runtime design
- evaluation approach
- what did not work
- how improvement was measured
- AI tools used

## Files In This Package

Required to run/deploy:

- `app/`
- `shl_product_catalog.json`
- `requirements.txt`
- `Dockerfile`
- `README.md`
- `approach.md`

Useful verification files:

- `tests/`
- `scripts/evaluate_public_traces.py`

Background/reference files:

- `SHL_Assessment_Recommender_Pipeline_Plan.md`
- `assignment_extracted.txt`

## Final Pre-Submission Checks

Run locally:

```powershell
python -m pytest -q
python scripts/evaluate_public_traces.py
```

Then test deployed URL:

```powershell
Invoke-RestMethod https://YOUR_PUBLIC_URL/health
```

And test deployed chat:

```powershell
$body = @{ messages = @(@{ role = "user"; content = "We run a graduate management trainee scheme. We need cognitive, personality, and situational judgement." }) } | ConvertTo-Json -Depth 5
Invoke-RestMethod https://YOUR_PUBLIC_URL/chat -Method Post -ContentType "application/json" -Body $body
```

