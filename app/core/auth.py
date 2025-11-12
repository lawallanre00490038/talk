# app/core/auth.py
import logging
from datetime import datetime, timedelta, timezone
import jwt, logging
from passlib.context import CryptContext
from fastapi import Request, Depends, Response, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from typing import Optional
from datetime import datetime


from app.schemas.auth import TokenUser, LoginResponseModel
from app.core.config import settings, BaseSettings
from app.db.models import User, UserRole
from app.errors import UnAuthenticated, UserNotFound, InvalidToken


passwd_context = CryptContext(schemes=["bcrypt"])
ACCESS_TOKEN_EXPIRE_MINUTES = 30
logger = logging.getLogger(__name__)


class OptionalOAuth2Scheme(OAuth2PasswordBearer):
    async def __call__(self, request: Request) -> Optional[str]:
        try:
            return await super().__call__(request)
        except Exception:
            return None

# Replace with the optional version
optional_oauth2_scheme = OptionalOAuth2Scheme(tokenUrl="token")


def generate_passwd_hash(password: str) -> str:
    hash = passwd_context.hash(password)

    return hash


def verify_password(password: str, hash: str) -> bool:
    return passwd_context.verify(password, hash)

def get_password_hash(password: str):
    return passwd_context.hash(password)


def decode_token(token: str, settings: BaseSettings) -> dict:
    try:
        if isinstance(token, str):
            token = token.encode("utf-8")

        token_data = jwt.decode(
            jwt=token, key=settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )

        return token_data

    except jwt.PyJWTError as e:
        logging.exception(e)
        return None


ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 300


def create_access_token(user, expires_delta: timedelta | None = None):
    to_encode = {
        "sub": user.email,
        "id": str(user.id),
        "is_verified": user.is_verified,
        "full_name": user.full_name,
        "role": user.role,
        "exp": datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    }
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)



def get_current_user_dependency(settings: BaseSettings):
    def get_current_user(
        request: Request,
        token: Optional[str] = Depends(optional_oauth2_scheme),
    ) -> TokenUser:
        access_token = token or request.cookies.get("access_token")

        if not access_token:
            raise UnAuthenticated(
                message="You are not authenticated. Please login to continue"
            )

        try:
            payload = decode_token(access_token, settings)
            email = payload.get("sub")
            user_id = payload.get("id")
            full_name = payload.get("full_name")
            role = payload.get("role")

            if not email or not user_id:
                raise UserNotFound()

            return TokenUser(
                full_name=full_name,
                email=email,
                id=user_id,
                is_verified=payload.get("is_verified"),
                role=role,
                access_token=access_token,
                token_type="bearer"
            )

        except jwt.ExpiredSignatureError:
            raise InvalidToken()
        except jwt.PyJWTError as e:
            # use your logger if needed
            raise UnAuthenticated()

    return get_current_user



def verify_email_response(user, access_token: str, response: Response):

    print("This is the user", user)

    user_data = {
        "id": str(user.id),
        "full_name": user.full_name,
        "email": user.email,
        "role": user.role,
        "is_verified": user.is_verified,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
    }

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True, 
        max_age=18000, 
        samesite="none",
        secure=True,
    )

    return LoginResponseModel(
        status=True,
        message="User successfully logged in",
        data=user_data
    )




def get_optional_current_user_dependency(settings):
    def optional_dependency(
        request: Request,
        token: Optional[str] = Depends(optional_oauth2_scheme)
    ) -> Optional[TokenUser]:
        access_token = token or request.cookies.get("access_token")
        if not access_token:
            return None

        try:
            payload = decode_token(access_token, settings)
            email = payload.get("sub")
            user_id = payload.get("id")
            full_name = payload.get("full_name")
            role = payload.get("role")

            if not email or not user_id:
                return None

            return TokenUser(
                full_name=full_name,
                email=email,
                id=user_id,
                is_verified=payload.get("is_verified"),
                role=role,
                access_token=access_token,
                token_type="bearer"
            )
        except jwt.ExpiredSignatureError:
            return None
        except jwt.PyJWTError:
            return None

    return optional_dependency



def json_serializer(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")



# current_user: Annotated[TokenUser, Depends(get_current_user_dependency(settings=settings))],


# Role-based access control dependencies
def require_role(required_role: UserRole):
    """Dependency factory for requiring a specific user role."""
    def role_checker(current_user: TokenUser = Depends(get_current_user_dependency(settings=settings))) -> User:
        if current_user.role != required_role and current_user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation not permitted. Requires '{required_role.value}' role."
            )
        return current_user
    return role_checker

require_admin = require_role(UserRole.ADMIN)
require_student = require_role(UserRole.STUDENT)
require_institution = require_role(UserRole.INSTITUTION)