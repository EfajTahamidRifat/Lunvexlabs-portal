import os
import time
import sqlite3
import html
import hashlib
import secrets
import re
from datetime import datetime, timezone
from flask import Flask, render_template_string, request, abort
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from PIL import Image
import boto3
from botocore.exceptions import ClientError

# ---------------- Configuration ----------------
# R2 Credentials
R2_ACCOUNT_ID = os.getenv("R2_ACCOUNT_ID")
R2_ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID")
R2_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY")
R2_BUCKET_NAME = os.getenv("R2_BUCKET_NAME")

if not all([R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET_NAME]):
    raise EnvironmentError("R2 environment variables are required.")

UPLOAD_FOLDER = "uploads"
PDF_FOLDER = "pdfs"
DATABASE = "lunvex.db"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PDF_FOLDER, exist_ok=True)

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB

# Initialize R2 client
s3_client = boto3.client(
    's3',
    endpoint_url=f'https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com',
    aws_access_key_id=R2_ACCESS_KEY_ID,
    aws_secret_access_key=R2_SECRET_ACCESS_KEY,
    region_name='auto'
)

# Verify R2 access on startup
try:
    s3_client.head_bucket(Bucket=R2_BUCKET_NAME)
    print("✅ R2 bucket is accessible")
except ClientError as e:
    raise EnvironmentError(f"R2 bucket access failed: {e}")

# ---------------- Agreements ----------------
TEAM_AGREEMENT_TEXT = """LUNVEX LABS – CORE TEAM MEMBER AGREEMENT

This legally binding Agreement (“Agreement”) is entered into on [Date] by and between:
Lunvex Labs, founded by Dewan Efaj Tahamid Rifat (“the Organization”), and [Full Name] (“the Member”).

1. ENGAGEMENT
You are appointed as a Core Team Member in your declared Niche and Specialization. This is an indefinite, performance-based engagement.

2. CONFIDENTIALITY
All non-public information (technical, strategic, or operational) is strictly confidential. Unauthorized disclosure constitutes grounds for immediate termination and legal action.

3. INTELLECTUAL PROPERTY
All work product, code, designs, or research created during your tenure is the sole and exclusive property of Lunvex Labs.

4. COMPENSATION
This role is performance-driven. No fixed salary is provided. Rewards (bonuses, equity, or commissions) are discretionary and based on measurable impact.

5. TERMINATION
- You may resign with 14 days’ written notice.
- Lunvex Labs reserves the right to terminate immediately for breach of conduct, inactivity (>14 days), or security violations.

6. PROFESSIONAL CONDUCT
All communication must occur via official Lunvex Labs channels (e.g., verified Telegram: @EfajTahamidRIFAT). Unprofessional behavior is not tolerated.

7. NO GUARANTEE OF SELECTION
Submission of this application is strictly preliminary and non-binding. It does not constitute acceptance, selection, or any obligation on the part of Lunvex Labs.

8. NON-INVESTOR STATUS
Applicants acknowledge that participation does not confer equity, ownership, or investor rights. Investment opportunities are separate and require direct qualification.

9. GOVERNING LAW
This Agreement is governed by the laws of Singapore. Legal notices may be sent via Telegram to @EfajTahamidRIFAT.
"""

INTERNSHIP_AGREEMENT_TEXT = """LUNVEX LABS – INTERNSHIP AGREEMENT

This educational Agreement (“Agreement”) is entered into on [Date] by and between:
Lunvex Labs, founded by Dewan Efaj Tahamid Rifat (“the Organization”), and [Full Name] (“the Intern”).

1. TERM
5-month unpaid internship from [Start Date] to [End Date]. Extension is at the Organization’s sole discretion.

2. PURPOSE
Hands-on mentorship in your chosen Niche and Specialization to build real-world skills.

3. CONFIDENTIALITY
All internal materials, tools, and communications are confidential. Disclosure is prohibited during and after the internship.

4. UNPAID NATURE
This is a voluntary, unpaid educational program. No salary, stipend, or benefits are provided. Successful completion yields an Official Certificate.

5. PATHWAY TO CORE TEAM
Exceptional performers may receive an invitation to join the Core Team post-internship.

6. TERMINATION
Lunvex Labs may terminate for misconduct, absenteeism, or breach. You may withdraw with 7 days’ notice.

7. NO GUARANTEE OF SELECTION
Submission of this application is strictly preliminary and non-binding. It does not constitute acceptance or selection.

8. NON-INVESTOR STATUS
Applicants acknowledge that participation does not confer equity, ownership, or investor rights.

9. GOVERNING LAW
This Agreement is governed by the laws of Singapore. Legal notices may be sent via Telegram to @EfajTahamidRIFAT.
"""

