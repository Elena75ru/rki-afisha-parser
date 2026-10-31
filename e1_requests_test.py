# -*- coding: utf-8 -*-
# e1_requests_test.py
# Один GET-запрос к https://www.e1.ru/afisha/ из исполнителя Salebot.
# Без SerpAPI, Jina, прокси, обхода ограничений, без токенов и персональных данных.
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


def handle(data):
    # Один запрос к фиксированному адресу
    url = "https://www.e1.ru/afisha/"

    try:
        try:
            params = json.loads(data) if data else {}
        except Exception as exc:
            params = {"_parse_error": "{}: {}".format(type(exc).__name__, exc)}

        if not (BS4_AVAILABLE and REQUESTS_AVAILABLE):
            return json.dumps(
                {
                    "ok": False,
                    "bs4_available": BS4_AVAILABLE,
                    "bs4_error": BS4_ERROR,
                    "requests_available": REQUESTS_AVAILABLE,
                    "requests_error": REQUESTS_ERROR,
                },
                ensure_ascii=False,
            )

        # Короткий таймаут: исполнитель ограничен ~15 секундами
        resp = requests.get(
            url,
            timeout=(4.0, 6.0),
            headers={"User-Agent": "Mozilla/5.0 (compatible; Salebot test)"},
        )
        resp.raise_for_status()

        body = resp.content  # исходные байты
        content_type = resp.headers.get("Content-Type")
        final_url = resp.url
        status = resp.status_code

        soup = BeautifulSoup(body, "html.parser")
        parser_encoding = soup.original_encoding

        title = soup.title.get_text(strip=True) if soup.title else None
        h1_tag = soup.find("h1")
        h1 = h1_tag.get_text(strip=True) if h1_tag is not None else None

        # До 10 заголовков h2/h3
        headings = []
        for tag in soup.find_all(["h2", "h3"])[:10]:
            txt = tag.get_text(strip=True)
            if txt:
                headings.append(txt)

        # До 5 ссылок на отдельные события (любой href, не только /afisha/)
        from urllib.parse import urljoin

        links = []
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if not href or href.startswith(("#", "javascript:", "mailto:")):
                continue
            text = a.get_text(strip=True)
            full = urljoin(final_url, href)
            links.append({"href": full, "text": text[:80]})
            if len(links) >= 5:
                break

        # Короткий фрагмент текста без script/style
        for tag in soup(["script", "style"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)
        text_fragment = text[:400]

        return json.dumps(
            {
                "ok": True,
                "status": status,
                "final_url": final_url,
                "body_bytes": len(body),
                "content_type": content_type,
                "parser_encoding": parser_encoding,
                "title": title,
                "h1": h1,
                "headings": headings,
                "links": links,
                "text_fragment": text_fragment,
            },
            ensure_ascii=False,
        )

    except Exception as exc:
        # Точная диагностика; не выдаём техническую ошибку за отсутствие событий
        return json.dumps(
            {
                "ok": False,
                "bs4_available": BS4_AVAILABLE,
                "requests_available": REQUESTS_AVAILABLE,
                "error": "{}: {}".format(type(exc).__name__, exc),
            },
            ensure_ascii=False,
        )
