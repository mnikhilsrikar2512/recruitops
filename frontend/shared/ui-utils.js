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
  "reassignment-review-drawer.html",
  "stage-move-dialog.html",
  "status-update-dialog.html",
  "interview-feedback-dialog.html",
  "offer-create-dialog.html",
  "meeting-form-dialog.html",
  "follow-up-form-dialog.html",
  "dashboard-actions-overlay.html",
  "onboarding-add-custom-stage-overlay.html",
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
