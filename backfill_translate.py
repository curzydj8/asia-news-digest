"""专项补译脚本：补翻已有条目的 title_zh/summary_zh（translate_a 被封时回退为英文原文的）。
用法: python3 backfill_translate.py [日期，默认今天]
只处理 title_zh == title_en 的条目；summary 仅在 summary_en 非空且 summary_zh == summary_en 时补翻。
复用 fetch_news.translate_batch（带缓存），不会改动其他字段和条目顺序。
"""
import json, os, sys, datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fetch_news import translate_batch

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

def main():
    day = sys.argv[1] if len(sys.argv) > 1 else datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).strftime("%Y-%m-%d")
    path = os.path.join(DATA_DIR, f"{day}.json")
    items = json.load(open(path, encoding="utf-8"))
    if isinstance(items, dict):
        items = items.get("items", [])

    todo_titles = [(i, it) for i, it in enumerate(items) if it.get("title_zh") == it.get("title_en") and it.get("title_en")]
    todo_summ = [(i, it) for i, it in enumerate(items)
                 if it.get("summary_en") and it.get("summary_zh") == it.get("summary_en")]

    print(f"{day}: items={len(items)} untranslated_titles={len(todo_titles)} untranslated_summaries={len(todo_summ)}")
    if not todo_titles and not todo_summ:
        print("nothing to do")
        return

    if todo_titles:
        zh_titles = translate_batch([it["title_en"] for _, it in todo_titles])
        for (i, _), zh in zip(todo_titles, zh_titles):
            items[i]["title_zh"] = zh
    if todo_summ:
        zh_summ = translate_batch([it["summary_en"] for _, it in todo_summ])
        for (i, _), zh in zip(todo_summ, zh_summ):
            items[i]["summary_zh"] = zh

    json.dump(items, open(path, "w", encoding="utf-8"), ensure_ascii=False)
    print("saved", path)

    # 快速自检：仍未翻译的（API 又被封时）
    left = sum(1 for it in items if it.get("title_zh") == it.get("title_en"))
    print("still untranslated titles:", left)

if __name__ == "__main__":
    main()
