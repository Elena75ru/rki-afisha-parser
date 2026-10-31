# -*- coding: utf-8 -*-
# e1_event_probe.py
# Исследование разметки карточек событий https://www.e1.ru/afisha/
# через BeautifulSoup в исполнителе Salebot. Без платных сервисов.
import json

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
    BS4_ERROR = None
except Exception as exc:
    BS4_AVAILABLE = False
    BS4_ERROR = "{}: {}".format(type(exc).__name__, exc)

try:
    import requests
    REQUESTS_AVAILABLE = True
    REQUESTS_ERROR = None
except Exception as exc:
    REQUESTS_AVAILABLE = False
    REQUESTS_ERROR = "{}: {}".format(type(exc).__name__, exc)

from urllib.parse import urljoin


def _probe_card(a, final_url):
    """Пытается вытащить данные из контейнера ссылки-кандидата.
    Возвращает dict или None, если контейнер не даёт связанной записи."""
    href = a.get("href", "").strip()
    if not href:
        return None
    container = a
    for _ in range(6):  # поднимаемся к ближайшему контейнеру-обёртке
        parent = container.parent
        if parent is None or parent.name in ("html", "body"):
            break
        container = parent

    name = a.get_text(strip=True)
    full_url = urljoin(final_url, href)

    # Дата/время/площадка — если они лежат в том же контейнере
    text_block = container.get_text(separator=" ", strip=True)
    date_hint = None
    time_hint = None
    place_hint = None

    import re
    m_date = re.search(r"(\d{1,2}\.\d{2}\.\d{4})", text_block)
    if m_date:
        date_hint = m_date.group(1)
    m_time = re.search(r"(\d{1,2}:\d{2})", text_block)
    if m_time:
        time_hint = m_time.group(1)

    return {
        "name": name or None,
        "url": full_url,
        "date": date_hint,
        "time": time_hint,
        "place": place_hint,
        "container_html": str(container)[:1200],
        "container_text": text_block[:600],
    }


def handle(data):
    url = "https://www.e1.ru/afisha/"

    try:
        try:
            params = json.loads(data) if data else {}
        except Exception as exc:
            params = {"_parse_error": "{}: {}".format(type(exc).__name__, exc)}

        if not (BS4_AVAILABLE and REQUESTS_AVAILABLE):
            return json.dumps(
                {"ok": False,
                 "bs4_available": BS4_AVAILABLE,
                 "bs4_error": BS4_ERROR,
                 "requests_available": REQUESTS_AVAILABLE,
                 "requests_error": REQUESTS_ERROR},
                ensure_ascii=False,
            )

        resp = requests.get(
            url,
            timeout=(4.0, 6.0),
            headers={"User-Agent": "Mozilla/5.0 (compatible; Salebot test)"},
        )
        resp.raise_for_status()

        body = resp.content
        soup = BeautifulSoup(body, "html.parser")
        status = resp.status_code
        final_url = resp.url

        # Кандидаты в карточки событий: ссылки, чей URL выглядит как
        # карточка мероприятия (id в пути). Без выдуманных CSS-классов.
        import re
        candidates = []
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if not href:
                continue
            if re.search(r"-id\d+", href) or "/afisha/" in href:
                candidates.append(a)

        # Убираем повторы по href
        seen = set()
        uniq = []
        for a in candidates:
            h = a["href"].strip()
            if h not in seen:
                seen.add(h)
                uniq.append(a)
        candidates = uniq

        # Берём первые до 5 и пробуем извлечь связанную запись
        cards = []
        for a in candidates[:5]:
            card = _probe_card(a, final_url)
            if card:
                cards.append(card)

        if not cards:
            return json.dumps(
                {
                    "ok": False,
                    "status": status,
                    "final_url": final_url,
                    "reason": "no event-card candidates found or no container yielded a related record",
                    "candidates_found": len(candidates),
                },
                ensure_ascii=False,
            )

        # Первая успешная карточка — результат
        first = cards[0]
        return json.dumps(
            {
                "ok": True,
                "status": status,
                "final_url": final_url,
                "event": {
                    "name": first["name"],
                    "url": first["url"],
                    "date": first["date"],
                    "time": first["time"],
                    "place": first["place"],
                },
                "container_html": first["container_html"],
                "container_text": first["container_text"],
            },
            ensure_ascii=False,
        )

    except Exception as exc:
        return json.dumps(
            {
                "ok": False,
                "bs4_available": BS4_AVAILABLE,
                "requests_available": REQUESTS_AVAILABLE,
                "error": "{}: {}".format(type(exc).__name__, exc),
            },
            ensure_ascii=False,
        )