NICHES = {
    "Cybersecurity": {
        "Penetration Testing": ["Web App Pentesting", "Mobile App Pentesting", "Network Pentesting"],
        "Bug Bounty & Vulnerability Research": ["Web Vulnerabilities", "Mobile Vulnerabilities", "Blockchain Audits"],
    },
    "Web Development": {
        "Frontend Development": ["React", "Vue.js", "Svelte"],
        "Backend Development": ["Node.js", "Django", "Flask"],
    },
}

# ---------------- Helpers ----------------
def is_valid_github_url(url):
    if not url or not url.startswith("https://github.com/"):
        return False
    pattern = r"^https://github\.com/([a-zA-Z0-9_-]+)(/?)$"
    return bool(re.fullmatch(pattern, url.strip()))

def secure_filename_custom(filename):
    safe = "".join(c for c in filename if c.isalnum() or c in "._- ")
    return safe.strip().replace(' ', '_') or "file"

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg'}

def save_uploaded_file(file, prefix):
    if not file or not file.filename:
        raise ValueError("No file")
    orig = secure_filename_custom(file.filename)
    path = os.path.join(app.config["UPLOAD_FOLDER"], f"{prefix}_{int(time.time())}_{orig}")
    file.save(path)
    return path

def is_valid_image(fp):
    try:
        with Image.open(fp) as img:
            return img.format in ('JPEG', 'PNG')
    except:
        return False

def upload_to_r2(local_path, r2_key):
    s3_client.upload_file(local_path, R2_BUCKET_NAME, r2_key)

def backup_db_to_r2():
    upload_to_r2(DATABASE, f"backups/{DATABASE}")

