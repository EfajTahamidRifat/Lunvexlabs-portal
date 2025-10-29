import os
import time
import sqlite3
import html
import imghdr
from flask import Flask, render_template_string, request
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
import dropbox

# ---------------- Configuration ----------------
DROPBOX_TOKEN = os.getenv("DROPBOX_TOKEN")
if not DROPBOX_TOKEN:
    raise EnvironmentError("DROPBOX_TOKEN environment variable is required.")

UPLOAD_FOLDER = "uploads"
PDF_FOLDER = "pdfs"
DATABASE = "lunvex.db"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PDF_FOLDER, exist_ok=True)

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Initialize Dropbox
try:
    dbx = dropbox.Dropbox(DROPBOX_TOKEN)
    dbx.users_get_current_account()
except Exception as e:
    app.logger.error(f"Dropbox setup failed: {e}")
    raise

# ---------------- Agreements ----------------
TEAM_AGREEMENT_HTML = """
<h3>LUNVEX LABS – CORE TEAM MEMBER AGREEMENT</h3>
<p><strong>This legally binding Agreement</strong> (“Agreement”) is entered into on [Date] by and between:</p>
<p><strong>Lunvex Labs</strong>, a global technology initiative (“the Organization”), and <strong>[Full Name]</strong> (“the Member”).</p>
<ol>
  <li><strong>Engagement</strong><br>You are appointed as a Core Team Member in your declared Niche and Specialization. This is an indefinite, performance-based engagement.</li>
  <li><strong>Confidentiality</strong><br>All non-public information (technical, strategic, or operational) is strictly confidential. Unauthorized disclosure constitutes grounds for immediate termination and legal action.</li>
  <li><strong>Intellectual Property</strong><br>All work product, code, designs, or research created during your tenure is the sole and exclusive property of Lunvex Labs.</li>
  <li><strong>Compensation</strong><br>This role is performance-driven. No fixed salary is provided. Rewards (bonuses, equity, or commissions) are discretionary and based on measurable impact.</li>
  <li><strong>Termination</strong><br>• You may resign with 14 days’ written notice.<br>• Lunvex Labs reserves the right to terminate immediately for breach of conduct, inactivity (>14 days), or security violations.</li>
  <li><strong>Professional Conduct</strong><br>All communication must occur via official Lunvex Labs channels (e.g., verified Telegram, email). Unprofessional behavior is not tolerated.</li>
</ol>
"""

INTERNSHIP_AGREEMENT_HTML = """
<h3>LUNVEX LABS – INTERNSHIP AGREEMENT</h3>
<p><strong>This educational Agreement</strong> (“Agreement”) is entered into on [Date] by and between:</p>
<p><strong>Lunvex Labs</strong>, a global technology initiative (“the Organization”), and <strong>[Full Name]</strong> (“the Intern”).</p>
<ol>
  <li><strong>Term</strong><br>5-month unpaid internship from [Start Date] to [End Date]. Extension is at the Organization’s sole discretion.</li>
  <li><strong>Purpose</strong><br>Hands-on mentorship in your chosen Niche and Specialization to build real-world skills.</li>
  <li><strong>Confidentiality</strong><br>All internal materials, tools, and communications are confidential. Disclosure is prohibited during and after the internship.</li>
  <li><strong>Unpaid Nature</strong><br>This is a <strong>voluntary, unpaid educational program</strong>. No salary, stipend, or benefits are provided. Successful completion yields an Official Certificate.</li>
  <li><strong>Pathway to Core Team</strong><br>Exceptional performers may receive an invitation to join the Core Team post-internship.</li>
  <li><strong>Termination</strong><br>Lunvex Labs may terminate for misconduct, absenteeism, or breach. You may withdraw with 7 days’ notice.</li>
</ol>
"""

TEAM_AGREEMENT_PDF = """LUNVEX LABS – CORE TEAM MEMBER AGREEMENT

This legally binding Agreement (“Agreement”) is entered into on [Date] by and between:
Lunvex Labs (“the Organization”) and [Full Name] (“the Member”).

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
All communication must occur via official Lunvex Labs channels (e.g., verified Telegram, email). Unprofessional behavior is not tolerated.
"""

