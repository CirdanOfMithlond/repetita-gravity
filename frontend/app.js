const state = {
  step: 0,
  analysis: null,
  complexity: null,
  pass: null,
  originalText: "",
};

let offlineDemoPromise;

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];
const esc = (value = "") => String(value).replace(/[&<>'"]/g, (char) => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"}[char]));
const pct = (value) => `${Math.round(Number(value || 0) * 100)}%`;
const pretty = (value = "") => String(value).replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());

function setSystem(status, detail, tone = "ready") {
  $("#systemStatus").textContent = status;
  $("#statusDetail").textContent = detail;
  const dot = $(".status-dot");
  dot.style.background = tone === "bad" ? "var(--red)" : tone === "warn" ? "var(--amber)" : "var(--green)";
  dot.style.boxShadow = `0 0 10px ${tone === "bad" ? "var(--red)" : tone === "warn" ? "var(--amber)" : "var(--green)"}`;
}

function setStep(step) {
  state.step = step;
  $$('[data-step]').forEach((button) => {
    const number = Number(button.dataset.step);
    button.disabled = number > step + 1;
    button.classList.toggle("active", number === step);
    button.classList.toggle("done", number < step);
  });
}

async function offlineDemo() {
  if (!offlineDemoPromise) {
    offlineDemoPromise = fetch("./demo-data.json").then((response) => {
      if (!response.ok) throw new Error("Bundled demo data is unavailable");
      return response.json();
    });
  }
  return offlineDemoPromise;
}

async function api(path, payload) {
  setSystem("PROCESSING", "Running bounded analysis and deterministic checks.", "warn");
  try {
    const response = await fetch(path, {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(payload),
    });
    if (!response.ok) throw new Error("Live service unavailable");
    return await response.json();
  } catch (_error) {
    const demo = await offlineDemo();
    const canonical = (value) => String(value || "").replaceAll("\r\n", "\n").trim();
    if (canonical(payload.text) !== canonical(demo.sample)) {
      throw new Error("The public static demo certifies the bundled sample only. Run the Python service for custom documents.");
    }
    if (path === "/api/analyse") return demo.analyse;
    if (path === "/api/safe-pass") return demo.safe_pass;
    throw new Error("This operation requires the live Python service.");
  }
}

async function loadSample() {
  let text;
  try {
    const response = await fetch("/api/sample");
    if (!response.ok) throw new Error("Live sample unavailable");
    text = (await response.json()).text;
  } catch (_error) {
    text = (await offlineDemo()).sample;
  }
  $("#sourceText").value = text;
  state.originalText = text;
  $("#auditMessage").textContent = "Fictional adversarial sample loaded — no analysis run.";
}

function updateMetrics() {
  const document = state.analysis.document;
  const text = $("#sourceText").value;
  $("#wordMetric").textContent = text.trim().split(/\s+/).filter(Boolean).length.toLocaleString();
  $("#unitMetric").textContent = document.units.length;
  $("#sectionMetric").textContent = document.sections.length;
  $("#familyMetric").textContent = state.analysis.families.length;
  $("#pressureMetric").textContent = pct(document.resource_plan.context_pressure);
  $("#passMetric").textContent = state.complexity.planned_passes;
  $("#strategyLabel").textContent = `Strategy: ${document.resource_plan.strategy.replaceAll("_", " ")}`;
  $("#sourceHash").textContent = `Source units: ${document.units[0]?.unit_id || "none"} … immutable`;
}

function renderSections() {
  const sections = state.analysis.document.sections;
  const units = state.analysis.document.units;
  $("#mapTitle").textContent = "Document structure";
  $("#mapState").textContent = "READ";
  $("#mapContent").className = "scroll-content";
  $("#mapContent").innerHTML = `<div class="section-list">${sections.map((section) => {
    const count = units.filter((unit) => unit.location.section_id === section.id).length;
    return `<article class="section-card"><header><strong>${esc(section.title)}</strong><small>LEVEL ${section.level}</small></header><small>${count} semantic source unit${count === 1 ? "" : "s"}</small></article>`;
  }).join("")}</div>`;
  $("#resultTitle").textContent = "Resource plan";
  $("#resultContent").className = "scroll-content";
  $("#resultContent").innerHTML = `<div class="plan-grid"><article><small>SAFE INPUT BUDGET</small><strong>${state.analysis.document.resource_plan.safe_input_budget.toLocaleString()}</strong></article><article><small>ESTIMATED TOKENS</small><strong>${state.analysis.document.resource_plan.estimated_tokens.toLocaleString()}</strong></article></div><p class="rationale">${esc(state.analysis.document.resource_plan.rationale)}</p>`;
}

function renderLedger() {
  $("#mapTitle").textContent = "Conservation Ledger";
  $("#mapState").textContent = "INDEXED";
  $("#mapContent").innerHTML = `<div class="decision-list">${state.analysis.document.units.map((unit) => `<article class="decision-card"><header><strong>${esc(unit.location.section_title)}</strong><code>${esc(unit.unit_id)}</code></header><small>${esc(unit.text)}</small><div class="disposition preserve">${esc(unit.discourse_role)} · ${esc(unit.local_function)}</div></article>`).join("")}</div>`;
  $("#resultTitle").textContent = "Ledger invariants";
  renderChecks(state.analysis.invariants);
}

function familyCard(family, mode) {
  const scores = Object.entries(family.gravity_scores || {});
  const evidence = Object.values(family.pair_evidence || {});
  const meanComposite = evidence.length ? evidence.reduce((sum, item) => sum + Number(item.composite), 0) / evidence.length : 0;
  const decisionSummary = family.decisions.reduce((acc, item) => ({...acc, [item.disposition]:(acc[item.disposition] || 0) + 1}), {});
  const mappingSignal = mode === 3 ? `<div class="signal-row"><span>MEAN COMPOSITE</span><strong>${meanComposite.toFixed(2)}</strong><span>${evidence.length} pair${evidence.length === 1 ? "" : "s"} compared</span></div>` : "";
  const decisionSignal = mode === 4 ? `<div class="decision-summary">${Object.entries(decisionSummary).map(([key,value]) => `<span>${value} ${esc(pretty(key))}</span>`).join("")}</div>` : "";
  const centreSignal = mode >= 5 ? `<p class="centre">Centre → ${esc(family.gravity_centre)}</p><div class="centre-scores">${scores.map(([name, score]) => `<div class="centre-score"><div><span>${esc(name)}</span><strong>${Number(score).toFixed(2)}</strong></div><div class="score-bar"><i style="width:${Math.max(4, Number(score) * 100)}%"></i></div></div>`).join("")}</div><p class="gravity-reason">${esc(family.gravity_rationale)}</p>` : "";
  return `<article class="family-card"><header><strong>${esc(family.label)}</strong><small>${family.unit_ids.length} OCCURRENCES</small></header><div class="sections">${family.sections.map((section) => `<span>${esc(section)}</span>`).join("")}</div>${mappingSignal}${decisionSignal}${centreSignal}</article>`;
}

function renderFamilies(mode) {
  $("#mapTitle").textContent = mode === 3 ? "Candidate families" : mode === 4 ? "Occurrence decisions" : "Logical Gravity Centres";
  $("#mapState").textContent = mode === 3 ? "MAPPED" : mode === 4 ? "CLASSIFIED" : "CENTRED";
  $("#mapContent").innerHTML = `<div class="family-list">${state.analysis.families.map((family) => familyCard(family, mode)).join("") || `<article class="family-card"><strong>No candidate family crossed the conservative threshold.</strong></article>`}</div>`;
  if (mode === 4) {
    $("#resultTitle").textContent = "Disposition register";
    $("#resultContent").innerHTML = `<div class="decision-list">${state.analysis.families.flatMap((family) => family.decisions.map((decision) => `<article class="decision-card"><header><code>${esc(decision.unit_id)}</code><small>CONFIDENCE ${Number(decision.confidence).toFixed(2)}</small></header><div class="axis-grid"><div><small>SEMANTIC RELATION</small><strong>${esc(pretty(decision.semantic_relation))}</strong></div><div><small>LOCAL FUNCTION</small><strong>${esc(pretty(decision.local_function))}</strong></div><div><small>EDITORIAL DISPOSITION</small><strong>${esc(pretty(decision.disposition))}</strong></div></div><p>${esc(decision.rationale)}</p><div class="disposition ${decision.disposition.includes("preserve") ? "preserve" : decision.disposition.includes("review") ? "review" : ""}">${esc(pretty(decision.disposition))}</div></article>`)).join("")}</div>`;
  }
}

function renderPlan() {
  const plan = state.complexity;
  $("#resultTitle").textContent = "Adaptive pass plan";
  $("#verificationState").textContent = "BOUNDED";
  $("#verificationState").className = "pill warn";
  $("#resultContent").innerHTML = `<div class="plan-grid"><article><small>COMPLEXITY INDEX</small><strong>${Number(plan.complexity_index).toFixed(2)}</strong></article><article><small>INITIAL PASS CAP</small><strong>${plan.planned_passes}</strong></article><article><small>RECURRENCE DENSITY</small><strong>${pct(plan.repetition_density)}</strong></article><article><small>DISPERSION</small><strong>${pct(plan.thematic_dispersion)}</strong></article></div><p class="rationale">${esc(plan.rationale)}</p>`;
  $("#auditMessage").textContent = `Initial cap: ${plan.planned_passes}; may stop early, add one bounded pass, or roll back.`;
}

function renderPass() {
  const tx = state.pass.transactions;
  const audits = state.pass.family_audits || [];
  const auditCards = audits.map((audit) => {
    const theme = audit.adjudication?.theme_label || audit.family_id || "Runtime semantic layer";
    const auditKind = audit.family_id ? "FAMILY AUDIT" : "RUNTIME GATE";
    const tone = audit.status === "COMMITTED" || audit.status === "PRESERVED" ? "good" : audit.status === "HUMAN_REVIEW" || audit.status === "MODEL_UNAVAILABLE" ? "warn" : "bad";
    return `<article class="report-card model-audit ${tone}"><small>GPT-5.6 ${auditKind} · ${esc(audit.status)}</small><strong>${esc(theme)}</strong><p>${esc(audit.reason || "Bounded semantic decision recorded.")}</p></article>`;
  }).join("");
  $("#resultTitle").textContent = "Committed transactions";
  $("#verificationState").textContent = tx.length ? `${tx.length} COMMITTED` : "WITHHELD";
  $("#verificationState").className = tx.length ? "pill good" : "pill warn";
  $("#resultContent").innerHTML = `<div class="report-list">${tx.map((item) => `<article class="report-card transaction"><small>${esc(item.transaction_id)}</small><br><b>${item.donors.length} donor${item.donors.length === 1 ? "" : "s"} repaired</b><p>${esc(item.donors.map((donor) => donor.proposed_repair).join(" "))}</p><small>Centre: ${esc(item.centre)} · atomic ${esc(item.state)}</small></article>`).join("") || `<article class="report-card"><strong>No automatic rewrite authorised.</strong><p class="rationale">Semantic risk exceeds the deterministic engine’s competence.</p></article>`}${auditCards}<article class="report-card"><small>STOP DECISION</small><p>${esc(state.pass.stop_reason)}</p></article><article class="report-card"><small>REVISED DOCUMENT</small><div class="revised-document">${esc(state.pass.revised_document)}</div></article></div>`;
  $("#auditMessage").textContent = state.pass.stop_reason;
}

function renderChecks(checks) {
  $("#resultContent").className = "scroll-content";
  $("#resultContent").innerHTML = Object.entries(checks).map(([name, passed]) => `<div class="check-row"><span>${esc(name.replaceAll("_", " "))}</span><span class="${passed ? "pass" : "fail"}">${passed ? "PASS" : "FAIL"}</span></div>`).join("");
}

function renderVerification() {
  const report = state.pass.global_verification;
  const semantic = state.pass.global_semantic_verification || {status: "NOT_RUN"};
  const formalPassed = report.ledger_coverage === 1 && !report.failures.length;
  const certified = Boolean(state.pass.certification?.eligible);
  $("#resultTitle").textContent = "Global conservation";
  $("#verificationState").textContent = certified ? "CERTIFIED" : formalPassed ? "FORMAL GATES PASSED" : "NOT VERIFIED";
  $("#verificationState").className = certified || formalPassed ? "pill good" : "pill bad";
  $("#coverageMetric").textContent = pct(report.ledger_coverage);
  $("#coverageMetric").style.color = formalPassed ? "var(--green)" : "var(--red)";
  const formalChecks = {
    every_original_unit_accounted: report.ledger_coverage === 1,
    no_hard_anchor_missing: report.missing_hard_anchors.length === 0,
    all_transactions_committed: report.all_transactions_committed,
    transaction_checks_passed: report.all_transaction_checks_passed,
    no_new_candidate_family: report.newly_introduced_family_count === 0,
  };
  renderChecks(formalChecks);
  const semanticLabel = semantic.mode === "bundled_reference_audit"
    ? "GPT-5.6 REFERENCE AUDIT + PYTHON RE-VERIFICATION"
    : "INDEPENDENT GPT-5.6 WHOLE-DOCUMENT REVIEW";
  $("#resultContent").insertAdjacentHTML("beforeend", `<div class="semantic-gate"><small>${semanticLabel}</small><strong class="${semantic.status === "PASSED" ? "pass" : semantic.status === "FAILED" ? "fail" : "pending"}">${esc(semantic.status)}</strong><p>${esc(semantic.reason || (semantic.status === "PASSED" ? "Every source unit and document-level semantic invariant passed independent review." : "Semantic certification remains withheld."))}</p></div>`);
  setSystem(certified ? state.pass.certification.label : formalPassed ? "FORMAL GATES PASSED" : "NOT VERIFIED", certified ? "Formal and independent semantic gates passed." : formalPassed ? "Independent global semantic certification remains pending." : "A critical conservation condition failed.", certified || formalPassed ? "ready" : "bad");
}

function renderReport() {
  const report = state.pass.global_verification;
  const tx = state.pass.transactions;
  const formalPassed = report.ledger_coverage === 1 && !report.failures.length;
  const certification = state.pass.certification || {eligible: false, label: "NOT YET VERIFIED", reasons: []};
  const semantic = state.pass.global_semantic_verification || {status: "NOT_RUN"};
  const transactionDetails = tx.map((item) => `<article class="report-card transaction wide"><small>COMMITTED FAMILY TRANSACTION · ${esc(item.transaction_id)}</small><strong>${item.donors.length} donor repaired → ${esc(item.centre)}</strong>${item.donors.map((donor) => `<div class="repair-pair"><span><b>BEFORE</b>${esc(donor.original_text)}</span><span><b>AFTER</b>${esc(donor.proposed_repair)}</span></div>`).join("")}</article>`).join("");
  $("#resultTitle").textContent = "Gravity Report";
  const certificationSummary = certification.eligible
    ? `${report.accounted_unit_count}/${report.original_unit_count} ledger units reconciled; 0 unresolved; formal conservation and independent semantic review passed.`
    : certification.reasons.join(" · ") || "At least one critical certification gate remains unresolved.";
  $("#resultContent").innerHTML = `<div class="report-list"><article class="report-card certification ${certification.eligible ? "verified" : formalPassed ? "pending" : "failed"}"><small>FINAL CERTIFICATION</small><strong>${esc(certification.label)}</strong><p>${esc(certificationSummary)}</p></article><div class="report-kpis"><article class="report-card"><small>LEDGER COVERAGE</small><strong>${report.accounted_unit_count} / ${report.original_unit_count}</strong></article><article class="report-card"><small>TRANSACTIONS</small><strong>${tx.length}</strong></article><article class="report-card"><small>ANCHOR LOSSES</small><strong>${report.missing_hard_anchors.length}</strong></article><article class="report-card"><small>UNRESOLVED</small><strong>${report.unresolved_occurrences}</strong></article><article class="report-card"><small>GRAVITY PASSES</small><strong>1 COMPLETED</strong><p>Stopped early; safety cap ${state.complexity.planned_passes}.</p></article><article class="report-card"><small>SEMANTIC GATE</small><strong>${esc(semantic.status)}</strong></article></div>${transactionDetails}<article class="report-card wide"><small>STOP REASON</small><p>${esc(state.pass.stop_reason)}</p></article></div>`;
  setSystem(certification.eligible ? certification.label : "REPORT GENERATED", certification.eligible ? "The document reached a stable, independently verified state." : "Final certification remains withheld until every semantic gate passes.", certification.eligible ? "ready" : "warn");
}

async function executeStep(step) {
  try {
    if (step === 1) {
      const text = $("#sourceText").value;
      const result = await api("/api/analyse", {text});
      state.analysis = result.analysis;
      state.complexity = result.complexity;
      state.originalText = text;
      state.pass = null;
      updateMetrics();
      renderSections();
      setSystem("DOCUMENT READ", "Immutable source indexed; no rewrite authorised.");
    } else if (step === 2) {
      renderLedger();
      setSystem("LEDGER INDEXED", `${state.analysis.document.units.length} immutable semantic units received stable identifiers.`);
    } else if (step === 3) {
      renderFamilies(3);
      setSystem("RECURRENCES MAPPED", `${state.analysis.families.length} conservative complete-link families detected.`);
    } else if (step === 4) {
      renderFamilies(4);
      setSystem("OCCURRENCES CLASSIFIED", "Relation, local function, and editorial disposition remain separate.");
    } else if (step === 5) {
      renderFamilies(5);
      setSystem("CENTRES LOCATED", "Candidate sections scored by functional competence and disruption risk.");
    } else if (step === 6) {
      renderPlan();
      setSystem("PASS PLAN READY", `${state.complexity.planned_passes} pass safety cap selected; early stopping remains active.`);
    }
    else if (step === 7) {
      state.pass = await api("/api/safe-pass", {text: state.originalText});
      renderPass();
      setSystem("PASS COMPLETE", `${state.pass.transactions.length} atomic transaction(s); semantic layer: ${state.pass.model_status}.`, state.pass.model_status === "MODEL_UNAVAILABLE" ? "warn" : "ready");
    } else if (step === 8) renderVerification();
    else if (step === 9) renderReport();
    setStep(step);
  } catch (error) {
    setSystem("NOT VERIFIED", error.message, "bad");
    $("#auditMessage").textContent = `Processing stopped: ${error.message}`;
  }
}

$$('[data-step]').forEach((button) => button.addEventListener("click", () => executeStep(Number(button.dataset.step))));
$("#resetButton").addEventListener("click", async () => {
  state.step = 0; state.analysis = null; state.complexity = null; state.pass = null;
  await loadSample();
  setStep(0);
  ["wordMetric","unitMetric","sectionMetric","familyMetric","pressureMetric","passMetric"].forEach((id) => $("#" + id).textContent = "—");
  $("#coverageMetric").textContent = "PENDING";
  $("#mapTitle").textContent = "Gravity map"; $("#mapState").textContent = "UNMAPPED";
  $("#mapContent").className = "empty-state"; $("#mapContent").innerHTML = `<div class="empty-orbit"><i></i><i></i><b></b></div><p>Read the document to initialise the Conservation Ledger.</p>`;
  $("#resultTitle").textContent = "Verification"; $("#verificationState").textContent = "NOT RUN"; $("#verificationState").className = "pill neutral";
  $("#resultContent").className = "empty-state compact"; $("#resultContent").innerHTML = `<div class="shield">✓</div><p>Certification remains withheld until every critical invariant passes.</p>`;
  setSystem("READY", "No transformation has been authorised.");
});
$("#sampleButton").addEventListener("click", loadSample);
$("#fileInput").addEventListener("change", async (event) => {
  const file = event.target.files[0];
  if (file) { $("#sourceText").value = await file.text(); state.originalText = $("#sourceText").value; }
});

loadSample();
setStep(0);
