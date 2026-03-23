"""qBittorrent API client — download torrents."""
import httpx

from app.config import QBIT_URL, QBIT_USER, QBIT_PASS, AUDIOBOOK_DIR

_sid: str = ""


async def _login() -> str:
    """Login to qBittorrent and return SID cookie."""
    global _sid
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{QBIT_URL}/api/v2/auth/login",
                data={"username": QBIT_USER, "password": QBIT_PASS},
            )
            sid = resp.cookies.get("SID", "")
            if sid:
                _sid = sid
            return _sid
    except Exception:
        return _sid


async def _get_client() -> tuple[httpx.AsyncClient, dict]:
    """Get HTTP client with auth cookies."""
    global _sid
    if not _sid:
        await _login()
    cookies = {"SID": _sid} if _sid else {}
    return httpx.AsyncClient(timeout=30, cookies=cookies), cookies


async def add_torrent(download_url: str = "", magnet_url: str = "",
                      category: str = "audiobooks") -> dict:
    """Add a torrent to qBittorrent. Save path is managed by qBit categories."""
    url = download_url or magnet_url
    if not url:
        return {"error": "No download URL or magnet provided"}

    data = {"urls": url, "category": category}

    try:
        client, cookies = await _get_client()
        async with client:
            resp = await client.post(f"{QBIT_URL}/api/v2/torrents/add", data=data)
            if resp.status_code == 403:
                # Re-login and retry
                await _login()
                client2, cookies2 = await _get_client()
                async with client2:
                    resp = await client2.post(f"{QBIT_URL}/api/v2/torrents/add", data=data)

            if resp.text == "Ok.":
                return {"status": "added"}
            return {"error": f"qBittorrent returned: {resp.text}"}
    except Exception as e:
        return {"error": str(e)}


async def list_torrents(category: str = "audiobooks") -> list[dict]:
    """List torrents in a category."""
    try:
        client, _ = await _get_client()
        async with client:
            resp = await client.get(
                f"{QBIT_URL}/api/v2/torrents/info",
                params={"category": category},
            )
            if resp.status_code == 403:
                await _login()
                client2, _ = await _get_client()
                async with client2:
                    resp = await client2.get(
                        f"{QBIT_URL}/api/v2/torrents/info",
                        params={"category": category},
                    )
            resp.raise_for_status()
            return [
                {
                    "hash": t["hash"],
                    "name": t["name"],
                    "size": t["size"],
                    "progress": round(t["progress"] * 100, 1),
                    "state": t["state"],
                    "dlspeed": t["dlspeed"],
                    "eta": t["eta"],
                    "save_path": t["save_path"],
                }
                for t in resp.json()
            ]
    except Exception:
        return []


async def delete_torrent(torrent_hash: str, delete_files: bool = False) -> bool:
    """Delete a torrent."""
    try:
        client, _ = await _get_client()
        async with client:
            resp = await client.post(
                f"{QBIT_URL}/api/v2/torrents/delete",
                data={"hashes": torrent_hash, "deleteFiles": str(delete_files).lower()},
            )
            return resp.status_code == 200
    except Exception:
        return False
