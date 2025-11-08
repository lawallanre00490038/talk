from typing import Optional, List

class MailService:
    def __init__(self, resend, settings):
        self.resend = resend
        self.settings = settings
        self.resend.api_key = self.settings.RESEND_API_KEY

    def send_verification_email(self, to_email: str, name: str, verification_token: str):
        verification_link = f"{self.settings.FRONTEND_URL}/auth/verify-email?token={verification_token}"

        params = {
            "from": f"CampusTALK Admin <{self.settings.RESEND_FROM_EMAIL}>",
            "to": [to_email],
            "subject": "Verify Your Email Address - CampusTALK",
            "html": f"""
                <html>
                    <head>
                        <style>
                            body {{
                                font-family: Arial, sans-serif;
                                background-color: #f4f6fa;
                                margin: 0;
                                padding: 0;
                                color: #333;
                            }}
                            .container {{
                                max-width: 600px;
                                margin: 40px auto;
                                background: #ffffff;
                                padding: 30px;
                                border-radius: 10px;
                                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                            }}
                            .header {{
                                background-color: #003366;
                                color: #ffffff;
                                padding: 20px;
                                text-align: center;
                                border-radius: 10px 10px 0 0;
                            }}
                            .header h1 {{
                                margin: 0;
                                font-size: 24px;
                            }}
                            .content {{
                                padding: 20px;
                            }}
                            .content p {{
                                font-size: 16px;
                                line-height: 1.6;
                            }}
                            .button {{
                                display: inline-block;
                                margin: 20px 0;
                                padding: 12px 24px;
                                background-color: #28a745;
                                color: white;
                                text-decoration: none;
                                font-weight: bold;
                                border-radius: 6px;
                                text-align: center;
                            }}
                            .footer {{
                                font-size: 12px;
                                color: #777;
                                text-align: center;
                                margin-top: 30px;
                            }}
                        </style>
                    </head>
                    <body>
                        <div class="container">
                            <div class="header">
                                <h1>Welcome to CampusTALK!</h1>
                            </div>
                            <div class="content">
                                <p>Hi {name},</p>
                                <p>Thank you for signing up for <strong>CampusTALK</strong>. To get started, please verify your email address by clicking the button below:</p>
                                <p style="text-align: center;">
                                    <a href="{verification_link}" class="button">Verify Your Email</a>
                                </p>
                                <p>If you did not create an account, you can safely ignore this email.</p>
                                <p>Welcome aboard!</p>
                                <p>Best regards,<br>The CampusTALK Team</p>
                            </div>
                            <div class="footer">
                                © 2025 CampusTALK. All rights reserved. | Built by <a href="https://equalyz.ai" style="color:#888;">EqualyzAI</a>
                            </div>
                        </div>
                    </body>
                </html>
            """
        }

        try:
            email = self.resend.Emails.send(params)
            print(email)
        except Exception as e:
            print(f"Error sending verification email: {e}")

    def send_reset_password_email(self, to_email: str, name: Optional[str], reset_token: str, is_admin: Optional[bool] = False, which_user: Optional[str] = None, admin_password: Optional[str] = None):
        reset_link = f"{self.settings.FRONTEND_URL}/auth/reset-password?token={reset_token}"

        params = {
            "from": f"CampusTALK Admin <{self.settings.RESEND_FROM_EMAIL}>",
            "to": [to_email],
            "subject": "Reset Your Password - CampusTALK",
            "html": f"""
                <html>
                    <head>
                        <style>
                            body {{
                                font-family: Arial, sans-serif;
                                background-color: #f2f4f8;
                                margin: 0;
                                padding: 0;
                                color: #333;
                            }}
                            .container {{
                                max-width: 600px;
                                margin: 40px auto;
                                background: #ffffff;
                                padding: 30px;
                                border-radius: 10px;
                                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                            }}
                            .header {{
                                background-color: #003366;
                                color: #ffffff;
                                padding: 20px;
                                text-align: center;
                                border-radius: 8px 8px 0 0;
                            }}
                            .content p {{
                                font-size: 16px;
                                line-height: 1.6;
                            }}
                            .button {{
                                display: inline-block;
                                padding: 12px 24px;
                                background-color: #007bff;
                                color: white;
                                text-decoration: none;
                                border-radius: 6px;
                            }}
                            .footer {{
                                margin-top: 30px;
                                font-size: 12px;
                                color: #777;
                                text-align: center;
                            }}
                        </style>
                    </head>
                    <body>
                        <div class="container">
                            <div class="header">
                                <h1>Password Reset Request</h1>
                            </div>
                            <div class="content">
                                <p>Hi {name},</p>
                                <p>We received a request to reset your CampusTALK account password.</p>
                                <p>Click the button below to proceed:</p>
                                <p style="text-align: center;">
                                    <a href="{reset_link}" class="button">Reset Your Password</a>
                                </p>
                                <p>If you didn’t make this request, you can ignore this email.</p>
                                <p>Cheers,<br>The CampusTALK Team</p>
                            </div>
                            <div class="footer">
                                © 2025 CampusTALK. All rights reserved. | Built by <a href="https://equalyz.ai" style="color:#888;">EqualyzAI</a>
                            </div>
                        </div>
                    </body>
                </html>
            """
        }

        try:
            email = self.resend.Emails.send(params)
            print(email)
        except Exception as e:
            print(f"Error sending password reset email: {e}")

    def send_announcement_email(self, to_emails: List[str], subject: str, greetings: str, message: str):
        params = {
            "from": f"CampusTALK Admin <{self.settings.RESEND_FROM_EMAIL}>",
            "to": to_emails,
            "subject": subject,
            "html": f"""
                <html>
                    <head>
                        <style>
                            body {{
                                font-family: Arial, sans-serif;
                                background-color: #f4f6fa;
                                padding: 0;
                                color: #333;
                            }}
                            .container {{
                                max-width: 600px;
                                margin: 40px auto;
                                background: #fff;
                                padding: 30px;
                                border-radius: 10px;
                                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                            }}
                            .header {{
                                background-color: #003366;
                                color: #ffffff;
                                padding: 20px;
                                text-align: center;
                                border-radius: 10px 10px 0 0;
                            }}
                            .content {{
                                padding: 20px;
                                font-size: 16px;
                                line-height: 1.6;
                            }}
                            .footer {{
                                font-size: 12px;
                                color: #777;
                                text-align: center;
                                margin-top: 30px;
                            }}
                        </style>
                    </head>
                    <body>
                        <div class="container">
                            <div class="header">
                                <h2>{subject}</h2>
                            </div>
                            <div class="content">
                                {greetings}<br><br>
                                {message}
                            </div>
                            <div class="footer">
                                © 2025 CampusTALK. All rights reserved. | Built by <a href="https://equalyz.ai" style="color:#888;">EqualyzAI</a>
                            </div>
                        </div>
                    </body>
                </html>
            """
        }

        try:
            email = self.resend.Emails.send(params)
            print(f"Email sent to: {to_emails}")
            return email
        except Exception as e:
            print(f"Error sending announcement email: {e}")
            raise e
