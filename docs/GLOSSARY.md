# Glossary

| Component | Purpose and use |
|---|---|
| Company page | `index.html` presents the company, professional services, products, and contact details. |
| Professional service notices | The `projektiranje` and `it` sections state B2B scope and pre-contract quotation terms. They do not cover the product section. |
| IT service cards | `Razvoj aplikacija` describes apps that automate tasks, connect data, and simplify work. `IT konzalting` invites companies to contact us for one free introductory hour and states more than ten years of AI experience. Keep one short paragraph per card without extra promotional headlines. |
| Company contact | The `kontakt` section shows the general company email address. Keep the displayed address and email button destination consistent. The app privacy contact is separate. |
| Product pages | `curvekeeper.html` and `curvekeeperMTG.html` describe the apps. Use clear sentences without em-dashes in both languages. `curvekeeper-privacy.html` gives their privacy information. |
| Free apps | Both CurveKeeper apps are free. Show Free / Besplatno prominently on company product cards and product heroes, with matching descriptions and metadata. Preserve release status and do not imply ad-free use. |
| Languages | `index.html` defaults to HR; both product pages and the privacy page default to EN. Keep these filenames. The menu button sets `?lang=hr` or `?lang=en` on the current URL and preserves its hash. Bare navigation links use the target page's default, not a stored preference. |
| Translations | `language.js` applies HR/EN pairs from `translations.js`, with product and privacy dictionaries loaded only on their pages. Mark text-only elements with `data-i18n`; use `data-i18n-alt`, `data-i18n-content`, and `data-i18n-aria-label` for attributes. Keep source HTML in its default language so it works without JavaScript. |
| Unchanged text | Use `translate="no"` only for proper names, addresses, platform names, and fixed identifiers. Preserve image files, links, and legal meaning. Text inside existing screenshots and store badges is not edited; their alternative text is translated. |
| Stylesheet | `styles.css` defines the shared design. Reuse its text styles for service notices. |
| Interaction script | `script.js` controls navigation, the carousel, section reveal, and screenshot viewing. |
| Browser checks | `tests\test_business_notices.py` checks the actual pages in both languages and writes screenshots and per-file JavaScript coverage. Missing translation markers and missing dictionary entries fail the checks. Run the command in `AGENTS.md`. |

Keep business quotations and compliance evidence outside this public repository.
