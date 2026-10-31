# -*- coding: utf-8 -*-
# Минимальный проверочный скрипт для исполнителя Python в Salebot.
# Без сетевых запросов, без токенов и персональных данных.
import json

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except Exception as exc:
    BS4_AVAILABLE = False
    BS4_ERROR = "{}: {}".format(type(exc).__name__, exc)


def handle(data):
    try:
        # Разбор входной JSON-строки из params блока
        try:
            params = json.loads(data) if data else {}
        except Exception as exc:
            params = {"_parse_error": "{}: {}".format(type(exc).__name__, exc)}

        if not BS4_AVAILABLE:
            return json.dumps(
                {
                    "ok": False,
                    "title": None,
                    "bs4_available": False,
                    "bs4_error": BS4_ERROR,
                },
                ensure_ascii=False,
            )

        # Тестовый HTML с русским заголовком
        html = '<h1>Проверка русского текста</h1>'

        soup = BeautifulSoup(html, "html.parser")
        h1 = soup.find("h1")
        title = h1.get_text(strip=True) if h1 is not None else None

        return json.dumps(
            {
                "ok": True,
                "title": title,
                "bs4_available": True,
                "received_params": params,
            },
            ensure_ascii=False,
        )

    except Exception as exc:
        # Диагностический результат при любой ошибке
        return json.dumps(
            {
                "ok": False,
                "title": None,
                "bs4_available": BS4_AVAILABLE,
                "error": "{}: {}".format(type(exc).__name__, exc),
            },
            ensure_ascii=False,
        )
