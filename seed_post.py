import asyncio
import cloudinary
import cloudinary.api
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.db.session import get_async_session_maker
# Added InstitutionProfile/Institution to find the ID
from app.db.models import Institution, Post, Media, MediaType, PostType, PostPrivacy, User, InstitutionProfile

# Cloudinary Config
cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET,
    secure=True
)

ADMIN_EMAIL = "ab@yopmail.com"

SCHOOL_POSTS_DATA = [
    {
        "id": "yabatech",
        "folder": "yabatech_post",
        "content": """🎓 Celebrating Excellence: Yaba College of Technology (YABATECH) - Nigeria's First Higher Educational Institution!

📍 Situated in the heart of Yaba, Lagos, YABATECH holds the prestigious title of being Nigeria's first higher educational institution, established in 1947. As the country's premier technical college, we've been shaping innovators, entrepreneurs, and industry leaders for over 75 years!

✨ Why YABATECH?
✅ Pioneering Legacy: First higher institution in Nigeria (1947)
✅ Technical Excellence: Specialized in polytechnic education and vocational training
✅ Industry-Ready Graduates: Practical skills that meet market demands
"""
    },
    {
        "id": "ileife", # Matches your school_scope logic
        "folder": "oau_post",
        "content": """🏛️ Discover Obafemi Awolowo University (OAU): Nigeria's Most Beautiful Campus!

📍 Nestled in the ancient city of Ile-Ife, Osun State, OAU stands as one of Africa's most prestigious universities, renowned for its stunning architecture, academic excellence, and rich cultural heritage since 1961.

✨ Why OAU?
✅ Architectural Marvel: Award-winning campus
✅ Academic Prestige: Among Africa's top universities
✅ Cultural Heritage: Cradle of Yoruba civilization
✅ Research Excellence: Leading innovations across disciplines
"""
    },
    {
        "id": "unilag",
        "folder": "unilag_post",
        "content":  """🎓 Discover the University of Lagos (UNILAG): Nigeria's Premier Institution!

📍 Located in the vibrant heart of Akoka, Yaba, UNILAG stands as one of Nigeria's foremost universities with over 60 years of academic excellence.

✨ Why UNILAG?
✅ Academic Excellence: Top-ranked in Africa
✅ Innovation Hub: Research & tech leadership
✅ Vibrant Campus Life
✅ Global Alumni Network
"""
    }
]






async def fetch_cloudinary_images(folder: str) -> list[str]:
    try:
        result = cloudinary.api.resources(
            type="upload",
            resource_type="image",
            prefix=folder,
            max_results=20
        )
        return [r["secure_url"] for r in result.get("resources", [])]
    except Exception as e:
        print(f"⚠️ Cloudinary fetch failed for {folder}: {e}")
        return []

async def seed_school_posts():
    async_session_maker = get_async_session_maker()
    async with async_session_maker() as session:
        # 1. Get admin user
        result = await session.execute(select(User).where(User.email == ADMIN_EMAIL))
        admin_user = result.scalar_one_or_none()
        if not admin_user:
            print(f"❌ Admin user {ADMIN_EMAIL} not found.")
            return

        for data in SCHOOL_POSTS_DATA:
            # 2. Query the CORRECT model (Institution)
            inst_result = await session.execute(
                select(Institution).where(Institution.id == data["id"])
            )
            institution = inst_result.scalar_one_or_none()
            
            if not institution:
                print(f"❌ Skipping {data['id']}: Not found in Institution table.")
                continue

            image_urls = await fetch_cloudinary_images(data["folder"])

            # 3. Create 10 posts
            for i in range(1, 11):
                post = Post(
                    author_id=admin_user.id,
                    content=f"Post #{i} for {institution.institution_name}\n\n{data['content']}",
                    post_type=PostType.POST,
                    privacy=PostPrivacy.PUBLIC,
                    school_scope=institution.id, 
                )
                session.add(post)
                await session.flush()

                if image_urls:
                    url = image_urls[(i - 1) % len(image_urls)]
                    session.add(Media(
                        post_id=post.id,
                        media_type=MediaType.IMAGE,
                        url=url,
                        file_metadata={"seed": True}
                    ))

            print(f"✅ Created 10 posts for {institution.institution_name}")

        await session.commit()
        print("\n🚀 Seeding successful!")

if __name__ == "__main__":
    asyncio.run(seed_school_posts())