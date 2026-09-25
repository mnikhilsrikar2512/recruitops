/* ═══════════════════════════════════════════════════════════════
   PIPELINE — Auto-extracted from app.js
   ═══════════════════════════════════════════════════════════════ */

function normalizePipelineStage(value) {
  return (value || "")
    .replace(/\s+/g, " ")
    .trim();
}


function slugifyPipelineValue(value) {
  return normalizePipelineStage(value).toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, "") || "stage";
}


function readPipelineFlow() {
  try {
    const saved = JSON.parse(window.localStorage.getItem("recruitops-pipeline-flow") || "null");
    if (Array.isArray(saved)) {
      const clean = saved.map(normalizePipelineStage).filter(Boolean);
      if (clean.length >= 2) return Array.from(new Set(clean));
    }
  } catch {
  }
  return DEFAULT_PIPELINE_FLOW.slice();
}


function savePipelineFlow(stages) {
  const clean = Array.from(new Set((stages || []).map(normalizePipelineStage).filter(Boolean))).slice(0, 8);
  const safeStages = clean.length >= 2 ? clean : DEFAULT_PIPELINE_FLOW.slice();
  window.localStorage.setItem("recruitops-pipeline-flow", JSON.stringify(safeStages));
  return safeStages;
}


function getPipelineBoardTrack() {
  const columns = getPipelineColumns();
  return columns[0]?.column?.parentElement || document.querySelector("[data-pipeline-board-track]");
}


function normalizePipelineDropZone(dropZone, stageName = "") {
  if (!dropZone) return dropZone;
  dropZone.classList.remove("flex", "items-center", "justify-center", "flex-row", "flex-wrap");
  dropZone.classList.add("flex-1", "overflow-y-auto", "hide-scrollbar", "space-y-3", "p-1", "pipeline-drop-zone");
  if (stageName) dropZone.dataset.pipelineDropZone = stageName;
  const hasCards = dropZone.querySelector(":scope > .cursor-grab, :scope > [data-pipeline-candidate-card], :scope > [data-application-id]");
  Array.from(dropZone.children).forEach((child) => {
    const isCard = child.matches(".cursor-grab, [data-pipeline-candidate-card], [data-application-id], .pipeline-card");
    if (!isCard) child.remove();
  });
  if (!hasCards) {
    const empty = document.createElement("div");
    empty.className = "pipeline-empty-note";
    empty.textContent = `Drop candidates into ${stageName || "this stage"}`;
    dropZone.appendChild(empty);
  }
  return dropZone;
}


function buildPipelineColumn(stageName, templateColumn = null) {
  const column = templateColumn?.cloneNode(true) || document.createElement("div");
  column.className = "w-[300px] flex flex-col bg-surface-alt/50 rounded-xl border border-border p-2";
  column.style.opacity = "";
  column.dataset.pipelineStage = stageName;
  column.querySelectorAll("[data-pipeline-candidate-card], .cursor-grab, .pipeline-card-action, .pipeline-stage-status").forEach((node) => node.remove());
  const heading = column.querySelector("h3") || column.querySelector("h2");
  if (heading) heading.textContent = stageName;
  const countNode = heading?.parentElement?.querySelector("span");
  if (countNode) countNode.textContent = "0";
  const dropZone = Array.from(column.querySelectorAll(":scope > div")).find((zone) => zone.querySelector(".pipeline-empty-note"))
    || Array.from(column.querySelectorAll(":scope > div")).at(-1)
    || column.appendChild(document.createElement("div"));
  normalizePipelineDropZone(dropZone, stageName);
  const addButton = Array.from(column.querySelectorAll("button")).find((button) => /add/i.test(getActionLabel(button)) || button.querySelector(".material-symbols-outlined"));
  if (addButton) {
    addButton.type = "button";
  }
  return column;
}


