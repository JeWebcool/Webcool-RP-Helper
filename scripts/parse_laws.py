import os
import json
import re
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

LAWS_CONFIG = {
    "constitution.json": ("https://forum.grand-rp.su/threads/404080/", "Конституция"),
    "ethics_code.json": ("https://forum.grand-rp.su/threads/404079/", "ЭК"),
    "labor_code.json": ("https://forum.grand-rp.su/threads/404078/", "ТК"),
    "road_code.json": ("https://forum.grand-rp.su/threads/404077/", "ДК"),
    "judicial_code.json": ("https://forum.grand-rp.su/threads/404076/", "СК"),
    "procedural_code.json": ("https://forum.grand-rp.su/threads/404075/", "ПК"),
    "administrative_code.json": ("https://forum.grand-rp.su/threads/404074/", "АК"),
    "gov_service_law.json": ("https://forum.grand-rp.su/threads/405387/", "Закон о гос. службе"),
    "advocate_law.json": ("https://forum.grand-rp.su/threads/404399/", "Закон об адвокатской деятельности"),
    "prosecutor_law.json": ("https://forum.grand-rp.su/threads/404091/", "Закон о Прокуратуре"),
    "ng_law.json": ("https://forum.grand-rp.su/threads/404072/", "NG"),
    "lspd_law.json": ("https://forum.grand-rp.su/threads/404071/", "LSPD"),
    "sahp_law.json": ("https://forum.grand-rp.su/threads/404070/", "SAHP"),
    "fib_law.json": ("https://forum.grand-rp.su/threads/404069/", "FIB"),
    "ems_law.json": ("https://forum.grand-rp.su/threads/404068/", "EMS"),
    "usss_law.json": ("https://forum.grand-rp.su/threads/404067/", "USSS"),
}

PUNISHMENT_REGEX = re.compile(
    r'((?:Наказывается|Санкции(?:\s+(?:пешеходу|водителю|пилоту))?|влечет\s+за\s+собой[^\n]*|штраф[^\n]*|арест[^\n]*|дисциплинарн[^\n]*взыскани[^\n]*)[^\n]*)',
    re.IGNORECASE
)

def clean_html_text(raw_text: str) -> str:
    if not raw_text:
        return ""
    text = re.sub(r'Приоритет\s+розыска[:\s]*\d+\.?', '', raw_text, flags=re.IGNORECASE)
    text = re.sub(r'Уровень\s+розыска[:\s]*\d+\.?', '', text, flags=re.IGNORECASE)
    return re.sub(r'\s+', ' ', text).strip()

