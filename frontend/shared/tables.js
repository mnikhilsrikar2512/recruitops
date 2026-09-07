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
    .replace(/\\([^)]*\\)/g, "")
    .replace(/\\d+\\s*records?.*$/i, "")
    .replace(/\\s+/g, " ")
    .trim()
    .toLowerCase();
}


function rowMatchesLens(rowText, lens) {
  const text = rowText.toLowerCase();
  if (!lens || /^(all|all reqs|all users|all clients|pending)$/.test(lens) && !/pending invite/.test(lens)) {
    return true;
  }
  if (/my reqs|assigned to me|my work/.test(lens)) {
    return /sarah j\\.?|sarah jenkins|assigned to me|owner: me/.test(text);
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
    const text = (row.textContent || "").replace(/\\s+/g, " ").trim();
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
      <p class="m-0 text-[12px] text-text-muted">Bulk actions are staged here so workflow intent is visible before API wiring.</p>
    </div>
    <div class="bulk-selection-actions">
      <button type="button" data-toast-title="Bulk review queued" data-toast="The selected records are ready to be reviewed together.">Review selected</button>
      <button type="button" data-toast-title="Bulk export queued" data-toast="The selected records are staged for export once backend actions are connected.">Export selection</button>
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
  const summary = (summaryNode?.textContent || "").replace(/\\s+/g, " ").trim();
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
        <strong data-search-status-title>Search preview ready</strong>
        <span class="table-search-status-chip" data-search-status-chip>Preview</span>
      </div>
      <p data-search-status-copy>Refine the current term or clear it before wiring this state to live data.</p>
      <p class="table-search-status-meta" data-search-status-meta>Search and filter states will stay layout-stable during API integration.</p>
    </div>
    <button type="button" data-clear-search-preview="true">Clear preview</button>
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
    (row) => row.dataset.generatedEmptyState !== "true" && !row.classList.contains("demo-empty-row"),
  );
}


function normalizeFilterText(value) {
  return (value || "")
    .replace(/\\([^)]*\\)/g, "")
    .replace(/\\b\\d+\\b/g, "")
    .replace(/\\s+/g, " ")
    .trim()
    .toLowerCase();
}


function extractFilterChoice(select) {
  if (!select || select.selectedIndex === 0) return "";
  const raw = select?.options?.[select.selectedIndex]?.textContent || "";
  return normalizeFilterText(raw.split(":").pop() || raw);
}


function isAllFilterChoice(choice) {
  return !choice || /^all\b|^show all\b|any|select|choose/.test(choice);
}


function rowMatchesFilterChoice(rowText, choice) {
  if (isAllFilterChoice(choice)) return true;
  if (rowText.includes(choice)) return true;
  if (/active|open/.test(choice)) return /active|open|sourcing|screen|interview|offer out|profile complete/.test(rowText) && !/inactive|closed|deactivated/.test(rowText);
  if (/pending/.test(choice)) return /pending|invite|review needed|action required|intake/.test(rowText);
  if (/urgent|high|critical|p1/.test(choice)) return /urgent|high|critical|p1|overdue/.test(rowText);
  if (/low|p3/.test(choice)) return /low|p3/.test(rowText);
  if (/medium|p2/.test(choice)) return /medium|p2/.test(rowText);
  if (/engineering/.test(choice)) return /engineer|engineering|frontend|backend|devops/.test(rowText);
  if (/product/.test(choice)) return /product/.test(rowText);
  if (/design/.test(choice)) return /design|ux/.test(rowText);
  if (/remote/.test(choice)) return /remote/.test(rowText);
  return false;
}


function updateTableEmptyState(table, visibleCount, label) {
  const tbody = table?.querySelector("tbody");
  if (!tbody) return;
  let emptyRow = tbody.querySelector("[data-generated-empty-state='true']");
  if (!emptyRow) {
    emptyRow = document.createElement("tr");
    emptyRow.className = "table-empty-state-row";
    emptyRow.dataset.generatedEmptyState = "true";
    emptyRow.innerHTML = renderTableEmptyCell({
      icon: "filter_list_off",
      title: "No records match this view",
      hint: label || "Adjust the filter or search term to widen the result set.",
      hintClass: "",
      columnCount: getTableColumnCount(table),
    });
    tbody.appendChild(emptyRow);
  }
  const hintNode = emptyRow.querySelector("p");
  if (hintNode && label) {
    hintNode.textContent = label;
  }
  emptyRow.hidden = visibleCount > 0;
}


