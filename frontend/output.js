(() => {
  const baseRenderPass = renderPass;
  const baseRenderReport = renderReport;

  const outputEsc = (value = "") => String(value).replace(/[&<>'"]/g, (char) => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"}[char]));

  function outputToolbar(active = "revised") {
    return `<div class="output-toolbar" aria-label="Document output controls">
      <div class="output-view-switch" role="group" aria-label="Choose document view">
        <button type="button" data-output-view="revised" class="${active === "revised" ? "active" : ""}">Revised</button>
        <button type="button" data-output-view="compare" class="${active === "compare" ? "active" : ""}">Compare</button>
        <button type="button" data-output-view="original" class="${active === "original" ? "active" : ""}">Original</button>
      </div>
      <div class="output-actions">
        <button type="button" data-output-action="copy">Copy revised</button>
        <button type="button" data-output-action="download">Download .txt</button>
      </div>
    </div>`;
  }

  function transactionComparison(item) {
    const donorPairs = item.donors.map((donor) => `<div class="repair-pair"><span><b>DONOR BEFORE</b>${outputEsc(donor.original_text)}</span><span><b>DONOR AFTER</b>${outputEsc(donor.proposed_repair)}</span></div>`).join("");
    const receiverChanged = item.receiver?.proposed_text && item.receiver.proposed_text !== item.receiver.original_text;
    const receiverDetail = receiverChanged
      ? `<div class="repair-pair receiver-pair"><span><b>CENTRE BEFORE</b>${outputEsc(item.receiver.original_text)}</span><span><b>CENTRE AFTER</b>${outputEsc(item.receiver.proposed_text)}</span></div>`
      : `<p class="receiver-note"><b>CENTRE PRESERVED</b>The canonical treatment in ${outputEsc(item.centre)} already contained the complete duplicated payload, so no receiver expansion was required.</p>`;
    return `<article class="compare-transaction"><header><small>${outputEsc(item.transaction_id)}</small><strong>${item.donors.length} donor${item.donors.length === 1 ? "" : "s"} → ${outputEsc(item.centre)}</strong></header>${donorPairs}${receiverDetail}</article>`;
  }

  function deliverableView(view = "revised") {
    if (!state.pass) return `<div class="output-empty">No revised document has been generated.</div>`;
    const original = state.pass.original_document || state.originalText;
    const revised = state.pass.revised_document || "";
    if (view === "original") {
      return `<div class="document-view"><div class="document-label"><span>IMMUTABLE ORIGINAL</span><small>${original.trim().split(/\s+/).filter(Boolean).length} words</small></div><pre>${outputEsc(original)}</pre></div>`;
    }
    if (view === "compare") {
      const comparisons = state.pass.transactions.map(transactionComparison).join("") || `<article class="compare-transaction"><strong>No committed changes</strong><p>The document was preserved because no safe consolidation was authorised.</p></article>`;
      return `<div class="compare-view"><div class="document-label"><span>TRACEABLE TRANSFORMATION</span><small>${state.pass.transactions.length} committed transaction${state.pass.transactions.length === 1 ? "" : "s"}</small></div>${comparisons}</div>`;
    }
    return `<div class="document-view"><div class="document-label"><span>COMPLETE REVISED DOCUMENT</span><small>${revised.trim().split(/\s+/).filter(Boolean).length} words</small></div><pre>${outputEsc(revised)}</pre></div>`;
  }

  function deliverableWorkbench(active = "revised") {
    return `<article class="report-card deliverable-card wide"><div class="deliverable-heading"><div><small>DELIVERABLE OUTPUT</small><strong>Original → Revised → Auditable change record</strong></div><span class="output-ready">READY TO RETURN</span></div>${outputToolbar(active)}<div id="deliverableView" class="deliverable-body">${deliverableView(active)}</div></article>`;
  }

  function appendWorkbench() {
    const reportList = document.querySelector("#resultContent .report-list");
    if (!reportList || reportList.querySelector(".deliverable-card")) return;
    const template = document.createElement("template");
    template.innerHTML = deliverableWorkbench("revised").trim();
    const workbench = template.content.firstElementChild;
    const stopCard = [...reportList.children].find((node) => node.textContent.includes("STOP DECISION") || node.textContent.includes("STOP REASON"));
    if (stopCard) stopCard.insertAdjacentElement("afterend", workbench);
    else reportList.appendChild(workbench);
  }

  async function copyRevisedText() {
    const text = state.pass?.revised_document || "";
    if (!text) throw new Error("No revised document is available to copy.");
    try {
      await navigator.clipboard.writeText(text);
    } catch (_error) {
      const temporary = document.createElement("textarea");
      temporary.value = text;
      temporary.setAttribute("readonly", "");
      temporary.style.position = "fixed";
      temporary.style.opacity = "0";
      document.body.appendChild(temporary);
      temporary.select();
      const copied = document.execCommand("copy");
      temporary.remove();
      if (!copied) throw new Error("Copy was blocked by the browser.");
    }
    document.querySelector("#auditMessage").textContent = "Complete revised document copied to the clipboard.";
  }

  function downloadRevisedText() {
    const text = state.pass?.revised_document || "";
    if (!text) throw new Error("No revised document is available to download.");
    const blob = new Blob([text], {type: "text/plain;charset=utf-8"});
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "repetita-gravity-revised.txt";
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(url);
    document.querySelector("#auditMessage").textContent = "Complete revised document downloaded as repetita-gravity-revised.txt.";
  }

  renderPass = function enhancedRenderPass() {
    baseRenderPass();
    appendWorkbench();
  };

  renderReport = function enhancedRenderReport() {
    baseRenderReport();
    appendWorkbench();
  };

  document.querySelector("#resultContent").addEventListener("click", async (event) => {
    const viewButton = event.target.closest("[data-output-view]");
    const actionButton = event.target.closest("[data-output-action]");
    try {
      if (viewButton) {
        document.querySelectorAll("[data-output-view]").forEach((button) => button.classList.toggle("active", button.dataset.outputView === viewButton.dataset.outputView));
        const view = document.querySelector("#deliverableView");
        if (view) view.innerHTML = deliverableView(viewButton.dataset.outputView);
      } else if (actionButton?.dataset.outputAction === "copy") {
        await copyRevisedText();
      } else if (actionButton?.dataset.outputAction === "download") {
        downloadRevisedText();
      }
    } catch (error) {
      document.querySelector("#auditMessage").textContent = error.message;
      setSystem("OUTPUT ACTION BLOCKED", error.message, "warn");
    }
  });
})();
