import anyio
import resend

from app.core.config import settings


def _send_credentials_email_sync(to_email: str, full_name: str, password: str) -> None:
    resend.api_key = settings.RESEND_API_KEY

    resend.Emails.send({
        "from": settings.EMAIL_FROM,
        "to": [to_email],
        "subject": "Welcome to Obelytics — Your Login Credentials",
        "html": f"""
        <!DOCTYPE html>
        <html>
        <body style="font-family:sans-serif;color:#111;max-width:480px;margin:0 auto;padding:24px">
          <h2 style="margin-bottom:8px">Welcome to Obelytics</h2>
          <p>Hello <strong>{full_name}</strong>,</p>
          <p>An account has been created for you. Use the credentials below to log in.</p>
          <table style="border-collapse:collapse;width:100%;margin:16px 0">
            <tr>
              <td style="padding:8px 12px;background:#f4f4f5;font-weight:600;width:30%">Email</td>
              <td style="padding:8px 12px;background:#fafafa;font-family:monospace">{to_email}</td>
            </tr>
            <tr>
              <td style="padding:8px 12px;background:#f4f4f5;font-weight:600">Password</td>
              <td style="padding:8px 12px;background:#fafafa;font-family:monospace">{password}</td>
            </tr>
          </table>
          <p style="color:#dc2626;font-size:13px">
            Please log in and change your password immediately.
          </p>
        </body>
        </html>
        """,
    })


async def send_credentials_email(to_email: str, full_name: str, password: str) -> None:
    await anyio.to_thread.run_sync(
        lambda: _send_credentials_email_sync(to_email, full_name, password)
    )
