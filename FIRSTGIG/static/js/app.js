document.addEventListener("DOMContentLoaded", () => {
  const confirmers = document.querySelectorAll("[data-confirm]");
  confirmers.forEach((el) => {
    el.addEventListener("click", (e) => {
      const msg = el.getAttribute("data-confirm");
      if (msg && !window.confirm(msg)) e.preventDefault();
    });
  });
});
