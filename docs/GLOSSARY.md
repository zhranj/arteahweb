# Glossary

| Component | Purpose and use |
|---|---|
| Company page | `index.html` presents the company, professional services, products, and contact details. |
| Professional service notices | The `projektiranje` and `it` sections state B2B scope and pre-contract quotation terms. They do not cover the product section. |
| IT service cards | `Razvoj aplikacija` describes apps that automate tasks, connect data, and simplify work. `IT konzalting` invites companies to contact us for one free introductory hour and states more than ten years of AI experience. Keep one short paragraph per card without extra promotional headlines. |
| Company contact | The `kontakt` section shows the general company email address. Keep the displayed address and email button destination consistent. The app privacy contact is separate. |
| Product pages | `curvekeeper.html` and `curvekeeperMTG.html` describe the apps. `curvekeeper-privacy.html` gives their privacy information. |
| Stylesheet | `styles.css` defines the shared design. Reuse its text styles for service notices. |
| Interaction script | `script.js` controls navigation, the carousel, section reveal, and screenshot viewing. |
| Browser checks | `tests\test_business_notices.py` checks the actual pages and writes screenshots and JavaScript coverage. Run the command in `AGENTS.md`. |

Keep business quotations and compliance evidence outside this public repository.
