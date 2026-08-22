// The homepage content and language variants are static HTML.
// JavaScript is used only as a progressive enhancement for the mobile menu.
document.documentElement.classList.add("js");

window.addEventListener("DOMContentLoaded", () => {
  const sidebar = document.getElementById("sidebar");
  const button = document.getElementById("menu-toggle");
  if (!sidebar || !button) return;

  const mobile = () => window.matchMedia("(max-width: 768px)").matches;

  const setOpen = (open) => {
    if (!mobile()) {
      sidebar.classList.remove("collapsed");
      button.setAttribute("aria-expanded", "true");
      return;
    }
    sidebar.classList.toggle("collapsed", !open);
    button.setAttribute("aria-expanded", String(open));
  };

  setOpen(false);

  button.addEventListener("click", () => {
    setOpen(sidebar.classList.contains("collapsed"));
  });

  sidebar.querySelectorAll("a[href^='#']").forEach(link => {
    link.addEventListener("click", () => setOpen(false));
  });

  window.addEventListener("resize", () => setOpen(!mobile()));

  document.addEventListener("keydown", event => {
    if (event.key === "Escape" && mobile()) {
      setOpen(false);
      button.focus();
    }
  });
});
