/* ═══════════════════════════════════════════════════════════════
   RoCharts — lightweight, dependency-free SVG chart renderers.
   No CDN, no build step: plain inline SVG + vanilla JS, consistent
   with the rest of shared/*.js. Charts are built from real data
   already loaded by api-client.js — this module only renders it.

   Palette: the validated default categorical palette (dataviz skill),
   reference instance — do not reorder slots. Status colors reuse the
   app's own semantic tokens (--ro-success/--ro-warning/--ro-danger)
   so chart status coloring matches every badge elsewhere in the app.
   ═══════════════════════════════════════════════════════════════ */
(function () {
  "use strict";

  const CATEGORICAL = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"];
  const STATUS = { good: "#217a46", warning: "#8a6a1f", critical: "#A1392C", neutral: "#726F66" };
  const INK = { primary: "#2B2823", secondary: "#4b5257", muted: "#898781", grid: "#e7e7e4", baseline: "#c9c9c5" };

  function esc(value) {
    return String(value == null ? "" : value).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }

  function fmt(value, format) {
    if (value == null) return "—";
    if (typeof format === "function") return format(value);
    if (format === "percent") return `${Math.round(value)}%`;
    if (format === "days") return `${value}d`;
    return Number(value).toLocaleString();
  }

  let tooltipEl = null;
  function tooltip() {
    if (tooltipEl && document.body.contains(tooltipEl)) return tooltipEl;
    tooltipEl = document.createElement("div");
    tooltipEl.className = "ro-chart-tooltip";
    tooltipEl.setAttribute("role", "status");
    document.body.appendChild(tooltipEl);
    return tooltipEl;
  }
  function showTooltip(evt, html) {
    const el = tooltip();
    el.innerHTML = html;
    el.style.display = "block";
    positionTooltip(evt);
  }
  function positionTooltip(evt) {
    const el = tooltip();
    const pad = 12;
    let x = evt.clientX + pad;
    let y = evt.clientY + pad;
    const rect = el.getBoundingClientRect();
    if (x + rect.width > window.innerWidth - 8) x = evt.clientX - rect.width - pad;
    if (y + rect.height > window.innerHeight - 8) y = evt.clientY - rect.height - pad;
    el.style.left = `${Math.max(8, x)}px`;
    el.style.top = `${Math.max(8, y)}px`;
  }
  function hideTooltip() {
    if (tooltipEl) tooltipEl.style.display = "none";
  }

  function srTable(container, headers, rows) {
    const table = document.createElement("table");
    table.className = "sr-only ro-chart-data-table";
    table.innerHTML = `<thead><tr>${headers.map((h) => `<th>${esc(h)}</th>`).join("")}</tr></thead>
      <tbody>${rows.map((r) => `<tr>${r.map((c) => `<td>${esc(c)}</td>`).join("")}</tr>`).join("")}</tbody>`;
    container.appendChild(table);
  }

  function emptyState(container, message) {
    container.innerHTML = `<div class="ro-chart-empty"><span class="material-symbols-outlined">bar_chart</span><p>${esc(message || "No data yet.")}</p></div>`;
  }

  /* ── Horizontal bar: one category per row, single series (magnitude by identity). ── */
  function bar(container, opts) {
    if (!container) return;
    const items = (opts.items || []).filter((i) => i && i.label != null);
    if (!items.length) return emptyState(container, opts.empty);
    const format = opts.format;
    const max = Math.max(...items.map((i) => Number(i.value) || 0), opts.min || 1);
    const rowH = 28;
    const gap = 10;
    const chartW = 100; /* percentage-based track, label/value sit outside the SVG track */
    const rows = items
      .map((item, i) => {
        const pct = Math.max(1.5, Math.round(((Number(item.value) || 0) / max) * 100));
        const color = item.color || CATEGORICAL[i % CATEGORICAL.length];
        return `<div class="ro-bar-row" data-index="${i}" tabindex="0" role="img" aria-label="${esc(item.label)}: ${esc(fmt(item.value, format))}">
          <span class="ro-bar-label" title="${esc(item.label)}">${esc(item.label)}</span>
          <span class="ro-bar-track"><span class="ro-bar-fill" style="width:${pct}%;background:${color}"></span></span>
          <span class="ro-bar-value">${esc(fmt(item.value, format))}</span>
        </div>`;
      })
      .join("");
    container.innerHTML = `<div class="ro-chart ro-chart-bar">${rows}</div>`;
    container.querySelectorAll(".ro-bar-row").forEach((row, i) => {
      const item = items[i];
      const show = (evt) => showTooltip(evt, `<strong>${esc(item.label)}</strong><br>${esc(fmt(item.value, format))}`);
      row.addEventListener("mousemove", show);
      row.addEventListener("mouseenter", show);
      row.addEventListener("mouseleave", hideTooltip);
      row.addEventListener("focus", (evt) => show({ clientX: row.getBoundingClientRect().right, clientY: row.getBoundingClientRect().top }));
      row.addEventListener("blur", hideTooltip);
    });
    srTable(container, [opts.labelHeader || "Category", opts.valueHeader || "Value"], items.map((i) => [i.label, fmt(i.value, format)]));
  }

  /* ── Grouped vertical bars: up to 3 categorical series per category. ── */
  function groupedBar(container, opts) {
    if (!container) return;
    const categories = opts.categories || [];
    const series = (opts.series || []).slice(0, 3);
    if (!categories.length || !series.length) return emptyState(container, opts.empty);
    const format = opts.format;
    const max = Math.max(1, ...series.flatMap((s) => s.values));
    const W = 640, H = 220, padL = 36, padB = 28, padT = 10, padR = 8;
    const plotW = W - padL - padR, plotH = H - padT - padB;
    const groupW = plotW / categories.length;
    const barGap = 4;
    const barW = Math.max(6, (groupW - 16) / series.length - barGap);
    const yTicks = 4;
    const gridLines = Array.from({ length: yTicks + 1 }, (_, i) => {
      const y = padT + (plotH / yTicks) * i;
      const val = Math.round(max - (max / yTicks) * i);
      return `<line x1="${padL}" x2="${W - padR}" y1="${y}" y2="${y}" stroke="${INK.grid}" stroke-width="1" />
        <text x="${padL - 6}" y="${y + 3}" text-anchor="end" font-size="10" fill="${INK.muted}">${fmt(val, format)}</text>`;
    }).join("");
    let bars = "";
    categories.forEach((cat, ci) => {
      const groupX = padL + ci * groupW + (groupW - series.length * (barW + barGap)) / 2;
      series.forEach((s, si) => {
        const v = Number(s.values[ci]) || 0;
        const h = Math.max(1, (v / max) * plotH);
        const x = groupX + si * (barW + barGap);
        const y = padT + plotH - h;
        const color = s.color || CATEGORICAL[si % CATEGORICAL.length];
        bars += `<rect class="ro-chart-bar-rect" data-cat="${ci}" data-series="${si}" x="${x}" y="${y}" width="${barW}" height="${h}" rx="2" fill="${color}" />`;
      });
      bars += `<text x="${groupX + (series.length * (barW + barGap)) / 2 - barGap / 2}" y="${H - 6}" text-anchor="middle" font-size="10" fill="${INK.secondary}">${esc(cat)}</text>`;
    });
    const legend = series
      .map((s, i) => `<span class="ro-chart-legend-item"><span class="ro-chart-swatch" style="background:${s.color || CATEGORICAL[i % CATEGORICAL.length]}"></span>${esc(s.name)}</span>`)
      .join("");
    container.innerHTML = `<div class="ro-chart ro-chart-grouped-bar">
        <svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(opts.ariaLabel || "Grouped bar chart")}">${gridLines}<g>${bars}</g></svg>
        ${series.length > 1 ? `<div class="ro-chart-legend">${legend}</div>` : ""}
      </div>`;
    container.querySelectorAll(".ro-chart-bar-rect").forEach((rect) => {
      const ci = Number(rect.dataset.cat), si = Number(rect.dataset.series);
      const s = series[si];
      const show = (evt) => showTooltip(evt, `<strong>${esc(categories[ci])}</strong><br>${esc(s.name)}: ${esc(fmt(s.values[ci], format))}`);
      rect.addEventListener("mousemove", show);
      rect.addEventListener("mouseenter", show);
      rect.addEventListener("mouseleave", hideTooltip);
    });
    const rows = categories.map((cat, ci) => [cat, ...series.map((s) => fmt(s.values[ci], format))]);
    srTable(container, [opts.labelHeader || "Category", ...series.map((s) => s.name)], rows);
  }

  /* ── Donut: composition of a whole, status or categorical coloring. ── */
  function donut(container, opts) {
    if (!container) return;
    const segments = (opts.segments || []).filter((s) => s && Number(s.value) > 0);
    const total = segments.reduce((sum, s) => sum + Number(s.value), 0);
    if (!segments.length || !total) return emptyState(container, opts.empty);
    const format = opts.format;
    const size = 160, stroke = 24, r = (size - stroke) / 2, cx = size / 2, cy = size / 2;
    const circumference = 2 * Math.PI * r;
    let offset = 0;
    const gapDeg = segments.length > 1 ? 2 : 0; /* 2px-equivalent surface gap between segments */
    const arcs = segments
      .map((s, i) => {
        const color = s.color || CATEGORICAL[i % CATEGORICAL.length];
        const frac = Number(s.value) / total;
        const len = Math.max(0, frac * circumference - gapDeg);
        const dash = `${len} ${circumference - len}`;
        const rotation = (offset / circumference) * 360 - 90;
        offset += frac * circumference;
        return `<circle data-index="${i}" cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="${color}" stroke-width="${stroke}"
          stroke-dasharray="${dash}" transform="rotate(${rotation} ${cx} ${cy})" stroke-linecap="butt" />`;
      })
      .join("");
    const legend = segments
      .map((s, i) => `<span class="ro-chart-legend-item"><span class="ro-chart-swatch" style="background:${s.color || CATEGORICAL[i % CATEGORICAL.length]}"></span>${esc(s.label)} <strong>${esc(fmt(s.value, format))}</strong></span>`)
      .join("");
    container.innerHTML = `<div class="ro-chart ro-chart-donut">
        <svg viewBox="0 0 ${size} ${size}" width="${size}" height="${size}" role="img" aria-label="${esc(opts.ariaLabel || "Composition chart")}">
          ${arcs}
          <text x="${cx}" y="${cy - 3}" text-anchor="middle" font-size="22" font-weight="700" fill="${INK.primary}">${esc(opts.centerValue != null ? opts.centerValue : total)}</text>
          <text x="${cx}" y="${cy + 16}" text-anchor="middle" font-size="10" fill="${INK.muted}">${esc(opts.centerLabel || "Total")}</text>
        </svg>
        <div class="ro-chart-legend ro-chart-legend-stack">${legend}</div>
      </div>`;
    container.querySelectorAll("circle[data-index]").forEach((circle) => {
      const s = segments[Number(circle.dataset.index)];
      const show = (evt) => showTooltip(evt, `<strong>${esc(s.label)}</strong><br>${esc(fmt(s.value, format))} (${Math.round((Number(s.value) / total) * 100)}%)`);
      circle.addEventListener("mousemove", show);
      circle.addEventListener("mouseenter", show);
      circle.addEventListener("mouseleave", hideTooltip);
    });
    srTable(container, [opts.labelHeader || "Category", opts.valueHeader || "Value"], segments.map((s) => [s.label, fmt(s.value, format)]));
  }

  /* ── Line / trend: up to 4 series over labeled steps (time-ordered). ── */
  function line(container, opts) {
    if (!container) return;
    const labels = opts.labels || [];
    const series = (opts.series || []).slice(0, 4);
    if (!labels.length || !series.length) return emptyState(container, opts.empty);
    const format = opts.format;
    const max = Math.max(1, ...series.flatMap((s) => s.values));
    const W = 640, H = 220, padL = 36, padB = 24, padT = 10, padR = 8;
    const plotW = W - padL - padR, plotH = H - padT - padB;
    const stepX = labels.length > 1 ? plotW / (labels.length - 1) : 0;
    const yTicks = 4;
    const gridLines = Array.from({ length: yTicks + 1 }, (_, i) => {
      const y = padT + (plotH / yTicks) * i;
      const val = Math.round(max - (max / yTicks) * i);
      return `<line x1="${padL}" x2="${W - padR}" y1="${y}" y2="${y}" stroke="${INK.grid}" stroke-width="1" />
        <text x="${padL - 6}" y="${y + 3}" text-anchor="end" font-size="10" fill="${INK.muted}">${fmt(val, format)}</text>`;
    }).join("");
    const xLabels = labels
      .map((lbl, i) => `<text x="${padL + i * stepX}" y="${H - 6}" text-anchor="middle" font-size="10" fill="${INK.secondary}">${esc(lbl)}</text>`)
      .join("");
    let paths = "";
    let dots = "";
    series.forEach((s, si) => {
      const color = s.color || CATEGORICAL[si % CATEGORICAL.length];
      const points = s.values.map((v, i) => {
        const x = padL + i * stepX;
        const y = padT + plotH - (Math.max(0, Number(v) || 0) / max) * plotH;
        return [x, y];
      });
      const d = points.map((p, i) => `${i === 0 ? "M" : "L"}${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(" ");
      paths += `<path d="${d}" fill="none" stroke="${color}" stroke-width="2" stroke-linejoin="round" />`;
      dots += points
        .map((p, i) => `<circle data-series="${si}" data-step="${i}" cx="${p[0].toFixed(1)}" cy="${p[1].toFixed(1)}" r="3" fill="${color}" stroke="#fff" stroke-width="1.5" />`)
        .join("");
    });
    const legend = series.length > 1
      ? `<div class="ro-chart-legend">${series.map((s, i) => `<span class="ro-chart-legend-item"><span class="ro-chart-swatch" style="background:${s.color || CATEGORICAL[i % CATEGORICAL.length]}"></span>${esc(s.name)}</span>`).join("")}</div>`
      : "";
    container.innerHTML = `<div class="ro-chart ro-chart-line">
        <svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(opts.ariaLabel || "Trend chart")}">${gridLines}${xLabels}${paths}${dots}</svg>
        ${legend}
      </div>`;
    container.querySelectorAll("circle[data-series]").forEach((dot) => {
      const si = Number(dot.dataset.series), step = Number(dot.dataset.step);
      const s = series[si];
      const show = (evt) => showTooltip(evt, `<strong>${esc(labels[step])}</strong><br>${esc(s.name)}: ${esc(fmt(s.values[step], format))}`);
      dot.addEventListener("mousemove", show);
      dot.addEventListener("mouseenter", show);
      dot.addEventListener("mouseleave", hideTooltip);
    });
    const rows = labels.map((lbl, i) => [lbl, ...series.map((s) => fmt(s.values[i], format))]);
    srTable(container, [opts.labelHeader || "Period", ...series.map((s) => s.name)], rows);
  }

  /* ── Sparkline: tiny inline trend for a KPI tile, no axes/legend. ── */
  function sparkline(container, values, color) {
    if (!container) return;
    const vals = (values || []).map((v) => Number(v) || 0);
    if (vals.length < 2) {
      container.innerHTML = "";
      return;
    }
    const max = Math.max(...vals, 1);
    const min = Math.min(...vals, 0);
    const span = max - min || 1;
    const W = 96, H = 28;
    const stepX = W / (vals.length - 1);
    const points = vals.map((v, i) => [i * stepX, H - ((v - min) / span) * H]);
    const d = points.map((p, i) => `${i === 0 ? "M" : "L"}${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(" ");
    container.innerHTML = `<svg viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" class="ro-sparkline" aria-hidden="true">
      <path d="${d}" fill="none" stroke="${color || CATEGORICAL[0]}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
    </svg>`;
  }

  window.RoCharts = { bar, groupedBar, donut, line, sparkline, CATEGORICAL, STATUS };
  document.addEventListener("scroll", hideTooltip, true);
})();
