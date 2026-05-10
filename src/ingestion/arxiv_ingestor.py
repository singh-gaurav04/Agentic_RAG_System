from __future__ import annotations

from typing import Any
from pathlib import Path
import logging
import requests
import feedparser
from dataclasses import dataclass
from src.config.settings import Settings
from src.ingestion.pdf_parser import PdfParser
from src.ingestion.chunker import TextChunker
from src.schemas.agent_schema import IngestRequest, IngestResponse, DocumentMetadata
from tenacity import retry, stop_after_attempt, wait_exponential
from src.retrieval.vector_store import VectorStore, EmbeddedChunk
from datetime import datetime, timedelta, UTC
from src.ingestion.pdf_parser import PdfParserError
from src.ingestion.pdf_parser import Documentloader

logger = logging.getLogger(__name__)

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
class ArxivFetchError(Exception):
    pass

#==================Arxiv Ingestor==================
#ingests Arxiv papers into the vector database
class ArxivIngestor:

    def __init__(self,settings: Settings,vector_store: VectorStore):
        self.settings = settings
        self.pdf_parser = PdfParser(Documentloader())
        self.text_chunker = TextChunker()
        self.vector_store = vector_store

    async def fetch_arxiv_papers(self,request: IngestRequest)->list[ArxivPaper]:
        last_date: datetime = datetime.now(UTC) - timedelta(days=request.days_back)  #last date to fetch papers from Arxiv(last n days)
        category_filter = f"cat:{request.category}"  #category filter for the papers like cs.AI

        params:dict[str,Any] = {
            "search_query": category_filter,
            "start": 0,
            "max_results": request.max_papers,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }

        try:
            response = requests.get(ARXIV_API_URL, params=params,timeout=30.0)
            response.raise_for_status()
        except requests.exceptions.RequestException as err:
            raise ArxivFetchError(f"Failed to fetch arXiv feed: {err}") from err

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
        logger.debug("download_pdf: %s", paper.pdf_url)
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

    async def ingest_paper(self, request: IngestRequest) -> IngestResponse:
        try:
            papers: list[ArxivPaper] = await self.fetch_arxiv_papers(request)
        except ArxivFetchError as err:
            return IngestResponse(
                requested=request.max_papers,
                indexed=0,
                skipped_duplicates=0,
                failed=1,
                failures=[str(err)],
            )
        indexed: int = 0
        skipped_duplicates: int = 0
        failed: int = 0
        failures: list[str] = []
        for start_index in range(0, len(papers), request.batch_size):
            batch: list[ArxivPaper] = papers[start_index : start_index + request.batch_size]
            logger.debug(
                "ingest batch papers=%s",
                [p.paper_id for p in batch],
            )
            for paper in batch:
                try:
                    if self.vector_store.has_paper(paper.paper_id):
                        skipped_duplicates += 1
                        continue
                    chunks: list[EmbeddedChunk] = await self.prepare_chunks_for_paper(paper)
                    logger.info("Indexed paper %s (%s chunks)", paper.paper_id, len(chunks))
                    self.vector_store.upsert(chunks)
                    indexed += 1
                except Exception as err:
                    failed += 1
                    failures.append(f"{paper.paper_id}: {err}")
        return IngestResponse(
            requested=request.max_papers,
            indexed=indexed,
            skipped_duplicates=skipped_duplicates,
            failed=failed,
            failures=failures,
        )
    
    async def prepare_chunks_for_paper(self, paper: ArxivPaper) -> list[EmbeddedChunk]:
        pdf_path: Path = await self.download_pdf(paper)
        try:
            full_text: str = self.pdf_parser.parse_pdf(pdf_path)
            logger.debug("prepare_chunks_for_paper: parsed PDF %s", paper.paper_id)
        except PdfParserError:
            full_text = paper.abstract

        chunks: list[str] = self.text_chunker.chunk_text(full_text)
        embedded_chunks: list[EmbeddedChunk] = []
        for chunk_index, chunk in enumerate(chunks):
            metadata: DocumentMetadata = DocumentMetadata(
                paper_id=paper.paper_id,
                title=paper.title,
                authors=paper.authors,
                abstract=paper.summary,
                section="unknown",
                source_url=paper.source_url,
                published_at=paper.published_at,
                chunk_index=chunk_index,
            )
            embedded_chunks.append(
                EmbeddedChunk(
                    id=f"{paper.paper_id}-{chunk_index}",
                    text=chunk,
                    metadata=metadata.model_dump(mode="json"),
                )
            )
        logger.debug(
            "prepare_chunks_for_paper: built %s embedded chunks for %s",
            len(embedded_chunks),
            paper.paper_id,
        )
        return embedded_chunks






