import os
import time
import sqlite3
from flask import Flask, render_template_string, request
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
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

# Initialize and validate Dropbox client
try:
    dbx = dropbox.Dropbox(DROPBOX_TOKEN)
    dbx.users_get_current_account()  # Validates token
except Exception as e:
    app.logger.error(f"Dropbox setup failed: {e}")
    raise

# ---------------- Agreements ----------------
TEAM_AGREEMENT_HTML = """
<h3>LUNVEX LABS – TEAM MEMBER AGREEMENT</h3>
<p><strong>This Team Member Agreement</strong> (“Agreement”) is entered into on [Date] by and between:</p>
<p><strong>Lunvex Labs</strong>, a global technology initiative (“the Organization”), and <strong>[Full Name]</strong> (“the Member”).</p>
<ol>
  <li><strong>Position & Engagement</strong><br>The Member is appointed as an official Team Member in the designated Niche and Specialization. This engagement is indefinite and continues until terminated per Section 5.</li>
  <li><strong>Confidentiality</strong><br>All non-public information accessed during the Member’s tenure is Confidential Information. The Member shall not disclose, reproduce, or exploit it without written authorization.</li>
  <li><strong>Intellectual Property</strong><br>All work product developed in the course of duties for Lunvex Labs is the exclusive property of Lunvex Labs.</li>
  <li><strong>Compensation</strong><br>This role operates under a performance-driven reward model. No fixed salary is guaranteed. Bonuses, commissions, or equity may be offered at the Organization’s discretion.</li>
  <li><strong>Termination</strong><br>• Member may resign with 14 days’ written notice.<br>• Lunvex Labs may terminate immediately for breach of conduct, inactivity, or security violations.</li>
  <li><strong>Communication</strong><br>Official communication occurs via verified Lunvex Labs channels (e.g., Telegram, email). Professional conduct is mandatory.</li>
</ol>
"""

INTERNSHIP_AGREEMENT_HTML = """
<h3>LUNVEX LABS – INTERNSHIP AGREEMENT</h3>
<p><strong>This Internship Agreement</strong> (“Agreement”) is entered into on [Date] by and between:</p>
<p><strong>Lunvex Labs</strong>, a global technology initiative (“the Organization”), and <strong>[Full Name]</strong> (“the Intern”).</p>
<ol>
  <li><strong>Term</strong><br>The internship lasts five (5) months from [Start Date] to [End Date]. Extension is at the Organization’s discretion.</li>
  <li><strong>Purpose</strong><br>Provides hands-on experience in the selected Niche and Specialization under mentorship.</li>
  <li><strong>Confidentiality</strong><br>All non-public information received is Confidential Information and must not be disclosed.</li>
  <li><strong>Compensation & Recognition</strong><br>• This is an unpaid educational internship.<br>• Successful completion yields an Official Certificate of Completion.<br>• Exceptional performers may be invited to join the Core Team.</li>
  <li><strong>Termination</strong><br>Lunvex Labs may terminate for misconduct, absenteeism, or breach. Intern may withdraw with 7 days’ notice.</li>
  <li><strong>Communication</strong><br>Official communication occurs via verified Lunvex Labs channels. Professionalism is required.</li>
</ol>
"""

TEAM_AGREEMENT_PDF = """LUNVEX LABS – TEAM MEMBER AGREEMENT

This Team Member Agreement (“Agreement”) is entered into on [Date] by and between:
Lunvex Labs (“the Organization”) and [Full Name] (“the Member”).

1. POSITION & ENGAGEMENT
The Member is appointed as an official Team Member in the designated Niche and Specialization. This engagement is indefinite and continues until terminated per Section 5.

2. CONFIDENTIALITY
All non-public information accessed during the Member’s tenure is Confidential Information. The Member shall not disclose, reproduce, or exploit it without written authorization.

3. INTELLECTUAL PROPERTY
All work product developed in the course of duties for Lunvex Labs is the exclusive property of Lunvex Labs.

4. COMPENSATION
This role operates under a performance-driven reward model. No fixed salary is guaranteed. Bonuses, commissions, or equity may be offered at the Organization’s discretion.

5. TERMINATION
- Member may resign with 14 days’ written notice.
- Lunvex Labs may terminate immediately for breach of conduct, inactivity, or security violations.

6. COMMUNICATION
Official communication occurs via verified Lunvex Labs channels (e.g., Telegram, email). Professional conduct is mandatory.
"""

