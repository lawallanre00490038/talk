from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status, Response, BackgroundTasks, Query
from datetime import timedelta
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.user_service import UserService
from app.utils.fastapi_email import EmailSchema, schedule_email
from app.errors import EmailAlreadyVerified
from app.core.auth import (
    create_access_token,
    get_current_user_dependency,
    verify_email_response,
    verify_password,
    generate_passwd_hash
)
from app.db.session import get_session, logger
from app.db.repositories.user_repo import institution_repo, student_profile_repo, user_repo
from app.schemas.auth import (
    InstitutionProfileRead,
    StudentProfileRead,
    TokenUser,
    UserCreateGeneralModel,
    UserCreateInstitutionModel,
    RegisterResponseModel,
    UserCreateRead,
    UserCreateStudentModel,
    UserLoginModel,
    LoginResponseModel
)
from app.db.models import StudentProfile, User, Institution, UserRole
from app.core.config import settings
from app.utils.resend_email import MailService

router = APIRouter()
user_service = UserService()
mail_service = MailService(resend=None, settings=settings)  # resend client injected later


# ==============================
# USER REGISTRATION ENDPOINT
# ==============================
@router.post("/register", response_model=RegisterResponseModel, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_in: UserCreateGeneralModel,
    bg_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session)
):
    """
    Register a new user.

    Steps:
    1. Check if the email already exists in the database.
    2. Hash the user’s password.
    3. Generate a username if not provided.
    4. Create a unique verification token.
    5. Save the user to the database.
    6. Send verification email in the background.

    Args:
        user_in (UserCreateGeneralModel): Input model with user registration data.
        bg_tasks (BackgroundTasks): FastAPI background tasks for async email sending.
        session (AsyncSession): SQLAlchemy async session.

    Returns:
        RegisterResponseModel: Status, message, and created user data.
    """
    db_user = await user_repo.get_by_email(session, email=user_in.email)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered."
        )

    hashed_password = generate_passwd_hash(user_in.password)
    username = user_in.username or user_in.email.split("@")[0]
    verification_token = str(uuid.uuid4())

    user_obj = User(
        email=user_in.email,
        username=username,
        full_name=user_in.full_name,
        verification_token=verification_token,
        hashed_password=hashed_password
    )

    created_user = await user_repo.create(session, obj_in=user_obj)
    logger.info(f"Created user {created_user.id}")


    # Run email in background
    # email_data = EmailSchema(
    #     email=[user_in.email],
    #     subject="Welcome to LagTalk 🎉",
    #     template_name="welcome.html",
    #     context={
    #         "name": user_in.full_name or username,
    #         "verify_link": f"{settings.FRONTEND_URL}/verify-email/{verification_token}"
    #     }
    # )

    # # Run email in background
    # schedule_email(bg_tasks, email_data)

    # Send verification email in the background
    bg_tasks.add_task(mail_service.send_verification_email, user_obj.email, str(user_obj.full_name), verification_token)

    return RegisterResponseModel(
        status=True,
        message="User created successfully, Please check your mail to verify your email address.",
        data=UserCreateRead.model_validate(created_user)
    )


