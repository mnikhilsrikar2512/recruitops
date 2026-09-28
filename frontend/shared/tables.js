/* ═══════════════════════════════════════════════════════════════
   TABLES — Auto-extracted from app.js
   ═══════════════════════════════════════════════════════════════ */

function toggleActiveWithin(group, target) {
  Array.from(group.children).forEach((child) => {
    child.classList.remove("is-active");
    if (child.tagName === "BUTTON") {
      child.setAttribute("aria-pressed", "false");
    }
  });
  target.classList.add("is-active");
  target.setAttribute("aria-pressed", "true");
}


function normalizeLensLabel(value) {
  return (value || "")
    .replace(/\([^)]*\)/g, "")
    .replace(/\d+\s*records?.*$/i, "")
    .replace(/\s+/g, " ")
    .trim()
    .toLowerCase();
}


function rowMatchesLens(rowText, lens) {
  const text = rowText.toLowerCase();
  if (!lens || /^(all|all reqs|all users|all clients|pending)$/.test(lens) && !/pending invite/.test(lens)) {
    return true;
  }
  if (/my reqs|assigned to me|my work/.test(lens)) {
    return /sarah j\.?|sarah jenkins|assigned to me|owner: me/.test(text);
  }
  if (/urgent|priority|high/.test(lens)) {
    return /urgent|p1|overdue|high|critical/.test(text);
  }
  if (/active/.test(lens)) {
    return /active|open|sourcing|interviewing/.test(text) && !/inactive|deactivated|closed/.test(text);
  }
  if (/pending invite|invited/.test(lens)) {
    return /pending|invite|invited/.test(text);
  }
  if (/deactivated|inactive/.test(lens)) {
    return /deactivated|inactive/.test(text);
  }
  if (/read/.test(lens) && !/unread/.test(lens)) {
    return /read|acknowledged|completed/.test(text);
  }
  if (/unread/.test(lens)) {
    return /unread|new|approval required|overdue/.test(text) && !/read/.test(text);
  }
  return true;
}


function applyTableLens(group, button) {
  const lens = normalizeLensLabel(button.textContent);
  const host = group.closest(".bg-surface, .shell-card, [data-demo-validate]") || document;
  const table = host.querySelector("table") || document.querySelector("table");
  const tbody = table?.querySelector("tbody");
  const rows = Array.from(tbody?.querySelectorAll("tr:not(.demo-empty-row)") || []);
  if (!table || !tbody || rows.length < 2) return null;

  let visibleCount = 0;
  rows.forEach((row) => {
    const text = (row.textContent || "").replace(/\s+/g, " ").trim();
    const visible = rowMatchesLens(text, lens);
    row.classList.toggle("is-demo-filtered-out", !visible);
    if (visible) visibleCount += 1;
  });

  let emptyRow = tbody.querySelector(".demo-empty-row");
  if (!emptyRow) {
    emptyRow = document.createElement("tr");
    emptyRow.className = "demo-empty-row";
    const td = document.createElement("td");
    td.colSpan = table.querySelectorAll("thead th").length || 1;
    emptyRow.appendChild(td);
    tbody.appendChild(emptyRow);
  }
  emptyRow.querySelector("td").textContent = `No records match the ${button.textContent.trim()} lens.`;
  emptyRow.hidden = visibleCount > 0;
  return { visibleCount, totalCount: rows.length };
}


function setupTableSelection(table) {
  const checkAll = table.querySelector("thead input[type='checkbox']");
  const rows = Array.from(table.querySelectorAll("tbody tr"));
  const rowChecks = rows
    .map((row) => ({ row, checkbox: row.querySelector("input[type='checkbox']") }))
    .filter((entry) => entry.checkbox);

  if (!checkAll || rowChecks.length === 0 || table.dataset.selectionEnhanced === "true") return;
  table.dataset.selectionEnhanced = "true";

  const bar = document.createElement("div");
  bar.className = "bulk-selection-bar";
  bar.innerHTML = `
    <div>
      <strong data-selection-count>0 records selected</strong>
    </div>
    <div class="bulk-selection-actions">
      <button type="button" data-toast-title="Bulk review queued" data-toast="The selected records are ready to be reviewed together.">Review selected</button>
      <button type="button" data-toast-title="Export queued" data-toast="The selected records will be exported.">Export selection</button>
    </div>
  `;
  table.parentElement.insertBefore(bar, table);

  const countNode = bar.querySelector("[data-selection-count]");

  const syncSelection = () => {
    const checkedRows = rowChecks.filter((entry) => entry.checkbox.checked);
    rowChecks.forEach(({ row, checkbox }) => {
      row.classList.toggle("is-row-selected", checkbox.checked);
    });
    const checkedCount = checkedRows.length;
    const total = rowChecks.length;
    checkAll.checked = checkedCount === total && total > 0;
    checkAll.indeterminate = checkedCount > 0 && checkedCount < total;
    bar.classList.toggle("is-visible", checkedCount > 0);
    if (countNode) {
      countNode.textContent = `${checkedCount} record${checkedCount === 1 ? "" : "s"} selected`;
    }
  };

  checkAll.addEventListener("change", () => {
    rowChecks.forEach(({ checkbox }) => {
      checkbox.checked = checkAll.checked;
    });
    syncSelection();
  });

  rowChecks.forEach(({ checkbox }) => {
    checkbox.addEventListener("change", syncSelection);
  });

  syncSelection();
}


function getTableColumnCount(table) {
  const firstRow = table.querySelector("tbody tr");
  const headerCells = table.querySelectorAll("thead th").length;
  const bodyCells = firstRow ? firstRow.children.length : 0;
  return Math.max(headerCells, bodyCells, 1);
}


function inferButtonLabel(button) {
  if (!button) return "";
  const existing = getActionLabel(button);
  if (existing) return existing;
  const icon = button.querySelector(".material-symbols-outlined")?.textContent?.trim().toLowerCase() || "";
  const labelMap = {
    more_vert: "Open record actions",
    edit: "Edit record",
    chevron_right: "Open details",
    visibility: "Preview record",
    open_in_new: "Open details",
  };
  return labelMap[icon] || "Open action";
}


function getRowSummary(row) {
  if (!row) return "this record";
  if (row.dataset.rowSummary) return row.dataset.rowSummary;
  const summaryNode = row.querySelector("td .font-semibold, td .font-medium, td p, td span");
  const summary = (summaryNode?.textContent || "").replace(/\s+/g, " ").trim();
  row.dataset.rowSummary = summary || "this record";
  return row.dataset.rowSummary;
}


function getLinkedTableSurface(source) {
  const localSurface = source.closest("[data-layout='filter-toolbar'], [data-layout='table-surface'], .topbar-search")?.closest("[data-layout='table-surface']");
  if (localSurface?.querySelector("table")) return localSurface;
  if (source.closest(".topbar-search")) {
    const explicitSurface = document.querySelector("[data-layout='table-surface']");
    if (explicitSurface?.querySelector("table")) return explicitSurface;
    return ensureInferredTableSurface(document.querySelector("table"));
  }
  return null;
}


function ensureInferredTableSurface(table) {
  if (!table) return null;
  const existing = table.closest("[data-layout='table-surface']");
  if (existing) return existing;
  const surface = table.parentElement?.parentElement || table.parentElement;
  if (!surface) return null;
  surface.setAttribute("data-layout", "table-surface");
  return surface;
}


function supportsSharedSearchPreview(input) {
  if (!input) return false;
  if (input.closest(".topbar-search")) return true;
  const tableSurface = input.closest("[data-layout='table-surface']");
  if (!tableSurface) return false;
  return Boolean(tableSurface.querySelector("table"));
}


function ensureTableSearchStatus(table) {
  if (!table) return null;
  const surface = table.closest("[data-layout='table-surface']") || table.parentElement;
  if (!surface) return null;
  let status = surface.querySelector("[data-table-search-status]");
  if (status) return status;
  status = document.createElement("div");
  status.className = "table-search-status";
  status.dataset.tableSearchStatus = "true";
  status.dataset.searchState = "idle";
  status.setAttribute("role", "status");
  status.setAttribute("aria-live", "polite");
  status.innerHTML = `
    <div class="table-search-status-copy">
      <div class="table-search-status-heading">
        <strong data-search-status-title>Search</strong>
        <span class="table-search-status-chip" data-search-status-chip></span>
      </div>
      <p data-search-status-copy></p>
      <p class="table-search-status-meta" data-search-status-meta></p>
    </div>
    <button type="button" data-clear-search-preview="true">Clear search</button>
  `;
  const footer = surface.querySelector("[data-layout='table-footer']");
  if (footer) {
    surface.insertBefore(status, footer);
  } else {
    surface.appendChild(status);
  }
  return status;
}


function getVisibleTableRowCount(table) {
  return Array.from(table?.querySelectorAll("tbody tr") || []).filter(
    (row) => !row.hidden && row.dataset.generatedEmptyState !== "true",
  ).length;
}


function getFilterableRows(table) {
  return Array.from(table?.querySelectorAll("tbody tr") || []).filter(
    (row) => row.dataset.generatedEmptyState !== "true"
      && row.dataset.rowTemplate !== "true"
      && !row.classList.contains("demo-empty-row"),
  );
}


function normalizeFilterText(value) {
  return (value || "")
    .replace(/\([^)]*\)/g, "")
    .replace(/\b\d+\b/g, "")
    .replace(/\s+/g, " ")
    .trim()
    .toLowerCase();
}


function extractFilterChoice(select) {
  if (!select || select.selectedIndex === 0 || select.value === "") return "";
  if (select.value) return normalizeFilterText(select.value);
  const raw = select.options[select.selectedIndex]?.textContent || "";
  return normalizeFilterText(raw.split(":").pop() || raw);
}


function isAllFilterChoice(choice) {
  return !choice || choice === "—" || choice === "-" || /^(all\b|show all\b|any\b|select\b|choose\b|location|industry|owner|status|client|priority|role|stage|readiness|stale status|related to|filters?)$/.test(choice);
}


function rowFilterToken(row, key) {
  if (!row || !key) return "";
  const attr = row.getAttribute(`data-filter-${key}`) || row.dataset[`filter${key.charAt(0).toUpperCase()}${key.slice(1).replace(/-([a-z])/g, (_, c) => c.toUpperCase())}`] || "";
  return normalizeFilterText(attr);
}

