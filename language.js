(() => {
    const supportedLanguages = ['hr', 'en'];
    const defaultLanguage = document.documentElement.lang;
    if (!supportedLanguages.includes(defaultLanguage)) {
        throw new Error(`Unsupported page language: ${defaultLanguage}`);
    }

    const toggle = document.querySelector('.language-toggle');
    const targets = [
        ['data-i18n', null],
        ['data-i18n-alt', 'alt'],
        ['data-i18n-content', 'content'],
        ['data-i18n-aria-label', 'aria-label']
    ];

    function requestedLanguage() {
        const requested = new URL(window.location.href).searchParams.get('lang');
        if (requested && !supportedLanguages.includes(requested)) {
            console.warn(`Unsupported language "${requested}"; using the page default.`);
        }
        return supportedLanguages.includes(requested) ? requested : defaultLanguage;
    }

    function applyLanguage(language) {
        const updates = [];
        targets.forEach(([marker, attribute]) => {
            document.querySelectorAll(`[${marker}]`).forEach(element => {
                const key = element.getAttribute(marker);
                const text = window.siteTranslations[key]?.[language];
                if (typeof text !== 'string' || !text) {
                    throw new Error(`Missing ${language} translation: ${key}`);
                }
                updates.push({ element, attribute, text });
            });
        });
        updates.forEach(({ element, attribute, text }) => {
            if (attribute) {
                element.setAttribute(attribute, text);
            } else {
                element.textContent = text;
            }
        });
        document.documentElement.lang = language;
        toggle.setAttribute('aria-label', language === 'hr' ? 'HR / EN - Prebaci na engleski' : 'HR / EN - Switch to Croatian');
        document.dispatchEvent(new Event('languagechange'));
    }

    toggle.addEventListener('click', () => {
        const language = document.documentElement.lang === 'hr' ? 'en' : 'hr';
        applyLanguage(language);
        const url = new URL(window.location.href);
        url.searchParams.set('lang', language);
        window.history.replaceState(window.history.state, '', url);
    });
    window.addEventListener('popstate', () => applyLanguage(requestedLanguage()));
    applyLanguage(requestedLanguage());
    toggle.hidden = false;
})();
