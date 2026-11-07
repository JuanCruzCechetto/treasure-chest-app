// Boton de modo dia / noche
(function () {
  const raiz = document.documentElement;
  const boton = document.getElementById('cambiar-tema');
  if (!boton) return;
  boton.addEventListener('click', function () {
    const nuevo = raiz.dataset.tema === 'noche' ? 'dia' : 'noche';
    raiz.dataset.tema = nuevo;
    try { localStorage.setItem('tema', nuevo); } catch (e) {}
  });
})();
