(function () {
  var STORAGE_KEY = "notesphere-theme";

  function isDark() {
    return document.documentElement.classList.contains("dark");
  }

  document.addEventListener("DOMContentLoaded", function () {
    document.addEventListener("click", function (event) {
      var btn = event.target.closest
        ? event.target.closest("[data-theme-toggle]")
        : null;
      if (!btn) return;
      var dark = !isDark();
      document.documentElement.classList.toggle("dark", dark);
      try {
        localStorage.setItem(STORAGE_KEY, dark ? "dark" : "light");
      } catch (e) {}
    });
  });
})();
