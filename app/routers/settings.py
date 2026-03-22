import os
import shutil
from fastapi import APIRouter, Depends, HTTPException
from app.models import SettingsUpdate
from app.services import auth, settings, audiobookshelf
from app.config import AUDIOBOOK_DIR

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("")
async def get_settings(user: dict = Depends(auth.get_current_user)):
    if user.get("is_admin"):
        return settings.get_all()
    return settings.get_public()


@router.put("")
async def update_settings(req: SettingsUpdate, user: dict = Depends(auth.require_admin)):
    data = req.model_dump(exclude_none=True)
    return settings.update(data)


@router.get("/disk-usage")
async def disk_usage(user: dict = Depends(auth.require_admin)):
    audiobook_dir = settings.get("audiobook_dir", AUDIOBOOK_DIR)
    usage = []
    try:
        for entry in sorted(os.scandir(audiobook_dir), key=lambda e: e.name):
            if entry.is_dir() and not entry.name.startswith("."):
                size, count = _get_dir_size(entry.path)
                usage.append({"name": entry.name, "size_bytes": size, "file_count": count})
            elif entry.is_file():
                usage.append({"name": entry.name, "size_bytes": entry.stat().st_size, "file_count": 1})
    except FileNotFoundError:
        pass
    return {"usage": usage, "base_dir": audiobook_dir}


@router.get("/disk-usage/{dirname}/subfolders")
async def subfolders(dirname: str, user: dict = Depends(auth.require_admin)):
    if "/" in dirname or "\\" in dirname or dirname.startswith("."):
        raise HTTPException(400, "Invalid directory name")
    audiobook_dir = settings.get("audiobook_dir", AUDIOBOOK_DIR)
    dirpath = os.path.join(audiobook_dir, dirname)
    subs = []
    try:
        for entry in sorted(os.scandir(dirpath), key=lambda e: e.name):
            if entry.is_dir() and not entry.name.startswith("."):
                size, count = _get_dir_size(entry.path)
                subs.append({"name": entry.name, "size_bytes": size, "file_count": count})
            elif entry.is_file():
                subs.append({"name": entry.name, "size_bytes": entry.stat().st_size, "file_count": 1})
    except FileNotFoundError:
        raise HTTPException(404, "Directory not found")
    return {"subfolders": subs}


@router.delete("/disk-usage/{dirname}")
async def delete_dir(dirname: str, subfolder: str = "",
                     user: dict = Depends(auth.require_admin)):
    if "/" in dirname or "\\" in dirname or dirname.startswith("."):
        raise HTTPException(400, "Invalid directory name")
    audiobook_dir = settings.get("audiobook_dir", AUDIOBOOK_DIR)
    target = os.path.join(audiobook_dir, dirname)
    if subfolder:
        if "/" in subfolder or "\\" in subfolder or subfolder.startswith("."):
            raise HTTPException(400, "Invalid subfolder name")
        target = os.path.join(target, subfolder)

    if not os.path.exists(target):
        raise HTTPException(404, "Not found")

    if os.path.isdir(target):
        shutil.rmtree(target)
    else:
        os.remove(target)

    # Trigger ABS scan
    try:
        libs = await audiobookshelf.get_libraries()
        for lib in libs:
            await audiobookshelf.scan_library(lib["id"])
    except Exception:
        pass

    return {"status": "deleted", "name": subfolder or dirname}


def _get_dir_size(path: str) -> tuple[int, int]:
    total_size = 0
    file_count = 0
    try:
        for dirpath, _dirnames, filenames in os.walk(path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                try:
                    total_size += os.path.getsize(fp)
                    file_count += 1
                except OSError:
                    pass
    except OSError:
        pass
    return total_size, file_count
