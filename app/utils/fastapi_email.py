from typing import List, Union
from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
from fastapi import BackgroundTasks
from jinja2 import Environment, FileSystemLoader, select_autoescape
from pydantic import BaseModel, EmailStr
import os
from pathlib import Path

# ============================================================
# 🔧 Configuration
# ============================================================
BASE_DIR = Path(__file__).resolve().parent
TEMPLATE_DIR = BASE_DIR / "templates"

conf = ConnectionConfig(
    MAIL_USERNAME=os.getenv("MAIL_USERNAME", "lagtalk"),
    MAIL_PASSWORD=os.getenv("MAIL_PASSWORD", "lagtalk1234"),
    MAIL_FROM=os.getenv("MAIL_FROM", "lawallanre49@gmail.com"),
    MAIL_PORT=int(os.getenv("MAIL_PORT", 465)),
    MAIL_SERVER=os.getenv("MAIL_SERVER", "mail.server.com"),
    MAIL_STARTTLS=bool(os.getenv("MAIL_STARTTLS", False)),
    MAIL_SSL_TLS=bool(os.getenv("MAIL_SSL_TLS", True)),
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True,
)

# ============================================================
# 🧠 Jinja2 Template Engine Setup
# ============================================================
env = Environment(
    loader=FileSystemLoader(str(TEMPLATE_DIR)),
    autoescape=select_autoescape(["html", "xml"])
)

# ============================================================
# 📧 Email Schema
# ============================================================
class EmailSchema(BaseModel):
    email: List[Union[EmailStr, str]]
    subject: str
    template_name: str
    context: dict  # variables to pass into the HTML template

# ============================================================
# 🧩 Utility Functions
# ============================================================
def render_email_template(template_name: str, context: dict) -> str:
    """Render a Jinja2 template with dynamic data"""
    template = env.get_template(template_name)
    return template.render(**context)


def create_email_message(email: EmailSchema) -> MessageSchema:
    """Generate message ready for sending"""
    html_content = render_email_template(email.template_name, email.context)
    return MessageSchema(
        subject=email.subject,
        recipients=email.email,
        body=html_content,
        subtype=MessageType.html
    )


async def send_email(message: MessageSchema):
    """Send the email using FastMail"""
    fm = FastMail(conf)
    await fm.send_message(message)


def schedule_email(background_tasks: BackgroundTasks, email_data: EmailSchema):
    """Schedule email sending as a background task"""
    message = create_email_message(email_data)
    background_tasks.add_task(send_email, message)
