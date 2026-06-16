"""DuckDuckGo Search (ddgs) в Haystack."""

from __future__ import annotations

import sys

from ddgs import DDGS
from haystack import Pipeline, component
from haystack.dataclasses import Document


@component
class DuckDuckGoSearch:
    """Компонент Haystack для веб-поиска через DuckDuckGo (ddgs)."""

    def __init__(self, max_results: int = 5) -> None:
        self.max_results = max(1, min(max_results, 10))

    @component.output_types(documents=list[Document], links=list[str])
    def run(self, query: str) -> dict[str, list]:
        documents: list[Document] = []
        links: list[str] = []

        with DDGS() as ddgs:
            for item in ddgs.text(query, max_results=self.max_results):
                title = item.get("title", "")
                url = item.get("href", "")
                snippet = item.get("body", "")
                documents.append(
                    Document(
                        content=f"{title}\n{snippet}".strip(),
                        meta={"title": title, "url": url},
                    )
                )
                if url:
                    links.append(url)

        return {"documents": documents, "links": links}


def main() -> None:
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "haystack deepset RAG"
    pipeline = Pipeline()
    pipeline.add_component("duckduckgo", DuckDuckGoSearch(max_results=5))
    result = pipeline.run({"duckduckgo": {"query": query}})

    documents = result["duckduckgo"]["documents"]
    links = result["duckduckgo"]["links"]

    print(f"\nЗапрос: {query}")
    print(f"Найдено: {len(documents)} документов\n")

    for index, doc in enumerate(documents, start=1):
        title = doc.meta.get("title", "Без названия")
        url = doc.meta.get("url", "")
        snippet = doc.content.split("\n", 1)[-1]
        print(f"{index}. {title}")
        print(f"   URL: {url}")
        if snippet:
            print(f"   {snippet[:200]}")
        print()

    print("Ссылки:")
    for link in links:
        print(f"  - {link}")


if __name__ == "__main__":
    main()
