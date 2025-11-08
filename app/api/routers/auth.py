# app/api/routers/auth.py
from turtle import st
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status,  Response, BackgroundTasks, Query
import resend
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import timedelta
import uuid


from app.services.user_service import UserService
from app.utils.fastapi_email import EmailSchema, schedule_email
from app.errors import (
   EmailAlreadyVerified
)
from app.core.auth import create_access_token, get_current_user_dependency, verify_email_response, verify_password, generate_passwd_hash
from app.db.session import get_session, logger
from app.db.repositories.user_repo import institution_repo, student_profile_repo, user_repo
from app.schemas.auth import InstitutionProfileRead, StudentProfileRead, TokenUser, UserCreateGeneralModel, UserCreateInstitutionModel, RegisterResponseModel, UserCreateRead, UserCreateStudentModel,  UserLoginModel, LoginResponseModel
from app.db.models import StudentProfile, User, Institution, UserRole
from app.core.config import settings
from app.utils.resend_email import MailService


router = APIRouter()
user_service = UserService()
mail_service = MailService(resend=resend, settings=settings)

@router.post("/register", response_model=RegisterResponseModel, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_in: UserCreateGeneralModel,
    bg_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session)
):
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

    bg_tasks.add_task(mail_service.send_verification_email, user_obj.email, str(user_obj.full_name), verification_token)
    
    return RegisterResponseModel(
        status=True,
        message="User created successfully, Please check your mail to verify your email address.",
        data=UserCreateRead.model_validate(created_user)
    )



@router.post("/login", response_model=LoginResponseModel)
async def login_for_access_token(
    form_data: UserLoginModel,
    response: Response,
    session: AsyncSession = Depends(get_session),
    
):
    user = await user_repo.get_by_username(session, username=form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        user=user, expires_delta=access_token_expires
    )
    return verify_email_response(
        user=user, access_token=access_token, response=response
    )


@router.post("/verify-email/")
async def verify_email(
    session: Annotated[AsyncSession, Depends(get_session)],
    response: Response,
    token: str = Query(..., description="Verification token from email"),
):
    """Verify user's email using the provided token."""
    # Retrieve user based on the verification token
    user = await user_service.verify_token(token, session)

    if user.is_verified:
        raise EmailAlreadyVerified()

    # Update user verification status
    user.is_verified = True
    user.verification_token = None
    
    # Commit changes to the database
    await session.commit()
    await session.refresh(user)


    print("The user from ", user)
    
    # Generate access token for the verified user
    access_token = create_access_token(user=user)
    
    # Prepare response
    response = verify_email_response(user, access_token, response)
    
    return response



@router.post("/create_student_profile", response_model=LoginResponseModel)
async def create_student_profile(
    student_profile_in: UserCreateStudentModel,
    current_user: Annotated[TokenUser, Depends(get_current_user_dependency(settings=settings))],
    session: AsyncSession = Depends(get_session),
):
    # Check if email is verified
    if not current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email not verified."
        )
    # If role is institutoion, then flag
    if current_user.role == UserRole.INSTITUTION:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Institution cannot create student profile."
        )

    # Check if student profile already exists
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

    print(
        f"Created student profile {student_obj}\n\n"
    )
    
    # Change user role to student in the user table
    user = await user_repo.get_by_email(session, email=current_user.email)
    user.role = UserRole.STUDENT
    await session.commit()

    logger.info(f"Created student {created_student.id}")

    return LoginResponseModel(
        status=True,
        message="Student profile created successfully",
        data=StudentProfileRead.model_validate(created_student)
    )




@router.post("/create_institution_profile", response_model=LoginResponseModel)
async def create_institution_profile(
    institution_profile_in: UserCreateInstitutionModel,
    current_user: Annotated[TokenUser, Depends(get_current_user_dependency(settings=settings))],
    session: AsyncSession = Depends(get_session),
):  
    # Check if email is verified
    if not current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email not verified."
        )
    
    # If role is student, then flag
    if current_user.role == UserRole.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Student cannot create institution profile."
        )

    # Check if institution profile already exists
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
    logger.info(f"Created institution {created_institution.id}")

    # Change user  role to institution in the user table
    user = await user_repo.get_by_email(session, email=current_user.email)
    user.role = UserRole.INSTITUTION
    await session.commit()

    return LoginResponseModel(
        status=True,
        message="Institution profile created successfully",
        data=InstitutionProfileRead.model_validate(created_institution)
    )