def parse_single_law(page, url: str, code_name: str, output_filename: str):
    print(f"🚀 Парсим: {code_name} ({url})...")
    
    try:
        page.goto(url, wait_until="networkidle", timeout=30000)
        html_content = page.content()
    except Exception as e:
        print(f"❌ Ошибка загрузки {url}: {e}")
        return

    soup = BeautifulSoup(html_content, "html.parser")
    post_content = soup.find("div", class_="bbWrapper")

    if not post_content:
        print(f"❌ Контейнер bbWrapper не найден для {code_name}.")
        return

    for br in post_content.find_all("br"):
        br.replace_with("\n")

    lines = [l.strip() for l in post_content.get_text().split('\n') if l.strip()]

    articles = []
    current_chapter = "Общие положения"
    current_article = None
    current_comment_type = None

    for line in lines:
        if re.search(r'^(?:\d+\s+Статья|Глава)\b', line, re.IGNORECASE) and len(line) < 120:
            current_chapter = clean_html_text(line)
            current_comment_type = None
            continue

        main_art_match = re.search(r'^(?:Статья\s+)?(\d+\.\d+)\s*(?:\((F|R)\))?\s*(.*)', line, re.IGNORECASE)
        sub_art_match = re.search(r'^(\d+\.\d+\.(\d+)(?:\.(\d+))?)\s*(.*)', line)

        if main_art_match and not sub_art_match:
            art_num = main_art_match.group(1).strip()
            law_type = main_art_match.group(2).upper() if main_art_match.group(2) else None
            rest_line = main_art_match.group(3).strip()

            wanted_match = re.search(r'(?:Приоритет|Уровень)\s+розыска[:\s]*(\d+)', line, re.IGNORECASE)
            wanted_level = int(wanted_match.group(1)) if wanted_match else None

            pun_match = PUNISHMENT_REGEX.search(rest_line)
            punishment_text = ""
            clean_body_text = rest_line
            
            if pun_match:
                punishment_text = pun_match.group(1).strip()
                clean_body_text = rest_line.replace(punishment_text, "").strip()

            current_article = {
                "code": code_name,
                "article": art_num,
                "chapter": current_chapter,
                "text": clean_html_text(clean_body_text),
                "punishment_text": punishment_text,
                "wanted_level": wanted_level,
                "type": law_type
            }
            articles.append(current_article)
            current_comment_type = None
            continue

        elif current_article and sub_art_match:
            current_comment_type = None
            lvl2, lvl3 = sub_art_match.group(2), sub_art_match.group(3)
            sub_text = clean_html_text(sub_art_match.group(4))

            wanted_match = re.search(r'(?:Приоритет|Уровень)\s+розыска[:\s]*(\d+)', line, re.IGNORECASE)
            if wanted_match and not current_article.get("wanted_level"):
                current_article["wanted_level"] = int(wanted_match.group(1))

            pun_match = PUNISHMENT_REGEX.search(line)
            if pun_match:
                found_pun = pun_match.group(1).strip()
                if found_pun and found_pun not in current_article["punishment_text"]:
                    current_article["punishment_text"] = (
                        f"{current_article['punishment_text']}; {found_pun}" 
                        if current_article["punishment_text"] else found_pun
                    )

            if lvl3:
                current_article.setdefault("subparts", [])
                if current_article["subparts"]:
                    last_sub = current_article["subparts"][-1]
                    last_sub.setdefault("nested", []).append({"sub": lvl3, "text": sub_text})
            else:
                current_article.setdefault("subparts", []).append({"sub": lvl2, "text": sub_text})

        elif current_article:
            lower_line, cleaned_line = line.lower(), clean_html_text(line)

            if "комментарий:" in lower_line or lower_line == "комментарий:":
                current_comment_type = "comments"
                remnant = clean_html_text(re.sub(r'комментарий:\s*', '', line, flags=re.IGNORECASE))
                if remnant:
                    current_article.setdefault("comments", []).append(remnant)
                    current_comment_type = None
                continue

            elif any(k in lower_line for k in ["примечание:", "примечания:"]) or lower_line in ["примечание:", "примечания:"]:
                current_comment_type = "notes"
                remnant = clean_html_text(re.sub(r'примечани[яе]:\s*', '', line, flags=re.IGNORECASE))
                if remnant:
                    current_article.setdefault("notes", []).append(remnant)
                    current_comment_type = None
                continue

            elif any(k in lower_line for k in ["исключение:", "исключения:"]) or lower_line in ["исключение:", "исключения:"]:
                current_comment_type = "exceptions"
                remnant = clean_html_text(re.sub(r'исключени[яе]:\s*', '', line, flags=re.IGNORECASE))
                if remnant:
                    current_article.setdefault("exceptions", []).append(remnant)
                    current_comment_type = None
                continue

            if current_comment_type and cleaned_line:
                current_article.setdefault(current_comment_type, []).append(cleaned_line)
                current_comment_type = None
                continue

            if cleaned_line and not any(w in lower_line for w in ["приоритет розыска", "уровень розыска", "наказывается", "санкции", "влечет за собой"]):
                current_article["text"] = (
                    f"{current_article['text']} {cleaned_line}" 
                    if current_article["text"] else cleaned_line
                )

    output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "database")
    os.makedirs(output_dir, exist_ok=True)
    out_file = os.path.join(output_dir, output_filename)

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=4)
    print(f"✅ Сохранено: {output_filename} (Статей: {len(articles)})")

if __name__ == "__main__":
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        for filename, (url, code_name) in LAWS_CONFIG.items():
            parse_single_law(page, url, code_name, filename)
        browser.close()
    print("\n🎉 Все законы успешно спарсены и разложены по файлам!")