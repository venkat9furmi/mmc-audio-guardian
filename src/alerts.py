# src/alerts.py
import datetime as dt
import requests

def send_console(feed, title, text, severity="info"):
    print(f"[ALERT][{severity.upper()}][{feed}] {title} – {text}")

def send_teams(webhook_url, feed, title, text, severity="info"):
    if not webhook_url:
        return
    card = {
        "@type": "MessageCard",
        "@context": "http://schema.org/extensions",
        "summary": title,
        "themeColor": {"info":"0078D4","warn":"FFA500","error":"D13438"}.get(severity,"0078D4"),
        "title": f"{feed}: {title}",
        "sections": [{
            "facts": [{"name":"Time","value": dt.datetime.utcnow().isoformat() + "Z"}],
            "text": text
        }]
    }
    try:
        r = requests.post(webhook_url, json=card, timeout=10)
        print(f"[Webhook] HTTP {r.status_code}")
    except Exception as e:
        print(f"[Webhook] post failed: {e}")
