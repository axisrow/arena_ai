"use strict";
const $ = (id) => document.getElementById(id);
const COLS = [
  { k: "name", t: "Model", get: (m) => m.name },
  { k: "org", t: "Org", get: (m) => m.org },
  { k: "lic", t: "License", get: (m) => m.license ?? "" },
  { k: "date", t: "Released", get: (m) => m.release_date ?? "" },
  { k: "elo", t: "Elo", num: true },
  { k: "rank", t: "Rank", num: true },
  { k: "votes", t: "Votes", num: true },
  { k: "pin", t: "$/M in", num: true, get: (m) => m.price_in },
  { k: "pout", t: "$/M out", num: true, get: (m) => m.price_out },
  { k: "ctx", t: "Context", num: true, get: (m) => m.context },
  { k: "mod", t: "Input", get: (m) => m.input_modalities.join(",") },
];
let DATA, ROWS, sort = { k: "elo", dir: -1 };

const catElo = (m, c) => (c.startsWith("@") ? m.arenas[c.slice(1)] : m.elo[c]);
const val = (m, k, c) => {
  const e = catElo(m, c);
  if (k === "elo") return e?.r ?? null;
  if (k === "rank") return e?.rank ?? null;
  if (k === "votes") return e?.votes ?? null;
  return COLS.find((x) => x.k === k).get(m);
};

function init(data) {
  DATA = data;
  ROWS = data.models;
  $("meta").textContent = `${ROWS.length} entries · built ${data.generated_at.slice(0, 16).replace("T", " ")} UTC`;
  $("cat").innerHTML =
    data.categories.map((c) => `<option value="${c}">${c.replace(/_/g, " ")}</option>`).join("") +
    data.arenas.map((a) => `<option value="@${a}">arena: ${a}</option>`).join("");
  const orgs = [...new Set(ROWS.map((m) => m.org).filter(Boolean))].sort();
  $("org").innerHTML = orgs.map((o) => `<option>${o}</option>`).join("");
  const add = (id, set) => ($(id).innerHTML += [...set].sort().map((v) => `<option>${v}</option>`).join(""));
  add("mod", new Set(ROWS.flatMap((m) => m.input_modalities)));
  add("param", new Set(ROWS.flatMap((m) => m.params)));
  restore();
  for (const el of document.querySelectorAll("#filters input,#filters select")) el.addEventListener("input", render);
  $("reset").onclick = () => { location.hash = ""; for (const el of document.querySelectorAll("#filters input,#filters select")) { el.type === "checkbox" ? (el.checked = false) : el.tagName === "SELECT" && el.multiple ? [...el.options].forEach((o) => (o.selected = false)) : (el.value = ""); } $("cat").value = "overall"; render(); };
  render();
}

const ids = ["q", "cat", "minElo", "open", "src", "from", "to", "maxIn", "maxOut", "minCtx", "mod", "param"];
function state() {
  const s = {};
  for (const id of ids) if ($(id).value) s[id] = $(id).value;
  const orgs = [...$("org").selectedOptions].map((o) => o.value);
  if (orgs.length) s.org = orgs.join("|");
  if ($("oneVariant").checked) s.best = "1";
  s.sort = sort.k + ":" + sort.dir;
  return s;
}
function restore() {
  const p = new URLSearchParams(location.hash.slice(1));
  $("cat").value = "overall";
  for (const id of ids) if (p.has(id)) $(id).value = p.get(id);
  if (p.has("org")) { const sel = p.get("org").split("|"); [...$("org").options].forEach((o) => (o.selected = sel.includes(o.value))); }
  $("oneVariant").checked = p.get("best") === "1";
  if (p.has("sort")) { const [k, d] = p.get("sort").split(":"); sort = { k, dir: +d || -1 }; }
}

