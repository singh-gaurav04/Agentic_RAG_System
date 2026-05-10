from langchain_community.tools import DuckDuckGoSearchRun
import asyncio


class WebSearchTool:
    def __init__(self) -> None:
        self.search_client = DuckDuckGoSearchRun()
    async def search(self, query: str, max_results: int = 5) -> list[str]:
        return await asyncio.to_thread(self.search_client.run, query, max_results=max_results)