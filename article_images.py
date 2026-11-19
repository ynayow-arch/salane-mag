import html
import json
import mimetypes
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


TOPIC_QUERIES = (
    ("김장", "kimchi preparation napa cabbage"),
    ("배추", "napa cabbage"),
    ("독감", "influenza vaccine"),
    ("예방접종", "vaccination"),
    ("고구마", "sweet potato food"),
    ("두부", "tofu food"),
    ("코트", "winter coat woman"),
    ("목도리", "scarf woman winter"),
    ("피부", "woman skincare"),
    ("보습", "moisturizer skincare"),
    ("양말", "winter socks"),
    ("신발", "walking shoes"),
    ("AI", "artificial intelligence family small business"),
    ("용돈", "family money support elderly parent"),
    ("증여세", "family financial planning"),
    ("전기장판", "electric blanket home safety"),
    ("전기난로", "electric heater home safety"),
    ("롱스커트", "mature woman winter long skirt outfit"),
    ("빙판길", "winter icy sidewalk walking safely"),
    ("낙상", "older adult fall prevention walking"),
    ("송년 모임", "older women friends winter group photo"),
    ("단체사진", "older women friends group photo"),
    ("데이터센터", "data center servers"),
    ("전력", "power grid"),
    ("금리", "bank interest rate"),
    ("해외직구", "online shopping parcel"),
)

LICENSE_PATTERN = re.compile(
    r"(?:CC0|CC BY(?:-SA)?(?:\s+[0-9.]+)?|public domain)",
    re.IGNORECASE,
)


def _clean_metadata(value):
    value = re.sub(r"<[^>]*>", "", value or "")
    return html.unescape(value).strip()


def _search_queries(title):
    matches = [query for keyword, query in TOPIC_QUERIES if keyword in title]
    queries = []
    if matches:
        queries.append(" ".join(matches[:2]))
        queries.extend(matches)
    else:
        queries.append(title)
    return list(dict.fromkeys(queries))


def _find_commons_image(title):
    headers = {"User-Agent": "MagazineArticleImages/1.0 (Wikimedia Commons API client)"}
    for query in _search_queries(title):
        params = {
            "action": "query",
            "generator": "search",
            "gsrsearch": query,
            "gsrnamespace": 6,
            "gsrlimit": 20,
            "prop": "imageinfo",
            "iiprop": "url|mime|extmetadata",
            "iiurlwidth": 1200,
            "format": "json",
            "formatversion": 2,
        }
        url = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(params)
        request = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))

        pages = data.get("query", {}).get("pages", [])
        if isinstance(pages, dict):
            pages = list(pages.values())
        pages.sort(key=lambda page: page.get("index", 0))

        for page in pages:
            title_text = page.get("title", "")
            if re.search(r"(coat of arms|logo|flag|diagram|map|chart|icon)", title_text, re.I):
                continue
            imageinfo = page.get("imageinfo", [{}])[0]
            mime = imageinfo.get("mime", "")
            if mime not in ("image/jpeg", "image/png", "image/webp"):
                continue

            metadata = imageinfo.get("extmetadata", {})
            license_name = _clean_metadata(metadata.get("LicenseShortName", {}).get("value", ""))
            if not LICENSE_PATTERN.search(license_name) or re.search(r"\bNC\b|non.?commercial", license_name, re.I):
                continue

            image_url = imageinfo.get("thumburl") or imageinfo.get("url")
            source_url = imageinfo.get("url")
            page_url = imageinfo.get("descriptionurl")
            if image_url and source_url and page_url:
                return {
                    "download_url": image_url,
                    "source_url": source_url,
                    "page_url": page_url,
                    "title": _clean_metadata(metadata.get("ObjectName", {}).get("value", re.sub(r"^File:", "", title_text))),
                    "license": license_name,
                    "author": _clean_metadata(metadata.get("Artist", {}).get("value", "")),
                    "mime": mime,
                }

    raise RuntimeError(
        f"No freely licensed Commons image found for {title!r}. "
        "Check the network or adjust TOPIC_QUERIES in article_images.py."
    )


