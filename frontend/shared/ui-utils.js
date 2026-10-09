/* ═══════════════════════════════════════════════════════════════
   UI UTILITIES — Shared across all modules
   ═══════════════════════════════════════════════════════════════ */

const NAV_GROUP_KEY = "recruitops-nav-groups";
const FOCUSABLE_SELECTOR = 'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';
const OVERLAY_ROUTE_FILES = new Set([
  "approval-review-drawer.html",
  "application-detail-drawer.html",
  "candidate-review-drawer.html",
  "contact-form-dialog.html",
  "daily-update-detail-panel.html",
  "deactivate-user-dialog.html",
  "assignment-history-drawer.html",
  "clarification-request-dialog.html",
  "duplicate-warning-modal.html",
  "exception-request-dialog.html",
  "link-to-requisition-dialog.html",
  "notification-detail-panel.html",
  "pipeline-history-drawer.html",
  "reassign-owner-dialog.html",
  "stage-move-dialog.html",
  "status-update-dialog.html",
  "interview-feedback-dialog.html",
  "offer-create-dialog.html",
  "meeting-form-dialog.html",
  "follow-up-form-dialog.html",
  "dashboard-actions-overlay.html",
]);

function dismissToast(toast) {
  if (!toast) return;
  toast.style.opacity = "0";
  toast.style.transform = "translateY(8px)";
  window.setTimeout(() => toast.remove(), 220);
}

function showToast(title, text = "") {
  const root = document.getElementById("toast-root");
  if (!root) return;
  root.setAttribute("aria-live", "polite");
  root.setAttribute("aria-atomic", "false");
  const toast = document.createElement("div");
  toast.className = "toast";
  toast.setAttribute("role", "status");
  toast.innerHTML = `
    <div class="toast-body">
      <div>
        <strong>${title}</strong>
        ${text ? `<p>${text}</p>` : ""}
      </div>
      <button type="button" class="toast-dismiss" aria-label="Dismiss message">
        <span class="material-symbols-outlined text-[18px]">close</span>
      </button>
    </div>
  `;
  const dismissButton = toast.querySelector(".toast-dismiss");
  if (dismissButton) {
    dismissButton.addEventListener("click", () => dismissToast(toast));
  }
  root.appendChild(toast);
  window.setTimeout(() => dismissToast(toast), 3200);
}

/**
 * Toast with an action button and countdown, e.g. Undo for bulk changes.
 * Returns { settled } — resolved once the window closes (action taken or
 * expired), with settled true when the user clicked the action in time.
 */
function showToastWithAction({ title, text = "", actionLabel = "", onAction = null, timeoutMs = 30000 }) {
  const root = document.getElementById("toast-root");
  if (!root) return Promise.resolve({ settled: false });
  root.setAttribute("aria-live", "polite");
  root.setAttribute("aria-atomic", "false");
  const toast = document.createElement("div");
  toast.className = "toast";
  toast.setAttribute("role", "status");
  toast.innerHTML = `
    <div class="toast-body">
      <div>
        <strong>${title}</strong>
        ${text ? `<p>${text}</p>` : ""}
        <div class="toast-action-row">
          <button type="button" class="toast-action">${actionLabel}</button>
          <span class="toast-countdown" aria-hidden="true"></span>
        </div>
      </div>
      <button type="button" class="toast-dismiss" aria-label="Dismiss message">
        <span class="material-symbols-outlined text-[18px]">close</span>
      </button>
    </div>
  `;
  let settled = false;
  let closed = false;
  let tickTimer = null;
  let closeTimer = null;
  let resolve;
  const promise = new Promise((res) => { resolve = res; });
  const close = (didAction) => {
    if (closed) return;
    closed = true;
    settled = didAction;
    window.clearInterval(tickTimer);
    window.clearTimeout(closeTimer);
    dismissToast(toast);
    resolve({ settled });
  };
  const actionButton = toast.querySelector(".toast-action");
  if (actionButton) {
    actionButton.addEventListener("click", () => close(true));
  }
  const dismissButton = toast.querySelector(".toast-dismiss");
  if (dismissButton) {
    dismissButton.addEventListener("click", () => close(false));
  }
  const countdown = toast.querySelector(".toast-countdown");
  const deadline = Date.now() + timeoutMs;
  tickTimer = window.setInterval(() => {
    if (countdown) countdown.textContent = `${Math.max(0, Math.ceil((deadline - Date.now()) / 1000))}s`;
  }, 500);
  if (countdown) countdown.textContent = `${Math.ceil(timeoutMs / 1000)}s`;
  closeTimer = window.setTimeout(() => close(false), timeoutMs);
  root.appendChild(toast);
  return promise;
}
