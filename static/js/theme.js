(function () {
  var root = document.documentElement;
  var toggle = document.getElementById("theme-toggle");

  function syncIcons(dark) {
    if (!toggle) return;
    var iconDark = toggle.querySelector(".icon-dark");
    var iconLight = toggle.querySelector(".icon-light");
    if (iconDark) iconDark.classList.toggle("hidden", !dark);
    if (iconLight) iconLight.classList.toggle("hidden", dark);
  }

  function applyTheme(dark) {
    root.classList.toggle("dark", dark);
    localStorage.setItem("notesphere-theme", dark ? "dark" : "light");
    syncIcons(dark);
  }

  if (toggle) {
    syncIcons(root.classList.contains("dark"));
    toggle.addEventListener("click", function () {
      applyTheme(!root.classList.contains("dark"));
    });
  }
})();
