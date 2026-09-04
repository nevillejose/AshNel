#!/usr/bin/env python3
"""
ASHNEL INC. — Lightweight Studio Inquiry & Estimator Backend
Zero-dependency Python 3 HTTP microservice with SMTP email dispatch.
"""

import os
import json
import time
import smtplib
import ssl
from http.server import HTTPServer, BaseHTTPRequestHandler
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formatdate, make_msgid
from pathlib import Path
from collections import defaultdict

# --- Configuration & Environment Loading ---
ENV_PATH = Path(__file__).parent / ".env"

def load_env():
    config = {
        "PORT": "8008",
        "HOST": "127.0.0.1",
        "SMTP_HOST": "smtp.gmail.com",
        "SMTP_PORT": "587",
        "SMTP_USER": "ashnelinc.in@gmail.com",
        "SMTP_PASS": "",
        "TO_EMAIL": "ashnelinc.in@gmail.com",
        "FROM_EMAIL": "advisory@ashnel.com",
        "APP_ENV": "production"
    }
    if ENV_PATH.exists():
        with open(ENV_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    config[k.strip()] = v.strip().strip("'\"")
    # Environment variables override .env file
    for k in config:
        if k in os.environ:
            config[k] = os.environ[k]
    return config

CONFIG = load_env()

# --- Simple In-Memory Rate Limiter (Anti-Spam) ---
# Tracks IP -> list of timestamps
IP_REQUESTS = defaultdict(list)
MAX_REQUESTS_PER_WINDOW = 8
WINDOW_SECONDS = 300  # 5 minutes

def is_rate_limited(ip: str) -> bool:
    now = time.time()
    # Prune old timestamps
    IP_REQUESTS[ip] = [t for t in IP_REQUESTS[ip] if now - t < WINDOW_SECONDS]
    if len(IP_REQUESTS[ip]) >= MAX_REQUESTS_PER_WINDOW:
        return True
    IP_REQUESTS[ip].append(now)
    return False

# --- SMTP Mail Dispatcher ---
def send_lead_email(subject: str, text_content: str, html_content: str, reply_to: str) -> bool:
    cfg = load_env()
    smtp_pass = cfg.get("SMTP_PASS", "").replace(" ", "")
    
    if not smtp_pass:
        print("[WARN] SMTP_PASS not set in .env! Logging inquiry to stdout instead.")
        print(f"Subject: {subject}\n{text_content}\n")
        return True

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"AshNel Studio Inquiries <{cfg.get('SMTP_USER')}>"
    msg["To"] = cfg.get("TO_EMAIL", "ashnelinc.in@gmail.com")
    msg["Reply-To"] = reply_to
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid(domain="ashnel.com")

    part1 = MIMEText(text_content, "plain", "utf-8")
    part2 = MIMEText(html_content, "html", "utf-8")
    msg.attach(part1)
    msg.attach(part2)

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(cfg["SMTP_HOST"], int(cfg["SMTP_PORT"]), timeout=20) as server:
            server.ehlo()
            server.starttls(context=context)
            server.ehlo()
            server.login(cfg["SMTP_USER"], smtp_pass)
            server.send_message(msg)
        print(f"[SUCCESS] Email dispatched for lead: {reply_to}")
        return True
    except Exception as e:
        print(f"[ERROR] SMTP dispatch failed: {e}")
        return False

# --- HTTP Request Handler ---
class APIHandler(BaseHTTPRequestHandler):
    def _send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def do_OPTIONS(self):
        self.send_response(204)
        self._send_cors_headers()
        self.end_headers()

    def _respond_json(self, status_code: int, data: dict):
        response = json.dumps(data).encode("utf-8")
        self.send_response(status_code)
        self._send_cors_headers()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def _get_client_ip(self) -> str:
        forwarded = self.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return self.headers.get("X-Real-IP", self.client_address[0])

    def do_GET(self):
        if self.path in ("/api/health", "/api/health/"):
            cfg = load_env()
            has_smtp = bool(cfg.get("SMTP_PASS"))
            self._respond_json(200, {
                "status": "ok",
                "service": "ashnel-api",
                "smtp_configured": has_smtp,
                "destination": cfg.get("TO_EMAIL")
            })
            return
        
        self._respond_json(404, {"error": "Not Found"})

    def do_POST(self):
        client_ip = self._get_client_ip()
        if is_rate_limited(client_ip):
            self._respond_json(429, {"error": "Rate limit exceeded. Please try again in a few minutes."})
            return

        content_length = int(self.headers.get("Content-Length", 0))
        if content_length <= 0 or content_length > 65536:
            self._respond_json(400, {"error": "Invalid payload size."})
            return

        try:
            raw_body = self.rfile.read(content_length).decode("utf-8")
            payload = json.loads(raw_body)
        except Exception:
            self._respond_json(400, {"error": "Invalid JSON format."})
            return

        # Honeypot spam trap
        if payload.get("website_url_hp"):
            # Bot caught, return fake success
            self._respond_json(200, {"success": True, "lead_id": "OK-RESERVED"})
            return

        if self.path in ("/api/intake", "/api/intake/"):
            self.handle_intake(payload)
        elif self.path in ("/api/contact", "/api/contact/"):
            self.handle_contact(payload)
        else:
            self._respond_json(404, {"error": "Endpoint not found"})

    def handle_intake(self, data: dict):
        name = data.get("name", "").strip()
        email = data.get("email", "").strip()
        track = data.get("track", "Turnkey MVP")
        timeline = data.get("timeline", "30-Day Sprint")
        budget = data.get("budget", "Flexible")
        scope = data.get("scope", "").strip()
        dpdp = data.get("dpdp_consent", False)

        if not name or not email:
            self._respond_json(400, {"error": "Name and valid email are required."})
            return

        subject = f"[New Lead: Intake Calculator] {name} — {track}"

        text_content = f"""
NEW FIXED-SCOPE INTAKE SUBMISSION
==================================
Date/Time: {formatdate(localtime=True)}
Name: {name}
Email: {email}
Track Selected: {track}
Timeline Target: {timeline}
Budget Tier: {budget}
DPDP Consent Confirmed: {'Yes' if dpdp else 'No'}

Brief Project Description / Bottleneck:
--------------------------------------
{scope if scope else 'None provided'}

==================================
Direct Reply: Hit reply to message {name} directly at {email}.
"""

        html_content = f"""
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #f8fafc; color: #0f172a; padding: 24px; margin: 0;">
  <div style="max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);">
    <div style="background-color: #080c15; padding: 20px 24px; border-bottom: 2px solid #d95a1e;">
      <h2 style="color: #ffffff; margin: 0; font-size: 18px; font-weight: 700; letter-spacing: -0.02em;">
        ASHNEL INC. <span style="color: #fb923c; font-weight: 400; font-size: 14px;">• New Project Intake</span>
      </h2>
    </div>
    <div style="padding: 24px;">
      <div style="display: inline-block; background: #fff7ed; border: 1px solid #fed7aa; color: #b84411; font-family: monospace; font-size: 11px; font-weight: 600; padding: 4px 10px; rounded: 6px; margin-bottom: 16px; border-radius: 4px;">
        TRACK: {track}
      </div>
      
      <table style="width: 100%; border-collapse: collapse; font-size: 14px; margin-bottom: 20px;">
        <tr style="border-bottom: 1px solid #f1f5f9;">
          <td style="padding: 10px 0; color: #64748b; font-weight: 600; width: 140px;">Client Name:</td>
          <td style="padding: 10px 0; color: #080c15; font-weight: 700;">{name}</td>
        </tr>
        <tr style="border-bottom: 1px solid #f1f5f9;">
          <td style="padding: 10px 0; color: #64748b; font-weight: 600;">Work Email:</td>
          <td style="padding: 10px 0;"><a href="mailto:{email}" style="color: #d95a1e; font-weight: 600; text-decoration: none;">{email}</a></td>
        </tr>
        <tr style="border-bottom: 1px solid #f1f5f9;">
          <td style="padding: 10px 0; color: #64748b; font-weight: 600;">Timeline Window:</td>
          <td style="padding: 10px 0; color: #080c15;">{timeline}</td>
        </tr>
        <tr style="border-bottom: 1px solid #f1f5f9;">
          <td style="padding: 10px 0; color: #64748b; font-weight: 600;">Budget Tier:</td>
          <td style="padding: 10px 0; color: #080c15; font-weight: 600;">{budget}</td>
        </tr>
        <tr>
          <td style="padding: 10px 0; color: #64748b; font-weight: 600;">DPDP Consent:</td>
          <td style="padding: 10px 0; color: #047857; font-weight: 600;">{'✓ Affirmative Consent Recorded' if dpdp else 'No'}</td>
        </tr>
      </table>

      <div style="background-color: #f8fafc; border-radius: 8px; border: 1px solid #e2e8f0; padding: 16px; margin-top: 12px;">
        <div style="font-size: 11px; font-family: monospace; color: #64748b; font-weight: 700; text-transform: uppercase; margin-bottom: 6px;">Scope Brief & Requirements</div>
        <p style="margin: 0; font-size: 14px; line-height: 1.6; color: #334155; white-space: pre-wrap;">{scope if scope else 'No additional scope details entered.'}</p>
      </div>

      <div style="margin-top: 24px; text-align: center;">
        <a href="mailto:{email}?subject=Re:%20ASHNEL%20INC.%20Turnkey%20Engineering%20Scope%20Review" style="display: inline-block; background-color: #080c15; color: #ffffff; padding: 12px 24px; border-radius: 8px; font-weight: 600; text-decoration: none; font-size: 13px;">
          Reply to {name} &rarr;
        </a>
      </div>
    </div>
    <div style="background: #f1f5f9; padding: 12px 24px; text-align: center; font-size: 11px; color: #64748b;">
      ASHNEL INC. • Bangalore Studio • Dispatched via Studio API Daemon
    </div>
  </div>
</body>
</html>
"""
        success = send_lead_email(subject, text_content, html_content, reply_to=email)
        if success:
            self._respond_json(200, {"success": True, "message": "Lead received and dispatched."})
        else:
            self._respond_json(500, {"error": "Could not dispatch email. Please try direct email."})

    def handle_contact(self, data: dict):
        name = data.get("name", "").strip()
        email = data.get("email", "").strip()
        org = data.get("org", "").strip()
        practice = data.get("practice", "General Advisory")
        budget = data.get("budget", "Not specified")
        message = data.get("message", "").strip()
        dpdp = data.get("dpdp_consent", False)

        if not name or not email or not message:
            self._respond_json(400, {"error": "Name, email, and inquiry brief are required."})
            return

        subject = f"[Studio Inquiry] {org if org else name} — {practice}"

        text_content = f"""
NEW STUDIO INQUIRY DESK SUBMISSION
==================================
Date/Time: {formatdate(localtime=True)}
Name: {name}
Email: {email}
Organization: {org if org else 'Individual'}
Practice Area: {practice}
Budget Window: {budget}
DPDP Consent Confirmed: {'Yes' if dpdp else 'No'}

Inquiry Scope:
-------------
{message}

==================================
Direct Reply: Hit reply to message {name} directly at {email}.
"""

        html_content = f"""
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #f8fafc; color: #0f172a; padding: 24px; margin: 0;">
  <div style="max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);">
    <div style="background-color: #080c15; padding: 20px 24px; border-bottom: 2px solid #d95a1e;">
      <h2 style="color: #ffffff; margin: 0; font-size: 18px; font-weight: 700; letter-spacing: -0.02em;">
        ASHNEL INC. <span style="color: #fb923c; font-weight: 400; font-size: 14px;">• Advisory Desk Inquiry</span>
      </h2>
    </div>
    <div style="padding: 24px;">
      <div style="display: inline-block; background: #fff7ed; border: 1px solid #fed7aa; color: #b84411; font-family: monospace; font-size: 11px; font-weight: 600; padding: 4px 10px; rounded: 6px; margin-bottom: 16px; border-radius: 4px;">
        PRACTICE: {practice}
      </div>

      <table style="width: 100%; border-collapse: collapse; font-size: 14px; margin-bottom: 20px;">
        <tr style="border-bottom: 1px solid #f1f5f9;">
          <td style="padding: 10px 0; color: #64748b; font-weight: 600; width: 140px;">Contact Name:</td>
          <td style="padding: 10px 0; color: #080c15; font-weight: 700;">{name}</td>
        </tr>
        <tr style="border-bottom: 1px solid #f1f5f9;">
          <td style="padding: 10px 0; color: #64748b; font-weight: 600;">Work Email:</td>
          <td style="padding: 10px 0;"><a href="mailto:{email}" style="color: #d95a1e; font-weight: 600; text-decoration: none;">{email}</a></td>
        </tr>
        <tr style="border-bottom: 1px solid #f1f5f9;">
          <td style="padding: 10px 0; color: #64748b; font-weight: 600;">Organization:</td>
          <td style="padding: 10px 0; color: #080c15;">{org if org else 'Individual'}</td>
        </tr>
        <tr style="border-bottom: 1px solid #f1f5f9;">
          <td style="padding: 10px 0; color: #64748b; font-weight: 600;">Budget Allocation:</td>
          <td style="padding: 10px 0; color: #080c15; font-weight: 600;">{budget}</td>
        </tr>
        <tr>
          <td style="padding: 10px 0; color: #64748b; font-weight: 600;">DPDP Consent:</td>
          <td style="padding: 10px 0; color: #047857; font-weight: 600;">{'✓ Affirmative Consent Recorded' if dpdp else 'No'}</td>
        </tr>
      </table>

      <div style="background-color: #f8fafc; border-radius: 8px; border: 1px solid #e2e8f0; padding: 16px; margin-top: 12px;">
        <div style="font-size: 11px; font-family: monospace; color: #64748b; font-weight: 700; text-transform: uppercase; margin-bottom: 6px;">Inquiry Brief</div>
        <p style="margin: 0; font-size: 14px; line-height: 1.6; color: #334155; white-space: pre-wrap;">{message}</p>
      </div>

      <div style="margin-top: 24px; text-align: center;">
        <a href="mailto:{email}?subject=Re:%20ASHNEL%20INC.%20Advisory%20Inquiry%20Response" style="display: inline-block; background-color: #080c15; color: #ffffff; padding: 12px 24px; border-radius: 8px; font-weight: 600; text-decoration: none; font-size: 13px;">
          Reply to {name} &rarr;
        </a>
      </div>
    </div>
    <div style="background: #f1f5f9; padding: 12px 24px; text-align: center; font-size: 11px; color: #64748b;">
      ASHNEL INC. • Bangalore Studio • Dispatched via Studio API Daemon
    </div>
  </div>
</body>
</html>
"""
        success = send_lead_email(subject, text_content, html_content, reply_to=email)
        if success:
            self._respond_json(200, {"success": True, "message": "Inquiry received and dispatched."})
        else:
            self._respond_json(500, {"error": "Could not dispatch email. Please try direct email."})


def run_server():
    cfg = load_env()
    host = cfg.get("HOST", "127.0.0.1")
    port = int(cfg.get("PORT", "8008"))
    server = HTTPServer((host, port), APIHandler)
    print(f"[*] ASHNEL INC. API Microservice running on http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[!] Shutting down server...")
        server.server_close()


if __name__ == "__main__":
    run_server()
