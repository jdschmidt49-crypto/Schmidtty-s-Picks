"""
Daily Sports Betting Picks Emailer
===================================
Runs each morning, calls the Claude API to generate today's best bets,
and emails a formatted HTML report to your recipient list.

SETUP INSTRUCTIONS:
1. Install dependencies:
       pip install anthropic requests

2. Fill in your credentials in the CONFIG section below.

3. Run manually to test:
       python sports_picks_emailer.py

4. Schedule it to run every morning (e.g. 8 AM):
   - Mac/Linux (cron):
       0 8 * * * /usr/bin/python3 /path/to/sports_picks_emailer.py
   - Windows (Task Scheduler):
       Action: python C:\path\to\sports_picks_emailer.py
   - Or deploy to a free cloud scheduler like:
       * GitHub Actions (free, reliable)
       * Railway / Render / Fly.io (free tiers)
       * Google Cloud Scheduler + Cloud Run

EMAIL OPTIONS — choose one:
   Option A: Gmail (easiest — uses your Gmail account)
   Option B: SendGrid (better for larger lists / deliverability)
   Option C: AWS SES (cheapest at scale)
See the comments in send_email() below to switch.
"""

import anthropic
import smtplib
import ssl
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# ─────────────────────────────────────────────
#  CONFIG — fill these in
# ─────────────────────────────────────────────

ANTHROPIC_API_KEY = "YOUR_ANTHROPIC_API_KEY"

# Recipients — add as many as you like
RECIPIENT_EMAILS = [
    "you@example.com",
    "friend@example.com",
]

# Sender — your Gmail address (for Option A)
# For SendGrid/SES, see send_email() below
SENDER_EMAIL = "your.gmail@gmail.com"

# Gmail App Password (NOT your regular Gmail password)
# Get one at: https://myaccount.google.com/apppasswords
# (Requires 2FA to be enabled on your Google account)
GMAIL_APP_PASSWORD = "YOUR_GMAIL_APP_PASSWORD"

EMAIL_SUBJECT_PREFIX = "🏆 Daily Sports Picks —"

# ─────────────────────────────────────────────
#  PROMPT — mirrors the sports-betting-picks skill
# ─────────────────────────────────────────────

PICKS_PROMPT = f"""You are an expert sports betting analyst. Today is {date.today().strftime('%A, %B %d, %Y')}.

Generate today's best sports bets slate by following these steps:

1. ASSESS TODAY'S SLATE
   Identify the most valuable betting opportunities across NBA, NHL, MLB, NFL (in season),
   and major soccer leagues. Focus on games happening TODAY.

2. VALUE ASSESSMENT FRAMEWORK
   For each candidate bet, evaluate:
   - Line Value: Is the public backing the wrong side? Is the line mispriced?
   - Form Edge: Recent win/loss streaks, back-to-backs, fatigue
   - Injury Edge: Key players out or questionable that the market hasn't fully priced
   - Matchup Angle: Style mismatches, pace differential, exploitable tendencies
   - Totals Logic: Pace, defense ratings, weather (outdoor games), trends

3. CONFIDENCE TIERS
   ⭐⭐⭐ Strong play — 3+ factors align
   ⭐⭐ Lean — 2 factors, some uncertainty
   ⭐ Flier — higher variance, smaller unit

4. OUTPUT FORMAT
   Return your analysis as clean HTML (no markdown, no code fences).
   Use this structure for each pick:

   - Sport badge, matchup name, game time
   - Pick (e.g. "Lakers -4.5"), approximate odds
   - Confidence tier with stars
   - 3-4 sentence reasoning citing specific stats, injuries, or trends

   End with:
   - 1-2 "Fades / Avoid" — popular public bets to fade
   - 1-2 "Keep an eye on" — injury news or line moves to watch

5. STYLE
   - Be specific and data-driven, not vague
   - Only cite real, known statistics and trends — do not fabricate
   - Include a brief disclaimer at the bottom about responsible gambling
   - Return ONLY the HTML body content (no <html>, <head>, or <body> tags)
   - Use inline styles for formatting so the email renders correctly in all clients
"""

