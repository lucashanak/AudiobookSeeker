"""Prowlarr API client — search torrent indexers."""
import asyncio
import re

import httpx

from app.config import PROWLARR_URL, PROWLARR_API_KEY

# Prowlarr categories
CAT_AUDIO = "3000"
CAT_BOOKS = "7000"
# Extra CZ/SK book categories not mapped under 7000 by Prowlarr
_EXTRA_BOOK_CATS = ["100023", "100018"]  # SkTorrent Knihy, TreZzoR Knihy CZ/SK

# Known audiobook subcategories across indexers
_AUDIOBOOK_CATS = {3030, 100024}
# Known music subcategories to exclude from audiobook results
_MUSIC_CATS = {3010, 3020, 3040, 100002, 100101, 104627}
# Known ebook subcategories across indexers
_EBOOK_CATS = {7020, 100601}
# Non-book subcategories that appear under 7000 (movies, etc.)
_NOT_BOOK_CATS = {7050, 100699}
# Regex to detect video/movie releases misclassified as books
_VIDEO_RE = re.compile(
    r"(?:1080p|720p|2160p|4K|WEB-DL|WEBRip|BluRay|BDRip|HDRip|"
    r"x264|x265|HEVC|H\.?264|H\.?265|DUAL|DTS|AAC\.?5\.1|"
    r"REMUX|CAM|TS|DVDRip|HDTV)",
    re.IGNORECASE,
)


async def _fetch(client: httpx.AsyncClient, query: str, category: str) -> list:
    """Fetch search results from Prowlarr for a single category."""
    params = {
        "query": query,
        "categories": category,
        "type": "search",
        "apikey": PROWLARR_API_KEY,
    }
    try:
        resp = await client.get(f"{PROWLARR_URL}/api/v1/search", params=params)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return []


async def search(query: str, category: str = CAT_AUDIO, limit: int = 30,
                 min_size: int = 0, audiobook_only: bool = False,
                 ebook_only: bool = False) -> list[dict]:
    """Search Prowlarr for torrents in given category."""
    if not PROWLARR_API_KEY:
        return []

    async with httpx.AsyncClient(timeout=30) as client:
        # For ebooks, also search CZ/SK book categories in parallel
        if ebook_only:
            tasks = [_fetch(client, query, category)]
            for extra in _EXTRA_BOOK_CATS:
                tasks.append(_fetch(client, query, extra))
            all_results = await asyncio.gather(*tasks)
            raw = []
            seen_guids = set()
            for batch in all_results:
                for item in batch:
                    guid = item.get("guid", "")
                    if guid not in seen_guids:
                        seen_guids.add(guid)
                        raw.append(item)
        else:
            raw = await _fetch(client, query, category)

    results = []
    for item in raw[:limit * 3]:
        size = item.get("size", 0)
        if min_size and size < min_size:
            continue
        cats = {c.get("id", 0) for c in item.get("categories", [])}
        title = item.get("title", "")
        # Filter out music when searching for audiobooks
        if audiobook_only and cats & _MUSIC_CATS and not cats & _AUDIOBOOK_CATS:
            continue
        # Filter out movies/video when searching for ebooks
        if ebook_only:
            if cats & _NOT_BOOK_CATS:
                continue
            if _VIDEO_RE.search(title):
                continue
        results.append({
            "title": title,
            "indexer": item.get("indexer", ""),
            "size": size,
            "seeders": item.get("seeders", 0),
            "leechers": item.get("leechers", 0),
            "download_url": item.get("downloadUrl", ""),
            "magnet_url": item.get("magnetUrl", ""),
            "info_url": item.get("infoUrl", ""),
            "categories": list(cats),
            "age_days": item.get("age", 0),
            "grabs": item.get("grabs", 0),
        })
    results.sort(key=lambda x: x["seeders"], reverse=True)
    return results[:limit]


async def get_indexers() -> list[dict]:
    """List configured Prowlarr indexers."""
    if not PROWLARR_API_KEY:
        return []
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{PROWLARR_URL}/api/v1/indexer",
                params={"apikey": PROWLARR_API_KEY},
            )
            resp.raise_for_status()
            return [
                {"id": i["id"], "name": i["name"], "enabled": i["enable"]}
                for i in resp.json()
            ]
    except Exception:
        return []
