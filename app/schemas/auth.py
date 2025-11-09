from datetime import datetime
import profile
from typing import Optional, Any, List
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from app.db.models import UserRole



class UserBase(BaseModel):
    full_name: str
    email: EmailStr


class AdminCreate(UserBase):
    full_name: str
    email: EmailStr
    password: str
    role: Optional[UserRole] = UserRole.ADMIN


class UserCreateGeneralModel(BaseModel):
    full_name: Optional[str] = None
    email:  Optional[EmailStr] = None
    role: Optional[UserRole] = UserRole.GENERAL
    password: str


    model_config = {
        "json_schema_extra": {
            "example": {
                "full_name": "John Doe",
                "email": "johndoe123@co.com",
                "role": "general",
                "password": "testpass123",
            }
        }
    }

class UserCreateStudentModel(BaseModel):
    # Student Profile
    
    institution_name: Optional[str] = None
    institution_id: Optional[str] = None

    matric_number: Optional[str] = None
    faculty: Optional[str] = None
    department: Optional[str] = None
    profile_picture: Optional[str] = None
    educational_level: Optional[str] = None
    course: Optional[str] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "matric_number": "150150150FG",
                "institution_name": "XYZ University",
                "institution_id": "xyz-university-123",
                "faculty": "Faculty of Science and Technology",
                "department": "Department of Computer Science",
                "profile_picture": "https://example.com/profile_picture.jpg",
                "educational_level": "Undergraduate",
                "course": "Computer Science",
            }
        }
    }

class UserCreateInstitutionModel(BaseModel):
    # Institution Profile
    institution_name: Optional[str] = None
    institution_email: Optional[EmailStr] = None
    institution_website: Optional[str] = None
    institution_location: Optional[str] = None
    institution_description: Optional[str] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "institution_name": "XYZ University",
                "institution_email": "xyzuniversity@co.com",
                "institution_website": "www.xyzuniversity.com",
                "institution_location": "123 Main St, Anytown USA",
                "institution_description": "XYZ University is a leading university in the field of Computer Science and Engineering.",
            }
        }
    }



class UserLoginModel(BaseModel):
    email: Optional[EmailStr] = None
    password: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "johndoe123@co.com",
                "password": "testpass123",
            }
        }
    }


class UserPublic(UserBase):
    id: str
    profile_picture: Optional[str] = None
    role: UserRole

    model_config = ConfigDict(from_attributes=True)


class ForgotPasswordModel(BaseModel):
    email: EmailStr


class ResetPasswordModel(BaseModel):
    password: str

class ResetPasswordSchemaResponseModel(BaseModel):
    status: bool
    message: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "status": True,
                "message": "Password reset email sent successfully."
            }
        }
    }




class FeedbackCreateModel(BaseModel):
    fullname: str
    email: EmailStr
    content: str

    model_config = {
        "json_schema_extra" : {
            "example": {
                "fullname": "John Doe",
                "email": "johndoe123@co.com",
                "content": "This is a feedback message."
            }
        }
    }


class UserRead(BaseModel):
    id: str
    full_name: str
    email: EmailStr
    is_verified: Optional[bool] = False
    role: Optional[UserRole] = UserRole.GENERAL
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True, extra="ignore")
    

class UserCreateRead(BaseModel):
    id: str
    full_name: str
    email: EmailStr
    role: Optional[str] = "user"
    verification_token: Optional[str] = None
    is_verified: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


    model_config = ConfigDict(from_attributes=True) 

class StudentProfileRead(BaseModel):
    matric_number: Optional[str] = None
    faculty: Optional[str] = None
    department: Optional[str] = None
    profile_picture: Optional[str] = None
    educational_level: Optional[str] = None
    course: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class InstitutionProfileRead(BaseModel):
    institution_name: Optional[str] = None
    institution_description: Optional[str] = None
    institution_email: Optional[EmailStr] = None
    institution_website: Optional[str] = None
    institution_location: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)




class LoginResponseModel(BaseModel):
    status: bool
    message: str
    data: Optional[Any] = None

class DeleteResponseModel(BaseModel):
    status: bool
    message: str

class RegisterResponseModel(BaseModel):
    status: bool
    message: str
    data: UserCreateRead


class TokenUser(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    id: Optional[str] = None
    is_verified: Optional[bool] = False
    role: Optional[str]
    access_token: Optional[str] = "Sorry, We can not send the access token in the response"
    token_type: Optional[str] = "bearer"

    model_config = ConfigDict(from_attributes=True)

class VerificationMailSchemaResponse(BaseModel):
    status: bool
    message: str
    verification_token: str

    model_config = ConfigDict(from_attributes=True)

class GooglePayload(BaseModel):
    sub: Optional[Any] = None
    name: str
    email: str
    picture: str
    verification_token: Optional[str] = None
    is_verified: bool

class GetTokenRequest(BaseModel):
    code: str



class AdminEmailSchema(BaseModel):
    subject: Optional[str] = "Admin Email"
    greetings: Optional[str] = "Hello"
    message: str
    user_emails: List[EmailStr]