# -*- coding: utf-8 -*-
# e1_event_probe.py (исправленная диагностическая версия)
# Исследование разметки карточек событий https://www.e1.ru/afisha/
# через BeautifulSoup в исполнителе Salebot.
# Без формирования подтверждённого события: только кандидаты и их контейнеры.
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


def _is_event_card_url(href, base_url):
    """Ссылка считается карточкой события, только если после urljoin
    домен совпадает и путь имеет вид /afisha/...-id<число>.
    Это ограниченный признак для первого теста, не универсальное правило."""
    full = urljoin(base_url, href)
    parsed = urlparse(full)
    base = urlparse(base_url)
    # домен совпадает с базовым
    if parsed.netloc != base.netloc:
        return False, full
    # путь /afisha/... с суффиксом -id<число> в конце сегмента
    if "/afisha/" not in parsed.path:
        return False, full
    if re.search(r"-id\d+", parsed.path):
        return True, full
    return False, full


def _container_info(container, base_url):
    """Тег, классы, текст и число разных ссылок-кандидатов внутри контейнера."""
    classes = container.get("class") or []
    tag = container.name
    text = container.get_text(separator=" ", strip=True)
    # считаем разные ссылки-кандидаты на события внутри контейнера
    cand_hrefs = set()
    for a in container.find_all("a", href=True):
        ok, _ = _is_event_card_url(a["href"], base_url)
        if ok:
            cand_hrefs.add(a["href"])
    return {
        "tag": tag,
        "classes": classes,
        "text": text[:300],
        "distinct_event_candidate_links": len(cand_hrefs),
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

        soup = BeautifulSoup(resp.content, "html.parser")
        status = resp.status_code
        final_url = resp.url

        # Кандидаты: ТОЛЬКО ссылки вида /afisha/...-id<число>, не разделы меню
        candidates = []
        seen = set()
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if not href or href in seen:
                continue
            ok, full = _is_event_card_url(href, final_url)
            if ok:
                seen.add(href)
                candidates.append((a, full))

        if not candidates:
            return json.dumps(
                {
                    "ok": True,
                    "status": status,
                    "final_url": final_url,
                    "event_verified": False,
                    "candidates_found": 0,
                    "candidates": [],
                    "note": "no event-card candidates (-id<number>) found on this page",
                },
                ensure_ascii=False,
            )

        # До трёх кандидатов: текст ссылки, URL, фрагменты ссылки и ближайших контейнеров
        result_candidates = []
        for a, full in candidates[:3]:
            link_text = a.get_text(strip=True)
            link_fragment = str(a)[:400]

            # ближайшие родительские контейнеры (по возрастанию глубины)
            containers = []
            current = a
            for _ in range(4):  # ограниченно, без безусловного подъёма на 6
                parent = current.parent
                if parent is None or parent.name in ("html", "body"):
                    break
                containers.append(_container_info(parent, final_url))
                current = parent

            result_candidates.append(
                {
                    "link_text": link_text or None,
                    "url": full,
                    "link_fragment": link_fragment,
                    "containers": containers,
                }
            )

        return json.dumps(
            {
                "ok": True,
                "status": status,
                "final_url": final_url,
                "event_verified": False,
                "candidates_found": len(candidates),
                "candidates": result_candidates,
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