function syncTableRowVisibility(table) {
  getFilterableRows(table).forEach((row) => {
    row.hidden = row.dataset.hiddenBySearch === "true" || row.dataset.hiddenByFilter === "true";
  });
}


function getTableForFilterToolbar(toolbar) {
  const tableSurface = toolbar?.closest("[data-layout='table-surface']");
  if (tableSurface?.querySelector("table")) return tableSurface.querySelector("table");
  const surface = toolbar?.closest("[data-demo-validate], .workspace-surface");
  return surface?.querySelector("table") || document.querySelector("table");
}


function applyToolbarFilters(toolbar, { notify = true } = {}) {
  const table = getTableForFilterToolbar(toolbar);
  if (!table) return null;
  const rows = getFilterableRows(table);
  if (!rows.length) return null;
  const selects = Array.from(toolbar.querySelectorAll("select"));
  const searchInput = toolbar.querySelector("input[placeholder*='Search']");
  const searchTerm = normalizeFilterText(searchInput?.value || "");
  const activeChoices = selects.map(extractFilterChoice).filter((choice) => !isAllFilterChoice(choice));
  let visibleCount = 0;

  rows.forEach((row) => {
    const text = normalizeFilterText(row.textContent || "");
    const matchesChoices = activeChoices.every((choice) => rowMatchesFilterChoice(text, choice));
    const matchesSearch = searchTerm.length < 2 || text.includes(searchTerm);
    const visible = matchesChoices && matchesSearch;
    row.dataset.hiddenByFilter = visible ? "false" : "true";
    if (visible) visibleCount += 1;
  });
  syncTableRowVisibility(table);
  updateTableEmptyState(
    table,
    visibleCount,
    searchTerm.length >= 2
      ? `No records matched "${searchInput.value.trim()}". Clear the search or adjust filters.`
      : "No records match the selected filters. Choose a broader filter to restore results.",
  );
  if (notify) {
    const label = activeChoices.length ? activeChoices.join(" + ") : searchTerm.length >= 2 ? searchInput.value.trim() : "All records";
    showToast("View filtered", `${visibleCount} of ${rows.length} records match ${label}.`);
  }
  return { visibleCount, totalCount: rows.length };
}

