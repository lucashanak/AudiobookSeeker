from fastapi import APIRouter, HTTPException, Depends
from app.models import DownloadRequest
from app.services import auth, qbittorrent, jobs

router = APIRouter(prefix="/api", tags=["downloads"])


@router.post("/download")
async def start_download(req: DownloadRequest, user: dict = Depends(auth.get_current_user)):
    job = jobs.create_job(
        title=req.title,
        indexer=req.indexer,
        size=req.size,
        username=user["username"],
        type=req.type,
    )
    # Category determines save path (configured in qBittorrent)
    category = "ebooks" if req.type == "ebook" else "audiobooks"

    result = await qbittorrent.add_torrent(
        download_url=req.download_url,
        magnet_url=req.magnet_url,
        category=category,
    )
    if "error" in result:
        jobs.update_job(job["id"], status="failed", error=result["error"])
        raise HTTPException(500, result["error"])
    jobs.update_job(job["id"], status="downloading")
    return {"status": "started", "job": job}


@router.get("/downloads")
async def list_downloads(user: dict = Depends(auth.get_current_user)):
    torrents = await qbittorrent.list_torrents(category="")  # All categories
    job_list = jobs.get_jobs()
    return {"torrents": torrents, "jobs": job_list}


@router.delete("/downloads/{torrent_hash}")
async def delete_download(torrent_hash: str, delete_files: bool = False,
                          user: dict = Depends(auth.get_current_user)):
    ok = await qbittorrent.delete_torrent(torrent_hash, delete_files)
    if not ok:
        raise HTTPException(500, "Failed to delete torrent")
    return {"status": "deleted"}
