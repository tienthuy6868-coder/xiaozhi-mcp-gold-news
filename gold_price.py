from mcp.server.fastmcp import FastMCP
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
import sys
import re
import gzip
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
    "Accept": "text/html, application/json, application/xml, text/xml, */*",
}

NEWS_FEEDS = {
    "domestic": [
        ("VnExpress", "vnexpress", "https://vnexpress.net/rss/thoi-su.rss"),
        ("Tuổi Trẻ", "tuoitre", "https://tuoitre.vn/rss/thoi-su.rss"),
        ("Thanh Niên", "thanhnien", "https://thanhnien.vn/rss/thoi-su.rss"),
        ("Dân Trí", "dantri", "https://dantri.com.vn/rss/su-kien.rss"),
        ("VietnamNet", "vietnamnet", "https://vietnamnet.vn/rss/thoi-su.rss"),
        ("Người Lao Động", "nld", "https://nld.com.vn/rss/thoi-su.rss"),
        ("VTC News", "vtcnews", "https://vtcnews.vn/rss/thoi-su.rss"),
        ("Giáo dục & Thời đại", "giaoducthoidai", "https://giaoducthoidai.vn/rss/thoi-su.rss"),
        ("Nhân Dân", "nhandan", "https://nhandan.vn/rss/home.rss"),
        ("Báo Chính phủ", "baochinhphu", "https://baochinhphu.vn/home.rss"),
        ("VTV", "vtv", "https://vtv.vn/rss/trong-nuoc.rss"),
        ("VietnamPlus", "vietnamplus", "https://www.vietnamplus.vn/rss/home.rss"),
        ("Báo Hải Phòng", "baohaiphong", "https://baohaiphong.vn/"),
        ("Công an nhân dân", "cand", "https://cand.com.vn/rss/thoi-su.rss"),
        ("Tiền Phong", "tienphong", "https://tienphong.vn/rss/thoi-su-12.rss"),
    ],
    "international": [
        ("VnExpress", "vnexpress", "https://vnexpress.net/rss/the-gioi.rss"),
        ("Tuổi Trẻ", "tuoitre", "https://tuoitre.vn/rss/the-gioi.rss"),
        ("Thanh Niên", "thanhnien", "https://thanhnien.vn/rss/the-gioi.rss"),
        ("Dân Trí", "dantri", "https://dantri.com.vn/rss/the-gioi.rss"),
        ("VietnamNet", "vietnamnet", "https://vietnamnet.vn/rss/the-gioi.rss"),
        ("Người Lao Động", "nld", "https://nld.com.vn/rss/quoc-te.rss"),
        ("VTC News", "vtcnews", "https://vtcnews.vn/rss/the-gioi.rss"),
        ("BBC Tiếng Việt", "bbc", "https://feeds.bbci.co.uk/vietnamese/rss.xml"),
        ("Nhân Dân", "nhandan", "https://nhandan.vn/rss/the-gioi-1231.rss"),
        ("VTV", "vtv", "https://vtv.vn/rss/the-gioi.rss"),
        ("VietnamPlus", "vietnamplus", "https://www.vietnamplus.vn/rss/thegioi.rss"),
        ("Công an nhân dân", "cand", "https://cand.com.vn/rss/the-gioi.rss"),
        ("Tiền Phong", "tienphong", "https://tienphong.vn/rss/the-gioi-5.rss"),
    ],
    "tech": [
        ("Tinh tế", "tinhte", "https://tinhte.vn/rss"),
        ("Quản trị mạng", "quantrimang", "https://quantrimang.com/"),
    ],
    "sports": [
        ("VnExpress Thể Thao", "vnexpress", "https://vnexpress.net/rss/the-thao.rss"),
        ("Thể thao 247", "thethao247", "https://thethao247.vn/trang-chu.rss"),
        ("Tuổi Trẻ Thể Thao", "tuoitre", "https://tuoitre.vn/rss/the-thao.rss"),
        ("Thanh Niên Thể Thao", "thanhnien", "https://thanhnien.vn/rss/the-thao.rss"),
    ],
}


