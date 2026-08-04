import os
import re

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
    
    for root, _, files in os.walk(quests):
        parts = root.lower().split(os.sep)
        
        # Если мы находимся внутри папки lang
        if "lang" in parts:
            lang_idx = parts.index("lang")
            # Если мы углубились дальше lang/ (например, lang/pt_br/... или lang/en_us/...)
            if len(parts) > lang_idx + 1:
                # Разрешаем искать файлы ТОЛЬКО внутри подпапки en_us, чужие языки пропускаем
                if parts[lang_idx + 1] != "en_us":
                    continue

        for name in files:
            if name.endswith(".snbt"):
                nl = name.lower()
                
                # Игнорируем монолитные файлы других языков типа ru_ru.snbt, es_es.snbt (кроме en_us.snbt)
                if re.match(r"^[a-z]{2}_[a-z]{2}\.snbt$", nl) and nl != "en_us.snbt":
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