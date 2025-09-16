import smtplib
from email.message import EmailMessage
from config.config import SMTP

def send_otp_email(to_addr, username, otp_code):
    msg = EmailMessage()
    msg['Subject'] = 'Il tuo codice OTP'
    msg['From'] = SMTP['from_addr']
    msg['To'] = to_addr
    msg.set_content(f"Ciao {username},\n\nil tuo codice OTP è: {otp_code}\nScade entro pochi minuti.\n\nSe non hai richiesto questo codice, ignora questa email.")

    try:
        if SMTP.get("use_tls", True):
            server = smtplib.SMTP(SMTP["host"], SMTP["port"])
            server.starttls()
            server.login(SMTP["username"], SMTP["password"])
        else:
            server = smtplib.SMTP_SSL(SMTP["host"], SMTP["port"])
            server.login(SMTP["username"], SMTP["password"])

        server.send_message(msg)
        server.quit()
        return True, None
    except Exception as e:
        return False, str(e)