INTERNSHIP_AGREEMENT_PDF = """LUNVEX LABS – INTERNSHIP AGREEMENT

This educational Agreement (“Agreement”) is entered into on [Date] by and between:
Lunvex Labs (“the Organization”) and [Full Name] (“the Intern”).

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
"""

# ---------------- Niches ----------------
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

# ---------------- Database ----------------
def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS applicants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('CoreTeam', 'Internship')),
            niche TEXT NOT NULL,
            sector TEXT NOT NULL,
            subsector TEXT,
            socials TEXT NOT NULL,
            photo TEXT NOT NULL,
            signature TEXT NOT NULL,
            agreed BOOLEAN NOT NULL DEFAULT 1,
            status TEXT DEFAULT 'Pending',
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(email, role)
        )
    """)
    conn.commit()
    conn.close()

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def is_valid_image(filepath):
    return imghdr.what(filepath) in ('jpeg', 'png')

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_uploaded_file(file, prefix):
    filename = file.filename.strip().replace(' ', '_').replace('..', '').replace('/', '')
    if not filename:
        filename = "unnamed"
    path = os.path.join(app.config["UPLOAD_FOLDER"], f"{prefix}_{int(time.time())}_{filename}")
    file.save(path)
    return path

# ---------------- PDF Generators ----------------
def generate_agreement_pdf(data, photo_path, signature_path):
    pdf_filename = f"AGREEMENT_{data['name'].replace(' ', '_')}_{int(time.time())}.pdf"
    pdf_path = os.path.join(PDF_FOLDER, pdf_filename)
    c = canvas.Canvas(pdf_path, pagesize=A4)
    width, height = A4

    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 50, "Lunvex Labs – Application Record")

    y = height - 90
    c.setFont("Helvetica", 12)
    role_display = "Core Team Member" if data["role"] == "CoreTeam" else "Intern"
    fields = [
        ("Name", data["name"]),
        ("Email", data["email"]),
        ("Role", role_display),
        ("Niche", data["niche"]),
        ("Specialization", data["sector"]),
        ("Sub-Sector", data.get("subsector") or "N/A"),
        ("Social Links", data["socials"])
    ]
    for label, value in fields:
        c.drawString(50, y, f"{label}: {value}")
        y -= 22

    if os.path.exists(photo_path):
        c.drawImage(photo_path, 50, y - 120, width=100, height=100)
    if os.path.exists(signature_path):
        c.drawImage(signature_path, 50, y - 240, width=200, height=50)

    y = y - 280
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "AGREEMENT:")
    y -= 20
    c.setFont("Helvetica", 9)

    agreement_text = TEAM_AGREEMENT_PDF if data["role"] == "CoreTeam" else INTERNSHIP_AGREEMENT_PDF
    agreement_text = agreement_text.replace("[Full Name]", data["name"])
    agreement_text = agreement_text.replace("[Date]", time.strftime("%B %d, %Y"))

    for line in agreement_text.split('\n'):
        if y < 50:
            c.showPage()
            y = height - 50
        c.drawString(50, y, line[:100])
        y -= 14

    c.save()
    return pdf_path

def generate_verification_pdf(name, role, email, submission_id):
    filename = f"VERIFICATION_{name.replace(' ', '_')}_{int(time.time())}.pdf"
    filepath = os.path.join(PDF_FOLDER, filename)
    c = canvas.Canvas(filepath, pagesize=A4)
    width, height = A4

    # Header background
    c.setFillColor(colors.Color(0.05, 0.1, 0.2, alpha=0.92))
    c.rect(0, height - 120, width, 120, fill=1, stroke=0)

    # Logo text
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 28)
    c.drawCentredString(width / 2, height - 60, "LUNVEX LABS")
    c.setFont("Helvetica", 14)
    c.setFillColor(colors.Color(0.7, 0.85, 0.95))
    c.drawCentredString(width / 2, height - 85, "Global Technology Initiative")

    # Success message
    c.setFillColor(colors.Color(0.05, 0.1, 0.2))
    c.setFont("Helvetica-Bold", 22)
    c.drawCentredString(width / 2, height - 160, "✅ Application Submitted")

    # Details
    c.setFont("Helvetica", 12)
    y = height - 200
    info = [
        f"Applicant: {name}",
        f"Pathway: {'Core Team' if role == 'CoreTeam' else 'Internship'}",
        f"Email: {email}",
        f"Submission ID: {submission_id}",
        f"Submitted: {time.strftime('%B %d, %Y at %I:%M %p UTC')}"
    ]
    for line in info:
        c.drawString(80, y, line)
        y -= 24

    # Footer
    c.setFillColor(colors.gray)
    c.setFont("Helvetica", 10)
    c.drawCentredString(width / 2, 80, "This is an automated verification receipt. Keep it for your records.")

    # Accent bar
    c.setFillColor(colors.Color(0.05, 0.65, 0.9))
    c.rect(0, 0, width, 10, fill=1, stroke=0)

    c.save()
    return filepath

# ---------------- HTML Template ----------------
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Join Lunvex Labs | Global Tech Talent</title>
    <meta name="description" content="Apply to Lunvex Labs' Core Team or Internship Program. Performance-driven, global, and confidential.">
    <link rel="preload" href="https://i.ibb.co/jktGByvB/grok-image-jw1wft.jpg" as="image">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/tsparticles@2.12.0/tsparticles.bundle.min.js"></script>
    <style>
        :root {
            --primary: #0ea5e9;
            --primary-light: #bae6fd;
            --gray-900: #0f172a;
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Inter', sans-serif;
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
            color: white;
            min-height: 100vh;
            padding: 20px;
            display: flex;
            justify-content: center;
            align-items: flex-start;
            position: relative;
            overflow-x: hidden;
        }
        #tsparticles { position: fixed; top: 0; left: 0; width: 100%; height: 100%; z-index: -1; }
        #app-loader {
            position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
            display: flex; justify-content: center; align-items: center;
            z-index: 10000; opacity: 1; visibility: visible;
            transition: opacity 0.6s ease, visibility 0.6s ease;
        }
        #app-loader.hidden { opacity: 0; visibility: hidden; }
        .loader {
            width: 160px; height: 185px; position: relative; background: #fff;
            border-radius: 100px 100px 0 0;
        }
        .loader:after {
            content: ""; position: absolute; width: 100px; height: 125px; left: 50%; top: 25px; transform: translateX(-50%);
            background-image: radial-gradient(circle, #000 48%, transparent 55%),
                radial-gradient(circle, #000 48%, transparent 55%),
                radial-gradient(circle, #fff 30%, transparent 45%),
                radial-gradient(circle, #000 48%, transparent 51%),
                linear-gradient(#000 20px, transparent 0),
                linear-gradient(#cfecf9 60px, transparent 0),
                radial-gradient(circle, #cfecf9 50%, transparent 51%),
                radial-gradient(circle, #cfecf9 50%, transparent 51%);
            background-repeat: no-repeat;
            background-size: 16px 16px, 16px 16px, 10px 10px, 42px 42px, 12px 3px,
                50px 25px, 70px 70px, 70px 70px;
            background-position: 25px 10px, 55px 10px, 36px 44px, 50% 30px, 50% 85px,
                50% 50px, 50% 22px, 50% 45px;
            animation: faceLift 3s linear infinite alternate;
        }
        .loader:before {
            content: ""; position: absolute; width: 140%; height: 125px; left: -20%; top: 0;
            background-image: radial-gradient(circle, #fff 48%, transparent 50%),
                radial-gradient(circle, #fff 48%, transparent 50%);
            background-repeat: no-repeat;
            background-size: 65px 65px;
            background-position: 0px 12px, 145px 12px;
            animation: earLift 3s linear infinite alternate;
        }
        @keyframes faceLift { 0% { transform: translateX(-60%); } 100% { transform: translateX(-30%); } }
        @keyframes earLift { 0% { transform: translateX(10px); } 100% { transform: translateX(0px); } }

        .card {
            background: rgba(255, 255, 255, 0.08);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border: 1px solid rgba(255, 255, 255, 0.12);
            border-radius: 20px;
            padding: 32px;
            margin-bottom: 28px;
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2), inset 0 0 0 1px rgba(255, 255, 255, 0.05);
            transition: transform 0.35s cubic-bezier(0.23, 1, 0.32, 1), box-shadow 0.35s ease;
            position: relative;
            overflow: hidden;
            max-width: 800px;
            width: 100%;
        }
        .card:hover { transform: translateY(-6px); box-shadow: 0 14px 36px rgba(0, 0, 0, 0.3), inset 0 0 0 1px rgba(255, 255, 255, 0.08); }
        .card::before {
            content: ''; position: absolute; top: 0; left: 0; right: 0; height: 4px;
            background: linear-gradient(90deg, #0ea5e9, #38bdf8, #0ea5e9);
            background-size: 200% 100%; animation: cardGlow 3s linear infinite; opacity: 0.7;
        }
        @keyframes cardGlow { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }
        .agreement-card { padding: 28px !important; margin-top: 12px; }
        h1 { font-weight: 700; font-size: 28px; text-align: center; color: white; margin-bottom: 8px; }
        .subtitle { text-align: center; color: rgba(255,255,255,0.85); font-size: 16px; margin-bottom: 28px; line-height: 1.5; }
        .logo { display: block; margin: 0 auto 20px; max-width: 140px; filter: drop-shadow(0 2px 8px rgba(0,0,0,0.3)); }
        .path-card {
            background: rgba(14, 165, 233, 0.08);
            border-left: 3px solid #0ea5e9;
            padding: 14px;
            border-radius: 0 12px 12px 0;
            margin: 16px 0;
            font-size: 14px;
        }
        label { display: block; margin-top: 20px; font-weight: 600; font-size: 14px; color: white; }
        input, select, button {
            width: 100%; padding: 14px 18px; margin-top: 8px; margin-bottom: 22px;
            border: 1px solid rgba(255,255,255,0.2); border-radius: 14px;
            font-size: 15px; font-family: inherit;
            background: rgba(255,255,255,0.06); color: white;
            transition: all 0.3s ease; backdrop-filter: blur(4px);
        }
        input:focus, select:focus {
            outline: none; border-color: var(--primary);
            background: rgba(14, 165, 233, 0.15);
            box-shadow: 0 0 0 3px rgba(14, 165, 233, 0.3);
        }
        button {
            background: linear-gradient(135deg, #0ea5e9, #38bdf8);
            color: white; font-weight: 600; border: none; cursor: pointer;
            letter-spacing: -0.01em; box-shadow: 0 4px 20px rgba(14, 165, 233, 0.4);
        }
        .checkbox-group {
            display: flex; align-items: flex-start; margin: 24px 0;
        }
        .checkbox-group input[type="checkbox"] {
            width: auto; margin-right: 14px; margin-top: 4px; accent-color: var(--primary); transform: scale(1.1);
        }
        .consent-note {
            font-size: 13px; color: rgba(255,255,255,0.7); margin-top: -12px; margin-bottom: 16px; font-style: italic;
        }
        @media (max-width: 600px) { .card { padding: 24px 16px; } h1 { font-size: 24px; } }
    </style>
</head>
<body>
    <div id="app-loader"><div class="loader"></div></div>
    <div id="tsparticles"></div>

    <div class="card">
        <img src="https://i.ibb.co/jktGByvB/grok-image-jw1wft.jpg" alt="Lunvex Labs" class="logo">
        <h1>Join Lunvex Labs</h1>
        <p class="subtitle">Contribute to cutting-edge global projects. Choose your pathway below.</p>

        <div class="path-card"><strong>Core Team</strong>: Performance-driven, indefinite engagement. No fixed salary. Rewards based on impact.</div>
        <div class="path-card"><strong>Internship</strong>: 5-month unpaid educational program. Certificate upon completion. Pathway to Core Team.</div>

        <div class="card agreement-card" id="agreement-preview">
            <p>Please select your pathway to review the full agreement.</p>
        </div>

        <form method="post" enctype="multipart/form-data">
            <label for="role">I want to...</label>
            <select name="role" id="role" required>
                <option value="">Select your pathway</option>
                <option value="CoreTeam">Apply to Join Core Team</option>
                <option value="Internship">Apply for Internship</option>
            </select>

            <label for="name">Full Name</label>
            <input type="text" name="name" id="name" required>

            <label for="email">Email</label>
            <input type="email" name="email" id="email" required>

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

            <label for="socials">Social Links (LinkedIn, GitHub, Portfolio, etc.)</label>
            <input type="text" name="socials" id="socials" placeholder="https://linkedin.com/in/..., https://github.com/..." required>

            <label>Photo (JPEG/PNG)</label>
            <input type="file" name="photo" accept="image/jpeg,image/png" required>

            <label>Signature (JPEG/PNG)</label>
            <input type="file" name="signature" accept="image/jpeg,image/png" required>

            <div class="checkbox-group" id="unpaid-ack" style="display:none;">
                <input type="checkbox" name="unpaid_ack" id="unpaid_ack" required>
                <label for="unpaid_ack" style="font-weight:500; color:white; margin-top: 2px;">
                    I understand this is an unpaid educational internship and confirm my voluntary participation.
                </label>
            </div>

            <div class="checkbox-group">
                <input type="checkbox" name="agreement" id="agreement" required>
                <label for="agreement" style="font-weight:500; color:white; margin-top: 2px;">
                    I have read, understood, and agree to the above agreement and Lunvex Labs' operational policies.
                </label>
            </div>
            <p class="consent-note">
                By submitting, you consent to the storage and processing of your data for recruitment purposes.
            </p>

            <button type="submit">Submit Application</button>
        </form>
    </div>

    <script>
        tsParticles.load("tsparticles", {
            fpsLimit: 60,
            particles: {
                number: { value: 80, density: { enable: true, area: 800 } },
                color: { value: "#0ea5e9" },
                shape: { type: "circle" },
                opacity: { value: 0.3, random: true },
                size: { value: { min: 1, max: 3 } },
                move: {
                    enable: true,
                    speed: 1,
                    direction: "none",
                    random: true,
                    straight: false,
                    outModes: "out"
                }
            },
            interactivity: {
                detectsOn: "canvas",
                events: {
                    onHover: { enable: true, mode: "repulse" },
                    onClick: { enable: true, mode: "push" },
                    resize: true
                }
            },
            detectRetina: true
        });

        const TEAM_AGREEMENT = {{ team_agreement | tojson }};
        const INTERNSHIP_AGREEMENT = {{ internship_agreement | tojson }};
        const NICHES_DATA = {{ niches | tojson }};

        const agreementPreview = document.getElementById('agreement-preview');
        const roleSelect = document.getElementById('role');
        const nicheSelect = document.getElementById('niche');
        const sectorSelect = document.getElementById('sector');
        const subsectorSelect = document.getElementById('subsector');
        const unpaidAck = document.getElementById('unpaid-ack');

        function updateAgreement() {
            const role = roleSelect.value;
            agreementPreview.innerHTML = role === 'CoreTeam' ? TEAM_AGREEMENT : 
                                        role === 'Internship' ? INTERNSHIP_AGREEMENT : 
                                        '<p>Please select your pathway to review the full agreement.</p>';
            agreementPreview.style.animation = 'none';
            setTimeout(() => { agreementPreview.style.animation = 'fadeInUp 0.7s ease forwards'; }, 10);
        }

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

        roleSelect.addEventListener('change', function() {
            updateAgreement();
            unpaidAck.style.display = this.value === 'Internship' ? 'flex' : 'none';
        });
        nicheSelect.addEventListener('change', updateSectors);
        sectorSelect.addEventListener('change', updateSubsectors);

        updateAgreement();

        window.addEventListener('load', () => {
            setTimeout(() => document.getElementById('app-loader')?.classList.add('hidden'), 600);
        });
    </script>
</body>
</html>
"""

