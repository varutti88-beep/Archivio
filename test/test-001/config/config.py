import os

BASE_DIR = os.path.dirname(os.path.dirname(__file__))

DEFAULT_ADMIN = {
    "username": "admin",
    "password": "Admin123!" 
}

SMTP = {
    "host": "smtp.example.com",
    "port": 587,
    "username": "no-reply@example.com",
    "password": "your_smtp_password",
    "use_tls": True,
    "from_addr": "no-reply@example.com"
}

OTP_EXPIRY = 5 * 60  