function rowMatchesFilterChoice(rowOrText, choice, filterKey) {
  const isRow = rowOrText instanceof Element;
  const row = isRow ? rowOrText : null;
  const text = normalizeFilterText(isRow ? (rowOrText.textContent || "") : (rowOrText || ""));
  if (isAllFilterChoice(choice)) return true;
  if (filterKey && row) {
    const token = rowFilterToken(row, filterKey);
    if (token) return token === choice;
  }
  if (text.includes(choice)) return true;
  /* Synonym expansion: option labels often differ from the row text.
     Each entry: [choice pattern, row-text pattern]. */
  const synonyms = [
    [/potential match/, /review|conflict|potential|match/],
    [/verified unique|^unique$/, /unique/],
    [/not checked|not-checked|not started/, /not checked|not-started/],
    [/missing docs|missing-docs/, /missing|pending docs|action required|needs review/],
    [/^ready$/, /complete|ready/],
    [/^incomplete/, /incomplete|pending|uploaded|parsed/],
    [/^linked$/, /req-|linked/],
    [/^unlinked/, /unlinked/],
    [/^archived/, /archived/],
    [/^passive/, /passive/],
    [/^inactive/, /inactive|deactivated/],
    [/^open$/, /open|sourcing/],
  ];
  for (const [choicePattern, rowPattern] of synonyms) {
    if (choicePattern.test(choice)) return rowPattern.test(text);
  }
  if (/active|open/.test(choice)) return /active|draft|open|sourcing|screen|interview|offer out|profile complete/.test(text) && !/inactive|closed|deactivated|archived/.test(text);
  if (/pending/.test(choice)) return /pending|invite|review needed|action required|intake/.test(text);
  if (/urgent|high|critical|p1/.test(choice)) return /urgent|high|critical|p1|overdue/.test(text);
  if (/low|p3/.test(choice)) return /low|p3/.test(text);
  if (/medium|p2/.test(choice)) return /medium|p2/.test(text);
  if (/engineering/.test(choice)) return /engineer|engineering|frontend|backend|devops/.test(text);
  if (/product/.test(choice)) return /product/.test(text);
  if (/design/.test(choice)) return /design|ux/.test(text);
  if (/remote/.test(choice)) return /remote/.test(text);
  return false;
}


function updateTableEmptyState(table, visibleCount, label, meta = {}) {
  const tbody = table?.querySelector("tbody");
  if (!tbody) return;
  let emptyRow = tbody.querySelector("[data-generated-empty-state='true']");
  const filtered = Boolean(meta.filtered || /match|search|filter/i.test(label || ""));
  if (!emptyRow) {
    emptyRow = document.createElement("tr");
    emptyRow.className = "table-empty-state-row";
    emptyRow.dataset.generatedEmptyState = "true";
    emptyRow.innerHTML = renderTableEmptyCell({
      icon: filtered ? "filter_list_off" : "inventory_2",
      title: filtered ? "No matching records" : undefined,
      hint: label || undefined,
      hintClass: "",
      columnCount: getTableColumnCount(table),
      filtered,
    });
    tbody.appendChild(emptyRow);
  } else {
    emptyRow.innerHTML = renderTableEmptyCell({
      icon: filtered ? "filter_list_off" : "inventory_2",
      title: filtered ? "No matching records" : undefined,
      hint: label || undefined,
      hintClass: "",
      columnCount: getTableColumnCount(table),
      filtered,
    });
  }
  emptyRow.hidden = visibleCount > 0;
}


function syncTableRowVisibility(table) {
  getFilterableRows(table).forEach((row) => {
    row.hidden = row.dataset.hiddenBySearch === "true" || row.dataset.hiddenByFilter === "true" || row.dataset.hiddenByPage === "true";
  });
}


function getTableForFilterToolbar(toolbar) {
  const tableSurface = toolbar?.closest("[data-layout='table-surface']");
  if (tableSurface?.querySelector("table")) return tableSurface.querySelector("table");
  /* Filter bars are usually a sibling card of the table card inside a
     workspace section — fall back to the enclosing section. */
  const scope = toolbar?.closest(".workspace-surface, section, [data-demo-validate]");
  return scope?.querySelector("table") || document.querySelector("table");
}


function isTopbarSearchInput(input) {
  return Boolean(input && (input.id === "topbar-search" || input.closest(".topbar-search, .app-topbar")));
}

function isWorkspaceFilterSelect(select) {
  if (!select || select.closest("table, form, [data-entity-dialog], .overlay-host, [data-overlay-surface], .advanced-filter-panel")) return false;
  if (select.classList.contains("custom-select") || select.id === "req-select") return false;
  /* Agent picker is an action control, not a table filter. */
  if (select.hasAttribute("data-agents-select")) return false;
  /* Global nav search lives in the topbar/home header, not a table toolbar. */
  if (select.hasAttribute("data-global-search")) return false;
  return true;
}

function getToolbarSearchInput(toolbar) {
  if (!toolbar) return null;
  return Array.from(toolbar.querySelectorAll("input[type='text']:not([data-palette-input]), input[type='search'], input:not([type])")).find((input) => {
    if (isTopbarSearchInput(input) || input.closest("table, form, [data-overlay-surface], .overlay-host")) return false;
    const placeholder = input.placeholder || "";
    const name = `${input.getAttribute("aria-label") || ""} ${placeholder}`.toLowerCase();
    return /search|filter|candidate|user|client|req/i.test(name) || Boolean(placeholder);
  }) || null;
}


/* Locate the filter toolbar belonging to a table surface. Pages mark
   nothing explicitly, so infer it: the smallest container inside the
   workspace scope that holds the filter selects and/or the search input. */
function findFilterToolbar(surface) {
  if (!surface || typeof surface.closest !== "function") return null;
  const marked = surface.querySelector("[data-layout='filter-toolbar']:not(:has(table)), [data-layout='pipeline-filter-bar'], [data-layout='report-filter-bar'], .ro-filter-bar");
  if (marked && !marked.querySelector("table")) return marked;
  const scope = surface.closest(".workspace-surface, section") || surface.parentElement || surface;
  const selects = Array.from(scope.querySelectorAll("select")).filter((select) => isWorkspaceFilterSelect(select) && select.options.length > 0);
  const searchInputs = Array.from(scope.querySelectorAll("input[type='text'], input[type='search'], input:not([type])")).filter(
    (input) => /search|filter/i.test(input.placeholder || "") && !input.closest("table, form") && !isTopbarSearchInput(input),
  );
  const nodes = [...selects, ...searchInputs];
  if (!nodes.length) return null;
  let container = nodes[0].parentElement;
  while (container && container !== scope && !nodes.every((node) => container.contains(node))) {
    container = container.parentElement;
  }
  if (!container || container === scope) return nodes[0].closest(".flex, [data-layout='filter-toolbar'], .ro-filter-bar") || nodes[0].parentElement;
  if (container.querySelector(":scope > table, table")) {
    const inner = Array.from(container.children).find((child) => !child.querySelector("table") && nodes.some((node) => child.contains(node)));
    if (inner) return inner;
  }
  return container;
}


function applyToolbarFilters(toolbar, { notify = true, searchTerm: termOverride } = {}) {
  const table = getTableForFilterToolbar(toolbar);
  const selects = toolbar ? Array.from(toolbar.querySelectorAll("select")) : [];
  const searchInput = getToolbarSearchInput(toolbar);
  const rawTerm = termOverride !== undefined ? termOverride : searchInput?.value || "";
  const searchTerm = normalizeFilterText(rawTerm);
  const activeSelects = selects
    .map((select) => ({ select, choice: extractFilterChoice(select), key: select.dataset.filterKey || "" }))
    .filter((entry) => !isAllFilterChoice(entry.choice));
  const tabChoice = normalizeFilterText(toolbar?.dataset.filterTab || "");

  if (table) {
    const rows = getFilterableRows(table);
    if (!rows.length) {
      applyPipelineFilters({ searchTerm, activeSelects, tabChoice });
      return null;
    }
    let visibleCount = 0;
    rows.forEach((row) => {
      const text = normalizeFilterText(row.textContent || "");
      /* Display IDs like REQ-168 normalize to digit-less text (which would
         match every row), so digit-bearing terms match raw text/filterCode
         instead of the normalized form. */
      const rawText = String(row.textContent || "").toLowerCase();
      const rawTermLower = rawTerm.trim().toLowerCase();
      const termHasDigits = /\d/.test(rawTermLower);
      const matchesChoices = activeSelects.every((entry) => rowMatchesFilterChoice(row, entry.choice, entry.key));
      const matchesTab = !tabChoice || isAllFilterChoice(tabChoice) || rowMatchesFilterChoice(row, tabChoice, toolbar?.dataset.filterTabKey || "status");
      const matchesSearch = searchTerm.length < 2
        || (termHasDigits
          ? (rawText.includes(rawTermLower) || String(row.dataset?.filterCode || "").toLowerCase().includes(rawTermLower))
          : text.includes(searchTerm));
      const visible = matchesChoices && matchesTab && matchesSearch;
      row.dataset.hiddenByFilter = visible ? "false" : "true";
      if (visible) visibleCount += 1;
    });
    table.dataset.page = "1";
    applyClientPagination(table);
    const filtered = activeSelects.length > 0 || searchTerm.length >= 2 || (tabChoice && !isAllFilterChoice(tabChoice));
    updateTableEmptyState(
      table,
      visibleCount,
      searchTerm.length >= 2
        ? `No records matched “${rawTerm.trim()}”. Clear the search or adjust filters.`
        : "No records match the selected filters. Choose a broader filter to restore results.",
      { filtered },
    );
    if (notify) {
      const label = activeSelects.length ? activeSelects.map((entry) => entry.choice).join(" + ") : searchTerm.length >= 2 ? searchInput.value.trim() : "All records";
      showToast("View filtered", `${visibleCount} of ${rows.length} records match ${label}.`);
    }
    return { visibleCount, totalCount: rows.length };
  }

  return applyPipelineFilters({ searchTerm, activeSelects, tabChoice, notify, rawTerm });
}

function describeToolbarFilters(toolbar) {
  const selects = Array.from(toolbar?.querySelectorAll("select") || [])
    .map((select) => select.options[select.selectedIndex]?.textContent?.trim())
    .filter((label) => label && !isAllFilterChoice(normalizeFilterText(label.split(":").pop() || label)));
  const search = toolbar?.querySelector("input[placeholder*='Search']")?.value?.trim();
  if (search && search.length >= 2) selects.push(`Search: ${search}`);
  return selects.length ? selects.join(" · ") : "No filters active";
}


const TABLE_PAGE_SIZE = 8;
const TABLE_PAGE_SIZE_MIN = 5;
const TABLE_PAGE_SIZE_MAX = 8;

function getEligibleTableRows(table) {
  return getFilterableRows(table).filter(
    (row) => row.dataset.hiddenBySearch !== "true" && row.dataset.hiddenByFilter !== "true",
  );
}

function getFittedPageSize(anchor, sampleEl) {
  const preset = Number(anchor?.dataset.pageSize);
  if (Number.isFinite(preset) && preset > 0) return preset;
  const sample = sampleEl
    || (anchor?.matches?.("table") ? anchor.querySelector("tbody tr") : anchor?.querySelector(":scope > *:not(.ro-pager)"));
  const rowH = Math.max(36, Math.round(sample?.getBoundingClientRect().height || 44));
  const top = anchor?.getBoundingClientRect?.().top ?? 0;
  const available = window.innerHeight - top - 48;
  const fit = Math.floor(available / rowH);
  const size = Math.min(TABLE_PAGE_SIZE_MAX, Math.max(TABLE_PAGE_SIZE_MIN, Number.isFinite(fit) && fit >= TABLE_PAGE_SIZE_MIN ? fit : TABLE_PAGE_SIZE));
  if (anchor?.dataset) anchor.dataset.pageSize = String(size);
  return size;
}

function getTablePageSize(table) {
  return getFittedPageSize(table, table?.querySelector("tbody tr"));
}

