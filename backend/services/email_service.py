import asyncio
import resend
import qrcode
import io
import base64

from config import RESEND_API_KEY, SENDER_EMAIL

resend.api_key = RESEND_API_KEY


async def send_email(to: str, subject: str, html: str):
    """Send an email via Resend. Returns True on success."""
    if not RESEND_API_KEY:
        return False
    try:
        await asyncio.to_thread(resend.Emails.send, {
            "from": SENDER_EMAIL,
            "to": [to],
            "subject": subject,
            "html": html,
        })
        return True
    except Exception as e:
        print(f"Email send error: {e}")
        return False


def email_wrapper(title: str, body_html: str) -> str:
    """Wrap email content in a styled template."""
    return f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;background:#1a1a1a;color:#e0e0e0;padding:30px;border-radius:12px;">
        <div style="text-align:center;margin-bottom:20px;">
            <h1 style="color:#4CAF50;margin:0;">SMA Antenna Calc</h1>
            <p style="color:#888;font-size:14px;">{title}</p>
        </div>
        {body_html}
        <div style="border-top:1px solid #333;margin-top:30px;padding-top:15px;text-align:center;font-size:12px;color:#666;">
            <p>SMA Antenna Analyzer &copy; 2026</p>
        </div>
    </div>
    """


def generate_qr_base64(url: str) -> str:
    qr = qrcode.QRCode(version=1, box_size=8, border=2)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")
