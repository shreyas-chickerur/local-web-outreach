/* The review, drawn on the page itself.
 *
 * Injected into the generated site when it is served with ?review=<id>, so an
 * operator reads findings where they happen instead of holding a list in one
 * hand and a page in the other. Nothing here is part of the site: the layer is
 * added at serve time and the stored HTML never contains it.
 *
 * A pin lands by its finding's anchor — a CSS selector for something structural
 * like a photograph, or the sentence itself for a claim. Anything in the head
 * has nothing to point at and is listed in the rail instead of being pinned
 * somewhere arbitrary, because a pin in the wrong place is worse than no pin.
 */
(function () {
  const DATA = window.__REVIEW__;
  if (!DATA || !DATA.findings) return;

  const TONE = {contradicted: "stop", defect: "warn", unsourced: "warn",
                assembled: "warn", wording: "mute", unmeasured: "mute",
                corroborated: "ok"};
  const SAYS = {contradicted: "the source says otherwise",
                defect: "something on the page is broken",
                unsourced: "nothing says this either way",
                assembled: "the parts are sourced, the sentence is not",
                wording: "the page\u2019s own phrasing \u2014 nothing to check it against",
                unmeasured: "could not be checked",
                corroborated: "the source says this"};

  const css = `
  .an-pin{position:absolute;z-index:2147483000;width:22px;height:22px;border-radius:50%;
    border:2px solid #fff;font:600 11px/18px ui-sans-serif,system-ui,sans-serif;
    color:#fff;text-align:center;cursor:pointer;box-shadow:0 1px 6px rgba(0,0,0,.35);
    padding:0}
  .an-pin.stop{background:#a33}.an-pin.warn{background:#b1761c}
  .an-pin.ok{background:#2c6a46}.an-pin.mute{background:#6b6b6b}
  .an-pin.done{opacity:.45}
  .an-pin.here{outline:3px solid rgba(255,255,255,.7)}
  /* An outline rather than a tint: the pages these findings sit on are as
     often near-black as near-white, and a wash that reads on one disappears
     on the other. */
  .an-mark{outline:2px solid #d89a2e!important;outline-offset:3px;border-radius:2px;
    scroll-margin:120px}
  .an-mark.stop{outline-color:#e05252!important}
  .an-mark.ok{outline-color:#4a9e72!important}
  .an-mark.here{outline-width:3px!important;
    box-shadow:0 0 0 6px rgba(216,154,46,.22)!important}
  .an-card{position:fixed;z-index:2147483001;width:min(430px,86vw);background:#fff;
    color:#25231f;border:1px solid #ddd9d2;border-radius:8px;
    box-shadow:0 10px 34px rgba(0,0,0,.28);font:14px/1.5 ui-sans-serif,system-ui,sans-serif;
    padding:14px 15px;max-height:min(78vh,640px);overflow:auto}
  .an-card .vd{font-size:10.5px;letter-spacing:.1em;text-transform:uppercase;color:#7d7a72}
  .an-card h4{margin:4px 0 6px;font-size:15px;line-height:1.35}
  .an-card p{margin:0 0 9px;color:#524f48;font-size:13.5px}
  .an-card .shot{display:block;max-width:100%;max-height:170px;border-radius:5px;
    border:1px solid #e0ddd6;margin:0 0 9px;background:#f4f2ee}
  .an-card .where{font:12px ui-monospace,Menlo,monospace;background:#f4f2ee;
    border:1px solid #e6e3dc;border-radius:4px;padding:5px 8px;margin:0 0 9px;
    overflow-x:auto;white-space:pre}
  .an-two{display:grid;grid-template-columns:1fr;gap:8px;margin:0 0 9px}
  .an-two > div{border:1px solid #e6e3dc;border-radius:5px;overflow:hidden}
  .an-two em{display:block;font-size:10px;letter-spacing:.09em;text-transform:uppercase;
    color:#8a867d;font-style:normal;padding:5px 8px;background:#f7f5f1;
    border-bottom:1px solid #e6e3dc}
  .an-two pre{margin:0;padding:7px 9px;font:12px/1.5 ui-monospace,Menlo,monospace;
    white-space:pre-wrap;word-break:break-word;max-height:150px;overflow:auto}
  .an-card .res{display:flex;gap:6px;flex-wrap:wrap;margin:0 0 9px}
  .an-card .res a{font-size:12px;color:#2d5f9a;text-decoration:none;padding:3px 9px;
    border:1px solid #d5e0ee;border-radius:999px}
  .an-card input{width:100%;font:inherit;font-size:13px;padding:6px 9px;
    border:1px solid #d9d6cf;border-radius:5px;margin:0 0 8px}
  .an-card .act{display:flex;gap:6px;flex-wrap:wrap}
  .an-card button{font:inherit;font-size:12.5px;padding:5px 11px;border-radius:5px;
    border:1px solid #d9d6cf;background:#fff;cursor:pointer;color:#25231f}
  .an-card button.primary{background:#25231f;color:#fff;border-color:#25231f}
  .an-card .said{margin:8px 0 0;font-size:12.5px;color:#2c6a46}
  .an-rail{position:fixed;right:0;top:0;bottom:0;width:300px;z-index:2147483002;
    background:#fbfaf7;border-left:1px solid #e0ddd6;overflow:auto;
    font:13px/1.5 ui-sans-serif,system-ui,sans-serif;color:#25231f;padding:14px}
  .an-rail h3{margin:0 0 3px;font-size:14px}
  .an-rail .sub{color:#7d7a72;font-size:12px}
  .an-rail .k{font-size:10.5px;letter-spacing:.12em;text-transform:uppercase;
    color:#8a867d;margin:16px 0 6px}
  .an-rail .row{border:1px solid #e6e3dc;border-left:3px solid #c9c6bf;border-radius:5px;
    padding:8px 10px;margin-bottom:7px;background:#fff;cursor:pointer;font-size:12.5px}
  .an-rail .row.stop{border-left-color:#a33}.an-rail .row.warn{border-left-color:#b1761c}
  .an-rail .row.ok{border-left-color:#2c6a46}.an-rail .row.done{opacity:.5}
  .an-rail .tally{display:flex;gap:5px;flex-wrap:wrap;margin-top:9px}
  .an-rail .tally span{font-size:11px;border:1px solid #ddd9d2;border-radius:999px;
    padding:2px 8px;color:#55524b}
  .an-rail label{display:flex;align-items:center;gap:6px;margin-top:12px;font-size:12.5px}
  body.an-on{margin-right:300px!important}
  .an-tab{position:fixed;right:10px;top:10px;z-index:2147483003;font:600 12px/1
    ui-sans-serif,system-ui,sans-serif;padding:8px 12px;border-radius:999px;
    border:1px solid #d9d6cf;background:#fff;color:#25231f;cursor:pointer;
    box-shadow:0 2px 8px rgba(0,0,0,.18);display:none}
  /* A phone-width preview has no room for a 300px rail beside it, so there the
     rail slides over and a tab brings it back. */
  body.an-narrow{margin-right:0!important}
  body.an-narrow .an-tab{display:block}
  body.an-narrow .an-rail{width:min(300px,88vw);transform:translateX(102%);
    transition:transform .18s ease}
  body.an-narrow .an-rail.open{transform:none}
  `;
  const style = document.createElement("style");
  style.textContent = css;
  document.head.appendChild(style);
  document.body.classList.add("an-on");

  function fit() {
    document.body.classList.toggle(
      "an-narrow", document.documentElement.clientWidth < 880);
  }
  fit();
  addEventListener("resize", fit);

  const tab = document.createElement("button");
  tab.className = "an-tab";
  tab.textContent = "Findings";
  tab.addEventListener("click", () => {
    const bar = document.querySelector(".an-rail");
    if (bar) bar.classList.toggle("open");
  });
  document.body.appendChild(tab);

  const norm = s => (s || "").replace(/\s+/g, " ").trim().toLowerCase();

  // The element a finding is about. For a claim that is the smallest block
  // whose text contains the sentence — smallest, so a pin lands on the
  // paragraph and not on <body>.
  function target(finding) {
    const a = finding.anchor || "page";
    if (a === "page") return null;
    if (a.startsWith("css:")) {
      try { return document.querySelector(a.slice(4)); } catch (e) { return null; }
    }
    const needle = norm(a.slice(5));
    if (!needle) return null;
    let best = null;
    const all = document.body.querySelectorAll("p,li,h1,h2,h3,h4,span,div,td,figcaption,a,button");
    for (const el of all) {
      // The rail lists the findings, so its rows contain the very sentences
      // being searched for. Without this the layer annotates itself and the
      // pins pile up in the corner.
      if (el.closest(".an-rail,.an-card,.an-tab")) continue;
      if (el.children.length > 3) continue;
      if (norm(el.textContent).indexOf(needle.slice(0, 55)) !== -1) {
        if (!best || el.textContent.length < best.textContent.length) best = el;
      }
    }
    return best;
  }

  const layer = document.createElement("div");
  layer.style.cssText = "position:absolute;top:0;left:0;right:0;pointer-events:none;z-index:2147482999";
  document.body.appendChild(layer);

  let open = null;
  const state = DATA.findings.map(f => ({f, el: null, pin: null}));

  // A pin sits just inside the top-left corner of what it is about, and never
  // outside the page: a hero photograph starts at x=0, and a pin centred on
  // that corner hangs half off the edge where nothing can click it.
  function place() {
    const up = window.scrollY, across = window.scrollX;
    const wide = document.documentElement.clientWidth;
    layer.style.height = document.body.scrollHeight + "px";
    state.forEach(s => {
      if (!s.pin || !s.el) return;
      const r = s.el.getBoundingClientRect();
      if (!r.width && !r.height) { s.pin.style.display = "none"; return; }
      s.pin.style.display = "";
      s.pin.style.top = Math.max(2, r.top + up + 4) + "px";
      s.pin.style.left =
        Math.min(Math.max(6, r.left + across + 4), wide - 330) + "px";
    });
  }

  // For a finding about a photograph, show the photograph. "IMG-0959-scaled.jpg"
  // is a filename; the picture is the thing being judged.
  function shotOf(s) {
    const el = s.el;
    if (!el || el.tagName !== "IMG") return "";
    // A photograph that cannot load is not evidence of anything, so the
    // thumbnail removes itself rather than leaving a broken-image box.
    return `<img class="shot" src="${escape_(el.getAttribute("src") || "")}" alt=""
              onerror="this.remove()">`;
  }

  function card(s) {
    if (open) { open.remove(); open = null; }
    const f = s.f;
    const mine = f.stage === "technical" ? "on the page now" : "the page says";
    const theirs = f.stage === "technical" ? "what it should be" : "the source says";
    const box = document.createElement("div");
    box.className = "an-card";
    box.innerHTML = `
      <div class="vd">${f.verdict} · ${SAYS[f.verdict] || ""}</div>
      <h4>${escape_(f.title)}</h4>
      ${f.detail ? `<p>${escape_(f.detail)}</p>` : ""}
      ${shotOf(s)}
      ${f.locator ? `<div class="where">${escape_(f.locator)}</div>` : ""}
      <div class="an-two">
        <div><em>${mine}</em><pre>${escape_(f.quote || "(nothing)")}</pre></div>
        ${f.evidence ? `<div><em>${theirs}</em><pre>${escape_(f.evidence)}</pre></div>` : ""}
      </div>
      ${(f.resources || []).length ? `<div class="res">${(f.resources || []).map(r =>
        `<a href="${escape_(r.url)}" target="_blank" rel="noopener">${escape_(r.label)} ↗</a>`
        ).join("")}</div>` : ""}
      <input placeholder="what you checked, and what you concluded" value="${escape_(f.note || "")}">
      <div class="act">
        <button class="primary" data-s="confirmed">Correct as is</button>
        <button data-s="corrected">Needs a change</button>
        <button data-s="dismissed">Not worth it</button>
        <button data-s="close">Close</button>
      </div>
      ${f.status && f.status !== "open"
        ? `<p class="said"><b>${escape_(f.status)}</b>${f.note ? " — " + escape_(f.note) : ""}</p>` : ""}`;
    document.body.appendChild(box);

    // Fixed to the window, beside whatever it is about — and centred when
    // there is nothing to sit beside, which is what happens for a finding in
    // the head. Parking it at the foot of the document, as this did before,
    // means every click scrolls you away from the thing you were reading.
    const wide = document.documentElement.clientWidth;
    const tall = document.documentElement.clientHeight;
    const size = box.getBoundingClientRect();
    const r = s.el ? s.el.getBoundingClientRect() : null;
    if (r && r.bottom > 0 && r.top < tall) {
      box.style.top = Math.max(10, Math.min(r.bottom + 10,
                                            tall - size.height - 10)) + "px";
      box.style.left = Math.max(10, Math.min(r.left,
                                             wide - size.width - 320)) + "px";
    } else {
      box.style.top = Math.max(10, (tall - size.height) / 2) + "px";
      box.style.left = Math.max(10, (wide - size.width) / 2 - 150) + "px";
    }
    box.querySelector("input").focus();
    state.forEach(o => { if (o.el) o.el.classList.remove("here"); if (o.pin) o.pin.classList.remove("here"); });
    if (s.el) s.el.classList.add("here");
    if (s.pin) s.pin.classList.add("here");
    box.addEventListener("click", ev => {
      // A source link inside a sandboxed frame depends on popup permissions
      // that vary by browser and by setting, and when they are missing the
      // click does nothing at all — no tab, no error. So the frame never
      // opens anything itself: it hands the address to the workbench, which
      // is an ordinary page and can simply open it.
      const link = ev.target && ev.target.closest && ev.target.closest("a[href]");
      if (link) {
        ev.preventDefault();
        parent.postMessage({kind: "review:open", url: link.href}, "*");
        return;
      }
      const status = ev.target && ev.target.getAttribute("data-s");
      if (!status) return;
      if (status === "close") { box.remove(); open = null; return; }
      const note = box.querySelector("input").value.trim();
      if (!note) { box.querySelector("input").focus(); return; }
      mark(s, status, note, box);
    });
    open = box;
  }

  // The frame is sandboxed without same-origin, on purpose: a generated page
  // should not be able to call the workbench's API. So a decision is handed to
  // the workbench, which owns the request, and the answer comes back by the
  // same route.
  const waiting = new Map();

  function mark(s, status, note, box) {
    const ticket = String(Date.now()) + ":" + s.f.id;
    waiting.set(ticket, {s, box});
    parent.postMessage({kind: "review:mark", ticket, finding_id: s.f.id,
                        status, note}, "*");
  }

  addEventListener("message", ev => {
    const msg = ev.data;
    if (!msg || msg.kind !== "review:marked") return;
    const held = waiting.get(msg.ticket);
    if (!held) return;
    waiting.delete(msg.ticket);
    if (msg.error) { alert(msg.error); return; }
    Object.assign(held.s.f, msg.finding || {});
    if (held.s.pin) held.s.pin.classList.add("done");
    held.box.remove();
    open = null;
    rail();
  });

  function escape_(text) {
    return String(text == null ? "" : text).replace(/[&<>"]/g,
      c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[c]));
  }

  let showSettled = false;

  function draw() {
    state.forEach((s, i) => {
      if (s.pin) { s.pin.remove(); s.pin = null; }
      if (s.mark && s.el) { s.el.classList.remove("an-mark", "stop", "ok"); s.mark = false; }
      const settled = s.f.verdict === "corroborated";
      if (settled && !showSettled) return;
      s.el = s.el || target(s.f);
      if (!s.el) return;
      const tone = TONE[s.f.verdict] || "warn";
      s.el.classList.add("an-mark");
      if (tone === "stop" || tone === "ok") s.el.classList.add(tone);
      s.mark = true;
      const pin = document.createElement("button");
      pin.className = "an-pin " + tone + (s.f.status !== "open" ? " done" : "");
      pin.textContent = String(i + 1);
      pin.style.pointerEvents = "auto";
      pin.title = s.f.title;
      pin.addEventListener("click", ev => { ev.stopPropagation(); card(s); });
      layer.appendChild(pin);
      s.pin = pin;
    });
    place();
    rail();
  }

  function rail() {
    let bar = document.querySelector(".an-rail");
    if (!bar) {
      bar = document.createElement("div");
      bar.className = "an-rail";
      document.body.appendChild(bar);
    }
    const open_ = state.filter(s => s.f.status === "open" && s.f.verdict !== "corroborated");
    const loose = state.filter(s => (s.f.anchor || "page") === "page");
    const unplaced = state.filter(s => (s.f.anchor || "page") !== "page" && !s.el
                                       && s.f.verdict !== "corroborated");
    const tally = {};
    state.forEach(s => { if (s.f.status === "open")
      tally[s.f.verdict] = (tally[s.f.verdict] || 0) + 1; });
    const row = s => `<div class="row ${TONE[s.f.verdict] || "warn"}${
      s.f.status !== "open" ? " done" : ""}" data-id="${s.f.id}">${escape_(s.f.title)}</div>`;
    bar.innerHTML = `
      <h3>Review · v${DATA.version}</h3>
      <div class="sub">${open_.length} still open of ${state.length}</div>
      <div class="tally">${Object.keys(tally).map(v =>
        `<span>${tally[v]} ${v}</span>`).join("")}</div>
      <label><input type="checkbox" id="an-settled" ${showSettled ? "checked" : ""}>
        show the ${state.filter(s => s.f.verdict === "corroborated").length} corroborated</label>
      ${loose.length ? `<div class="k">Whole page · nothing to pin</div>${
        loose.map(row).join("")}` : ""}
      ${unplaced.length ? `<div class="k">Could not be placed</div>${
        unplaced.map(row).join("")}` : ""}`;
    bar.querySelector("#an-settled").addEventListener("change", ev => {
      showSettled = ev.target.checked; draw();
    });
    bar.addEventListener("click", ev => {
      const id = ev.target && ev.target.getAttribute("data-id");
      if (!id) return;
      const s = state.find(x => String(x.f.id) === id);
      if (!s) return;
      if (s.el) s.el.scrollIntoView({block: "center", behavior: "smooth"});
      card(s);
    });
  }

  addEventListener("scroll", place, {passive: true});
  addEventListener("resize", () => { place(); });
  if (document.readyState === "complete") draw();
  else addEventListener("load", draw);
  setTimeout(draw, 1200);   // photographs change the layout as they arrive
})();
