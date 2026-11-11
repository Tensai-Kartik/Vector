"""Anti-bot and CAPTCHA verification gate detection helpers."""

from typing import Dict, Any, Optional
from playwright.async_api import Page


async def detect_anti_bot_gate(page: Optional[Page]) -> Dict[str, Any]:
    """
    Detects whether the current browser page is gated by a CAPTCHA or anti-bot
    verification challenge (e.g., Google /sorry/ reCAPTCHA, hCaptcha, Cloudflare Turnstile).
    Does NOT attempt to solve or bypass the challenge.
    """
    if not page:
        return {"blocked": False}

    url = (getattr(page, "url", "") or "").lower()
    if any(pat in url for pat in ["/sorry/index", "google.com/sorry", "cdn-cgi/l/chk_captcha"]):
        return {
            "blocked": True,
            "kind": "recaptcha_gate",
            "url": page.url,
            "reason": (
                "Target site redirected to a human-verification / CAPTCHA gate "
                "(e.g., Google unusual-traffic check on shared cloud IP)."
            ),
        }

    # Dummy pages in unit tests may not have evaluate()
    evaluate_fn = getattr(page, "evaluate", None)
    if not callable(evaluate_fn):
        return {"blocked": False}

    try:
        hit = await page.evaluate("""() => {
            const url = (window.location.href || '').toLowerCase();
            if (url.includes('/sorry/') || url.includes('chk_captcha')) {
                return 'CAPTCHA verification page (/sorry/)';
            }
            const captchaSelectors = [
                'form[action*="sorry"]',
                '#captcha-form',
                'iframe[src*="recaptcha"]',
                '.g-recaptcha',
                '.h-captcha',
                '.cf-turnstile',
                '#cf-challenge-running'
            ];
            for (const sel of captchaSelectors) {
                const el = document.querySelector(sel);
                if (el && (el.offsetWidth > 0 || el.offsetHeight > 0 || document.body.innerText.length < 2500)) {
                    // Only treat embedded recaptcha as blocking gate when page has challenge copy or minimal content
                    const txt = (document.body ? document.body.innerText : '').slice(0, 1500).toLowerCase();
                    if (
                        sel === 'form[action*="sorry"]' ||
                        sel === '#captcha-form' ||
                        sel === '#cf-challenge-running' ||
                        txt.includes('unusual traffic') ||
                        txt.includes('not a robot') ||
                        txt.includes('verify you are human')
                    ) {
                        return 'Anti-bot challenge detected (' + sel + ')';
                    }
                }
            }
            const bodyText = (document.body ? document.body.innerText : '').slice(0, 2200).toLowerCase();
            const markers = [
                'unusual traffic from your computer network',
                'sending automated queries',
                "i'm not a robot",
                'verify you are human',
                'checking if the site connection is secure',
                "sign in to confirm you're not a bot",
                'sign in to confirm you\u2019re not a bot',
                "confirm you're not a bot",
                'confirm you\u2019re not a bot'
            ];
            for (const m of markers) {
                if (bodyText.includes(m)) {
                    return 'Anti-bot gate phrase detected: "' + m + '"';
                }
            }
            return null;
        }""")
        if hit:
            return {
                "blocked": True,
                "kind": "captcha_challenge",
                "url": getattr(page, "url", ""),
                "reason": (
                    f"{hit}. Automated agents cannot bypass CAPTCHA/human-verification gates. "
                    "Open the URL in your browser tab or run VECTOR locally to verify manually."
                ),
            }
    except Exception:
        pass

    return {"blocked": False}

