from __future__ import annotations

import asyncio
from typing import Optional

from hdfilm_dl.models import AlternativeSource
from hdfilm_dl.scraper import extract_alternatives, extract_episode_info, extract_movie_info

BASE_URL = "https://www.hdfilmcehennemi.nl"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


class HdfilmClient:
    def __init__(self):
        self._playwright = None
        self._browser = None

    async def _ensure_browser(self):
        if not self._browser:
            from playwright.async_api import async_playwright
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(headless=True)

    async def fetch_page_html(self, url: str) -> str:
        await self._ensure_browser()
        context = await self._browser.new_context(
            user_agent=USER_AGENT,
            viewport={"width": 1280, "height": 720},
            java_script_enabled=True,
        )
        page = await context.new_page()
        async def block_detect(route):
            if "devtools-console-detect" in route.request.url:
                await route.abort()
            else:
                await route.continue_()
        await page.route("**/*", block_detect)
        await page.goto(url, wait_until="networkidle", timeout=30000)
        await asyncio.sleep(2)
        html = await page.content()
        await context.close()
        return html

    async def get_episode_page(self, slug: str, season: int = 1, episode: int = 1) -> str:
        url = f"{BASE_URL}/dizi/{slug}/sezon-{season}/bolum-{episode}/"
        return await self.fetch_page_html(url)

    async def get_movie_page(self, slug: str) -> str:
        url = f"{BASE_URL}/{slug}/"
        return await self.fetch_page_html(url)

    def parse_episode_info(self, html: str, fallback_slug: str = "") -> dict:
        return extract_episode_info(html, fallback_slug)

    def parse_movie_info(self, html: str, slug: str = "") -> dict:
        return extract_movie_info(html, slug)

    def parse_alternatives(self, html: str) -> list[AlternativeSource]:
        return extract_alternatives(html)

    async def close(self):
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
