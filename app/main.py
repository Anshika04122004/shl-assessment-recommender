from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from app.recommender import chat
from app.schemas import ChatRequest, ChatResponse


app = FastAPI(title="SHL Conversational Assessment Recommender")


@app.get("/", response_class=HTMLResponse)
def root() -> str:
    return """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>SHL Assessment Recommender</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f6f7fb;
      --panel: #ffffff;
      --text: #1f2937;
      --muted: #667085;
      --line: #d9dee8;
      --accent: #2563eb;
      --accent-dark: #1d4ed8;
      --assistant: #eef4ff;
      --user: #ecfdf3;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: var(--bg);
      color: var(--text);
    }
    main {
      width: min(1120px, calc(100vw - 32px));
      margin: 24px auto;
      display: grid;
      grid-template-columns: minmax(0, 1fr) 360px;
      gap: 16px;
    }
    header {
      width: min(1120px, calc(100vw - 32px));
      margin: 24px auto 0;
      display: flex;
      justify-content: space-between;
      align-items: end;
      gap: 16px;
    }
    h1 { margin: 0; font-size: 24px; line-height: 1.2; }
    .links { display: flex; gap: 8px; flex-wrap: wrap; }
    .links a {
      color: var(--accent);
      text-decoration: none;
      font-weight: 600;
      font-size: 14px;
    }
    .surface {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      min-height: 0;
    }
    #chat {
      height: calc(100vh - 220px);
      min-height: 420px;
      overflow: auto;
      padding: 16px;
      display: flex;
      flex-direction: column;
      gap: 10px;
    }
    .message {
      max-width: 82%;
      padding: 10px 12px;
      border-radius: 8px;
      white-space: pre-wrap;
      line-height: 1.45;
      font-size: 15px;
    }
    .user { align-self: flex-end; background: var(--user); }
    .assistant { align-self: flex-start; background: var(--assistant); }
    form {
      display: flex;
      gap: 8px;
      padding: 12px;
      border-top: 1px solid var(--line);
      background: var(--panel);
      border-radius: 0 0 8px 8px;
    }
    textarea {
      flex: 1;
      min-height: 48px;
      max-height: 140px;
      resize: vertical;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 10px;
      font: inherit;
    }
    button {
      border: 0;
      border-radius: 8px;
      padding: 0 16px;
      min-width: 88px;
      background: var(--accent);
      color: #fff;
      font-weight: 700;
      cursor: pointer;
    }
    button:hover { background: var(--accent-dark); }
    button:disabled { opacity: 0.55; cursor: not-allowed; }
    aside {
      padding: 14px;
      height: calc(100vh - 156px);
      min-height: 520px;
      overflow: auto;
    }
    h2 { margin: 0 0 12px; font-size: 16px; }
    table { width: 100%; border-collapse: collapse; font-size: 13px; }
    th, td { border-bottom: 1px solid var(--line); text-align: left; padding: 8px 4px; vertical-align: top; }
    th { color: var(--muted); font-size: 12px; }
    td a { color: var(--accent); font-weight: 600; text-decoration: none; }
    .empty { color: var(--muted); font-size: 14px; line-height: 1.5; }
    .status { color: var(--muted); font-size: 13px; margin-top: 8px; }
    @media (max-width: 860px) {
      main { grid-template-columns: 1fr; }
      aside { height: auto; min-height: 220px; }
      #chat { height: 58vh; }
      header { align-items: start; flex-direction: column; }
      .message { max-width: 94%; }
    }
  </style>
</head>
<body>
  <header>
    <div>
      <h1>SHL Assessment Recommender</h1>
      <div class="status">API: <code>/health</code> ready, <code>/chat</code> active</div>
    </div>
    <nav class="links">
      <a href="/docs">Swagger Docs</a>
      <a href="/health">Health</a>
    </nav>
  </header>
  <main>
    <section class="surface">
      <div id="chat"></div>
      <form id="form">
        <textarea id="input" placeholder="Describe the role or paste a job description..."></textarea>
        <button id="send" type="submit">Send</button>
      </form>
    </section>
    <aside class="surface">
      <h2>Recommendations</h2>
      <div id="recommendations" class="empty">No shortlist yet.</div>
      <div id="done" class="status"></div>
    </aside>
  </main>
  <script>
    const messages = [];
    const chat = document.getElementById("chat");
    const form = document.getElementById("form");
    const input = document.getElementById("input");
    const send = document.getElementById("send");
    const recs = document.getElementById("recommendations");
    const done = document.getElementById("done");

    function addMessage(role, content) {
      const div = document.createElement("div");
      div.className = "message " + role;
      div.textContent = content;
      chat.appendChild(div);
      chat.scrollTop = chat.scrollHeight;
    }

    function renderRecommendations(items) {
      if (!items.length) {
        recs.className = "empty";
        recs.textContent = "No shortlist yet.";
        return;
      }
      recs.className = "";
      recs.innerHTML = `
        <table>
          <thead><tr><th>Name</th><th>Type</th></tr></thead>
          <tbody>
            ${items.map(item => `
              <tr>
                <td><a href="${item.url}" target="_blank" rel="noreferrer">${item.name}</a></td>
                <td>${item.test_type}</td>
              </tr>
            `).join("")}
          </tbody>
        </table>
      `;
    }

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const content = input.value.trim();
      if (!content) return;
      input.value = "";
      send.disabled = true;
      messages.push({ role: "user", content });
      addMessage("user", content);

      try {
        const response = await fetch("/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ messages })
        });
        const data = await response.json();
        messages.push({ role: "assistant", content: data.reply });
        addMessage("assistant", data.reply);
        renderRecommendations(data.recommendations || []);
        done.textContent = data.end_of_conversation ? "Conversation marked complete." : "";
      } catch (error) {
        addMessage("assistant", "Request failed. Check the server console and try again.");
      } finally {
        send.disabled = false;
        input.focus();
      }
    });

    addMessage("assistant", "Tell me what role you are hiring for and what you need to measure.");
  </script>
</body>
</html>
    """


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat_endpoint(request: ChatRequest) -> ChatResponse:
    reply, recommendations, end_of_conversation = chat(request.messages)
    return ChatResponse(
        reply=reply,
        recommendations=recommendations,
        end_of_conversation=end_of_conversation,
    )
