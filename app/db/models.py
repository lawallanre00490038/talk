import profile
import uuid
import enum
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
import sqlalchemy as sa
from sqlalchemy import Column, JSON, Enum, DateTime
from sqlalchemy.sql.functions import user
from sqlmodel import Field, Relationship, SQLModel, func


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


class ConversationUserLink(SQLModel, table=True):
    user_id: str = Field(foreign_key="user.id", primary_key=True)
    conversation_id: str = Field(foreign_key="conversation.id", primary_key=True)
    is_muted: bool = Field(default=False)


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
    is_onboarding_completed: bool = Field(default=False, nullable=True)
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

    student_profile: Optional["StudentProfile"] = Relationship(
        back_populates="user", 
        sa_relationship_kwargs={"cascade": "all, delete-orphan", "lazy": "selectin"}
    )
    institution_profile: Optional["InstitutionProfile"] = Relationship(
        back_populates="user", 
        sa_relationship_kwargs={"cascade": "all, delete-orphan", "lazy": "selectin"}
    )

    posts: List["Post"] = Relationship(back_populates="author", sa_relationship_kwargs={"lazy": "selectin"})
    comments: List["Comment"] = Relationship(back_populates="author", sa_relationship_kwargs={"lazy": "selectin"})
    likes: List["Like"] = Relationship(back_populates="user", sa_relationship_kwargs={"lazy": "selectin"})
    complaints_filed: List["Complaint"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[Complaint.reporter_id]", "lazy": "selectin"}
    )
    notifications: List["Notification"] = Relationship(back_populates="user", sa_relationship_kwargs={"lazy": "selectin"})
    
    communities: List["Community"] = Relationship(
        back_populates="members", link_model=UserCommunityLink, sa_relationship_kwargs={"lazy": "selectin"}
    )
    channels: List["Channel"] = Relationship(
        back_populates="members", link_model=UserChannelLink, sa_relationship_kwargs={"lazy": "selectin"}
    )
    # Conversations (direct messages)
    conversations: List["Conversation"] = Relationship(
        back_populates="members", link_model=ConversationUserLink, sa_relationship_kwargs={"lazy": "selectin"}
    )
    messages_sent: List["Message"] = Relationship(back_populates="sender", sa_relationship_kwargs={"lazy": "selectin"})





class StudentProfile(SQLModel, table=True):
    id: str = Field(default_factory=generate_uuid, primary_key=True)
    user_id: str = Field(foreign_key="user.id", unique=True)
    institution_id: Optional[str] = Field(foreign_key="institution.id", default=None)
    institution_name: Optional[str] = None
    faculty: Optional[str] = None
    department: Optional[str] = None
    matric_number: Optional[str]  = None
    educational_level: Optional[str]  = None
    course: Optional[str] = None
    graduation_year: Optional[int] = None
    
    user: User = Relationship(back_populates="student_profile", sa_relationship_kwargs={"lazy": "selectin"})
    institution: Optional["Institution"] = Relationship(back_populates="students", sa_relationship_kwargs={"lazy": "selectin"})



class Institution(SQLModel, table=True):
    id: str = Field(default_factory=generate_uuid, primary_key=True)
    institution_email: Optional[str] = Field(unique=True, index=True, default=None)
    institution_profile_picture: Optional[str] = None
    institution_name: str = Field(unique=True, index=True)
    institution_description: Optional[str] = None
    institution_website: Optional[str] = None
    institution_location: Optional[str] = None

    students: List["StudentProfile"] = Relationship(back_populates="institution", sa_relationship_kwargs={"lazy": "selectin"})
    institution_profiles: List["InstitutionProfile"] = Relationship(back_populates="institution", sa_relationship_kwargs={"lazy": "selectin"})
    student_resources: List["StudentResource"] = Relationship(back_populates="institution", sa_relationship_kwargs={"lazy": "selectin"})
    uploaded_documents: List["UploadedDocument"] = Relationship(back_populates="institution", sa_relationship_kwargs={"lazy": "selectin"})



class InstitutionProfile(SQLModel, table=True):
    id: str = Field(default_factory=generate_uuid, primary_key=True)
    user_id: str = Field(foreign_key="user.id", unique=True)
    institution_id: str = Field(foreign_key="institution.id")
    profile_picture: Optional[str] = None

    institution_name: str
    institution_email: str

    user: User = Relationship(back_populates="institution_profile", sa_relationship_kwargs={"lazy": "selectin"})
    institution: Institution = Relationship(back_populates="institution_profiles", sa_relationship_kwargs={"lazy": "selectin"})





class Community(SQLModel, table=True):
    id: str = Field(default_factory=generate_uuid, primary_key=True)
    name: str = Field(unique=True, index=True)
    description: str
    created_by: str = Field(foreign_key="user.id")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True))
    )

    members: List[User] = Relationship(back_populates="communities", link_model=UserCommunityLink, sa_relationship_kwargs={"lazy": "selectin"})
    posts: List["Post"] = Relationship(back_populates="community", sa_relationship_kwargs={"lazy": "selectin"})