# ==============================
# USER LOGIN ENDPOINT
# ==============================
@router.post("/login", response_model=LoginResponseModel)
async def login_for_access_token(
    form_data: UserLoginModel,
    response: Response,
    session: AsyncSession = Depends(get_session),
):
    """
    Authenticate a user and provide an access token.

    Steps:
    1. Retrieve the user by username.
    2. Verify the password.
    3. Generate JWT access token.
    4. Return the token along with email verification check.

    Args:
        form_data (UserLoginModel): Input model containing username and password.
        response (Response): FastAPI response object to attach cookies or headers.
        session (AsyncSession): SQLAlchemy async session.

    Returns:
        LoginResponseModel: Access token and user info.
    """
    user = await user_repo.get_by_username(session, username=form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(user=user, expires_delta=access_token_expires)
    return verify_email_response(user=user, access_token=access_token, response=response)


# ==============================
# EMAIL VERIFICATION ENDPOINT
# ==============================
@router.post("/verify-email/")
async def verify_email(
    session: Annotated[AsyncSession, Depends(get_session)],
    response: Response,
    token: str = Query(..., description="Verification token from email"),
):
    """
    Verify a user's email address using a token.

    Steps:
    1. Find user by verification token.
    2. Check if email is already verified.
    3. Update verification status and remove token.
    4. Commit changes to the database.
    5. Generate access token for verified user.

    Args:
        session (AsyncSession): SQLAlchemy async session.
        response (Response): FastAPI response object.
        token (str): Verification token sent via email.

    Returns:
        Response: FastAPI response with access token if successful.
    """
    user = await user_service.verify_token(token, session)

    if user.is_verified:
        raise EmailAlreadyVerified()

    user.is_verified = True
    user.verification_token = None
    await session.commit()
    await session.refresh(user)

    access_token = create_access_token(user=user)
    response = verify_email_response(user, access_token, response)
    return response


# ==============================
# CREATE STUDENT PROFILE ENDPOINT
# ==============================
@router.post("/create_student_profile", response_model=LoginResponseModel)
async def create_student_profile(
    student_profile_in: UserCreateStudentModel,
    current_user: Annotated[TokenUser, Depends(get_current_user_dependency(settings=settings))],
    session: AsyncSession = Depends(get_session),
):
    """
    Create a student profile for the current user.

    Restrictions:
    - User email must be verified.
    - User role cannot be INSTITUTION.
    - Cannot create profile if one already exists.

    Steps:
    1. Validate current user email and role.
    2. Check for existing student profile.
    3. Save new student profile.
    4. Update user role to STUDENT.

    Args:
        student_profile_in (UserCreateStudentModel): Input data for student profile.
        current_user (TokenUser): Authenticated current user.
        session (AsyncSession): SQLAlchemy async session.

    Returns:
        LoginResponseModel: Status, message, and created student profile data.
    """
    if not current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email not verified."
        )

    if current_user.role == UserRole.INSTITUTION:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Institution cannot create student profile."
        )

    db_user = await student_profile_repo.get_by_user_id(session, user_id=current_user.id)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Student profile already exists."
        )

    student_obj = StudentProfile(
        user_id=current_user.id,
        institution_name=student_profile_in.institution_name,
        institution_id=student_profile_in.institution_id,
        profile_picture=student_profile_in.profile_picture,
        matric_number=student_profile_in.matric_number,
        faculty=student_profile_in.faculty,
        department=student_profile_in.department,
        educational_level=student_profile_in.educational_level,
        course=student_profile_in.course
    )
    created_student = await student_profile_repo.create(session, obj_in=student_obj)

    user = await user_repo.get_by_email(session, email=current_user.email)
    user.role = UserRole.STUDENT
    await session.commit()

    logger.info(f"Created student {created_student.id}")

    return LoginResponseModel(
        status=True,
        message="Student profile created successfully",
        data=StudentProfileRead.model_validate(created_student)
    )


# ==============================
# CREATE INSTITUTION PROFILE ENDPOINT
# ==============================
@router.post("/create_institution_profile", response_model=LoginResponseModel)
async def create_institution_profile(
    institution_profile_in: UserCreateInstitutionModel,
    current_user: Annotated[TokenUser, Depends(get_current_user_dependency(settings=settings))],
    session: AsyncSession = Depends(get_session),
):
    """
    Create an institution profile for the current user.

    Restrictions:
    - User email must be verified.
    - User role cannot be STUDENT.
    - Cannot create profile if one already exists.

    Steps:
    1. Validate current user email and role.
    2. Check for existing institution profile.
    3. Save new institution profile.
    4. Update user role to INSTITUTION.

    Args:
        institution_profile_in (UserCreateInstitutionModel): Input data for institution profile.
        current_user (TokenUser): Authenticated current user.
        session (AsyncSession): SQLAlchemy async session.

    Returns:
        LoginResponseModel: Status, message, and created institution profile data.
    """
    if not current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email not verified."
        )

    if current_user.role == UserRole.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Student cannot create institution profile."
        )

    db_user = await institution_repo.get_by_user_id(session, user_id=current_user.id)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Institution profile already exists."
        )

    institution_obj = Institution(
        user_id=current_user.id,
        institution_name=institution_profile_in.institution_name,
        institution_email=institution_profile_in.institution_email or current_user.email,
        institution_description=institution_profile_in.institution_description,
        institution_website=institution_profile_in.institution_website,
        institution_location=institution_profile_in.institution_location,
    )
    created_institution = await institution_repo.create(session, obj_in=institution_obj)

    user = await user_repo.get_by_email(session, email=current_user.email)
    user.role = UserRole.INSTITUTION
    await session.commit()

    logger.info(f"Created institution {created_institution.id}")

    return LoginResponseModel(
        status=True,
        message="Institution profile created successfully",
        data=InstitutionProfileRead.model_validate(created_institution)
    )