def _local_illustration(title):
    if "양말" in title or "신발" in title:
        artwork = '<path d="M430 170h85v170l65 60q15 18-8 30H420q-20-10-10-32l20-48z" fill="#d77d6b"/><path d="M610 180h82v160l68 58q16 18-8 32H600q-19-10-9-33l19-47z" fill="#e2b34e"/><path d="M385 430q70-35 200 0l-20 54H365z" fill="#647c78"/><path d="M585 430q70-35 200 0l-20 54H565z" fill="#647c78"/>'
    elif "AI" in title:
        artwork = '<rect x="390" y="215" width="420" height="270" rx="24" fill="#647c78"/><rect x="420" y="245" width="360" height="200" rx="12" fill="#f3e7d4"/><path d="M520 510h160l35 34H485z" fill="#d77d6b"/><circle cx="600" cy="345" r="52" fill="#d9b469"/><path d="M600 275v-30m0 200v-30m70-70h30m-200 0h30" stroke="#647c78" stroke-width="16" stroke-linecap="round"/>'
    elif "용돈" in title or "증여세" in title:
        artwork = '<rect x="390" y="300" width="420" height="185" rx="28" fill="#687c73"/><circle cx="490" cy="350" r="46" fill="#e2b34e"/><circle cx="600" cy="350" r="46" fill="#d9b469"/><circle cx="710" cy="350" r="46" fill="#e2b34e"/><path d="M470 430h260" stroke="#f7f0e5" stroke-width="18" stroke-linecap="round"/><path d="M500 240q100-80 200 0" fill="none" stroke="#d77d6b" stroke-width="24" stroke-linecap="round"/>'
    elif "전기장판" in title or "전기난로" in title:
        artwork = '<rect x="380" y="350" width="440" height="150" rx="34" fill="#d77d6b"/><path d="M420 385h360M420 430h360M420 475h360" stroke="#f7f0e5" stroke-width="12" stroke-linecap="round"/><rect x="530" y="250" width="140" height="82" rx="18" fill="#687c73"/><circle cx="600" cy="290" r="20" fill="#e2b34e"/><path d="M480 525h240" stroke="#647c78" stroke-width="16" stroke-linecap="round"/>'
    elif "롱스커트" in title:
        artwork = '<circle cx="600" cy="190" r="58" fill="#d89c78"/><path d="M505 260q95-70 190 0l55 105H450z" fill="#687c73"/><path d="M470 360h260l78 155H392z" fill="#d77d6b"/><path d="M560 270l40 72 40-72" fill="none" stroke="#e2b34e" stroke-width="18" stroke-linecap="round"/>'
    elif "빙판길" in title or "낙상" in title:
        artwork = '<path d="M300 480h600" stroke="#83a698" stroke-width="28" stroke-linecap="round"/><path d="M390 430l120-110 100 80 110-140" fill="none" stroke="#d9b469" stroke-width="18" stroke-linecap="round"/><circle cx="600" cy="185" r="48" fill="#d89c78"/><path d="M595 240l-20 130 90 55m-70-182l90 75 55-5m-165 57l-65 105m150-50l45 100" fill="none" stroke="#687c73" stroke-width="30" stroke-linecap="round"/>'
    elif "송년" in title or "단체사진" in title:
        artwork = '<circle cx="470" cy="255" r="52" fill="#d89c78"/><circle cx="600" cy="220" r="58" fill="#d9a080"/><circle cx="730" cy="255" r="52" fill="#c98e70"/><path d="M390 330q80-65 160 0l30 150H360zM515 300q85-70 170 0l35 180H480zM650 330q80-65 160 0l30 150H620z" fill="#687c73"/><rect x="540" y="445" width="120" height="72" rx="14" fill="#d9b469"/><circle cx="600" cy="481" r="20" fill="#f7f0e5"/>'
    elif "코트" in title or "목도리" in title:
        artwork = '<circle cx="600" cy="210" r="52" fill="#d89c78"/><path d="M520 275l-90 65 42 150h256l42-150-90-65-80 65z" fill="#687c73"/><path d="M565 270l35 70 35-70 25 21-23 120h-74l-23-120z" fill="#c56c5b"/><path d="M578 305h44v170h-44z" fill="#d9b469"/>'
    elif "피부" in title or "보습" in title:
        artwork = '<path d="M470 280h260v195q0 35-35 35H505q-35 0-35-35z" fill="#d89c78"/><rect x="510" y="235" width="180" height="48" rx="12" fill="#f3d9b6"/><rect x="540" y="205" width="120" height="34" rx="8" fill="#687c73"/><path d="M780 310q-75 60-20 110 55-25 20-110z" fill="#83a698"/><path d="M405 350q-48-54-83 0 35 54 83 0z" fill="#93ad83"/>'
    elif "김장" in title or "배추" in title:
        artwork = '<path d="M600 470q-170-80-125-220 44-100 125-20 81-80 125 20 45 140-125 220z" fill="#f1d78f"/><path d="M600 470q-105-108-68-225 30-92 68-15 38-77 68 15 37 117-68 225z" fill="#8da77d"/><path d="M600 466v-208" stroke="#f8efd9" stroke-width="18" stroke-linecap="round"/>'
    elif "독감" in title or "예방접종" in title:
        artwork = '<path d="M600 190l155 58v110q0 126-155 188-155-62-155-188V248z" fill="#77978a"/><path d="M600 245v205" stroke="#f7eedc" stroke-width="28" stroke-linecap="round"/><path d="M520 345h160" stroke="#f7eedc" stroke-width="28" stroke-linecap="round"/><circle cx="600" cy="347" r="24" fill="#d77d6b"/>'
    elif "고구마" in title or "두부" in title:
        artwork = '<path d="M430 390q-30-102 75-143 110-43 186 30 55 54 12 128-58 92-190 76-65-8-83-91z" fill="#b46f53"/><path d="M450 385q-10-78 84-108 86-28 145 20" fill="none" stroke="#e0b48d" stroke-width="18" stroke-linecap="round"/><path d="M685 280q52-85 112-28-29 67-112 28z" fill="#819777"/><circle cx="760" cy="385" r="38" fill="#f2dfa9"/>'
    else:
        artwork = '<circle cx="600" cy="350" r="142" fill="#d9b469"/><path d="M600 225q-84 70 0 145 84-75 0-145z" fill="#77978a"/><path d="M600 365q-115 30-78 112 90 2 78-112z" fill="#93ad83"/><path d="M605 365q115 30 78 112-90 2-78-112z" fill="#d77d6b"/>'

    safe_title = html.escape(title[:42])
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="700" viewBox="0 0 1200 700">'
        '<rect width="1200" height="700" rx="36" fill="#f7f0e5"/>'
        '<circle cx="900" cy="160" r="190" fill="#eadfce"/>'
        '<circle cx="250" cy="560" r="220" fill="#eee2d0"/>'
        '<text x="90" y="100" fill="#647c70" font-size="24" font-family="Malgun Gothic,Noto Sans KR,sans-serif" letter-spacing="3">TODAY, WITH WARMTH</text>'
        f'<g stroke="#fff9ef" stroke-width="10" stroke-linejoin="round">{artwork}</g>'
        f'<text x="90" y="590" fill="#433f39" font-size="38" font-weight="700" font-family="Malgun Gothic,Noto Sans KR,sans-serif">{safe_title}</text>'
        '<text x="92" y="635" fill="#81796e" font-size="20" font-family="Malgun Gothic,Noto Sans KR,sans-serif">편안한 하루를 위한 작은 이야기</text>'
        '</svg>'
    )
    return {
        "license": "Original local SVG illustration",
        "author": "Generated locally",
        "mime": "image/svg+xml",
        "title": title,
        "svg": svg,
    }