class Channel(SQLModel, table=True):
    id: str = Field(default_factory=generate_uuid, primary_key=True)
    name: str = Field(index=True)
    description: str
    is_private: bool = Field(default=False)
    created_by: str = Field(foreign_key="user.id")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    members: List[User] = Relationship(back_populates="channels", link_model=UserChannelLink, sa_relationship_kwargs={"lazy": "selectin"})
    posts: List["Post"] = Relationship(back_populates="channel", sa_relationship_kwargs={"lazy": "selectin"})


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

    author: User = Relationship(back_populates="posts", sa_relationship_kwargs={"lazy": "selectin"})
    media: List["Media"] = Relationship(back_populates="post", sa_relationship_kwargs={"lazy": "selectin"})
    comments: List["Comment"] = Relationship(back_populates="post", sa_relationship_kwargs={"lazy": "selectin"})
    likes: List["Like"] = Relationship(back_populates="post", sa_relationship_kwargs={"lazy": "selectin"})
    community: Optional[Community] = Relationship(back_populates="posts", sa_relationship_kwargs={"lazy": "selectin"})
    channel: Optional[Channel] = Relationship(back_populates="posts", sa_relationship_kwargs={"lazy": "selectin"})


class Media(SQLModel, table=True):
    id: str = Field(default_factory=generate_uuid, primary_key=True)
    post_id: str = Field(foreign_key="post.id")
    media_type: MediaType = Field(sa_column=Column(Enum(MediaType)))
    url: str

    file_metadata: Dict[str, Any] = Field(
        sa_column=Column("metadata", JSON),
        default={}
    )

    post: "Post" = Relationship(back_populates="media", sa_relationship_kwargs={"lazy": "selectin"})


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

    author: User = Relationship(back_populates="comments", sa_relationship_kwargs={"lazy": "selectin"})
    post: Post = Relationship(back_populates="comments", sa_relationship_kwargs={"lazy": "selectin"})
    likes: List["Like"] = Relationship(back_populates="comment", sa_relationship_kwargs={"lazy": "selectin"})


class Like(SQLModel, table=True):
    id: str = Field(default_factory=generate_uuid, primary_key=True)
    user_id: str = Field(foreign_key="user.id")
    post_id: Optional[str] = Field(foreign_key="post.id", default=None)
    comment_id: Optional[str] = Field(foreign_key="comment.id", default=None)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True))
    )


    user: User = Relationship(back_populates="likes", sa_relationship_kwargs={"lazy": "selectin"})
    post: Optional[Post] = Relationship(back_populates="likes", sa_relationship_kwargs={"lazy": "selectin"})
    comment: Optional[Comment] = Relationship(back_populates="likes", sa_relationship_kwargs={"lazy": "selectin"})


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


class Conversation(SQLModel, table=True):
    id: str = Field(default_factory=generate_uuid, primary_key=True)
    title: Optional[str] = None
    is_group: bool = Field(default=False)
    created_by: Optional[str] = Field(foreign_key="user.id", default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    members: List[User] = Relationship(back_populates="conversations", link_model=ConversationUserLink, sa_relationship_kwargs={"lazy": "selectin"})
    messages: List["Message"] = Relationship(back_populates="conversation", sa_relationship_kwargs={"lazy": "selectin"})


class Message(SQLModel, table=True):
    id: str = Field(default_factory=generate_uuid, primary_key=True)
    conversation_id: str = Field(foreign_key="conversation.id", index=True)
    sender_id: str = Field(foreign_key="user.id", index=True)
    content: str
    attachments: Dict[str, Any] = Field(sa_column=Column(JSON), default={})
    is_read: bool = Field(default=False)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    conversation: Conversation = Relationship(back_populates="messages", sa_relationship_kwargs={"lazy": "selectin"})
    sender: User = Relationship(back_populates="messages_sent", sa_relationship_kwargs={"lazy": "selectin"})


class StudentResource(SQLModel, table=True):
    """Resources and links exposed to students via a Student Portal (per institution)."""
    id: str = Field(default_factory=generate_uuid, primary_key=True)
    institution_id: str = Field(foreign_key="institution.id", index=True)
    title: str
    description: Optional[str] = None
    url: Optional[str] = None
    resource_type: Optional[str] = None
    created_by: Optional[str] = Field(foreign_key="user.id", default=None)

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=sa.Column(sa.DateTime(timezone=True))  # <--- correct way
    )


    institution: Institution = Relationship(back_populates="student_resources", sa_relationship_kwargs={"lazy": "selectin"})


class UploadedDocument(SQLModel, table=True):
    id: str = Field(default_factory=generate_uuid, primary_key=True)
    institution_id: str = Field(foreign_key="institution.id", index=True)
    title: str
    description: Optional[str] = None
    file_url: str
    file_metadata: Dict[str, Any] = Field(sa_column=Column(JSON), default={})
    uploaded_by: Optional[str] = Field(foreign_key="user.id", default=None)
    is_processed: bool = Field(default=False)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=sa.Column(sa.DateTime(timezone=True))  # <--- correct way
    )

    institution: Institution = Relationship(back_populates="uploaded_documents", sa_relationship_kwargs={"lazy": "selectin"})

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

    user: User = Relationship(back_populates="notifications", sa_relationship_kwargs={"lazy": "selectin"})


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
