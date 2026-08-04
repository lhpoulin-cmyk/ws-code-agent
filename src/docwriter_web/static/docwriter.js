// Progressive enhancement only. Review actions remain ordinary forms and links.
document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("details[data-focus-target]").forEach((details) => {
    details.addEventListener("toggle", () => {
      if (details.open) document.getElementById(details.dataset.focusTarget)?.focus();
    });
  });
});
