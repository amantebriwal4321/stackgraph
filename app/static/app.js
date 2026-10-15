const logEl = document.querySelector("#log");
const evidenceEl = document.querySelector("#evidence");
const pillsEl = document.querySelector("#pills");
const form = document.querySelector("#ask");
const questionEl = document.querySelector("#question");
const userEl = document.querySelector("#user");
const sendBtn = document.querySelector("#send");
const scoutBtn = document.querySelector("#scout");
const examplesEl = document.querySelector("#examples");

const sessionId = sessionStorage.getItem("stackgraph-session") || ("s" + Math.random().toString(16).slice(2, 14));
sessionStorage.setItem("stackgraph-session", sessionId);

function pill(text, bad) {
  const span = document.createElement("span");
  span.className = "pill" + (bad ? " bad" : "");
  span.textContent = text;
  return span;
}

function renderHealth(data) {
  pillsEl.replaceChildren();
  if (!data.ok) {
    pillsEl.append(pill("FalkorDB down", true));
    return;
  }
  const counts = data.counts || {};
  pillsEl.append(pill("FalkorDB " + data.graph));
  pillsEl.append(pill(data.mode === "llm" ? "model " + (data.model || "") : "rule router"));
  pillsEl.append(pill((counts.tools || 0) + " tools"));
  pillsEl.append(pill((counts.depends_on || 0) + " depends"));
  if (data.scout && data.scout.ts) {
    pillsEl.append(pill("scout " + data.scout.signals_written + " signals"));
  }
}

async function loadHealth() {
  const response = await fetch("/api/health");
  const data = await response.json();
  if (!response.ok) {
    renderHealth({ ok: false });
    showError(data.detail || "FalkorDB is not reachable. The app has no other database.");
    return;
  }
  renderHealth(data);
}

function showError(message) {
  const node = document.createElement("div");
  node.className = "error";
  node.textContent = typeof message === "string" ? message : JSON.stringify(message);
  evidenceEl.prepend(node);
}

function addBubble(role, text, meta) {
  const article = document.createElement("article");
  article.className = "bubble " + role;
  const p = document.createElement("p");
  p.textContent = text;
  article.append(p);
  if (meta) {
    const small = document.createElement("span");
    small.className = "meta";
    small.textContent = meta;
    article.append(small);
  }
  logEl.append(article);
  logEl.scrollTop = logEl.scrollHeight;
}

function nodeClass(labels) {
  const label = (labels || [])[0] || "";
  if (label === "Signal") return "node signal";
  if (label === "User") return "node user";
  if (label === "Maintainer") return "node maintainer";
  return "node";
}

function renderPaths(paths) {
  if (!paths || !paths.length) return;
  paths.slice(0, 8).forEach((path) => {
    const wrap = document.createElement("div");
    const title = document.createElement("div");
    title.className = "muted";
    title.textContent = path.label || "Path";
    wrap.append(title);
    const nodes = path.nodes || [];
    const edges = path.edges || [];
    if (!edges.length && nodes.length > 1 && nodes[0].properties && nodes[0].properties.score !== undefined) {
      const rank = document.createElement("div");
      rank.className = "rank";
      const scores = nodes.map((node) => Number(node.properties.score) || 0);
      const max = Math.max(...scores, 0.0001);
      nodes.forEach((node, index) => {
        const row = document.createElement("div");
        const n = document.createElement("span");
        n.textContent = String(index + 1);
        const bar = document.createElement("span");
        bar.className = "bar";
        bar.style.width = Math.max(8, (scores[index] / max) * 100) + "%";
        const name = document.createElement("span");
        name.textContent = node.name + "  " + scores[index];
        row.append(n, bar, name);
        rank.append(row);
      });
      wrap.append(rank);
    } else {
      const line = document.createElement("div");
      line.className = "path";
      nodes.forEach((node, index) => {
        const chip = document.createElement("span");
        chip.className = nodeClass(node.labels);
        chip.textContent = node.name || node.id;
        const small = document.createElement("small");
        small.textContent = (node.labels || []).join(", ") || "node";
        chip.append(small);
        line.append(chip);
        if (edges[index]) {
          const edge = document.createElement("span");
          edge.className = "edge";
          edge.textContent = edges[index].type || "edge";
          line.append(edge);
        }
      });
      wrap.append(line);
    }
    evidenceEl.append(wrap);
  });
}

function renderCypher(calls) {
  (calls || []).slice(0, 6).forEach((call) => {
    const head = document.createElement("div");
    head.className = "cypher-head";
    const label = document.createElement("span");
    label.textContent = (call.graph || "graph") + (call.error ? "  failed" : "");
    const button = document.createElement("button");
    button.type = "button";
    button.className = "copy";
    button.textContent = "Copy";
    const text = call.rendered || call.query || "";
    button.addEventListener("click", () => navigator.clipboard.writeText(text));
    head.append(label, button);
    const pre = document.createElement("pre");
    pre.className = "cypher";
    pre.textContent = text;
    evidenceEl.append(head, pre);
  });
}

function showEvidence(data) {
  evidenceEl.replaceChildren();
  renderPaths(data.paths || []);
  renderCypher(data.cypher || []);
}

async function ask(question) {
  sendBtn.disabled = true;
  sendBtn.textContent = "Reading the graph";
  addBubble("user", question);
  try {
    const response = await fetch("/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question,
        user_id: userEl.value || "demo",
        session_id: sessionId,
      }),
    });
    const data = await response.json();
    if (!response.ok) {
      showError(data.detail || "The graph query failed.");
      addBubble("agent", "FalkorDB did not answer. There is no fallback store.");
      return;
    }
    const meta = [data.mode, data.intent, (data.agents || []).join(" + "), data.memory_graph].filter(Boolean).join(" · ");
    addBubble("agent", data.answer || "No answer text.", meta);
    showEvidence(data);
  } catch (error) {
    showError(error.message);
  } finally {
    sendBtn.disabled = false;
    sendBtn.textContent = "Ask the graph";
  }
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  const question = questionEl.value.trim();
  if (!question) return;
  ask(question);
});

questionEl.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    form.requestSubmit();
  }
});

scoutBtn.addEventListener("click", async () => {
  scoutBtn.disabled = true;
  try {
    const response = await fetch("/api/scout", { method: "POST" });
    const data = await response.json();
    if (!response.ok) {
      showError(data.detail || "Scout failed.");
      return;
    }
    addBubble("agent", "Scout wrote " + data.signals_written + " blast radius signals at " + data.ts + ".", "scout");
    showEvidence({ paths: [], cypher: data.cypher });
    loadHealth();
  } finally {
    scoutBtn.disabled = false;
  }
});

async function loadExamples() {
  const response = await fetch("/api/examples");
  const data = await response.json();
  (data.examples || []).forEach((text) => {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = text;
    button.addEventListener("click", () => {
      questionEl.value = text;
      ask(text);
    });
    examplesEl.append(button);
  });
}

loadHealth();
loadExamples();
