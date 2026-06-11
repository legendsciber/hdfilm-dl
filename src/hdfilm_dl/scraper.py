import re
from typing import Optional

from bs4 import BeautifulSoup

from hdfilm_dl.models import AlternativeSource


def extract_episode_info(html: str, fallback_slug: str = "") -> dict:
    soup = BeautifulSoup(html, "lxml")

    breadcrumb_links = soup.select(".breadcrumb a")
    slug = None
    anime_title = None
    if breadcrumb_links:
        for link in breadcrumb_links:
            href = link.get("href", "")
            match = re.search(r"/dizi/([^/]+)/", href)
            if match:
                slug = match.group(1)
                anime_title = link.get_text(strip=True)
                break

    title_tag = soup.select_one("h1.section-title")
    title = ""
    if title_tag:
        title = title_tag.get_text(" ", strip=True)

    if not slug:
        url_match = re.search(r'/dizi/([^/]+)/', html)
        if url_match:
            slug = url_match.group(1)

    return {
        "slug": slug or fallback_slug,
        "anime_title": anime_title or slug or fallback_slug,
        "title": title,
    }


def extract_movie_info(html: str, slug_from_url: str = "") -> dict:
    soup = BeautifulSoup(html, "lxml")

    title_tag = soup.select_one("h1.section-title")
    title = ""
    if title_tag:
        title = title_tag.get_text(" ", strip=True)

    jsonld_script = soup.find("script", type="application/ld+json")
    year = ""
    if jsonld_script:
        import json
        try:
            data = json.loads(jsonld_script.string)
            if not title:
                title = data.get("name", "")
            date_str = data.get("datePublished", "")
            if date_str:
                y_match = re.search(r"\d{4}", date_str)
                if y_match:
                    year = y_match.group(0)
        except (json.JSONDecodeError, AttributeError):
            pass

    alt_title = title or slug_from_url.replace("-", " ").title()

    return {
        "title": alt_title,
        "year": year,
        "slug": slug_from_url,
        "is_movie": True,
    }


def extract_alternatives(html: str) -> list[AlternativeSource]:
    soup = BeautifulSoup(html, "lxml")
    alternatives = []

    for btn in soup.select("[aria-label='Alternative tab content'] button"):
        video_id = btn.get("data-video", "")
        name = btn.get_text(strip=True)
        active = btn.get("data-active", "") == "1"
        if video_id:
            alternatives.append(AlternativeSource(name=name, video_id=video_id, active=active))

    return alternatives


def extract_language_tabs(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    tabs = []
    for btn in soup.select("[aria-label='Language tab menu'] button"):
        lang = btn.get("data-lang", "")
        name = btn.get_text(strip=True)
        active = btn.get("data-active", "") == "1"
        tabs.append({"lang": lang, "name": name, "active": active})
    return tabs


def extract_initial_iframe_src(html: str) -> Optional[str]:
    soup = BeautifulSoup(html, "lxml")
    iframe = soup.select_one("[aria-label='Player'] iframe")
    if iframe:
        return iframe.get("data-src") or iframe.get("src")
    return None