function applyPipelineFlowToBoard(stages = readPipelineFlow()) {
  if (!["pipeline-board", "stage-move-dialog"].includes(document.body?.dataset.routeId || "")) return;
  const track = getPipelineBoardTrack();
  const columns = getPipelineColumns();
  if (!track || !columns.length) return;
  track.dataset.pipelineBoardTrack = "true";
  const template = columns[0].column.cloneNode(true);
  const cardsByStage = new Map();
  const reassignedCards = [];
  columns.forEach((column) => {
    const cards = Array.from(column.dropZone?.querySelectorAll(":scope > .cursor-grab, :scope > [data-pipeline-candidate-card], :scope > [data-application-id]") || []);
    cardsByStage.set(slugifyPipelineValue(column.name), cards);
  });
  track.innerHTML = "";
  stages.forEach((stageName, index) => {
    const slug = slugifyPipelineValue(stageName);
    const matchedColumn = columns.find((column) => slugifyPipelineValue(column.name) === slug)?.column;
    const nextColumn = matchedColumn || buildPipelineColumn(stageName, template);
    nextColumn.dataset.pipelineStage = stageName;
    nextColumn.style.opacity = "";
    const heading = nextColumn.querySelector("h3") || nextColumn.querySelector("h2");
    if (heading) heading.textContent = stageName;
    const dropZone = Array.from(nextColumn.querySelectorAll(":scope > div")).find((zone) => zone.querySelector(".cursor-grab, [data-pipeline-candidate-card], [data-application-id], .pipeline-empty-note"))
      || Array.from(nextColumn.querySelectorAll(":scope > div")).at(-1);
    track.appendChild(nextColumn);
    if (!matchedColumn) {
      (cardsByStage.get(slug) || []).forEach((card) => dropZone?.appendChild(card));
    }
    if (index === 0) {
      columns
        .filter((column) => !stages.some((stage) => slugifyPipelineValue(stage) === slugifyPipelineValue(column.name)))
        .forEach((removedColumn) => {
          (cardsByStage.get(slugifyPipelineValue(removedColumn.name)) || []).forEach((card) => {
            card.querySelector(".pipeline-stage-status")?.remove();
            const status = document.createElement("div");
            status.className = "pipeline-stage-status mt-2 rounded-lg bg-warning-bg px-2 py-1 text-[11px] font-semibold text-warning-text";
            status.textContent = `Reassigned from removed ${removedColumn.name} stage`;
            card.appendChild(status);
            dropZone?.appendChild(card);
            reassignedCards.push(card);
          });
        });
    }
    if (dropZone) normalizePipelineDropZone(dropZone, stageName);
  });
  updatePipelineCounts(getPipelineColumns());
  if (reassignedCards.length) {
    showToast("Flow updated safely", `${reassignedCards.length} candidate card${reassignedCards.length === 1 ? "" : "s"} kept visible after stage changes.`);
  }
}


