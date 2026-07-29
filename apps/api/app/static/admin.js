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
  return ct.includes("application/json") ? res.json() : res;
}

const esc = (value) =>
  String(value ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

const ROLE_LABELS = {
  chief: "Главный врач",
  deputy: "Заместитель",
  pathology_head: "Зав. отделением патологии",
  head: "Зав. отделением",
  other: "Другое",
};

const FIELD_LABELS = {
  address: "Адрес",
  phones: "Телефон",
  emails: "Email",
  website: "Сайт",
  chief_physician: "Главный врач",
  pathology_head: "Отделение патологии",
  nmic_ref: "Связь с НМИЦ",
};

function filters() {
  const p = new URLSearchParams();
  if ($("q").value.trim()) p.set("q", $("q").value.trim());
  if ($("type").value) p.set("type", $("type").value);
  if ($("region").value) p.set("region", $("region").value);
  if ($("city").value.trim()) p.set("city", $("city").value.trim());
  if ($("hasEmail").checked) p.set("has_email", "true");
  if ($("hasChief").checked) p.set("has_chief", "true");
  return p;
}

function filterBody() {
  const body = Object.fromEntries(filters().entries());
  if (body.has_email) body.has_email = true;
  if (body.has_chief) body.has_chief = true;
  return body;
}

async function loadMeta() {
  const [types, regions, stats] = await Promise.all([
    api("/api/v1/meta/types"),
    api("/api/v1/meta/regions"),
    api("/api/v1/meta/stats"),
  ]);
  types.forEach((t) => $("type").append(new Option(t.label, t.code)));
  regions.forEach((r) => $("region").append(new Option(r, r)));
  $("meta").textContent = `Всего в базе: ${stats.total}`;
}

async function search() {
  const p = filters();
  p.set("page_size", "50");
  const data = await api(`/api/v1/institutions?${p}`);
  $("meta").textContent = `Найдено: ${data.total} (показано ${data.items.length})`;
  $("rows").innerHTML = data.items
    .map(
      (item) => `<tr data-id="${item.id}">
        <td>${esc(item.name)}</td>
        <td>${esc(item.type)}</td>
        <td>${esc(item.city)}</td>
        <td>${item.chief_physician ? esc(item.chief_physician) : '<span class="empty">—</span>'}</td>
        <td>${item.pathology_head ? esc(item.pathology_head) : '<span class="empty">—</span>'}</td>
        <td>${esc((item.phones || [])[0] || "")}<br /><span class="dim">${esc((item.emails || [])[0] || "")}</span></td>
      </tr>`
    )
    .join("");
  $("rows")
    .querySelectorAll("tr")
    .forEach((tr) => {
      tr.onclick = () => showCard(data.items.find((i) => i.id === tr.dataset.id));
    });
}

let currentId = null;

async function showCard(item) {
  currentId = item.id;
  $("card").classList.remove("hidden");
  $("cardTitle").textContent = item.name;
  const facts = [
    ["Тип", item.type],
    ["Регион", item.region],
    ["Город", item.city],
    ["Адрес", item.address],
    ["Телефоны", (item.phones || []).join(", ")],
    ["Email", (item.emails || []).join(", ")],
    ["Сайт", item.website],
    ["Главный врач", item.chief_physician],
    ["Отделение патологии", item.pathology_head],
    ["НМИЦ", item.nmic_ref],
    ["Источник", item.source_url],
  ];
  $("cardFacts").innerHTML = facts
    .filter(([, value]) => value)
    .map(([label, value]) => `<dt>${esc(label)}</dt><dd>${esc(value)}</dd>`)
    .join("");
  await loadPersons(item.id);
}

async function loadPersons(institutionId) {
  const box = $("cardPersons");
  try {
    const data = await api(`/api/v1/institutions/${institutionId}/persons?min_confidence=low`);
    if (!data.items.length) {
      box.innerHTML = '<p class="empty">Персоны не найдены — запустите обогащение.</p>';
      return;
    }
    box.innerHTML = data.items
      .map(
        (p) => `<div class="person">
          <div>
            <strong>${esc(p.full_name)}</strong>
            <span class="badge ${esc(p.confidence)}">${esc(p.confidence)}</span>
            ${p.verified_manually ? '<span class="badge verified">проверено</span>' : ""}
            <div class="dim">${esc(ROLE_LABELS[p.role] || p.role)}${p.department ? " · " + esc(p.department) : ""}</div>
            <a class="dim" href="${esc(p.source_url)}" target="_blank" rel="noopener">источник</a>
          </div>
          <button type="button" class="ghost" data-verify="${p.id}" ${p.verified_manually ? "disabled" : ""}>Подтвердить</button>
        </div>`
      )
      .join("");
    box.querySelectorAll("[data-verify]").forEach((btn) => {
      btn.onclick = async () => {
        await api(`/api/v1/admin/persons/${btn.dataset.verify}`, {
          method: "PATCH",
          auth: true,
          body: JSON.stringify({ verified_manually: true }),
        });
        await loadPersons(institutionId);
        await search();
      };
    });
  } catch (e) {
    box.innerHTML = `<p class="empty">${esc(e.message || e)}</p>`;
  }
}

async function loadQuality() {
  const data = await api("/api/v1/admin/metrics/completeness", { auth: true });
  $("qualityFields").innerHTML = Object.entries(data.fields)
    .map(
      ([key, value]) => `<div class="metric">
        <span class="metric-label">${esc(FIELD_LABELS[key] || key)}</span>
        <span class="metric-value">${value.pct}%</span>
        <span class="dim">${value.filled} из ${data.total}</span>
        <div class="bar"><i style="width:${Math.min(value.pct, 100)}%"></i></div>
      </div>`
    )
    .join("");
  $("qualityTypes").innerHTML = data.by_type
    .map(
      (t) => `<tr>
        <td>${esc(t.label)}</td><td>${t.total}</td><td>${t.chief_pct}%</td>
        <td>${t.email_pct}%</td><td>${t.phone_pct}%</td><td>${t.site_pct}%</td>
      </tr>`
    )
    .join("");
  const persons = Object.entries(data.persons).map(([k, v]) => `${esc(k)}: <strong>${v}</strong>`);
  const attempts = Object.entries(data.attempts).map(([k, v]) => `${esc(k)}: <strong>${v}</strong>`);
  $("qualityAttempts").innerHTML =
    `<div class="metric"><span class="metric-label">Персоны</span><span>${persons.join(" · ") || "—"}</span></div>` +
    `<div class="metric"><span class="metric-label">Попытки обхода</span><span>${attempts.join(" · ") || "—"}</span></div>`;
}

async function loadQueue() {
  const p = new URLSearchParams();
  if ($("queueRole").value) p.set("role", $("queueRole").value);
  if ($("queueConfidence").value) p.set("confidence", $("queueConfidence").value);
  if ($("queueUnverified").checked) p.set("unverified_only", "true");
  p.set("limit", "100");
  const data = await api(`/api/v1/admin/persons?${p}`, { auth: true });
  $("queueMeta").textContent = `Всего подходит: ${data.total} (показано ${data.items.length})`;
  $("queueRows").innerHTML = data.items
    .map(
      (p) => `<tr>
        <td>${esc(p.full_name)}</td>
        <td>${esc(ROLE_LABELS[p.role] || p.role)}</td>
        <td>${esc(p.position_raw || "")}</td>
        <td><span class="badge ${esc(p.confidence)}">${esc(p.confidence)}</span></td>
        <td><a href="${esc(p.source_url)}" target="_blank" rel="noopener">открыть</a></td>
        <td><button type="button" class="ghost" data-verify="${p.id}">Подтвердить</button></td>
      </tr>`
    )
    .join("");
  $("queueRows")
    .querySelectorAll("[data-verify]")
    .forEach((btn) => {
      btn.onclick = async () => {
        await api(`/api/v1/admin/persons/${btn.dataset.verify}`, {
          method: "PATCH",
          auth: true,
          body: JSON.stringify({ verified_manually: true }),
        });
        await loadQueue();
      };
    });
}

document.querySelectorAll(".tab").forEach((tab) => {
  tab.onclick = () => {
    document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("active", t === tab));
    document.querySelectorAll(".tabpanel").forEach((panel) => {
      panel.classList.toggle("hidden", panel.id !== `tab-${tab.dataset.tab}`);
    });
    if (tab.dataset.tab === "quality") loadQuality().catch((e) => alert(e.message || e));
    if (tab.dataset.tab === "queue") loadQueue().catch((e) => alert(e.message || e));
  };
});

