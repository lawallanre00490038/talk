import asyncio
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.db.session import get_async_session_maker, create_tables
from app.db.models import User, Institution, InstitutionProfile, StudentProfile, Post, UploadedDocument, StudentResource
from app.core.auth import get_password_hash
from app.db.repositories.institution_repo import institution_repo


async def seed_all():
    """Seed database with institutions, users, posts, and resources.
    
    This function is idempotent — it will skip existing data and create only new records.
    """
    # create tables first
    await create_tables()

    session_maker = get_async_session_maker(force_new=True)
    async with session_maker() as session:
        # Define institutions
        institutions_data = [
            {
                "id": "unilag",
                "institution_name": "University of Lagos",
                "institution_email": "info@unilag.edu.ng",
                "institution_profile_picture": "https://i.pinimg.com/736x/7c/0e/fe/7c0efec92682d80048147b2e73d3c4d2.jpg",
                "institution_description": "The University of Lagos (UNILAG) is a federal university founded in 1962. It is one of Nigeria's first-generation universities and a leading academic institution in West Africa.",
                "institution_location": "Akoka, Yaba, Lagos State, Nigeria",
                "institution_website": "https://unilag.edu.ng"
            },
            {
                "id": "ileife",
                "institution_name": "Obafemi Awolowo University (formerly University of Ife)",
                "institution_email": "info@oauife.edu.ng",
                "institution_profile_picture": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTfwWX6sdVsQrNytuqVQjijmgSGpet1NZQg7w&s",
                "institution_description": "Obafemi Awolowo University, located in Ile-Ife, Osun State, Nigeria, was established in 1961. It is renowned for academic excellence, cultural heritage, and student activism.",
                "institution_location": "Ile-Ife, Osun State, Nigeria",
                "institution_website": "https://oauife.edu.ng"
            },
            {
                "id": "yabatech",
                "institution_name": "Yaba College of Technology",
                "institution_email": "info@yabatech.edu.ng",
                "institution_profile_picture": "https://i0.wp.com/educeleb.com/wp-content/uploads/2017/09/YabaTech-logo.jpg?fit=505%2C523&ssl=1",
                "institution_description": "Yaba College of Technology (YABATECH), established in 1947, is Nigeria's first higher educational institution and a leading center for technical and vocational training.",
                "institution_location": "Yaba, Lagos State, Nigeria",
                "institution_website": "https://yabatech.edu.ng"
            }
        ]

        # Create institutions
        institutions = {}
        for inst_data in institutions_data:
            existing = await institution_repo.get(session, inst_data["id"])
            if existing:
                institutions[inst_data["id"]] = existing
                print(f"  ℹ️  Institution already exists: {inst_data['institution_name']}")
                continue

            institution = Institution(**inst_data)
            session.add(institution)
            await session.commit()
            await session.refresh(institution)
            institutions[inst_data["id"]] = institution
            print(f"  ✅ Created institution: {inst_data['institution_name']}")

        # Create student user and profile for UNILAG
        student_unilag_stmt = select(User).where(User.email == "student@unilag.edu")
        student_unilag_result = await session.execute(student_unilag_stmt)
        student_unilag = student_unilag_result.scalars().first()
        if not student_unilag:
            student_unilag = User(
                email="student@unilag.edu",
                full_name="Felix Gabriel",
                hashed_password=get_password_hash("password123"),
                role="student",
                is_verified=True,
            )
            session.add(student_unilag)
            await session.commit()
            await session.refresh(student_unilag)
            print(f"  ✅ Created user: {student_unilag.email}")
        else:
            print(f"  ℹ️  User already exists: {student_unilag.email}")

        # Link student to UNILAG
        try:
            student_profile_stmt = select(StudentProfile).where(StudentProfile.user_id == student_unilag.id)
            student_profile_result = await session.execute(student_profile_stmt)
            student_profile = student_profile_result.scalars().first()

            if not student_profile:
                student_profile = StudentProfile(
                    user_id=student_unilag.id,
                    institution_id=institutions["unilag"].id,
                    institution_name=institutions["unilag"].institution_name,
                    matric_number="150150150FG",
                    faculty="Faculty of Science and Technology",
                    department="Computer Science",
                    educational_level="100 Level",
                )
                session.add(student_profile)
                await session.commit()
                print(f"  ✅ Linked student to UNILAG")
            else:
                print(f"  ℹ️  Student profile already exists")
        except IntegrityError:
            await session.rollback()
            print(f"  ⚠️  Skipped duplicate student profile")

        print("\n✅ Seeding complete!")


if __name__ == "__main__":
    asyncio.run(seed_all())