function findTableFooter(table) {
  const surface = table?.closest("[data-layout='table-surface']")
    || table?.closest(".bg-surface, .shell-card")
    || table?.parentElement;
  if (!surface) return null;
  const marked = surface.querySelector(":scope > [data-layout='table-footer'], :scope > .ro-pager");
  if (marked) return marked;
  const wrap = table.closest(".overflow-x-auto, .overflow-auto") || table;
  const sibling = wrap.nextElementSibling;
  if (sibling?.matches?.("[data-layout='table-footer'], .ro-pager")) return sibling;
  if (sibling && /showing\s+\d+|^\s*\d+\s*(–|-|to)\s*\d+\s+of\s+\d+/i.test(sibling.textContent || "") && !sibling.querySelector("select, input, h2, h3")) {
    return sibling;
  }
  return null;
}

function ensurePagerFooter(table) {
  let footer = findTableFooter(table);
  if (footer) {
    footer.dataset.layout = "table-footer";
    footer.classList.add("ro-pager");
    return footer;
  }
  const wrap = table.closest(".overflow-x-auto, .overflow-auto") || table;
  footer = document.createElement("div");
  footer.className = "ro-pager";
  footer.dataset.layout = "table-footer";
  footer.dataset.generatedPager = "true";
  footer.innerHTML = '<span data-page-summary class="ro-pager-summary"></span><div data-layout="pagination-controls" class="ro-pager-controls"></div>';
  wrap.insertAdjacentElement("afterend", footer);
  table._roPager = footer;
  return footer;
}

