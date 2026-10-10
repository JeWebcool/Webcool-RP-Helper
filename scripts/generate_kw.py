import json
import os
import re

DATABASE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "database")
OUTPUT_KEYWORDS_FILE = os.path.join(DATABASE_DIR, "keywords_map.json")

# Стоп-слова для фильтрации мусора
STOP_WORDS = {"в", "на", "и", "с", "по", "к", "о", "от", "for", "для", "не", "за", "или", "что", "как", "а", "но", "до", "из", "у", "же", "это", "при", "лицо", "года"}

def extract_all_text(item: dict) -> str:
    """Собирает весь доступный текст из статьи (включая подпункты, примечания и исключения) для качественного поиска."""
    texts = [
        item.get("name", ""),
        item.get("text", ""),
        item.get("chapter", ""),
        item.get("punishment_text", "")
    ]
    
    # Собираем текст из подпунктов и вложений
    for sub in item.get("subparts", []):
        texts.append(sub.get("text", ""))
        for nest in sub.get("nested", []):
            texts.append(nest.get("text", ""))
            
    # Собираем из примечаний, комментариев и исключений
    for key in ("notes", "comments", "exceptions"):
        val = item.get(key, [])
        if isinstance(val, list):
            texts.extend(val)
            
    return " ".join(t for t in texts if t).lower()

def generate_global_keywords():
    if not os.path.exists(DATABASE_DIR):
        print(f"❌ Ошибка: Папка database не найдена по пути {DATABASE_DIR}!")
        return

    keywords_map = {}
    
    # Кастомный игровой сленг и синонимы с привязкой к кодексу и статье
    slang_additions = {
        "АК:4.4": ["увольнение", "работодатель", "без оснований", "беспредел"],
    }

    excluded_files = {"config.json", "keywords_map.json"}
    total_articles = 0

    for filename in os.listdir(DATABASE_DIR):
        if filename.endswith(".json") and filename not in excluded_files:
            file_path = os.path.join(DATABASE_DIR, filename)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if not isinstance(data, list):
                        continue
                    
                    for item in data:
                        art_num = str(item.get("article", ""))
                        if not art_num:
                            continue
                        
                        code = item.get("code", "")
                        unique_key = f"{code}:{art_num}" if code else art_num
                        
                        # Извлекаем текст изо всех полей статьи
                        combined_text = extract_all_text(item)
                        
                        # Вытаскиваем слова (только русские буквы длиной от 3 символов)
                        raw_words = re.findall(r'[а-яё]{3,}', combined_text)
                        article_keywords = {w for w in raw_words if w not in STOP_WORDS}
                        
                        # Добавляем кастомный сленг, если он задан
                        if unique_key in slang_additions:
                            article_keywords.update(slang_additions[unique_key])
                        elif art_num in slang_additions:
                            article_keywords.update(slang_additions[art_num])
                        
                        keywords_map[unique_key] = list(article_keywords)
                        total_articles += 1
            except Exception as e:
                print(f"⚠️ Ошибка обработки файла {filename}: {e}")

    with open(OUTPUT_KEYWORDS_FILE, "w", encoding="utf-8") as f:
        json.dump(keywords_map, f, ensure_ascii=False, indent=4)
        
    print(f"✅ Успешно! Сгенерированы ключевые слова для {total_articles} статей со всех законов. Файл сохранен в {OUTPUT_KEYWORDS_FILE}.")

if __name__ == "__main__":
    generate_global_keywords()