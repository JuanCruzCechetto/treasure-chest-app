// Alterna entre modo día (fondo blanco, texto negro) y modo noche (fondo negro, texto blanco).
(function () {
  const raiz = document.documentElement;
  const boton = document.getElementById('cambiar-tema');
  if (!boton) return;
  boton.addEventListener('click', function () {
    const nuevo = raiz.dataset.tema === 'noche' ? 'dia' : 'noche';
    raiz.dataset.tema = nuevo;
    try { localStorage.setItem('tema', nuevo); } catch (e) { /* sin almacenamiento: solo dura esta página */ }
  });
})();
