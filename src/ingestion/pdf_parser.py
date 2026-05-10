from __future__ import annotations

import logging
from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader

logger = logging.getLogger(__name__)


class PdfParserError(Exception):
    pass

#==================Document Loader==================
#loads the document pages into a list of strings(per page)
class Documentloader:

    def load_document_pages(self,pdf_path: Path) -> list[str]:
        #==================Load Document Pages==================
        try:
            loader = PyPDFLoader(str(pdf_path))
            documents = loader.load()
            page_texts: list[str] = [document.page_content for document in documents]
            if not page_texts:
                raise PdfParserError("No pages found in the document")
            return page_texts
        except Exception as e:
            logger.warning("load_document_pages failed for %s: %s", pdf_path, e)
            raise PdfParserError(f"Error loading document pages: {e}")
    

#==================PDF Parser==================
#combines all the pages into a single string
class PdfParser:
    def __init__(self,document_loader: Documentloader | None = None):
        self.document_loader = document_loader


    def parse_pdf(self,pdf_path: Path) -> str:
        try:
            logger.debug("parse_pdf: loading %s", pdf_path)
            pages_text:list[str] = self.document_loader.load_document_pages(pdf_path)
            text = " ".join(pages_text)

            if not text:
                raise PdfParserError("No text found in the document")
            return text
        except Exception as e:
                raise PdfParserError(f"Error parsing PDF: {e}")
