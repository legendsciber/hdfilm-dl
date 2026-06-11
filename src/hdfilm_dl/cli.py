from __future__ import annotations

import asyncio
import re
import sys

import click
from rich.console import Console
from rich.panel import Panel

from hdfilm_dl.client import HdfilmClient
from hdfilm_dl.downloader import download_episode, download_movie
from hdfilm_dl.models import EpisodeInfo, VideoSource
from hdfilm_dl.playwright_scraper import find_source_async, find_movie_source_async

console = Console()

SERIES_RE = re.compile(
    r"^https?://(?:www\.)?hdfilmcehennemi\.nl/dizi/([^/]+)/sezon-(\d+)/bolum-(\d+)/"
)
MOVIE_RE = re.compile(
    r"^https?://(?:www\.)?hdfilmcehennemi\.nl/([^/]+)/?$"
)


def parse_url(url: str) -> tuple[str, str, int, int] | None:
    """Returns (type, slug, season, episode) where type is 'series' or 'movie'."""
    m = SERIES_RE.match(url)
    if m:
        return ("series", m.group(1), int(m.group(2)), int(m.group(3)))
    m = MOVIE_RE.match(url)
    if m and m.group(1) not in ("category", "yil", "dizi", "film-robotu"):
        return ("movie", m.group(1), 0, 0)
    return None


@click.group()
def main():
    """hdfilmcehennemi.nl video downloader"""


async def _do_inspect(url: str):
    parsed = parse_url(url)
    if not parsed:
        console.print("[red]Invalid URL[/red]")
        console.print("  Series: https://www.hdfilmcehennemi.nl/dizi/slug/sezon-1/bolum-1/")
        console.print("  Movie:  https://www.hdfilmcehennemi.nl/slug/")
        return

    ptype, slug, season, episode = parsed
    client = HdfilmClient()

    with console.status("[cyan]Loading page..."):
        if ptype == "series":
            html = await client.get_episode_page(slug, season, episode)
        else:
            html = await client.get_movie_page(slug)

    info = client.parse_episode_info(html, slug) if ptype == "series" else client.parse_movie_info(html, slug)
    alternatives = client.parse_alternatives(html)
    await client.close()

    console.print("[bold]Page Info:[/bold]")
    console.print(f"  Type: {ptype}")
    console.print(f"  Title: {info.get('title', slug)}")
    if ptype == "series":
        console.print(f"  Season: {season}")
        console.print(f"  Episode: {episode}")
    if ptype == "movie":
        console.print(f"  Year: {info.get('year', '?')}")

    if alternatives:
        console.print(f"\n[bold]Video Sources ({len(alternatives)}):[/bold]")
        for alt in alternatives:
            marker = "[green]Active[/green]" if alt.active else "[dim]Inactive[/dim]"
            console.print(f"  {marker} {alt.name} (video_id: {alt.video_id})")
    else:
        console.print("\n[yellow]No alternative video sources found.[/yellow]")

    console.print("\n[bold]Note:[/bold] Use `hdfilm-dl download <url>` to download.")


async def _do_download(url: str, output: str):
    parsed = parse_url(url)
    if not parsed:
        console.print("[red]Invalid URL[/red]")
        console.print("  Series: https://www.hdfilmcehennemi.nl/dizi/slug/sezon-1/bolum-1/")
        console.print("  Movie:  https://www.hdfilmcehennemi.nl/slug/")
        return

    ptype, slug, season, episode = parsed
    client = HdfilmClient()

    with console.status("[cyan]Loading page..."):
        if ptype == "series":
            html = await client.get_episode_page(slug, season, episode)
        else:
            html = await client.get_movie_page(slug)

    info_data = client.parse_episode_info(html, slug) if ptype == "series" else client.parse_movie_info(html, slug)
    alternatives = client.parse_alternatives(html)
    await client.close()

    source_index = 1
    if alternatives and len(alternatives) > 1:
        console.print("\n[bold]Available sources:[/bold]")
        for i, alt in enumerate(alternatives):
            marker = "[green]Active[/green]" if alt.active else "[dim]Inactive[/dim]"
            console.print(f"  [{i}] {marker} {alt.name}")
        choice = click.prompt("Choose source", type=int, default=1, show_default=True)
        if 0 <= choice < len(alternatives):
            source_index = choice

    if ptype == "series":
        info = EpisodeInfo(
            slug=slug,
            season=season,
            episode=episode,
            title=info_data.get("title", f"Episode {episode}"),
            anime_title=info_data.get("anime_title", slug),
        )

        console.print(Panel(f"[bold]hdfilm-dl[/bold]\n{url}", width=60))
        console.print("[cyan]Opening browser with Playwright...[/cyan]")

        source = await find_source_async(slug, season, episode, source_index)
        if source:
            console.print(f"[green]Video source found:[/green] {source.url[:80]}...")
            download_episode(source, info, output)
        else:
            console.print("[red]Video source not found.[/red]")
            sys.exit(1)

    else:
        title = info_data.get("title", slug.replace("-", " ").title())
        year = info_data.get("year", "")

        console.print(Panel(f"[bold]hdfilm-dl[/bold]\n{url}", width=60))
        console.print("[cyan]Opening browser with Playwright...[/cyan]")

        source = await find_movie_source_async(slug, source_index)
        if source:
            console.print(f"[green]Video source found:[/green] {source.url[:80]}...")
            download_movie(source, title, year, output)
        else:
            console.print("[red]Video source not found.[/red]")
            sys.exit(1)


@main.command()
@click.argument("url")
@click.option("-o", "--output", default=".", help="Output directory")
def download(url: str, output: str):
    """Download series episode or movie from URL"""
    asyncio.run(_do_download(url, output))


@main.command()
@click.argument("url")
@click.option("-s", "--start", type=int, default=1, help="Start episode")
@click.option("-e", "--end", type=int, required=True, help="End episode")
@click.option("-o", "--output", default=".", help="Output directory")
def batch(url: str, start: int, end: int, output: str):
    """Download a range of episodes (series only)"""
    parsed = parse_url(url)
    if not parsed or parsed[0] != "series":
        console.print("[red]Batch download is for series only. Use a series URL.[/red]")
        sys.exit(1)

    ptype, slug, season, _ = parsed
    console.print(Panel(f"[bold]Batch download:[/bold] {slug} S{season} Episodes {start}-{end}", width=60))

    for ep in range(start, end + 1):
        info = EpisodeInfo(
            slug=slug,
            season=season,
            episode=ep,
            title=f"Episode {ep}",
            anime_title=slug.replace("-", " ").title(),
        )
        console.print(f"\n[cyan]--- Episode {ep} ---[/cyan]")
        source = asyncio.run(find_source_async(slug, season, ep))
        if source:
            download_episode(source, info, output)
        else:
            console.print(f"[yellow]No source for episode {ep}, skipping...[/yellow]")

    console.print("[green]Batch download complete![/green]")


@main.command()
@click.argument("url")
def inspect(url: str):
    """Show page info"""
    asyncio.run(_do_inspect(url))


@main.command()
def version():
    """Show version info"""
    from hdfilm_dl import __version__
    console.print(f"hdfilm-dl v{__version__}")


if __name__ == "__main__":
    main()