function filtered() {
  const q = $("q").value.trim().toLowerCase(), c = $("cat").value;
  const orgs = [...$("org").selectedOptions].map((o) => o.value);
  const num = (id) => ($(id).value === "" ? null : Number($(id).value));
  const minElo = num("minElo"), maxIn = num("maxIn"), maxOut = num("maxOut"), minCtx = num("minCtx");
  const from = $("from").value, to = $("to").value, open = $("open").value, src = $("src").value;
  const mod = $("mod").value, param = $("param").value;
  let rows = ROWS.filter((m) => {
    if (q && !(m.name + " " + m.org + " " + (m.or_id ?? "")).toLowerCase().includes(q)) return false;
    if (orgs.length && !orgs.includes(m.org)) return false;
    if (open === "open" && m.open !== true) return false;
    if (open === "closed" && m.open !== false) return false;
    if (src === "both" && !(m.in_arena && m.in_openrouter)) return false;
    if (src === "arena" && !(m.in_arena && !m.in_openrouter)) return false;
    if (src === "or" && !(m.in_openrouter && !m.in_arena)) return false;
    if (from && !(m.release_date && m.release_date >= from)) return false;
    if (to && !(m.release_date && m.release_date <= to)) return false;
    if (minElo != null && !((catElo(m, c)?.r ?? -1) >= minElo)) return false;
    if (maxIn != null && !(m.price_in != null && m.price_in <= maxIn)) return false;
    if (maxOut != null && !(m.price_out != null && m.price_out <= maxOut)) return false;
    if (minCtx != null && !((m.context ?? 0) >= minCtx * 1000)) return false;
    if (mod && !m.input_modalities.includes(mod)) return false;
    if (param && !m.params.includes(param)) return false;
    return true;
  });
  if ($("oneVariant").checked) { // keep the top-rated Arena row per OpenRouter model (or per name)
    const best = new Map();
    for (const m of rows) {
      const key = m.or_id ?? m.name, cur = best.get(key);
      if (!cur || (catElo(m, c)?.r ?? -1) > (catElo(cur, c)?.r ?? -1)) best.set(key, m);
    }
    rows = [...best.values()];
  }
  return rows;
}

function cell(m, k, c) {
  const e = catElo(m, c);
  switch (k) {
    case "name": {
      const link = m.or_id ? `<a href="https://openrouter.ai/${m.or_id}" target="_blank" rel="noopener">${esc(m.name)}</a>` : esc(m.name);
      const tags = (m.in_arena ? "" : ' <span class="tag">OpenRouter only</span>') + (m.in_openrouter ? "" : ' <span class="tag">Arena only</span>');
      return link + tags;
    }
    case "lic": return m.license == null ? "" : `<span class="tag ${m.open ? "open" : ""}">${esc(m.license)}</span>`;
    case "date": return m.release_date ? `<span title="source: ${m.release_source}">${m.release_date}</span>` : "";
    case "elo": return e ? `<span title="95% CI ${e.lo}–${e.hi}">${Math.round(e.r)}</span>` : "";
    case "rank": return e ? e.rank : "";
    case "votes": return e ? e.votes.toLocaleString() : "";
    case "pin": case "pout": {
      const v = k === "pin" ? m.price_in : m.price_out;
      return v == null ? "" : v === 0 ? "free" : "$" + (v < 1 ? v.toFixed(3) : v.toFixed(2));
    }
    case "ctx": return m.context ? (m.context >= 1e6 ? +(m.context / 1e6).toFixed(2) + "M" : Math.round(m.context / 1000) + "K") : "";
    default: return esc(String(COLS.find((x) => x.k === k).get(m) ?? ""));
  }
}
const esc = (s) => s.replace(/[&<>"]/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[ch]);

function render() {
  const c = $("cat").value;
  const rows = filtered();
  const cmp = (a, b) => {
    const x = val(a, sort.k, c), y = val(b, sort.k, c);
    if (x == null || x === "") return y == null || y === "" ? 0 : 1; // empties always last
    if (y == null || y === "") return -1;
    return (x < y ? -1 : x > y ? 1 : 0) * sort.dir;
  };
  rows.sort(cmp);
  $("count").textContent = `${rows.length} of ${ROWS.length} shown`;
  $("tbl").tHead.innerHTML = "<tr>" + COLS.map((col) => `<th data-k="${col.k}" class="${col.num ? "num " : ""}${col.k === sort.k ? "sorted" : ""}">${col.t}${col.k === sort.k ? (sort.dir > 0 ? " ▲" : " ▼") : ""}</th>`).join("") + "</tr>";
  $("tbl").tBodies[0].innerHTML = rows.slice(0, 1500).map((m) => "<tr>" + COLS.map((col) => `<td class="${col.num ? "num" : ""}">${cell(m, col.k, c)}</td>`).join("") + "</tr>").join("");
  for (const th of $("tbl").tHead.rows[0].cells) th.onclick = () => { const k = th.dataset.k; sort = { k, dir: sort.k === k ? -sort.dir : (COLS.find((x) => x.k === k).num ? -1 : 1) }; render(); };
  history.replaceState(null, "", "#" + new URLSearchParams(state()));
}

fetch("data/models.json").then((r) => r.json()).then(init).catch((e) => ($("meta").textContent = "Failed to load data/models.json: " + e));
