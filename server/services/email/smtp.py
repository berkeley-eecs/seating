import smtplib
from email.message import EmailMessage


class SMTPConfig:
    def __init__(self, smtp_server, smtp_port, username, password):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.username = username
        self.password = password


def send_email(*, smtp: SMTPConfig, from_addr, to_addr, subject, body, body_html=None, use_tls=True):
    msg = EmailMessage()
    msg['From'] = from_addr
    msg['To'] = to_addr
    msg['Subject'] = subject
    msg.set_content(body)

    if body_html:
        msg.add_alternative(body_html, subtype='html')

    try:
        with smtplib.SMTP(smtp.smtp_server, smtp.smtp_port) as server:
            if use_tls:
                server.starttls()
            server.login(smtp.username, smtp.password)
            server.send_message(msg)
        return True
    except Exception as e:
        print(e)
        return False
