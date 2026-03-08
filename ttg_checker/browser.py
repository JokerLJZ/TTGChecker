from __future__ import annotations

import random
import time
from dataclasses import dataclass
from pathlib import Path

from playwright.sync_api import BrowserContext, Page, TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from ttg_checker.config import BrowserConfig, TtgConfig


class CheckinError(RuntimeError):
    """Raised when check-in cannot be completed."""


@dataclass(slots=True)
class CheckinResult:
    success: bool
    message: str
    screenshot_path: str | None = None


class TtgBrowserClient:
    def __init__(self, browser_config: BrowserConfig, ttg_config: TtgConfig) -> None:
        self.browser_config = browser_config
        self.ttg_config = ttg_config

    def run_checkin(self) -> CheckinResult:
        screenshot_dir = Path(self.browser_config.screenshot_dir)
        screenshot_dir.mkdir(parents=True, exist_ok=True)

        with sync_playwright() as playwright:
            context = playwright.firefox.launch_persistent_context(
                user_data_dir=self.browser_config.profile_path,
                headless=self.browser_config.headless,
                slow_mo=self.browser_config.slow_mo_ms,
                user_agent=self.browser_config.user_agent,
            )
            try:
                context.set_default_navigation_timeout(self.browser_config.navigation_timeout_ms)
                page = self._open_target_page(context)
                self._guard_response_status(page)
                self._guard_logged_in(page)
                button = self._locate_checkin_button(page)
                self._human_pause()
                button.scroll_into_view_if_needed()
                button.hover()
                self._human_pause()
                button.click(force=False)
                self._human_pause()
                message = self._extract_feedback(page)
                screenshot = screenshot_dir / "checkin-success.png"
                page.screenshot(path=str(screenshot), full_page=True)
                return CheckinResult(success=True, message=message, screenshot_path=str(screenshot))
            except Exception as exc:
                screenshot = screenshot_dir / "checkin-error.png"
                self._safe_capture(context, str(screenshot))
                if isinstance(exc, CheckinError):
                    raise CheckinError(f"{exc} | screenshot={screenshot}") from exc
                raise CheckinError(f"{type(exc).__name__}: {exc} | screenshot={screenshot}") from exc
            finally:
                context.close()

    def _open_target_page(self, context: BrowserContext) -> Page:
        page = context.new_page()
        response = page.goto(self.ttg_config.checkin_url, wait_until="domcontentloaded")
        if response is None:
            raise CheckinError("TTG page returned no response")
        status = response.status
        if status >= 400:
            raise CheckinError(f"TTG page returned HTTP {status}")
        page.wait_for_load_state("networkidle")
        return page

    def _guard_response_status(self, page: Page) -> None:
        content = page.content()
        if "502 Bad Gateway" in content or "404 Not Found" in content:
            raise CheckinError("TTG page opened with an error document")

    def _guard_logged_in(self, page: Page) -> None:
        body_text = page.locator("body").inner_text(timeout=10_000).lower()
        if any(keyword.lower() in body_text for keyword in self.ttg_config.logged_out_keywords):
            raise CheckinError("Firefox profile is not logged in to TTG")

    def _locate_checkin_button(self, page: Page):
        for selector in self.ttg_config.button_selectors:
            locator = page.locator(selector).first
            try:
                locator.wait_for(state="visible", timeout=5_000)
                return locator
            except PlaywrightTimeoutError:
                continue
        raise CheckinError("Unable to locate the TTG check-in button")

    def _extract_feedback(self, page: Page) -> str:
        for selector in self.ttg_config.success_message_selectors:
            locator = page.locator(selector).first
            try:
                text = locator.inner_text(timeout=5_000).strip()
            except PlaywrightTimeoutError:
                continue
            normalized = " ".join(text.split())
            if any(keyword.lower() in normalized.lower() for keyword in self.ttg_config.success_keywords):
                return normalized[:500]
        body = page.locator("body").inner_text(timeout=10_000)
        normalized = " ".join(body.split())
        return normalized[:500]

    def _human_pause(self) -> None:
        low, high = self.browser_config.action_delay_seconds
        time.sleep(random.uniform(low, high))

    @staticmethod
    def _safe_capture(context: BrowserContext, output_path: str) -> None:
        for page in context.pages:
            try:
                page.screenshot(path=output_path, full_page=True)
                return
            except Exception:
                continue