function openPipelineFlowManager() {
  if (document.querySelector(".pipeline-flow-modal")) return;
  const currentStages = readPipelineFlow();
  const modal = document.createElement("div");
  modal.className = "pipeline-flow-modal";
  modal.setAttribute("role", "dialog");
  modal.setAttribute("aria-modal", "true");
  modal.innerHTML = `
    <div class="pipeline-flow-panel">
      <div class="border-b border-border bg-surface-alt/80 px-5 py-4">
        <div class="flex items-start justify-between gap-3">
          <div>
            <p class="m-0 font-label-caps text-label-caps uppercase tracking-[0.16em] text-text-muted">Admin Flow</p>
            <h2 class="m-0 mt-1 font-headline-md text-headline-md text-on-surface">Manage pipeline stages</h2>
            <p class="m-0 mt-1 text-[13px] text-text-muted">Rename, reorder, or add stages. Candidate cards stay attached to the nearest safe stage.</p>
          </div>
          <button type="button" class="rounded-xl border border-border bg-surface p-2 text-text-muted hover:bg-highlight-soft hover:text-on-surface" data-flow-close aria-label="Close stage manager">
            <span class="material-symbols-outlined text-[20px]">close</span>
          </button>
        </div>
      </div>
      <div class="p-5">
        <div class="pipeline-flow-list" data-flow-list></div>
        <button type="button" class="pipeline-flow-add mt-4 inline-flex items-center gap-2 border border-border bg-surface px-3 py-2 text-on-surface hover:bg-highlight-soft" data-flow-add>
          <span class="material-symbols-outlined text-[18px]">add</span>
          Add stage
        </button>
        <p class="mt-3 text-[12px] font-semibold text-text-muted" data-flow-error></p>
      </div>
      <div class="pipeline-flow-footer flex flex-wrap items-center justify-between gap-3 border-t border-border bg-surface-soft px-5 py-4">
        <button type="button" class="border border-border bg-surface px-3 py-2 text-text-muted hover:bg-highlight-soft" data-flow-reset>Reset defaults</button>
        <div class="flex gap-2">
          <button type="button" class="border border-border bg-surface px-3 py-2 text-on-surface hover:bg-highlight-soft" data-flow-close>Cancel</button>
          <button type="button" class="bg-primary px-4 py-2 text-on-primary hover:bg-primary-hover" data-flow-save>Apply flow</button>
        </div>
      </div>
    </div>
  `;
  const list = modal.querySelector("[data-flow-list]");
  const error = modal.querySelector("[data-flow-error]");
  const renderRows = (stages) => {
    list.innerHTML = "";
    stages.forEach((stage, index) => {
      const row = document.createElement("div");
      row.className = "pipeline-flow-row";
      row.innerHTML = `
        <span class="pipeline-flow-icon material-symbols-outlined">drag_indicator</span>
        <input value="${stage.replace(/"/g, "&quot;")}" aria-label="Stage ${index + 1} name">
        <div class="pipeline-flow-actions">
          <button type="button" class="border border-border bg-surface px-2 text-text-muted hover:bg-highlight-soft" data-flow-up aria-label="Move stage up"><span class="material-symbols-outlined text-[16px]">keyboard_arrow_up</span></button>
          <button type="button" class="border border-border bg-surface px-2 text-text-muted hover:bg-highlight-soft" data-flow-down aria-label="Move stage down"><span class="material-symbols-outlined text-[16px]">keyboard_arrow_down</span></button>
          <button type="button" class="border border-border bg-surface px-2 text-danger-text hover:bg-danger-bg" data-flow-remove aria-label="Remove stage"><span class="material-symbols-outlined text-[16px]">delete</span></button>
        </div>
      `;
      list.appendChild(row);
    });
  };
  const readRows = () => Array.from(list.querySelectorAll("input")).map((input) => input.value);
  const close = () => modal.remove();
  renderRows(currentStages);
  modal.addEventListener("click", (event) => {
    if (event.target === modal || event.target.closest("[data-flow-close]")) {
      close();
      return;
    }
    const row = event.target.closest(".pipeline-flow-row");
    if (event.target.closest("[data-flow-add]")) {
      renderRows(readRows().concat(`Stage ${list.querySelectorAll("input").length + 1}`));
      list.querySelector(".pipeline-flow-row:last-child input")?.focus();
      return;
    }
    if (event.target.closest("[data-flow-reset]")) {
      renderRows(DEFAULT_PIPELINE_FLOW);
      error.textContent = "Defaults restored. Apply flow to update the board.";
      return;
    }
    if (event.target.closest("[data-flow-save]")) {
      const cleaned = readRows().map(normalizePipelineStage).filter(Boolean);
      const unique = Array.from(new Set(cleaned));
      if (unique.length < 2) {
        error.textContent = "Keep at least two unique stages so the workflow remains usable.";
        return;
      }
      const savedStages = savePipelineFlow(unique);
      close();
      applyPipelineFlowToBoard(savedStages);
      setupPipelineBoardInteractions();
      showToast("Flow applied", `${savedStages.length} stages are now reflected on the pipeline board and move dialog.`);
      return;
    }
    if (!row) return;
    const rows = Array.from(list.children);
    const index = rows.indexOf(row);
    if (event.target.closest("[data-flow-up]") && index > 0) {
      list.insertBefore(row, rows[index - 1]);
      row.querySelector("input")?.focus();
    }
    if (event.target.closest("[data-flow-down]") && index < rows.length - 1) {
      list.insertBefore(rows[index + 1], row);
      row.querySelector("input")?.focus();
    }
    if (event.target.closest("[data-flow-remove]")) {
      if (rows.length <= 2) {
        error.textContent = "Keep at least two stages in the flow.";
        return;
      }
      row.remove();
    }
  });
  modal.addEventListener("keydown", (event) => {
    if (event.key === "Escape") close();
  });
  document.body.appendChild(modal);
  modal.querySelector("input")?.focus();
}


function resolvePipelineColumnFromHeading(heading) {
  let node = heading?.parentElement;
  while (node && !node.classList?.contains("workspace-surface") && !node.classList?.contains("overlay-underlay") && !node.matches?.("[data-demo-validate]")) {
    const className = String(node.className || "");
    const looksLikeStageColumn = className.includes("w-[300px]") && /flex-col/.test(className) && /border/.test(className);
    if (looksLikeStageColumn || (node.dataset?.pipelineStage && !node.dataset.pipelineBoardTrack)) {
      return node;
    }
    if (node.querySelectorAll?.(".cursor-grab, [data-pipeline-candidate-card]").length) {
      return node;
    }
    node = node.parentElement;
  }
  return null;
}


function getPipelineColumns(root = document) {
  return Array.from(root.querySelectorAll(".workspace-surface h3, .overlay-underlay h3, [data-demo-validate] h3"))
    .map((heading) => {
      const name = normalizePipelineStage(heading.textContent);
      const column = resolvePipelineColumnFromHeading(heading);
      if (!name || !column) return null;
      const zones = Array.from(column.querySelectorAll(":scope > div"));
      const dropZone = zones.find((zone) => zone.querySelector(".cursor-grab, [data-pipeline-candidate-card], .pipeline-empty-note"))
        || zones[zones.length - 1];
      const countNode = heading.parentElement?.querySelector("span");
      return { name, id: slugifyPipelineValue(name), heading, column, dropZone, countNode };
    })
    .filter(Boolean);
}


