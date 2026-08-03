document.addEventListener("DOMContentLoaded", function () {
  document.querySelectorAll("input[data-toggle='password']").forEach(function (input) {
    var button = document.createElement("button");
    button.type = "button";
    button.className = "text-sm text-blue-600 hover:underline mt-1";
    button.textContent = "Show password";
    button.setAttribute("aria-label", "Toggle password visibility");

    input.parentNode.insertBefore(button, input.nextSibling);

    button.addEventListener("click", function () {
      var isVisible = input.type === "text";
      input.type = isVisible ? "password" : "text";
      button.textContent = isVisible ? "Show password" : "Hide password";
    });
  });

  var menuToggle = document.getElementById("menu-toggle");
  var mobileMenu = document.getElementById("mobile-menu");

  if (menuToggle && mobileMenu) {
    menuToggle.addEventListener("click", function () {
      var hidden = mobileMenu.classList.toggle("hidden");
      menuToggle.setAttribute("aria-expanded", hidden ? "false" : "true");
    });
  }
});
