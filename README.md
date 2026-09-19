# Revit Knowledge MCP

Единый stdio MCP-сервер, реализующий разные варианты поиска:

- **Семантический поиск** по векторным коллекциям Qdrant
  (Revit API docs, SDK samples, pyRevit, Navisworks, Archicad).
- **Поиск и чтение доков** — доступ к живой официальной документации Revit API
  (rvtdocs.com): поиск сущностей и получение полных страниц в markdown.

Два уровня доступа:

1. **Широта (семантика):** `search_knowledge`, `research`.
2. **Точность (доки):** `lookup_api`, `get_api_doc`.

## Tools

| Tool | Назначение |
|------|-----------|
| `search_knowledge` | Семантический поиск по коллекциям Qdrant. Естественный язык. |
| `lookup_api` | Поиск сущностей Revit API в индексе rvtdocs.com (класс, метод, свойство, событие, enum, ctor). |
| `get_api_doc` | Полная страница документации в markdown по slug/URL (description, remarks, hierarchy, syntax, examples, member-таблицы). |
| `list_collections` | Список коллекций Qdrant с количеством точек. |
| `check_collection` | Проверка одной коллекции и её размера. |
| `research` | Композит: семантический поиск → извлечение сущностей Revit → подтягивание официальных доков. |

## Архитектура

```
revit_knowledge_mcp/
  server.py            # сборка FastMCP, регистрация тулов, stdio
  config.py            # config.yaml + переопределения через env
  registry.py          # каталог коллекций (platform, description)
  embeddings.py        # bge-m3: Ollama (local) / OpenAI-совместимый (cloud)
  ranking.py           # RRF для кросс-бэкендного ранжирования
  deps.py
  backends/
    qdrant_backend.py  # семантический поиск (research_server)
    rvtdocs_backend.py # живой поиск и страницы (Rvt_Docs_MCP)
    openai_backend.py  # опциональный OpenAI vector store
  sources/
    rvtdocs.py         # клиент /search/v2/api/ и страниц
    html_to_md.py      # структурный HTML→markdown парсер
  tools/               # knowledge, api_docs, collections, research
```

Ключевые решения:

- Бэкенды за общим интерфейсом `SearchBackend`; семантические результаты
  (Qdrant + OpenAI) сливаются через RRF, т.к. их score несопоставимы.
- Коллекции проиндексированы моделью `bge-m3` (1024d). Модель эмбеддингов
  фиксирована в каталоге коллекций, иначе запрос несовместим с базой.
- Парсер доков **структурный** (классы/заголовки), а не по HTML-комментариям:
  сайт rvtdocs.com был переработан (старый `/search/api/search` теперь 404,
  используется `/search/v2/api/` с обязательным `fields`).
- Живой доступ к докам — best-effort: ошибки возвращаются в поле `errors`,
  сервер продолжает работать.

## Требования

- Python 3.11+
- Qdrant (локально `127.0.0.1:6333` или remote)
- Ollama с моделью `bge-m3` (либо облачный OpenAI-совместимый провайдер)

```bash
pip install -r requirements.txt
```

## Конфигурация

Основной файл — `config.yaml` (или путь из `RKM_CONFIG`). Секреты — через env.

| Переменная | Назначение |
|-----------|-----------|
| `RKM_QDRANT_MODE` | `local` / `remote` |
| `RKM_QDRANT_HOST`, `RKM_QDRANT_PORT` | локальный Qdrant |
| `RKM_QDRANT_URL`, `RKM_QDRANT_API_KEY` | remote Qdrant |
| `RKM_EMBED_MODE` | `local` (Ollama) / `cloud` |
| `RKM_EMBED_MODEL` | модель эмбеддингов (по умолчанию `bge-m3`) |
| `RKM_OLLAMA_URL` | URL Ollama embeddings |
| `RKM_EMBED_API_URL`, `RKM_EMBED_API_KEY` (или `POLZA_API_KEY`) | облачные эмбеддинги |
| `OPENAI_API_KEY`, `OPENAI_VECTOR_STORE_ID` | опциональный OpenAI vector store |
| `RKM_DOCS_YEAR` | год Revit API для доков |
| `RKM_LOG_LEVEL` | уровень логирования |

## Запуск

```bash
python -m revit_knowledge_mcp
```

Логи пишутся в stderr (stdout занят MCP-протоколом).

### Регистрация в Kilo

```json
{
  "mcp": {
    "revit-knowledge": {
      "type": "local",
      "command": ["python", "-m", "revit_knowledge_mcp"],
      "environment": { "PYTHONPATH": "D:/DEV/revit_knowledge_mcp" },
      "enabled": true,
      "timeout": 120000
    }
  }
}
```

## Тесты

```bash
python -m pytest
```

## Замечания

- `lookup_api` рассчитан на короткие имена сущностей, не на фразы.
- Для коллекций-сэмплов без заголовка (`db_id` + `summary`) title строится из
  первого предложения summary.
- Языки code-блоков определяются по подписям вкладок (C#, VB, C++, F#,
  Python), т.к. сайт помечает все блоки как `language-cs`.
