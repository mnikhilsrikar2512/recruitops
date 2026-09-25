/* ═══════════════════════════════════════════════════════════════
   FORMS — Auto-extracted from app.js
   ═══════════════════════════════════════════════════════════════ */

function annotateRequiredFields(scope = document) {
  scope.querySelectorAll("label").forEach((label) => {
    const text = label.textContent || "";
    if (!text.includes("*")) return;
    const htmlFor = label.getAttribute("for");
    if (htmlFor) {
      const target = scope.querySelector(`#${CSS.escape(htmlFor)}`);
      if (target) {
        target.setAttribute("required", "required");
      }
      return;
    }
    const nested = label.querySelector("input, select, textarea");
    if (nested) {
      nested.setAttribute("required", "required");
    }
  });

  const selectorConfig = document.body?.dataset.requiredSelectors || "";
  selectorConfig
    .split("||")
    .map((selector) => selector.trim())
    .filter(Boolean)
    .forEach((selector) => {
      try {
        const target = scope.querySelector(selector);
        if (target) {
          target.setAttribute("required", "required");
        }
      } catch (error) {
        console.warn(`Skipping invalid required selector: ${selector}`);
      }
    });
}


function clearFieldError(field) {
  field.classList.remove("field-error");
  field.removeAttribute("aria-invalid");
}


function markFieldError(field) {
  field.classList.add("field-error");
  field.setAttribute("aria-invalid", "true");
}


function bindFieldValidation(scope = document) {
  scope.querySelectorAll("input, select, textarea").forEach((field) => {
    const clearState = () => {
      const value = field.type === "checkbox" || field.type === "radio" ? String(field.checked) : (field.value || "").trim();
      if (value) {
        clearFieldError(field);
      }
    };
    field.addEventListener("input", clearState);
    field.addEventListener("change", clearState);
  });
}


function getInteractiveFields(scope) {
  const requiredFields = Array.from(scope.querySelectorAll("input[required], select[required], textarea[required]"))
    .filter((field) => field.type !== "checkbox" && field.type !== "radio" && !field.disabled);
  if (requiredFields.length > 0) {
    return requiredFields;
  }
  return Array.from(scope.querySelectorAll("input, select, textarea"))
    .filter((field) => field.type !== "checkbox" && field.type !== "radio" && !field.disabled);
}


function getProgressFields(form) {
  const requiredFields = Array.from(form.querySelectorAll("input[required], select[required], textarea[required]"))
    .filter((field) => field.type !== "checkbox" && field.type !== "radio" && !field.disabled);
  if (requiredFields.length >= 2) {
    return requiredFields;
  }
  return Array.from(form.querySelectorAll("input, select, textarea"))
    .filter((field) => field.type !== "checkbox" && field.type !== "radio" && !field.disabled);
}


function isFieldComplete(field) {
  const value = (field.value || "").trim();
  if (!value) return false;
  if (field.tagName === "SELECT" && /select/i.test(field.options[field.selectedIndex]?.text || "")) {
    return false;
  }
  if (field.type === "email" && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) {
    return false;
  }
  if (field.type === "number") {
    const numericValue = Number(value);
    if (Number.isNaN(numericValue)) return false;
    if (field.min && numericValue < Number(field.min)) return false;
    if (field.max && numericValue > Number(field.max)) return false;
  }
  return true;
}


function setupFormProgress(form) {
  if (form.id === "login-form") return;
  if (form.dataset.skipProgress === "true") return;
  if (form.id === "profile-details-form" || form.id === "profile-password-form") return;
  const fields = getProgressFields(form);
  if (fields.length < 2) return;

  const progressCard = document.createElement("section");
  progressCard.className = "form-progress";
  progressCard.setAttribute("aria-live", "polite");
  progressCard.innerHTML = `
    <div class="form-progress-label">
      <div>
        <strong>Completion progress</strong>
        <p class="m-0 text-[12px] text-text-muted">Keep moving through the essentials before triggering the next workflow step.</p>
      </div>
      <span data-form-progress-count>0 of ${fields.length} ready</span>
    </div>
    <div class="form-progress-track" aria-hidden="true">
      <div class="form-progress-value" data-form-progress-value></div>
    </div>
  `;

  form.prepend(progressCard);
  const countNode = progressCard.querySelector("[data-form-progress-count]");
  const valueNode = progressCard.querySelector("[data-form-progress-value]");

  const updateProgress = () => {
    const completeCount = fields.filter((field) => isFieldComplete(field)).length;
    const percent = Math.round((completeCount / fields.length) * 100);
    if (countNode) {
      countNode.textContent = `${completeCount} of ${fields.length} ready`;
    }
    if (valueNode) {
      valueNode.style.width = `${percent}%`;
    }
  };

  fields.forEach((field) => {
    field.addEventListener("input", updateProgress);
    field.addEventListener("change", updateProgress);
  });
  updateProgress();
}


function validateScope(scope) {
  let firstInvalid = null;
  const fields = getInteractiveFields(scope);
  fields.forEach((field) => clearFieldError(field));
  fields.forEach((field) => {
    if (!isFieldComplete(field)) {
      markFieldError(field);
      if (!firstInvalid) firstInvalid = field;
    }
  });
  if (firstInvalid) {
    firstInvalid.focus();
    showToast("Some details still need attention", "Complete the highlighted fields before continuing.");
    return false;
  }
  return true;
}


function validateForm(form) {
  return validateScope(form);
}


function resetAlertBanner(banner) {
  if (!banner) return;
  banner.className = "hidden w-full p-3 rounded flex items-start gap-3 border";
}


function showAlertState(config) {
  const banner = document.getElementById("alert-banner");
  const alertIcon = document.getElementById("alert-icon");
  const alertTitle = document.getElementById("alert-title");
  const alertMessage = document.getElementById("alert-message");
  if (!banner || !alertIcon || !alertTitle || !alertMessage) return;

  resetAlertBanner(banner);
  banner.classList.remove("hidden");
  banner.classList.add(config.bgClass, config.textClass, config.borderClass);
  banner.setAttribute("role", config.role || "status");
  alertIcon.textContent = config.icon;
  alertTitle.textContent = config.title;
  alertMessage.textContent = config.message;
}


function getFocusableElements(container) {
  if (!container) return [];
  return Array.from(container.querySelectorAll(FOCUSABLE_SELECTOR))
    .filter((element) => !element.hasAttribute("disabled") && element.getAttribute("aria-hidden") !== "true" && element.getClientRects().length > 0);
}


function focusFirstInteractive(container) {
  const [first] = getFocusableElements(container);
  if (first) {
    first.focus();
  }
}


function trapFocusWithin(event, container) {
  if (event.key !== "Tab") return;
  const focusable = getFocusableElements(container);
  if (focusable.length === 0) return;

  const first = focusable[0];
  const last = focusable[focusable.length - 1];
  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault();
    last.focus();
    return;
  }
  if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault();
    first.focus();
  }
}


