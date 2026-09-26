import json
import re
import unittest
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import expect, sync_playwright


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / ".test-output"
BUSINESS_SCOPE = "isključivo poslovnim korisnicima za potrebe njihove djelatnosti"
QUOTATION = (
    "Cijenu određujemo prema opsegu projekta. "
    "Opseg usluge, cijenu i uvjete plaćanja utvrđujemo pisanom ponudom "
    "prije sklapanja ugovora."
)


class BusinessNoticeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        OUTPUT.mkdir(exist_ok=True)
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(headless=True)
        cls.coverage_by_url = {
            source.as_uri(): bytearray(len(source.read_bytes().decode("utf-8").encode("utf-16-le")) // 2)
            for source in ROOT.glob("*.js")
        }
        cls.covered = cls.coverage_by_url[(ROOT / "script.js").as_uri()]

    @classmethod
    def tearDownClass(cls):
        summary = {
            "tool": "Chromium V8 precise coverage",
            "source": "script.js",
            "covered_utf16_units": sum(cls.covered),
            "total_utf16_units": len(cls.covered),
            "percent": round(100 * sum(cls.covered) / len(cls.covered), 2),
            "scripts": {
                url.rsplit("/", 1)[-1]: {
                    "covered_utf16_units": sum(covered),
                    "total_utf16_units": len(covered),
                    "percent": round(100 * sum(covered) / len(covered), 2),
                }
                for url, covered in cls.coverage_by_url.items()
            },
        }
        (OUTPUT / "browser-coverage.json").write_text(
            json.dumps(summary, indent=2) + "\n", encoding="utf-8"
        )
        print(f"\nBrowser JavaScript coverage: {summary['percent']}%")
        cls.browser.close()
        cls.playwright.stop()

    def setUp(self):
        self.context = self.browser.new_context(viewport={"width": 1440, "height": 1000})
        self.context.set_default_timeout(5000)
        self.page = self.context.new_page()
        self.errors = []
        self.page.on("pageerror", lambda error: self.errors.append(str(error)))
        self.cdp = self.context.new_cdp_session(self.page)
        self.cdp.send("Profiler.enable")
        self.cdp.send("Profiler.startPreciseCoverage", {"callCount": True, "detailed": True})
        self.page.goto((ROOT / "index.html").as_uri())

    def tearDown(self):
        self.collect_coverage()
        self.cdp.send("Profiler.stopPreciseCoverage")
        self.context.close()
        self.assertEqual(self.errors, [], "The real page must not raise JavaScript errors.")

    def collect_coverage(self):
        result = self.cdp.send("Profiler.takePreciseCoverage")
        for script in result["result"]:
            if script["url"] not in self.coverage_by_url:
                continue
            covered = self.coverage_by_url[script["url"]]
            executed = bytearray(len(covered))
            ranges = [item for function in script["functions"] for item in function["ranges"]]
            # Nested zero-count ranges override their executed parent range.
            for item in sorted(ranges, key=lambda item: item["endOffset"] - item["startOffset"], reverse=True):
                start, end = item["startOffset"], item["endOffset"]
                executed[start:end] = bytes([int(item["count"] > 0)]) * (end - start)
            for index, value in enumerate(executed):
                covered[index] |= value

    def test_ac1_ac2_each_service_has_business_scope_and_precontract_quotation(self):
        # Each section must carry its own notice, not rely on a company-wide claim.
        subjects = {
            "projektiranje": "Usluge projektiranja, organizacije i savjetovanja",
            "it": "Razvoj aplikacija po narudžbi, IT savjetovanje i tehničku podršku",
        }
        for section_id, subject in subjects.items():
            with self.subTest(section=section_id):
                section = self.page.locator(f"#{section_id}")
                expect(section.get_by_text(f"{subject} pružamo {BUSINESS_SCOPE}.", exact=True)).to_have_count(1)
                expect(section.get_by_text(QUOTATION, exact=True)).to_have_count(1)
                self.assertIsNone(re.search(r"€|\b(?:EUR|HRK|kn)\b|/\s*h\b", section.inner_text()),
                                  "Do not add public rates beside the quotation terms.")

    def test_ac3_scope_does_not_extend_to_the_company_or_apps(self):
        notices = self.page.get_by_text(BUSINESS_SCOPE, exact=False)
        expect(notices).to_have_count(2)
        expect(self.page.get_by_text(QUOTATION, exact=True)).to_have_count(2)
        self.assertEqual(
            notices.evaluate_all("(nodes) => nodes.map(node => node.closest('section')?.id).sort()"),
            ["it", "projektiranje"],
        )
        for section_id in ("o-nama", "products", "kontakt"):
            expect(self.page.locator(f"#{section_id}")).to_have_count(1)
            expect(self.page.locator(f"#{section_id}")).not_to_contain_text("isključivo poslovnim")
        for filename in ("curvekeeper.html", "curvekeeperMTG.html", "curvekeeper-privacy.html", "mojgradsmrdi.html"):
            with self.subTest(page=filename):
                self.collect_coverage()
                self.page.goto((ROOT / filename).as_uri())
                expect(self.page.locator("body")).not_to_contain_text("isključivo poslovnim")
                expect(self.page.locator("body")).not_to_contain_text(QUOTATION)
                if filename == "curvekeeper-privacy.html":
                    app_contacts = self.page.get_by_role("link", name="curvekeeper@arteah.hr", exact=True)
                    expect(app_contacts).to_have_count(2)
                    for app_contact in app_contacts.all():
                        expect(app_contact).to_have_attribute("href", "mailto:curvekeeper@arteah.hr")

    def test_ac4_notices_are_visible_on_mobile_and_desktop(self):
        for width in (375, 1440):
            self.page.set_viewport_size({"width": width, "height": 1000})
            for section_id in ("projektiranje", "it"):
                with self.subTest(width=width, section=section_id):
                    section = self.page.locator(f"#{section_id}")
                    notice = section.get_by_text(BUSINESS_SCOPE, exact=False)
                    notice.scroll_into_view_if_needed()
                    expect(section).to_have_css("opacity", "1")
                    expect(notice).to_be_visible()
                    expect(notice).to_be_in_viewport()
                    expect(section.get_by_text(QUOTATION, exact=True)).to_be_visible()
                    for paragraph in (notice, section.get_by_text(QUOTATION, exact=True)):
                        self.assertTrue(paragraph.evaluate("""element => {
                            for (let node = element; node; node = node.parentElement) {
                                const style = getComputedStyle(node);
                                if (Number(style.opacity) === 0 || style.visibility !== 'visible'
                                    || style.display === 'none') return false;
                            }
                            return getComputedStyle(element).color !== 'rgba(0, 0, 0, 0)'
                                && element.scrollWidth <= element.clientWidth
                                && element.scrollHeight <= element.clientHeight;
                        }"""), "The notice must not be transparent or clipped.")
                    self.assertTrue(self.page.evaluate(
                        "() => document.documentElement.scrollWidth <= window.innerWidth"
                    ), f"The page overflows at {width}px.")
                    section.evaluate("""section => window.scrollTo({
                        top: section.getBoundingClientRect().top + window.scrollY - 80,
                        behavior: 'instant'
                    })""")
                    self.page.screenshot(path=str(OUTPUT / f"{section_id}-{width}.png"), animations="disabled")

    def test_ac5_existing_cards_links_and_mobile_navigation_work(self):
        for section_id in ("projektiranje", "it"):
            expect(self.page.locator(f"#{section_id} .service-card")).to_have_count(2)
        links = self.page.locator("#products .product-card")
        self.assertEqual(links.evaluate_all("(nodes) => nodes.map(node => node.getAttribute('href'))"),
                         ["curvekeeper.html", "curvekeeperMTG.html", "mojgradsmrdi.html"])
        self.page.set_viewport_size({"width": 375, "height": 1000})
        button = self.page.get_by_role("button", name="Otvori ili zatvori izbornik")
        button.click()
        expect(self.page.locator(".nav-links")).to_have_class("nav-links active")
        self.page.locator(".nav-links").get_by_role("link", name="IT", exact=True).click()
        expect(self.page.locator(".nav-links")).to_have_class("nav-links")
        expect(self.page).to_have_url((ROOT / "index.html").as_uri() + "#it")
        expect(self.page.locator("#it")).to_have_css("opacity", "1")

    def test_company_contact_uses_the_general_inbox(self):
        # The displayed address and email action must agree.
        contact = self.page.locator("#kontakt")
        expect(contact.locator(".contact-info")).to_contain_text("kontakt@arteah.hr")
        expect(contact.get_by_role("link", name="Pošaljite email", exact=True)).to_have_attribute(
            "href", "mailto:kontakt@arteah.hr"
        )
        expect(self.page.locator("body")).not_to_contain_text("tea@arteah.hr")
        expect(self.page.locator('a[href="mailto:tea@arteah.hr"]')).to_have_count(0)

    def test_it_service_copy_is_short_scoped_and_visible(self):
        # Pin the approved benefits and free offer without adding promotional headlines.
        expect(self.page.locator("#it").get_by_role("heading")).to_have_text(
            ["IT usluge", "Razvoj aplikacija", "IT konzalting"]
        )
        descriptions = {
            "Razvoj aplikacija": (
                "development",
                "Razvijamo web, mobilne i desktop aplikacije prilagođene Vašem načinu rada. "
                "Automatizirajte zadatke, povežite podatke i olakšajte rad svojem timu i kupcima.",
            ),
            "IT konzalting": (
                "consulting",
                "Kontaktirajte nas za jedan sat besplatnog uvodnog savjetovanja za tvrtke. "
                "Uz više od deset godina iskustva u području umjetne inteligencije, "
                "pomažemo Vam otkriti kako automatizacija i AI mogu unaprijediti Vaše poslovanje.",
            ),
        }
        for title, (slug, text) in descriptions.items():
            with self.subTest(card=title):
                card = self.page.locator("#it .service-card").filter(
                    has=self.page.get_by_role("heading", name=title, exact=True)
                )
                expect(card).to_have_count(1)
                expect(card.locator(".service-icon svg")).to_have_count(1)
                expect(card.locator("p")).to_have_text([text])
                expect(card).to_have_text(f"{title} {text}")
                expect(self.page.get_by_text(text, exact=True)).to_have_count(1)
                for width in (375, 1440):
                    self.page.set_viewport_size({"width": width, "height": 1000})
                    card.scroll_into_view_if_needed()
                    expect(self.page.locator("#it")).to_have_css("opacity", "1")
                    card.evaluate("""card => window.scrollTo({
                        top: card.getBoundingClientRect().top + window.scrollY - 100,
                        behavior: 'instant'
                    })""")
                    expect(card).to_be_in_viewport(ratio=1)
                    paragraph = card.locator("p")
                    expect(paragraph).to_be_visible()
                    expect(paragraph).to_be_in_viewport(ratio=1)
                    self.assertTrue(paragraph.evaluate("""element => {
                        for (let node = element; node; node = node.parentElement) {
                            if (Number(getComputedStyle(node).opacity) === 0) return false;
                        }
                        return getComputedStyle(element).color !== 'rgba(0, 0, 0, 0)'
                            && element.scrollWidth <= element.clientWidth
                            && element.scrollHeight <= element.clientHeight;
                    }"""), f"The {title} text must not be transparent or clipped at {width}px.")
                    self.assertTrue(self.page.evaluate(
                        "() => document.documentElement.scrollWidth <= window.innerWidth"
                    ), f"The {title} card overflows at {width}px.")
                    self.page.screenshot(
                        path=str(OUTPUT / f"it-{slug}-{width}.png"), animations="disabled"
                    )

    def test_language_defaults_and_round_trip_on_every_page(self):
        pages = [
            ("index.html", "hr", "Umjetnost susreće arhitekturu", "Art Meets Architecture"),
            ("curvekeeper.html", "en", "Features", "Značajke"),
            ("curvekeeperMTG.html", "en", "Features", "Značajke"),
            ("curvekeeper-privacy.html", "en", "Privacy Policy", "Pravila privatnosti"),
            ("mojgradsmrdi.html", "en", "Free and anonymous odor reporting", "Besplatna i anonimna prijava mirisa"),
        ]
        for filename, default, original_heading, translated_heading in pages:
            with self.subTest(page=filename):
                self.collect_coverage()
                self.page.goto((ROOT / filename).as_uri())
                expect(self.page.locator("html")).to_have_attribute("lang", default)
                expect(self.page.get_by_role("heading", name=original_heading, exact=True)).to_have_count(1)
                original = self.page.locator("body").inner_text()
                links = self.page.locator("a").evaluate_all("(nodes) => nodes.map(n => n.getAttribute('href'))")
                sources = self.page.locator("img").evaluate_all("(nodes) => nodes.map(n => n.getAttribute('src'))")
                toggle = self.page.locator(".language-toggle")
                expect(toggle).to_be_visible()
                expect(toggle).to_have_text("HR / EN")
                toggle.click()
                other = "en" if default == "hr" else "hr"
                expect(self.page.locator("html")).to_have_attribute("lang", other)
                expect(self.page.get_by_role("heading", name=translated_heading, exact=True)).to_have_count(1)
                self.assertNotEqual(self.page.locator("body").inner_text(), original)
                self.assertEqual(self.page.locator("a").evaluate_all("(nodes) => nodes.map(n => n.getAttribute('href'))"), links)
                self.assertEqual(self.page.locator("img").evaluate_all("(nodes) => nodes.map(n => n.getAttribute('src'))"), sources)
                toggle.click()
                expect(self.page.locator("html")).to_have_attribute("lang", default)
                self.assertEqual(self.page.locator("body").inner_text(), original)

    def test_language_selection_preserves_filename_hash_and_page_defaults(self):
        self.page.goto((ROOT / "index.html").as_uri() + "#it")
        self.page.locator(".language-toggle").click()
        expect(self.page).to_have_url((ROOT / "index.html").as_uri() + "?lang=en#it")
        self.page.reload()
        expect(self.page.locator("html")).to_have_attribute("lang", "en")
        expect(self.page.locator("#it h2")).to_have_text("IT services")
        self.page.locator('#products a[href="curvekeeperMTG.html"]').click()
        expect(self.page).to_have_url((ROOT / "curvekeeperMTG.html").as_uri())
        expect(self.page.locator("html")).to_have_attribute("lang", "en")
        self.page.locator(".language-toggle").click()
        expect(self.page.locator("html")).to_have_attribute("lang", "hr")
        self.page.locator(".logo").click()
        expect(self.page).to_have_url((ROOT / "index.html").as_uri())
        expect(self.page.locator("html")).to_have_attribute("lang", "hr")

    def test_language_toggle_is_keyboard_accessible_and_fits_mobile(self):
        for filename in ("index.html", "curvekeeper.html", "curvekeeperMTG.html", "curvekeeper-privacy.html", "mojgradsmrdi.html"):
            for width in (375, 768, 1440):
                with self.subTest(page=filename, width=width):
                    self.collect_coverage()
                    self.page.set_viewport_size({"width": width, "height": 1000})
                    self.page.goto((ROOT / filename).as_uri())
                    for _ in range(2):
                        toggle = self.page.locator(".language-toggle")
                        expect(toggle).to_be_visible()
                        expect(toggle).to_be_in_viewport(ratio=1)
                        language = self.page.locator("html").get_attribute("lang")
                        expected_name = "HR / EN - Prebaci na engleski" if language == "hr" else "HR / EN - Switch to Croatian"
                        expect(toggle).to_have_accessible_name(expected_name)
                        self.assertTrue(self.page.evaluate(
                            "() => document.documentElement.scrollWidth <= window.innerWidth"
                        ), f"{filename} overflows at {width}px.")
                        self.page.screenshot(path=str(OUTPUT / f"{Path(filename).stem}-{language}-{width}.png"))
                        toggle.focus()
                        toggle.press("Enter")

    def test_mobile_menu_updates_language_without_losing_navigation(self):
        self.page.set_viewport_size({"width": 375, "height": 800})
        self.page.locator(".mobile-menu-btn").click()
        expect(self.page.locator(".nav-links")).to_be_visible()
        self.page.locator(".language-toggle").click()
        expect(self.page.locator(".nav-links a")).to_have_text(
            ["About us", "Architecture", "IT", "Products", "Contact"]
        )
        self.page.locator(".nav-links").get_by_role("link", name="Contact", exact=True).click()
        expect(self.page.locator(".nav-links")).to_be_hidden()
        expect(self.page).to_have_url((ROOT / "index.html").as_uri() + "?lang=en#kontakt")

    def test_unsupported_language_warns_and_keeps_the_page_default(self):
        warnings = []
        self.page.on("console", lambda message: warnings.append(message.text) if message.type == "warning" else None)
        self.page.goto((ROOT / "index.html").as_uri() + "?lang=de")
        expect(self.page.locator("html")).to_have_attribute("lang", "hr")
        self.assertTrue(any('Unsupported language "de"' in warning for warning in warnings))
        self.page.locator(".language-toggle").click()
        expect(self.page).to_have_url((ROOT / "index.html").as_uri() + "?lang=en")

    def test_english_company_copy_and_croatian_privacy_keep_their_meaning(self):
        self.page.goto((ROOT / "index.html").as_uri() + "?lang=en")
        expect(self.page.locator("#it")).to_contain_text("one free hour")
        expect(self.page.locator("#it")).to_contain_text("more than ten years")
        expect(self.page.locator("#it")).to_contain_text("business customers")
        expect(self.page.locator("#projektiranje")).to_contain_text("before the contract")
        expect(self.page.locator("#products")).not_to_contain_text("business customers")
        expect(self.page.locator("#kontakt")).to_contain_text("kontakt@arteah.hr")
        self.collect_coverage()
        self.page.goto((ROOT / "curvekeeper-privacy.html").as_uri() + "?lang=hr")
        expect(self.page.locator(".privacy-content h2")).to_have_count(16)
        expect(self.page.locator(".effective-date")).to_contain_text("2026-01-01")
        expect(self.page.locator(".privacy-content")).to_contain_text("Google AdMob")
        expect(self.page.locator(".privacy-content")).to_contain_text("13")
        expect(self.page.locator('a[href="mailto:curvekeeper@arteah.hr"]')).to_have_count(2)
        expect(self.page.get_by_role("heading", name="16) Kontakt", exact=True)).to_have_count(1)
        for clause in (
            "Ne prodajemo Vaše osobne podatke.",
            "Vi odlučujete hoćete li poslati poruku.",
            "nije namijenjena djeci mlađoj od 13 godina",
            "Nijedan način prijenosa ili pohrane nije 100% siguran.",
            "Pogodnost je neobvezna.",
        ):
            expect(self.page.locator(".privacy-content")).to_contain_text(clause)

    def test_all_language_bearing_text_and_attributes_are_registered(self):
        for filename in ("index.html", "curvekeeper.html", "curvekeeperMTG.html", "curvekeeper-privacy.html", "mojgradsmrdi.html"):
            with self.subTest(page=filename):
                self.collect_coverage()
                self.page.goto((ROOT / filename).as_uri())
                missing = self.page.evaluate(r"""() => {
                    const missing = [];
                    const walker = document.createTreeWalker(document.documentElement, NodeFilter.SHOW_TEXT);
                    while (walker.nextNode()) {
                        const node = walker.currentNode;
                        if (!/\p{L}/u.test(node.textContent)) continue;
                        const parent = node.parentElement;
                        if (parent.closest('script, style, [data-i18n], [translate="no"], .language-toggle')) continue;
                        missing.push(node.textContent.trim().slice(0, 100));
                    }
                    for (const [attribute, marker] of [
                        ['alt', 'data-i18n-alt'], ['aria-label', 'data-i18n-aria-label']
                    ]) {
                        for (const element of document.querySelectorAll(`[${attribute}]`)) {
                            if (element.matches('.language-toggle')) continue;
                            if (element.getAttribute(attribute) && !element.hasAttribute(marker)
                                && !element.closest('[translate="no"]')) {
                                missing.push(`${attribute}: ${element.getAttribute(attribute)}`);
                            }
                        }
                    }
                    const description = document.querySelector('meta[name="description"]');
                    if (!description?.hasAttribute('data-i18n-content')) missing.push('meta description');
                    for (const element of document.querySelectorAll('meta[property^="og:"], meta[name^="twitter:"]')) {
                        const name = element.getAttribute('property') || element.getAttribute('name');
                        if (/(title|description|alt)$/.test(name) && !element.hasAttribute('data-i18n-content')) {
                            missing.push(name);
                        }
                    }
                    return missing;
                }""")
                self.assertEqual(missing, [], "Unregistered text could remain in the wrong language.")
                original_metadata = self.page.locator('meta[name="description"]').get_attribute("content")
                self.page.locator(".language-toggle").click()
                self.assertNotEqual(
                    self.page.locator('meta[name="description"]').get_attribute("content"),
                    original_metadata,
                )

    def test_curvekeeper_free_message_is_prominent_and_keeps_release_status(self):
        for language, label in (("en", "Free app"), ("hr", "Besplatna aplikacija")):
            free_word = re.compile(r"\bfree\b" if language == "en" else r"\bbesplatn", re.I)
            with self.subTest(language=language, page="company"):
                self.collect_coverage()
                self.page.goto((ROOT / "index.html").as_uri() + "?lang=" + language)
                expect(self.page.locator("#products h2")).to_have_text(
                    "Free apps" if language == "en" else "Besplatne aplikacije"
                )
                for card in self.page.locator("#products .product-card").all():
                    card.scroll_into_view_if_needed()
                    expect(self.page.locator("#products")).to_have_css("opacity", "1")
                    expect(card.locator(".free-badge")).to_have_text(label)
                    expect(card.locator(".free-badge")).to_be_visible()
                    expect(card.locator("p")).to_contain_text(free_word)
                    for width in (375, 1440):
                        self.page.set_viewport_size({"width": width, "height": 1100})
                        card.locator(".free-badge").scroll_into_view_if_needed()
                        expect(card.locator(".free-badge")).to_be_in_viewport(ratio=1)
                        expect(card.locator(".free-badge")).to_have_css("opacity", "1")
                        expect(card.locator(".free-badge")).to_have_css("text-transform", "uppercase")
                expect(self.page.locator("#products .free-badge")).to_have_count(3)
                expect(self.page.locator('#products a[href="curvekeeper.html"] .coming-soon-badge')).to_have_text(
                    "Coming Soon" if language == "en" else "Uskoro"
                )
                expect(self.page.locator('#products a[href="curvekeeperMTG.html"] img.store-badge')).to_be_visible()
                expect(self.page.locator("body")).not_to_contain_text(re.compile(r"ad-free|ad free|bez oglasa", re.I))
            for filename in ("curvekeeper.html", "curvekeeperMTG.html"):
                with self.subTest(language=language, page=filename):
                    self.collect_coverage()
                    self.page.goto((ROOT / filename).as_uri() + "?lang=" + language)
                    hero = self.page.locator(".CurveKeeper-hero")
                    badge = hero.locator(".free-badge")
                    expect(badge).to_have_text(label)
                    expect(badge).to_be_visible()
                    expect(badge).to_have_css("font-weight", "700")
                    expect(hero.locator(".CurveKeeper-tagline")).to_contain_text(free_word)
                    expect(self.page).to_have_title(free_word)
                    self.assertRegex(self.page.locator('meta[name="description"]').get_attribute("content"),
                                     free_word)
                    expect(self.page.locator("body")).not_to_contain_text(re.compile(r"ad-free|ad free|bez oglasa", re.I))
                    for width in (375, 1440):
                        self.page.set_viewport_size({"width": width, "height": 1100})
                        badge.scroll_into_view_if_needed()
                        expect(badge).to_be_in_viewport(ratio=1)
                        expect(badge).to_have_css("opacity", "1")
                        expect(badge).to_have_css("text-transform", "uppercase")
                    if filename == "curvekeeper.html":
                        expect(hero.locator(".coming-soon-badge")).to_have_text("Coming Soon" if language == "en" else "Uskoro")
                    else:
                        expect(hero.locator(".coming-soon-badge")).to_have_text(
                            "Coming Soon to iOS App Store" if language == "en" else "Uskoro u trgovini App Store za iOS"
                        )
                        expect(hero.locator('a[href="https://play.google.com/store/apps/details?id=com.curvekeeper.mtg"]')).to_have_count(1)

    def test_mojgradsmrdi_product_directs_visitors_to_free_anonymous_reporting(self):
        # The card must open our product page, which must direct visitors to the real site.
        card = self.page.locator('#products a[href="mojgradsmrdi.html"]')
        expect(card).to_contain_text("Besplatna")
        expect(card).to_contain_text("anonimna")
        card.click()
        expect(self.page).to_have_url((ROOT / "mojgradsmrdi.html").as_uri())
        expect(self.page.locator("html")).to_have_attribute("lang", "en")
        for language in ("en", "hr"):
            with self.subTest(language=language):
                if language == "hr":
                    self.page.locator(".language-toggle").click()
                main = self.page.locator("main")
                description_words = re.compile(r"free.*anonymous" if language == "en" else r"besplatna.*anonimna", re.I)
                expect(self.page).to_have_title(description_words)
                self.assertRegex(self.page.locator('meta[name="description"]').get_attribute("content"), description_words)
                expect(main.get_by_role("heading", level=1)).to_have_text("MojGradSmrdi.hr")
                expect(main.locator(".free-badge")).to_have_text(
                    "Free app" if language == "en" else "Besplatna aplikacija"
                )
                expect(main.locator('h2[data-i18n="moj.tagline"]')).to_have_text(
                    "Free and anonymous odor reporting" if language == "en" else "Besplatna i anonimna prijava mirisa"
                )
                expect(main).to_contain_text("No account, name, or email required." if language == "en"
                                           else "Bez korisničkog računa, imena ili e-pošte.")
                expect(main).to_contain_text("approximate location" if language == "en" else "približnu lokaciju")
                visit = main.get_by_role("link", name="Visit mojgradsmrdi.hr" if language == "en" else "Posjetite mojgradsmrdi.hr", exact=True)
                expect(visit).to_have_attribute("href", "https://mojgradsmrdi.hr/")
                expect(visit).to_have_attribute("target", "_blank")
                expect(visit).to_have_attribute("rel", "noopener noreferrer")
                expect(main.locator('a[href="https://mojgradsmrdi.hr/privacy"]')).to_have_count(1)
                expect(main).not_to_contain_text(re.compile("no data|bez prikupljanja podataka", re.I))
                self.assertNotIn("\u2014", self.page.content())
                expect(main.locator("form, input, textarea")).to_have_count(0)
                for width in (375, 1440):
                    self.page.set_viewport_size({"width": width, "height": 1100})
                    expect(visit).to_be_visible()
                    expect(visit).to_be_in_viewport(ratio=1)
                    self.assertTrue(self.page.evaluate("document.documentElement.scrollWidth <= innerWidth"))
                    self.assertTrue(main.locator("h1").evaluate(
                        "element => element.getBoundingClientRect().height <= parseFloat(getComputedStyle(element).lineHeight) + 1"
                    ), "Keep the product name together without an orphaned final letter.")
                    self.page.screenshot(path=str(OUTPUT / f"mojgradsmrdi-product-{language}-{width}.png"))
        self.collect_coverage()
        self.page.goto((ROOT / "index.html").as_uri() + "?lang=en")
        expect(self.page.locator('#products a[href="mojgradsmrdi.html"]')).to_contain_text("Free and anonymous")

    def test_mojgradsmrdi_explains_technology_and_links_facebook(self):
        for language in ("en", "hr"):
            with self.subTest(language=language):
                self.collect_coverage()
                self.page.goto((ROOT / "mojgradsmrdi.html").as_uri() + "?lang=" + language)
                technology = self.page.locator(".product-technology")
                expect(technology.get_by_role("heading", name="How it works" if language == "en" else "Kako radi", exact=True)).to_have_count(1)
                expect(technology.locator("li")).to_have_count(4)
                for name in ("Next.js", "React", "TypeScript", "Leaflet", "OpenStreetMap", "PostgreSQL", "Open-Meteo"):
                    expect(technology).to_contain_text(name)
                expect(technology).to_contain_text("shifted before storage" if language == "en" else "pomiču prije pohrane")
                expect(technology).to_contain_text("report limits" if language == "en" else "ograničenja prijava")
                facebook = self.page.get_by_role("link", name="Follow on Facebook" if language == "en" else "Pratite na Facebooku", exact=True)
                expect(facebook).to_have_attribute("href", "https://www.facebook.com/profile.php?id=61594654555021")
                expect(facebook).to_have_attribute("target", "_blank")
                expect(facebook).to_have_attribute("rel", "noopener noreferrer")
                expect(facebook).to_be_visible()

    def test_mojgradsmrdi_reuses_brand_assets_and_share_metadata(self):
        image_root = "img/mojgradsmrdi/"
        profile_path = image_root + "mojgradsmrdi-facebook-profile.png"
        cover_path = image_root + "mojgradsmrdi-facebook-cover.png"
        origin = "https://" + (ROOT / "CNAME").read_text(encoding="utf-8").strip()
        share_url = origin + "/img/mojgradsmrdi/varazdin-map-v4.png"
        card_image = self.page.locator('#products a[href="mojgradsmrdi.html"] img')
        expect(card_image).to_have_attribute("src", profile_path)
        expect(card_image).to_have_attribute("width", "1024")
        expect(card_image).to_have_attribute("height", "1024")
        self.assertEqual(card_image.evaluate("image => [image.naturalWidth, image.naturalHeight]"), [1024, 1024])
        self.collect_coverage()
        self.page.goto((ROOT / "mojgradsmrdi.html").as_uri())
        for language in ("en", "hr"):
            with self.subTest(language=language):
                if language == "hr":
                    self.page.locator(".language-toggle").click()
                cover = self.page.locator(".product-cover img")
                expect(cover).to_have_attribute("src", cover_path)
                expect(cover).to_have_attribute("width", "1640")
                expect(cover).to_have_attribute("height", "720")
                self.assertEqual(cover.evaluate("image => [image.naturalWidth, image.naturalHeight]"), [1640, 720])
                expect(cover).to_have_attribute("alt", "MojGradSmrdi promotional map illustration with fictional reports."
                                               if language == "en" else "Promotivna ilustracija karte MojGradSmrdi s izmišljenim prijavama.")
                caption = "Promotional illustration. The reports shown are fictional, not live data." if language == "en" else "Promotivna ilustracija. Prikazane prijave su izmišljene, a ne podaci uživo."
                expect(self.page.locator(".product-cover figcaption")).to_have_text(caption)
                for word in (("type", "intensity", "duration", "no unpleasant smell") if language == "en"
                             else ("vrstu", "jačinu", "trajanje", "nema neugodnog mirisa")):
                    expect(self.page.locator('[data-i18n="moj.details"]')).to_contain_text(word)
                expect(self.page.locator('meta[property="og:image"]')).to_have_attribute("content", share_url)
                expect(self.page.locator('meta[property="og:url"]')).to_have_attribute("content", origin + "/mojgradsmrdi.html")
                expect(self.page.locator('meta[name="twitter:image"]')).to_have_attribute("content", share_url)
                expect(self.page.locator('meta[property="og:image:width"]')).to_have_attribute("content", "1200")
                expect(self.page.locator('meta[property="og:image:height"]')).to_have_attribute("content", "630")
                expect(self.page.locator('meta[name="twitter:card"]')).to_have_attribute("content", "summary_large_image")
                title = "MojGradSmrdi.hr - Free and anonymous odor reporting | ARTEAH" if language == "en" else "MojGradSmrdi.hr - Besplatna i anonimna prijava mirisa | ARTEAH"
                for selector in ('meta[property="og:title"]', 'meta[name="twitter:title"]'):
                    expect(self.page.locator(selector)).to_have_attribute("content", title)
                for selector in ('meta[property="og:image:alt"]', 'meta[name="twitter:image:alt"]'):
                    expect(self.page.locator(selector)).to_have_attribute("content", re.compile("fictional" if language == "en" else "izmišljen"))
                for width in (375, 1440):
                    self.page.set_viewport_size({"width": width, "height": 1100})
                    cover.scroll_into_view_if_needed()
                    expect(cover).to_be_visible()
                    bounds = cover.bounding_box()
                    self.assertAlmostEqual(bounds["width"] / bounds["height"], 1640 / 720, delta=0.01)
                    self.assertTrue(self.page.evaluate("document.documentElement.scrollWidth <= innerWidth"))
        actual_share_url = self.page.locator('meta[property="og:image"]').get_attribute("content")
        share_file = ROOT.joinpath(*urlsplit(actual_share_url).path.lstrip("/").split("/"))
        data = share_file.read_bytes()
        self.assertEqual(data[:8], b"\x89PNG\r\n\x1a\n")
        self.assertEqual((int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")), (1200, 630))

    def test_product_descriptions_use_clear_sentences_without_em_dashes(self):
        # Read rendered text so literal characters and HTML entities are both checked.
        for filename, prefix in (("curvekeeper.html", "runes"), ("curvekeeperMTG.html", "mtg")):
            for language in ("en", "hr"):
                with self.subTest(page=filename, language=language):
                    self.collect_coverage()
                    self.page.goto((ROOT / filename).as_uri() + "?lang=" + language)
                    expect(self.page.locator("html")).to_have_attribute("lang", language)
                    expect(self.page.locator(".feature-block")).to_have_count(8)
                    expect(self.page.locator("body")).not_to_contain_text("\u2014")
                    self.assertNotIn("\u2014", self.page.content(), "Text attributes must also be free of em-dashes.")
                    turn = self.page.locator(f'[data-i18n="{prefix}.turnTracking"]')
                    completion = self.page.locator(f'[data-i18n="{prefix}.setCompletion"]')
                    progress = self.page.locator(f'[data-i18n="{prefix}.setProgress"]')
                    for phrase in (("turn number", "match results") if language == "en"
                                   else ("redni broj poteza", "rezultate meča")):
                        expect(turn).to_contain_text(phrase)
                    for phrase in (("rarities", "foil", "copies") if language == "en"
                                   else ("rijetkosti", "foil", "primjeraka")):
                        expect(completion).to_contain_text(phrase)
                    expect(progress).to_contain_text("up to three trackers" if language == "en" else "do tri praćenja")
                    expect(progress).to_contain_text("automatically" if language == "en" else "automatski")
                    expect(progress).to_contain_text("Cardmarket")
                    if prefix == "mtg":
                        expect(progress).to_contain_text("TCGPlayer")
                    else:
                        expect(progress).not_to_contain_text("TCGPlayer")

    def test_product_lightbox_localizes_controls_and_image_descriptions(self):
        for filename in ("curvekeeper.html", "curvekeeperMTG.html"):
            with self.subTest(page=filename):
                self.collect_coverage()
                self.page.goto((ROOT / filename).as_uri() + "?lang=hr")
                expect(self.page.locator(".legal-notice")).to_contain_text("Bez službene povezanosti")
                expect(self.page.locator(".privacy-notice")).to_contain_text("Osobni podaci ne šalju se ni na jedan poslužitelj")
                source = "javnog API-ja tvrtke Riot Games" if filename == "curvekeeper.html" else "javnog API-ja platforme Scryfall"
                expect(self.page.locator(".data-grid")).to_contain_text(source)
                images = self.page.locator(".feature-screenshots").first.locator("img")
                images.first.click()
                expect(self.page.locator(".lightbox-overlay")).to_have_class("lightbox-overlay active")
                expect(self.page.get_by_role("button", name="Zatvori", exact=True)).to_be_visible()
                expect(images.first).to_have_attribute("alt", "Prikaz kamere s kartom")
                expect(self.page.locator(".lightbox-image")).to_have_attribute("alt", "Prikaz kamere s kartom")
                self.page.get_by_role("button", name="Sljedeća", exact=True).click()
                expect(self.page.locator(".lightbox-counter")).to_have_text("2 / 3")
                self.page.get_by_role("button", name="Prethodna", exact=True).click()
                expect(self.page.locator(".lightbox-counter")).to_have_text("1 / 3")
                self.page.keyboard.press("ArrowLeft")
                expect(self.page.locator(".lightbox-counter")).to_have_text("3 / 3")
                self.page.keyboard.press("ArrowRight")
                expect(self.page.locator(".lightbox-counter")).to_have_text("1 / 3")
                self.page.keyboard.press("Escape")
                expect(self.page.locator(".lightbox-overlay")).not_to_have_class("lightbox-overlay active")
                self.page.locator(".language-toggle").click()
                images.first.click()
                expect(self.page.get_by_role("button", name="Close", exact=True)).to_be_visible()
                expect(self.page.locator(".lightbox-image")).to_have_attribute("alt", "Camera view with card")
                self.page.get_by_role("button", name="Close", exact=True).click()

    def test_bare_page_defaults_work_without_javascript(self):
        context = self.browser.new_context(java_script_enabled=False)
        try:
            page = context.new_page()
            for filename, language, heading in (
                ("index.html", "hr", "Umjetnost susreće arhitekturu"),
                ("curvekeeper.html", "en", "Features"),
                ("curvekeeperMTG.html", "en", "Features"),
                ("curvekeeper-privacy.html", "en", "Privacy Policy"),
                ("mojgradsmrdi.html", "en", "Free and anonymous odor reporting"),
            ):
                with self.subTest(page=filename):
                    page.goto((ROOT / filename).as_uri())
                    expect(page.locator("html")).to_have_attribute("lang", language)
                    expect(page.get_by_role("heading", name=heading, exact=True)).to_be_visible()
                    expect(page.locator(".language-toggle")).to_be_hidden()
        finally:
            context.close()

    def test_default_html_matches_its_translations_without_javascript(self):
        # This checks source consistency; literal assertions above check translation meaning.
        context = self.browser.new_context(java_script_enabled=False)
        try:
            source_page = context.new_page()
            for filename in ("index.html", "curvekeeper.html", "curvekeeperMTG.html", "curvekeeper-privacy.html", "mojgradsmrdi.html"):
                with self.subTest(page=filename):
                    source_page.goto((ROOT / filename).as_uri())
                    language = source_page.locator("html").get_attribute("lang")
                    entries = source_page.evaluate("""() => {
                        const entries = [];
                        for (const [marker, attribute] of [
                            ['data-i18n', null], ['data-i18n-alt', 'alt'],
                            ['data-i18n-content', 'content'], ['data-i18n-aria-label', 'aria-label']
                        ]) {
                            for (const element of document.querySelectorAll(`[${marker}]`)) {
                                entries.push({key: element.getAttribute(marker),
                                    value: attribute ? element.getAttribute(attribute) : element.textContent});
                            }
                        }
                        return entries;
                    }""")
                    self.collect_coverage()
                    self.page.goto((ROOT / filename).as_uri())
                    translations = self.page.evaluate("window.siteTranslations")
                    for entry in entries:
                        with self.subTest(key=entry["key"]):
                            self.assertEqual(
                                " ".join(entry["value"].split()),
                                " ".join(translations[entry["key"]][language].split()),
                                "Default HTML and runtime translation disagree.",
                            )
        finally:
            context.close()


if __name__ == "__main__":
    unittest.main()
