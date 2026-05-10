from __future__ import annotations

import logging
from dataclasses import dataclass
from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)

#==================Chunking Configuration==================
@dataclass
class ChunkingConfig:
    chunk_size: int = 900
    chunk_overlap: int = 150

class TextChunker:
    def __init__(self, config: ChunkingConfig | None = None) -> None:

        self.config = config or ChunkingConfig()
        
        #==================Initialize Text Splitter==================
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.config.chunk_size,
            chunk_overlap=self.config.chunk_overlap,
            length_function=len,
            is_separator_regex=False,
            # separators=["\n\n", "\n", " ", ""]
        )


    def chunk_text(self,text: str) -> list[str]:
        logger.debug("chunk_text: input length=%s", len(text))
        normalized_text = " ".join(text.strip())
        
        #==================Handle Empty Text==================
        if not normalized_text:
            return []
        
        #==================Chunk Text==================
        return self.splitter.split_text(normalized_text)

