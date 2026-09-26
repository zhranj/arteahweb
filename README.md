# ARTEAH d.o.o. Website

Official website for ARTEAH d.o.o. — architectural consulting and IT services company based in Varaždin, Croatia.

## Local Development

Simply open `index.html` in a browser to preview the site.

The top-menu **HR / EN** button changes the current page language.
`index.html` defaults to Croatian. `curvekeeper.html`, `curvekeeperMTG.html`, `mojgradsmrdi.html`,
and `curvekeeper-privacy.html` default to English.
An explicit `?lang=hr` or `?lang=en` keeps the selected language on reload.
Existing filenames and navigation links stay unchanged. No shared language
preference overrides the default of another page.

The MojGradSmrdi product page gives a short introduction and links to
`https://mojgradsmrdi.hr/` for free anonymous odor reporting.

### Browser checks

These tools are for tests only. The website still needs no build step.

```powershell
python -m pip install -r requirements-test.txt
python -m playwright install chromium
python -m unittest discover -s tests -v
```

The checks cover service notices, HR/EN translation, per-page defaults, mobile layout,
metadata, product links, contact addresses, privacy terms, and lightbox controls.
They save screenshots and Chromium V8 JavaScript coverage in `.test-output\`.
See `AGENTS.md` for the workflow and `docs\GLOSSARY.md` for the components.

## Deployment to GitHub Pages

### 1. Push to GitHub

```bash
git add .
git commit -m "Initial Arteah website"
git remote add origin https://github.com/YOUR-USERNAME/arteahweb.git
git push -u origin main
```

### 2. Enable GitHub Pages

1. Go to your repository on GitHub
2. Navigate to **Settings** → **Pages**
3. Under "Source", select **Deploy from a branch**
4. Choose **main** branch and **/ (root)** folder
5. Click **Save**

Your site will be live at `https://YOUR-USERNAME.github.io/arteahweb/`

### 3. Configure Custom Domain (Optional)

#### In GitHub:
1. On the same Pages settings page, enter your domain under "Custom domain" (e.g., `arteah.hr`)
2. Check **Enforce HTTPS**
3. Create a `CNAME` file in the repo root containing your domain name

#### DNS Settings at Your Registrar:

For **apex domain** (e.g., `arteah.hr`), add A records pointing to:
```
185.199.108.153
185.199.109.153
185.199.110.153
185.199.111.153
```

For **www subdomain**, add a CNAME record:
```
www  →  YOUR-USERNAME.github.io
```

> **Note:** DNS propagation can take up to 24-48 hours.

## Project Structure

```
arteahweb/
├── index.html      # Main HTML file
├── styles.css      # Stylesheet
├── script.js       # JavaScript (carousel, mobile menu, animations)
├── img/            # Images for hero carousel
└── README.md       # This file
```

## License

© 2026 ARTEAH d.o.o. All rights reserved.
