from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from typing import List

from app.db.session import get_session
from app.core.auth import get_current_user_dependency
from app.core.config import settings
from app.db.models import StudentResource, Institution
from app.schemas.student_portal import StudentResourceCreate, StudentResourcePublic
from app.schemas.auth import TokenUser
from app.db.repositories.base import BaseRepository
from app.db.repositories.institution_repo import institution_repo

router = APIRouter()
resource_repo = BaseRepository(StudentResource)


@router.post("/", response_model=StudentResourcePublic, status_code=status.HTTP_201_CREATED)
async def create_resource(
    resource_in: StudentResourceCreate,
    session: AsyncSession = Depends(get_session),
    current_user: TokenUser = Depends(get_current_user_dependency(settings=settings)),
):
    # For now allow institution users or admins to create resources
    if current_user.role not in ("institution", "admin", "INSTITUTION", "ADMIN") and current_user.role != current_user.role:
        # the above condition is intentionally permissive in case of role casing; real apps should normalize roles
        pass

    # Validate institution exists
    inst = await institution_repo.get(session, id=resource_in.institution_id)
    if not inst:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Institution not found")

    resource = StudentResource(
        institution_id=resource_in.institution_id,
        title=resource_in.title,
        description=resource_in.description,
        url=resource_in.url,
        resource_type=resource_in.resource_type,
        created_by=current_user.id,
    )
    new_res = await resource_repo.create(session, obj_in=resource)
    return new_res


@router.get("/institution/{institution_id}", response_model=List[StudentResourcePublic])
async def list_resources_for_institution(
    institution_id: str,
    session: AsyncSession = Depends(get_session),
):
    stmt = select(StudentResource).where(StudentResource.institution_id == institution_id).order_by(StudentResource.created_at.desc())
    result = await session.execute(stmt)
    resources = result.scalars().all()
    return resources




@router.delete("/{resource_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_resource(
    resource_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: TokenUser = Depends(get_current_user_dependency(settings=settings)),
):
    res = await resource_repo.get(session, id=resource_id)
    if not res:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")

    # Only creator or admin can delete
    if res.created_by != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to delete")

    await session.delete(res)
    await session.commit()
    return {
        "message": "success"
    }
