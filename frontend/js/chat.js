// ── Chat UI ───────────────────────────────────────────────────────────────────
const SESSION_ID    = "demo-session";
const chatWindow    = document.getElementById("chat-window");
const chatInput     = document.getElementById("chat-input");
const sendBtn       = document.getElementById("send-btn");
const micBtn        = document.getElementById("mic-btn");
const suggestionsEl = document.getElementById("suggestions");
const exportBtn     = document.getElementById("export-pdf-btn");
const langSelect    = document.getElementById("lang-select");

// ── Message rendering ─────────────────────────────────────────────────────────
function appendMessage(role, text, evidence, data, intent) {
  const msg = document.createElement("div");
  msg.className = `msg ${role}`;

  if (role === "assistant") {
    const meta = document.createElement("div");
    meta.className = "msg-meta";
    meta.innerHTML = `<span class="msg-sender">Kavach</span>`;
    if (intent && intent !== "general_query") {
      const badge = document.createElement("span");
      badge.className = "intent-badge";
      badge.textContent = intent.replace(/_/g, " ");
      meta.appendChild(badge);
    }
    msg.appendChild(meta);
  }

  const textEl = document.createElement("div");
  textEl.textContent = text;
  msg.appendChild(textEl);

  if (evidence) {
    const ev = document.createElement("div");
    ev.className = "evidence";
    ev.innerHTML = `<span class="evidence-icon">🔍</span> ${evidence}`;
    msg.appendChild(ev);
  }

  if (data) {
    const block = renderDataBlock(data);
    if (block) msg.appendChild(block);
  }

  chatWindow.appendChild(msg);
  chatWindow.scrollTop = chatWindow.scrollHeight;
}

function showTypingIndicator() {
  const el = document.createElement("div");
  el.className = "typing-indicator";
  el.id = "typing-indicator";
  el.innerHTML = "<span></span><span></span><span></span>";
  chatWindow.appendChild(el);
  chatWindow.scrollTop = chatWindow.scrollHeight;
}

function removeTypingIndicator() {
  const el = document.getElementById("typing-indicator");
  if (el) el.remove();
}

// ── Data block renderer ───────────────────────────────────────────────────────
function renderDataBlock(data) {
  const wrap = document.createElement("div");
  wrap.className = "data-block";

  if (data.hotspots) {
    wrap.appendChild(makeTable(
      ["Area", "City", "Cases"],
      data.hotspots.map(h => [h.area_name, h.city, h.case_count])
    ));
    return wrap;
  }

  if (data.repeat_offenders) {
    wrap.appendChild(makeTable(
      ["ID", "Name", "Age", "Prior Offenses", "Risk"],
      data.repeat_offenders.map(r => [r.accused_id, r.name, r.age, r.prior_offenses, r.risk_score])
    ));
    return wrap;
  }

  if (data.case_history) {
    wrap.appendChild(makeTable(
      ["FIR", "Crime Type", "Date", "Status", "Role"],
      data.case_history.map(c => [c.fir_id, c.crime_type, c.date_filed, c.status, c.role])
    ));
    if (data.risk_factors && data.risk_factors.length) {
      const ul = document.createElement("ul");
      ul.style.cssText = "margin:8px 0 0 14px;font-size:12px;color:var(--danger);";
      data.risk_factors.forEach(f => {
        const li = document.createElement("li");
        li.textContent = f;
        ul.appendChild(li);
      });
      wrap.appendChild(ul);
    }
    return wrap;
  }

  if (data.alerts) {
    const ul = document.createElement("ul");
    ul.style.cssText = "margin:4px 0 0 14px;font-size:12px;";
    data.alerts.forEach(a => {
      const li = document.createElement("li");
      li.textContent = `[${a.type}${a.severity ? " / " + a.severity : ""}] ${a.message}`;
      ul.appendChild(li);
    });
    wrap.appendChild(ul);
    return wrap;
  }

  if (data.nodes && data.edges) {
    wrap.appendChild(makeTable(
      ["Entity", "Type"],
      data.nodes.map(n => [n.label, n.type])
    ));
    return wrap;
  }

  if (data.matches) {
    wrap.appendChild(makeTable(
      ["ID", "Name", "Age", "Gender", "Risk"],
      data.matches.map(r => [r.accused_id, r.name, r.age, r.gender, r.risk_score])
    ));
    return wrap;
  }

  return null;
}

function makeTable(headers, rows) {
  const table = document.createElement("table");
  const thead = document.createElement("thead");
  const headRow = document.createElement("tr");
  headers.forEach(h => {
    const th = document.createElement("th");
    th.textContent = h;
    headRow.appendChild(th);
  });
  thead.appendChild(headRow);
  table.appendChild(thead);

  const tbody = document.createElement("tbody");
  rows.forEach(r => {
    const tr = document.createElement("tr");
    r.forEach(cell => {
      const td = document.createElement("td");
      td.textContent = cell ?? "–";
      tr.appendChild(td);
    });
    tbody.appendChild(tr);
  });
  table.appendChild(tbody);
  return table;
}

