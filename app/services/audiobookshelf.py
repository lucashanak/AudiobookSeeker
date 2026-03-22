"""Audiobookshelf API client — library management and streaming."""
import httpx

from app.config import ABS_URL, ABS_USER, ABS_PASS

_token: str = ""


async def _login() -> str:
    """Login to Audiobookshelf and cache the token."""
    global _token
    if not ABS_URL or not ABS_USER:
        return ""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{ABS_URL}/login",
                json={"username": ABS_USER, "password": ABS_PASS},
            )
            resp.raise_for_status()
            data = resp.json()
            _token = data.get("user", {}).get("token", "")
            return _token
    except Exception:
        return ""


async def _get_token() -> str:
    global _token
    if not _token:
        await _login()
    return _token


async def _headers() -> dict:
    token = await _get_token()
    return {"Authorization": f"Bearer {token}"} if token else {}


async def get_libraries() -> list[dict]:
    """List all libraries."""
    try:
        hdrs = await _headers()
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{ABS_URL}/api/libraries", headers=hdrs)
            resp.raise_for_status()
            data = resp.json()
            return [
                {"id": lib["id"], "name": lib["name"], "mediaType": lib.get("mediaType", "")}
                for lib in data.get("libraries", [])
            ]
    except Exception:
        return []


async def get_library_items(library_id: str, limit: int = 50, page: int = 0,
                            sort: str = "media.metadata.title") -> dict:
    """Get audiobooks from a library."""
    try:
        hdrs = await _headers()
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{ABS_URL}/api/libraries/{library_id}/items",
                headers=hdrs,
                params={"limit": limit, "page": page, "sort": sort, "minified": 1},
            )
            resp.raise_for_status()
            data = resp.json()
            items = []
            for item in data.get("results", []):
                meta = item.get("media", {}).get("metadata", {})
                media = item.get("media", {})
                authors = ", ".join(a.get("name", "") for a in meta.get("authors", []))
                narrators = ", ".join(meta.get("narrators", []))
                items.append({
                    "id": item["id"],
                    "title": meta.get("title", ""),
                    "author": authors,
                    "narrator": narrators,
                    "duration": media.get("duration", 0),
                    "cover": f"/api/library/items/{item['id']}/cover" if media.get("coverPath") else "",
                    "description": (meta.get("description") or "")[:300],
                    "year": meta.get("publishedYear", ""),
                    "series": ", ".join(s.get("name", "") for s in meta.get("series", [])),
                    "genres": meta.get("genres", []),
                    "num_tracks": media.get("numAudioFiles", 0),
                    "size": item.get("size", 0),
                })
            return {"items": items, "total": data.get("total", 0)}
    except Exception:
        return {"items": [], "total": 0}


async def search_library(library_id: str, query: str) -> list[dict]:
    """Search within an Audiobookshelf library."""
    try:
        hdrs = await _headers()
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{ABS_URL}/api/libraries/{library_id}/search",
                headers=hdrs,
                params={"q": query},
            )
            resp.raise_for_status()
            data = resp.json()
            items = []
            for result in data.get("book", []):
                item = result.get("libraryItem", {})
                meta = item.get("media", {}).get("metadata", {})
                media = item.get("media", {})
                authors = ", ".join(a.get("name", "") for a in meta.get("authors", []))
                items.append({
                    "id": item.get("id", ""),
                    "title": meta.get("title", ""),
                    "author": authors,
                    "duration": media.get("duration", 0),
                    "cover": f"/api/library/items/{item['id']}/cover" if media.get("coverPath") else "",
                    "description": (meta.get("description") or "")[:300],
                    "year": meta.get("publishedYear", ""),
                    "num_tracks": media.get("numAudioFiles", 0),
                    "size": item.get("size", 0),
                })
            return items
    except Exception:
        return []


async def get_item(item_id: str) -> dict | None:
    """Get a single audiobook's full details."""
    try:
        hdrs = await _headers()
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{ABS_URL}/api/items/{item_id}", headers=hdrs)
            resp.raise_for_status()
            item = resp.json()
            meta = item.get("media", {}).get("metadata", {})
            media = item.get("media", {})
            authors = ", ".join(a.get("name", "") for a in meta.get("authors", []))
            narrators = ", ".join(meta.get("narrators", []))
            chapters = [
                {"id": ch["id"], "title": ch["title"], "start": ch["start"], "end": ch["end"]}
                for ch in media.get("chapters", [])
            ]
            return {
                "id": item["id"],
                "title": meta.get("title", ""),
                "author": authors,
                "narrator": narrators,
                "description": meta.get("description", ""),
                "duration": media.get("duration", 0),
                "cover": f"/api/library/items/{item['id']}/cover" if media.get("coverPath") else "",
                "year": meta.get("publishedYear", ""),
                "series": ", ".join(s.get("name", "") for s in meta.get("series", [])),
                "genres": meta.get("genres", []),
                "chapters": chapters,
                "num_tracks": media.get("numAudioFiles", 0),
                "size": item.get("size", 0),
            }
    except Exception:
        return None


async def get_progress(item_id: str) -> dict | None:
    """Get listening progress for an item."""
    try:
        hdrs = await _headers()
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{ABS_URL}/api/me/progress/{item_id}", headers=hdrs)
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            data = resp.json()
            return {
                "progress": data.get("progress", 0),
                "currentTime": data.get("currentTime", 0),
                "isFinished": data.get("isFinished", False),
                "duration": data.get("duration", 0),
            }
    except Exception:
        return None


async def scan_library(library_id: str) -> bool:
    """Trigger a library scan."""
    try:
        hdrs = await _headers()
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(f"{ABS_URL}/api/libraries/{library_id}/scan", headers=hdrs)
            return resp.status_code == 200
    except Exception:
        return False


async def get_status() -> dict:
    """Check Audiobookshelf connectivity."""
    try:
        token = await _get_token()
        if token:
            return {"connected": True}
        # Try to login fresh
        token = await _login()
        return {"connected": bool(token)}
    except Exception:
        return {"connected": False}
