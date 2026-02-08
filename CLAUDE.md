# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Static website for ARTEAH d.o.o., an architectural consulting and IT services company based in Varaždin, Croatia. Hosted on GitHub Pages at arteah.hr.

## Development

No build system. Open `index.html` directly in a browser to preview.

## Deployment

Site auto-deploys via GitHub Pages from the `master` branch. Push to `master` to deploy.

## Architecture

**Pure static site** - HTML, CSS, and vanilla JavaScript with no frameworks or dependencies.

### Pages
- `index.html` - Main company landing page (Croatian language)
- `eidolon.html` - Product page for Eidolon Riftbound mobile app (English)

### Styling
- `styles.css` - Single stylesheet with CSS custom properties in `:root`
- Mobile-first responsive design with breakpoint at 768px
- Uses Inter font from Google Fonts

### JavaScript
- `script.js` - Handles mobile menu toggle, hero carousel (5s interval), scroll effects, and section reveal animations via IntersectionObserver

### Assets
- `img/` - Hero carousel backgrounds and product images
- `CNAME` - GitHub Pages custom domain configuration
