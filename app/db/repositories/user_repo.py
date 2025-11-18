# app/db/repositories/user_repo.py
from typing import Optional
from sqlmodel import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User, StudentProfile, Institution
from app.db.repositories.base import BaseRepository

class UserRepository(BaseRepository[User]):
    async def get_by_email(self, session: AsyncSession, *, email: str) -> Optional[User]:
        statement = select(User).where(User.email == email).options(selectinload(User.student_profile), selectinload(User.institution_profile))
        result = await session.execute(statement)
        return result.scalars().first()

    async def get_by_username(self, session: AsyncSession, *, username: str) -> Optional[User]:
        statement = select(User).where(User.username == username).options(selectinload(User.student_profile), selectinload(User.institution_profile))
        result = await session.execute(statement)
        return result.scalars().first()

user_repo = UserRepository(User)




class StudentProfileRepository(BaseRepository[StudentProfile]):
    async def get_by_user_id(self, session: AsyncSession, *, user_id: str) -> Optional[StudentProfile]:
        statement = select(StudentProfile).where(StudentProfile.user_id == user_id).options(selectinload(StudentProfile.institution))
        result = await session.execute(statement)
        return result.scalars().first()

student_profile_repo = StudentProfileRepository(StudentProfile)





class InstitutionRepository(BaseRepository[Institution]):
    async def get_by_user_id(self, session: AsyncSession, *, user_id: str) -> Optional[Institution]:
        # keep for compatibility but load related students/profiles lazily via selectin
        statement = select(Institution).where(Institution.user_id == user_id).options(selectinload(Institution.students), selectinload(Institution.institution_profiles))
        result = await session.execute(statement)
        return result.scalars().first()

institution_repo = InstitutionRepository(Institution)