// ── Suggestion chips ──────────────────────────────────────────────────────────
function renderSuggestions(suggestions) {
  if (!suggestionsEl) return;
  suggestionsEl.innerHTML = "";
  (suggestions || []).forEach(s => {
    const chip = document.createElement("div");
    chip.className = "suggestion-chip";
    chip.textContent = s;
    chip.onclick = () => {
      chatInput.value = s;
      sendMessage();
    };
    suggestionsEl.appendChild(chip);
  });
}

// ── Send message ──────────────────────────────────────────────────────────────
async function sendMessage() {
  const text = chatInput.value.trim();
  if (!text) return;

  appendMessage("user", text);
  chatInput.value = "";
  renderSuggestions([]);
  showTypingIndicator();

  try {
    const res = await apiPost("/api/chat", {
      session_id: SESSION_ID,
      message:    text,
      language:   langSelect ? langSelect.value : "en",
    });
    removeTypingIndicator();
    appendMessage("assistant", res.message, res.evidence, res.data, res.intent);
    renderSuggestions(res.suggestions);
  } catch (err) {
    removeTypingIndicator();
    appendMessage("assistant", "Sorry, something went wrong reaching the backend. Is the API running?");
    console.error(err);
  }
}

if (sendBtn) sendBtn.addEventListener("click", sendMessage);
if (chatInput) {
  chatInput.addEventListener("keydown", e => {
    if (e.key === "Enter" && !e.shiftKey) sendMessage();
  });
}

if (exportBtn) {
  exportBtn.addEventListener("click", () => {
    window.open(`/api/export/${SESSION_ID}/pdf`, "_blank");
  });
}

// ── Voice Input (Web Speech API) ──────────────────────────────────────────────
// Supports both English (en-IN) and Kannada (kn-IN) via language selector
let recognition  = null;
let recognizing  = false;

const LANG_MAP = {
  en: "en-IN",
  kn: "kn-IN",  // Kannada – Web Speech API support varies by browser/OS
};

function setupSpeechRecognition() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    if (micBtn) {
      micBtn.title   = "Voice input not supported in this browser (try Chrome)";
      micBtn.disabled = true;
      micBtn.style.opacity = "0.4";
    }
    return;
  }

  recognition = new SpeechRecognition();
  recognition.continuous     = false;
  recognition.interimResults = true;   // show interim so user gets feedback

  recognition.onresult = event => {
    let interim = "";
    let final   = "";
    for (let i = event.resultIndex; i < event.results.length; i++) {
      const t = event.results[i][0].transcript;
      if (event.results[i].isFinal) final += t;
      else interim += t;
    }
    // Show interim result in input as preview
    if (chatInput) chatInput.value = final || interim;
    // Auto-send once we have a final result
    if (final) sendMessage();
  };

  recognition.onend = () => {
    recognizing = false;
    if (micBtn) micBtn.classList.remove("recording");
  };

  recognition.onerror = err => {
    recognizing = false;
    if (micBtn) micBtn.classList.remove("recording");
    if (err.error !== "no-speech") {
      console.warn("[voice]", err.error);
    }
  };
}

if (micBtn) {
  micBtn.addEventListener("click", () => {
    if (!recognition) {
      setupSpeechRecognition();
      if (!recognition) return;
    }

    if (recognizing) {
      recognition.stop();
      return;
    }

    const lang = langSelect ? langSelect.value : "en";
    recognition.lang = LANG_MAP[lang] || "en-IN";

    recognizing = true;
    micBtn.classList.add("recording");
    micBtn.title = recognition.lang === "kn-IN"
      ? "🎤 Kannada ಭಾಷಣ ಆಲಿಸುತ್ತಿದ್ದೇನೆ…"
      : "🎤 Listening in English…";
    recognition.start();
  });
}

// Language selector updates the mic tooltip
if (langSelect) {
  langSelect.addEventListener("change", () => {
    if (micBtn && !recognizing) {
      const lang = langSelect.value;
      micBtn.title = lang === "kn"
        ? "ಕನ್ನಡದಲ್ಲಿ ಮಾತನಾಡಿ (Speak in Kannada)"
        : "Speak in English";
    }
  });
}

setupSpeechRecognition();

// ── Initial greeting ──────────────────────────────────────────────────────────
window.addEventListener("DOMContentLoaded", () => {
  appendMessage(
    "assistant",
    "Namaskara! I'm Kavach, the KSP Crime Intelligence Assistant. " +
    "Ask me about FIRs, accused profiles, criminal networks, crime hotspots, or early-warning alerts. " +
    "You can type in English or Kannada, or use the 🎤 mic button for voice input."
  );
  renderSuggestions([
    "Show crime hotspots",
    "List repeat offenders",
    "Show risk profile for accused #1",
    "Show network for accused #1",
    "Show socio-economic insights",
    "Show early warning alerts",
  ]);
});
