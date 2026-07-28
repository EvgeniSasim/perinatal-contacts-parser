from fastapi import Depends, Header, HTTPException, status

from app.config import get_settings


def require_admin_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> None:
    expected = get_settings().admin_api_key
    if not x_api_key or x_api_key != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing API key")


AdminAuth = Depends(require_admin_api_key)
