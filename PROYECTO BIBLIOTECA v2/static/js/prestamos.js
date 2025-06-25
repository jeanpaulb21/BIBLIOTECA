document.addEventListener("DOMContentLoaded", function () {
  const contenido = document.getElementById("contenido-opcion");
  const modal = new bootstrap.Modal(document.getElementById("modalPrestamo"));
  const modalBody = document.getElementById("modal-prestamo-body");
  const modalTitle = document.getElementById("modalPrestamoLabel");

  const cargarContenido = (url) => {
    fetch(url)
      .then(response => response.text())
      .then(html => {
        if (url.includes("nuevo") || url.includes("editar")) {
          modalBody.innerHTML = html;

          if (url.includes("nuevo")) {
            modalTitle.textContent = "Agregar Préstamo";
            modal.show();
            setTimeout(inicializarFormularioPrestamo, 100);  // 👈 ejecuta el script del formulario
          } else if (url.includes("editar")) {
            modalTitle.textContent = "Editar Préstamo";
            modal.show();
          } else if (url.includes("mostrar")) {
            modalTitle.textContent = "Lista de Préstamos";
            modal.show();
          }

        } else {
          contenido.style.opacity = 0;
          setTimeout(() => {
            contenido.innerHTML = html;
            contenido.style.opacity = 1;
          }, 150);
        }
      });
  };

  document.getElementById("btn-mostrar-prestamos")?.addEventListener("click", () => {
    cargarContenido("/admin/prestamos/mostrar");
  });

  document.getElementById("btn-agregar-prestamos")?.addEventListener("click", () => {
    cargarContenido("/admin/prestamos/nuevo");
  });

  function inicializarFormularioPrestamo() {
    const form = document.getElementById("form-prestamo");
    if (!form) return;

    form.addEventListener("submit", function (e) {
      e.preventDefault();

      const datos = {
        usuario_id: document.getElementById("usuario_id").value,
        libro_id: document.getElementById("libro_id").value,
        fecha_prestamo: document.getElementById("fecha_prestamo").value
      };

      fetch("/admin/prestamos/guardar", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(datos)
      })
      .then(res => res.json())
      .then(respuesta => {
        if (respuesta.mensaje) {
          document.getElementById("notificacion-prestamo").classList.remove("d-none");
          form.reset();
        }
      });
    });
  }
});