function extractPipelineCandidate(card, fallbackStage = "") {
  const nameNode = Array.from(card.querySelectorAll("p")).find((node) => /text-on-surface/.test(node.className || ""))
    || card.querySelector("p");
  const metaNode = nameNode?.parentElement?.querySelector("p.text-text-muted")
    || Array.from(card.querySelectorAll("p")).find((node) => node !== nameNode && /yrs exp|google|stripe|amazon|meta|netflix|apple/i.test(node.textContent || ""));
  const ownerNode = Array.from(card.querySelectorAll("[title]")).find((node) => /owner:/i.test(node.getAttribute("title") || ""));
  const badges = Array.from(card.querySelectorAll(".font-label-caps, .text-label-caps"))
    .map((node) => normalizePipelineStage(node.textContent))
    .filter(Boolean);
  const name = normalizePipelineStage(nameNode?.textContent);
  const meta = normalizePipelineStage(metaNode?.textContent);
  if (!name) return null;
  return {
    id: card.dataset.applicationId || slugifyPipelineValue(name),
    name,
    meta,
    stage: fallbackStage,
    owner: normalizePipelineStage((ownerNode?.getAttribute("title") || "").replace(/owner:/i, "")),
    badges,
  };
}


function getPipelineCandidates(root = document) {
  const candidates = [];
  getPipelineColumns(root).forEach((column) => {
    Array.from(column.dropZone?.querySelectorAll(":scope > .cursor-grab, :scope > [data-pipeline-candidate-card]") || []).forEach((card) => {
      const candidate = extractPipelineCandidate(card, column.name);
      if (candidate) candidates.push({ ...candidate, card, column });
    });
  });
  return candidates;
}


function updatePipelineCounts(columns = getPipelineColumns()) {
  columns.forEach((column) => {
    const count = column.dropZone?.querySelectorAll(":scope > [data-pipeline-candidate-card], :scope > .cursor-grab").length || 0;
    if (column.countNode) column.countNode.textContent = String(count);
    const empty = column.dropZone?.querySelector(".pipeline-empty-note");
    if (empty) empty.hidden = count > 0;
  });
}


function rememberPipelineCandidate(candidate) {
  if (!candidate?.name) return;
  const payload = JSON.stringify({
    id: candidate.id,
    name: candidate.name,
    meta: candidate.meta,
    stage: candidate.stage,
    owner: candidate.owner,
    badges: candidate.badges || [],
  });
  window.sessionStorage.setItem("recruitops-selected-pipeline-candidate", payload);
  window.localStorage.setItem("recruitops-selected-pipeline-candidate", payload);
}


function pipelineCandidateUrl(candidate, target = "stage-move-dialog.html") {
  if (!candidate?.name) return target;
  const params = new URLSearchParams({
    candidate: candidate.id || slugifyPipelineValue(candidate.name),
    name: candidate.name,
    meta: candidate.meta || "",
    stage: candidate.stage || "",
    owner: candidate.owner || "",
  });
  if (/^\d+$/.test(String(candidate.id || ""))) {
    params.set("application_id", String(candidate.id));
  }
  return `${target}?${params.toString()}`;
}


function readRememberedPipelineCandidate() {
  try {
    const params = new URLSearchParams(window.location.search);
    if (params.get("candidate") || params.get("name")) {
      return {
        id: params.get("candidate") || slugifyPipelineValue(params.get("name") || ""),
        name: params.get("name") || "",
        meta: params.get("meta") || "",
        stage: params.get("stage") || "",
        owner: params.get("owner") || "",
        badges: [],
      };
    }
    return JSON.parse(
      window.sessionStorage.getItem("recruitops-selected-pipeline-candidate")
      || window.localStorage.getItem("recruitops-selected-pipeline-candidate")
      || "null"
    );
  } catch {
    return null;
  }
}


