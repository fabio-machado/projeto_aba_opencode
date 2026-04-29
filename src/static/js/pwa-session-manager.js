// pwa-session-manager.js — T020/T021/T022: sessão persistente Supabase + refresh + offline
(function () {
  'use strict';

  var SUPABASE_URL = window.SUPABASE_URL;
  var SUPABASE_ANON_KEY = window.SUPABASE_ANON_KEY;
  if (!SUPABASE_URL || !SUPABASE_ANON_KEY) return;

  var supabase = null;
  try {
    if (!window.supabase) return;  // Supabase SDK CDN not loaded
    supabase = window.supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
      auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: false }
    });
  } catch (e) { return; }

  var REFRESH_MARGIN_MS = 5 * 60 * 1000; // 5 min before expiry

  function isNearExpiry(session) {
    if (!session || !session.expires_at) return false;
    return (new Date(session.expires_at * 1000).getTime() - Date.now()) < REFRESH_MARGIN_MS;
  }

  function setSessionExpiredUI() {
    document.body.setAttribute('data-session-expired', 'true');
    var b = document.createElement('div');
    b.id = 'pwa-session-expired-banner';
    b.setAttribute('role', 'alert');
    b.innerHTML = '<div style="position:fixed;bottom:0;left:0;right:0;z-index:100;background:#fef2f2;border-top:1px solid #fecaca;padding:12px 16px;text-align:center;font-size:14px;color:#991b1b;">Sess&atilde;o expirada &mdash; <a href="/login/" style="font-weight:600;text-decoration:underline;color:#991b1b;">fa&ccedil;a login para editar</a></div>';
    document.body.appendChild(b);
  }

  function clearSessionExpiredUI() {
    document.body.removeAttribute('data-session-expired');
    var b = document.getElementById('pwa-session-expired-banner');
    if (b) b.remove();
  }

  async function refreshSession() {
    try {
      var { data, error } = await supabase.auth.refreshSession();
      if (error) throw error;
      if (data && data.session) { clearSessionExpiredUI(); return data.session; }
    } catch (err) {
      if (err.message && err.message.indexOf('refresh_token_not_found') !== -1) {
        setSessionExpiredUI();
      }
    }
    return null;
  }

  async function checkAndRefresh() {
    var { data } = await supabase.auth.getSession();
    var session = data && data.session;
    if (session && isNearExpiry(session)) await refreshSession();
  }

  document.addEventListener('DOMContentLoaded', function () {
    if (!navigator.onLine) return;  // T022: skip refresh when offline
    checkAndRefresh();
  });

  document.addEventListener('visibilitychange', function () {
    if (document.visibilityState === 'visible' && navigator.onLine) checkAndRefresh();
  });
})();
