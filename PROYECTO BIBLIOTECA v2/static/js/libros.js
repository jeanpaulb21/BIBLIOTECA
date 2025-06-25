document.addEventListener("DOMContentLoaded", function () {
  const contenido = document.getElementById("contenido-opcion");
  const modal = new bootstrap.Modal(document.getElementById("modalLibro"));
  const modalBody = document.getElementById("modal-libro-body");

  const cargarContenido = (url) => {
    fetch(url)
      .then((response) => response.text())
      .then((html) => {
        if (url.includes("nuevo") || url.includes("editar")) {
          // 🌟 Animación suave para el contenido del modal
          modalBody.style.opacity = 0;
          modalBody.innerHTML = html;
          setTimeout(() => {
            modalBody.style.opacity = 1;
          }, 50);
          modal.show();
        } else {
          // 🌟 Animación suave para el contenido principal
          contenido.style.opacity = 0;
          setTimeout(() => {
            contenido.innerHTML = html;
            contenido.style.opacity = 1;
            if (url.includes("mostrar")) {
              asignarEventosBotonesEditar();
            }
          }, 150);
        }
      });
  };

  document.getElementById("btn-agregar")?.addEventListener("click", () => {
    cargarContenido("/admin/libros/nuevo");
  });

  document.getElementById("btn-mostrar")?.addEventListener("click", () => {
    cargarContenido("/admin/libros/mostrar");
  });

  document.getElementById("btn-eliminar")?.addEventListener("click", () => {
    cargarContenido("/admin/libros/eliminar");
  });

  function asignarEventosBotonesEditar() {
    document.querySelectorAll(".btn-editar").forEach((btn) => {
      btn.addEventListener("click", function () {
        const libroId = this.getAttribute("data-id");
        cargarContenido(`/admin/libros/editar/${libroId}`);
      });
    });
  }

  // Inicial asignación de eventos si ya hay contenido cargado
  asignarEventosBotonesEditar();
});

// ✅ Animación suave al cargar libros en el modal directamente
document.getElementById("btn-mostrar-libros-modal")?.addEventListener("click", () => {
  fetch("/admin/libros/mostrar")
    .then(res => res.text())
    .then(html => {
      const modal = new bootstrap.Modal(document.getElementById("modalLibro"));
      const modalBody = document.getElementById("modal-libro-body");
      modalBody.style.opacity = 0;
      modalBody.innerHTML = html;
      setTimeout(() => {
        modalBody.style.opacity = 1;
      }, 50);
      document.getElementById("modalLibroLabel").textContent = "Lista de Libros";
      modal.show();
    });
});
