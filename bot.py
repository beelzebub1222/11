import os
import dns.resolver
import requests
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# ================= CONFIG =================
BOT_TOKEN = os.getenv("8713108517:AAEJy91OXF6EogSH1fdevYGmZ3go-W4UMJc")
THREADS = int(os.getenv("THREADS", "10"))
TIMEOUT = 5

# ================= FINGERPRINT =================
FINGERPRINTS = {
    "AWS S3": {
        "cnames": ["amazonaws.com"],
        "signatures": ["NoSuchBucket"]
    },
    "GitHub Pages": {
        "cnames": ["github.io"],
        "signatures": ["There isn't a GitHub Pages site here"]
    },
    "Heroku": {
        "cnames": ["herokuapp.com"],
        "signatures": ["no such app"]
    },
    "Vercel": {
        "cnames": ["vercel.app"],
        "signatures": ["404: This page could not be found"]
    },
    "Netlify": {
        "cnames": ["netlify.app"],
        "signatures": ["not found"]
    }
}

# ================= SCANNER =================
class Scanner:
    def __init__(self):
        self.lock = threading.Lock()
        self.vuln = 0

    def get_cname(self, domain):
        try:
            return str(dns.resolver.resolve(domain, "CNAME")[0].target).rstrip(".")
        except:
            return None

    def detect(self, cname):
        if not cname:
            return None
        for service, data in FINGERPRINTS.items():
            for c in data["cnames"]:
                if c in cname.lower():
                    return service
        return None

    def check(self, domain, service):
        try:
            r = requests.get(f"https://{domain}", timeout=TIMEOUT)
            for sig in FINGERPRINTS[service]["signatures"]:
                if sig.lower() in r.text.lower():
                    return True
        except:
            pass
        return False

    def scan(self, domain):
        cname = self.get_cname(domain)

        if not cname:
            return f"❌ {domain} (No CNAME)"

        service = self.detect(cname)

        if not service:
            return f"⚪ {domain} → {cname} (Unknown)"

        if self.check(domain, service):
            with self.lock:
                self.vuln += 1
            return f"🔥 {domain} → {service} TAKEOVER!"

        return f"✅ {domain} → {service}"


scanner = Scanner()

# ================= COMMAND =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Takeover Scanner Bot (Railway)\n\n"
        "/scan domain.com\n"
        "Upload .txt untuk mass scan"
    )

async def scan_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ /scan domain.com")
        return

    domain = context.args[0].lower()
    res = scanner.scan(domain)
    await update.message.reply_text(res)

# ================= FILE =================
async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document

    if not doc.file_name.endswith(".txt"):
        await update.message.reply_text("❌ File harus .txt")
        return

    file = await doc.get_file()
    await file.download_to_drive("domains.txt")

    await update.message.reply_text("📂 Scanning file...")

    with open("domains.txt") as f:
        domains = list(set(
            d.strip().lower()
            for d in f
            if d.strip() and not d.startswith("#")
        ))

    results = []
    vuln = []

    with ThreadPoolExecutor(max_workers=THREADS) as executor:
        futures = [executor.submit(scanner.scan, d) for d in domains]

        for future in as_completed(futures):
            r = future.result()
            results.append(r)
            if "🔥" in r:
                vuln.append(r)

    msg = f"✅ Done\nTotal: {len(domains)}\n🔥 Vuln: {len(vuln)}\n\n"

    if vuln:
        msg += "\n".join(vuln[:20])

    await update.message.reply_text(msg)

# ================= MAIN =================
def main():
    if not BOT_TOKEN:'8713108517:AAEJy91OXF6EogSH1fdevYGmZ3go-W4UMJc'
        print("❌ BOT_TOKEN belum di set")
        return

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("scan", scan_cmd))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_file))

    print("🤖 Bot running...")

    while True:
        try:
            app.run_polling()
        except Exception as e:
            print("Restarting...", e)

if __name__ == "__main__":
    main()