$("searchBtn").onclick = () => search().catch((e) => alert(e.message || e));
$("q").onkeydown = (e) => {
  if (e.key === "Enter") search().catch((err) => alert(err.message || err));
};
$("closeCard").onclick = () => $("card").classList.add("hidden");
$("apiKey").onchange = () => localStorage.setItem("pnc_api_key", $("apiKey").value.trim());
$("apiKey").value = localStorage.getItem("pnc_api_key") || "";
$("queueBtn").onclick = () => loadQueue().catch((e) => alert(e.message || e));

$("exportBtn").onclick = async () => {
  try {
    const job = await api("/api/v1/admin/export", {
      method: "POST",
      auth: true,
      body: JSON.stringify(filterBody()),
    });
    if (job.status !== "done" || !job.result_json?.download) {
      alert(`Экспорт не удался: ${job.error || job.status}`);
      return;
    }
    const res = await fetch(job.result_json.download, { headers: { "X-API-Key": apiKey() } });
    const blob = await res.blob();
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `perinatal-contacts-${job.id}.xlsx`;
    a.click();
    URL.revokeObjectURL(a.href);
  } catch (e) {
    alert(e.message || e);
  }
};

$("mailBtn").onclick = () => $("mailDialog").showModal();

$("mailPreviewBtn").onclick = async () => {
  try {
    const data = await api("/api/v1/admin/mailings/preview", {
      method: "POST",
      auth: true,
      body: JSON.stringify({
        subject: $("mailSubject").value,
        body_html: $("mailBody").value,
        filter: filterBody(),
      }),
    });
    $("mailPreview").innerHTML =
      `<p class="dim">Получателей: <strong>${data.total_recipients}</strong>, из них с обращением по ФИО: <strong>${data.personalized_count}</strong></p>` +
      data.samples
        .map((s) => `<div class="sample"><div class="dim">${esc(s.email)}</div><strong>${esc(s.subject)}</strong>${s.body_html}</div>`)
        .join("");
  } catch (e) {
    alert(e.message || e);
  }
};

