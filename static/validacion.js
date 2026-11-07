// Validacion en el cliente. El servidor valida igual.
(function () {
  function mostrar(form, campo, mensaje) {
    const input = form.querySelector('[name="' + campo + '"]');
    const salida = form.querySelector('[data-error-de="' + campo + '"]');
    if (salida) salida.textContent = mensaje || '';
    if (input) input.classList.toggle('invalido', Boolean(mensaje));
  }

  function hoyLocal() {
    const d = new Date();
    return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
  }

  const reglas = {
    registro(f) {
      const e = {};
      if (!/^[A-Za-z0-9_]{3,20}$/.test(f.nombre.value.trim()))
        e.nombre = 'Entre 3 y 20 caracteres: letras, números o guion bajo.';
      if (f.clave.value.length < 8) e.clave = 'La contraseña debe tener al menos 8 caracteres.';
      if (f.confirmar.value !== f.clave.value) e.confirmar = 'Las contraseñas no coinciden.';
      return e;
    },
    login(f) {
      const e = {};
      if (!f.nombre.value.trim()) e.nombre = 'Ingresá tu usuario.';
      if (!f.clave.value) e.clave = 'Ingresá tu contraseña.';
      return e;
    },
    gasto(f) {
      const e = {};
      const desc = f.descripcion.value.trim();
      if (!desc || desc.length > 100) e.descripcion = 'La descripción es obligatoria (máx. 100 caracteres).';
      const monto = parseFloat(f.monto.value);
      if (isNaN(monto) || monto <= 0) e.monto = 'El monto tiene que ser mayor a 0.';
      if (!f.categoria.value) e.categoria = 'Elegí una categoría.';
      if (!f.fecha.value) e.fecha = 'Elegí una fecha.';
      else if (f.fecha.value > hoyLocal()) e.fecha = 'La fecha no puede ser futura.';
      return e;
    }
  };

  document.querySelectorAll('form[data-validar]').forEach(function (form) {
    const regla = reglas[form.dataset.validar];
    form.addEventListener('submit', function (ev) {
      const errores = regla(form);
      Array.from(form.elements).forEach(function (el) { if (el.name) mostrar(form, el.name, errores[el.name]); });
      if (Object.keys(errores).length) {
        ev.preventDefault();
        const primero = form.querySelector('.invalido');
        if (primero) primero.focus();
      }
    });
  });
})();