def _insert_image_markdown(markdown_path, image_path, image_info, alt_text):
    text = markdown_path.read_text(encoding="utf-8")
    if re.search(r"!\[[^\]]*\]\([^)]+\)", text):
        return

    lines = text.splitlines()
    if not lines or not lines[0].startswith("# "):
        raise ValueError(f"Article must start with an H1 title: {markdown_path}")

    index = 1
    while index < len(lines):
        line = lines[index].strip()
        if not line:
            index += 1
            continue
        if re.match(r"^>\s*\*\*(?:한 줄 요약|메타 설명)\s*[:：]", line):
            index += 1
            continue
        if re.match(r"^\*\*(?:작성일|정보 기준 시점)\s*[:：]", line):
            index += 1
            continue
        break

    relative_path = os.path.relpath(image_path, markdown_path.parent).replace(os.sep, "/")
    if image_info.get("page_url"):
        source_title = image_info["title"].replace("[", "").replace("]", "")
        author = image_info.get("author") or "저작자 정보는 출처 페이지 참조"
        credit = f"> 이미지 출처: [{source_title}]({image_info['page_url']}) · {image_info['license']} · {author}"
    else:
        credit = "> 이미지: 글 주제에 맞춰 매거진에서 직접 만든 그림입니다."
    lines[index:index] = [
        f"![{alt_text}]({relative_path})",
        credit,
        "",
    ]
    markdown_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def ensure_article_image(article_path):
    markdown_path = Path(article_path).resolve()
    text = markdown_path.read_text(encoding="utf-8")
    existing = re.search(r"!\[([^\]]*)\]\(([^)]+)\)", text)
    if existing:
        source = existing.group(2)
        if source.startswith(("https://", "http://")):
            return None
        local_path = (markdown_path.parent / Path(source.replace("/", os.sep))).resolve()
        metadata_path = local_path.with_suffix(".json")
        if local_path.is_file() and metadata_path.is_file():
            return json.loads(metadata_path.read_text(encoding="utf-8"))
        if local_path.is_file():
            return None

    title_match = re.search(r"^#\s+(.+)$", text, re.M)
    title = title_match.group(1).strip() if title_match else markdown_path.stem
    image_root = markdown_path.parent / "assets" / "images"
    image_root.mkdir(parents=True, exist_ok=True)
    metadata_path = image_root / f"{markdown_path.stem}.json"
    if metadata_path.is_file():
        image_info = json.loads(metadata_path.read_text(encoding="utf-8"))
        image_path = image_root / image_info.get("filename", "")
        if image_path.is_file():
            _insert_image_markdown(markdown_path, image_path, image_info, re.sub(r"[\[\]()]", "", title))
            return image_info

    try:
        image_info = _find_commons_image(title)
        request = urllib.request.Request(
            image_info["download_url"],
            headers={"User-Agent": "MagazineArticleImages/1.0 (Wikimedia Commons API client)"},
        )
        with urllib.request.urlopen(request, timeout=45) as response:
            image_data = response.read(12 * 1024 * 1024 + 1)
        if len(image_data) > 12 * 1024 * 1024:
            raise RuntimeError(f"Commons image is larger than 12 MB: {image_info['page_url']}")
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, RuntimeError) as error:
        print(f"Warning: Commons image unavailable ({error}); creating an original local illustration.")
        image_info = _local_illustration(title)
        image_data = image_info.pop("svg").encode("utf-8")

    extension = mimetypes.guess_extension(image_info["mime"]) or ".jpg"
    if extension == ".jpe":
        extension = ".jpg"
    image_path = image_root / f"{markdown_path.stem}{extension}"
    image_path.write_bytes(image_data)

    image_info["filename"] = image_path.name
    metadata_path = image_path.with_suffix(".json")
    metadata_path.write_text(json.dumps(image_info, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    alt_text = re.sub(r"[\[\]()]", "", title)
    _insert_image_markdown(markdown_path, image_path, image_info, alt_text)
    return image_info


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Find and insert a freely licensed article image.")
    parser.add_argument("article", help="Path to a Markdown article")
    args = parser.parse_args()
    result = ensure_article_image(args.article)
    if result:
        print(f"Saved image: {result['filename']} ({result['license']})")
    else:
        print("Article already has an image; no new image was downloaded.")
