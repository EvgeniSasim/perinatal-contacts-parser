const $ = (id) => document.getElementById(id);

function apiKey() {
  return localStorage.getItem("pnc_api_key") || $("apiKey").value.trim();
}

async function api(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  if (options.auth) headers["X-API-Key"] = apiKey();
  if (options.body && !headers["Content-Type"]) headers["Content-Type"] = "application/json";
  const res = await fetch(path, { ...options, headers });
  if (!res.ok) throw new Error(await res.text());
  const ct = res.headers.get("content-type") || "";
  if (ct.includes("application/json")) return res.json();
  return res;
}

function params() {
  const p = new URLSearchParams();
  if ($("q").value.trim()) p.set("q", $("q").value.trim());
  if ($("type").value) p.set("type", $("type").value);
  if ($("region").value) p.set("region", $("region").value);
  if ($("city").value.trim()) p.set("city", $("city").value.trim());
  if ($("hasEmail").checked) p.set("has_email", "true");
  p.set("page_size", "50");
  return p;
}

async function loadMeta() {
  const [types, regions, stats] = await Promise.all([
    api("/api/v1/meta/types"),
    api("/api/v1/meta/regions"),
    api("/api/v1/meta/stats"),
  ]);
  const typeSel = $("type");
  types.forEach((t) => {
    const o = document.createElement("option");
    o.value = t.code;
    o.textContent = t.label;
    typeSel.appendChild(o);
  });
  const regionSel = $("region");
  regions.forEach((r) => {
    const o = document.createElement("option");
    o.value = r;
    o.textContent = r;
    regionSel.appendChild(o);
  });
  $("meta").textContent = `Всего в базе: ${stats.total}`;
}

async function search() {
  const data = await api(`/api/v1/institutions?${params()}`);
  $("meta").textContent = `Найдено: ${data.total}`;
  const tbody = $("rows");
  tbody.innerHTML = "";
  data.items.forEach((item) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `<td>${item.name}</td><td>${item.type}</td><td>${item.region}</td><td>${item.city}</td><td>${(item.phones || [])[0] || ""}</td><td>${(item.emails || [])[0] || ""}</td>`;
    tr.onclick = () => showCard(item);
    tbody.appendChild(tr);
  });
}

function showCard(item) {
  $("card").classList.remove("hidden");
  $("cardTitle").textContent = item.name;
  $("cardBody").textContent = JSON.stringify(item, null, 2);
}

$("searchBtn").onclick = () => search().catch(alert);
$("closeCard").onclick = () => $("card").classList.add("hidden");
$("apiKey").onchange = () => localStorage.setItem("pnc_api_key", $("apiKey").value.trim());
$("apiKey").value = localStorage.getItem("pnc_api_key") || "";

$("exportBtn").onclick = async () => {
  try {
    const body = Object.fromEntries(params().entries());
    if (body.has_email) body.has_email = true;
    const job = await api("/api/v1/admin/export", { method: "POST", auth: true, body: JSON.stringify(body) });
    if (job.status === "done" && job.result_json?.download) {
      window.location.href = job.result_json.download + `?` ; // file endpoint needs header — open via fetch blob
      const res = await fetch(job.result_json.download, { headers: { "X-API-Key": apiKey() } });
      const blob = await res.blob();
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = `export-${job.id}.xlsx`;
      a.click();
    } else {
      alert(JSON.stringify(job));
    }
  } catch (e) {
    alert(e.message || e);
  }
};

$("mailBtn").onclick = async () => {
  try {
    const filter = Object.fromEntries(params().entries());
    if (filter.has_email) filter.has_email = true;
    const campaign = await api("/api/v1/admin/mailings", {
      method: "POST",
      auth: true,
      body: JSON.stringify({
        subject: "Тестовая рассылка",
        body_html: "<p>Здравствуйте!</p>",
        dry_run: true,
        filter,
      }),
    });
    alert(`Dry-run: skipped=${campaign.skipped_count}, status=${campaign.status}`);
  } catch (e) {
    alert(e.message || e);
  }
};

loadMeta().then(search).catch(alert);
