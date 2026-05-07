from __future__ import annotations

from typing import Any
from pathlib import Path

import requests
import feedparser
from dataclasses import dataclass
from src.config.settings import Settings
from src.ingestion.pdf_parser import PdfParser
from src.ingestion.chunker import TextChunker
from rich import print
from src.schemas.agent_schema import IngestRequest
from tenacity import retry, stop_after_attempt, wait_exponential

from datetime import datetime, timedelta, UTC

#==================Arxiv Paper==================
#contains the metadata and content of an Arxiv paper
ARXIV_API_URL: str = "http://export.arxiv.org/api/query"

@dataclass(frozen=True)
class ArxivPaper:
    paper_id: str
    title: str
    authors: list[str]
    summary: str
    source_url: str
    pdf_url: str
    published_at: datetime

class PdfDownloadError(Exception):
    pass

#==================Arxiv Ingestor==================
#ingests Arxiv papers into the vector database
class ArxivIngestor:

    def __init__(self,settings: Settings):
        self.settings = settings
        self.pdf_parser = PdfParser()
        self.text_chunker = TextChunker()

    async def fetch_arxiv_papers(self,request: IngestRequest)->list[ArxivPaper]:
        last_date  = datetime.now() - timedelta(days=request.days_back)  #last date to fetch papers from Arxiv(last n days)
        category_filter = f"cat:{request.category}"  #category filter for the papers like cs.AI

        params:dict[str,Any] = {
            "search_query": category_filter,
            "start": 0,
            "max_results": request.max_papers,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }

        response = requests.get(ARXIV_API_URL, params=params,timeout=30.0)
        print(response)
        response.raise_for_status()

        feed = feedparser.parse(response.text)

        papers:list[ArxivPaper] = []

        for entry in feed.entries:
            published_at: datetime = datetime(*entry.published_parsed[:6], tzinfo=UTC)
            if published_at < last_date:
                continue
            paper_id: str = entry.id.rsplit("/", maxsplit=1)[-1]
            pdf_url: str = next(link.href for link in entry.links if link.type == "application/pdf")
            papers.append(
                ArxivPaper(
                    paper_id=paper_id,
                    title=entry.title.strip(),
                    authors=[author.name for author in entry.authors],
                    summary=entry.summary.strip(),
                    published_at=published_at,
                    pdf_url=pdf_url,
                    source_url=entry.id,
                )
            )
        return papers

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def download_pdf(self,paper: ArxivPaper):
        pdf_dir: Path = Path(self.settings.raw_pdf_dir)
        pdf_dir.mkdir(parents=True, exist_ok=True)

        pdf_path: Path = pdf_dir / f"{paper.paper_id}.pdf"

        #if the pdf already exists, return the path
        if pdf_path.exists():
            return pdf_path
        
        try:
            response = requests.get(paper.pdf_url, timeout=60.0)
            response.raise_for_status()
        
            pdf_path.write_bytes(response.content)
            return pdf_path
        except Exception as e:
            raise PdfDownloadError(f"Error downloading PDF: {e}")


    
        










    def ingest_papers(self,request: IngestRequest):
        pass







