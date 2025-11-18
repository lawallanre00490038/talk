import asyncio
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_async_session_maker, create_tables
from app.db.models import User, Institution, InstitutionProfile, StudentProfile, Post, UploadedDocument, StudentResource
from app.core.auth import get_password_hash
from app.db.repositories.institution_repo import institution_repo


async def seed_all():
    """Seed database with institutions, users, posts, and resources."""
    # create tables first
    await create_tables()

    session_maker = get_async_session_maker(force_new=True)
    async with session_maker() as session:  # type: AsyncSession
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
            # Check if institution already exists
            existing = await institution_repo.get_by_name(session, inst_data["institution_name"])
            if existing:
                institutions[inst_data["id"]] = existing
                continue

            institution = Institution(**inst_data)
            session.add(institution)
            await session.commit()
            await session.refresh(institution)
            institutions[inst_data["id"]] = institution

        # Create users
        general_user = User(
            email="general@example.com",
            full_name="General User",
            hashed_password=get_password_hash("password123"),
            role="general",
            is_verified=True,
        )

        student_unilag = User(
            email="student@unilag.edu",
            full_name="Felix Gabriel",
            hashed_password=get_password_hash("password123"),
            role="student",
            is_verified=True,
        )

        student_ileife = User(
            email="student@ileife.edu",
            full_name="Ade Ogunlade",
            hashed_password=get_password_hash("password123"),
            role="student",
            is_verified=True,
        )

        inst_admin_unilag = User(
            email="admin@unilag.edu.ng",
            full_name="Unilag Admin",
            hashed_password=get_password_hash("adminpass123"),
            role="institution",
            is_verified=True,
        )

        inst_admin_ileife = User(
            email="admin@oauife.edu.ng",
            full_name="OAU Admin",
            hashed_password=get_password_hash("adminpass123"),
            role="institution",
            is_verified=True,
        )

        session.add_all([general_user, student_unilag, student_ileife, inst_admin_unilag, inst_admin_ileife])
        await session.commit()
        await session.refresh(general_user)
        await session.refresh(student_unilag)
        await session.refresh(student_ileife)
        await session.refresh(inst_admin_unilag)
        await session.refresh(inst_admin_ileife)

        # Link institution admins
        unilag_admin_profile = InstitutionProfile(
            user_id=inst_admin_unilag.id,
            institution_id=institutions["unilag"].id,
            institution_name=institutions["unilag"].institution_name,
            institution_email=institutions["unilag"].institution_email or "",
        )
        ileife_admin_profile = InstitutionProfile(
            user_id=inst_admin_ileife.id,
            institution_id=institutions["ileife"].id,
            institution_name=institutions["ileife"].institution_name,
            institution_email=institutions["ileife"].institution_email or "",
        )
        session.add_all([unilag_admin_profile, ileife_admin_profile])

        # Link student profiles to institutions
        student_profile_unilag = StudentProfile(
            user_id=student_unilag.id,
            institution_id=institutions["unilag"].id,
            institution_name=institutions["unilag"].institution_name,
            matric_number="150150150FG",
            faculty="Faculty of Science and Technology",
            department="Computer Science",
            educational_level="100 Level",
        )
        student_profile_ileife = StudentProfile(
            user_id=student_ileife.id,
            institution_id=institutions["ileife"].id,
            institution_name=institutions["ileife"].institution_name,
            matric_number="OADSC001",
            faculty="Faculty of Science",
            department="Physics",
            educational_level="200 Level",
        )
        session.add_all([student_profile_unilag, student_profile_ileife])

        await session.commit()

        # Create posts for UNILAG (school-only and mirrored)
        unilag_school_post = Post(
            author_id=inst_admin_unilag.id,
            content="Welcome students to the University of Lagos campus! 🎓 Check the electric bus service to move around campus.",
            post_type="post",
            privacy="school_only",
            school_scope=institutions["unilag"].institution_name,
        )

        unilag_mirrored_post = Post(
            author_id=inst_admin_unilag.id,
            content="University of Lagos: Open day next week — all invited! Learn about our programs and campus life.",
            post_type="post",
            privacy="public",
            school_scope=None,
        )

        # Create posts for ILEIFE
        ileife_school_post = Post(
            author_id=inst_admin_ileife.id,
            content="Obafemi Awolowo University welcomes all students to the 2024/2025 academic session. Let's build greatness together! 🚀",
            post_type="post",
            privacy="school_only",
            school_scope=institutions["ileife"].institution_name,
        )

        session.add_all([unilag_school_post, unilag_mirrored_post, ileife_school_post])
        await session.commit()

        # Create student resources for UNILAG
        unilag_resource1 = StudentResource(
            institution_id=institutions["unilag"].id,
            title="Final Exam Timetable",
            description="PDF with final exam dates for all departments",
            url="https://unilag.edu.ng/exams/timetable.pdf",
            resource_type="pdf",
            created_by=inst_admin_unilag.id,
        )
        unilag_resource2 = StudentResource(
            institution_id=institutions["unilag"].id,
            title="Student Handbook",
            description="Complete guide for students at UNILAG",
            url="https://unilag.edu.ng/handbook.pdf",
            resource_type="pdf",
            created_by=inst_admin_unilag.id,
        )
        session.add_all([unilag_resource1, unilag_resource2])

        # Create student resources for ILEIFE
        ileife_resource1 = StudentResource(
            institution_id=institutions["ileife"].id,
            title="Academic Calendar 2024/2025",
            description="Important dates and academic schedule",
            url="https://oauife.edu.ng/calendar.pdf",
            resource_type="pdf",
            created_by=inst_admin_ileife.id,
        )
        session.add(ileife_resource1)

        # Create uploaded documents for RAG
        unilag_doc = UploadedDocument(
            institution_id=institutions["unilag"].id,
            title="Admission Brochure 2025",
            description="Comprehensive admission brochure for UNILAG",
            file_url="https://example.com/unilag/brochure.pdf",
            uploaded_by=inst_admin_unilag.id,
        )
        ileife_doc = UploadedDocument(
            institution_id=institutions["ileife"].id,
            title="OAU Course Catalogue",
            description="All available programs and courses at OAU",
            file_url="https://example.com/oau/courses.pdf",
            uploaded_by=inst_admin_ileife.id,
        )
        session.add_all([unilag_doc, ileife_doc])

        await session.commit()

        # Print summary
        print(" Database seeded successfully!")
        print(f"   Institutions: {len(institutions_data)}")
        print(f"   Users: general={general_user.email}, students={student_unilag.email} | {student_ileife.email}, admins={inst_admin_unilag.email} | {inst_admin_ileife.email}")
        print(f"   Posts, resources, and documents created for each institution.")


if __name__ == "__main__":
    asyncio.run(seed_all())
