"""
Browser Automation Service
--------------------------
Playwright-based browser automation with DOM-first, Vision-fallback approach.

Cost optimization strategy:
1. DOM-Based (FREE): Use CSS/XPath selectors, text matching, ARIA roles
2. Vision-Assisted (PAID): Only when DOM approach fails, use Claude Vision

This service enables Sakhi to:
- Navigate websites and fill forms
- Click buttons and links by text/role/selector
- Extract content from pages
- Handle complex UIs with vision fallback
"""

from __future__ import annotations

import asyncio
import base64
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from enum import Enum

LOGGER = logging.getLogger(__name__)

# Browser configuration
DEFAULT_VIEWPORT = {"width": 1280, "height": 800}
DEFAULT_TIMEOUT_MS = 30000
SCREENSHOT_DIR = Path("/tmp/sakhi/browser_screenshots")


class ActionStrategy(str, Enum):
    """Strategy for executing actions."""
    DOM_ONLY = "dom_only"  # Only try DOM-based approach
    VISION_ONLY = "vision_only"  # Only use vision (expensive)
    DOM_FIRST = "dom_first"  # Try DOM, fallback to vision (recommended)


class BrowserActionType(str, Enum):
    """Types of browser actions."""
    NAVIGATE = "navigate"
    CLICK = "click"
    TYPE = "type"
    SELECT = "select"
    SCROLL = "scroll"
    WAIT = "wait"
    SCREENSHOT = "screenshot"
    EXTRACT = "extract"
    HOVER = "hover"
    PRESS_KEY = "press_key"


# =============================================================================
# Browser Automation Class
# =============================================================================

