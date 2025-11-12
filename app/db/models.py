import profile
import uuid
import enum
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

from sqlalchemy import Column, JSON, Enum, DateTime
from sqlalchemy.sql.functions import user
from sqlmodel import Field, Relationship, SQLModel


class UserRole(str, enum.Enum):
    GENERAL = "general"
    STUDENT = "student"
    INSTITUTION = "institution"
    ADMIN = "admin"


class PostType(str, enum.Enum):
    POST = "post"
    REEL = "reel"


class PostPrivacy(str, enum.Enum):
    PUBLIC = "public"
    SCHOOL_ONLY = "school_only"
    FOLLOWERS_ONLY = "followers_only"


class MediaType(str, enum.Enum):
    IMAGE = "image"
    VIDEO = "video"


class NotificationType(str, enum.Enum):
    LIKE = "like"
    COMMENT = "comment"
    FOLLOW = "follow"
    MENTION = "mention"
    CHANNEL_INVITE = "channel_invite"



def generate_uuid() -> str:
    return str(uuid.uuid4())


# Link Models for Many-to-Many Relationships
class UserCommunityLink(SQLModel, table=True):
    user_id: str = Field(foreign_key="user.id", primary_key=True)
    community_id: str = Field(foreign_key="community.id", primary_key=True)


class UserChannelLink(SQLModel, table=True):
    user_id: str = Field(foreign_key="user.id", primary_key=True)
    channel_id: str = Field(foreign_key="channel.id", primary_key=True)
    is_admin: bool = Field(default=False)
    is_moderator: bool = Field(default=False)


# Main Models
class User(SQLModel, table=True):
    id: str = Field(default_factory=generate_uuid, primary_key=True, index=True)
    email: str = Field(unique=True, index=True)
    username: Optional[str] = Field(unique=True, default=None, index=True)
    hashed_password: str
    full_name: Optional[str] = None
    bio: Optional[str] = None
    profile_picture: Optional[str] = None
    is_active: bool = Field(default=True)
    verification_token: Optional[str]  = None
    is_verified: bool = Field(default=False)
    role: UserRole = Field(sa_column=Column(Enum(UserRole)), default=UserRole.GENERAL)
    
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True))
    )

    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), onupdate=datetime.now(timezone.utc))
    )

    student_profile: Optional["StudentProfile"] = Relationship(back_populates="user")
    institution_profile: Optional["InstitutionProfile"] = Relationship(back_populates="user")

    posts: List["Post"] = Relationship(back_populates="author")
    comments: List["Comment"] = Relationship(back_populates="author")
    likes: List["Like"] = Relationship(back_populates="user")
    complaints_filed: List["Complaint"] = Relationship(sa_relationship_kwargs={'foreign_keys':'[Complaint.reporter_id]'})
    notifications: List["Notification"] = Relationship(back_populates="user")
    
    communities: List["Community"] = Relationship(back_populates="members", link_model=UserCommunityLink)
    channels: List["Channel"] = Relationship(back_populates="members", link_model=UserChannelLink)





class StudentProfile(SQLModel, table=True):
    id: str = Field(default_factory=generate_uuid, primary_key=True)
    user_id: str = Field(foreign_key="user.id", unique=True)
    institution_id: Optional[str] = Field(foreign_key="institution.id", default=None)
    institution_name: Optional[str] = None

    profile_picture: Optional[str] = None
    faculty: Optional[str] = None
    department: Optional[str] = None
    matric_number: Optional[str]  = None
    educational_level: Optional[str]  = None
    course: Optional[str] = None
    graduation_year: Optional[int] = None
    
    user: User = Relationship(back_populates="student_profile")
    institution: Optional["Institution"] = Relationship(back_populates="students")



class Institution(SQLModel, table=True):
    id: str = Field(default_factory=generate_uuid, primary_key=True)
    institution_email: Optional[str] = Field(unique=True, index=True, default=None)
    institution_profile_picture: Optional[str] = None
    institution_name: str = Field(unique=True, index=True)
    institution_description: Optional[str] = None
    institution_website: Optional[str] = None
    institution_location: Optional[str] = None

    students: List["StudentProfile"] = Relationship(back_populates="institution")
    institution_profiles: List["InstitutionProfile"] = Relationship(back_populates="institution")



class InstitutionProfile(SQLModel, table=True):
    id: str = Field(default_factory=generate_uuid, primary_key=True)
    user_id: str = Field(foreign_key="user.id", unique=True)
    institution_id: str = Field(foreign_key="institution.id", unique=True)
    profile_picture: Optional[str] = None

    institution_name: str
    institution_email: str

    user: User = Relationship(back_populates="institution_profile")
    institution: Institution = Relationship(back_populates="institution_profiles")





