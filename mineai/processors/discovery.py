import os

from mineai.constants import LOOSE_JSON_SEARCH_DIRS


def discover_jar_files(mc_dir: str) -> list[str]:
    mods_dir = os.path.join(mc_dir, "mods")
    if not os.path.isdir(mods_dir):
        return []
    return [os.path.join(mods_dir, f) for f in os.listdir(mods_dir) if f.endswith(".jar")]


def discover_loose_lang_files(mc_dir: str) -> list[str]:
    found: list[str] = []
    for rel in LOOSE_JSON_SEARCH_DIRS:
        base = os.path.join(mc_dir, rel.replace("/", os.sep))
        if not os.path.isdir(base):
            continue
        for root, _, files in os.walk(base):
            for name in files:
                if name.lower() == "en_us.json":
                    found.append(os.path.join(root, name))
    return found


def discover_snbt_files(mc_dir: str) -> list[str]:
    quests = os.path.join(mc_dir, "config", "ftbquests", "quests")
    if not os.path.isdir(quests):
        return []
    
    result: list[str] = []
    # Список языковых файлов, которые точно нужно игнорировать
    ignore_langs = {
        "ru_ru.snbt", "zh_cn.snbt", "es_es.snbt", "de_de.snbt", 
        "fr_fr.snbt", "pt_br.snbt", "ko_kr.snbt", "ja_jp.snbt"
    }
    
    for root, _, files in os.walk(quests):
        is_lang_dir = "lang" in root.lower().split(os.sep)
        
        for name in files:
            if name.endswith(".snbt"):
                nl = name.lower()
                
                # Если мы в папке lang, берем ТОЛЬКО en_us.snbt
                if is_lang_dir and nl != "en_us.snbt":
                    continue
                
                # Отсекаем известные файлы переводов, если они лежат в корне квестов
                if nl in ignore_langs:
                    continue
                    
                result.append(os.path.join(root, name))
                
    return result


def discover_bq_files(mc_dir: str) -> list[str]:
    # Путь к папке BetterQuesting
    quests_dir = os.path.join(mc_dir, "config", "betterquesting", "DefaultQuests")
    if not os.path.isdir(quests_dir):
        return []
        
    result: list[str] = []
    for root, _, files in os.walk(quests_dir):
        for name in files:
            # Нам нужны только файлы .json внутри папок QuestLines и Quests
            if name.endswith(".json") and ("QuestLines" in root or "Quests" in root):
                result.append(os.path.join(root, name))
                
    return result