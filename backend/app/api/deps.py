from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.db.session import get_db
from app.models.user import User, UserRole


bearer_scheme = HTTPBearer(auto_error=False)


#Tut ya vynes get_current_user, chtoby ne razduvat ostalnoy kod.
def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Требуется авторизация",
        )

    payload = decode_token(credentials.credentials, expected_type="access")
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Некорректные данные токена",
        )

    user = db.scalar(select(User).where(User.id == int(user_id)))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Пользователь не найден",
        )
    if not user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Аккаунт ожидает подтверждения администратора",
        )

    return user


#Tut obrabatyvayu require_write_access, vse po delu i bez lishnego.
def require_write_access(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.role == UserRole.viewer.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Роль наблюдателя имеет только доступ на чтение",
        )
    return current_user


#Tut ya vynes require_admin, chtoby ne razduvat ostalnoy kod.
def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Требуются права администратора",
        )
    return current_user