class Community(SQLModel, table=True):
    id: str = Field(default_factory=generate_uuid, primary_key=True)
    name: str = Field(unique=True, index=True)
    description: str
    created_by: str = Field(foreign_key="user.id")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True))
    )

    members: List[User] = Relationship(back_populates="communities", link_model=UserCommunityLink)
    posts: List["Post"] = Relationship(back_populates="community")


class Channel(SQLModel, table=True):
    id: str = Field(default_factory=generate_uuid, primary_key=True)
    name: str = Field(index=True)
    description: str
    is_private: bool = Field(default=False)
    created_by: str = Field(foreign_key="user.id")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    members: List[User] = Relationship(back_populates="channels", link_model=UserChannelLink)
    posts: List["Post"] = Relationship(back_populates="channel")


class Post(SQLModel, table=True):
    id: str = Field(default_factory=generate_uuid, primary_key=True, index=True)
    author_id: str = Field(foreign_key="user.id", index=True)
    content: str
    post_type: PostType = Field(sa_column=Column(Enum(PostType)), default=PostType.POST)
    privacy: PostPrivacy = Field(sa_column=Column(Enum(PostPrivacy)), default=PostPrivacy.PUBLIC)
    school_scope: Optional[str] = Field(default=None, index=True) # e.g., "University of Lagos"
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True))
    )
    
    community_id: Optional[str] = Field(foreign_key="community.id", default=None)
    channel_id: Optional[str] = Field(foreign_key="channel.id", default=None)

    author: User = Relationship(back_populates="posts")
    media: List["Media"] = Relationship(back_populates="post")
    comments: List["Comment"] = Relationship(back_populates="post")
    likes: List["Like"] = Relationship(back_populates="post")
    community: Optional[Community] = Relationship(back_populates="posts")
    channel: Optional[Channel] = Relationship(back_populates="posts")


class Media(SQLModel, table=True):
    id: str = Field(default_factory=generate_uuid, primary_key=True)
    post_id: str = Field(foreign_key="post.id")
    media_type: MediaType = Field(sa_column=Column(Enum(MediaType)))
    url: str

    file_metadata: Dict[str, Any] = Field(
        sa_column=Column("metadata", JSON),
        default={}
    )

    post: "Post" = Relationship(back_populates="media")


class Comment(SQLModel, table=True):
    id: str = Field(default_factory=generate_uuid, primary_key=True)
    content: str
    author_id: str = Field(foreign_key="user.id")
    post_id: str = Field(foreign_key="post.id", index=True)
    parent_comment_id: Optional[str] = Field(foreign_key="comment.id", default=None)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True))
    )

    author: User = Relationship(back_populates="comments")
    post: Post = Relationship(back_populates="comments")
    likes: List["Like"] = Relationship(back_populates="comment")


class Like(SQLModel, table=True):
    id: str = Field(default_factory=generate_uuid, primary_key=True)
    user_id: str = Field(foreign_key="user.id")
    post_id: Optional[str] = Field(foreign_key="post.id", default=None)
    comment_id: Optional[str] = Field(foreign_key="comment.id", default=None)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True))
    )


    user: User = Relationship(back_populates="likes")
    post: Optional[Post] = Relationship(back_populates="likes")
    comment: Optional[Comment] = Relationship(back_populates="likes")


class Complaint(SQLModel, table=True):
    id: str = Field(default_factory=generate_uuid, primary_key=True)
    reporter_id: str = Field(foreign_key="user.id")
    reported_post_id: Optional[str] = Field(foreign_key="post.id", default=None)
    reported_comment_id: Optional[str] = Field(foreign_key="comment.id", default=None)
    reported_user_id: Optional[str] = Field(foreign_key="user.id", default=None)
    reason: str
    is_resolved: bool = Field(default=False)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True))
    )

class Notification(SQLModel, table=True):
    id: str = Field(default_factory=generate_uuid, primary_key=True)
    user_id: str = Field(foreign_key="user.id", index=True)
    notification_type: NotificationType = Field(sa_column=Column(Enum(NotificationType)))
    content: Dict[str, Any] = Field(sa_column=Column(JSON))
    is_read: bool = Field(default=False)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True))
    )

    user: User = Relationship(back_populates="notifications")

# Models for analysis and metrics (could be in a separate DB/service in a larger system)
class Sentiment(SQLModel, table=True):
    id: str = Field(default_factory=generate_uuid, primary_key=True)
    post_id: Optional[str] = Field(foreign_key="post.id", default=None)
    comment_id: Optional[str] = Field(foreign_key="comment.id", default=None)
    score: float # e.g., -1.0 to 1.0
    model_version: str
    analyzed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Analytics(SQLModel, table=True):
    id: str = Field(default_factory=generate_uuid, primary_key=True)
    entity_id: str = Field(index=True) # Could be post_id, user_id, etc.
    entity_type: str = Field(index=True) # "post", "user"
    metric_name: str # "views", "impressions"
    value: int
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))