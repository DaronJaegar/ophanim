"""Demo data for the clinic's Drive and Gmail (Bruce, Module A).

python -m sensors.demo_files      ->  demo_files/  (git-ignored)
  Patient records/    8 fake patient notes (made-up names) to upload as the "Patient records" folder
  Invoices/           3 fake vendor invoices to upload to Drive
  Netbanking login    decoy doc with the decoy-doc honeytoken link
  decoy_email.txt     text for the decoy email with the decoy-email link

Every file is marked DEMO DATA. Re-run on event day after BRAIN_URL changes to the hotspot IP,
because the honeytoken links point at the brain.
"""
import html, os, shutil, subprocess, tempfile
from common.config import BRAIN_URL, CLINIC_NAME
from sensors.honeytoken import TOKENS

OUT = "demo_files"
CHROME = [r"C:\Program Files\Google\Chrome\Application\chrome.exe",
          r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
          "google-chrome", "chromium", "chromium-browser"]

PATIENTS = [  # made-up people only
    ("Ravi Menon", 54, "Type 2 diabetes review", "HbA1c 7.4%. Continue metformin 500 mg twice daily. Recheck in 3 months."),
    ("Lakshmi Iyer", 38, "Migraine follow-up", "Two episodes this month. Continue sumatriptan as needed. Sleep diary advised."),
    ("Arjun Shetty", 29, "Sports injury, right ankle", "Grade 1 sprain. RICE, ankle brace for 2 weeks. Physio referral given."),
    ("Fatima Khan", 61, "Hypertension", "BP 142/88. Amlodipine 5 mg daily continued. Reduce salt. Review in 6 weeks."),
    ("Deepak Rao", 45, "Annual health check", "All bloods normal. Mild vitamin D deficiency; supplement for 8 weeks."),
    ("Meera Pillai", 33, "Antenatal visit, 20 weeks", "Scan normal. Iron and folic acid continued. Next visit in 4 weeks."),
    ("Suresh Gowda", 67, "COPD review", "Stable. Inhaler technique checked. Pneumococcal vaccine due."),
    ("Ananya Das", 12, "Asthma, child", "Mild intermittent. Salbutamol inhaler with spacer. School action plan given."),
]
INVOICES = [  # fictional vendors
    ("INV-2026-1041", "Nimbus Pharma Distributors", [("Paracetamol 500 mg, 10 x 100", 4, 620), ("Amoxicillin 250 mg, 10 x 50", 2, 1450)]),
    ("INV-2026-1042", "Kaveri Lab Reagents", [("HbA1c test kits, box of 50", 1, 8200), ("Glucose strips, box of 100", 3, 1150)]),
    ("INV-2026-1043", "BrightCare Medical Supplies", [("Nitrile gloves, box of 100", 10, 380), ("Disposable syringes 5 ml, 100", 5, 540)]),
]
STYLE = ("body{font-family:Arial,sans-serif;margin:40px;color:#222} h1{font-size:22px;margin:0}"
         " .demo{color:#b00;font-weight:bold;border:2px solid #b00;padding:4px 8px;display:inline-block;margin:10px 0}"
         " table{border-collapse:collapse;width:100%;margin-top:16px} td,th{border:1px solid #999;padding:6px;text-align:left}"
         " .r{text-align:right}")
DEMO = "DEMO DATA - fictional, for the Chakravyuh security demo only"

def _page(title, body):
    return (f"<!doctype html><html><head><meta charset='utf-8'><title>{html.escape(title)}</title>"
            f"<style>{STYLE}</style></head><body><div class='demo'>{DEMO}</div>{body}</body></html>")

def _pdf(page, path, browser):
    """Print an HTML page to PDF with headless Chrome/Edge; fall back to the .html file."""
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as f:
        f.write(page)
    try:
        if browser:
            subprocess.run([browser, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                            f"--print-to-pdf={os.path.abspath(path)}", "file:///" + f.name.replace("\\", "/")],
                           capture_output=True, timeout=60)
        if not os.path.exists(path):
            shutil.copy(f.name, path[:-4] + ".html")
    finally:
        os.remove(f.name)

def main():
    browser = next((b for b in CHROME if shutil.which(b) or os.path.exists(b)), None)
    shutil.rmtree(OUT, ignore_errors=True)
    for d in ("Patient records", "Invoices"):
        os.makedirs(os.path.join(OUT, d))
    for i, (name, age, reason, plan) in enumerate(PATIENTS, 1):
        body = (f"<h1>{CLINIC_NAME} - Consultation note</h1><p><b>Patient:</b> {name} &nbsp; <b>Age:</b> {age}"
                f" &nbsp; <b>ID:</b> SC-{1000 + i}</p><p><b>Reason:</b> {reason}</p><p><b>Plan:</b> {plan}</p>"
                f"<p><b>Doctor:</b> Dr. A. Kulkarni</p>")
        _pdf(_page(name, body), os.path.join(OUT, "Patient records", f"SC-{1000 + i} {name}.pdf"), browser)
    for num, vendor, items in INVOICES:
        rows = "".join(f"<tr><td>{d}</td><td class='r'>{q}</td><td class='r'>{p:,}</td><td class='r'>{q * p:,}</td></tr>"
                       for d, q, p in items)
        sub = sum(q * p for _, q, p in items)
        body = (f"<h1>Tax invoice {num}</h1><p><b>From:</b> {vendor}<br><b>To:</b> {CLINIC_NAME}</p>"
                f"<table><tr><th>Item</th><th class='r'>Qty</th><th class='r'>Rate (Rs)</th><th class='r'>Amount (Rs)</th></tr>{rows}"
                f"<tr><td colspan=3><b>Total incl. 12% GST</b></td><td class='r'><b>{round(sub * 1.12):,}</b></td></tr></table>"
                f"<p>Payment within 15 days to the bank account on file.</p>")
        _pdf(_page(num, body), os.path.join(OUT, "Invoices", f"Invoice {num} {vendor}.pdf"), browser)
    by_place = {where: tok for tok, where in TOKENS.items()}
    if "decoy-doc" in by_place:
        link = f"{BRAIN_URL}/t/{by_place['decoy-doc']}"
        body = (f"<h1>Netbanking login</h1><p>Clinic current account - login page:</p><p><a href='{link}'>{link}</a></p>"
                "<p>User ID and password are with Dr. Kulkarni.</p>")
        _pdf(_page("Netbanking login", body), os.path.join(OUT, "Netbanking login.pdf"), browser)
    if "decoy-email" in by_place:
        with open(os.path.join(OUT, "decoy_email.txt"), "w", encoding="utf-8") as f:
            f.write("Subject: Netbanking - new login link\n\n"
                    "Hi, the bank changed the netbanking page. Use this link from now on:\n"
                    f"{BRAIN_URL}/t/{by_place['decoy-email']}\n\n({DEMO})\n")
    print("Wrote", OUT, "with", "PDFs" if browser else "HTML files (no Chrome/Edge found)")

if __name__ == "__main__":
    main()