INTERNSHIP_AGREEMENT_PDF = """LUNVEX LABS – INTERNSHIP AGREEMENT

This Internship Agreement (“Agreement”) is entered into on [Date] by and between:
Lunvex Labs (“the Organization”) and [Full Name] (“the Intern”).

1. TERM
The internship lasts five (5) months from [Start Date] to [End Date]. Extension is at the Organization’s discretion.

2. PURPOSE
Provides hands-on experience in the selected Niche and Specialization under mentorship.

3. CONFIDENTIALITY
All non-public information received is Confidential Information and must not be disclosed.

4. COMPENSATION & RECOGNITION
- This is an unpaid educational internship.
- Successful completion yields an Official Certificate of Completion.
- Exceptional performers may be invited to join the Core Team.

5. TERMINATION
Lunvex Labs may terminate for misconduct, absenteeism, or breach. Intern may withdraw with 7 days’ notice.

6. COMMUNICATION
Official communication occurs via verified Lunvex Labs channels. Professionalism is required.
"""

# ---------------- Niches ----------------
NICHES = {
    "Web Development": [
        "Frontend Development",
        "Backend Development",
        "Full-Stack Development",
        "LAMP Stack (Linux, Apache, MySQL, PHP)",
        "MEAN Stack (MongoDB, Express, Angular, Node.js)",
        "MERN Stack (MongoDB, Express, React, Node.js)",
        "JAMstack (JavaScript, APIs, Markup)",
        "Serverless Web Architecture",
        "WordPress & CMS Development",
        "Custom Enterprise Web Solutions"
    ],
    "App Development": [
        "iOS Native Development (Swift/UIKit/SwiftUI)",
        "Android Native Development (Kotlin/Java)",
        "Cross-Platform (Flutter)",
        "Cross-Platform (React Native)",
        "Mobile Backend & API Integration",
        "Firebase-Powered Applications",
        "Progressive Web Apps (PWA)",
        "Enterprise Mobile Solutions"
    ],
    "Cybersecurity": [
        "Penetration Testing",
        "Security Operations Center (SOC) Analysis",
        "Digital Forensics & Incident Response",
        "Bug Bounty & Vulnerability Research",
        "Malware Analysis & Reverse Engineering",
        "Network & Infrastructure Security",
        "Threat Intelligence & Hunting",
        "Security Compliance & Auditing"
    ],
    "AI & ML": [
        "Machine Learning Engineering",
        "Data Science & Analytics",
        "Natural Language Processing (NLP)",
        "Computer Vision & Image AI",
        "AI-Powered Automation",
        "Chatbot & Conversational AI Development",
        "TensorFlow/PyTorch Model Deployment",
        "Generative AI Integration"
    ],
    "Web3 & Blockchain": [
        "Smart Contract Development (Solidity)",
        "Smart Contract Auditing",
        "DeFi Protocol Development",
        "NFT Platform & Marketplace Development",
        "Blockchain Infrastructure & Nodes",
        "Crypto Wallet & dApp Integration",
        "Layer 2 & Scalability Solutions (Polygon, etc.)",
        "On-Chain Analytics & Monitoring"
    ],
    "E-commerce": [
        "Shopify Store Development & Customization",
        "WooCommerce & WordPress E-commerce",
        "Amazon FBA & Marketplace Optimization",
        "Dropshipping Automation",
        "Payment Gateway Integration",
        "E-commerce SEO & Conversion Optimization",
        "Digital Advertising (Meta, Google Ads)",
        "E-commerce Analytics & CRO"
    ],
    "Graphic Design": [
        "UI/UX Design (Figma, Adobe XD)",
        "Brand Identity & Logo Design",
        "Marketing & Social Media Graphics",
        "3D Modeling & Product Visualization",
        "Motion Graphics (After Effects)",
        "Print & Packaging Design",
        "Illustration & Digital Art",
        "Design Systems & Component Libraries"
    ],
    "Marketing & SEO": [
        "Technical SEO & Site Audits",
        "Content Strategy & SEO Writing",
        "Google Ads & Performance Marketing",
        "Social Media Marketing (Organic & Paid)",
        "Email Marketing Automation",
        "Marketing Analytics & Attribution",
        "Conversion Rate Optimization (CRO)",
        "Brand Strategy & Positioning"
    ],
    "Video Editing": [
        "YouTube Content Editing",
        "Short-Form Video (TikTok, Reels, Shorts)",
        "Corporate & Explainer Videos",
        "Color Grading & Visual Effects",
        "Motion Graphics Integration",
        "Documentary & Narrative Editing",
        "DaVinci Resolve Color Workflow",
        "Premiere Pro & After Effects Pipeline"
    ]
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
            role TEXT NOT NULL CHECK(role IN ('Team', 'Internship')),
            niche TEXT NOT NULL,
            sector TEXT NOT NULL,
            socials TEXT NOT NULL,
            photo TEXT NOT NULL,
            signature TEXT NOT NULL,
            agreed BOOLEAN NOT NULL DEFAULT 0,
            status TEXT DEFAULT 'Pending'
        )
    """)
    conn.commit()
    conn.close()

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

# ---------------- Gorgeous HTML Template ----------------
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Lunvex Labs Application</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --primary: #0ea5e9;
            --primary-light: #bae6fd;
            --primary-gradient: linear-gradient(135deg, #0ea5e9, #38bdf8);
            --gray-50: #f8fafc;
            --gray-100: #f1f5f9;
            --gray-200: #e2e8f0;
            --gray-600: #475569;
            --gray-700: #334155;
            --gray-800: #1e293b;
            --gray-900: #0f172a;
            --border: #cbd5e1;
            --radius: 16px;
            --shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.06), 0 8px 10px -6px rgba(0, 0, 0, 0.05);
            --shadow-hover: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
            --transition: all 0.35s cubic-bezier(0.23, 1, 0.32, 1);
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
            color: var(--gray-800);
            min-height: 100vh;
            padding: 24px;
            display: flex;
            justify-content: center;
            align-items: flex-start;
        }

        .container {
            width: 100%;
            max-width: 800px;
            background: white;
            border-radius: var(--radius);
            box-shadow: var(--shadow);
            padding: 40px;
            margin-top: 32px;
            transition: var(--transition);
        }

        .container:hover {
            box-shadow: var(--shadow-hover);
            transform: translateY(-2px);
        }

        h1 {
            font-weight: 700;
            font-size: 28px;
            text-align: center;
            color: var(--gray-900);
            margin-bottom: 8px;
        }

        .subtitle {
            text-align: center;
            color: var(--gray-600);
            font-size: 15px;
            margin-bottom: 32px;
        }

        .logo {
            display: block;
            margin: 0 auto 24px;
            max-width: 140px;
            transition: transform 0.4s ease, filter 0.3s ease;
            filter: drop-shadow(0 2px 4px rgba(0,0,0,0.1));
        }

        .logo:hover {
            transform: scale(1.04) rotate(0.5deg);
        }

        .agreement-box {
            background: var(--gray-50);
            border: 1px solid var(--gray-200);
            border-radius: var(--radius);
            padding: 28px;
            margin-bottom: 36px;
            opacity: 0;
            transform: translateY(12px);
            animation: fadeInUp 0.7s ease forwards;
            position: relative;
        }

        .agreement-box::before {
            content: '';
            position: absolute;
            left: 0;
            top: 0;
            bottom: 0;
            width: 4px;
            background: var(--primary);
            border-radius: var(--radius) 0 0 var(--radius);
        }

        @keyframes fadeInUp {
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        .agreement-box h3 {
            font-size: 18px;
            font-weight: 700;
            color: var(--gray-900);
            margin-bottom: 16px;
        }

        .agreement-box p {
            margin-bottom: 16px;
            line-height: 1.6;
            color: var(--gray-700);
        }

        .agreement-box ol {
            padding-left: 24px;
            margin: 16px 0;
        }

        .agreement-box li {
            margin-bottom: 12px;
            line-height: 1.6;
            color: var(--gray-700);
        }

        label {
            display: block;
            margin-top: 20px;
            font-weight: 600;
            font-size: 14px;
            color: var(--gray-800);
        }

        input, select, button {
            width: 100%;
            padding: 14px 18px;
            margin-top: 8px;
            margin-bottom: 22px;
            border: 1px solid var(--border);
            border-radius: 12px;
            font-size: 15px;
            font-family: inherit;
            transition: var(--transition);
            background: white;
        }

        input:focus, select:focus {
            outline: none;
            border-color: var(--primary);
            box-shadow: 0 0 0 3px var(--primary-light);
            background: #f0f9ff;
        }

        input:hover, select:hover {
            border-color: var(--gray-600);
        }

        .checkbox-group {
            display: flex;
            align-items: flex-start;
            margin: 24px 0;
        }

        .checkbox-group input[type="checkbox"] {
            width: auto;
            margin-right: 14px;
            margin-top: 4px;
            accent-color: var(--primary);
            transform: scale(1.1);
        }

        button {
            background: var(--primary-gradient);
            color: white;
            font-weight: 600;
            font-size: 16px;
            border: none;
            border-radius: 12px;
            padding: 16px;
            cursor: pointer;
            transform: translateY(0);
            transition: var(--transition);
            letter-spacing: -0.01em;
            box-shadow: 0 4px 6px -1px rgba(14, 165, 233, 0.3);
        }

        button:hover {
            transform: translateY(-3px);
            box-shadow: 0 10px 15px -3px rgba(14, 165, 233, 0.4);
        }

        button:active {
            transform: translateY(0);
            box-shadow: 0 4px 6px -1px rgba(14, 165, 233, 0.3);
        }

        @media (max-width: 600px) {
            .container {
                padding: 28px 20px;
            }
            h1 {
                font-size: 24px;
            }
            input, select, button {
                padding: 14px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <img src="https://i.ibb.co/jktGByvB/grok-image-jw1wft.jpg" alt="Lunvex Labs" class="logo">
        <h1>Join Lunvex Labs</h1>
        <p class="subtitle">Apply as a Team Member or Intern</p>

        <div class="agreement-box" id="agreement-preview">
            <p>Please select a role to view the agreement.</p>
        </div>

        <form method="post" enctype="multipart/form-data">
            <label for="role">Role</label>
            <select name="role" id="role" required>
                <option value="">Select Role</option>
                <option value="Team">Team Member</option>
                <option value="Internship">Intern</option>
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

            <label for="socials">Social Links (LinkedIn, GitHub, Portfolio, etc.)</label>
            <input type="text" name="socials" id="socials" placeholder="https://linkedin.com/in/..., https://github.com/..." required>

            <label>Photo (JPEG/PNG)</label>
            <input type="file" name="photo" accept="image/jpeg,image/png" required>

            <label>Signature (JPEG/PNG)</label>
            <input type="file" name="signature" accept="image/jpeg,image/png" required>

            <div class="checkbox-group">
                <input type="checkbox" name="agreement" id="agreement" required>
                <label for="agreement" style="font-weight:500; color: var(--gray-800); margin-top: 2px;">
                    I have read and agree to the above agreement.
                </label>
            </div>

            <button type="submit">Submit Application</button>
        </form>
    </div>

    <script>
        const TEAM_AGREEMENT = {{ team_agreement | tojson }};
        const INTERNSHIP_AGREEMENT = {{ internship_agreement | tojson }};
        const agreementPreview = document.getElementById('agreement-preview');
        const roleSelect = document.getElementById('role');
        const nicheSelect = document.getElementById('niche');
        const sectorSelect = document.getElementById('sector');

        function updateAgreement() {
            const role = roleSelect.value;
            if (role === 'Team') {
                agreementPreview.innerHTML = TEAM_AGREEMENT;
            } else if (role === 'Internship') {
                agreementPreview.innerHTML = INTERNSHIP_AGREEMENT;
            } else {
                agreementPreview.innerHTML = '<p>Please select a role to view the agreement.</p>';
            }
            agreementPreview.style.animation = 'none';
            setTimeout(() => {
                agreementPreview.style.animation = 'fadeInUp 0.7s ease forwards';
            }, 10);
        }

        function updateSectors() {
            const selectedNiche = nicheSelect.value;
            sectorSelect.innerHTML = '<option value="">Select Specialization</option>';
            if (selectedNiche && {{ niches | tojson }}[selectedNiche]) {
                {{ niches | tojson }}[selectedNiche].forEach(sector => {
                    const option = document.createElement('option');
                    option.value = sector;
                    option.textContent = sector;
                    sectorSelect.appendChild(option);
                });
            }
        }

        roleSelect.addEventListener('change', updateAgreement);
        nicheSelect.addEventListener('change', updateSectors);

        updateAgreement();
        updateSectors();
    </script>
</body>
</html>
"""

