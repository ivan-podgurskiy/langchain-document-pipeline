/* Document Pipeline Dashboard */

const API_BASE = "";

function $(sel, ctx = document) {
  return ctx.querySelector(sel);
}

function $$(sel, ctx = document) {
  return [...ctx.querySelectorAll(sel)];
}

// Navigation
$$(".nav-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    $$(".nav-btn").forEach((b) => b.classList.remove("active"));
    $$(".view").forEach((v) => v.classList.remove("active"));
    btn.classList.add("active");
    const viewId = "view-" + btn.dataset.view;
    $(`#${viewId}`).classList.add("active");

    if (btn.dataset.view === "documents") {
      document.getElementById("document-detail")?.classList.add("hidden");
      document.getElementById("documents-list")?.classList.remove("hidden");
      loadDocuments();
    }
    if (btn.dataset.view === "upload") loadDocumentsForQuery();
    if (btn.dataset.view === "query") loadDocumentsForQuery();
    if (btn.dataset.view === "costs") loadCosts();
  });
});

// Documents list
async function loadDocuments() {
  const list = $("#documents-list");
  const detail = $("#document-detail");
  list.classList.remove("hidden");
  detail.classList.add("hidden");
  list.innerHTML = '<span class="loading">Loading...</span>';

  try {
    const res = await fetch(API_BASE + "/documents/");
    if (!res.ok) throw new Error(res.statusText);
    const docs = await res.json();
    if (!Array.isArray(docs)) throw new Error("Invalid API response");
    if (docs.length === 0) {
      list.innerHTML = `
        <div class="empty-state">
          <p>No documents yet.</p>
          <p>Upload a PDF to get started.</p>
        </div>
      `;
      return;
    }
    list.innerHTML = docs
      .map(
        (d) => `
      <div class="doc-card" data-id="${d.id}">
        <div class="doc-card-filename">${escapeHtml(d.filename)}</div>
        <div class="doc-card-meta">
          <span>${d.page_count} pages</span>
          <span>${d.chunk_count} chunks</span>
          <span class="status-badge status-${d.status}">${d.status}</span>
          <span>${formatDate(d.created_at)}</span>
        </div>
      </div>
    `
      )
      .join("");

    list.querySelectorAll(".doc-card").forEach((card) => {
      card.addEventListener("click", () => showDocumentDetail(card.dataset.id));
    });
  } catch (err) {
    list.innerHTML = `<p class="error-msg">Failed to load: ${err.message}</p>`;
  }
}

