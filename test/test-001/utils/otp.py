import random
import time
from config.config import OTP_EXPIRY

def generate_otp(length=6):
    return ''.join(str(random.randint(0,9)) for _ in range(length))

def make_otp_payload():
    code = generate_otp()
    expiry = int(time.time()) + OTP_EXPIRY
    return code, expiry