function setupPipelineBoardInteractions() {
  if (!["pipeline-board", "stage-move-dialog"].includes(document.body?.dataset.routeId || "")) return;
  applyPipelineFlowToBoard(readPipelineFlow());
  const columns = getPipelineColumns();
  if (!columns.length) return;
  const selectCard = (card, silent = false) => {
    const candidate = extractPipelineCandidate(card, card.closest("[data-pipeline-stage]")?.dataset.pipelineStage || "");
    if (!candidate) return;
    document.querySelectorAll("[data-pipeline-candidate-card].is-selected").forEach((node) => node.classList.remove("is-selected"));
    card.classList.add("is-selected");
    rememberPipelineCandidate(candidate);
    if (!silent) showToast("Candidate selected", `${candidate.name} is ready for a stage move.`);
  };

  columns.forEach((column) => {
    column.column.dataset.pipelineStage = column.name;
    column.dropZone?.classList.add("pipeline-drop-zone");
    column.dropZone?.setAttribute("data-pipeline-drop-zone", column.name);
    if (column.dropZone) normalizePipelineDropZone(column.dropZone, column.name);

    if (!column.dropZone?.dataset.pipelineDropBound) {
      column.dropZone.dataset.pipelineDropBound = "true";
      column.dropZone.addEventListener("dragover", (event) => {
        event.preventDefault();
        column.dropZone.classList.add("is-drop-target");
      });
      column.dropZone.addEventListener("dragleave", (event) => {
        if (!column.dropZone.contains(event.relatedTarget)) {
          column.dropZone.classList.remove("is-drop-target");
        }
      });
      column.dropZone.addEventListener("drop", (event) => {
        event.preventDefault();
        column.dropZone.classList.remove("is-drop-target");
        const cardId = event.dataTransfer?.getData("text/plain");
        const card = cardId ? document.querySelector(`[data-pipeline-card-id="${cardId}"]`) : null;
        if (!card || card.closest("[data-pipeline-drop-zone]") === column.dropZone) return;
        const previous = extractPipelineCandidate(card, card.closest("[data-pipeline-stage]")?.dataset.pipelineStage || "");
        const sourceZone = card.closest("[data-pipeline-drop-zone]");
        column.dropZone.classList.remove("flex", "items-center", "justify-center");
        column.dropZone.querySelectorAll(".pipeline-empty-note, .border-dashed").forEach((node) => {
          if (!node.closest(".cursor-grab, [data-pipeline-candidate-card], [data-application-id]")) node.remove();
        });
        column.dropZone.appendChild(card);
        if (sourceZone && sourceZone !== column.dropZone && !sourceZone.querySelector(".cursor-grab, [data-pipeline-candidate-card], [data-application-id]")) {
          normalizePipelineDropZone(sourceZone, sourceZone.dataset.pipelineDropZone || "");
        }
        card.querySelector(".pipeline-stage-status")?.remove();
        const status = document.createElement("div");
        status.className = "pipeline-stage-status mt-2 rounded-lg bg-success-bg px-2 py-1 text-[11px] font-semibold text-success-text";
        status.textContent = `Moved to ${column.name} just now`;
        card.appendChild(status);
        selectCard(card, true);
        updatePipelineCounts(getPipelineColumns());
        showToast("Candidate moved", `${previous?.name || "Candidate"} moved to ${column.name}.`);
      });
    }
  });

  getPipelineCandidates().forEach(({ card, id, name }) => {
    card.dataset.pipelineCandidateCard = "true";
    card.dataset.pipelineCardId = id;
    card.setAttribute("draggable", "true");
    card.setAttribute("role", "button");
    card.setAttribute("tabindex", "0");
    card.setAttribute("aria-label", `Select ${name} for pipeline actions`);
    if (!card.querySelector(".pipeline-card-action, [data-route*='stage-move']")) {
      const action = document.createElement("button");
      action.type = "button";
      action.className = "pipeline-card-action";
      action.innerHTML = '<span class="material-symbols-outlined text-[16px]">move_up</span><span>Move stage</span>';
      card.appendChild(action);
    }
    card.querySelectorAll(".pipeline-card-action, [data-route*='stage-move']").forEach((action) => {
      if (action.dataset.pipelineMoveBound === "true") return;
      action.dataset.pipelineMoveBound = "true";
      action.type = "button";
      action.addEventListener("click", (event) => {
        event.preventDefault();
        event.stopPropagation();
        selectCard(card, true);
        const candidate = extractPipelineCandidate(card, card.closest("[data-pipeline-stage]")?.dataset.pipelineStage || "");
        const href = pipelineCandidateUrl(candidate);
        if (typeof navigateToRoute === "function") navigateToRoute(href);
        else window.location.href = typeof buildRouteHref === "function" ? buildRouteHref(href) : href;
      });
    });
    if (!card.dataset.pipelineCardBound) {
      card.dataset.pipelineCardBound = "true";
      card.addEventListener("click", (event) => {
        if (event.target.closest("button, a, input, select, textarea")) return;
        selectCard(card);
      });
      card.addEventListener("keydown", (event) => {
        if (event.key !== "Enter" && event.key !== " ") return;
        event.preventDefault();
        selectCard(card);
      });
      card.addEventListener("dragstart", (event) => {
        selectCard(card, true);
        card.classList.add("is-dragging");
        event.dataTransfer?.setData("text/plain", id);
        if (event.dataTransfer) event.dataTransfer.effectAllowed = "move";
      });
      card.addEventListener("dragend", () => {
        card.classList.remove("is-dragging");
        document.querySelectorAll(".pipeline-drop-zone.is-drop-target").forEach((zone) => zone.classList.remove("is-drop-target"));
      });
    }
  });

  const remembered = readRememberedPipelineCandidate();
  const rememberedCard = remembered?.id ? document.querySelector(`[data-pipeline-card-id="${remembered.id}"]`) : null;
  if (rememberedCard) selectCard(rememberedCard, true);
  document.querySelectorAll('a[href="stage-move-dialog.html"], a[href*="stage-move-dialog.html"]').forEach((link) => {
    if (link.dataset.pipelineMoveLinkBound) return;
    link.dataset.pipelineMoveLinkBound = "true";
    link.addEventListener("click", (event) => {
      const selectedCard = document.querySelector("[data-pipeline-candidate-card].is-selected")
        || document.querySelector("[data-pipeline-candidate-card]");
      const candidate = selectedCard
        ? extractPipelineCandidate(selectedCard, selectedCard.closest("[data-pipeline-stage]")?.dataset.pipelineStage || "")
        : readRememberedPipelineCandidate();
      if (!candidate?.name) return;
      event.preventDefault();
      event.stopPropagation();
      rememberPipelineCandidate(candidate);
      const href = pipelineCandidateUrl(candidate, "stage-move-dialog.html");
      if (typeof navigateToRoute === "function") navigateToRoute(href);
      else window.location.href = typeof buildRouteHref === "function" ? buildRouteHref(href) : href;
    }, { capture: true });
  });
  if (document.body?.dataset.routeId === "pipeline-board") {
    Array.from(document.querySelectorAll("button")).filter((button) => /manage stages/i.test(getActionLabel(button))).forEach((button) => {
      if (button.dataset.pipelineFlowButtonBound) return;
      button.dataset.pipelineFlowButtonBound = "true";
      button.dataset.toast = "";
      button.type = "button";
      button.addEventListener("click", (event) => {
        event.preventDefault();
        event.stopPropagation();
        openPipelineFlowManager();
      }, { capture: true });
    });
  }
  updatePipelineCounts(columns);
}