function csvEscapeCell(value) {
  const text = String(value ?? "").replace(/\s+/g, " ").trim();
  if (/[",\n]/.test(text)) return `"${text.replace(/"/g, '""')}"`;
  return text;
}

function applyClientPagination(table) {
  if (!table || table.closest("[data-overlay-surface]")) return;
  const eligible = getEligibleTableRows(table);
  if (!eligible.length) {
    getFilterableRows(table).forEach((row) => {
      row.dataset.hiddenByPage = "true";
    });
    syncTableRowVisibility(table);
    const emptyFooter = findTableFooter(table);
    if (emptyFooter?.dataset.generatedPager === "true") emptyFooter.remove();
    return;
  }
  const pageSize = getTablePageSize(table);
  const totalPages = Math.max(1, Math.ceil(eligible.length / pageSize) || 1);
  let page = Number(table.dataset.page || 1);
  if (!Number.isFinite(page) || page < 1) page = 1;
  if (page > totalPages) page = totalPages;
  table.dataset.page = String(page);
  const start = (page - 1) * pageSize;
  const end = start + pageSize;
  getFilterableRows(table).forEach((row) => {
    const index = eligible.indexOf(row);
    const onPage = index >= 0 && index >= start && index < end;
    row.dataset.hiddenByPage = onPage ? "false" : "true";
  });
  syncTableRowVisibility(table);
  paintPaginationControls(table, {
    page,
    pageSize,
    totalPages,
    start: eligible.length ? start + 1 : 0,
    end: Math.min(end, eligible.length),
    total: eligible.length,
  });
}

function paintPaginationControls(table, state) {
  const needsPager = state.total > state.pageSize && state.totalPages > 1;
  let footer = findTableFooter(table);
  if (!needsPager) {
    if (footer?.dataset.generatedPager === "true") {
      footer.remove();
      return;
    }
    if (!footer) return;
    const summary = footer.querySelector("[data-page-summary]") || footer.querySelector("span, .font-body-sm, .text-body-sm, p");
    if (summary) {
      summary.dataset.pageSummary = "true";
      summary.textContent = state.total ? `${state.total} of ${state.total}` : "0 of 0";
    }
    const host = footer.querySelector("[data-layout='pagination-controls']");
    if (host) host.innerHTML = "";
    return;
  }
  footer = ensurePagerFooter(table);
  footer.dataset.layout = "table-footer";
  footer.classList.add("ro-pager");
  let summary = footer.querySelector("[data-page-summary]");
  if (!summary) {
    summary = footer.querySelector("span, .font-body-sm, .text-body-sm, p");
  }
  if (!summary) {
    summary = document.createElement("span");
    summary.className = "ro-pager-summary";
    footer.prepend(summary);
  }
  summary.dataset.pageSummary = "true";
  summary.classList.add("ro-pager-summary");
  summary.textContent = `${state.start}–${state.end} of ${state.total}`;
  let host = footer.querySelector("[data-layout='pagination-controls']");
  if (!host) {
    host = document.createElement("div");
    footer.appendChild(host);
  }
  host.dataset.layout = "pagination-controls";
  host.classList.add("ro-pager-controls");
  host.innerHTML = "";
  const makeBtn = (label, page, disabled, ariaLabel) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.textContent = label;
    btn.disabled = Boolean(disabled);
    btn.setAttribute("aria-label", ariaLabel);
    if (typeof page === "number" && !disabled) {
      btn.addEventListener("click", (event) => {
        event.preventDefault();
        event.stopPropagation();
        table.dataset.page = String(page);
        applyClientPagination(table);
      });
    }
    return btn;
  };
  host.appendChild(makeBtn("‹", state.page - 1, state.page <= 1, "Previous page"));
  const status = document.createElement("span");
  status.className = "ro-pager-status";
  status.textContent = `${state.page} / ${state.totalPages}`;
  host.appendChild(status);
  host.appendChild(makeBtn("›", state.page + 1, state.page >= state.totalPages, "Next page"));
}

function getCollectionItems(container) {
  return Array.from(container?.children || []).filter((child) => {
    if (child.classList.contains("ro-pager") || child.dataset.layout === "table-footer") return false;
    if (child.dataset.generatedEmptyState === "true") return false;
    if (child.matches("thead, colgroup, caption, script, style")) return false;
    return true;
  });
}

function applyCollectionPagination(container) {
  if (!container || container.closest("[data-overlay-surface], form, nav")) return;
  const items = getCollectionItems(container);
  if (items.length < TABLE_PAGE_SIZE_MIN) {
    const leftover = container.parentElement?.querySelector(":scope > .ro-pager[data-generated-pager='true']")
      || (container.nextElementSibling?.dataset?.generatedPager === "true" ? container.nextElementSibling : null);
    leftover?.remove();
    return;
  }
  const pageSize = getFittedPageSize(container, items[0]);
  const totalPages = Math.max(1, Math.ceil(items.length / pageSize));
  let page = Number(container.dataset.page || 1);
  if (!Number.isFinite(page) || page < 1) page = 1;
  if (page > totalPages) page = totalPages;
  container.dataset.page = String(page);
  const start = (page - 1) * pageSize;
  const end = start + pageSize;
  items.forEach((item, index) => {
    item.hidden = index < start || index >= end;
  });
  if (totalPages <= 1) {
    const leftover = container.nextElementSibling?.dataset?.generatedPager === "true" ? container.nextElementSibling : null;
    leftover?.remove();
    return;
  }
  let footer = container.nextElementSibling;
  if (!footer?.classList?.contains("ro-pager")) {
    footer = document.createElement("div");
    footer.className = "ro-pager";
    footer.dataset.layout = "table-footer";
    footer.dataset.generatedPager = "true";
    footer.innerHTML = '<span data-page-summary class="ro-pager-summary"></span><div data-layout="pagination-controls" class="ro-pager-controls"></div>';
    container.insertAdjacentElement("afterend", footer);
  }
  const summary = footer.querySelector("[data-page-summary]");
  if (summary) summary.textContent = `${start + 1}–${Math.min(end, items.length)} of ${items.length}`;
  const host = footer.querySelector("[data-layout='pagination-controls']");
  if (!host) return;
  host.innerHTML = "";
  const go = (nextPage) => {
    container.dataset.page = String(nextPage);
    applyCollectionPagination(container);
  };
  const prev = document.createElement("button");
  prev.type = "button";
  prev.textContent = "‹";
  prev.disabled = page <= 1;
  prev.setAttribute("aria-label", "Previous page");
  prev.addEventListener("click", (event) => {
    event.preventDefault();
    event.stopPropagation();
    go(page - 1);
  });
  const status = document.createElement("span");
  status.className = "ro-pager-status";
  status.textContent = `${page} / ${totalPages}`;
  const next = document.createElement("button");
  next.type = "button";
  next.textContent = "›";
  next.disabled = page >= totalPages;
  next.setAttribute("aria-label", "Next page");
  next.addEventListener("click", (event) => {
    event.preventDefault();
    event.stopPropagation();
    go(page + 1);
  });
  host.append(prev, status, next);
}

function refreshWorkspacePagers(scope = document) {
  const root = scope?.nodeType === 1 ? scope : document;
  const tables = root.matches?.("table")
    ? [root]
    : Array.from(root.querySelectorAll(".workspace-surface table, main table"));
  tables.forEach((table) => applyClientPagination(table));
  const listSelectors = [
    "[data-notification-list]",
    "[data-notifications-command-center] .divide-y",
    "[data-follow-up-list]",
    "[data-role-workflow-rows]",
    ".workspace-surface .overflow-y-auto.flex-1",
  ];
  listSelectors.forEach((selector) => {
    root.querySelectorAll?.(selector).forEach((host) => applyCollectionPagination(host));
  });
}

function exportTableAsCsv(table, filename) {
  if (!table) {
    showToast("Nothing to export", "This page does not have a data table.");
    return false;
  }
  const headerCells = Array.from(table.querySelectorAll("thead th"));
  const skipLast = headerCells.length > 1 && !(headerCells[headerCells.length - 1].textContent || "").trim();
  const headers = headerCells
    .filter((_, index) => !(skipLast && index === headerCells.length - 1))
    .map((th) => csvEscapeCell(th.textContent));
  const rows = getEligibleTableRows(table).map((row) => {
    const cells = Array.from(row.children).filter((cell) => cell.tagName === "TD" || cell.tagName === "TH");
    return cells
      .filter((_, index) => !(skipLast && index === cells.length - 1))
      .map((cell) => csvEscapeCell(cell.textContent));
  });
  if (!rows.length) {
    showToast("Nothing to export", "No visible rows match the current filters.");
    return false;
  }
  const csv = ["\ufeff" + headers.join(","), ...rows.map((cols) => cols.join(","))].join("\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename || `${document.body?.dataset.routeId || "export"}.csv`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
  showToast("Export ready", `${rows.length} row${rows.length === 1 ? "" : "s"} downloaded.`);
  return true;
}

function exportWorkspaceAsCsv() {
  const filename = `${document.body?.dataset.routeId || "export"}.csv`;
  const table = document.querySelector(".workspace-surface table") || document.querySelector("main table");
  if (table && getEligibleTableRows(table).length) {
    return exportTableAsCsv(table, filename);
  }
  if (typeof downloadReportCsv === "function" && window.reportState?.columns?.length) {
    downloadReportCsv();
    return true;
  }
  const metrics = [];
  document.querySelectorAll(".workspace-surface .metric-card, [data-role-kpi-strip] > div, .workspace-surface [data-layout='metric-card']").forEach((card) => {
    const label = card.querySelector(".font-label-caps, .text-label-caps, .text-text-muted")?.textContent?.trim();
    const value = card.querySelector(".font-headline-lg, .text-headline-lg, .font-headline-md, .text-headline-md")?.textContent?.trim();
    if (label && value && value !== "—") metrics.push([csvEscapeCell(label), csvEscapeCell(value)]);
  });
  if (!metrics.length) {
    showToast("Nothing to export", "This page has no table or metrics to download.");
    return false;
  }
  const csv = ["\ufeffLabel,Value", ...metrics.map((row) => row.join(","))].join("\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
  showToast("Export ready", `${metrics.length} metrics downloaded.`);
  return true;
}

function getEditRouteForRow(row) {
  const routeId = document.body?.dataset.routeId || "";
  const recordId = row?.dataset.recordId || "";
  const viewRoute = row?.dataset.route || "";
  if (routeId === "candidate-profiles" && recordId) return `candidate-review-drawer.html?candidate_id=${recordId}`;
  if (routeId === "requisition-list" && recordId) return `requisition-intake-edit.html?requisition_id=${recordId}`;
  if (routeId === "client-directory" && recordId) return `contact-form-dialog.html?client_id=${recordId}`;
  if (routeId === "follow-ups" && recordId) return `follow-up-form-dialog.html?id=${recordId}`;
  if (routeId === "offer-management" && viewRoute) return viewRoute;
  if (routeId === "offer-management" && recordId) return `offer-create-dialog.html?offer_id=${recordId}`;
  if (viewRoute.includes("candidate-detail.html")) return viewRoute.replace("candidate-detail.html", "candidate-review-drawer.html");
  if (viewRoute.includes("requisition-detail.html")) return viewRoute.replace("requisition-detail.html", "requisition-intake-edit.html");
  if (viewRoute.includes("client-detail.html")) return viewRoute.replace("client-detail.html", "contact-form-dialog.html");
  return viewRoute;
}

function invokeRowEdit(row) {
  const id = row?.dataset.recordId || "";
  if (!id) return false;
  const routeId = document.body?.dataset.routeId || "";
  if (routeId === "client-directory" && typeof openClientDialog === "function") {
    openClientDialog(id, typeof loadClients === "function" ? loadClients : undefined);
    return true;
  }
  if (routeId === "user-management" && typeof openUserDialog === "function") {
    openUserDialog(id, typeof loadUsers === "function" ? loadUsers : undefined);
    return true;
  }
  if (routeId === "role-management" && typeof openRoleDialog === "function") {
    openRoleDialog(id, typeof loadRoles === "function" ? loadRoles : undefined);
    return true;
  }
  const editRoute = getEditRouteForRow(row);
  if (editRoute && typeof navigateToRoute === "function") {
    navigateToRoute(editRoute);
    return true;
  }
  return false;
}

function invokeRowAction(row, action) {
  const id = row?.dataset.recordId || "";
  const routeId = document.body?.dataset.routeId || "";
  if (action === "duplicate" && routeId === "role-management" && id && typeof duplicateRole === "function") {
    duplicateRole(id);
    return true;
  }
  return false;
}

function rowActionControlMeta(control) {
  const icon = control.querySelector(".material-symbols-outlined")?.textContent?.trim().toLowerCase() || "";
  const label = (control.getAttribute("aria-label") || control.getAttribute("title") || (typeof getActionLabel === "function" ? getActionLabel(control) : "") || "").trim();
  return { icon, label, labelKey: label.toLowerCase() };
}

function isReservedRowAction(control) {
  const { labelKey } = rowActionControlMeta(control);
  if (/approve|reject|assign|remove/.test(labelKey)) return true;
  return Boolean(
    control.dataset.slotAccount
    || control.dataset.editAccount
    || control.dataset.editId
    || control.dataset.approvalId
    || control.classList.contains("approve-btn")
    || control.classList.contains("reject-btn"),
  );
}

function isCompactIconAction(control) {
  if (isReservedRowAction(control)) return false;
  const { icon, labelKey } = rowActionControlMeta(control);
  return /^(edit|visibility|post_add|more_vert|open_in_new|chevron_right|content_copy|history)$/.test(icon)
    || /^(edit|view|more|duplicate|audit)/.test(labelKey);
}

function isCompactActionCell(cell) {
  if (!cell || cell.matches("th")) return false;
  if (cell.dataset.layout === "row-actions") return true;
  const controls = Array.from(cell.querySelectorAll("button, a")).filter((node) => !node.closest(".ro-row-menu"));
  if (!controls.length) return false;
  if (!controls.every(isCompactIconAction)) return false;
  const text = (cell.textContent || "").replace(/\s+/g, " ").trim();
  const controlText = controls.map((node) => (node.textContent || "").replace(/\s+/g, " ").trim()).join(" ");
  return text.length <= controlText.length + 12;
}

function findRowActionCell(row) {
  const cells = Array.from(row?.children || []).filter((cell) => cell.tagName === "TD" || cell.tagName === "TH");
  return cells.find((cell) => cell.dataset.layout === "row-actions")
    || [...cells].reverse().find((cell) => isCompactActionCell(cell))
    || null;
}

function closeRowActionMenus(except) {
  document.querySelectorAll(".ro-row-menu-open").forEach((wrap) => {
    if (wrap === except) return;
    wrap.classList.remove("ro-row-menu-open");
    const menu = wrap.querySelector(".ro-row-menu");
    if (menu) {
      menu.hidden = true;
      menu.classList.remove("is-fixed");
    }
    wrap.querySelector("button[aria-haspopup='menu']")?.setAttribute("aria-expanded", "false");
  });
}

function positionRowActionMenu(trigger, menu) {
  const rect = trigger.getBoundingClientRect();
  menu.classList.add("is-fixed");
  menu.style.position = "fixed";
  menu.style.top = `${Math.round(rect.bottom + 4)}px`;
  menu.style.right = `${Math.round(Math.max(8, window.innerWidth - rect.right))}px`;
  menu.style.left = "auto";
  menu.style.zIndex = "80";
}

function wireHoverKebabMenus(scope = document) {
  const root = scope instanceof Element ? scope : document;
  const hosts = root.matches?.(".ro-row-menu-host")
    ? [root]
    : Array.from(root.querySelectorAll(".ro-row-menu-host"));
  hosts.forEach((host) => {
    if (host.dataset.hoverMenuWired === "true") return;
    const trigger = host.querySelector("button[aria-haspopup='menu']");
    const menu = host.querySelector(".ro-row-menu");
    if (!trigger || !menu) return;
    host.dataset.hoverMenuWired = "true";
    const openMenu = () => {
      clearTimeout(host._kebabCloseTimer);
      closeRowActionMenus(host);
      menu.hidden = false;
      host.classList.add("ro-row-menu-open");
      trigger.setAttribute("aria-expanded", "true");
      positionRowActionMenu(trigger, menu);
    };
    const closeMenu = () => {
      menu.hidden = true;
      menu.classList.remove("is-fixed");
      host.classList.remove("ro-row-menu-open");
      trigger.setAttribute("aria-expanded", "false");
      if (host.contains(document.activeElement)) document.activeElement.blur();
      host.closest("tr")?.blur?.();
    };
    const scheduleClose = () => {
      host._kebabCloseTimer = setTimeout(closeMenu, 140);
    };
    host.addEventListener("mouseenter", openMenu);
    host.addEventListener("mouseleave", scheduleClose);
    menu.addEventListener("mouseenter", () => clearTimeout(host._kebabCloseTimer));
    menu.addEventListener("mouseleave", scheduleClose);
    trigger.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      if (menu.hidden) openMenu();
    });
    menu.addEventListener("click", (event) => {
      const item = event.target.closest("button[role='menuitem']");
      if (!item) return;
      event.preventDefault();
      event.stopPropagation();
      const route = item.dataset.route;
      const row = item.closest("tr") || host.closest("tr");
      closeMenu();
      if (item.dataset.editRecord) invokeRowEdit(row);
      else if (item.dataset.rowAction) invokeRowAction(row, item.dataset.rowAction);
      else if (route && typeof navigateToRoute === "function") navigateToRoute(route);
    });
  });
}

function collectRowActionItems(row, existingButtons) {
  const recordId = row.dataset.recordId || "";
  const viewRoute = row.dataset.route || "";
  const routeId = document.body?.dataset.routeId || "";
  const items = [];
  const seen = new Set();
  const addItem = (label, attrs = {}) => {
    const key = String(label || "").trim().toLowerCase();
    if (!key || seen.has(key)) return;
    seen.add(key);
    items.push({ label, ...attrs });
  };
  existingButtons.forEach((control) => {
    const { icon, label, labelKey } = rowActionControlMeta(control);
    if (icon === "more_vert" || /^more/.test(labelKey)) return;
    if (icon === "history" || /audit/.test(labelKey)) return;
    if (icon === "visibility" || /^view/.test(labelKey)) addItem("View", { route: viewRoute || control.dataset.route || "" });
    else if (icon === "content_copy" || /duplicate/.test(labelKey)) addItem("Duplicate", { action: "duplicate" });
    else if (icon === "post_add" || /requisition/.test(labelKey)) {
      addItem("New requisition", { route: recordId ? `requisition-intake.html?client_id=${recordId}` : "requisition-intake.html" });
    } else if ((icon === "edit" || /^edit/.test(labelKey)) && /permission/.test(labelKey)) {
      addItem("Edit permissions", { route: recordId ? `role-permissions-editor.html?role_id=${recordId}` : "role-permissions-editor.html" });
    } else if (icon === "edit" || /^edit/.test(labelKey)) {
      addItem("Edit", { edit: true });
    } else if (label && control.dataset.route) {
      addItem(label.replace(/^(open|edit)\s+/i, "").trim() || "Open", { route: control.dataset.route });
    }
  });
  if (viewRoute) addItem("View", { route: viewRoute });
  if (recordId) addItem("Edit", { edit: true });
  if (routeId === "client-directory" && recordId) {
    addItem("New requisition", { route: `requisition-intake.html?client_id=${recordId}` });
  }
  if (routeId === "role-management" && recordId) {
    addItem("Edit permissions", { route: `role-permissions-editor.html?role_id=${recordId}` });
    addItem("Duplicate", { action: "duplicate" });
  }
  return items.filter((item) => item.edit || item.action || item.route);
}

function wireRowActionMenu(row) {
  if (!row || row.dataset.rowMenuWired === "true") return;
  const actionCell = findRowActionCell(row);
  if (!actionCell) return;
  const existing = Array.from(actionCell.querySelectorAll("button, a")).filter((node) => !node.closest(".ro-row-menu"));
  if (!existing.length) return;
  if (!existing.every(isCompactIconAction)) return;
  const items = collectRowActionItems(row, existing);
  if (!items.length) return;
  row.dataset.rowMenuWired = "true";
  const moreBtn = document.createElement("button");
  moreBtn.type = "button";
  moreBtn.className = "ro-card-kebab-trigger";
  moreBtn.innerHTML = `<span class="material-symbols-outlined">more_vert</span>`;
  moreBtn.setAttribute("aria-haspopup", "menu");
  moreBtn.setAttribute("aria-expanded", "false");
  moreBtn.setAttribute("aria-label", "Row actions");
  moreBtn.dataset.rowMenuBound = "true";
  actionCell.classList.add("relative", "ro-row-menu-host");
  actionCell.dataset.layout = "row-actions";
  actionCell.replaceChildren(moreBtn);
  const menu = document.createElement("div");
  menu.className = "ro-row-menu";
  menu.hidden = true;
  menu.setAttribute("role", "menu");
  const recordId = row.dataset.recordId || "";
  menu.innerHTML = items.map((item) => {
    if (item.edit) return `<button type="button" role="menuitem" data-edit-record="${recordId}" aria-label="Edit">Edit</button>`;
    if (item.action) return `<button type="button" role="menuitem" data-row-action="${item.action}">${item.label}</button>`;
    return `<button type="button" role="menuitem" data-route="${item.route || ""}">${item.label}</button>`;
  }).join("");
  actionCell.appendChild(menu);
}

function wireLiveTableInteractions(scope = document) {
  const tables = scope?.matches?.("table")
    ? [scope]
    : Array.from((scope || document).querySelectorAll("table"));
  tables.forEach((table) => {
    getFilterableRows(table).forEach((row) => wireRowActionMenu(row));
    if (typeof wireHoverKebabMenus === "function") wireHoverKebabMenus(table);
    if (!table.dataset.page) table.dataset.page = "1";
    applyClientPagination(table);
  });
  hydrateLiveFilters(scope?.matches?.("table") ? scope.closest(".workspace-surface, section") || document : scope);
}


function setupAdvancedFilterPanels(scope = document) {
  scope.querySelectorAll("[data-layout='filter-toolbar']").forEach((toolbar) => {
    const trigger = Array.from(toolbar.querySelectorAll("button")).find((button) => /more filters|filter_list/i.test(getActionLabel(button)));
    if (!trigger || trigger.dataset.advancedFilterBound === "true") return;
    trigger.dataset.advancedFilterBound = "true";
    trigger.type = "button";
    const panel = document.createElement("div");
    const panelId = `advanced-filters-${Math.random().toString(16).slice(2)}`;
    panel.id = panelId;
    panel.className = "advanced-filter-panel";
    panel.setAttribute("role", "region");
    panel.setAttribute("aria-live", "polite");
    panel.innerHTML = `
      <span data-advanced-filter-copy></span>
      <button type="button" data-reset-toolbar-filters="true">Reset filters</button>
    `;
    toolbar.insertAdjacentElement("afterend", panel);
    trigger.setAttribute("aria-expanded", "false");
    const initialCopy = panel.querySelector("[data-advanced-filter-copy]");
    if (initialCopy) initialCopy.textContent = `Current view: ${describeToolbarFilters(toolbar)}.`;
    trigger.setAttribute("aria-controls", panelId);

    const syncCopy = () => {
      const copy = panel.querySelector("[data-advanced-filter-copy]");
      if (copy) {
        copy.textContent = `Current view: ${describeToolbarFilters(toolbar)}.`;
      }
    };

    trigger.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      const visible = !panel.classList.contains("is-visible");
      panel.classList.toggle("is-visible", visible);
      trigger.setAttribute("aria-expanded", visible ? "true" : "false");
      syncCopy();
    });

    panel.querySelector("[data-reset-toolbar-filters]")?.addEventListener("click", () => {
      toolbar.querySelectorAll("select").forEach((select) => {
        select.selectedIndex = 0;
      });
      const searchField = getToolbarSearchInput(toolbar);
      if (searchField) searchField.value = "";
      const result = applyToolbarFilters(toolbar, { notify: false });
      syncCopy();
      showToast("Filters reset", result ? `Showing ${result.visibleCount} of ${result.totalCount} records.` : "The workspace is back to its default view.");
    });
  });
}


function clearTableSearchPreview(table) {
  if (!table) return;
  if (table.dataset.previewTimerId) {
    window.clearTimeout(Number(table.dataset.previewTimerId));
    delete table.dataset.previewTimerId;
  }
  table.querySelectorAll("tbody tr[data-generated-empty-state='true']").forEach((row) => row.remove());
  table.querySelectorAll("tbody tr[data-hidden-by-search='true']").forEach((row) => {
    row.hidden = false;
    delete row.dataset.hiddenBySearch;
  });
  getFilterableRows(table).forEach((row) => {
    row.dataset.hiddenBySearch = "false";
  });
  syncTableRowVisibility(table);
  const status = table.closest("[data-layout='table-surface']")?.querySelector("[data-table-search-status]");
  if (status) {
    status.classList.remove("is-visible");
    status.dataset.searchState = "idle";
  }
  delete table.dataset.previewTerm;
  delete table.dataset.previewState;
  delete table.dataset.previewRequestId;
}


function setTableSearchPreview(table, term) {
  if (!table) return null;
  clearTableSearchPreview(table);

  const normalized = term.trim();
  const status = ensureTableSearchStatus(table);
  const titleNode = status?.querySelector("[data-search-status-title]");
  const copyNode = status?.querySelector("[data-search-status-copy]");
  const metaNode = status?.querySelector("[data-search-status-meta]");
  const chipNode = status?.querySelector("[data-search-status-chip]");
  const requestId = `${Date.now()}-${Math.random().toString(16).slice(2, 8)}`;

  table.dataset.previewTerm = normalized;
  table.dataset.previewState = "loading";
  table.dataset.previewRequestId = requestId;
  if (status && titleNode && copyNode) {
    status.dataset.searchState = "loading";
    titleNode.textContent = `Searching for "${normalized}"`;
    copyNode.textContent = "";
    if (metaNode) metaNode.textContent = "";
    if (chipNode) chipNode.textContent = "Loading";
    status.classList.add("is-visible");
  }

  const finalizePreview = () => {
    if (table.dataset.previewRequestId !== requestId) return;
    delete table.dataset.previewTimerId;

    const rows = getFilterableRows(table);
    const needle = normalized.toLowerCase();
    let matches = 0;
    rows.forEach((row) => {
      const hit = (row.textContent || "").toLowerCase().includes(needle);
      row.dataset.hiddenBySearch = hit ? "false" : "true";
      if (hit) matches += 1;
    });
    syncTableRowVisibility(table);
    table.dataset.previewState = matches ? "results" : "empty";

    if (!matches) {
      const body = table.querySelector("tbody");
      const columnCount = getTableColumnCount(table);
      const emptyRow = document.createElement("tr");
      emptyRow.className = "table-empty-state-row";
      emptyRow.dataset.generatedEmptyState = "true";
      emptyRow.innerHTML = renderTableEmptyCell({
        icon: "search_off",
        title: `No matching records for "${normalized}"`,
        hint: "Clear the search or try a broader term.",
        hintClass: "",
        columnCount,
      });
      body?.appendChild(emptyRow);
      if (status && titleNode && copyNode) {
        status.dataset.searchState = "empty";
        titleNode.textContent = `No records matched "${normalized}"`;
        copyNode.textContent = "Clear the search or try a broader term.";
        if (metaNode) metaNode.textContent = "";
        if (chipNode) chipNode.textContent = "Empty";
        status.classList.add("is-visible");
      }
      return;
    }

    if (status && titleNode && copyNode) {
      status.dataset.searchState = "results";
      titleNode.textContent = `Results for "${normalized}"`;
      copyNode.textContent = "";
      if (metaNode) metaNode.textContent = `${matches} of ${rows.length} records match.`;
      if (chipNode) chipNode.textContent = "Results";
      status.classList.add("is-visible");
    }
  };

  table.dataset.previewTimerId = String(window.setTimeout(finalizePreview, 180));
  return null;
}


function getRowPrimaryAction(row) {
  if (!row) return null;
  const actionCandidates = Array.from(row.querySelectorAll("a, button")).filter((control) => {
    if (control.closest("thead")) return false;
    if (control.matches("input, select, textarea")) return false;
    if (control.closest("[data-layout='row-actions']")) return true;
    return Boolean((control.textContent || control.getAttribute("aria-label") || control.getAttribute("title") || "").trim());
  });
  return actionCandidates[0] || null;
}


function getCellSortValue(cell) {
  const raw = (cell?.textContent || "").replace(/\s+/g, " ").trim();
  const number = raw.match(/-?\d+(?:\.\d+)?/);
  if (number && /^(?:\$|₹|€|£)?\s*-?\d|^\d+\s*(?:d|days?|hrs?|hours?|%)?\b/i.test(raw)) {
    return Number(number[0]);
  }
  return raw.toLowerCase();
}


function compareSortValues(a, b) {
  if (typeof a === "number" && typeof b === "number") return a - b;
  return String(a).localeCompare(String(b), undefined, { numeric: true, sensitivity: "base" });
}


function setupSortableTables(scope = document) {
  scope.querySelectorAll("table").forEach((table) => {
    if (table.dataset.sortableBound === "true") return;
    table.dataset.sortableBound = "true";
    const headers = Array.from(table.querySelectorAll("thead th"));
    headers.forEach((header, columnIndex) => {
      const label = (header.textContent || "").replace(/\s+/g, " ").trim();
      if (!label || /actions?|^$/.test(label.toLowerCase()) || header.querySelector("input")) return;
      header.dataset.sortableColumn = "true";
      header.tabIndex = 0;
      header.setAttribute("role", "button");
      header.setAttribute("aria-sort", "none");
      header.setAttribute("aria-label", `Sort by ${label}`);

      const sortColumn = () => {
        const current = header.dataset.sortDirection === "asc" ? "desc" : "asc";
        headers.forEach((item) => {
          delete item.dataset.sortDirection;
          item.setAttribute("aria-sort", "none");
        });
        header.dataset.sortDirection = current;
        header.setAttribute("aria-sort", current === "asc" ? "ascending" : "descending");
        const tbody = table.querySelector("tbody");
        const rows = getFilterableRows(table);
        rows
          .sort((rowA, rowB) => {
            const valueA = getCellSortValue(rowA.children[columnIndex]);
            const valueB = getCellSortValue(rowB.children[columnIndex]);
            return current === "asc" ? compareSortValues(valueA, valueB) : compareSortValues(valueB, valueA);
          })
          .forEach((row) => tbody?.appendChild(row));
        const emptyState = tbody?.querySelector("[data-generated-empty-state='true'], .demo-empty-row");
        if (emptyState) tbody?.appendChild(emptyState);
        applyClientPagination(table);
        showToast("Table sorted", `${label} is sorted ${current === "asc" ? "ascending" : "descending"}.`);
      };

      header.addEventListener("click", sortColumn);
      header.addEventListener("keydown", (event) => {
        if (event.key !== "Enter" && event.key !== " ") return;
        event.preventDefault();
        sortColumn();
      });
    });
  });
}


function setupTableInteractionPolish(scope = document) {
  scope.querySelectorAll("table").forEach((table) => {
    const bodyRows = Array.from(table.querySelectorAll("tbody tr"));
    bodyRows.forEach((row) => {
      const cells = Array.from(row.children);
      const actionCell = typeof findRowActionCell === "function"
        ? findRowActionCell(row)
        : [...cells].reverse().find((cell) => cell.querySelector("button, a"));
      if (!actionCell) return;
      actionCell.dataset.layout = "row-actions";
      actionCell.querySelectorAll("button, a").forEach((control) => {
        if (control.tagName === "BUTTON" && !control.getAttribute("type")) {
          control.setAttribute("type", "button");
        }
        if (!control.getAttribute("aria-label")) {
          control.setAttribute("aria-label", inferButtonLabel(control));
        }
        if (!control.getAttribute("title")) {
          control.setAttribute("title", inferButtonLabel(control));
        }
      });
      actionCell.querySelectorAll("div").forEach((group) => {
        if (group.className.includes("group-hover:opacity-100")) {
          group.classList.add("table-row-action-reveal");
        }
      });
      row.dataset.rowSummary = getRowSummary(row);
      if (!row.hasAttribute("tabindex")) {
        row.tabIndex = 0;
      }
      row.dataset.rowInteractive = "true";
    });

    bodyRows.forEach((row, index) => {
      row.addEventListener("focus", () => {
        bodyRows.forEach((item) => item.classList.remove("is-active-record"));
        row.classList.add("is-active-record");
      });

      row.addEventListener("click", (event) => {
        if (event.target.closest("button, a, input, select, textarea, label")) return;
        bodyRows.forEach((item) => item.classList.remove("is-active-record"));
        row.classList.add("is-active-record");
        row.focus();
      });

      row.addEventListener("keydown", (event) => {
        if (event.target !== row) return;
        if (event.key === "ArrowDown") {
          event.preventDefault();
          bodyRows[(index + 1) % bodyRows.length]?.focus();
          return;
        }
        if (event.key === "ArrowUp") {
          event.preventDefault();
          bodyRows[(index - 1 + bodyRows.length) % bodyRows.length]?.focus();
          return;
        }
        if (event.key === "Home") {
          event.preventDefault();
          bodyRows[0]?.focus();
          return;
        }
        if (event.key === "End") {
          event.preventDefault();
          bodyRows[bodyRows.length - 1]?.focus();
          return;
        }
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          row.click();
          if (row.classList.contains("is-active-record")) {
            return;
          }
          const primaryAction = getRowPrimaryAction(row);
          if (primaryAction) {
            primaryAction.click();
            return;
          }
        }
      });
    });
  });
}


function setPaginationButtonActive(button, active) {
  if (!button) return;
  button.setAttribute("aria-pressed", active ? "true" : "false");
  button.classList.toggle("is-active", active);
}


function setupTableControlPolish() {
  document.querySelectorAll("table").forEach((table) => ensureInferredTableSurface(table));
  document.querySelectorAll("[data-layout='table-surface']").forEach((surface) => {
    const footer = surface.querySelector("[data-layout='table-footer'], :scope > div:last-of-type");
    const filterToolbar = findFilterToolbar(surface);
    const paginationButtons = Array.from(footer?.querySelectorAll("button") || []);
    const paginationHost = paginationButtons[0]?.parentElement;
    if (footer && paginationButtons.length > 0) {
      footer.dataset.layout = "table-footer";
    }
    if (paginationHost && paginationHost !== footer) {
      paginationHost.dataset.layout = "pagination-controls";
    }
    const liveTable = surface.querySelector("table");
    if (liveTable) applyClientPagination(liveTable);

    filterToolbar?.querySelectorAll("button").forEach((button) => {
      const label = getActionLabel(button);
      if (button.dataset.toast || button.dataset.route) return;
      if (/more filters/.test(label)) {
        return;
      }
    });

    filterToolbar?.querySelectorAll("select").forEach((select) => {
      if (select.dataset.filterPolished === "true") return;
      select.dataset.filterPolished = "true";
      select.addEventListener("change", () => {
        const choice = select.options[select.selectedIndex]?.textContent?.trim() || "Current filter";
        const result = applyToolbarFilters(filterToolbar, { notify: false });
        showToast("Filter applied", result ? `${choice} — showing ${result.visibleCount} of ${result.totalCount} records.` : choice);
      });
    });

    filterToolbar?.querySelectorAll("input[type='text'], input:not([type])").forEach((input) => {
      if (input.dataset.liveFilterBound === "true" || input.type === "email" || input.type === "password") return;
      input.dataset.liveFilterBound = "true";
      input.addEventListener("input", () => {
        if (input.dataset.liveFilterTimerId) {
          window.clearTimeout(Number(input.dataset.liveFilterTimerId));
        }
        input.dataset.liveFilterTimerId = String(window.setTimeout(() => {
          delete input.dataset.liveFilterTimerId;
          const value = input.value.trim();
          if (value.length === 1) return;
          applyToolbarFilters(filterToolbar, { notify: value.length >= 2 });
        }, 220));
      });
      input.addEventListener("keydown", (event) => {
        if (event.key !== "Escape") return;
        input.value = "";
        applyToolbarFilters(filterToolbar);
      });
    });

    /* Real paging is owned by applyClientPagination — leftover prototype
       page-number buttons are rebuilt there instead of being cosmetic. */
  });

  document.querySelectorAll("[data-layout='filter-toolbar']").forEach((filterToolbar) => {
    filterToolbar.querySelectorAll("button").forEach((button) => {
      const label = getActionLabel(button);
      if (button.dataset.toast || button.dataset.route) return;
      if (/more filters/.test(label)) {
        return;
      }
    });

    filterToolbar.querySelectorAll("select").forEach((select) => {
      if (select.dataset.filterPolished === "true") return;
      select.dataset.filterPolished = "true";
      select.addEventListener("change", () => {
        const choice = select.options[select.selectedIndex]?.textContent?.trim() || "Current filter";
        const result = applyToolbarFilters(filterToolbar, { notify: false });
        showToast("Filter applied", result ? `${choice} — showing ${result.visibleCount} of ${result.totalCount} records.` : choice);
      });
    });

    const searchField = getToolbarSearchInput(filterToolbar);
    if (searchField && searchField.dataset.liveFilterBound !== "true") {
      const input = searchField;
      input.dataset.liveFilterBound = "true";
      input.addEventListener("input", () => {
        if (input.dataset.liveFilterTimerId) {
          window.clearTimeout(Number(input.dataset.liveFilterTimerId));
        }
        input.dataset.liveFilterTimerId = String(window.setTimeout(() => {
          delete input.dataset.liveFilterTimerId;
          const value = input.value.trim();
          if (value.length === 1) return;
          applyToolbarFilters(filterToolbar, { notify: value.length >= 2 });
        }, 220));
      });
      input.addEventListener("keydown", (event) => {
        if (event.key !== "Escape") return;
        input.value = "";
        applyToolbarFilters(filterToolbar);
      });
    }
  });
}


const LIVE_FILTER_VOCAB = {
  status: [["", "All statuses"], ["active", "Active"], ["inactive", "Inactive"], ["pending", "Pending"], ["archived", "Archived"], ["open", "Open"], ["sourcing", "Sourcing"], ["closed", "Closed"]],
  duplicate: [["", "All duplicate states"], ["unique", "Verified Unique"], ["potential", "Potential Matches"], ["not-checked", "Not Checked"]],
  readiness: [["", "All readiness"], ["ready", "Ready"], ["incomplete", "Incomplete"], ["missing-docs", "Missing Docs"]],
  linkage: [["", "All linkage"], ["linked", "Linked"], ["unlinked", "Unlinked"]],
  priority: [["", "All priorities"], ["critical", "Critical"], ["urgent", "Urgent"], ["high", "High"], ["medium", "Medium"], ["low", "Low"]],
  "stale-status": [["", "All freshness"], ["fresh", "Fresh"], ["stale", "Stale"]],
};

const FILTER_BUTTON_KEYS = {
  client: "client",
  status: "status",
  priority: "priority",
  owner: "owner",
  stage: "stage",
  category: "category",
  readiness: "readiness",
  "stale status": "stale-status",
  role: "role",
  location: "location",
};

const FILTER_ALL_LABELS = {
  owner: "All owners",
  client: "All clients",
  category: "All categories",
  status: "All statuses",
  priority: "All priorities",
  stage: "All stages",
  role: "All roles",
  location: "All locations",
  industry: "All industries",
  duplicate: "All duplicate states",
  readiness: "All readiness",
  linkage: "All linkage",
  type: "All types",
  round: "All rounds",
  interviewer: "All interviewers",
  department: "All departments",
  req: "All requisitions",
  "stale-status": "All freshness",
};

function inferFilterKeyFromLabel(label) {
  const raw = String(label || "").split(":")[0].trim().toLowerCase().replace(/^all\s+/, "");
  if (FILTER_BUTTON_KEYS[raw]) return FILTER_BUTTON_KEYS[raw];
  if (/duplicate/.test(raw)) return "duplicate";
  if (/req link|linkage/.test(raw)) return "linkage";
  if (/related/.test(raw)) return "related";
  if (/industry/.test(raw)) return "industry";
  if (/request type|type/.test(raw)) return "type";
  return raw.replace(/\s+/g, "-") || "filter";
}

function uniqueRowFilterValues(table, key) {
  const values = new Map();
  const headers = Array.from(table?.querySelectorAll("thead th") || []).map((th) => normalizeFilterText(th.textContent));
  const aliases = {
    type: ["request type", "type"],
    priority: ["priority"],
    status: ["status"],
    owner: ["owner", "requester"],
    client: ["client", "company", "account"],
    location: ["location"],
    role: ["role"],
    stage: ["stage"],
    category: ["category"],
    industry: ["industry"],
    round: ["round"],
    interviewer: ["interviewer"],
    department: ["department"],
  }[key] || [String(key || "").replace(/-/g, " ")];
  const colIndex = headers.findIndex((header) => aliases.some((alias) => header === alias || header.startsWith(`${alias} `) || header.includes(alias)));
  getFilterableRows(table).forEach((row) => {
    let raw = (row.getAttribute(`data-filter-${key}`) || "").trim();
    if ((!raw || raw === "—") && colIndex >= 0) {
      raw = (row.children[colIndex]?.textContent || "").replace(/\s+/g, " ").trim();
      if (key === "priority") raw = raw.replace(/overdue\s+\d+d/i, "").replace(/\d+d left/i, "").replace(/no sla/i, "").trim();
    }
    if (!raw || raw === "—") return;
    values.set(normalizeFilterText(raw), raw);
  });
  return Array.from(values.entries()).sort((a, b) => a[1].localeCompare(b[1]));
}

function uniqueCardFilterValues(key) {
  const values = new Map();
  document.querySelectorAll(".pipeline-card").forEach((card) => {
    const raw = (card.getAttribute(`data-filter-${key}`) || "").trim();
    if (!raw || raw === "—") return;
    values.set(normalizeFilterText(raw), raw);
  });
  return Array.from(values.entries()).sort((a, b) => a[1].localeCompare(b[1]));
}

function escapeFilterAttr(value) {
  return String(value || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/"/g, "&quot;");
}

function uniqueCollectionFilterValues(key) {
  const values = new Map();
  document.querySelectorAll(".pipeline-card, article[data-notification-id], [data-live-notification-row]").forEach((node) => {
    const raw = (node.getAttribute(`data-filter-${key}`) || "").trim();
    if (!raw || raw === "—") return;
    values.set(normalizeFilterText(raw), raw);
  });
  return Array.from(values.entries()).sort((a, b) => a[1].localeCompare(b[1]));
}

function fillFilterSelect(select, key, table) {
  const previous = select.value;
  const allLabel = FILTER_ALL_LABELS[key] || `All ${String(key || "filters").replace(/-/g, " ")}`;
  const seen = new Set();
  const options = [];
  const addOption = (value, label) => {
    const text = String(label || "").trim();
    if (!text) return;
    const normalized = normalizeFilterText(text);
    const isAll = isAllFilterChoice(normalized) || /^all\b/.test(normalized) || /:\s*(all|show all)$/.test(normalized);
    if (isAll) {
      if (!options.length) {
        options.push(["", allLabel]);
        seen.add("all");
      }
      return;
    }
    if (seen.has(normalized) || seen.has(String(value || ""))) return;
    seen.add(normalized);
    if (value) seen.add(String(value));
    options.push([value == null ? "" : String(value), text]);
  };
  addOption("", allLabel);
  (LIVE_FILTER_VOCAB[key] || []).forEach(([value, label]) => addOption(value, label));
  const extra = table ? uniqueRowFilterValues(table, key) : uniqueCollectionFilterValues(key);
  extra.forEach(([value, label]) => addOption(value, label));
  select.innerHTML = options.map(([value, label]) => `<option value="${escapeFilterAttr(value)}">${escapeFilterAttr(label)}</option>`).join("");
  if (previous && Array.from(select.options).some((opt) => opt.value === previous)) select.value = previous;
  else select.selectedIndex = 0;
  select.dataset.filterKey = key;
}

function replaceFilterButtonWithSelect(button, key) {
  const select = document.createElement("select");
  select.className = "bg-surface border border-border rounded text-on-surface font-body-sm py-1.5 pl-2 pr-8 focus:outline-none focus:border-primary";
  select.dataset.filterKey = key;
  select.setAttribute("aria-label", `Filter by ${key.replace(/-/g, " ")}`);
  button.replaceWith(select);
  return select;
}

function bindLiveFilterControl(toolbar, control) {
  if (!toolbar || !control || control.dataset.filterPolished === "true") return;
  control.dataset.filterPolished = "true";
  if (control.tagName === "SELECT") {
    control.addEventListener("change", () => {
      const choice = control.options[control.selectedIndex]?.textContent?.trim() || "Current filter";
      const result = applyToolbarFilters(toolbar, { notify: false });
      if (result) showToast("Filter applied", `${choice} — showing ${result.visibleCount} of ${result.totalCount} records.`);
    });
    return;
  }
  control.dataset.liveFilterBound = "true";
  control.addEventListener("input", () => {
    if (control.dataset.liveFilterTimerId) window.clearTimeout(Number(control.dataset.liveFilterTimerId));
    control.dataset.liveFilterTimerId = String(window.setTimeout(() => {
      delete control.dataset.liveFilterTimerId;
      const value = control.value.trim();
      if (value.length === 1) return;
      applyToolbarFilters(toolbar, { notify: false });
    }, 220));
  });
}

function bindFilterTabs(toolbar) {
  const groups = Array.from(toolbar.querySelectorAll(".flex.space-x-1, [data-toggle-group='true'], .flex.items-center.gap-1"));
  groups.forEach((group) => {
    const buttons = Array.from(group.querySelectorAll("button")).filter((button) => {
      const label = getActionLabel(button);
      return /^(all\b|my\b|active|pending|deactivated|onboarding|urgent)/.test(label);
    });
    if (buttons.length < 2) return;
    const labels = buttons.map((button) => getActionLabel(button));
    if (labels.some((label) => /^(unread|read)$/.test(label))) return;
    buttons.forEach((button) => {
      if (button.dataset.filterTabBound === "true") return;
      button.dataset.filterTabBound = "true";
      button.addEventListener("click", (event) => {
        event.preventDefault();
        buttons.forEach((item) => {
          item.classList.remove("bg-surface", "bg-secondary-container", "text-on-surface", "text-on-secondary-container", "is-active");
          item.classList.add("text-text-muted");
          item.setAttribute("aria-pressed", "false");
        });
        button.classList.remove("text-text-muted");
        button.classList.add("bg-surface", "text-on-surface", "is-active");
        button.setAttribute("aria-pressed", "true");
        const label = getActionLabel(button);
        toolbar.dataset.filterTab = /^(all|all clients|all users|all reqs|my reqs)$/.test(label) ? "" : label.replace(/^my\s+/, "");
        if (/urgent/.test(label)) toolbar.dataset.filterTabKey = "priority";
        else if (/my req/.test(label)) toolbar.dataset.filterTabKey = "owner";
        else toolbar.dataset.filterTabKey = "status";
        applyToolbarFilters(toolbar, { notify: false });
      });
    });
  });
}

function nodeHasDataTable(node) {
  return Boolean(node?.querySelector?.("table"));
}

function isDecorativeFilterButton(button) {
  if (!button || button.dataset.route) return false;
  const icon = button.querySelector(".material-symbols-outlined")?.textContent?.trim().toLowerCase() || "";
  const label = typeof getActionLabel === "function" ? getActionLabel(button) : "";
  return icon === "filter_list" && (!label || /^(filter_list|more filters|filters)$/.test(label));
}

function placeFilterBarBeforeTable(bar) {
  if (!bar || nodeHasDataTable(bar)) return bar;
  const table = getTableForFilterToolbar(bar) || bar.closest(".workspace-surface, section, .bg-surface")?.querySelector("table");
  const card = table?.closest(".bg-surface, [data-layout='table-surface'], section.shell-card") || table?.parentElement?.parentElement;
  if (!card || !table) return bar;
  const tableWrap = Array.from(card.children).find((child) => child.contains(table)) || table.closest(".overflow-x-auto, .overflow-auto") || table;
  if (tableWrap && tableWrap.parentElement === card && bar.parentElement !== card) {
    card.insertBefore(bar, tableWrap);
  } else if (bar.parentElement !== card && tableWrap?.parentElement) {
    tableWrap.parentElement.insertBefore(bar, tableWrap);
  }
  const emptyHeader = Array.from(card.children).find((child) => child !== bar && !child.contains(table) && !child.querySelector("select, input, button:not(.md\\:hidden button)") && child.matches(".border-b, .bg-surface-alt"));
  if (emptyHeader && !emptyHeader.querySelector("select, input[type='text'], input[type='search']")) {
    const onlyHidden = Array.from(emptyHeader.children).every((child) => getComputedStyle(child).display === "none" || child === bar);
    if (onlyHidden || !emptyHeader.textContent.trim()) emptyHeader.remove();
  }
  return bar;
}

function collectFilterControls(root) {
  if (!root) return { tabs: [], searches: [], selects: [], dates: [], buttons: [] };
  const tabs = Array.from(root.querySelectorAll("[data-toggle-group='true'], [role='tablist']")).filter((node) => !node.closest("table, .overlay-host"));
  if (!tabs.length) {
    const group = Array.from(root.querySelectorAll(".flex.items-center.gap-1, .flex.space-x-1")).find((node) => {
      const buttons = Array.from(node.querySelectorAll("button"));
      return buttons.length >= 2 && buttons.every((button) => /^(all\b|my\b|active|pending|deactivated|onboarding|urgent)/.test(getActionLabel(button)));
    });
    if (group) tabs.push(group);
  }
  const searches = Array.from(root.querySelectorAll("input[type='text'], input[type='search'], input:not([type])")).filter((input) => {
    if (isTopbarSearchInput(input) || input.closest("table, form, .overlay-host")) return false;
    return /search|filter/i.test(`${input.placeholder || ""} ${input.getAttribute("aria-label") || ""}`);
  });
  const selects = Array.from(root.querySelectorAll("select")).filter((select) => isWorkspaceFilterSelect(select));
  const dates = Array.from(root.querySelectorAll("input[type='date']")).filter((input) => !input.closest("table, form, .overlay-host"));
  const buttons = Array.from(root.querySelectorAll("button")).filter((button) => {
    if (button.dataset.route || button.closest("table, [aria-haspopup='menu'], [data-toggle-group], [role='tablist']")) return false;
    return Boolean(FILTER_BUTTON_KEYS[getActionLabel(button)]);
  });
  return { tabs, searches, selects, dates, buttons };
}

function ensureDedicatedFilterBar(toolbar) {
  if (!toolbar) return toolbar;
  const host = nodeHasDataTable(toolbar)
    ? toolbar
    : toolbar.closest(".bg-surface:has(table), [data-layout='table-surface'], section.shell-card") || toolbar;
  const existing = Array.from((host || toolbar).querySelectorAll("[data-layout='filter-toolbar'], [data-layout='pipeline-filter-bar'], .ro-filter-bar")).find((node) => !nodeHasDataTable(node));
  const table = host.querySelector("table");
  const tableWrap = table ? (Array.from(host.children).find((child) => child.contains(table)) || table.closest(".overflow-x-auto, .overflow-auto") || table) : null;
  let bar = existing;
  if (!bar) {
    bar = document.createElement("div");
    bar.className = "ro-filter-bar";
    bar.dataset.layout = "filter-toolbar";
    if (tableWrap?.parentElement) tableWrap.parentElement.insertBefore(bar, tableWrap);
    else if (!nodeHasDataTable(toolbar)) {
      toolbar.classList.add("ro-filter-bar");
      toolbar.dataset.layout = "filter-toolbar";
      bar = toolbar;
    } else {
      host.insertBefore(bar, host.firstChild);
    }
  }
  const controls = collectFilterControls(host);
  const movedNodes = [
    ...controls.tabs,
    ...controls.searches.map((input) => input.closest(".relative") || input),
    ...controls.selects,
    ...controls.dates,
    ...controls.buttons,
  ].filter(Boolean);
  /* Ancestors of the controls being moved, so emptied wrappers can be
     pruned afterwards instead of rendering as stray bordered strips. */
  const movedAncestors = new Set();
  movedNodes.forEach((node) => {
    let parent = node.parentElement;
    while (parent && parent !== host && parent !== bar) {
      movedAncestors.add(parent);
      parent = parent.parentElement;
    }
  });
  movedNodes.forEach((node) => {
    if (bar === node || bar.contains(node) || node.contains(bar)) return;
    bar.appendChild(node);
  });
  movedAncestors.forEach((wrap) => {
    if (!wrap.isConnected || bar.contains(wrap) || wrap === host) return;
    if (wrap.contains(bar) || (table && wrap.contains(table))) return;
    /* Small label chips (e.g. "FILTERS") orphaned when their controls moved. */
    Array.from(wrap.children).forEach((child) => {
      if (child === bar || bar.contains(child) || child.contains(bar)) return;
      if (child.querySelector("input, select, button, textarea, table, a[href], h1, h2, h3, h4, h5, h6, [data-toggle-group], [role='tablist']")) return;
      if ((child.textContent || "").trim().length <= 16) child.remove();
    });
    if (wrap.querySelector("input, select, button, textarea, table, a[href], h1, h2, h3, h4, h5, h6")) return;
    const text = (wrap.textContent || "").trim();
    if (text.length > 16) return;
    wrap.remove();
  });
  if (tableWrap && bar.parentElement !== tableWrap.parentElement && tableWrap.parentElement) {
    tableWrap.parentElement.insertBefore(bar, tableWrap);
  }
  if (host !== bar && host.getAttribute("data-layout") === "filter-toolbar" && nodeHasDataTable(host)) {
    host.removeAttribute("data-layout");
    host.classList.remove("ro-filter-bar");
  }
  return bar;
}

function expandFilterToolbar(toolbar) {
  if (!toolbar) return toolbar;
  if (toolbar.matches?.(".relative") && toolbar.querySelectorAll("button, select").length < 2) {
    toolbar = toolbar.parentElement || toolbar;
  }
  if (nodeHasDataTable(toolbar)) return ensureDedicatedFilterBar(toolbar);
  const scope = toolbar.closest(".workspace-surface, section.shell-card, .app-canvas") || document.body;
  let best = toolbar;
  let node = toolbar;
  while (node && node !== scope) {
    const parent = node.parentElement;
    if (!parent || parent === scope) break;
    if (parent.querySelector("h1, h2") && !node.querySelector("h1, h2")) break;
    if (nodeHasDataTable(parent)) break;
    const height = node.getBoundingClientRect?.().height || 0;
    if (height > 160) break;
    const search = node.querySelector("input[placeholder*='Search'], input[placeholder*='Filter'], input[placeholder*='candidates']");
    const selects = Array.from(node.querySelectorAll("select")).filter(isWorkspaceFilterSelect);
    const tabs = node.querySelector("[data-toggle-group='true'], [role='tablist'], .flex.space-x-1");
    const filterButtons = Array.from(node.querySelectorAll("button")).filter((button) => {
      if (button.dataset.route || button.closest("table, [aria-haspopup='menu']")) return false;
      return Boolean(FILTER_BUTTON_KEYS[getActionLabel(button)]);
    });
    const score = Number(Boolean(search && !isTopbarSearchInput(search))) + Number(Boolean(tabs)) + Number(selects.length > 0 || filterButtons.length >= 2);
    if (score >= 2) best = node;
    node = parent;
  }
  return ensureDedicatedFilterBar(best);
}

function arrangeFilterToolbar(toolbar) {
  if (!toolbar) return toolbar;
  toolbar = ensureDedicatedFilterBar(toolbar);
  if (nodeHasDataTable(toolbar)) return toolbar;
  toolbar.classList.add("ro-filter-bar");
  if (toolbar.dataset.layout !== "pipeline-filter-bar" && toolbar.dataset.layout !== "report-filter-bar") {
    toolbar.dataset.layout = "filter-toolbar";
  }
  Array.from(toolbar.querySelectorAll("button")).forEach((button) => {
    if (isDecorativeFilterButton(button) && !button.closest("[data-toggle-group], [role='tablist']")) button.remove();
  });
  /* Decorative filter-icon buttons anywhere in the surface (outside tables and
     the real bar) leave an empty padded strip behind — remove them too. */
  const surfaceForIcons = toolbar.closest(".workspace-surface, section.shell-card") || document;
  Array.from(surfaceForIcons.querySelectorAll("button")).forEach((button) => {
    if (button.closest("table, .ro-filter-bar, [data-overlay-surface], .overlay-host, [data-toggle-group], [role='tablist']")) return;
    if (button.dataset.route || button.dataset.wired === "true") return;
    if (isDecorativeFilterButton(button)) button.remove();
  });
  const searchInput = typeof getToolbarSearchInput === "function"
    ? getToolbarSearchInput(toolbar)
    : toolbar.querySelector("input[placeholder*='Search'], input[placeholder*='Filter'], input[placeholder*='candidates']");
  const searchWrap = searchInput ? (searchInput.closest(".relative") || searchInput) : null;
  const tabGroup = toolbar.querySelector("[data-toggle-group='true'], [role='tablist']");
  const selects = Array.from(toolbar.querySelectorAll("select")).filter((select) => isWorkspaceFilterSelect(select) && !select.closest("table"));
  const dateInputs = Array.from(toolbar.querySelectorAll("input[type='date']"));
  let selectCluster = toolbar.querySelector(":scope > .ro-filter-selects");
  if (!selectCluster && (selects.length || dateInputs.length)) {
    selectCluster = document.createElement("div");
    selectCluster.className = "ro-filter-selects";
    selectCluster.setAttribute("data-layout", "filter-selects");
  }
  if (selectCluster) {
    [...selects, ...dateInputs].forEach((node) => {
      if (node.parentElement !== selectCluster) selectCluster.appendChild(node);
    });
  }
  const ordered = [tabGroup, searchWrap, selectCluster].filter(Boolean);
  ordered.forEach((node) => toolbar.appendChild(node));
  Array.from(toolbar.children).forEach((child) => {
    if (ordered.includes(child)) return;
    if (child.matches(".w-px, .h-6.w-px")) child.remove();
    else if (child.classList.contains("relative") && !child.querySelector("input, select, button")) child.remove();
    else if (isDecorativeFilterButton(child)) child.remove();
    else if (!child.querySelector("input, select, button, [data-toggle-group], [role='tablist']") && !child.matches("input, select, button, span, p, label") && !(child.textContent || "").trim()) {
      child.remove();
    }
  });
  toolbar.querySelectorAll(".relative").forEach((wrap) => {
    if (wrap === searchWrap) return;
    if (!wrap.querySelector("input, select, button")) wrap.remove();
  });
  /* Sibling cards left holding nothing but a small label chip (e.g. the
     "FILTERS" caption card) after their controls moved into the bar. */
  const surfaceForChips = toolbar.closest(".workspace-surface, section.shell-card") || toolbar.parentElement;
  if (surfaceForChips) {
    Array.from(surfaceForChips.children).forEach((sib) => {
      if (sib === toolbar || sib.contains(toolbar) || toolbar.contains(sib)) return;
      if (sib.querySelector("input, select, button, textarea, table, a[href], h1, h2, h3, h4, h5, h6, [data-toggle-group], [role='tablist'], img")) return;
      const text = (sib.textContent || "").trim();
      if (!text || text.length > 24) return;
      sib.remove();
    });
  }
  return placeFilterBarBeforeTable(toolbar);
}

function hydrateLiveFilters(scope = document) {
  const root = scope && scope !== document ? scope : document;
  /* Home is a categorized card grid, not a data table — the filter-toolbar
     machinery would restructure it and destroy the layout. */
  if (root === document && document.body?.dataset.routeId === "home") return;
  const surfaces = new Set();
  if (root.querySelectorAll) {
    root.querySelectorAll(".workspace-surface, [data-layout='table-surface'], section.shell-card").forEach((node) => surfaces.add(node));
  }
  if (root.classList?.contains("workspace-surface")) surfaces.add(root);
  if (!surfaces.size) surfaces.add(document);

  surfaces.forEach((surface) => {
    let toolbar = surface.querySelector?.("[data-layout='filter-toolbar']:not(:has(table)), [data-layout='pipeline-filter-bar'], [data-layout='report-filter-bar'], .ro-filter-bar") || findFilterToolbar(surface);
    if (!toolbar) {
      const search = Array.from(surface.querySelectorAll?.("input[placeholder*='Search'], input[placeholder*='Filter'], input[placeholder*='candidates']") || []).find((input) => !isTopbarSearchInput(input));
      if (search) toolbar = search.closest(".flex:not(.relative), [data-toggle-group], .bg-surface") || search.parentElement;
    }
    if (toolbar?.matches?.(".relative") && toolbar.querySelectorAll("button, select").length < 2) {
      toolbar = toolbar.parentElement;
    }
    if (!toolbar || toolbar.closest("[data-overlay-surface], .overlay-host")) return;
    toolbar = ensureDedicatedFilterBar(expandFilterToolbar(toolbar));
    toolbar = arrangeFilterToolbar(toolbar);
    if (nodeHasDataTable(toolbar)) return;
    if (toolbar.dataset.layout !== "pipeline-filter-bar" && toolbar.dataset.layout !== "report-filter-bar") {
      toolbar.dataset.layout = "filter-toolbar";
    }

    const table = getTableForFilterToolbar(toolbar) || surface.querySelector?.("table");
    Array.from(toolbar.querySelectorAll("button")).forEach((button) => {
      if (button.dataset.route || button.closest("[aria-haspopup='menu']") || isDecorativeFilterButton(button)) return;
      const label = getActionLabel(button);
      if (/^(unread|read|all\b|my reqs|all reqs|urgent|active|pending|deactivated)$/.test(label)) return;
      const key = FILTER_BUTTON_KEYS[label];
      if (!key) return;
      const select = replaceFilterButtonWithSelect(button, key);
      fillFilterSelect(select, key, table);
      bindLiveFilterControl(toolbar, select);
    });

    toolbar.querySelectorAll("select").forEach((select) => {
      if (!isWorkspaceFilterSelect(select) || select.closest("table")) return;
      const key = select.dataset.filterKey || inferFilterKeyFromLabel(select.options[0]?.textContent || select.getAttribute("aria-label") || "");
      fillFilterSelect(select, key, table);
      bindLiveFilterControl(toolbar, select);
    });

    const searchInput = getToolbarSearchInput(toolbar);
    if (searchInput) bindLiveFilterControl(toolbar, searchInput);
    bindFilterTabs(toolbar);
    arrangeFilterToolbar(toolbar);
  });
}

function getFilterableCards() {
  const pipeline = Array.from(document.querySelectorAll(".pipeline-card"));
  if (pipeline.length) return pipeline;
  return Array.from(document.querySelectorAll("article[data-notification-id], [data-live-notification-row]"));
}

function applyPipelineFilters({ searchTerm = "", activeSelects = [], tabChoice = "", notify = false, rawTerm = "" } = {}) {
  const cards = getFilterableCards();
  if (!cards.length) return null;
  let visibleCount = 0;
  cards.forEach((card) => {
      const text = normalizeFilterText(card.textContent || "");
      /* Display IDs like CND-1001 normalize to digit-less text, so
         digit-bearing terms match the card's raw text instead. */
      const rawText = String(card.textContent || "").toLowerCase();
      const rawTermLower = String(rawTerm || "").trim().toLowerCase();
      const termHasDigits = /\d/.test(rawTermLower);
      const matchesChoices = activeSelects.every((entry) => rowMatchesFilterChoice(card, entry.choice, entry.key));
      const matchesTab = !tabChoice || isAllFilterChoice(tabChoice) || rowMatchesFilterChoice(card, tabChoice);
      const matchesSearch = searchTerm.length < 2
        || (termHasDigits ? rawText.includes(rawTermLower) : text.includes(searchTerm));
      const visible = matchesChoices && matchesTab && matchesSearch;
    card.hidden = !visible;
    if (visible) visibleCount += 1;
  });
  document.querySelectorAll("[data-pipeline-stage]").forEach((col) => {
    const host = col.querySelector(".pipeline-drop-zone, [data-pipeline-drop-zone]");
    if (!host) return;
    const visibleCards = Array.from(host.querySelectorAll(".pipeline-card")).filter((card) => !card.hidden);
    const badge = col.querySelector("h3")?.parentElement?.querySelector("span");
    if (badge) badge.textContent = String(visibleCards.length);
    let empty = host.querySelector(".pipeline-empty-note");
    if (!visibleCards.length) {
      if (!empty) {
        empty = document.createElement("div");
        empty.className = "pipeline-empty-note";
        host.appendChild(empty);
      }
      empty.hidden = false;
      empty.textContent = searchTerm || activeSelects.length ? "No candidates match these filters." : "No candidates in this stage";
    } else if (empty) {
      empty.hidden = true;
    }
  });
  if (notify) showToast("View filtered", `${visibleCount} of ${cards.length} candidates match.`);
  return { visibleCount, totalCount: cards.length };
}

function resetWorkspaceFilters(source) {
  const surface = source?.closest(".workspace-surface, section, .app-canvas") || document.querySelector(".workspace-surface") || document;
  surface.querySelectorAll("[data-layout='filter-toolbar'] select, .workspace-surface select").forEach((select) => {
    if (select.closest("table, form, [data-overlay-surface], .overlay-host")) return;
    select.selectedIndex = 0;
  });
  surface.querySelectorAll("input[placeholder*='Search'], input[placeholder*='Filter'], input[placeholder*='candidates']").forEach((input) => {
    if (input.closest("form, [data-overlay-surface], .overlay-host") || input.id === "topbar-search") return;
    input.value = "";
  });
  const toolbar = findFilterToolbar(surface.querySelector("[data-layout='table-surface']") || surface);
  if (toolbar) {
    delete toolbar.dataset.filterTab;
    applyToolbarFilters(toolbar, { notify: false });
  } else {
    applyPipelineFilters({});
  }
  showToast("Filters cleared", "Showing all records in this view.");
}