class BrowserAutomation:
    """
    Playwright-based browser automation with smart fallback to vision.

    Usage:
        async with BrowserAutomation() as browser:
            await browser.navigate("https://google.com")
            await browser.type_text("input[name='q']", "Italian restaurants")
            await browser.click("button[type='submit']")
            content = await browser.extract_text("div.results")
    """

    def __init__(
        self,
        headless: bool = True,
        viewport: Optional[Dict[str, int]] = None,
        strategy: ActionStrategy = ActionStrategy.DOM_FIRST,
        timeout_ms: int = DEFAULT_TIMEOUT_MS,
    ):
        self.headless = headless
        self.viewport = viewport or DEFAULT_VIEWPORT
        self.strategy = strategy
        self.timeout_ms = timeout_ms

        self._playwright = None
        self._browser = None
        self._context = None
        self._page = None

        # Tracking
        self.actions_executed = 0
        self.vision_fallbacks = 0
        self.dom_successes = 0

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop()

    async def start(self) -> None:
        """Start the browser."""
        try:
            from playwright.async_api import async_playwright

            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=self.headless,
            )
            self._context = await self._browser.new_context(
                viewport=self.viewport,
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            )
            self._page = await self._context.new_page()

            # Set default timeout
            self._page.set_default_timeout(self.timeout_ms)

            LOGGER.info("[browser] Started browser (headless=%s)", self.headless)

        except ImportError:
            raise RuntimeError(
                "Playwright not installed. Run: pip install playwright && playwright install chromium"
            )

    async def stop(self) -> None:
        """Stop the browser."""
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

        LOGGER.info(
            "[browser] Stopped. Actions: %d, DOM successes: %d, Vision fallbacks: %d",
            self.actions_executed,
            self.dom_successes,
            self.vision_fallbacks,
        )

    @property
    def page(self):
        """Get the current page."""
        if not self._page:
            raise RuntimeError("Browser not started. Call start() first.")
        return self._page

    # =========================================================================
    # Navigation
    # =========================================================================

    async def navigate(self, url: str, wait_until: str = "domcontentloaded") -> Dict[str, Any]:
        """
        Navigate to a URL.

        Args:
            url: The URL to navigate to
            wait_until: When to consider navigation done (domcontentloaded, load, networkidle)

        Returns:
            Navigation result with status and URL
        """
        LOGGER.info("[browser] Navigating to: %s", url)

        try:
            response = await self.page.goto(url, wait_until=wait_until)
            self.actions_executed += 1

            return {
                "success": True,
                "url": self.page.url,
                "status": response.status if response else None,
                "title": await self.page.title(),
            }
        except Exception as e:
            LOGGER.error("[browser] Navigation failed: %s", e)
            return {"success": False, "error": str(e)}

    async def go_back(self) -> bool:
        """Go back in browser history."""
        try:
            await self.page.go_back()
            self.actions_executed += 1
            return True
        except Exception as e:
            LOGGER.error("[browser] Go back failed: %s", e)
            return False

    async def go_forward(self) -> bool:
        """Go forward in browser history."""
        try:
            await self.page.go_forward()
            self.actions_executed += 1
            return True
        except Exception as e:
            LOGGER.error("[browser] Go forward failed: %s", e)
            return False

    # =========================================================================
    # Click Actions (DOM-first with Vision fallback)
    # =========================================================================

    async def click(
        self,
        target: str,
        *,
        timeout_ms: Optional[int] = None,
        force_vision: bool = False,
    ) -> Dict[str, Any]:
        """
        Click an element using DOM-first strategy with vision fallback.

        Args:
            target: CSS selector, XPath, text content, or description for vision
            timeout_ms: Override default timeout
            force_vision: Skip DOM approach and use vision directly

        Returns:
            Result with success status and method used
        """
        timeout = timeout_ms or self.timeout_ms

        # Skip DOM if forced vision or vision-only strategy
        if not force_vision and self.strategy != ActionStrategy.VISION_ONLY:
            # Try DOM-based approaches in order of reliability
            result = await self._click_dom(target, timeout)
            if result["success"]:
                self.dom_successes += 1
                self.actions_executed += 1
                return result

        # Vision fallback (if enabled)
        if self.strategy in (ActionStrategy.DOM_FIRST, ActionStrategy.VISION_ONLY):
            LOGGER.info("[browser] DOM click failed, trying vision fallback for: %s", target)
            result = await self._click_vision(target)
            if result["success"]:
                self.vision_fallbacks += 1
                self.actions_executed += 1
            return result

        return {"success": False, "error": "All click methods failed", "target": target}

    async def _click_dom(self, target: str, timeout: int) -> Dict[str, Any]:
        """Try various DOM-based click approaches."""
        approaches = [
            # 1. Direct CSS/XPath selector
            lambda: self._click_selector(target, timeout),
            # 2. Click by exact text
            lambda: self._click_by_text(target, timeout),
            # 3. Click by partial text
            lambda: self._click_by_text(target, timeout, exact=False),
            # 4. Click by role + name
            lambda: self._click_by_role(target, timeout),
            # 5. Click by label
            lambda: self._click_by_label(target, timeout),
        ]

        for approach in approaches:
            try:
                result = await approach()
                if result["success"]:
                    return result
            except Exception as e:
                LOGGER.debug("[browser] DOM approach failed: %s", e)
                continue

        return {"success": False, "method": "dom", "error": "No DOM approach worked"}

    async def _click_selector(self, selector: str, timeout: int) -> Dict[str, Any]:
        """Click using CSS or XPath selector."""
        try:
            # Check if it looks like a selector
            if not any(c in selector for c in [".", "#", "[", "/", ">"]):
                return {"success": False}

            locator = self.page.locator(selector).first
            await locator.click(timeout=timeout)
            return {"success": True, "method": "selector", "selector": selector}
        except Exception:
            return {"success": False}

    async def _click_by_text(self, text: str, timeout: int, exact: bool = True) -> Dict[str, Any]:
        """Click element by text content."""
        try:
            if exact:
                locator = self.page.get_by_text(text, exact=True).first
            else:
                locator = self.page.get_by_text(text).first
            await locator.click(timeout=timeout)
            return {"success": True, "method": "text", "text": text, "exact": exact}
        except Exception:
            return {"success": False}

    async def _click_by_role(self, name: str, timeout: int) -> Dict[str, Any]:
        """Click element by ARIA role and accessible name."""
        roles = ["button", "link", "menuitem", "tab", "checkbox", "radio"]
        for role in roles:
            try:
                locator = self.page.get_by_role(role, name=name).first
                await locator.click(timeout=min(timeout, 5000))  # Quick check
                return {"success": True, "method": "role", "role": role, "name": name}
            except Exception:
                continue
        return {"success": False}

    async def _click_by_label(self, label: str, timeout: int) -> Dict[str, Any]:
        """Click element by associated label."""
        try:
            locator = self.page.get_by_label(label).first
            await locator.click(timeout=timeout)
            return {"success": True, "method": "label", "label": label}
        except Exception:
            return {"success": False}

    async def _click_vision(self, description: str) -> Dict[str, Any]:
        """Use vision to find and click element."""
        from sakhi.apps.api.services.agent.screen_analyzer import analyze_screen_for_element

        # Take screenshot
        screenshot_path = await self.screenshot(save=True)
        if not screenshot_path:
            return {"success": False, "error": "Failed to take screenshot"}

        # Use vision to find element
        element = await analyze_screen_for_element(
            screenshot_path=screenshot_path,
            element_description=description,
            width=self.viewport["width"],
            height=self.viewport["height"],
        )

        if not element:
            return {"success": False, "method": "vision", "error": "Element not found by vision"}

        # Click at the coordinates
        x, y = element.get("x", 0), element.get("y", 0)
        confidence = element.get("confidence", 0)

        if confidence < 0.5:
            LOGGER.warning("[browser] Low confidence vision match: %.2f", confidence)

        try:
            await self.page.mouse.click(x, y)
            return {
                "success": True,
                "method": "vision",
                "coordinates": {"x": x, "y": y},
                "confidence": confidence,
                "element": element,
            }
        except Exception as e:
            return {"success": False, "method": "vision", "error": str(e)}

    # =========================================================================
    # Type Actions
    # =========================================================================

    async def type_text(
        self,
        target: str,
        text: str,
        *,
        clear_first: bool = True,
        press_enter: bool = False,
        timeout_ms: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Type text into an input field.

        Args:
            target: Selector, placeholder text, or label
            text: Text to type
            clear_first: Clear existing content first
            press_enter: Press Enter after typing
            timeout_ms: Override timeout

        Returns:
            Result with success status
        """
        timeout = timeout_ms or self.timeout_ms

        # Try DOM approaches
        if self.strategy != ActionStrategy.VISION_ONLY:
            result = await self._type_dom(target, text, clear_first, press_enter, timeout)
            if result["success"]:
                self.dom_successes += 1
                self.actions_executed += 1
                return result

        # Vision fallback
        if self.strategy in (ActionStrategy.DOM_FIRST, ActionStrategy.VISION_ONLY):
            result = await self._type_vision(target, text, clear_first, press_enter)
            if result["success"]:
                self.vision_fallbacks += 1
                self.actions_executed += 1
            return result

        return {"success": False, "error": "All type methods failed"}

    async def _type_dom(
        self,
        target: str,
        text: str,
        clear_first: bool,
        press_enter: bool,
        timeout: int,
    ) -> Dict[str, Any]:
        """Type using DOM-based approaches."""
        approaches = [
            # 1. Direct selector
            lambda: self._type_selector(target, text, clear_first, timeout),
            # 2. By placeholder
            lambda: self._type_by_placeholder(target, text, clear_first, timeout),
            # 3. By label
            lambda: self._type_by_label(target, text, clear_first, timeout),
            # 4. By role
            lambda: self._type_by_role(target, text, clear_first, timeout),
        ]

        for approach in approaches:
            try:
                result = await approach()
                if result["success"]:
                    if press_enter:
                        await self.page.keyboard.press("Enter")
                    return result
            except Exception as e:
                LOGGER.debug("[browser] Type approach failed: %s", e)
                continue

        return {"success": False, "method": "dom"}

    async def _type_selector(
        self, selector: str, text: str, clear_first: bool, timeout: int
    ) -> Dict[str, Any]:
        """Type into element by selector."""
        try:
            if not any(c in selector for c in [".", "#", "[", "/", ">", "input", "textarea"]):
                return {"success": False}

            locator = self.page.locator(selector).first
            if clear_first:
                await locator.clear(timeout=timeout)
            await locator.fill(text, timeout=timeout)
            return {"success": True, "method": "selector", "selector": selector}
        except Exception:
            return {"success": False}

    async def _type_by_placeholder(
        self, placeholder: str, text: str, clear_first: bool, timeout: int
    ) -> Dict[str, Any]:
        """Type into element by placeholder."""
        try:
            locator = self.page.get_by_placeholder(placeholder).first
            if clear_first:
                await locator.clear(timeout=timeout)
            await locator.fill(text, timeout=timeout)
            return {"success": True, "method": "placeholder", "placeholder": placeholder}
        except Exception:
            return {"success": False}

    async def _type_by_label(
        self, label: str, text: str, clear_first: bool, timeout: int
    ) -> Dict[str, Any]:
        """Type into element by label."""
        try:
            locator = self.page.get_by_label(label).first
            if clear_first:
                await locator.clear(timeout=timeout)
            await locator.fill(text, timeout=timeout)
            return {"success": True, "method": "label", "label": label}
        except Exception:
            return {"success": False}

    async def _type_by_role(
        self, name: str, text: str, clear_first: bool, timeout: int
    ) -> Dict[str, Any]:
        """Type into element by role."""
        roles = ["textbox", "searchbox", "combobox"]
        for role in roles:
            try:
                locator = self.page.get_by_role(role, name=name).first
                if clear_first:
                    await locator.clear(timeout=min(timeout, 5000))
                await locator.fill(text, timeout=min(timeout, 5000))
                return {"success": True, "method": "role", "role": role, "name": name}
            except Exception:
                continue
        return {"success": False}

    async def _type_vision(
        self,
        description: str,
        text: str,
        clear_first: bool,
        press_enter: bool,
    ) -> Dict[str, Any]:
        """Use vision to find input and type."""
        # First click the input field
        click_result = await self._click_vision(description)
        if not click_result["success"]:
            return {"success": False, "error": "Could not find input field via vision"}

        # Clear if needed
        if clear_first:
            await self.page.keyboard.press("Control+a")
            await self.page.keyboard.press("Backspace")

        # Type the text
        await self.page.keyboard.type(text)

        if press_enter:
            await self.page.keyboard.press("Enter")

        return {"success": True, "method": "vision", "text": text}

    # =========================================================================
    # Other Actions
    # =========================================================================

    async def scroll(
        self,
        direction: str = "down",
        amount: int = 300,
    ) -> Dict[str, Any]:
        """Scroll the page."""
        try:
            delta_y = amount if direction == "down" else -amount
            await self.page.mouse.wheel(0, delta_y)
            self.actions_executed += 1
            return {"success": True, "direction": direction, "amount": amount}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def press_key(self, key: str) -> Dict[str, Any]:
        """Press a keyboard key."""
        try:
            await self.page.keyboard.press(key)
            self.actions_executed += 1
            return {"success": True, "key": key}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def wait(self, ms: int = 1000) -> Dict[str, Any]:
        """Wait for a specified time."""
        await asyncio.sleep(ms / 1000)
        return {"success": True, "waited_ms": ms}

    async def wait_for_selector(
        self,
        selector: str,
        timeout_ms: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Wait for an element to appear."""
        try:
            await self.page.wait_for_selector(
                selector,
                timeout=timeout_ms or self.timeout_ms,
            )
            return {"success": True, "selector": selector}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # =========================================================================
    # Content Extraction
    # =========================================================================

    async def extract_text(
        self,
        selector: Optional[str] = None,
    ) -> str:
        """Extract text content from page or element."""
        try:
            if selector:
                locator = self.page.locator(selector).first
                return await locator.inner_text()
            else:
                return await self.page.inner_text("body")
        except Exception as e:
            LOGGER.error("[browser] Text extraction failed: %s", e)
            return ""

    async def extract_html(
        self,
        selector: Optional[str] = None,
    ) -> str:
        """Extract HTML content from page or element."""
        try:
            if selector:
                locator = self.page.locator(selector).first
                return await locator.inner_html()
            else:
                return await self.page.content()
        except Exception as e:
            LOGGER.error("[browser] HTML extraction failed: %s", e)
            return ""

    async def extract_links(self) -> List[Dict[str, str]]:
        """Extract all links from the page."""
        try:
            links = await self.page.evaluate("""
                () => Array.from(document.querySelectorAll('a[href]')).map(a => ({
                    text: a.innerText.trim(),
                    href: a.href,
                    title: a.title || ''
                }))
            """)
            return links
        except Exception as e:
            LOGGER.error("[browser] Link extraction failed: %s", e)
            return []

    async def get_page_info(self) -> Dict[str, Any]:
        """Get current page information."""
        return {
            "url": self.page.url,
            "title": await self.page.title(),
            "viewport": self.viewport,
        }

    # =========================================================================
    # Screenshot
    # =========================================================================

    async def screenshot(
        self,
        *,
        save: bool = False,
        full_page: bool = False,
    ) -> Optional[str]:
        """
        Take a screenshot.

        Args:
            save: Save to disk and return path
            full_page: Capture full scrollable page

        Returns:
            File path if save=True, else base64 data
        """
        try:
            if save:
                SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
                path = SCREENSHOT_DIR / f"screenshot_{self.actions_executed}.png"
                await self.page.screenshot(path=str(path), full_page=full_page)
                return str(path)
            else:
                data = await self.page.screenshot(full_page=full_page)
                return base64.b64encode(data).decode("utf-8")
        except Exception as e:
            LOGGER.error("[browser] Screenshot failed: %s", e)
            return None


# =============================================================================
# Convenience Functions
# =============================================================================

async def run_browser_task(
    task: str,
    starting_url: str,
    *,
    headless: bool = True,
    max_steps: int = 20,
    strategy: ActionStrategy = ActionStrategy.DOM_FIRST,
) -> Dict[str, Any]:
    """
    Run a browser automation task with AI decision making.

    This is a high-level function that combines browser automation
    with the action decider.

    Args:
        task: Natural language task description
        starting_url: URL to start at
        headless: Run browser in headless mode
        max_steps: Maximum automation steps
        strategy: DOM_FIRST (recommended), VISION_ONLY, or DOM_ONLY

    Returns:
        Task result with status and extracted data
    """
    from sakhi.apps.api.services.agent.screen_analyzer import analyze_screen
    from sakhi.apps.api.services.agent.action_decider import decide_next_action

    async with BrowserAutomation(headless=headless, strategy=strategy) as browser:
        # Navigate to starting URL
        nav_result = await browser.navigate(starting_url)
        if not nav_result["success"]:
            return {"success": False, "error": f"Failed to navigate: {nav_result.get('error')}"}

        action_history = []

        for step in range(max_steps):
            # Take screenshot for analysis
            screenshot_path = await browser.screenshot(save=True)

            # Analyze the current screen
            analysis = await analyze_screen(
                screenshot_path=screenshot_path,
                width=browser.viewport["width"],
                height=browser.viewport["height"],
                task_context=task,
                previous_actions=action_history[-5:],
            )

            # Decide next action
            decision = await decide_next_action(
                task_description=task,
                task_context={"browser_mode": True},
                screen_analysis=analysis,
                action_history=action_history,
                step_number=step + 1,
            )

            # Check if complete
            if decision.get("is_complete"):
                return {
                    "success": True,
                    "completed": True,
                    "steps": step + 1,
                    "reasoning": decision.get("reasoning"),
                    "result": decision.get("result"),
                    "stats": {
                        "dom_successes": browser.dom_successes,
                        "vision_fallbacks": browser.vision_fallbacks,
                    },
                }

            # Execute the action
            action = decision.get("action")
            if not action:
                continue

            action_type = action.get("type")
            params = action.get("parameters", {})

            if action_type == "click":
                result = await browser.click(params.get("target", ""))
            elif action_type == "type":
                result = await browser.type_text(
                    params.get("target", ""),
                    params.get("text", ""),
                    press_enter=params.get("press_enter", False),
                )
            elif action_type == "scroll":
                result = await browser.scroll(
                    params.get("direction", "down"),
                    params.get("amount", 300),
                )
            elif action_type == "navigate":
                result = await browser.navigate(params.get("url", ""))
            elif action_type == "wait":
                result = await browser.wait(params.get("ms", 1000))
            elif action_type == "key":
                result = await browser.press_key(params.get("key", ""))
            else:
                result = {"success": False, "error": f"Unknown action: {action_type}"}

            action_history.append({
                "type": action_type,
                "parameters": params,
                "result": result,
                "reasoning": decision.get("reasoning"),
            })

            # Small delay between actions
            await asyncio.sleep(0.5)

        return {
            "success": False,
            "completed": False,
            "steps": max_steps,
            "error": "Max steps reached",
            "stats": {
                "dom_successes": browser.dom_successes,
                "vision_fallbacks": browser.vision_fallbacks,
            },
        }


__all__ = [
    "ActionStrategy",
    "BrowserActionType",
    "BrowserAutomation",
    "run_browser_task",
]
