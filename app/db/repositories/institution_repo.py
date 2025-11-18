from typing import Optional
from sqlmodel import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Institution, UploadedDocument, Post, InstitutionProfile


class InstitutionRepository:
    def __init__(self):
        pass

    async def get(self, session: AsyncSession, id: str) -> Optional[Institution]:
        # use selectinload to eagerly load related collections safely in async context
        return await session.get(Institution, id, options=[selectinload(Institution.students), selectinload(Institution.institution_profiles)])

    async def get_by_name(self, session: AsyncSession, name: str) -> Optional[Institution]:
        statement = select(Institution).where(Institution.institution_name == name)
        statement = statement.options(selectinload(Institution.students), selectinload(Institution.uploaded_documents))
        result = await session.execute(statement)
        return result.scalars().first()

    async def get_students_count(self, session: AsyncSession, institution_id: str) -> int:
        institution = await session.get(Institution, institution_id, options=[selectinload(Institution.students)])
        if not institution:
            return 0
        return len(institution.students) if hasattr(institution, "students") else 0

    async def get_posts_count(self, session: AsyncSession, institution: Institution) -> int:
        # Count posts that have school_scope matching institution name
        statement = select(Post).where(Post.school_scope == institution.institution_name)
        # use a count query instead of loading all rows
        result = await session.execute(statement)
        return result.scalars().all().__len__()

    async def create_document(self, session: AsyncSession, *, obj_in: UploadedDocument) -> UploadedDocument:
        session.add(obj_in)
        await session.commit()
        await session.refresh(obj_in)
        return obj_in

    async def get_documents_for_institution(self, session: AsyncSession, institution_id: str):
        statement = select(UploadedDocument).where(UploadedDocument.institution_id == institution_id)
        statement = statement.options(selectinload(UploadedDocument.institution))
        result = await session.execute(statement)
        return result.scalars().all()

    async def get_document(self, session: AsyncSession, id: str):
        return await session.get(UploadedDocument, id)

    async def is_user_institution_admin(self, session: AsyncSession, user_id: str, institution_id: str) -> bool:
        """Return True if the given user has an InstitutionProfile for the given institution_id."""
        statement = select(InstitutionProfile).where(
            InstitutionProfile.user_id == user_id,
            InstitutionProfile.institution_id == institution_id,
        )
        result = await session.execute(statement.options(selectinload(InstitutionProfile.user)))
        return result.scalars().first() is not None


institution_repo = InstitutionRepository()