# ---------------- Helpers ----------------
def save_uploaded_file(file, prefix):
    filename = file.filename.strip().replace(' ', '_').replace('..', '').replace('/', '')
    if not filename:
        filename = "unnamed"
    path = os.path.join(app.config["UPLOAD_FOLDER"], f"{prefix}_{int(time.time())}_{filename}")
    file.save(path)
    return path

def generate_pdf(data, photo_path, signature_path):
    pdf_filename = f"{data['name'].replace(' ', '_')}_{int(time.time())}.pdf"
    pdf_path = os.path.join(PDF_FOLDER, pdf_filename)
    c = canvas.Canvas(pdf_path, pagesize=A4)
    width, height = A4

    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 50, "Lunvex Labs – Application Record")

    y = height - 90
    c.setFont("Helvetica", 12)
    fields = [
        ("Name", data["name"]),
        ("Email", data["email"]),
        ("Role", data["role"]),
        ("Niche", data["niche"]),
        ("Specialization", data["sector"]),
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

    agreement_text = TEAM_AGREEMENT_PDF if data["role"] == "Team" else INTERNSHIP_AGREEMENT_PDF
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

# ---------------- Routes ----------------
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        try:
            name = request.form.get("name", "").strip()
            email = request.form.get("email", "").strip()
            role = request.form.get("role")
            niche = request.form.get("niche")
            sector = request.form.get("sector")
            socials = request.form.get("socials", "").strip()
            agreed = request.form.get("agreement") == "on"

            if not all([name, email, role, niche, sector, socials]):
                return "<h2 style='text-align:center;color:#ef4444;margin:40px;'>❌ All fields are required.</h2>", 400

            if role not in ["Team", "Internship"]:
                return "<h2 style='text-align:center;color:#ef4444;margin:40px;'>❌ Invalid role.</h2>", 400

            if niche not in NICHES or sector not in NICHES[niche]:
                return "<h2 style='text-align:center;color:#ef4444;margin:40px;'>❌ Invalid niche or specialization.</h2>", 400

            if not agreed:
                return "<h2 style='text-align:center;color:#ef4444;margin:40px;'>❌ You must agree to the agreement.</h2>", 400

            photo = request.files.get("photo")
            signature = request.files.get("signature")
            if not photo or not signature:
                return "<h2 style='text-align:center;color:#ef4444;margin:40px;'>❌ Photo and signature are required.</h2>", 400

            if not photo.filename or not signature.filename:
                return "<h2 style='text-align:center;color:#ef4444;margin:40px;'>❌ Please upload valid image files.</h2>", 400

            photo_path = save_uploaded_file(photo, "photo")
            signature_path = save_uploaded_file(signature, "signature")

            with get_db_connection() as conn:
                conn.execute(
                    """INSERT INTO applicants 
                    (name, email, role, niche, sector, socials, photo, signature, agreed)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (name, email, role, niche, sector, socials, photo_path, signature_path, True)
                )
                conn.commit()

            pdf_path = generate_pdf({
                "name": name,
                "email": email,
                "role": role,
                "niche": niche,
                "sector": sector,
                "socials": socials
            }, photo_path, signature_path)

            dropbox_path = f"/LunvexLabs/{os.path.basename(pdf_path)}"
            with open(pdf_path, "rb") as f:
                dbx.files_upload(f.read(), dropbox_path, mode=dropbox.files.WriteMode.overwrite)

            return """
            <div style="max-width:600px;margin:60px auto;text-align:center;font-family:'Inter',sans-serif;color:#0f172a;">
                <h2 style="color:#0ea5e9;font-weight:700;">✅ Application Submitted</h2>
                <p style="font-size:16px;margin-top:12px;">Your application and signed agreement have been securely stored.</p>
                <p>Thank you for your interest in Lunvex Labs.</p>
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
