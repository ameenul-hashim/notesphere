# NoteSphere Loading Page

Animated branded loading page that shows while the Render app cold-starts, then redirects to the app.

## How it works

1. User opens this page (hosted on GitHub Pages - always on, loads instantly)
2. Sees the animated "NoteSphere" brand + loader
3. The page polls the Render app every 3 seconds
4. When the app responds (cold start done), it redirects to the app

## Deploy to GitHub Pages

### Option A: Separate repo (recommended)

1. Create a new GitHub repo (e.g. `notesphere-loading`)
2. Upload `index.html` and `.nojekyll` to it
3. Go to repo **Settings → Pages**
4. Under **Source**, select `main` branch and `/ (root)` folder
5. Save - your site is live at `https://<username>.github.io/notesphere-loading/`

### Option B: Same repo, `gh-pages` branch

1. Create a branch `gh-pages` containing only `index.html` and `.nojekyll`
2. Go to repo **Settings → Pages**
3. Select `gh-pages` branch and `/ (root)` folder

## Update the app URL

In `index.html`, change this line to your actual Render URL:

```js
const APP_URL = "https://notesphere-4rlw.onrender.com";
```

## Give users this URL

Share the GitHub Pages URL (e.g. `https://ameenul-hashim.github.io/notesphere-loading/`) instead of the Render URL directly. Users see the animation during cold start, then get redirected to the app.