function setupStageMoveOverlay() {
  if (document.body?.dataset.routeId !== "stage-move-dialog") return;
  const surface = document.querySelector("[data-overlay-surface='true']");
  const selects = Array.from(surface?.querySelectorAll("select") || []);
  const targetStage = selects[0];
  const rationale = surface?.querySelector("#reason");
  const notes = surface?.querySelector("#notes");
  const rejectToggle = surface?.querySelector('input[type="checkbox"].peer');
  const shareNotes = surface?.querySelector("#share_notes");
  const confirmButton = Array.from(surface?.querySelectorAll("button") || []).find((button) => /confirm transition/i.test(getActionLabel(button)));
  const summary = ensureDecisionSummary(
    surface?.querySelector(".p-inset-card.flex.flex-col") || surface,
    "stage-move",
    "Transition readiness",
    "Keep the stage destination, rationale, and notes aligned before you finalize the move.",
  );
  if (!surface || !targetStage || !rationale || !notes || !confirmButton || !summary) return;
  const candidates = getPipelineCandidates(document).map(({ card, column, ...candidate }) => ({
    ...candidate,
    stage: column?.name || candidate.stage,
  }));
  const remembered = readRememberedPipelineCandidate();
  if (remembered?.name && !candidates.some((candidate) => candidate.id === remembered.id || candidate.name === remembered.name)) {
    candidates.unshift(remembered);
  }
  const matchedCandidate = remembered
    ? candidates.find((candidate) => candidate.id === remembered.id)
      || candidates.find((candidate) => candidate.name === remembered.name)
    : null;
  let activeCandidate = remembered?.name
    ? { ...(matchedCandidate || {}), ...remembered }
    : matchedCandidate || candidates[0];
  const headerSubtitle = surface.querySelector("h2")?.parentElement?.querySelector("p");
  const stageRow = targetStage.closest(".flex.items-center.justify-between") || targetStage.closest(".flex");
  const currentStageLabel = stageRow?.querySelector(":scope > div:first-child div span:last-child");
  const picker = document.createElement("div");
  picker.className = "stage-candidate-picker";
  picker.innerHTML = `
    <label class="font-label-caps text-label-caps text-text-muted uppercase" for="stage-candidate-select">Candidate</label>
    <div class="relative mt-2">
      <select id="stage-candidate-select" class="w-full appearance-none bg-surface border border-border rounded px-3 py-2 pr-8 font-body-md text-body-md text-on-surface focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-colors cursor-pointer"></select>
      <span class="material-symbols-outlined absolute right-2 top-1/2 -translate-y-1/2 text-outline pointer-events-none">expand_more</span>
    </div>
    <p class="mt-2 font-body-sm text-body-sm text-text-muted" data-stage-candidate-meta></p>
  `;
  const candidateSelect = picker.querySelector("#stage-candidate-select");
  const candidateMeta = picker.querySelector("[data-stage-candidate-meta]");
  candidates.forEach((candidate) => {
    const option = document.createElement("option");
    option.value = candidate.id;
    option.textContent = `${candidate.name} - ${candidate.stage || "Pipeline"}`;
    candidateSelect.appendChild(option);
  });
  if (activeCandidate?.id && !candidateSelect.querySelector(`option[value="${activeCandidate.id}"]`)) {
    const option = document.createElement("option");
    option.value = activeCandidate.id;
    option.textContent = `${activeCandidate.name} - ${activeCandidate.stage || "Pipeline"}`;
    candidateSelect.appendChild(option);
  }
  stageRow?.parentElement?.insertBefore(picker, stageRow);

  const sync = ({ fromRejectToggle = false } = {}) => {
    const selectedBase = candidates.find((candidate) => candidate.id === candidateSelect.value) || activeCandidate;
    const rememberedCandidate = readRememberedPipelineCandidate();
    const selectedCandidate = rememberedCandidate?.id === selectedBase?.id
      ? { ...selectedBase, ...rememberedCandidate, badges: selectedBase.badges || rememberedCandidate.badges || [] }
      : selectedBase;
    activeCandidate = selectedCandidate;
    if (activeCandidate) rememberPipelineCandidate(activeCandidate);
    const activeOption = activeCandidate?.id ? candidateSelect.querySelector(`option[value="${activeCandidate.id}"]`) : null;
    if (activeOption && activeCandidate?.stage) {
      activeOption.textContent = `${activeCandidate.name} - ${activeCandidate.stage}`;
    }
    if (headerSubtitle && activeCandidate) {
      headerSubtitle.textContent = `${activeCandidate.name} - ${activeCandidate.meta || "Pipeline candidate"}`;
    }
    if (candidateMeta && activeCandidate) {
      const owner = activeCandidate.owner ? `Owner ${activeCandidate.owner}` : "Owner ready";
      candidateMeta.textContent = `${activeCandidate.meta || "Candidate profile"} - ${owner}`;
    }
    if (currentStageLabel && activeCandidate?.stage) {
      currentStageLabel.textContent = activeCandidate.stage;
    }
    const stageNames = readPipelineFlow().length
      ? readPipelineFlow()
      : getPipelineColumns(document).map((column) => column.name).filter(Boolean);
    const desiredValue = targetStage.value;
    if (stageNames.length) {
      targetStage.innerHTML = "";
      stageNames.filter((stage) => stage !== activeCandidate?.stage).concat("Rejected").forEach((stage) => {
        const option = document.createElement("option");
        option.value = slugifyPipelineValue(stage);
        option.textContent = stage;
        targetStage.appendChild(option);
      });
      if (Array.from(targetStage.options).some((option) => option.value === desiredValue)) {
        targetStage.value = desiredValue;
      }
    }
    if (rejectToggle?.checked && targetStage.value !== "rejected") {
      targetStage.value = "rejected";
    } else if (!rejectToggle?.checked && targetStage.value === "rejected" && fromRejectToggle) {
      targetStage.value = Array.from(targetStage.options).find((option) => option.value !== "rejected")?.value || "rejected";
    }

    const targetLabel = targetStage.options[targetStage.selectedIndex]?.text?.trim() || "Choose target stage";
    const rationaleLabel = rationale.options[rationale.selectedIndex]?.text?.trim() || "Add rationale";
    const noteState = (notes.value || "").trim();
    const isRejection = rejectToggle?.checked || targetStage.value === "rejected";
    const canConfirm = isFieldComplete(rationale) && noteState.length >= 16;

    confirmButton.textContent = isRejection ? "Confirm Rejection" : "Confirm Transition";
    setActionEnabled(confirmButton, canConfirm);
    updateDecisionSummaryMeta(summary, [
      { icon: "person", text: activeCandidate?.name || "Choose candidate" },
      { icon: "move_up", text: targetLabel },
      { icon: isRejection ? "cancel" : "rule", text: rationaleLabel },
      { icon: shareNotes?.checked ? "groups" : "notes", text: shareNotes?.checked ? "Notes shared with hiring team" : "Internal-only notes" },
    ]);
  };

  if (activeCandidate?.id) candidateSelect.value = activeCandidate.id;
  candidateSelect.addEventListener("change", () => sync());
  targetStage.addEventListener("change", () => {
    if (rejectToggle) {
      rejectToggle.checked = targetStage.value === "rejected";
    }
    sync();
  });
  rationale.addEventListener("change", sync);
  notes.addEventListener("input", sync);
  rejectToggle?.addEventListener("change", () => sync({ fromRejectToggle: true }));
  shareNotes?.addEventListener("change", sync);
  confirmButton.addEventListener("click", (event) => {
    event.preventDefault();
    event.stopPropagation();
    if (!validateScope(surface)) return;
    const targetLabel = targetStage.options[targetStage.selectedIndex]?.text?.trim() || "selected stage";
    showToast("Interaction validated", `${activeCandidate?.name || "Candidate"} will move from ${activeCandidate?.stage || "current stage"} to ${targetLabel}.`);
  });
  sync();
}