def _http_get(url: str, timeout: int = 10) -> str:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
        if resp.headers.get("Content-Encoding") == "gzip" or raw[:2] == b"\x1f\x8b":
            raw = gzip.decompress(raw)
        return raw.decode("utf-8", errors="replace")


def _clean_html(text: str) -> str:
    if not text:
        return ""
    text = html.unescape(text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _fetch_single_feed(source_name: str, url: str, per_feed_limit: int) -> list[dict]:
    items_list = []
    try:
        body = _http_get(url, timeout=10)
        if "quantrimang.com" in url or "baohaiphong.vn" in url:
            soup = BeautifulSoup(body, "html.parser")
            seen_urls = set()
            base_domain = "https://quantrimang.com" if "quantrimang.com" in url else "https://baohaiphong.vn"
            pattern = r"-\d{5,}$" if "quantrimang.com" in url else r"-\d{5,}\.html$"
            for a in soup.find_all("a", href=True):
                href = a.get("href", "")
                title = a.get_text(" ", strip=True)
                if len(title) > 25 and re.search(pattern, href):
                    full_url = href if href.startswith("http") else f"{base_domain}{href}"
                    if full_url not in seen_urls:
                        seen_urls.add(full_url)
                        items_list.append({
                            "source": source_name,
                            "title": title,
                            "summary": "",
                            "url": full_url,
                            "published_at": "",
                        })
                        if len(items_list) >= per_feed_limit:
                            break
            return items_list

        root = ET.fromstring(body)
        for item in root.findall("./channel/item")[:per_feed_limit]:
            title = _clean_html(item.findtext("title") or "")
            desc = _clean_html(item.findtext("description") or "")
            link = (item.findtext("link") or "").strip()
            pub_date = (item.findtext("pubDate") or "").strip()
            if len(desc) > 220:
                desc = desc[:220].rstrip() + "..."
            if title and link:
                items_list.append({
                    "source": source_name,
                    "title": title,
                    "summary": desc,
                    "url": link,
                    "published_at": pub_date,
                })
    except Exception:
        pass
    return items_list


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
def get_thoi_su_noi_bat(scope: str = "both", source: str = "all", limit: int = 8) -> dict:
    """
    Lấy tin tức thời sự, quốc tế, công nghệ và thể thao mới nhất từ các đầu báo lớn:
    VnExpress, Tuổi Trẻ, Thanh Niên, Dân Trí, VietnamNet, Người Lao Động, VTC News,
    Giáo dục & Thời đại, Nhân Dân, Báo Chính phủ, VTV, VietnamPlus, Báo Hải Phòng,
    Công an nhân dân, Tiền Phong, BBC Tiếng Việt, Tinh tế, Quản trị mạng, Thể thao 247.
    Mỗi tin đều có sẵn `url` để người dùng có thể yêu cầu đọc nội dung đầy đủ bằng `get_full_article`.
    Args:
        scope: 'domestic' (trong nước), 'international' (quốc tế), 'tech' (công nghệ), 'sports' (thể thao), 'both' (trong nước & quốc tế, mặc định), hoặc 'all' (tất cả).
        source: 'all' (tổng hợp nhiều báo, mặc định), hoặc 'vnexpress', 'tuoitre', 'thanhnien', 'dantri', 'vietnamnet', 'nld', 'vtcnews', 'giaoducthoidai', 'nhandan', 'baochinhphu', 'vtv', 'vietnamplus', 'baohaiphong', 'cand', 'tienphong', 'bbc', 'tinhte', 'quantrimang', 'thethao247'.
        limit: Số lượng tin mỗi mục (mặc định 8, tối đa 15).
    """
    limit = max(1, min(int(limit), 15))
    scope_norm = (scope or "both").strip().lower()
    source_norm = (source or "all").strip().lower()

    # If user explicitly asks for a tech or sports source without setting scope, route automatically
    if source_norm in ("tinhte", "quantrimang") and scope_norm == "both":
        scope_norm = "tech"
    elif source_norm == "thethao247" and scope_norm == "both":
        scope_norm = "sports"

    scopes = []
    if scope_norm in ("domestic", "trong_nuoc", "both", "all"):
        scopes.append(("domestic_news", NEWS_FEEDS["domestic"]))
    if scope_norm in ("international", "quoc_te", "world", "both", "all"):
        scopes.append(("international_news", NEWS_FEEDS["international"]))
    if scope_norm in ("tech", "cong_nghe", "technology", "all"):
        scopes.append(("tech_news", NEWS_FEEDS["tech"]))
    if scope_norm in ("sports", "the_thao", "sport", "all"):
        scopes.append(("sports_news", NEWS_FEEDS["sports"]))
    if not scopes:
        scopes = [
            ("domestic_news", NEWS_FEEDS["domestic"]),
            ("international_news", NEWS_FEEDS["international"]),
        ]

    output = {"success": False}
    for out_key, feed_list in scopes:
        selected = [
            (name, url)
            for name, code, url in feed_list
            if source_norm == "all" or source_norm == code
        ]
        if not selected:
            selected = [(name, url) for name, _, url in feed_list]

        per_feed = limit if len(selected) == 1 else max(2, (limit // len(selected)) + 2)
        with ThreadPoolExecutor(max_workers=len(selected)) as pool:
            results = list(pool.map(lambda f: _fetch_single_feed(f[0], f[1], per_feed), selected))

        # Interleave items round-robin across newspapers so results are diverse
        merged = []
        idx = 0
        while len(merged) < limit:
            added = False
            for r in results:
                if idx < len(r):
                    merged.append(r[idx])
                    added = True
                    if len(merged) >= limit:
                        break
            if not added:
                break
            idx += 1

        if merged:
            output["success"] = True
        output[out_key] = merged

    return output


@mcp.tool()
def get_full_article(url: str) -> dict:
    """
    Đọc nội dung đầy đủ của một bài báo từ link `url` (hỗ trợ VnExpress, Tuổi Trẻ, Thanh Niên, Dân Trí, VietnamNet và các báo phổ biến).
    Dùng tool này khi người dùng muốn nghe chi tiết / đọc đầy đủ một tin tức vừa được điểm qua.
    Args:
        url: Đường dẫn URL của bài báo.
    """
    if not url or not url.startswith("http"):
        return {"success": False, "message": "URL bài báo không hợp lệ"}

    try:
        html_text = _http_get(url, timeout=12)
        soup = BeautifulSoup(html_text, "html.parser")

        for tag in soup(["script", "style", "noscript", "iframe", "aside", "nav", "footer"]):
            tag.decompose()

        title_el = soup.select_one("h1.title-detail, h1.detail-title, h1.article-title, h1.title-page, h1.content-detail-title, h1")
        title = title_el.get_text(" ", strip=True) if title_el else ""

        sapo_el = soup.select_one("p.description, h2.detail-sapo, h2.singular-sapo, div.content-detail-sapo, .sapo")
        sapo = sapo_el.get_text(" ", strip=True) if sapo_el else ""

        content_selectors = [
            "article.fck_detail",
            "div.detail-content",
            "div.detail-content-body",
            "div.singular-content",
            "div.maincontent",
            "div.content-detail",
            "div.detail__content",
            "div.content-news-detail",
            "div.edittor-content",
            "div.article__body",
            "div.article-body",
            "div.entry-content",
            "div.cms-body",
            "div#abody",
            "div.post-content",
            "div.xf-body-content",
            "div#main-content",
            "main article",
            "article",
        ]
        paragraphs = []
        for sel in content_selectors:
            container = soup.select_one(sel)
            if container:
                for p in container.select("p, span.xf-body-paragraph"):
                    txt = p.get_text(" ", strip=True)
                    if len(txt) > 25:
                        paragraphs.append(txt)
                if paragraphs:
                    break

        if not paragraphs:
            for p in soup.select("p, span.xf-body-paragraph"):
                txt = p.get_text(" ", strip=True)
                if len(txt) > 40:
                    paragraphs.append(txt)

        body = "\n".join(paragraphs)
        if len(body) > 4500:
            body = body[:4500].rsplit(" ", 1)[0] + "..."

        return {
            "success": bool(body or sapo),
            "url": url,
            "title": title,
            "sapo": sapo,
            "content": body,
        }
    except Exception as e:
        return {"success": False, "url": url, "message": f"Không đọc được bài báo: {e}"}


if __name__ == "__main__":
    mcp.run(transport="stdio")
