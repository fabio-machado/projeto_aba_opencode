// pwa-install-banner.js — Banner de instalação PWA
// (T014, T016, T017)
(function () {
  'use strict';
  var deferredPrompt = null;
  var bannerDismissed = localStorage.getItem('aef_pwa_banner_dismissed');
  var isInstalled = localStorage.getItem('aef_pwa_installed');

  window.deferredPrompt = null;

  window.addEventListener('beforeinstallprompt', function (e) {
    e.preventDefault();
    deferredPrompt = e;
    window.deferredPrompt = e;
    if (bannerDismissed || isInstalled) return;
    document.body.dispatchEvent(new CustomEvent('pwa:installable', { detail: {} }));
  });

  window.showInstallPrompt = function () {
    if (!deferredPrompt) return;
    deferredPrompt.prompt();
    deferredPrompt.userChoice.then(function (result) {
      if (result.outcome === 'accepted') {
        localStorage.setItem('aef_pwa_installed', 'true');
      }
      deferredPrompt = null;
      window.deferredPrompt = null;
    });
  };

  window.dismissInstallBanner = function () {
    localStorage.setItem('aef_pwa_banner_dismissed', 'true');
    var d = new Date();
    d.setDate(d.getDate() + 30);
    localStorage.setItem('aef_pwa_banner_dismissed_until', d.toISOString());
    document.body.dispatchEvent(new CustomEvent('pwa:banner-dismissed'));
  };

  window.addEventListener('appinstalled', function () {
    localStorage.setItem('aef_pwa_installed', 'true');
    document.body.dispatchEvent(new CustomEvent('pwa:installed'));
  });
})();
