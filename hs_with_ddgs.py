from haystack import Pipeline

from duckduckgo import DuckDuckGoSearch

pipeline = Pipeline()
pipeline.add_component("websearch", DuckDuckGoSearch(max_results=3))

results = pipeline.run({"websearch": {"query": "Что такое frico?"}})

documents = results["websearch"]["documents"]
links = results["websearch"]["links"]

print("Найденные документы:")
for doc in documents:
    print(f"Контент: {doc.content}")

print("\nСсылки:")
for link in links:
    print(link)
