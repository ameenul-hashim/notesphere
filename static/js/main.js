(function () {
  "use strict";

  var lastFocused = null;
  var pendingForm = null;

  function focusable(el) {
    return el.querySelectorAll(
      'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
    );
  }

  function trapFocus(container, event) {
    var items = focusable(container);
    if (items.length === 0) return;
    var first = items[0];
    var last = items[items.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }

  /* ---------- Password visibility (eye toggle) ---------- */
  var EYE_ON_SVG =
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>';
  var EYE_OFF_SVG =
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><path d="M1 1l22 22"/></svg>';

  function initPasswordToggles() {
    document.querySelectorAll("input[data-toggle='password']").forEach(function (input) {
      if (input.dataset.eyeBound) return;
      input.dataset.eyeBound = "1";

      var shell = document.createElement("span");
      shell.className = "input-shell";
      input.parentNode.insertBefore(shell, input);
      shell.appendChild(input);

      var button = document.createElement("button");
      button.type = "button";
      button.className = "password-toggle";
      button.setAttribute("aria-label", "Show password");
      button.setAttribute("aria-pressed", "false");
      button.setAttribute("tabindex", "-1");
      button.innerHTML = EYE_ON_SVG;

      button.addEventListener("click", function () {
        var visible = input.type === "text";
        input.type = visible ? "password" : "text";
        button.innerHTML = visible ? EYE_ON_SVG : EYE_OFF_SVG;
        button.setAttribute("aria-pressed", visible ? "false" : "true");
        button.setAttribute("aria-label", visible ? "Show password" : "Hide password");
        input.focus();
      });

      shell.appendChild(button);
    });
  }

  /* ---------- Sidebar drawer ---------- */
  function initSidebar() {
    var sidebar = document.getElementById("sidebar");
    var overlay = document.getElementById("sidebar-overlay");
    var openers = Array.prototype.slice.call(document.querySelectorAll("[data-sidebar-open]"));
    if (!sidebar || !overlay) return;

    function setOpen(open, opener) {
      sidebar.classList.toggle("open", open);
      overlay.classList.toggle("open", open);
      openers.forEach(function (o) {
        o.setAttribute("aria-expanded", open ? "true" : "false");
      });
      if (open) {
        lastFocused = opener;
        var closeBtn = sidebar.querySelector("[data-sidebar-close]");
        if (closeBtn) closeBtn.focus();
      } else if (lastFocused) {
        lastFocused.focus();
      }
    }

    openers.forEach(function (opener) {
      opener.addEventListener("click", function () {
        setOpen(!sidebar.classList.contains("open"), opener);
      });
    });

    var closeBtn = sidebar.querySelector("[data-sidebar-close]");
    if (closeBtn) {
      closeBtn.addEventListener("click", function () {
        setOpen(false, closeBtn);
      });
    }

    overlay.addEventListener("click", function () {
      setOpen(false, null);
    });

    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape" && sidebar.classList.contains("open")) {
        setOpen(false, null);
      }
      if (event.key === "Tab" && sidebar.classList.contains("open")) {
        trapFocus(sidebar, event);
      }
    });
  }

  /* ---------- Toasts ---------- */
  var TOAST_DURATIONS = { success: 5000, info: 6000, warning: 7000, error: 9000 };
  var TOAST_ICONS = {
    success:
      '<svg class="toast-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><path d="M22 4L12 14.01l-3-3"/></svg>',
    info:
      '<svg class="toast-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/></svg>',
    warning:
      '<svg class="toast-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><path d="M12 9v4"/><path d="M12 17h.01"/></svg>',
    error:
      '<svg class="toast-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="10"/><path d="M12 8v4"/><path d="M12 16h.01"/></svg>',
  };

  function makeToastEl(variant, message) {
    var toast = document.createElement("div");
    toast.className = "toast toast-" + (variant || "info") + " toast-dynamic";
    toast.setAttribute("data-toast", "");
    toast.setAttribute("role", variant === "error" ? "alert" : "status");
    toast.innerHTML = TOAST_ICONS[variant] || TOAST_ICONS.info;
    var msg = document.createElement("p");
    msg.className = "toast-msg";
    msg.textContent = message;
    toast.appendChild(msg);
    return toast;
  }

  function attachToastControls(toast, variant) {
    var closeBtn = document.createElement("button");
    closeBtn.type = "button";
    closeBtn.className = "toast-close";
    closeBtn.setAttribute("aria-label", "Dismiss notification");
    closeBtn.innerHTML =
      '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><path d="M6 6l12 12M18 6L6 18"/></svg>';
    toast.appendChild(closeBtn);

    var progress = document.createElement("span");
    progress.className = "toast-progress";
    progress.setAttribute("aria-hidden", "true");
    toast.appendChild(progress);

    function dismiss() {
      if (toast.classList.contains("toast-leaving")) return;
      toast.classList.add("toast-leaving");
      toast.addEventListener("animationend", function () {
        toast.remove();
      });
    }

    closeBtn.addEventListener("click", dismiss);

    var duration = TOAST_DURATIONS[variant] || 6000;
    progress.style.animationDuration = duration + "ms";
    progress.addEventListener("animationend", dismiss);
  }

  function initToasts() {
    document.querySelectorAll(".toast[data-toast]:not(.toast-dynamic)").forEach(function (toast) {
      var variant = "info";
      if (toast.classList.contains("toast-success")) variant = "success";
      else if (toast.classList.contains("toast-error")) variant = "error";
      else if (toast.classList.contains("toast-warning")) variant = "warning";
      attachToastControls(toast, variant);
    });
  }

  window.showToast = function (variant, message) {
    var stack = document.querySelector("[data-toast-stack]");
    if (!stack) {
      stack = document.createElement("div");
      stack.className = "toast-stack";
      stack.setAttribute("data-toast-stack", "");
      stack.setAttribute("aria-live", "polite");
      document.body.appendChild(stack);
    }
    var toast = makeToastEl(variant, message);
    attachToastControls(toast, variant);
    stack.appendChild(toast);
  };

  /* ---------- Sidebar collapse (desktop) ---------- */
  function initSidebarCollapse() {
    var btn = document.querySelector("[data-sidebar-collapse]");
    if (!btn) return;
    btn.addEventListener("click", function () {
      var sidebar = document.getElementById("sidebar");
      var shell = document.querySelector(".app-shell");
      var collapsed = sidebar.classList.toggle("collapsed");
      if (shell) shell.classList.toggle("collapsed", collapsed);
      btn.setAttribute("aria-expanded", String(!collapsed));
      btn.title = collapsed ? "Expand sidebar" : "Collapse sidebar";
    });
  }

  /* ---------- Topbar scroll shadow ---------- */
  function initTopbar() {
    var topbar = document.querySelector("[data-topbar]");
    if (!topbar) return;
    function update() {
      topbar.classList.toggle("scrolled", window.scrollY > 8);
    }
    window.addEventListener("scroll", update, { passive: true });
    update();
  }

  /* ---------- Notification popover ---------- */
  function initNavPop() {
    var pop = document.querySelector("[data-nav-pop]");
    if (!pop) return;
    var trigger = pop.querySelector("[data-bell-trigger]");
    var menu = pop.querySelector("[data-bell-menu]");
    if (!trigger || !menu) return;

    function open() {
      menu.classList.add("open");
      menu.setAttribute("aria-hidden", "false");
      trigger.setAttribute("aria-expanded", "true");
    }
    function close() {
      menu.classList.remove("open");
      menu.setAttribute("aria-hidden", "true");
      trigger.setAttribute("aria-expanded", "false");
    }

    trigger.addEventListener("click", function (event) {
      event.stopPropagation();
      if (menu.classList.contains("open")) {
        close();
      } else {
        open();
      }
    });

    document.addEventListener("click", function (event) {
      if (!pop.contains(event.target)) close();
    });

    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape" && menu.classList.contains("open")) close();
    });
  }

  /* ---------- Confirm modal ---------- */
  var modalEl = null;

  function openModal(title, message, confirmText, danger) {
    if (!modalEl) return false;
    var modalTitle = document.getElementById("modal-title");
    var modalDesc = document.getElementById("modal-desc");
    var confirmBtn = document.getElementById("modal-confirm");
    var closeBtn = document.getElementById("modal-close");

    lastFocused = document.activeElement;
    modalTitle.textContent = title || "Are you sure?";
    modalDesc.textContent = message || "";
    confirmBtn.textContent = confirmText || "Confirm";
    confirmBtn.className = "btn " + (danger ? "btn-danger" : "btn-primary");

    modalEl.classList.add("open");
    modalEl.setAttribute("aria-hidden", "false");
    document.body.style.overflow = "hidden";

    if (closeBtn) closeBtn.focus();

    function onKeydown(event) {
      if (event.key === "Escape") close();
      if (event.key === "Tab") trapFocus(modalEl, event);
    }

    function onBackdropClick(event) {
      if (event.target === modalEl) close();
    }

    function close() {
      modalEl.classList.remove("open");
      modalEl.setAttribute("aria-hidden", "true");
      document.body.style.overflow = "";
      document.removeEventListener("keydown", onKeydown);
      modalEl.removeEventListener("click", onBackdropClick);
      if (lastFocused) lastFocused.focus();
    }

    confirmBtn.onclick = function () {
      close();
      var form = pendingForm;
      pendingForm = null;
      if (form) form.submit();
    };

    if (closeBtn) {
      closeBtn.onclick = close;
    }

    document.addEventListener("keydown", onKeydown);
    modalEl.addEventListener("click", onBackdropClick);
    return true;
  }

  function initConfirmForms() {
    document.querySelectorAll("form[data-confirm]").forEach(function (form) {
      form.addEventListener("submit", function (event) {
        event.preventDefault();
        pendingForm = form;
        openModal(
          form.getAttribute("data-confirm-title"),
          form.getAttribute("data-confirm"),
          form.getAttribute("data-confirm-label"),
          form.hasAttribute("data-confirm-danger")
        );
      });
    });
  }

  /* ---------- Image preview ---------- */
  function initImagePreviews() {
    document.querySelectorAll("input[data-preview]").forEach(function (input) {
      var target = document.querySelector("[data-preview-target]");
      if (!target) return;
      input.addEventListener("change", function () {
        var file = input.files && input.files[0];
        if (!file) return;
        var reader = new FileReader();
        reader.onload = function () {
          target.innerHTML = "";
          var img = document.createElement("img");
          img.src = reader.result;
          img.alt = "Preview";
          target.appendChild(img);
        };
        reader.readAsDataURL(file);
      });
    });
  }

  function initFilterSelects() {
    var selects = document.querySelectorAll("select[data-auto-submit]");
    Array.prototype.forEach.call(selects, function (select) {
      select.addEventListener("change", function () {
        if (select.form) select.form.submit();
      });
    });
  }

  /* ---------- Avatar picker: move the selected highlight on change ---------- */
  function initAvatarOptions() {
    var allOptions = document.querySelectorAll(".avatar-option");
    Array.prototype.forEach.call(allOptions, function (option) {
      var radio = option.querySelector("input[type='radio']");
      if (!radio) return;
      radio.addEventListener("change", function () {
        Array.prototype.forEach.call(allOptions, function (o) {
          var input = o.querySelector("input[type='radio']");
          o.classList.toggle("selected", input && input.checked);
        });
      });
    });
  }

  /* ---------- Form Field Errors (auto-dismiss & clear on typing) ---------- */
  function initFieldErrors() {
    var errorEls = document.querySelectorAll(".field-error, [data-field-error]");
    errorEls.forEach(function (errEl) {
      function dismissError() {
        if (errEl.classList.contains("fade-out")) return;
        errEl.classList.add("fade-out");
        setTimeout(function () {
          if (errEl.parentNode) errEl.parentNode.removeChild(errEl);
        }, 300);
      }

      // Auto-dismiss after 6 seconds
      var timer = setTimeout(dismissError, 6000);

      // Dismiss immediately when user types/changes any field in the same container or form
      var parent = errEl.closest(".field, .field-wrap, form, td, div") || errEl.parentNode;
      if (parent) {
        var inputs = parent.querySelectorAll("input, select, textarea");
        inputs.forEach(function (input) {
          function onUserEdit() {
            clearTimeout(timer);
            dismissError();
            input.removeEventListener("input", onUserEdit);
            input.removeEventListener("change", onUserEdit);
          }
          input.addEventListener("input", onUserEdit);
          input.addEventListener("change", onUserEdit);
        });
      }
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    modalEl = document.getElementById("modal");
    initPasswordToggles();
    initSidebar();
    initToasts();
    initSidebarCollapse();
    initTopbar();
    initNavPop();
    initConfirmForms();
    initImagePreviews();
    initFilterSelects();
    initAvatarOptions();
    initFieldErrors();
  });
})();

