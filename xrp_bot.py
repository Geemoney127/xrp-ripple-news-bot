import requests, feedparser, json, os

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]
CRYPTOPANIC_KEY = os.environ.get("CRYPTOPANIC_KEY", "")

PRICE_MOVE_ALERT = 3.0
RSS_FEEDS = [
    "https://news.google.com/rss/search?q=XRP+OR+Ripple&hl=en-US&gl=US&ceid=US:en",
    "https://cointelegraph.com/rss/tag/ripple",
    "https://cryptoslate.com/feed/",
]
KEYWORDS = ["xrp", "ripple"]
STATE_FILE = "state.json"

def load_state():
    try:
        with open(STATE_FILE) as f:
            s = json.load(f)
            return set(s["seen"]), s.get("last_price")
    except FileNotFoundError:
        return set(), None

def save_state(seen, last_price):
    # keep the seen list from growing forever
    trimmed = list(seen)[-500:]
    with open(STATE_FILE, "w") as f:
        json.dump({"seen": trimmed, "last_price": last_price}, f)

def send(msg):
    requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        params={"chat_id": CHAT_ID, "text": msg})

def get_cryptopanic():
    if not CRYPTOPANIC_KEY:
        return []
    r = requests.get("https://cryptopanic.com/api/v1/posts/",
        params={"auth_token": CRYPTOPANIC_KEY, "currencies": "XRP"}, timeout=15)
    return [(str(p["id"]), p["title"], p["url"]) for p in r.json().get("results", [])]

def get_rss():
    items = []
    for url in RSS_FEEDS:
        for e in feedparser.parse(url).entries:
            text = (e.get("title", "") + e.get("summary", "")).lower()
            if any(k in text for k in KEYWORDS):
                items.append((e.get("id", e.link), e.title, e.link))
    return items

def get_price():
    r = requests.get("https://api.coingecko.com/api/v3/simple/price",
        params={"ids": "ripple", "vs_currencies": "usd"}, timeout=15)
    return r.json()["ripple"]["usd"]

seen, last_price = load_state()

for pid, title, url in get_cryptopanic() + get_rss():
    if pid not in seen:
        seen.add(pid)
        send(f"📰 {title}\n{url}")

try:
    price = get_price()
    if last_price is None:
        send(f"💲 XRP price: ${price:.4f}")
    elif abs(price - last_price) / last_price * 100 >= PRICE_MOVE_ALERT:
        arrow = "📈" if price > last_price else "📉"
        send(f"{arrow} XRP moved to ${price:.4f} (was ${last_price:.4f})")
    last_price = price
except Exception as e:
    print("price error:", e)

save_state(seen, last_price)