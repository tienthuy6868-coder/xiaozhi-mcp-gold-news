from mcp.server.fastmcp import FastMCP
import sys
import re
import html
import urllib.request
import json
import xml.etree.ElementTree as ET

if sys.platform == "win32":
    sys.stderr.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")

mcp = FastMCP("GoldAndNews")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json, application/xml, text/xml, */*",
}


def _http_get(url: str, timeout: int = 10) -> str:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def _clean_html(text: str) -> str:
    if not text:
        return ""
    text = html.unescape(text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


@mcp.tool()
def get_gold_price() -> dict:
    """
    Lấy giá vàng mới nhất tại Việt Nam (vàng miếng SJC 999.9, nhẫn trơn 999.9, vàng 24K, 18K)
    và giá vàng thế giới (XAU/USD).
    Dùng tool này khi người dùng hỏi: giá vàng, giá vàng hôm nay, vàng SJC, vàng nhẫn 9999, giá vàng thế giới.
    """
    result = {"success": False, "vietnam_gold": [], "world_gold": None}

    try:
        pnj_raw = _http_get("https://edge-api.pnj.io/ecom-frontend/v1/get-gold-price?zone=11")
        pnj_data = json.loads(pnj_raw)
        result["update_date"] = pnj_data.get("updateDate", "")
        target_codes = {"SJC", "N24K", "KB", "24K", "18K"}
        for item in pnj_data.get("data", []):
            code = item.get("masp")
            if code in target_codes:
                buy = item.get("giamua")
                sell = item.get("giaban")
                result["vietnam_gold"].append({
                    "code": code,
                    "name": item.get("tensp", ""),
                    "buy_trieu_luong": round(buy * 0.01, 2) if isinstance(buy, (int, float)) else None,
                    "sell_trieu_luong": round(sell * 0.01, 2) if isinstance(sell, (int, float)) else None,
                })
        if result["vietnam_gold"]:
            result["success"] = True
    except Exception as e:
        result["vietnam_error"] = str(e)

    try:
        world_raw = _http_get("https://api.gold-api.com/price/XAU")
        world_data = json.loads(world_raw)
        if "price" in world_data:
            result["world_gold"] = {
                "price_usd_per_oz": round(float(world_data["price"]), 2),
                "updated_at": world_data.get("updatedAt", ""),
            }
            result["success"] = True
    except Exception as e:
        result["world_error"] = str(e)

    return result


@mcp.tool()
def get_thoi_su_noi_bat(scope: str = "both", limit: int = 5) -> dict:
    """
    Lấy tin tức thời sự nổi bật mới nhất trong nước (Việt Nam) và/hoặc quốc tế (thế giới) từ RSS VnExpress.
    Args:
        scope: 'domestic' (trong nước), 'international' (quốc tế), hoặc 'both' (cả hai, mặc định).
        limit: Số lượng tin mỗi mục (mặc định 5, tối đa 8).
    """
    limit = max(1, min(int(limit), 8))
    scope_norm = (scope or "both").strip().lower()

    feeds = []
    if scope_norm in ("domestic", "trong_nuoc", "both"):
        feeds.append(("domestic_news", "https://vnexpress.net/rss/thoi-su.rss"))
    if scope_norm in ("international", "quoc_te", "world", "both"):
        feeds.append(("international_news", "https://vnexpress.net/rss/the-gioi.rss"))
    if not feeds:
        feeds = [
            ("domestic_news", "https://vnexpress.net/rss/thoi-su.rss"),
            ("international_news", "https://vnexpress.net/rss/the-gioi.rss"),
        ]

    output = {"success": False}
    for key, url in feeds:
        items_list = []
        try:
            xml_text = _http_get(url, timeout=10)
            root = ET.fromstring(xml_text)
            for item in root.findall("./channel/item")[:limit]:
                title = _clean_html(item.findtext("title") or "")
                desc = _clean_html(item.findtext("description") or "")
                pub_date = (item.findtext("pubDate") or "").strip()
                if len(desc) > 220:
                    desc = desc[:220].rstrip() + "..."
                if title:
                    items_list.append({
                        "title": title,
                        "summary": desc,
                        "published_at": pub_date,
                    })
            if items_list:
                output["success"] = True
        except Exception as e:
            output[f"{key}_error"] = str(e)
        output[key] = items_list

    return output


if __name__ == "__main__":
    mcp.run(transport="stdio")