$("mailSendBtn").onclick = async () => {
  try {
    const campaign = await api("/api/v1/admin/mailings", {
      method: "POST",
      auth: true,
      body: JSON.stringify({
        subject: $("mailSubject").value,
        body_html: $("mailBody").value,
        dry_run: true,
        filter: filterBody(),
      }),
    });
    alert(`Dry-run завершён: адресатов ${campaign.skipped_count}, отправлено ${campaign.sent_count}`);
  } catch (e) {
    alert(e.message || e);
  }
};

$("enrichBtn").onclick = async () => {
  if (!confirm("Запустить обогащение 25 учреждений без главврача? Это займёт несколько минут.")) return;
  try {
    const body = { limit: 25, only_missing_chief: true };
    if ($("region").value) body.region = $("region").value;
    if ($("type").value) body.type = $("type").value;
    const job = await api("/api/v1/admin/jobs/enrich", { method: "POST", auth: true, body: JSON.stringify(body) });
    const r = job.result_json || {};
    alert(
      job.status === "done"
        ? `Обработано: ${r.processed}\nНайдено сайтов: ${r.sites_found}\nГлавврачей: ${r.chief_found}\nОтделений патологии: ${r.pathology_found}\nEmail добавлено: ${r.emails_added}`
        : `Ошибка: ${job.error}`
    );
    await search();
  } catch (e) {
    alert(e.message || e);
  }
};

$("enrichOneBtn").onclick = async () => {
  if (!currentId) return;
  try {
    const job = await api("/api/v1/admin/jobs/enrich", {
      method: "POST",
      auth: true,
      body: JSON.stringify({ institution_id: currentId, force: true }),
    });
    alert(job.status === "done" ? JSON.stringify(job.result_json.items?.[0] || {}, null, 2) : `Ошибка: ${job.error}`);
    await showCard(await api(`/api/v1/institutions/${currentId}`));
  } catch (e) {
    alert(e.message || e);
  }
};

loadMeta().then(search).catch((e) => alert(e.message || e));
