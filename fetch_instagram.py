"""Instagram (Instagram Login API) verisini çekip data.json'a yazar. Sadece standart kütüphane kullanır."""
import json, os, urllib.parse, urllib.request, urllib.error
from datetime import datetime, timezone

API = "https://graph.instagram.com"
TOKEN = os.environ["IG_TOKEN"]


def get(path, **p):
    p["access_token"] = TOKEN
    url = f"{API}/{path}?{urllib.parse.urlencode(p)}"
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        raise RuntimeError(e.read().decode()[:300])


def val(m):
    if m.get("values"):
        return m["values"][0].get("value", 0)
    return m.get("total_value", {}).get("value", 0)


METRICS = ["views", "reach", "saved", "shares", "total_interactions", "ig_reels_avg_watch_time"]


def insights(mid):
    out = {}
    try:
        for m in get(f"{mid}/insights", metric=",".join(METRICS))["data"]:
            out[m["name"]] = val(m)
    except RuntimeError:
        for k in METRICS:  # biri hata verirse diğerlerini tek tek dene
            try:
                out[k] = val(get(f"{mid}/insights", metric=k)["data"][0])
            except RuntimeError:
                pass
    return out


def parse(ts):
    return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S%z")


now = datetime.now(timezone.utc)
try:
    old = json.load(open("data.json", encoding="utf-8"))
except Exception:
    old = {}

me = get("me", fields="username,followers_count,media_count")
followers = old.get("followers", [])
followers.append({"d": now.isoformat(), "n": me.get("followers_count", 0)})
followers = followers[-800:]

BASIC = "id,timestamp,media_type,media_product_type,like_count,comments_count,permalink"
try:
    items = get("me/media", fields=BASIC + ",view_count", limit=50)["data"]
except RuntimeError:
    items = get("me/media", fields=BASIC, limit=50)["data"]

prev = {v["id"]: v for v in old.get("videos", [])}
videos = []
for it in items:
    if it.get("media_type") != "VIDEO" and it.get("media_product_type") != "REELS":
        continue
    ins = insights(it["id"])
    t = parse(it["timestamp"])
    views = ins.get("views", it.get("view_count", 0))
    v = {
        "id": it["id"],
        "t": t.isoformat(),
        "url": it.get("permalink", ""),
        "views": views,
        "likes": it.get("like_count", 0),
        "comments": it.get("comments_count", 0),
        "saves": ins.get("saved", 0),
        "shares": ins.get("shares", 0),
        "reach": ins.get("reach", 0),
        "avgWatch": round(ins.get("ig_reels_avg_watch_time", 0) / 1000, 1),
    }
    age = (now - t).total_seconds() / 3600
    snaps = prev.get(it["id"], {}).get("snaps", [])
    if age <= 72:  # ilk 72 saatte her çalışmada anlık görüntü al
        snaps.append([round(age, 2), views, v["likes"]])
    v["snaps"] = snaps
    videos.append(v)

json.dump(
    {"username": me.get("username"), "updated": now.isoformat(), "followers": followers, "videos": videos},
    open("data.json", "w", encoding="utf-8"),
    ensure_ascii=False,
)
print("tamam:", len(videos), "video,", followers[-1]["n"], "takipçi")