async function showDocumentDetail(id) {
  const list = $("#documents-list");
  const detail = $("#document-detail");
  const content = $("#document-detail-content");
  list.classList.add("hidden");
  detail.classList.remove("hidden");
  content.innerHTML = '<span class="loading">Loading...</span>';

  try {
    const res = await fetch(API_BASE + "/documents/" + id);
    if (!res.ok) throw new Error(res.statusText);
    const doc = await res.json();

    const pdfUrl = API_BASE + "/documents/" + id + "/file";
    const pdfAvailable = await checkPdfAvailable(pdfUrl);
    const pdfViewerHtml = pdfAvailable
      ? `
      <div class="pdf-viewer-section">
        <h3>PDF Preview</h3>
        <div class="pdf-viewer-container">
          <iframe src="${pdfUrl}#toolbar=1" class="pdf-viewer" title="PDF document"></iframe>
        </div>
      </div>`
      : `
      <div class="pdf-viewer-section">
        <h3>PDF Preview</h3>
        <div class="pdf-unavailable">
          <p>PDF file not available. This document was likely ingested before file storage was enabled.</p>
          <div class="pdf-attach-area">
            <input type="file" id="attach-pdf-input" accept=".pdf" hidden>
            <button type="button" class="btn btn-primary" id="attach-pdf-btn">Attach PDF</button>
            <span id="attach-pdf-status" class="attach-status"></span>
          </div>
        </div>
      </div>`;

    content.innerHTML = `
      <div class="doc-detail-header">
        <h2>${escapeHtml(doc.filename)}</h2>
        <div class="doc-detail-meta">
          <span>ID: <code>${doc.id}</code></span>
          <span>Pages: ${doc.page_count}</span>
          <span>Chunks: ${doc.chunk_count}</span>
          <span class="status-badge status-${doc.status}">${doc.status}</span>
          <span>Ingested: ${formatDate(doc.created_at)}</span>
        </div>
      </div>
      ${pdfViewerHtml}
      <div class="extract-section">
        <h3>Structured extraction</h3>
        <p class="extract-hint">Run HCPCS and demographics chains on this document's text.</p>
        <button type="button" class="btn btn-primary" id="run-extract-btn">Run extraction</button>
        <div id="extract-result" class="extract-result hidden"></div>
      </div>
      <div class="chunks-section">
        <h3>Chunks (${doc.chunks.length})</h3>
        ${doc.chunks
          .map(
            (c) => `
          <div class="chunk-item">
            <div class="chunk-header" data-expanded="false">
              <span class="chunk-preview">${escapeHtml(c.content_preview)}</span>
              <span class="chunk-badge">Page ${c.page_number} · #${c.chunk_index}</span>
            </div>
            <div class="chunk-body hidden">
              <div class="chunk-content">${escapeHtml(c.content)}</div>
            </div>
          </div>
        `
          )
          .join("")}
      </div>
    `;

    content.querySelectorAll(".chunk-header").forEach((h) => {
      h.addEventListener("click", () => {
        const body = h.nextElementSibling;
        const expanded = h.dataset.expanded === "true";
        h.dataset.expanded = !expanded;
        body.classList.toggle("hidden", expanded);
      });
    });

    const attachBtn = content.querySelector("#attach-pdf-btn");
    const attachInput = content.querySelector("#attach-pdf-input");
    const attachStatus = content.querySelector("#attach-pdf-status");
    if (attachBtn && attachInput && attachStatus) {
      attachBtn.addEventListener("click", () => attachInput.click());
      attachInput.addEventListener("change", async (e) => {
        const file = e.target.files?.[0];
        if (!file) return;
        attachBtn.disabled = true;
        attachStatus.textContent = "Uploading…";
        attachStatus.className = "attach-status";
        try {
          const form = new FormData();
          form.append("file", file);
          const res = await fetch(API_BASE + "/documents/" + id + "/file", {
            method: "PUT",
            body: form,
          });
          const data = await res.json().catch(() => ({}));
          if (res.ok) {
            attachStatus.textContent = "Attached successfully. ";
            attachStatus.className = "attach-status success";
            attachStatus.innerHTML += "<button type='button' class='btn-link' id='refresh-pdf'>Show preview</button>";
            content.querySelector("#refresh-pdf")?.addEventListener("click", () => showDocumentDetail(id));
          } else {
            attachStatus.textContent = data.detail || res.statusText || "Failed";
            attachStatus.className = "attach-status error";
          }
        } catch (err) {
          attachStatus.textContent = err.message;
          attachStatus.className = "attach-status error";
        } finally {
          attachBtn.disabled = false;
          attachInput.value = "";
        }
      });
    }

    const extractBtn = content.querySelector("#run-extract-btn");
    const extractResult = content.querySelector("#extract-result");
    if (extractBtn && extractResult) {
      extractBtn.addEventListener("click", () => runExtraction(id, extractBtn, extractResult));
    }
  } catch (err) {
    content.innerHTML = `<p class="error-msg">Failed to load: ${err.message}</p>`;
  }
}

$("#back-to-list")?.addEventListener("click", () => {
  $("#document-detail").classList.add("hidden");
  $("#documents-list").classList.remove("hidden");
  loadDocuments();
});

$("#refresh-docs")?.addEventListener("click", loadDocuments);

// Upload
const uploadZone = $("#upload-zone");
const fileInput = $("#file-input");
const uploadResult = $("#upload-result");

$("#browse-files")?.addEventListener("click", () => fileInput?.click());

fileInput?.addEventListener("change", (e) => {
  const file = e.target.files?.[0];
  if (file) uploadFile(file);
});

uploadZone?.addEventListener("dragover", (e) => {
  e.preventDefault();
  uploadZone.classList.add("dragover");
});

uploadZone?.addEventListener("dragleave", () => {
  uploadZone.classList.remove("dragover");
});

