# ARTEAH website

Read `docs\GLOSSARY.md` before changing a component.
The site uses static HTML, CSS, and JavaScript. It has no production dependencies or build step.

## Scope

Keep the professional service notices in their architectural and IT sections.
Do not describe CurveKeeper apps or the whole company as B2B-only.
Do not publish negotiated rates, customer records, or internal quotation guidance.
Use the existing design and Croatian text for the company page.

## Board and records

Board: `C:\Users\zoran\OneDrive\Obsidian\WorkItems\Work Items\arteahweb KANBAN.md`.
Edit cards through the loopme `kanban.mjs` script.
Store task records, research, and reports under `Z:\Research\arteahweb\`.
Keep these records outside the public website repository.

## Browser checks

Install test dependencies with `python -m pip install -r requirements-test.txt`.
Install the browser with `python -m playwright install chromium`.
Run `python -m unittest discover -s tests -v`.

The same command collects Chromium V8 precise coverage for `script.js`.
It writes the summary and service screenshots to the ignored `.test-output\` directory.
The coverage percentage measures executed JavaScript source ranges, not HTML or CSS.
Browser assertions and inspected screenshots cover the service text and layout.

## Delivery

Keep one card per commit. Include the card ID and the Copilot co-author trailer.
Preserve the `origin` and `athena` remotes.
A push to the GitHub Pages source branch can deploy the site. Do not push without approval.
