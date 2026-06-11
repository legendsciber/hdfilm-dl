from dataclasses import dataclass, field
from typing import Optional


@dataclass
class EpisodeInfo:
    slug: str
    season: int
    episode: int
    title: str
    anime_title: str


@dataclass
class VideoSource:
    url: str
    referer: str
    quality: Optional[str] = None


@dataclass
class AlternativeSource:
    name: str
    video_id: str
    active: bool
