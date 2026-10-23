from typing import List, Dict, Any, Optional
from urllib.parse import urlparse
import re
from playwright.async_api import Page
from app.models.inspector import PageObservation, ElementObservation

SENSITIVE_FIELD_PATTERNS = ["password", "secret", "token", "ssn", "cvv", "creditcard", "auth", "api_key"]

class DOMInspector:
    """
    Playwright-based DOM inspector that extracts structured, bounded,
    accessibility-focused observations from the live browser state.
    """

    @staticmethod
    def is_sensitive_name(name_or_id: Optional[str]) -> bool:
        if not name_or_id:
            return False
        clean = name_or_id.lower().replace("-", "").replace("_", "")
        return any(pat in clean for pat in SENSITIVE_FIELD_PATTERNS)

    @staticmethod
    async def inspect_page(page: Page, max_elements: int = 60) -> PageObservation:
        url = page.url
        title = await page.title()
        domain = urlparse(url).netloc

        # Run client-side extraction script in browser context
        script = """
        () => {
            const results = [];
            const interactiveSelectors = [
                'button',
                'a[href]',
                'input',
                'select',
                'textarea',
                '[role="button"]',
                '[role="link"]',
                '[role="checkbox"]',
                '[role="menuitem"]',
                '[role="tab"]'
            ];

            const elements = document.querySelectorAll(interactiveSelectors.join(','));
            const headings = Array.from(document.querySelectorAll('h1, h2, h3'))
                                 .map(h => (h.innerText || '').trim())
                                 .filter(t => t.length > 0 && t.length < 100)
                                 .slice(0, 10);

            const hasForms = document.querySelectorAll('form').length > 0;

            for (let el of elements) {
                if (results.length >= 80) break;

                const rect = el.getBoundingClientRect();
                const style = window.getComputedStyle(el);
                const isVisible = !!(rect.width > 0 && rect.height > 0 && style.visibility !== 'hidden' && style.display !== 'none');

                if (!isVisible) continue;

                const tagName = el.tagName.toLowerCase();
                const role = el.getAttribute('role') || (tagName === 'button' ? 'button' : (tagName === 'a' ? 'link' : (tagName === 'input' ? 'textbox' : '')));
                const id = el.id || '';
                const nameAttr = el.getAttribute('name') || '';
                const placeholder = el.getAttribute('placeholder') || '';
                const inputType = el.getAttribute('type') || (tagName === 'input' ? 'text' : '');
                const rawText = (el.innerText || el.textContent || '').trim().replace(/\\s+/g, ' ');
                const text = rawText.length > 80 ? rawText.slice(0, 77) + '...' : rawText;
                const isEnabled = !el.disabled;
                const isEditable = (tagName === 'input' || tagName === 'textarea') && !el.readOnly && !el.disabled;

                // Candidate preferred selector
                let selector = '';
                if (id) {
                    selector = '#' + CSS.escape(id);
                } else if (nameAttr) {
                    selector = `${tagName}[name="${nameAttr}"]`;
                } else if (placeholder) {
                    selector = `${tagName}[placeholder="${placeholder}"]`;
                } else if (role && text && text.length < 40) {
                    selector = `role=${role}[name="${text}"]`;
                } else if (text && text.length < 30) {
                    selector = `text="${text}"`;
                } else {
                    selector = `${tagName}.${Array.from(el.classList).slice(0, 2).join('.')}`;
                }

                // Options if select
                let options = [];
                if (tagName === 'select') {
                    options = Array.from(el.querySelectorAll('option')).map(o => (o.value || o.text).trim()).slice(0, 10);
                }

                // Attributes
                const attributes = {};
                for (let attr of el.attributes) {
                    if (['id', 'name', 'class', 'href', 'type', 'aria-label', 'data-testid'].includes(attr.name)) {
                        attributes[attr.name] = attr.value;
                    }
                }

                results.push({
                    selector,
                    tagName,
                    role,
                    name: el.getAttribute('aria-label') || nameAttr || text || '',
                    text,
                    placeholder,
                    inputType,
                    value: (tagName === 'input' || tagName === 'textarea') ? el.value : null,
                    isVisible,
                    isEnabled,
                    isEditable,
                    options,
                    attributes,
                    boundingBox: {
                        x: rect.x,
                        y: rect.y,
                        width: rect.width,
                        height: rect.height
                    }
                });
            }

            return {
                headings,
                hasForms,
                elements: results
            };
        }
        """

        raw_data = await page.evaluate(script)

        # Count occurrences of candidate selectors to compute uniqueness
        selector_counts: Dict[str, int] = {}
        for item in raw_data["elements"]:
            s = item["selector"]
            selector_counts[s] = selector_counts.get(s, 0) + 1

        element_obs_list: List[ElementObservation] = []
        for item in raw_data["elements"][:max_elements]:
            s = item["selector"]
            val = item.get("value")
            # Redact sensitive field values
            if DOMInspector.is_sensitive_name(item.get("name")) or DOMInspector.is_sensitive_name(item.get("placeholder")) or item.get("inputType") == "password":
                val = "[REDACTED_SENSITIVE]"

            obs = ElementObservation(
                selector=s,
                tag_name=item["tagName"],
                role=item.get("role") or None,
                name=item.get("name") or None,
                text=item.get("text") or None,
                placeholder=item.get("placeholder") or None,
                input_type=item.get("inputType") or None,
                value=val,
                is_visible=item.get("isVisible", True),
                is_enabled=item.get("isEnabled", True),
                is_editable=item.get("isEditable", False),
                options=item.get("options", []),
                attributes=item.get("attributes", {}),
                uniqueness_count=selector_counts.get(s, 1),
                bounding_box=item.get("boundingBox")
            )
            element_obs_list.append(obs)

        return PageObservation(
            url=url,
            title=title,
            domain=domain,
            interactive_elements=element_obs_list,
            headings=raw_data.get("headings", []),
            has_forms=raw_data.get("hasForms", False),
            total_elements_sampled=len(element_obs_list)
        )
