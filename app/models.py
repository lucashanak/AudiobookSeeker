from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class DownloadRequest(BaseModel):
    title: str
    indexer: str = ""
    download_url: str = ""
    magnet_url: str = ""
    size: int = 0
    seeders: int = 0


class SettingsUpdate(BaseModel):
    prowlarr_url: str | None = None
    prowlarr_api_key: str | None = None
    qbit_url: str | None = None
    qbit_user: str | None = None
    qbit_pass: str | None = None
    abs_url: str | None = None
    abs_user: str | None = None
    abs_pass: str | None = None
    qbit_save_path: str | None = None
    audiobook_dir: str | None = None


class CreateUserRequest(BaseModel):
    username: str
    password: str
    is_admin: bool = False


class ChangePasswordRequest(BaseModel):
    new_password: str
