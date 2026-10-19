/* ═══════════════════════════════════════════════════════════════
   RoExport — shared download helpers for report pages.

   PDF: the browser's own print pipeline (window.print → Save as PDF).
   Every chart in shared/charts.js is inline SVG, so it prints as
   crisp vector art identical to the on-screen chart — no rasterizing,
   no third-party PDF library, no network dependency. Pages opt in by
   tagging the printable region with [data-report-print] and adding
   shared/report-print.css.

   Excel: a self-contained SpreadsheetML 2003 XML document (the
   single-file XML flavor Excel/Sheets/LibreOffice all open as a real
   workbook — bold headers, column widths, number formats, frozen
   header row) rather than a bare CSV. No bundler, no zip writer, no
   network — just well-formed XML, written by hand once, here.
   ═══════════════════════════════════════════════════════════════ */
(function () {
  "use strict";

  function esc(value) {
    return String(value == null ? "" : value).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }

  function cellXml(value, numeric) {
    if (value == null || value === "") return `<Cell><Data ss:Type="String"></Data></Cell>`;
    if (numeric && typeof value === "number" && Number.isFinite(value)) {
      return `<Cell><Data ss:Type="Number">${value}</Data></Cell>`;
    }
    return `<Cell><Data ss:Type="String">${esc(value)}</Data></Cell>`;
  }

  /**
   * Download a real, formatted Excel workbook.
   * @param {string} filename  without extension
   * @param {{title?:string, sheetName?:string, columns:{key:string,label:string,numeric?:boolean,width?:number}[], rows:object[], subtitle?:string}} spec
   */
  function downloadExcel(filename, spec) {
    const columns = spec.columns || [];
    const rows = spec.rows || [];
    const sheetName = (spec.sheetName || "Report").slice(0, 31);
    const colWidths = columns.map((c) => `<Column ss:Width="${c.width || 120}" />`).join("");
    const titleRow = spec.title
      ? `<Row><Cell ss:MergeAcross="${Math.max(0, columns.length - 1)}" ss:StyleID="title"><Data ss:Type="String">${esc(spec.title)}</Data></Cell></Row>
         ${spec.subtitle ? `<Row><Cell ss:MergeAcross="${Math.max(0, columns.length - 1)}" ss:StyleID="subtitle"><Data ss:Type="String">${esc(spec.subtitle)}</Data></Cell></Row><Row></Row>` : "<Row></Row>"}`
      : "";
    const headerRow = `<Row ss:StyleID="header">${columns.map((c) => `<Cell><Data ss:Type="String">${esc(c.label)}</Data></Cell>`).join("")}</Row>`;
    const bodyRows = rows
      .map((row, i) => `<Row ss:StyleID="${i % 2 === 0 ? "rowEven" : "rowOdd"}">${columns.map((c) => cellXml(row[c.key], c.numeric)).join("")}</Row>`)
      .join("");
    const xml = `<?xml version="1.0"?>
<?mso-application progid="Excel.Sheet"?>
<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet"
 xmlns:o="urn:schemas-microsoft-com:office:office"
 xmlns:x="urn:schemas-microsoft-com:office:excel"
 xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet">
 <Styles>
  <Style ss:ID="title"><Font ss:Size="14" ss:Bold="1" ss:Color="#2B2823"/></Style>
  <Style ss:ID="subtitle"><Font ss:Size="10" ss:Color="#726F66"/></Style>
  <Style ss:ID="header"><Font ss:Bold="1" ss:Color="#FFFFFF"/><Interior ss:Color="#3F5D43" ss:Pattern="Solid"/><Alignment ss:Vertical="Center"/></Style>
  <Style ss:ID="rowEven"><Interior ss:Color="#FFFFFF" ss:Pattern="Solid"/></Style>
  <Style ss:ID="rowOdd"><Interior ss:Color="#FAFAF9" ss:Pattern="Solid"/></Style>
 </Styles>
 <Worksheet ss:Name="${esc(sheetName)}">
  <Table>${colWidths}
   ${titleRow}
   ${headerRow}
   ${bodyRows}
  </Table>
  <WorksheetOptions xmlns="urn:schemas-microsoft-com:office:excel">
   <FreezePanes/><FrozenNoSplit/><SplitHorizontal>${spec.title ? 3 : 1}</SplitHorizontal><TopRowBottomPane>${spec.title ? 3 : 1}</TopRowBottomPane>
  </WorksheetOptions>
 </Worksheet>
</Workbook>`;
    const blob = new Blob([xml], { type: "application/vnd.ms-excel" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${filename}.xls`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
    if (typeof showToast === "function") showToast("Excel workbook downloaded", `${rows.length} row${rows.length === 1 ? "" : "s"} exported`);
  }

  /**
   * Trigger the browser's print pipeline over a page's printable region.
   * Charts (inline SVG) and tables print as vector/text, not a screenshot.
   * Pages that don't already have their own letterhead (report-viewer does)
   * get a lightweight printed header with the report name and the date.
   */
  function downloadPdf(opts) {
    opts = opts || {};
    if (opts.beforePrint) opts.beforePrint();
    let header = document.querySelector(".ro-print-header");
    if (!header && (opts.title || opts.docTitle)) {
      header = document.createElement("div");
      header.className = "ro-print-header";
      const main = document.querySelector("main.app-canvas") || document.body;
      main.insertBefore(header, main.firstChild);
    }
    if (header && (opts.title || opts.docTitle)) {
      const now = new Date().toLocaleDateString(undefined, { year: "numeric", month: "long", day: "numeric" });
      header.innerHTML = `<p class="ro-print-header-title">${esc(opts.title || opts.docTitle)}</p>
        <p class="ro-print-header-meta">${esc(opts.subtitle || "")}${opts.subtitle ? " · " : ""}Generated ${esc(now)}</p>`;
      header.classList.add("is-active");
    }
    const prevTitle = document.title;
    if (opts.docTitle) document.title = opts.docTitle;
    const cleanup = () => {
      if (header) header.classList.remove("is-active");
      document.title = prevTitle;
      window.removeEventListener("afterprint", cleanup);
    };
    window.addEventListener("afterprint", cleanup);
    window.print();
  }

  window.RoExport = { downloadExcel, downloadPdf };
})();