# ---------------- Routes ----------------
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        try:
            name = html.escape(request.form.get("name", "").strip())
            email = html.escape(request.form.get("email", "").strip())
            role = request.form.get("role")
            niche = request.form.get("niche")
            sector = request.form.get("sector")
            subsector = request.form.get("subsector") or ""
            socials = html.escape(request.form.get("socials", "").strip())
            agreed = request.form.get("agreement") == "on"

            if not all([name, email, role, niche, sector, socials]):
                return "<h2 style='text-align:center;color:#ef4444;margin:40px;'>❌ All fields are required.</h2>", 400

            if role not in ["CoreTeam", "Internship"]:
                return "<h2 style='text-align:center;color:#ef4444;margin:40px;'>❌ Invalid selection.</h2>", 400

            if niche not in NICHES or sector not in NICHES[niche]:
                return "<h2 style='text-align:center;color:#ef4444;margin:40px;'>❌ Invalid niche or specialization.</h2>", 400

            if subsector and subsector not in NICHES[niche][sector]:
                return "<h2 style='text-align:center;color:#ef4444;margin:40px;'>❌ Invalid sub-sector.</h2>", 400

            if not agreed:
                return "<h2 style='text-align:center;color:#ef4444;margin:40px;'>❌ You must agree to the agreement.</h2>", 400

            if role == "Internship" and request.form.get("unpaid_ack") != "on":
                return "<h2 style='text-align:center;color:#ef4444;margin:40px;'>❌ You must acknowledge the unpaid nature of the internship.</h2>", 400

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

            try:
                with get_db_connection() as conn:
                    conn.execute(
                        """INSERT INTO applicants 
                        (name, email, role, niche, sector, subsector, socials, photo, signature, agreed)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (name, email, role, niche, sector, subsector, socials, photo_path, signature_path, True)
                    )
                    conn.commit()
            except sqlite3.IntegrityError:
                os.remove(photo_path)
                os.remove(signature_path)
                return "<h2 style='text-align:center;color:#ef4444;margin:40px;'>❌ You've already applied for this pathway.</h2>", 400

            # Generate unique submission ID
            submission_id = f"LX{int(time.time())}"

            # 1. Generate full agreement PDF
            agreement_pdf = generate_agreement_pdf({
                "name": name,
                "email": email,
                "role": role,
                "niche": niche,
                "sector": sector,
                "subsector": subsector,
                "socials": socials
            }, photo_path, signature_path)

            # 2. Generate colorful verification PDF
            verification_pdf = generate_verification_pdf(name, role, email, submission_id)

            # Upload both to Dropbox
            for pdf_path in [agreement_pdf, verification_pdf]:
                dropbox_path = f"/LunvexLabs/{os.path.basename(pdf_path)}"
                with open(pdf_path, "rb") as f:
                    dbx.files_upload(f.read(), dropbox_path, mode=dropbox.files.WriteMode.overwrite)

            return f"""
            <div style="max-width:600px;margin:60px auto;text-align:center;font-family:'Inter',sans-serif;
                        background:rgba(15,23,42,0.85);padding:36px;border-radius:20px;color:white;">
                <h2 style="color:#0ea5e9;font-weight:700;">✅ Application Submitted</h2>
                <p style="font-size:16px;margin:16px 0;">Thank you, <strong>{name}</strong>!</p>
                <p>Your application has been securely processed.</p>
                <p style="font-size:14px;color:#94a3b8;margin-top:20px;">
                    Submission ID: <code>{submission_id}</code>
                </p>
                <p style="font-size:13px;color:#64748b;margin-top:24px;">
                    Two PDFs have been generated and stored:<br>
                    • Full agreement record<br>
                    • Colorful verification receipt
                </p>
            </div>
            """

        except Exception as e:
            app.logger.exception("Submission failed")
            return """
            <div style="max-width:600px;margin:60px auto;text-align:center;font-family:'Inter',sans-serif;color:#ef4444;">
                <h2>❌ Submission Failed</h2>
                <p>An unexpected error occurred. Please try again.</p>
            </div>
            """, 500

    return render_template_string(
        HTML_TEMPLATE,
        niches=NICHES,
        team_agreement=TEAM_AGREEMENT_HTML,
        internship_agreement=INTERNSHIP_AGREEMENT_HTML
    )

# ---------------- Run ----------------
if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