function describeToolbarFilters(toolbar) {
  const selects = Array.from(toolbar?.querySelectorAll("select") || [])
    .map((select) => select.options[select.selectedIndex]?.textContent?.trim())
    .filter((label) => label && !isAllFilterChoice(normalizeFilterText(label.split(":").pop() || label)));
  const search = toolbar?.querySelector("input[placeholder*='Search']")?.value?.trim();
  if (search && search.length >= 2) selects.push(`Search: ${search}`);
  return selects.length ? selects.join(" · ") : "No filters active";
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
      <span data-advanced-filter-copy>Optional filters are staged here for API-backed expansion.</span>
      <button type="button" data-reset-toolbar-filters="true">Reset filters</button>
    `;
    toolbar.insertAdjacentElement("afterend", panel);
    trigger.setAttribute("aria-expanded", "false");
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
      showToast(visible ? "Advanced filters opened" : "Advanced filters hidden", "This area is ready for richer API-backed filtering.");
    });

    panel.querySelector("[data-reset-toolbar-filters]")?.addEventListener("click", () => {
      toolbar.querySelectorAll("select").forEach((select) => {
        select.selectedIndex = 0;
      });
      toolbar.querySelectorAll("input[placeholder*='Search']").forEach((input) => {
        input.value = "";
      });
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
  if (!table) return { title: "Search captured", body: `Ready to wire '${term}' into API-backed search.` };
  clearTableSearchPreview(table);

  const normalized = term.trim();
  const status = ensureTableSearchStatus(table);
  const titleNode = status?.querySelector("[data-search-status-title]");
  const copyNode = status?.querySelector("[data-search-status-copy]");
  const metaNode = status?.querySelector("[data-search-status-meta]");
  const chipNode = status?.querySelector("[data-search-status-chip]");
  const noResults = /^(?:zzz|none|empty|nomatch|no ?match|404)$/i.test(normalized);
  const visibleCount = getVisibleTableRowCount(table);
  const requestId = `${Date.now()}-${Math.random().toString(16).slice(2, 8)}`;

  table.dataset.previewTerm = normalized;
  table.dataset.previewState = "loading";
  table.dataset.previewRequestId = requestId;
  if (status && titleNode && copyNode) {
    status.dataset.searchState = "loading";
    titleNode.textContent = `Searching for "${normalized}"`;
    copyNode.textContent = "Simulating the loading state now so API-backed search can slot in without a UI rewrite.";
    if (metaNode) {
      metaNode.textContent = `${visibleCount || "No"} current records will reconcile into the next result state.`;
    }
    if (chipNode) {
      chipNode.textContent = "Loading";
    }
    status.classList.add("is-visible");
  }

  const finalizePreview = () => {
    if (table.dataset.previewRequestId !== requestId) return;
    delete table.dataset.previewTimerId;
    table.dataset.previewState = noResults ? "empty" : "results";

    if (noResults) {
      const body = table.querySelector("tbody");
      const columnCount = getTableColumnCount(table);
      Array.from(body?.querySelectorAll("tr") || []).forEach((row) => {
        row.hidden = true;
        row.dataset.hiddenBySearch = "true";
      });
      const emptyRow = document.createElement("tr");
      emptyRow.className = "table-empty-state-row";
      emptyRow.dataset.generatedEmptyState = "true";
      emptyRow.innerHTML = renderTableEmptyCell({
        icon: "search_off",
        title: `No matching records for \"${normalized}\"`,
        hint: "Clear the search or try a broader term.",
        hintClass: "",
        columnCount,
      });
      body?.appendChild(emptyRow);
      if (status && titleNode && copyNode) {
        status.dataset.searchState = "empty";
        titleNode.textContent = `No records matched "${normalized}"`;
        copyNode.textContent = "The empty state is intentional and can now be reused for live search and filter responses.";
        if (metaNode) {
          metaNode.textContent = "0 records returned in this staged response.";
        }
        if (chipNode) {
          chipNode.textContent = "Empty";
        }
        status.classList.add("is-visible");
      }
      return;
    }

    if (status && titleNode && copyNode) {
      status.dataset.searchState = "results";
      titleNode.textContent = `Previewing search for "${normalized}"`;
      copyNode.textContent = "The existing records stay visible while this query is staged for live search wiring.";
      if (metaNode) {
        metaNode.textContent = `${visibleCount} records remain visible while result wiring is still mocked.`;
      }
      if (chipNode) {
        chipNode.textContent = "Results";
      }
      status.classList.add("is-visible");
    }
  };

  table.dataset.previewTimerId = String(window.setTimeout(finalizePreview, 180));
  return {
    title: "Search captured",
    body: `Ready to wire '${normalized}' into API-backed search.`,
  };
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
  const raw = (cell?.textContent || "").replace(/\\s+/g, " ").trim();
  const number = raw.match(/-?\\d+(?:\\.\\d+)?/);
  if (number && /^(?:\\$|₹|€|£)?\\s*-?\\d|^\\d+\\s*(?:d|days?|hrs?|hours?|%)?\\b/i.test(raw)) {
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
      const label = (header.textContent || "").replace(/\\s+/g, " ").trim();
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
      const actionCell = [...cells].reverse().find((cell) => cell.querySelector("button, a"));
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
    const filterToolbar = surface.querySelector("[data-layout='filter-toolbar'], :scope > div:first-of-type");
    const pageSummary = footer?.querySelector("span, .font-body-sm, .text-body-sm");
    const paginationButtons = Array.from(footer?.querySelectorAll("button") || []);
    const numericButtons = paginationButtons.filter((button) => /^\\d+$/.test((button.textContent || "").trim()));
    const paginationHost = paginationButtons[0]?.parentElement;
    if (footer && paginationButtons.length > 0) {
      footer.dataset.layout = "table-footer";
    }
    if (paginationHost && paginationHost !== footer) {
      paginationHost.dataset.layout = "pagination-controls";
    }

    filterToolbar?.querySelectorAll("button").forEach((button) => {
      const label = getActionLabel(button);
      if (button.dataset.toast || button.dataset.route) return;
      if (/more filters/.test(label)) {
        button.dataset.toastTitle = "Advanced filters staged";
        button.dataset.toast = "These filters are ready for richer API-backed table slicing without changing the workspace layout.";
        return;
      }
      if (/^role$|^location$|^region$|^type$|^client$|^status$|^priority$/.test(label)) {
        button.dataset.toastTitle = "Filter staged";
        button.dataset.toast = `${label.replace(/^./, (char) => char.toUpperCase())} filtering is ready for live table queries.`;
      }
    });

    filterToolbar?.querySelectorAll("select").forEach((select) => {
      if (select.dataset.filterPolished === "true") return;
      select.dataset.filterPolished = "true";
      select.addEventListener("change", () => {
        const choice = select.options[select.selectedIndex]?.textContent?.trim() || "Current filter";
        const result = applyToolbarFilters(filterToolbar, { notify: false });
        const suffix = result ? ` Showing ${result.visibleCount} of ${result.totalCount} records.` : "";
        showToast("Filter applied", `${choice} is now filtering this workspace.${suffix}`);
      });
    });

    filterToolbar?.querySelectorAll("input[placeholder*='Search']").forEach((input) => {
      if (input.dataset.liveFilterBound === "true") return;
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

    numericButtons.forEach((button, index) => {
      if (button.dataset.paginationBound === "true") return;
      button.dataset.paginationBound = "true";
      if (!button.getAttribute("type")) button.setAttribute("type", "button");
      setPaginationButtonActive(button, index === 0);
      button.addEventListener("click", (event) => {
        event.preventDefault();
        numericButtons.forEach((item) => setPaginationButtonActive(item, item === button));
        const pageNumber = (button.textContent || "").trim();
        if (pageSummary && /page\\s+\\d+/i.test(pageSummary.textContent || "")) {
          pageSummary.textContent = (pageSummary.textContent || "").replace(/Page\\s+\\d+/i, `Page ${pageNumber}`);
        }
        showToast("Page preview staged", `Page ${pageNumber} is ready for API-backed pagination.`);
      });
    });

    paginationButtons
      .filter((button) => !numericButtons.includes(button))
      .forEach((button) => {
        if (button.dataset.paginationBound === "true") return;
        button.dataset.paginationBound = "true";
        if (!button.getAttribute("type")) button.setAttribute("type", "button");
        button.addEventListener("click", (event) => {
          if (button.disabled) return;
          event.preventDefault();
          const label = getActionLabel(button) || button.getAttribute("title") || "Next page";
          showToast("Pagination staged", `${label.replace(/^./, (char) => char.toUpperCase())} is ready for live page navigation.`);
        });
      });
  });

  document.querySelectorAll("[data-layout='filter-toolbar']").forEach((filterToolbar) => {
    filterToolbar.querySelectorAll("button").forEach((button) => {
      const label = getActionLabel(button);
      if (button.dataset.toast || button.dataset.route) return;
      if (/more filters/.test(label)) {
        button.dataset.toastTitle = "Advanced filters staged";
        button.dataset.toast = "These filters are ready for richer API-backed table slicing without changing the workspace layout.";
        return;
      }
      if (/^role$|^location$|^region$|^type$|^client$|^status$|^priority$/.test(label)) {
        button.dataset.toastTitle = "Filter staged";
        button.dataset.toast = `${label.replace(/^./, (char) => char.toUpperCase())} filtering is ready for live table queries.`;
      }
    });

    filterToolbar.querySelectorAll("select").forEach((select) => {
      if (select.dataset.filterPolished === "true") return;
      select.dataset.filterPolished = "true";
      select.addEventListener("change", () => {
        const choice = select.options[select.selectedIndex]?.textContent?.trim() || "Current filter";
        const result = applyToolbarFilters(filterToolbar, { notify: false });
        const suffix = result ? ` Showing ${result.visibleCount} of ${result.totalCount} records.` : "";
        showToast("Filter applied", `${choice} is now filtering this workspace.${suffix}`);
      });
    });

    filterToolbar.querySelectorAll("input[placeholder*='Search']").forEach((input) => {
      if (input.dataset.liveFilterBound === "true") return;
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
  });
}


