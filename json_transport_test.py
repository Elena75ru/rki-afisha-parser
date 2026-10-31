# -*- coding: utf-8 -*-
# json_transport_test.py — проверка передачи Python → Salebot (без E1)
# Возвращает через json.dumps пять искусственных записей + плоские test4 поля.
import json

def handle(data):
    candidates = [
        {
            "n": 1,
            "name": "Тест 1 «один»",
            "url": "https://example.org/one",
            "note": "строка с кавычками «и» переносом\nстроки",
        },
        {
            "n": 2,
            "name": "Тест 2 \"двойные\"",
            "url": "https://example.org/two",
            "note": "вторая запись",
        },
        {
            "n": 3,
            "name": "Тест 3 — тире",
            "url": "https://example.org/three",
            "note": "третья",
        },
        {
            "n": 4,
            "name": "Тест 4 «четыре»",
            "url": "https://example.org/four",
            "note": "четвёртая: кавычки «», перенос\nстроки",
        },
        {
            "n": 5,
            "name": "Тест 5 (пять)",
            "url": "https://example.org/five",
            "note": "пятая",
        },
    ]

    payload = {
        "ok": True,
        "candidates": candidates,
        "test4_name": candidates[3]["name"],
        "test4_url": candidates[3]["url"],
    }

    # Самопроверка: json.loads(json.dumps(...)) — ok=true только при успехе
    try:
        encoded = json.dumps(payload, ensure_ascii=False)
        decoded = json.loads(encoded)
        self_ok = decoded["ok"] is True and len(decoded["candidates"]) == 5
    except Exception:
        self_ok = False

    payload["self_check_ok"] = self_ok
    return json.dumps(payload, ensure_ascii=False)