uploadZone?.addEventListener("drop", (e) => {
  e.preventDefault();
  uploadZone.classList.remove("dragover");
  const file = e.dataTransfer?.files?.[0];
  if (file && file.name.toLowerCase().endsWith(".pdf")) uploadFile(file);
});

async function uploadFile(file) {
  uploadResult.classList.add("hidden");
  uploadResult.className = "upload-result";

  const form = new FormData();
  form.append("file", file);

  try {
    const res = await fetch(API_BASE + "/ingest/", {
      method: "POST",
      body: form,
    });
    const data = await res.json().catch(() => ({}));
    uploadResult.classList.remove("hidden");
    if (res.ok) {
      uploadResult.classList.add("success");
      uploadResult.innerHTML = `
        <strong>Uploaded successfully</strong><br>
        Document ID: <code>${data.document_id}</code><br>
        Chunks: ${data.chunk_count}
      `;
      fileInput.value = "";
      loadDocuments();
    } else {
      uploadResult.classList.add("error");
      uploadResult.innerHTML = `<strong>Error</strong>: ${data.detail || res.statusText}`;
    }
  } catch (err) {
    uploadResult.classList.remove("hidden");
    uploadResult.classList.add("error");
    uploadResult.innerHTML = `<strong>Error</strong>: ${err.message}`;
  }
}

// Query
async function loadDocumentsForQuery() {
  try {
    const res = await fetch(API_BASE + "/documents/");
    if (!res.ok) return;
    const docs = await res.json();
    const select = $("#query-document");
    if (!select) return;
    select.innerHTML = '<option value="">All documents</option>' + docs.map((d) => `<option value="${d.id}">${escapeHtml(d.filename)}</option>`).join("");
  } catch (_) {}
}

$("#query-form")?.addEventListener("submit", async (e) => {
  e.preventDefault();
  const question = $("#query-question")?.value?.trim();
  const documentId = $("#query-document")?.value || undefined;
  const submitBtn = $("#query-submit");
  const resultDiv = $("#query-result");

  if (!question || question.length < 3) return;

  submitBtn.disabled = true;
  resultDiv.classList.add("hidden");
  resultDiv.innerHTML = '<span class="loading">Searching...</span>';
  resultDiv.classList.remove("hidden");

  try {
    const res = await fetch(API_BASE + "/query/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, document_id: documentId || null }),
    });
    const data = await res.json().catch(() => ({}));

    if (!res.ok) {
      resultDiv.innerHTML = `<p class="error-msg">${data.detail || res.statusText}</p>`;
      return;
    }

    resultDiv.innerHTML = `
      <div class="answer-block">
        <h4>Answer</h4>
        <p>${escapeHtml(data.answer)}</p>
        <p class="doc-detail-meta">Model: ${data.model} · Tokens: ${data.input_tokens} in / ${data.output_tokens} out · Multi-query: ${data.multi_query ? "yes" : "no"}</p>
      </div>
      ${data.sources?.length ? `
      <div class="sources-block">
        <h4>Sources (${data.sources.length})</h4>
        ${data.sources
          .map(
            (s) => `
          <div class="source-item">
            <span class="score">Similarity: ${(s.similarity_score * 100).toFixed(1)}%</span>
            <span> · Page ${s.page_number}</span>
            <p style="margin: 0.5rem 0 0;">${escapeHtml(s.content)}</p>
          </div>
        `
          )
          .join("")}
      </div>
      ` : ""}
    `;
  } catch (err) {
    resultDiv.innerHTML = `<p class="error-msg">${err.message}</p>`;
  } finally {
    submitBtn.disabled = false;
  }
});

