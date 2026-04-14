import os
import secrets

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

# auto_error=False prevents FastAPI from sending WWW-Authenticate header,
# which would trigger the browser's native Basic Auth popup dialog.
security = HTTPBasic(auto_error=False)


def require_admin(credentials: HTTPBasicCredentials = Depends(security)):
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    admin_password = os.getenv("ADMIN_PASSWORD")
    if not admin_password:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin not configured",
        )

    valid_username = secrets.compare_digest(credentials.username.encode(), b"admin")
    valid_password = secrets.compare_digest(
        credentials.password.encode(), admin_password.encode()
    )

    if not (valid_username and valid_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    return credentials
