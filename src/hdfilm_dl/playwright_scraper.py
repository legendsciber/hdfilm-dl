from __future__ import annotations

import asyncio
from typing import Optional

from rich.console import Console

from hdfilm_dl.models import VideoSource

BASE_URL = "https://www.hdfilmcehennemi.nl"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

console = Console()


class HdfilmScraper:
    def __init__(self):
        self._playwright = None
        self._browser = None

    async def __aenter__(self):
        from playwright.async_api import async_playwright
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=True)
        return self

    async def __aexit__(self, *args):
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

    async def fetch_page_html(self, url: str) -> str:
        context = await self._browser.new_context(
            user_agent=USER_AGENT,
            viewport={"width": 1280, "height": 720},
            java_script_enabled=True,
        )
        page = await context.new_page()
        await self._block_antibot(page)
        await page.goto(url, wait_until="networkidle", timeout=30000)
        await asyncio.sleep(2)
        html = await page.content()
        await context.close()
        return html

    async def _block_antibot(self, page):
        async def block_detect(route):
            if "devtools-console-detect" in route.request.url:
                await route.abort()
            else:
                await route.continue_()
        await page.route("**/*", block_detect)

    async def _capture_m3u8(
        self,
        page,
        url: str,
        source_index: int = 1,
    ) -> Optional[VideoSource]:
        m3u8_urls = []

        async def on_response(response):
            if response.status == 200 and ".m3u8" in response.url.lower():
                m3u8_urls.append(response.url)
        page.on("response", on_response)

        await page.goto(url, wait_until="networkidle", timeout=30000)
        await asyncio.sleep(2)

        play_btn = page.locator("[aria-label='Play video']")
        if await play_btn.count() > 0:
            await play_btn.click()
            await asyncio.sleep(3)

        alt_buttons = page.locator("[aria-label='Alternative tab content'] button")
        count = await alt_buttons.count()

        if source_index < 0 or source_index >= count:
            source_index = count - 1 if count > 0 else 0

        if count > 0:
            btn = alt_buttons.nth(source_index)
            text = await btn.text_content()
            console.print(f"  [dim]Using source: {text.strip()}[/dim]")
            await btn.click()
            await asyncio.sleep(12)

        video_src = None
        if m3u8_urls:
            master = [u for u in m3u8_urls if "master" in u.lower()]
            video_src = master[0] if master else m3u8_urls[0]

        if not video_src:
            video_src = await page.evaluate("""
                () => {
                    const frames = document.querySelectorAll('iframe');
                    for (const f of frames) {
                        try {
                            const win = f.contentWindow;
                            if (win && win.jwplayer) {
                                const p = win.jwplayer();
                                const pl = p.getPlaylist();
                                if (pl && pl[0] && pl[0].file) return pl[0].file;
                            }
                        } catch(e) {}
                        try {
                            const doc = f.contentDocument || f.contentWindow.document;
                            if (!doc) continue;
                            const v = doc.querySelector('video');
                            if (v) {
                                const s = v.currentSrc || v.src;
                                if (s && s.startsWith('http')) return s;
                            }
                        } catch(e) {}
                    }
                    return null;
                }
            """)

        if video_src:
            return VideoSource(url=video_src, referer=BASE_URL)
        return None

    async def find_video_source(
        self,
        slug: str,
        season: int,
        episode: int,
        source_index: int = 1,
    ) -> Optional[VideoSource]:
        url = f"{BASE_URL}/dizi/{slug}/sezon-{season}/bolum-{episode}/"
        context = await self._browser.new_context(
            user_agent=USER_AGENT,
            viewport={"width": 1280, "height": 720},
            java_script_enabled=True,
        )
        page = await context.new_page()
        await self._block_antibot(page)
        result = await self._capture_m3u8(page, url, source_index)
        await context.close()
        return result

    async def find_movie_source(
        self,
        slug: str,
        source_index: int = 1,
    ) -> Optional[VideoSource]:
        url = f"{BASE_URL}/{slug}/"
        context = await self._browser.new_context(
            user_agent=USER_AGENT,
            viewport={"width": 1280, "height": 720},
            java_script_enabled=True,
        )
        page = await context.new_page()
        await self._block_antibot(page)
        result = await self._capture_m3u8(page, url, source_index)
        await context.close()
        return result


async def find_source_async(
    slug: str,
    season: int,
    episode: int,
    source_index: int = 1,
) -> Optional[VideoSource]:
    async with HdfilmScraper() as scraper:
        return await scraper.find_video_source(slug, season, episode, source_index)


async def find_movie_source_async(
    slug: str,
    source_index: int = 1,
) -> Optional[VideoSource]:
    async with HdfilmScraper() as scraper:
        return await scraper.find_movie_source(slug, source_index)