function setupReassignOwnerOverlay() {
  if (document.body?.dataset.routeId !== "reassign-owner-dialog") return;
  const surface = document.querySelector("[data-overlay-surface='true']");
  const ownerInput = surface?.querySelector("#new-owner-select");
  const reasonInput = surface?.querySelector("#reassign-reason");
  const confirmButton = Array.from(surface?.querySelectorAll("button") || []).find((button) => /confirm reassignment/i.test(getActionLabel(button)));
  const summary = ensureDecisionSummary(
    surface?.querySelector(".p-gutter.flex.flex-col") || surface,
    "reassign-owner",
    "Reassignment readiness",
    "Confirm the next owner and the audit reason before you hand this requisition over.",
  );
  if (!surface || !ownerInput || !reasonInput || !confirmButton || !summary) return;

  const sync = () => {
    const ownerValue = (ownerInput.value || "").trim();
    const reasonLength = (reasonInput.value || "").trim().length;
    const canConfirm = ownerValue.length >= 3 && reasonLength >= 16;
    setActionEnabled(confirmButton, canConfirm);
    updateDecisionSummaryMeta(summary, [
      { icon: "person", text: ownerValue || "Select new owner" },
      { icon: "receipt_long", text: reasonLength > 0 ? `${reasonLength} characters of audit context` : "Audit reason required" },
      { icon: "hub", text: "Communications and tasks will follow owner state" },
    ]);
  };

  ownerInput.addEventListener("input", sync);
  reasonInput.addEventListener("input", sync);
  sync();
}