# ─────────────────────────────────────────────
#  EMAIL TEMPLATE
# ─────────────────────────────────────────────

def build_email_html(picks_html: str, today: str) -> str:
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Daily Sports Picks — {today}</title>
</head>
<body style="margin:0; padding:0; background:#f5f5f0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f5f5f0; padding: 32px 16px;">
    <tr>
      <td align="center">
        <table width="600" cellpadding="0" cellspacing="0" style="max-width:600px; width:100%;">

          <!-- Header -->
          <tr>
            <td style="background:#1a1a1a; border-radius:12px 12px 0 0; padding: 24px 32px;">
              <p style="margin:0; font-size:11px; font-weight:600; letter-spacing:0.1em; color:#888; text-transform:uppercase;">Daily Betting Picks</p>
              <h1 style="margin:4px 0 0; font-size:22px; font-weight:500; color:#ffffff;">{today}</h1>
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="background:#ffffff; border-radius:0 0 12px 12px; padding: 28px 32px; border: 0.5px solid #e5e5e5; border-top:none;">
              {picks_html}
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="padding: 20px 0 0; text-align:center;">
              <p style="margin:0; font-size:12px; color:#aaa;">
                Generated by Claude · Unsubscribe by replying to this email<br>
                For entertainment purposes only. Please gamble responsibly.
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""

# ─────────────────────────────────────────────
#  GENERATE PICKS via Claude API
# ─────────────────────────────────────────────

def generate_picks() -> str:
    print("Calling Claude API to generate today's picks...")
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4000,
        messages=[
            {"role": "user", "content": PICKS_PROMPT}
        ]
    )

    picks_html = message.content[0].text
    print("Picks generated successfully.")
    return picks_html

# ─────────────────────────────────────────────
#  SEND EMAIL
# ─────────────────────────────────────────────

def send_email(subject: str, html_body: str):
    """
    Sends via Gmail SMTP (Option A — default).

    ── Option B: SendGrid ──────────────────────────────
    pip install sendgrid
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail
    sg = SendGridAPIClient(api_key="YOUR_SENDGRID_API_KEY")
    for recipient in RECIPIENT_EMAILS:
        msg = Mail(from_email=SENDER_EMAIL, to_emails=recipient,
                   subject=subject, html_content=html_body)
        sg.send(msg)
    return

    ── Option C: AWS SES ───────────────────────────────
    pip install boto3
    import boto3
    ses = boto3.client('ses', region_name='us-east-1')
    for recipient in RECIPIENT_EMAILS:
        ses.send_email(
            Source=SENDER_EMAIL,
            Destination={'ToAddresses': [recipient]},
            Message={'Subject': {'Data': subject},
                     'Body': {'Html': {'Data': html_body}}}
        )
    return
    """

    context = ssl.create_default_context()
    print(f"Sending email to {len(RECIPIENT_EMAILS)} recipient(s)...")

    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
        server.login(SENDER_EMAIL, GMAIL_APP_PASSWORD)

        for recipient in RECIPIENT_EMAILS:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = SENDER_EMAIL
            msg["To"] = recipient
            msg.attach(MIMEText(html_body, "html"))
            server.sendmail(SENDER_EMAIL, recipient, msg.as_string())
            print(f"  ✓ Sent to {recipient}")

    print("All emails sent.")

# ─────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────

def main():
    today_str = date.today().strftime("%A, %B %d, %Y")
    subject = f"{EMAIL_SUBJECT_PREFIX} {today_str}"

    try:
        picks_html = generate_picks()
        full_html = build_email_html(picks_html, today_str)
        send_email(subject, full_html)
        print(f"\nDone! Daily picks emailed for {today_str}.")
    except anthropic.APIError as e:
        print(f"Claude API error: {e}")
        raise
    except smtplib.SMTPAuthenticationError:
        print("Gmail auth failed. Double-check your App Password.")
        raise
    except Exception as e:
        print(f"Unexpected error: {e}")
        raise

if __name__ == "__main__":
    main()
