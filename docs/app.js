(() => {
  const $ = (s) => document.querySelector(s);
  const store = {
    get(k, d) { try { const v = localStorage.getItem("jr:" + k); return v ? JSON.parse(v) : d; } catch { return d; } },
    set(k, v) { try { localStorage.setItem("jr:" + k, JSON.stringify(v)); } catch {} },
  };

  const S = {
    data: null, status: null,
    tab: store.get("tab", "india"),
    place: null, q: "",
    toggles: new Set(store.get("toggles", ["nous"])),
    sort: store.get("sort", "score"),
    saved: store.get("saved", {}), applied: store.get("applied", {}), hidden: store.get("hidden", {}),
    prevVisit: store.get("lastVisit", null),
  };

  const ago = (iso) => {
    if (!iso) return "";
    const h = (Date.now() - new Date(iso).getTime()) / 36e5;
    if (h < 1) return Math.max(1, Math.round(h * 60)) + "m ago";
    if (h < 24) return Math.round(h) + "h ago";
    const d = Math.round(h / 24);
    return d === 1 ? "1 day ago" : d + " days ago";
  };
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const isNew = (j) => S.prevVisit ? j.first_seen > S.prevVisit : (Date.now() - new Date(j.first_seen)) < 36e5 * 14;

  async function load() {
    const bust = "?t=" + Date.now();
    try {
      const [d, s] = await Promise.all([
        fetch("data/jobs.json" + bust, { cache: "no-store" }).then((r) => r.json()),
        fetch("data/status.json" + bust, { cache: "no-store" }).then((r) => r.json()).catch(() => null),
      ]);
      S.data = d; S.status = s;
    } catch (e) {
      $("#list").innerHTML = `<p class="empty">Couldn't load jobs (${esc(e.message)}). Pull down to retry.</p>`;
      return;
    }
    $("#cIndia").textContent = S.data.india.length;
    $("#cAbroad").textContent = S.data.abroad.length;
    renderStatus();
    render();
    // mark this visit after a moment so "New" badges survive the first look
    setTimeout(() => store.set("lastVisit", S.data.generated_at), 4000);
  }

  function renderStatus() {
    const st = S.status, g = S.data.generated_at;
    $("#scanAge").textContent = "scanned " + ago(g);
    const hrs = (Date.now() - new Date(g)) / 36e5;
    const okRatio = st ? st.boards_ok / Math.max(1, st.boards_total) : 0;
    const dot = document.querySelector(".dot");
    dot.className = "dot " + (hrs > 26 || okRatio < 0.6 ? "bad" : hrs > 14 || okRatio < 0.9 ? "warn" : "ok");
    if (!st) return;
    const failed = Object.entries(st.sources).filter(([, v]) => !v.ok);
    const li = st.linkedin || {};
    $("#statusBody").innerHTML = `
      <p><b>${new Date(g).toLocaleString()}</b> · took ${st.duration_s}s</p>
      <p>Company boards: <b>${st.boards_ok}/${st.boards_total}</b> answered.
      New this scan: <b>${st.new?.india ?? 0}</b> India, <b>${st.new?.abroad ?? 0}</b> abroad.</p>
      <p>LinkedIn: ${li.requests ? `${li.found} found, ${li.checked} opened, <b>${li.closed}</b> closed ones dropped${li.blocked ? ", <b>rate-limited</b> this run" : ""}` : "skipped"}.</p>
      <p>Sponsor registers: UK ${esc(st.registers?.uk_register ?? "–")}, NL ${esc(st.registers?.nl_register ?? "–")}</p>
      ${failed.length ? `<p>Boards that failed (yesterday's jobs kept):</p><ul>${failed.map(([k, v]) => `<li>${esc(v.company)} — ${esc(v.error)}</li>`).join("")}</ul>` : ""}
      <p>Every job here was listed as open by the company's own job system, or opened on LinkedIn and checked, during this scan.</p>`;
  }

  function filtered() {
    let L = S.data[S.tab] || [];
    const T = S.toggles;
    const q = S.q.trim().toLowerCase();
    L = L.filter((j) => {
      if (T.has("hidden")) { if (!S.hidden[j.id]) return false; } else if (S.hidden[j.id]) return false;
      if (T.has("saved") && !S.saved[j.id]) return false;
      if (T.has("applied") && !S.applied[j.id]) return false;
      if (T.has("new") && !isNew(j)) return false;
      if (S.tab === "abroad") {
        if (T.has("sponsor") && j.sponsorship !== "confirmed") return false;
        if (T.has("nous") && j.place === "United States" && S.place !== "United States") return false;
      }
      if (S.place && j.place !== S.place) return false;
      if (q) {
        const hay = (j.title + " " + j.company + " " + j.location + " " + (j.skills || []).join(" ")).toLowerCase();
        if (!q.split(/\s+/).every((w) => hay.includes(w))) return false;
      }
      return true;
    });
    if (S.sort === "new") L = [...L].sort((a, b) => (b.posted_at || b.first_seen || "").localeCompare(a.posted_at || a.first_seen || ""));
    return L;
  }

  function renderPlaces() {
    const L = S.data[S.tab] || [];
    const counts = {};
    L.forEach((j) => { if (!S.hidden[j.id]) counts[j.place] = (counts[j.place] || 0) + 1; });
    const places = Object.entries(counts).sort((a, b) => b[1] - a[1]);
    $("#places").innerHTML =
      `<button class="chip ${S.place ? "" : "on"}" data-p="">All</button>` +
      places.map(([p, n]) => `<button class="chip ${S.place === p ? "on" : ""}" data-p="${esc(p)}">${esc(p)}<small>${n}</small></button>`).join("");
  }

  function card(j) {
    const sc = j.score >= 75 ? "s-hi" : j.score >= 55 ? "s-md" : "";
    const tags = [];
    if (isNew(j)) tags.push(`<span class="tag new">NEW</span>`);
    if (j.partition === "abroad") {
      if (j.sponsorship === "confirmed") tags.push(`<span class="tag visa">Visa/relocation stated</span>`);
      else if (j.sponsorship === "likely") tags.push(`<span class="tag visa">Usually sponsors</span>`);
      else tags.push(`<span class="tag">Visa not stated</span>`);
      if (j.language) tags.push(`<span class="tag warn">Needs ${esc(j.language)}</span>`);
    }
    (j.flags || []).filter((f) => !f.startsWith("needs")).forEach((f) => tags.push(`<span class="tag warn">${esc(f)}</span>`));
    if (j.salary) tags.push(`<span class="tag sal">${esc(j.salary)}</span>`);
    (j.skills || []).slice(0, 5).forEach((s) => tags.push(`<span class="tag">${esc(s)}</span>`));
    const dim = S.applied[j.id] || S.hidden[j.id];
    return `<article class="card ${dim ? "dim" : ""}" data-id="${esc(j.id)}">
      <div class="ring ${sc}" title="Fit score">${j.score}</div>
      <div>
        <h3 class="t">${esc(j.title)}</h3>
        <div class="co">${esc(j.company)} ${j.tier === 1 ? '<span class="tier">★</span>' : ""}</div>
        <div class="meta">${esc(j.location)}</div>
        <div class="meta">${j.posted_at ? "posted " + ago(j.posted_at) + " · " : ""}via ${esc(j.src)}</div>
        <div class="tags">${tags.join("")}</div>
      </div>
      <div class="more">
        ${j.visa_note ? `<p>“${esc(j.visa_note)}”</p>` : ""}
        ${j.min_years != null ? `<p>Asks for ${j.min_years}+ years.</p>` : ""}
        <p>First seen ${ago(j.first_seen)}, last confirmed open ${ago(j.last_seen)}.</p>
      </div>
      <div class="acts">
        <a class="btn apply" href="${esc(j.url)}" target="_blank" rel="noopener">Apply</a>
        <button class="btn ${S.saved[j.id] ? "on" : ""}" data-act="saved" aria-label="Save">${S.saved[j.id] ? "★" : "☆"}</button>
        <button class="btn ${S.applied[j.id] ? "on" : ""}" data-act="applied">${S.applied[j.id] ? "Applied ✓" : "Applied?"}</button>
        <button class="btn" data-act="hidden" aria-label="Hide">${S.hidden[j.id] ? "Unhide" : "✕"}</button>
      </div>
    </article>`;
  }

  let renderLimit = 60;
  function render() {
    if (!S.data) return;
    document.body.classList.toggle("abroad", S.tab === "abroad");
    document.querySelectorAll(".seg button").forEach((b) => b.classList.toggle("on", b.dataset.tab === S.tab));
    document.querySelectorAll("#toggles .chip[data-t]").forEach((b) => b.classList.toggle("on", S.toggles.has(b.dataset.t)));
    $("#sort").value = S.sort;
    renderPlaces();
    const L = filtered();
    $("#list").innerHTML = L.slice(0, renderLimit).map(card).join("") +
      (L.length > renderLimit ? `<button class="btn" id="moreBtn">Show ${L.length - renderLimit} more</button>` : "");
    $("#empty").hidden = L.length > 0;
  }

  // ---- events ----
  document.querySelector(".seg").addEventListener("click", (e) => {
    const b = e.target.closest("button"); if (!b) return;
    S.tab = b.dataset.tab; S.place = null; renderLimit = 60; store.set("tab", S.tab); render(); scrollTo(0, 0);
  });
  $("#places").addEventListener("click", (e) => {
    const b = e.target.closest("button"); if (!b) return;
    S.place = b.dataset.p || null; renderLimit = 60; render();
  });
  $("#toggles").addEventListener("click", (e) => {
    const b = e.target.closest("button[data-t]"); if (!b) return;
    const t = b.dataset.t;
    S.toggles.has(t) ? S.toggles.delete(t) : S.toggles.add(t);
    store.set("toggles", [...S.toggles]); renderLimit = 60; render();
  });
  $("#sort").addEventListener("change", (e) => { S.sort = e.target.value; store.set("sort", S.sort); render(); });
  let qt; $("#q").addEventListener("input", (e) => { clearTimeout(qt); qt = setTimeout(() => { S.q = e.target.value; render(); }, 120); });

  $("#list").addEventListener("click", (e) => {
    if (e.target.id === "moreBtn") { renderLimit += 60; render(); return; }
    const el = e.target.closest(".card"); if (!el) return;
    const id = el.dataset.id;
    const act = e.target.closest("[data-act]")?.dataset.act;
    if (act) {
      const m = S[act];
      m[id] ? delete m[id] : (m[id] = Date.now());
      store.set(act, m);
      render();
      return;
    }
    if (e.target.closest("a")) {
      return; // Apply link
    }
    el.classList.toggle("open");
  });

  $("#statusBtn").addEventListener("click", () => $("#statusDlg").showModal());
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible" && S.data && (Date.now() - new Date(S.data.generated_at)) > 36e5) load();
  });

  if ("serviceWorker" in navigator) navigator.serviceWorker.register("sw.js").catch(() => {});
  load();
})();