# ---------------- Database ----------------
def init_db():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS applicants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            submission_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('CoreTeam', 'Internship')),
            niche TEXT NOT NULL,
            sector TEXT NOT NULL,
            subsector TEXT,
            github_url TEXT NOT NULL,
            photo_path TEXT NOT NULL,
            signature_path TEXT NOT NULL,
            agreed BOOLEAN NOT NULL DEFAULT 1,
            applied_at TEXT NOT NULL,
            UNIQUE(email, role)
        )
    """)
    conn.commit()
    conn.close()

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

# ---------------- PDF Generators ----------------
def generate_internal_pdf(data, photo_path, signature_path, submission_id):
    pdf_path = os.path.join(PDF_FOLDER, f"INTERNAL_{submission_id}.pdf")
    c = canvas.Canvas(pdf_path, pagesize=A4)
    w, h = A4

    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, h - 50, "Lunvex Labs – Internal Application Record")
    c.setFont("Helvetica", 10)
    c.setFillColor(colors.gray)
    c.drawString(50, h - 70, f"Submission ID: {submission_id} | {data['applied_at']} UTC")

    y = h - 110
    c.setFont("Helvetica-Bold", 12)
    c.setFillColor(colors.black)
    c.drawString(50, y, "APPLICANT DETAILS")
    y -= 20
    c.setFont("Helvetica", 11)

    fields = [
        ("Name", data["name"]),
        ("Email", data["email"]),
        ("GitHub", data["github_url"]),
        ("Role", "Core Team" if data["role"] == "CoreTeam" else "Intern"),
        ("Niche", data["niche"]),
        ("Specialization", data["sector"]),
        ("Sub-Sector", data.get("subsector") or "N/A"),
    ]
    for label, val in fields:
        c.drawString(50, y, f"{label}:")
        c.drawString(180, y, str(val)[:80])
        y -= 20

    # Agreement
    y = y - 20
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "ACCEPTED AGREEMENT")
    y -= 25
    c.setFont("Helvetica", 9)

    txt = TEAM_AGREEMENT_TEXT if data["role"] == "CoreTeam" else INTERNSHIP_AGREEMENT_TEXT
    txt = txt.replace("[Full Name]", data["name"])
    txt = txt.replace("[Date]", data["applied_at"].split()[0])
    if data["role"] == "Internship":
        start = data["applied_at"].split()[0]
        from datetime import timedelta
        end = (datetime.fromisoformat(data["applied_at"].replace(' ', 'T')) + timedelta(days=150)).strftime("%Y-%m-%d")
        txt = txt.replace("[Start Date]", start).replace("[End Date]", end)

    for line in txt.split('\n'):
        if y < 60:
            c.showPage()
            y = h - 50
        c.drawString(50, y, line[:90])
        y -= 14

    # Watermark
    c.saveState()
    c.setFont("Helvetica", 40)
    c.setFillColorRGB(0.9, 0.9, 0.9, 0.5)
    c.drawCentredString(w / 2, h / 2, "CONFIDENTIAL")
    c.restoreState()
    c.save()
    return pdf_path

def generate_receipt_pdf(name, role, email, submission_id):
    pdf_path = os.path.join(PDF_FOLDER, f"RECEIPT_{submission_id}.pdf")
    c = canvas.Canvas(pdf_path, pagesize=A4)
    w, h = A4

    c.setFillColor(colors.Color(0.05, 0.1, 0.2, alpha=0.95))
    c.rect(0, h - 100, w, 100, fill=1)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 26)
    c.drawCentredString(w / 2, h - 50, "LUNVEX LABS")
    c.setFont("Helvetica", 12)
    c.setFillColor(colors.Color(0.8, 0.9, 1.0))
    c.drawCentredString(w / 2, h - 75, "Global Technology Initiative")

    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(w / 2, h - 130, "✅ Application Submitted")

    y = h - 170
    info = [
        f"Applicant: {html.escape(name)}",
        f"Pathway: {'Core Team' if role == 'CoreTeam' else 'Internship'}",
        f"Email: {html.escape(email)}",
        f"Submission ID: {submission_id}",
        f"Submitted: {datetime.now(timezone.utc).strftime('%B %d, %Y at %I:%M %p UTC')}"
    ]
    for line in info:
        c.drawString(80, y, line)
        y -= 28

    c.setFont("Helvetica", 12)
    c.setFillColor(colors.Color(0.05, 0.65, 0.9))
    c.drawString(80, y - 20, "Next Step:")
    c.setFont("Helvetica", 11)
    c.setFillColor(colors.black)
    c.drawString(80, y - 40, "Contact the Founder on Telegram for confirmation:")
    c.setFillColor(colors.blue)
    c.drawString(80, y - 60, "@EfajTahamidRIFAT")

    c.setFillColor(colors.gray)
    c.setFont("Helvetica", 9)
    c.drawCentredString(w / 2, 50, "This receipt confirms submission only. No selection is guaranteed.")
    c.setFillColor(colors.Color(0.05, 0.65, 0.9))
    c.rect(0, 0, w, 8, fill=1)
    c.save()
    return pdf_path

# ---------------- Templates ----------------
# (HOME_TEMPLATE, APPLY_TEMPLATE, FAQ_TEMPLATE, INVESTORS_TEMPLATE remain exactly as in previous full code)
# For brevity, they are included below in full.

HOME_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Lunvex Labs | We Are Hiring</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style> body { font-family: 'Inter', sans-serif; background: #0f172a; color: white; margin: 0; padding: 0; }
        .hero { text-align: center; padding: 80px 20px; }
        .hero h1 { font-size: 48px; margin-bottom: 20px; color: #0ea5e9; }
        .hero p { font-size: 20px; max-width: 700px; margin: 0 auto 40px; color: #cbd5e1; }
        .nav { display: flex; justify-content: center; gap: 30px; margin-bottom: 60px; }
        .nav a { color: #94a3b8; text-decoration: none; font-weight: 500; }
        .nav a:hover { color: #0ea5e9; }
        .btn { display: inline-block; background: #0ea5e9; color: white; padding: 14px 32px; border-radius: 12px; text-decoration: none; font-weight: 600; margin-top: 20px; }
    </style>
</head>
<body>
    <div class="hero">
        <h1>We Are Hiring</h1>
        <p>Lunvex Labs is seeking exceptional global talent for its Core Team and Internship Program in Cybersecurity, AI, Web3, and more.</p>
        <a href="/apply" class="btn">Apply Now</a>
    </div>
    <div class="nav">
        <a href="/">Home</a>
        <a href="/apply">Apply</a>
        <a href="/faqs">FAQs</a>
        <a href="/investors">Investors</a>
    </div>
</body>
</html>
"""

