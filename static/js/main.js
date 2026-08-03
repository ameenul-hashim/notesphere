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

  /* ---------- Password visibility ---------- */
  function initPasswordToggles() {
    document.querySelectorAll("input[data-toggle='password']").forEach(function (input) {
      if (input.parentNode.querySelector(".password-toggle")) return;
      var button = document.createElement("button");
      button.type = "button";
      button.className = "password-toggle";
      button.textContent = "Show password";
      button.setAttribute("aria-label", "Toggle password visibility");
      button.setAttribute("aria-pressed", "false");
      input.parentNode.insertBefore(button, input.nextSibling);

      button.addEventListener("click", function () {
        var visible = input.type === "text";
        input.type = visible ? "password" : "text";
        button.textContent = visible ? "Show password" : "Hide password";
        button.setAttribute("aria-pressed", visible ? "false" : "true");
      });
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

  /* ---------- Alerts ---------- */
  function initAlerts() {
    var alerts = Array.prototype.slice.call(
      document.querySelectorAll(".alert[data-autodismiss]")
    );

    function dismissAlert(alert) {
      if (alert.classList.contains("alert-leaving")) return;
      alert.classList.add("alert-leaving");
      alert.addEventListener("animationend", function () {
        alert.remove();
      });
    }

    alerts.forEach(function (alert) {
      var closeBtn = document.createElement("button");
      closeBtn.type = "button";
      closeBtn.className = "alert-close";
      closeBtn.setAttribute("aria-label", "Dismiss");
      closeBtn.innerHTML =
        '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><path d="M6 6l12 12M18 6L6 18"/></svg>';
      alert.appendChild(closeBtn);

      closeBtn.addEventListener("click", function () {
        dismissAlert(alert);
      });

      var dismissIn = parseInt(alert.getAttribute("data-autodismiss"), 10);
      if (!isNaN(dismissIn) && dismissIn > 0) {
        setTimeout(function () {
          dismissAlert(alert);
        }, dismissIn);
      }
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

  document.addEventListener("DOMContentLoaded", function () {
    modalEl = document.getElementById("modal");
    initPasswordToggles();
    initSidebar();
    initAlerts();
    initConfirmForms();
  });
})();
