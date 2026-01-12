// 1) Buscador en vivo para tablas
document.addEventListener("DOMContentLoaded", () => {
  const search = document.querySelector("[data-table-search]");
  const table = document.querySelector("[data-table]");

  if (search && table) {
    const rows = Array.from(table.querySelectorAll("tbody tr"));

    search.addEventListener("input", () => {
      const q = search.value.toLowerCase().trim();
      rows.forEach((tr) => {
        const text = tr.innerText.toLowerCase();
        tr.style.display = text.includes(q) ? "" : "none";
      });
    });
  }

  // 2) Validación simple de cédula (solo ejemplo)
  const cedulaInput = document.querySelector("input[name='cedula']");
  if (cedulaInput) {
    cedulaInput.addEventListener("input", () => {
      cedulaInput.value = cedulaInput.value.replace(/\D/g, ""); // solo números
    });
  }
});
