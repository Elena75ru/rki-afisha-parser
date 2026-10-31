# -*- coding: utf-8 -*-
# e1_event_probe.py (этап: list/card, извлечение полей внутри <a>, карточка «Аффинаж»)
# Два отдельных режима через params.stage. Без платных сервисов.
import json
import re

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

from urllib.parse import urljoin, urlparse

# Русские названия месяцев для поиска даты в тексте ссылки
MONTHS = ["января", "февраля", "марта", "апреля", "мая", "июня",
          "июля", "августа", "сентября", "октября", "ноября", "декабря"]

CARD_URL = "https://www.e1.ru/afisha/concert/affinazh-id16141586/"
LIST_URL = "https://www.e1.ru/afisha/"


def _is_event_card_url(href, base_url):
    full = urljoin(base_url, href)
    parsed = urlparse(full)
    base = urlparse(base_url)
    if parsed.netloc != base.netloc:
        return False, full
    if "/afisha/" not in parsed.path:
        return False, full
    if re.search(r"-id\d+", parsed.path):
        return True, full
    return False, full


def _extract_from_link(a, base_url):
    """Поля ТОЛЬКО внутри конкретного <a>. Дату ищем по названию месяца,
    не по любому русскому слову. Год не подставляем."""
    href = a.get("href", "").strip()
    ok, full = _is_event_card_url(href, base_url)
    if not ok:
        return None

    link_text = a.get_text(separator=" ", strip=True)
    source = "link_text"

    date_raw = None
    time_raw = None
    age = None
    genre = None

    # дата: «N месяц» — число + одно из названий месяцев, год НЕ добавляем
    m_date = re.search(r"(\d{1,2}\s+(?:" + "|".join(MONTHS) + r"))", link_text)
    if m_date:
        date_raw = m_date.group(1)

    m_time = re.search(r"(\d{1,2}:\d{2})", link_text)
    if m_time:
        time_raw = m_time.group(1)

    m_age = re.search(r"(\d{1,2}\+)\s*•", link_text)
    if m_age:
        age = m_age.group(1)

    m_genre = re.search(r"•\s*([^•]+)$", link_text)
    if m_genre:
        genre = m_genre.group(1).strip()

    # название: всё до даты (если дата найдена)
    name = link_text
    if date_raw:
        idx = link_text.find(date_raw)
        if idx > 0:
            name = link_text[:idx].strip()
    name = name or None

    return {
        "name": name,
        "date_raw": date_raw,      # без года
        "date_full": None,         # null, пока не подтверждено
        "time": time_raw,
        "age": age,
        "genre": genre,
        "url": full,
        "link_text": link_text,
        "source": source,
    }


def _stage_list(params):
    resp = requests.get(LIST_URL, timeout=(4.0, 6.0),
                        headers={"User-Agent": "Mozilla/5.0 (compatible; Salebot test)"})
    resp.raise_for_status()
    soup = BeautifulSoup(resp.content, "html.parser")
    final_url = resp.url

    candidates = []
    seen = set()
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href in seen:
            continue
        card = _extract_from_link(a, final_url)
        if card:
            seen.add(href)
            candidates.append(card)

    total_found = len(candidates)
    returned = candidates[:5]

    return {
        "ok": True,
        "status": resp.status_code,
        "final_url": final_url,
        "stage": "list",
        "candidates_total": total_found,
        "candidates_returned": len(returned),
        "extraction_ok": total_found > 0,   # не безусловно
        "candidates": returned,
        # происхождение: кандидаты собраны со всей страницы афиши;
        # блок, из которого они взяты, в коде не зафиксирован
        "section": "whole page; originating block not fixed in code",
    }


def _stage_card(params):
    resp = requests.get(CARD_URL, timeout=(4.0, 6.0),
                        headers={"User-Agent": "Mozilla/5.0 (compatible; Salebot test)"})
    resp.raise_for_status()
    soup = BeautifulSoup(resp.content, "html.parser")
    final_url = resp.url

    title = soup.title.get_text(strip=True) if soup.title else None
    h1_tag = soup.find("h1")
    h1 = h1_tag.get_text(strip=True) if h1_tag is not None else None

    # структурированные данные — если есть, сохраняем структуру целиком
    ld_objects = []
    for ld in soup.find_all("script", type="application/ld+json"):
        try:
            ld_objects.append(json.loads(ld.get_text()))
        except Exception:
            pass

    # короткий фрагмент текста ВОКРУГ названия/расписания/площадки,
    # если такой фрагмент найден (не первые 600 символов навигации)
    for tag in soup(["script", "style"]):
        tag.decompose()
    text = soup.get_text(separator=" ", strip=True)

    # ищем фрагмент около названия события из title/h1
    probe = None
    target = None
    for cand in (h1, title):
        if cand:
            # берём первое вхождение в тексте и окно вокруг него
            idx = text.find(cand)
            if idx != -1:
                target = cand
                probe = text[max(0, idx - 150): idx + 250]
                break
    if probe is None:
        # если названия в тексте нет — короткий фрагмент середины текста
        mid = len(text) // 2
        probe = text[mid: mid + 400]

    return {
        "ok": True,
        "status": resp.status_code,
        "final_url": final_url,
        "stage": "card",
        "title": title,
        "h1": h1,
        "ld_objects": ld_objects,          # структура сохранена, связи не сплющивались
        "text_fragment_around_name": probe,
        "session_date": None,               # не подтверждено — null
        "session_time": None,
        "price": None,
        "address": None,
        "venue": None,
        "event_verified": False,
        # source для полей: где они найдены (здесь — из ld_objects, если разобрано,
        # иначе null). Связываем только с конкретным объектом.
        "fields_source": "ld_objects (structure kept) — to be read per object",
    }


def handle(data):
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

        stage = params.get("stage")

        if stage == "list":
            result = _stage_list(params)
        elif stage == "card":
            result = _stage_card(params)
        else:
            return json.dumps(
                {"ok": False,
                 "error": "unknown stage: {}".format(stage),
                 "expected": ["list", "card"]},
                ensure_ascii=False,
            )

        return json.dumps(result, ensure_ascii=False)

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
