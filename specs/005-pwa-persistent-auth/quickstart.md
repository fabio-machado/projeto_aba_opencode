# Quickstart: PWA com Sessão Persistente

**Date**: 2026-04-29
**Feature**: 005-pwa-persistent-auth

## Development Setup

### 1. Install django-pwa

```bash
pip install django-pwa
```

Or add to `requirements.txt`:
```
django-pwa>=2.0.0
```

### 2. Configure Django

In `src/config/settings/base.py`:

```python
INSTALLED_APPS = [
    # ... existing apps
    "pwa",
]

PWA_APP_CONFIG = {
    "name": "Autismo em Foco",
    "short_name": "AEF",
    "display": "standalone",
    "orientation": "portrait",
    "theme_color": "#14b8a6",
    "background_color": "#f8fafc",
    "start_url": "/",
    "scope": "/",
    "icons": [
        {"src": "/static/images/pwa/icon-192x192.png", "sizes": "192x192", "type": "image/png"},
        {"src": "/static/images/pwa/icon-512x512.png", "sizes": "512x512", "type": "image/png"},
    ],
}
```

In `src/config/urls.py`:

```python
urlpatterns = [
    # ... existing paths
    path("", include("pwa.urls")),
]
```

### 3. Update base.html

Add to `<head>` in `src/templates/base.html`:

```django
{% load pwa %}
{% progressive_web_app_meta %}
```

### 4. Add PWA Scripts

Include in `base.html` before closing `</body>`:

```html
<script src="/static/js/pwa-session-manager.js"></script>
<script src="/static/js/pwa-install-banner.js"></script>
```

### 5. Add Logout Button to Header

In `src/templates/partials/nav/_header.html`, add a logout button inside the user menu:

```html
<a href="/logout/" class="block px-4 py-2 text-sm text-error hover:bg-surface-variant">
  Sair
</a>
```

### 6. Generate Icons

Create icons at:
- `src/static/images/pwa/icon-192x192.png`
- `src/static/images/pwa/icon-512x512.png`

Use a tool like [PWA Asset Generator](https://github.com/onderceylan/pwa-asset-generator) or design them in Figma/Illustrator.

## Testing

### Unit Tests

```bash
cd src
pytest apps/ -v -k pwa
```

### Lighthouse PWA Audit

1. Open Chrome DevTools → Lighthouse
2. Select "PWA" category
3. Run audit on the homepage
4. Target score: ≥ 90

### Manual Testing Checklist

- [ ] App is installable from Chrome menu (⋮ → Install)
- [ ] After installation, app opens in standalone mode (no address bar)
- [ ] App loads CSS/JS instantly on second visit (offline mode test)
- [ ] Session persists after closing and reopening the app
- [ ] Banner "Instalar App para registro rápido" appears for non-installed users
- [ ] Banner disappears after installation
- [ ] Logout button is accessible from header menu
- [ ] After logout, user is redirected to login page

### Offline Test

1. Open the app in Chrome
2. Open DevTools → Network → Set to "Offline"
3. Refresh the page
4. Verify that the app shell (header, nav, styles) loads correctly
5. Verify that dynamic content shows offline state or cached data

## Deployment Notes

- HTTPS is required for Service Workers in production
- The `django-pwa` app must be included in `INSTALLED_APPS` on all environments
- Static files must be served correctly (use `collectstatic` in production)
- The manifest.json and serviceworker.js are served automatically by django-pwa