// Costs
async function loadCosts() {
  const content = $("#costs-content");
  content.innerHTML = '<span class="loading">Loading...</span>';

  try {
    const res = await fetch(API_BASE + "/costs/");
    if (!res.ok) throw new Error(res.statusText);
    const data = await res.json();

    content.innerHTML = `
      <div class="cost-summary">
        <dl>
          <dt>Total cost</dt>
          <dd>$${data.total_cost_usd.toFixed(4)}</dd>
          <dt>Total input tokens</dt>
          <dd>${data.total_input_tokens.toLocaleString()}</dd>
          <dt>Total output tokens</dt>
          <dd>${data.total_output_tokens.toLocaleString()}</dd>
          <dt>Calls</dt>
          <dd>${data.call_count}</dd>
        </dl>
      </div>
      ${Object.keys(data.by_model || {}).length ? `
      <h4 style="margin-bottom: 0.5rem;">By model</h4>
      ${Object.entries(data.by_model)
        .map(
          ([model, m]) => `
        <div class="cost-summary">
          <strong>${model}</strong>
          <dl>
            <dt>Cost</dt>
            <dd>$${m.total_cost_usd.toFixed(4)}</dd>
            <dt>Input / Output tokens</dt>
            <dd>${m.input_tokens.toLocaleString()} / ${m.output_tokens.toLocaleString()}</dd>
          </dl>
        </div>
      `
        )
        .join("")}
      ` : ""}
    `;
  } catch (err) {
    content.innerHTML = `<p class="error-msg">${err.message}</p>`;
  }
}

$("#refresh-costs")?.addEventListener("click", loadCosts);

async function runExtraction(documentId, button, resultEl) {
  button.disabled = true;
  resultEl.classList.remove("hidden");
  resultEl.innerHTML = '<span class="loading">Extracting...</span>';

  try {
    const res = await fetch(API_BASE + "/extract/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ document_id: documentId, chains: ["hcpcs", "demographics"] }),
    });
    const data = await res.json().catch(() => ({}));

    if (!res.ok) {
      const detail = typeof data.detail === "string" ? data.detail : res.statusText;
      resultEl.innerHTML = `<p class="error-msg">${escapeHtml(detail)}</p>`;
      return;
    }

    const hcpcsHtml =
      data.hcpcs_codes?.length > 0
        ? `<ul class="extract-list">${data.hcpcs_codes
            .map(
              (c) =>
                `<li><code>${escapeHtml(c.code)}</code> — ${escapeHtml(c.description)}${
                  c.quantity != null ? ` · qty ${c.quantity}` : ""
                }</li>`
            )
            .join("")}</ul>`
        : "<p>No HCPCS codes found.</p>";

    const patient = data.patient;
    const patientHtml = patient
      ? `<p><strong>${escapeHtml(patient.first_name)} ${escapeHtml(patient.last_name)}</strong></p>
         <p class="doc-detail-meta">DOB: ${escapeHtml(patient.date_of_birth || "—")} · MRN: ${escapeHtml(
           patient.mrn || "—"
         )}</p>
         ${
           patient.diagnoses?.length
             ? `<ul class="extract-list">${patient.diagnoses
                 .map(
                   (d) =>
                     `<li><code>${escapeHtml(d.code)}</code> — ${escapeHtml(d.description)}${
                       d.primary ? " (primary)" : ""
                     }</li>`
                 )
                 .join("")}</ul>`
             : ""
         }`
      : "<p>No patient demographics extracted.</p>";

    const warningsHtml =
      data.warnings?.length > 0
        ? `<p class="extract-warnings">${data.warnings.map((w) => escapeHtml(w)).join("<br>")}</p>`
        : "";

    resultEl.innerHTML = `
      <div class="extract-block">
        <h4>HCPCS codes (${data.hcpcs_codes?.length || 0})</h4>
        ${hcpcsHtml}
      </div>
      <div class="extract-block">
        <h4>Patient demographics</h4>
        ${patientHtml}
      </div>
      <p class="doc-detail-meta">Model: ${escapeHtml(data.model)} · Tokens: ${data.input_tokens} in / ${data.output_tokens} out</p>
      ${warningsHtml}
    `;
  } catch (err) {
    resultEl.innerHTML = `<p class="error-msg">${escapeHtml(err.message)}</p>`;
  } finally {
    button.disabled = false;
  }
}

// Helpers
async function checkPdfAvailable(url) {
  try {
    const res = await fetch(url, { method: "HEAD" });
    return res.ok;
  } catch {
    return false;
  }
}

function escapeHtml(s) {
  if (s == null) return "";
  const div = document.createElement("div");
  div.textContent = s;
  return div.innerHTML;
}

function formatDate(iso) {
  if (!iso) return "";
  try {
    const d = new Date(iso);
    return d.toLocaleString();
  } catch {
    return iso;
  }
}

// Init
loadDocuments();
loadDocumentsForQuery();
