const $ = (s) => document.querySelector(s);
const esc = (t) => String(t).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const post = (url, body) => fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }).then((r) => r.json());

/* ---- tabs ---- */
function openTab(name) {
  document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("active", t.dataset.tab === name));
  document.querySelectorAll(".panel").forEach((p) => p.classList.toggle("active", p.id === name));
  if (name === "train") loadModelInfo();
}
document.querySelectorAll(".tab").forEach((t) => (t.onclick = () => openTab(t.dataset.tab)));

/* ---- chat ---- */
function addBubble(text, who, extra = "") {
  const d = document.createElement("div");
  d.className = "bubble " + who;
  d.innerHTML = esc(text) + extra;
  $("#log").appendChild(d);
  $("#log").scrollTop = $("#log").scrollHeight;
  return d;
}
const ACTIONS = { resume: ["Open resume check", "resume"], eligibility: ["Open eligibility checker", "elig"], quiz: ["Start mock quiz", "quiz"] };
async function send(text) {
  text = (text || $("#msg").value).trim();
  if (!text) return;
  $("#msg").value = "";
  addBubble(text, "me");
  const typing = addBubble("...", "bot");
  try {
    const r = await post("/api/chat", { message: text });
    const meta = r.intent ? `<span class="meta">intent: ${esc(r.intent)} | confidence: ${Math.round(r.confidence * 100)}%</span>` : "";
    const a = r.action && ACTIONS[r.action] ? `<br><button class="go" data-go="${ACTIONS[r.action][1]}">${ACTIONS[r.action][0]}</button>` : "";
    typing.innerHTML = esc(r.reply) + a + meta;
  } catch (e) { typing.textContent = "Server not reachable. Is app.py running?"; }
  $("#log").scrollTop = $("#log").scrollHeight;
}
$("#send").onclick = () => send();
$("#msg").addEventListener("keydown", (e) => e.key === "Enter" && send());
$("#chips").onclick = (e) => e.target.tagName === "BUTTON" && send(e.target.textContent);
$("#log").onclick = (e) => e.target.dataset.go && openTab(e.target.dataset.go);
addBubble("Hello! I'm your Campus Placement Assistant. Ask a question, or use the tabs on the left for resume check, eligibility and a mock quiz.", "bot");

/* ---- resume analyser ---- */
$("#rgo").onclick = async () => {
  const fd = new FormData();
  fd.append("role", $("#role").value);
  fd.append("text", $("#rtext").value);
  if ($("#rfile").files[0]) fd.append("file", $("#rfile").files[0]);
  const r = await fetch("/api/resume", { method: "POST", body: fd }).then((x) => x.json());
  if (r.error) return ($("#rout").innerHTML = `<div class="card"><span class="tag no">${esc(r.error)}</span></div>`);
  const secs = Object.entries(r.sections).map(([k, v]) => `<span class="tag ${v ? "ok" : "no"}">${esc(k)}</span>`).join("");
  $("#rout").innerHTML = `
    <div class="card score"><div class="ring" style="--p:${r.score}"><span>${r.score}</span></div>
      <div><h3>${esc(r.grade)} for ${esc(r.role)}</h3><p class="hint">${r.word_count} words | ${r.found_skills.length} of ${r.found_skills.length + r.missing_skills.length} role skills found</p></div></div>
    <div class="card"><h3>Skills found</h3><div class="tags">${r.found_skills.map((s) => `<span class="tag ok">${esc(s)}</span>`).join("") || "None"}</div>
      <h3>Skills missing</h3><div class="tags">${r.missing_skills.map((s) => `<span class="tag no">${esc(s)}</span>`).join("") || "None"}</div>
      <h3>Sections</h3><div class="tags">${secs}</div></div>
    <div class="card"><h3>How to improve</h3><ul class="list">${r.tips.map((t) => `<li>${esc(t)}</li>`).join("") || "<li>Looks strong. Tailor it to each company.</li>"}</ul></div>`;
};

