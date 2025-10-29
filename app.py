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
    raise EnvironmentError(
        "Missing DROPBOX_TOKEN environment variable. "
        "Generate a token in your Dropbox App Console under 'Settings > Generated access token'."
    )

UPLOAD_FOLDER = "uploads"
PDF_FOLDER = "pdfs"
DATABASE = "lunvex.db"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PDF_FOLDER, exist_ok=True)

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Initialize Dropbox client with minimal scope (files.content.write)
dbx = dropbox.Dropbox(DROPBOX_TOKEN)

# ---------------- Niches: Role & Stack-Based ----------------
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
            status TEXT DEFAULT 'Pending'
        )
    """)
    conn.commit()
    conn.close()

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

# ---------------- HTML Template ----------------
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Lunvex Labs Application</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background-color: #f8fafc;
            color: #1e293b;
            margin: 0;
            padding: 0;
        }
        .container {
            max-width: 600px;
            margin: 40px auto;
            padding: 30px;
            background: white;
            border-radius: 12px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        }
        h1 {
            text-align: center;
            margin-bottom: 30px;
            color: #0f172a;
            font-weight: 600;
        }
        .logo {
            display: block;
            margin: 0 auto 20px;
            max-width: 150px;
            height: auto;
        }
        label {
            display: block;
            margin-top: 16px;
            font-weight: 600;
            font-size: 14px;
            color: #334155;
        }
        input, select, button {
            width: 100%;
            padding: 12px;
            margin-top: 6px;
            margin-bottom: 16px;
            border: 1px solid #cbd5e1;
            border-radius: 8px;
            box-sizing: border-box;
            font-size: 15px;
        }
        input:focus, select:focus {
            outline: none;
            border-color: #3b82f6;
            box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.15);
        }
        button {
            background-color: #0ea5e9;
            color: white;
            font-weight: 600;
            cursor: pointer;
            transition: background-color 0.2s;
        }
        button:hover {
            background-color: #0284c7;
        }
    </style>
</head>
<body>
    <div class="container">
        <img src="https://i.ibb.co/jktGByvB/grok-image-jw1wft.jpg" alt="Lunvex Labs" class="logo">
        <h1>Lunvex Labs Application</h1>
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

            <button type="submit">Submit Application</button>
        </form>
    </div>

    <script>
        document.addEventListener('DOMContentLoaded', () => {
            const niches = {{ niches | tojson }};
            const nicheSelect = document.getElementById('niche');
            const sectorSelect = document.getElementById('sector');

            function updateSectors() {
                const selectedNiche = nicheSelect.value;
                sectorSelect.innerHTML = '<option value="">Select Specialization</option>';
                if (selectedNiche && niches[selectedNiche]) {
                    niches[selectedNiche].forEach(sector => {
                        const option = document.createElement('option');
                        option.value = sector;
                        option.textContent = sector;
                        sectorSelect.appendChild(option);
                    });
                }
            }

            nicheSelect.addEventListener('change', updateSectors);
            updateSectors();
        });
    </script>
</body>
</html>
"""

# ---------------- Helpers ----------------
def save_uploaded_file(file, prefix):
    # Basic sanitization
    filename = file.filename.replace(' ', '_').replace('..', '').replace('/', '')
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

            if not all([name, email, role, niche, sector, socials]):
                return "<h2 style='text-align:center;color:#ef4444;'>All fields are required.</h2>", 400

            if niche not in NICHES or sector not in NICHES[niche]:
                return "<h2 style='text-align:center;color:#ef4444;'>Invalid niche or specialization.</h2>", 400

            photo = request.files.get("photo")
            signature = request.files.get("signature")
            if not photo or not signature:
                return "<h2 style='text-align:center;color:#ef4444;'>Photo and signature are required.</h2>", 400

            photo_path = save_uploaded_file(photo, "photo")
            signature_path = save_uploaded_file(signature, "signature")

            with get_db_connection() as conn:
                conn.execute(
                    """INSERT INTO applicants 
                    (name, email, role, niche, sector, socials, photo, signature)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (name, email, role, niche, sector, socials, photo_path, signature_path)
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
            <div style="max-width:600px;margin:60px auto;text-align:center;font-family:sans-serif;color:#0f172a;">
                <h2 style="color:#0ea5e9;">✅ Application Submitted</h2>
                <p>Your application has been received and securely stored.</p>
                <p>Thank you for your interest in Lunvex Labs.</p>
            </div>
            """

        except Exception as e:
            app.logger.error(f"Submission error: {e}")
            return """
            <div style="max-width:600px;margin:60px auto;text-align:center;font-family:sans-serif;color:#ef4444;">
                <h2>❌ Submission Failed</h2>
                <p>An unexpected error occurred. Please try again or contact support.</p>
            </div>
            """, 500

    return render_template_string(HTML_TEMPLATE, niches=NICHES)

# ---------------- Run ----------------
if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000)