APPLY_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Apply | Lunvex Labs</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root { --primary: #0ea5e9; }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Inter', sans-serif;
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
            color: white;
            min-height: 100vh;
            padding: 20px;
        }
        .card {
            background: rgba(15, 23, 42, 0.7);
            backdrop-filter: blur(12px);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 20px;
            padding: 32px;
            margin: 40px auto;
            max-width: 800px;
            width: 100%;
        }
        h1 { font-weight: 700; font-size: 28px; text-align: center; margin-bottom: 10px; }
        .pathway-info {
            background: rgba(14, 165, 233, 0.15);
            padding: 14px;
            border-radius: 12px;
            font-size: 14px;
            margin-bottom: 24px;
            line-height: 1.5;
        }
        label { display: block; margin-top: 20px; font-weight: 600; font-size: 14px; }
        input, select, button {
            width: 100%; padding: 14px; margin-top: 8px; margin-bottom: 22px;
            border: 1px solid rgba(255,255,255,0.2);
            border-radius: 12px;
            font-size: 15px;
            background: rgba(0,0,0,0.2);
            color: white;
        }
        button {
            background: linear-gradient(135deg, #0ea5e9, #38bdf8);
            color: white;
            font-weight: 600;
            border: none;
            cursor: pointer;
        }
        .checkbox-group { display: flex; align-items: flex-start; margin: 24px 0; }
        .checkbox-group input[type="checkbox"] {
            width: auto; margin-right: 14px; margin-top: 4px; accent-color: var(--primary);
        }
        .notice {
            background: rgba(56, 189, 248, 0.15);
            border-left: 4px solid #0ea5e9;
            padding: 16px;
            border-radius: 0 8px 8px 0;
            margin: 24px 0;
            font-size: 14px;
            line-height: 1.5;
        }
        .nav { text-align: center; margin-bottom: 20px; }
        .nav a { color: #94a3b8; text-decoration: none; margin: 0 15px; }
        .nav a:hover { color: #0ea5e9; }
    </style>
</head>
<body>
    <div class="nav">
        <a href="/">Home</a> | 
        <a href="/apply">Apply</a> | 
        <a href="/faqs">FAQs</a> | 
        <a href="/investors">Investors</a>
    </div>

    <div class="card">
        <h1>Apply to Lunvex Labs</h1>
        
        <div class="pathway-info">
            <strong>Core Team</strong>: Performance-driven role. No salary. Discretionary rewards.<br>
            <strong>Internship</strong>: 5-month unpaid program. Certificate issued. Top performers may join Core Team.
        </div>

        <form method="post" enctype="multipart/form-data">
            <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
            
            <label for="role">I want to...</label>
            <select name="role" id="role" required>
                <option value="">Select your pathway</option>
                <option value="CoreTeam">Apply to Join Core Team</option>
                <option value="Internship">Apply for Internship</option>
            </select>

            <label for="name">Full Name</label>
            <input type="text" name="name" id="name" required maxlength="100">

            <label for="email">Email</label>
            <input type="email" name="email" id="email" required maxlength="100">

            <label for="niche">Niche</label>
            <select name="niche" id="niche" required>
                <option value="">Select Niche</option>
                {% for niche in niches.keys() %}
                <option value="{{ niche }}">{{ niche }}</option>
                {% endfor %}
            </select>

            <label for="sector">Specialization</label>
            <select name="sector" id="sector" required>
                <option value="">Select Specialization</option>
            </select>

            <label for="subsector">Sub-Sector (Optional)</label>
            <select name="subsector" id="subsector">
                <option value="">Not Applicable</option>
            </select>

            <label for="socials">GitHub Profile (Required)</label>
            <input type="url" name="socials" id="socials" placeholder="https://github.com/your-username" required maxlength="100" pattern="https://github\.com/([a-zA-Z0-9_-]+)/?$">
            <p style="font-size:13px;color:#94a3b8;margin-top:6px;">
              🔒 Only public GitHub profiles accepted. Used for technical verification.
            </p>

            <label>Photo (JPEG/PNG, max 5MB)</label>
            <input type="file" name="photo" accept="image/jpeg,image/png" required>

            <label>Signature (JPEG/PNG, max 5MB)</label>
            <input type="file" name="signature" accept="image/jpeg,image/png" required>

            <div class="checkbox-group" id="unpaid-ack" style="display:none;">
                <input type="checkbox" name="unpaid_ack" id="unpaid_ack" required>
                <label for="unpaid_ack" style="font-weight:500;">
                    I understand this is an unpaid educational internship and confirm my voluntary participation.
                </label>
            </div>

            <div class="checkbox-group">
                <input type="checkbox" name="agreement" id="agreement" required>
                <label for="agreement" style="font-weight:500;">
                    I have read and agree to the Lunvex Labs Agreement and policies.
                </label>
            </div>

            <div class="notice">
              📌 <strong>This submission is not final.</strong><br>
              It is a preliminary expression of interest only.<br>
              <strong>No selection, offer, or engagement is guaranteed.</strong><br>
              Only shortlisted candidates will be contacted by the Founder on Telegram.
            </div>

            <button type="submit">Submit Application</button>
        </form>
    </div>

    <script>
        const NICHES_DATA = {{ niches | tojson }};
        const roleSelect = document.getElementById('role');
        const nicheSelect = document.getElementById('niche');
        const sectorSelect = document.getElementById('sector');
        const subsectorSelect = document.getElementById('subsector');
        const unpaidAck = document.getElementById('unpaid-ack');

        function updateSectors() {
            const niche = nicheSelect.value;
            sectorSelect.innerHTML = '<option value="">Select Specialization</option>';
            subsectorSelect.innerHTML = '<option value="">Not Applicable</option>';
            if (niche && NICHES_DATA[niche]) {
                Object.keys(NICHES_DATA[niche]).forEach(sector => {
                    const opt = document.createElement('option');
                    opt.value = sector;
                    opt.textContent = sector;
                    sectorSelect.appendChild(opt);
                });
            }
        }

        function updateSubsectors() {
            const niche = nicheSelect.value;
            const sector = sectorSelect.value;
            subsectorSelect.innerHTML = '<option value="">Not Applicable</option>';
            if (niche && sector && NICHES_DATA[niche]?.[sector]) {
                NICHES_DATA[niche][sector].forEach(sub => {
                    const opt = document.createElement('option');
                    opt.value = sub;
                    opt.textContent = sub;
                    subsectorSelect.appendChild(opt);
                });
            }
        }

        roleSelect.addEventListener('change', () => {
            unpaidAck.style.display = roleSelect.value === 'Internship' ? 'flex' : 'none';
        });
        nicheSelect.addEventListener('change', updateSectors);
        sectorSelect.addEventListener('change', updateSubsectors);
    </script>
</body>
</html>
"""

FAQ_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FAQs | Lunvex Labs</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Inter', sans-serif; background: #0f172a; color: white; margin: 0; padding: 0; }
        .container { max-width: 800px; margin: 40px auto; padding: 0 20px; }
        h1 { text-align: center; margin-bottom: 40px; color: #0ea5e9; }
        .faq { margin-bottom: 24px; padding-bottom: 24px; border-bottom: 1px solid #334155; }
        .faq h3 { margin-bottom: 10px; color: #f1f5f9; }
        .faq p { color: #cbd5e1; line-height: 1.6; }
        .nav { text-align: center; margin-bottom: 30px; }
        .nav a { color: #94a3b8; text-decoration: none; margin: 0 15px; }
        .nav a:hover { color: #0ea5e9; }
    </style>
</head>
<body>
    <div class="nav">
        <a href="/">Home</a> | 
        <a href="/apply">Apply</a> | 
        <a href="/faqs">FAQs</a> | 
        <a href="/investors">Investors</a>
    </div>
    <div class="container">
        <h1>Frequently Asked Questions</h1>
        
        <div class="faq">
            <h3>Is the internship paid?</h3>
            <p>No. The internship is an unpaid educational program designed to provide hands-on experience. Exceptional performers may be invited to join the Core Team.</p>
        </div>
        
        <div class="faq">
            <h3>Is the Core Team role salaried?</h3>
            <p>No. Core Team roles are performance-driven. Compensation (bonuses, equity, commissions) is discretionary and based on measurable impact.</p>
        </div>
        
        <div class="faq">
            <h3>Why do I need to provide GitHub and a real email?</h3>
            <p>We require a public GitHub profile to verify your technical background. All confirmations are sent manually by the Founder (<a href='https://t.me/EfajTahamidRIFAT' style='color:#0ea5e9'>@EfajTahamidRIFAT</a>) via Telegram after reviewing your application.</p>
        </div>
        
        <div class="faq">
            <h3>Will I be selected if I apply?</h3>
            <p>No. Submission is <strong>not final</strong> and does not guarantee selection. Only a limited number of highly qualified candidates are shortlisted. If selected, the Founder will respond to your Telegram message.</p>
        </div>
        
        <div class="faq">
            <h3>What happens after I submit my application?</h3>
            <p>You will receive a verification receipt. Please DM <a href="https://t.me/EfajTahamidRIFAT" style="color:#0ea5e9">@EfajTahamidRIFAT</a> on Telegram for confirmation and next steps.</p>
        </div>
        
        <div class="faq">
            <h3>Where is Lunvex Labs based?</h3>
            <p>Lunvex Labs is a global initiative with team members across multiple time zones. All collaboration happens remotely via official channels.</p>
        </div>
    </div>
</body>
</html>
"""

INVESTORS_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Investors | Lunvex Labs</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        body { 
            font-family: 'Inter', sans-serif; 
            background: #0f172a; 
            color: white; 
            margin: 0; 
            padding: 0; 
        }
        .container { 
            max-width: 800px; 
            margin: 40px auto; 
            padding: 0 20px; 
        }
        h1 { 
            text-align: center; 
            margin-bottom: 30px; 
            color: #0ea5e9; 
            font-weight: 700;
        }
        p { 
            color: #cbd5e1; 
            line-height: 1.7; 
            margin-bottom: 20px; 
        }
        .highlight { 
            background: rgba(14, 165, 233, 0.12); 
            border-left: 3px solid #0ea5e9; 
            padding: 18px; 
            border-radius: 0 8px 8px 0;
            margin: 24px 0;
        }
        .contact { 
            background: rgba(14, 165, 233, 0.15); 
            padding: 24px; 
            border-radius: 16px; 
            margin-top: 30px; 
            text-align: center;
        }
        .contact a { 
            color: #0ea5e9; 
            text-decoration: underline; 
            font-weight: 600;
            font-size: 16px;
        }
        .nav { 
            text-align: center; 
            margin-bottom: 30px; 
        }
        .nav a { 
            color: #94a3b8; 
            text-decoration: none; 
            margin: 0 15px; 
        }
        .nav a:hover { 
            color: #0ea5e9; 
        }
        .disclaimer { 
            font-size: 13px; 
            color: #64748b; 
            margin-top: 30px; 
            line-height: 1.5;
        }
    </style>
</head>
<body>
    <div class="nav">
        <a href="/">Home</a> | 
        <a href="/apply">Apply</a> | 
        <a href="/faqs">FAQs</a> | 
        <a href="/investors">Investors</a>
    </div>
    
    <div class="container">
        <h1>Strategic Investment Opportunity</h1>
        
        <p>
            <strong>Lunvex Labs</strong> is a global technology initiative founded by <strong>Dewan Efaj Tahamid Rifat</strong>, 
            focused on next-generation solutions in <strong>Cybersecurity, AI, and Web3 infrastructure</strong>.
        </p>

        <div class="highlight">
            🔐 <strong>Ownership Structure</strong><br>
            • Founder holds <strong>80%</strong> of the company<br>
            • <strong>20% equity</strong> is reserved for strategic investors (18+ only)<br>
            • No public token sale. No crowdfunding. Only direct, private participation.
        </div>

        <p>
            We are not seeking passive capital — we seek <strong>aligned partners</strong> who believe in secure, 
            decentralized innovation and can add strategic value beyond funding.
        </p>

        <p>
            As a <em>“crypto hunter”</em>, the Founder prioritizes builders, security researchers, and visionaries 
            who understand the intersection of trust, technology, and execution.
        </p>

        <div class="contact">
            <strong>For qualified investors only:</strong><br>
            Contact the Founder directly on Telegram:<br>
            <a href="https://t.me/EfajTahamidRIFAT" target="_blank">@EfajTahamidRIFAT</a>
        </div>

        <div class="disclaimer">
            <strong>Disclaimer:</strong> This page is an invitation for preliminary discussion only. 
            No securities are offered or sold via this website. Investment opportunities, if any, 
            will be presented under separate, confidential agreements compliant with applicable laws. 
            You must be 18+ and accredited (where required) to participate.
        </div>
    </div>
</body>
</html>
"""

# ---------------- Routes ----------------
@app.route("/")
def home():
    return render_template_string(HOME_TEMPLATE)

@app.route("/apply", methods=["GET", "POST"])
def apply():
    if request.method == "GET":
        token = secrets.token_urlsafe(32)
        return render_template_string(APPLY_TEMPLATE, niches=NICHES, csrf_token=token)

    token = request.form.get('csrf_token')
    if not token or len(token) < 20:
        abort(400)

    try:
        name = html.escape(request.form.get("name", "").strip()[:100])
        email = html.escape(request.form.get("email", "").strip()[:100].lower())
        role = request.form.get("role")
        niche = request.form.get("niche")
        sector = request.form.get("sector")
        subsector = request.form.get("subsector") or ""
        github_url = request.form.get("socials", "").strip()
        agreed = request.form.get("agreement") == "on"

        if not all([name, email, role, niche, sector, github_url]):
            return "<h2 style='text-align:center;color:#ef4444;margin:40px;'>❌ All fields are required.</h2>", 400

        if role not in ["CoreTeam", "Internship"]:
            return "<h2 style='text-align:center;color:#ef4444;margin:40px;'>❌ Invalid selection.</h2>", 400

        if niche not in NICHES or sector not in NICHES[niche]:
            return "<h2 style='text-align:center;color:#ef4444;margin:40px;'>❌ Invalid niche or specialization.</h2>", 400

        if subsector and subsector not in NICHES[niche][sector]:
            return "<h2 style='text-align:center;color:#ef4444;margin:40px;'>❌ Invalid sub-sector.</h2>", 400

        if not is_valid_github_url(github_url):
            return "<h2 style='text-align:center;color:#ef4444;margin:40px;'>❌ Provide a valid GitHub URL (e.g., https://github.com/yourname)</h2>", 400

        if not agreed:
            return "<h2 style='text-align:center;color:#ef4444;margin:40px;'>❌ Agreement is required.</h2>", 400

        if role == "Internship" and request.form.get("unpaid_ack") != "on":
            return "<h2 style='text-align:center;color:#ef4444;margin:40px;'>❌ Acknowledge unpaid nature.</h2>", 400

        photo = request.files.get("photo")
        signature = request.files.get("signature")
        if not photo or not signature or not photo.filename or not signature.filename:
            return "<h2 style='text-align:center;color:#ef4444;margin:40px;'>❌ Valid photo and signature required.</h2>", 400

        if not (allowed_file(photo.filename) and allowed_file(signature.filename)):
            return "<h2 style='text-align:center;color:#ef4444;margin:40px;'>❌ Only JPG/PNG allowed.</h2>", 400

        photo_path = save_uploaded_file(photo, "photo")
        signature_path = save_uploaded_file(signature, "signature")

        if not (is_valid_image(photo_path) and is_valid_image(signature_path)):
            os.remove(photo_path)
            os.remove(signature_path)
            return "<h2 style='text-align:center;color:#ef4444;margin:40px;'>❌ Invalid image format.</h2>", 400

        applied_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        submission_id = f"LX{int(time.time())}_{hashlib.sha256(email.encode()).hexdigest()[:8]}"

        try:
            with get_db() as conn:
                conn.execute("""
                    INSERT INTO applicants 
                    (submission_id, name, email, role, niche, sector, subsector, github_url, photo_path, signature_path, agreed, applied_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (submission_id, name, email, role, niche, sector, subsector, github_url, photo_path, signature_path, True, applied_at))
                conn.commit()
        except sqlite3.IntegrityError:
            os.remove(photo_path)
            os.remove(signature_path)
            return "<h2 style='text-align:center;color:#ef4444;margin:40px;'>❌ Already applied for this pathway.</h2>", 400

        internal_pdf = generate_internal_pdf({
            "name": name,
            "email": email,
            "role": role,
            "niche": niche,
            "sector": sector,
            "subsector": subsector,
            "github_url": github_url,
            "applied_at": applied_at
        }, photo_path, signature_path, submission_id)

        receipt_pdf = generate_receipt_pdf(name, role, email, submission_id)

        # Upload to R2 with per-user prefix
        user_prefix = f"submissions/{submission_id}/"
        upload_to_r2(internal_pdf, f"{user_prefix}INTERNAL_RECORD.pdf")
        upload_to_r2(receipt_pdf, f"{user_prefix}RECEIPT.pdf")
        upload_to_r2(photo_path, f"{user_prefix}photo.jpg")
        upload_to_r2(signature_path, f"{user_prefix}signature.png")
        backup_db_to_r2()

        # Cleanup
        for f in [photo_path, signature_path, internal_pdf, receipt_pdf]:
            if os.path.exists(f):
                os.remove(f)

        return f"""
        <div style="max-width:600px;margin:60px auto;text-align:center;font-family:'Inter',sans-serif;
                    background:rgba(15,23,42,0.85);padding:36px;border-radius:20px;color:white;">
            <h2 style="color:#0ea5e9;font-weight:700;">✅ Application Submitted</h2>
            <p style="font-size:16px;margin:16px 0;">Thank you, <strong>{html.escape(name)}</strong>!</p>
            <p style="font-size:15px;color:#94a3b8;margin-top:20px;background:rgba(30,41,59,0.6);padding:16px;border-radius:12px;line-height:1.5;">
              📌 <strong>This submission is not final.</strong><br>
              Only shortlisted candidates will be contacted by the Founder on Telegram:<br>
              <a href="https://t.me/EfajTahamidRIFAT" style="color:#0ea5e9;">@EfajTahamidRIFAT</a><br>
              <em>Efaj will never DM you first — you must initiate contact.</em>
            </p>
            <p style="font-size:13px;color:#64748b;margin-top:20px;">
                Submission ID: <code>{submission_id}</code>
            </p>
        </div>
        <div style="text-align:center;margin-top:20px;">
            <a href="/" style="color:#0ea5e9;">← Back to Home</a>
        </div>
        """

    except Exception as e:
        app.logger.exception("Submission failed")
        return """
        <div style="max-width:600px;margin:60px auto;text-align:center;font-family:'Inter',sans-serif;color:#ef4444;">
            <h2>❌ Submission Failed</h2>
            <p>An unexpected error occurred. Please try again.</p>
            <a href="/apply" style="color:#0ea5e9;">← Try Again</a>
        </div>
        """, 500

@app.route("/faqs")
def faqs():
    return render_template_string(FAQ_TEMPLATE)

@app.route("/investors")
def investors():
    return render_template_string(INVESTORS_TEMPLATE)

if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
