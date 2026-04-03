# Landing Page Export — Setup Instructions

## Files

- `free-analysis.html` — Full landing page (self-contained, no framework dependencies)
- `free-analysis.css` — All styles, prefixed with `mtg-` to avoid conflicts with your marketing site CSS

## 1. Drop into your marketing site

Copy both files into your marketing site repo. Adjust the CSS `<link>` path in the HTML to wherever you place the CSS file.

All CSS classes are prefixed with `mtg-` so they won't collide with your existing styles. The page is wrapped in a `.mtg-landing` container that scopes everything.

If your marketing site already loads Lato, you can remove the Google Fonts `<link>` tags from the HTML `<head>`.

## 2. Configure the two URLs in the script

At the bottom of the HTML, find the `CONFIG` section:

```js
var API_BASE = 'https://content-exploration-featurebranch.up.railway.app';
var STATUS_PAGE = 'https://vizualizd.mapthegap.ai/free-analysis';
```

- **API_BASE** — The subdomain where your backend API lives. This is where the `POST /api/public/leadgen/start` call goes.
- **STATUS_PAGE** — The subdomain page that shows the processing status tracker. After the API call succeeds, the user is redirected here with `?run_id=xxx&email=xxx` in the URL.

## 3. CORS — Allow the TLD to call the subdomain API

The landing page on `mapthegap.ai` makes a `fetch()` to `vizualizd.mapthegap.ai`. The browser will block this unless CORS headers are set on the backend.

In your FastAPI backend, update the CORS middleware to allow your marketing domain:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://mapthegap.ai",
        "https://www.mapthegap.ai",
        # keep any existing origins
    ],
    allow_credentials=True,
    allow_methods=["POST", "GET"],
    allow_headers=["Content-Type"],
)
```

If you already have a wildcard `"*"` origin, this is already handled — but explicit origins are better for production.

## 4. Update the subdomain status page to accept URL params

The subdomain `free-analysis.html` needs to pick up `run_id` and `email` from the URL when redirected from the TLD. Replace the `restore()` function at the bottom of the subdomain's script with:

```js
(function restore() {
    // Check URL params first (redirected from marketing site)
    var params = new URLSearchParams(window.location.search);
    var paramRunId = params.get('run_id');
    var paramEmail = params.get('email');

    if (paramRunId && paramEmail) {
        currentRunId = paramRunId;
        currentEmail = paramEmail;
        localStorage.setItem('leadgen_run_id', paramRunId);
        localStorage.setItem('leadgen_email', paramEmail);
        // Clean URL
        window.history.replaceState({}, '', window.location.pathname);
    }

    // Then check localStorage (page refresh / returning visitor)
    var savedRunId = localStorage.getItem('leadgen_run_id');
    var savedEmail = localStorage.getItem('leadgen_email');
    if (savedRunId && savedEmail) {
        currentRunId = savedRunId;
        currentEmail = savedEmail;
        document.getElementById('emailConfirm').textContent = savedEmail;
        showScreen('screen-processing');
        showModal();
        startPolling();
    }
})();
```

## Flow summary

```
mapthegap.ai/free-analysis (marketing site)
  │
  ├─ User enters URL → modal asks for email
  │
  ├─ POST to vizualizd.mapthegap.ai/api/public/leadgen/start
  │   (cross-origin, needs CORS)
  │
  └─ Redirect to vizualizd.mapthegap.ai/free-analysis?run_id=xxx&email=xxx
       │
       └─ Status tracker polls until complete
```
