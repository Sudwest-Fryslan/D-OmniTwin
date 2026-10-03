/*
 * Uitloggen in de viewer (#266). De backend is de OIDC-client (ADR 0008): uitloggen verwijdert de
 * sessie en geeft het adres waarmee de browser ook bij Keycloak uitlogt; daarna terug naar de kaart.
 * Ook gebruikt door de pagina "Geen toegang" (src/omnitwin/viewer_toegang.py).
 */
(function () {
  'use strict';

  async function uitloggen(knop) {
    knop.disabled = true;
    try {
      const res = await fetch('/api/admin/auth/logout?terug=/', { method: 'POST', credentials: 'same-origin' });
      const data = res.ok ? await res.json() : {};
      window.location.assign(data.uitlog_url || '/');
    } catch (e) {
      window.location.assign('/');
    }
  }

  function koppel() {
    const knop = document.getElementById('uitloggen');
    if (knop) knop.addEventListener('click', function () { uitloggen(knop); });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', koppel);
  } else {
    koppel();
  }
})();
