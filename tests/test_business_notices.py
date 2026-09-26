import json
import re
import unittest
from pathlib import Path

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
        cls.covered = bytearray(
            len((ROOT / "script.js").read_bytes().decode("utf-8").encode("utf-16-le")) // 2
        )

    @classmethod
    def tearDownClass(cls):
        summary = {
            "tool": "Chromium V8 precise coverage",
            "source": "script.js",
            "covered_utf16_units": sum(cls.covered),
            "total_utf16_units": len(cls.covered),
            "percent": round(100 * sum(cls.covered) / len(cls.covered), 2),
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
            if script["url"] != (ROOT / "script.js").as_uri():
                continue
            executed = bytearray(len(self.covered))
            ranges = [item for function in script["functions"] for item in function["ranges"]]
            # Nested zero-count ranges override their executed parent range.
            for item in sorted(ranges, key=lambda item: item["endOffset"] - item["startOffset"], reverse=True):
                start, end = item["startOffset"], item["endOffset"]
                executed[start:end] = bytes([int(item["count"] > 0)]) * (end - start)
            for index, value in enumerate(executed):
                self.covered[index] |= value

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
        for filename in ("curvekeeper.html", "curvekeeperMTG.html", "curvekeeper-privacy.html"):
            with self.subTest(page=filename):
                self.collect_coverage()
                self.page.goto((ROOT / filename).as_uri())
                expect(self.page.locator("body")).not_to_contain_text("isključivo poslovnim")
                expect(self.page.locator("body")).not_to_contain_text(QUOTATION)

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
                         ["curvekeeper.html", "curvekeeperMTG.html"])
        self.page.set_viewport_size({"width": 375, "height": 1000})
        button = self.page.get_by_role("button", name="Toggle menu")
        button.click()
        expect(self.page.locator(".nav-links")).to_have_class("nav-links active")
        self.page.locator(".nav-links").get_by_role("link", name="IT", exact=True).click()
        expect(self.page.locator(".nav-links")).to_have_class("nav-links")
        expect(self.page).to_have_url((ROOT / "index.html").as_uri() + "#it")
        expect(self.page.locator("#it")).to_have_css("opacity", "1")

    def test_it_consulting_offers_companies_one_free_hour_with_ai_experience(self):
        # Keep the free discovery offer in consulting, not in the app or architecture offers.
        paragraphs = [
            "Savjetovanje i tehnička podrška za digitalizaciju Vašeg poslovanja.",
            "Tvrtkama nudimo jedan sat besplatnog uvodnog savjetovanja za istraživanje "
            "mogućnosti razvoja poslovanja, s posebnim naglaskom na primjenu umjetne "
            "inteligencije (AI).",
            "Imamo više od deset godina iskustva u području umjetne inteligencije.",
        ]
        card = self.page.locator("#it .service-card").filter(
            has=self.page.get_by_role("heading", name="IT konzalting", exact=True)
        )
        expect(card).to_have_count(1)
        expect(card.locator("p")).to_have_text(paragraphs)
        for text in paragraphs[1:]:
            expect(self.page.get_by_text(text, exact=True)).to_have_count(1)
        for width in (375, 1440):
            with self.subTest(width=width):
                self.page.set_viewport_size({"width": width, "height": 1000})
                card.scroll_into_view_if_needed()
                expect(self.page.locator("#it")).to_have_css("opacity", "1")
                card.evaluate("""card => window.scrollTo({
                    top: card.getBoundingClientRect().top + window.scrollY - 100,
                    behavior: 'instant'
                })""")
                expect(card).to_be_in_viewport(ratio=1)
                for paragraph in card.locator("p").all():
                    expect(paragraph).to_be_visible()
                    expect(paragraph).to_be_in_viewport(ratio=1)
                    self.assertTrue(paragraph.evaluate("""element => {
                        for (let node = element; node; node = node.parentElement) {
                            if (Number(getComputedStyle(node).opacity) === 0) return false;
                        }
                        return getComputedStyle(element).color !== 'rgba(0, 0, 0, 0)'
                            && element.scrollWidth <= element.clientWidth
                            && element.scrollHeight <= element.clientHeight;
                    }"""), "The consulting text must not be transparent or clipped.")
                self.assertTrue(self.page.evaluate(
                    "() => document.documentElement.scrollWidth <= window.innerWidth"
                ), f"The consulting card overflows at {width}px.")
                self.page.screenshot(
                    path=str(OUTPUT / f"it-consulting-{width}.png"), animations="disabled"
                )


if __name__ == "__main__":
    unittest.main()
