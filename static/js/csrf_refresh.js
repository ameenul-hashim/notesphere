/* NoteSphere — keep CSRF tokens fresh.
 *
 * Django rotates the CSRF token on login. If a form page is restored from the
 * browser's back/forward cache (or is still open in another tab), its hidden
 * token can no longer match the cookie and the POST is rejected. This script
 * refreshes the token whenever the page becomes active again and patches any
 * csrfmiddlewaretoken inputs plus the meta tag used by theme.js.
 */
(function () {
  "use strict";

  var ENDPOINT = "/csrf/refresh/";
  var MIN_INTERVAL = 30000;
  var lastRefresh = 0;
  var inFlight = false;

  function applyToken(token) {
    if (!token) return;
    var meta = document.querySelector('meta[name="csrf-token"]');
    if (meta) meta.setAttribute("content", token);
    var fields = document.querySelectorAll('input[name="csrfmiddlewaretoken"]');
    for (var i = 0; i < fields.length; i++) {
      fields[i].value = token;
    }
  }

  function refresh() {
    if (inFlight) return Promise.resolve();
    inFlight = true;
    return fetch(ENDPOINT, {
      method: "GET",
      credentials: "same-origin",
      cache: "no-store",
      headers: { "X-Requested-With": "XMLHttpRequest" },
    })
      .then(function (response) {
        return response.ok ? response.json() : null;
      })
      .then(function (data) {
        if (data && data.csrfToken) {
          applyToken(data.csrfToken);
          lastRefresh = Date.now();
        }
      })
      .catch(function () {})
      .then(function () {
        inFlight = false;
      });
  }

  function refreshIfStale() {
    if (Date.now() - lastRefresh < MIN_INTERVAL) return;
    refresh();
  }

  window.NoteSphereRefreshCSRF = refresh;

  window.addEventListener("pageshow", function (event) {
    if (event.persisted) refreshIfStale();
  });
  window.addEventListener("focus", refreshIfStale);
  document.addEventListener("visibilitychange", function () {
    if (!document.hidden) refreshIfStale();
  });
})();
