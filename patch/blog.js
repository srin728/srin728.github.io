window.addEventListener("DOMContentLoaded", () => {
  const sidebar = document.getElementById("sidebar");
  const hamburger = document.getElementById("hamburger");
  if (!sidebar || !hamburger) return;

  const closeSidebar = () => {
    sidebar.classList.remove("open");
    hamburger.setAttribute("aria-expanded", "false");
    hamburger.setAttribute("aria-label", "メニューを開く");
  };

  hamburger.addEventListener("click", event => {
    event.stopPropagation();
    const isOpen = sidebar.classList.toggle("open");
    hamburger.setAttribute("aria-expanded", String(isOpen));
    hamburger.setAttribute("aria-label", isOpen ? "メニューを閉じる" : "メニューを開く");
  });

  document.addEventListener("click", event => {
    if (!sidebar.contains(event.target) && !hamburger.contains(event.target)) {
      closeSidebar();
    }
  });

  document.addEventListener("keydown", event => {
    if (event.key === "Escape") closeSidebar();
  });
});