/* ---- eligibility ---- */
$("#ego").onclick = async () => {
  const r = await post("/api/eligibility", {
    cgpa: $("#cgpa").value, tenth: $("#tenth").value, twelfth: $("#twelfth").value, backlogs: $("#backlogs").value, branch: $("#branch").value,
  });
  if (r.error) return ($("#eout").innerHTML = `<div class="card"><span class="tag no">${esc(r.error)}</span></div>`);
  $("#eout").innerHTML = `<div class="card"><h3>You are eligible for ${r.eligible_count} of ${r.total} companies</h3>` +
    r.results.map((c) => `<div class="co"><div><b>${esc(c.company)}</b><small>${esc(c.package)} | ${esc(c.rounds)}</small>
      ${c.reasons.map((x) => `<small style="color:var(--red)">${esc(x)}</small>`).join("")}</div>
      <span class="pill ${c.eligible ? "ok" : "no"}">${c.eligible ? "Eligible" : "Not eligible"}</span></div>`).join("") +
    `<p class="hint">Criteria are sample values from data/companies.json. Edit them to match your college.</p></div>`;
};

/* ---- quiz ---- */
let quizQs = [], picks = {};
$("#qgo").onclick = async () => {
  const r = await fetch("/api/quiz?n=5&category=" + encodeURIComponent($("#qcat").value)).then((x) => x.json());
  quizQs = r.questions; picks = {};
  $("#qout").innerHTML = quizQs.map((q, i) => `<div class="card"><h3>${i + 1}. ${esc(q.q)}</h3><p class="hint">${esc(q.category)}</p>
    ${q.options.map((o, j) => `<button class="opt" data-q="${q.id}" data-o="${j}">${esc(o)}</button>`).join("")}</div>`).join("") +
    `<button class="primary" id="qsub">Submit answers</button>`;
  $("#qsub").onclick = submitQuiz;
};
$("#qout").onclick = (e) => {
  if (!e.target.classList.contains("opt")) return;
  e.target.parentElement.querySelectorAll(".opt").forEach((b) => b.classList.remove("sel"));
  e.target.classList.add("sel");
  picks[e.target.dataset.q] = +e.target.dataset.o;
};
async function submitQuiz() {
  quizQs.forEach((q) => { if (!(q.id in picks)) picks[q.id] = -1; });
  const r = await post("/api/quiz/submit", { answers: picks });
  $("#qout").innerHTML = `<div class="card score"><div class="ring" style="--p:${r.percent}"><span>${r.percent}%</span></div>
    <div><h3>${r.correct} of ${r.total} correct</h3><p class="hint">${esc(r.message)}</p></div></div>` +
    r.review.map((x) => `<div class="card rv ${x.is_correct ? "" : "bad"}"><b>${esc(x.q)}</b><br>Your answer: ${esc(x.your)}<br>Correct: ${esc(x.correct)}<br><span class="hint">${esc(x.explain)}</span></div>`).join("") +
    `<button class="primary" id="qgo2">Try another round</button>`;
  $("#qgo2").onclick = () => $("#qgo").click();
}

/* ---- train the model ---- */
async function loadModelInfo() {
  const m = await fetch("/api/model-info").then((x) => x.json());
  $("#minfo").innerHTML = [["Training sentences", m.samples], ["Intents", m.intents], ["Test accuracy", Math.round(m.test_accuracy * 100) + "%"], ["CV accuracy", Math.round(m.cv_accuracy * 100) + "%"], ["Last trained", m.trained_at]]
    .map(([k, v]) => `<div class="stat"><b>${esc(v)}</b><span>${k}</span></div>`).join("") + `<p class="hint" style="flex-basis:100%">${esc(m.algorithm)}</p>`;
  $("#intentlist").innerHTML = (m.intents_list || []).map((i) => `<option value="${esc(i)}">`).join("");
  $("#unk").innerHTML = (m.recent_unknown || []).reverse().map((u) => `<li data-m="${esc(u.message)}">${esc(u.message)} <span class="hint">(guess: ${esc(u.best_guess)})</span></li>`).join("") || "<li class='hint'>Nothing yet.</li>";
}
$("#unk").onclick = (e) => { const li = e.target.closest("li"); if (li && li.dataset.m) $("#tsent").value = li.dataset.m; };
$("#tgo").onclick = async () => {
  $("#tmsg").textContent = "Training...";
  const r = await post("/api/teach", { sentence: $("#tsent").value, intent: $("#tint").value, answer: $("#tans").value, key: $("#tkey").value });
  $("#tmsg").textContent = r.error ? r.error : `Done. Retrained on ${r.metrics.samples} sentences (test accuracy ${Math.round(r.metrics.test_accuracy * 100)}%).`;
  if (r.ok) { $("#tsent").value = ""; loadModelInfo(); }
};