function setupApprovalReviewOverlay() {
  if (document.body?.dataset.routeId !== "approval-review-drawer") return;
  const surface = document.querySelector("[data-overlay-surface='true']");
  const footer = surface?.querySelector("footer");
  const requestInfoButton = Array.from(footer?.querySelectorAll("button") || []).find((button) => /request info/i.test(getActionLabel(button)));
  const rejectButton = Array.from(footer?.querySelectorAll("button") || []).find((button) => /^reject$/.test(getActionLabel(button)));
  const approveButton = Array.from(footer?.querySelectorAll("button") || []).find((button) => /^approve$/.test(getActionLabel(button)));
  const summary = ensureDecisionSummary(
    surface?.querySelector(".flex-1.overflow-y-auto") || surface,
    "approval-review",
    "Decision status",
    "Choose the next decision path once the request type, impact, and risk are clear.",
  );
  if (!surface || !summary || !footer) return;

  const setState = (state) => {
    const map = {
      info: [
        { icon: "info", text: "Request more information" },
        { icon: "schedule", text: "Decision paused until requester responds" },
      ],
      reject: [
        { icon: "cancel", text: "Reject this request" },
        { icon: "gavel", text: "A rejection rationale should be captured next" },
      ],
      approve: [
        { icon: "check_circle", text: "Approve this request" },
        { icon: "done_all", text: "Ready for downstream workflow release" },
      ],
    };
    updateDecisionSummaryMeta(summary, map[state] || [
      { icon: "pending_actions", text: "Decision not chosen yet" },
      { icon: "rule", text: "Review the business and audit context first" },
    ]);
  };

  requestInfoButton?.addEventListener("click", () => setState("info"));
  rejectButton?.addEventListener("click", () => setState("reject"));
  approveButton?.addEventListener("click", () => setState("approve"));
  setState("");
}


function setupPipelineHistoryOverlay() {
  if (document.body?.dataset.routeId !== "pipeline-history-drawer") return;
  const surface = document.querySelector("[data-overlay-surface='true']");
  const timelineItems = Array.from(surface?.querySelectorAll(".timeline-item") || []);
  const summary = ensureDecisionSummary(
    surface?.querySelector(".flex-1.overflow-y-auto") || surface,
    "pipeline-history",
    "Timeline summary",
    "Use the event mix below to spot whether this candidate path was mostly manual, automated, or integration-driven.",
  );
  if (!surface || !summary || timelineItems.length === 0) return;

  const manualCount = timelineItems.filter((item) => /manual/i.test(item.textContent || "")).length;
  const automationCount = timelineItems.filter((item) => /automation|system/i.test(item.textContent || "")).length;
  const apiCount = timelineItems.filter((item) => /api sync|integration/i.test(item.textContent || "")).length;
  updateDecisionSummaryMeta(summary, [
    { icon: "history", text: `${timelineItems.length} timeline events` },
    { icon: "touch_app", text: `${manualCount} manual updates` },
    { icon: "api", text: `${apiCount + automationCount} automated or integrated steps` },
  ]);
}


