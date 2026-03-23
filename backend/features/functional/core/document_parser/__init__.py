"""
Document Parser Module
"""
from abc import ABC, abstractmethod
from typing import Optional
from pathlib import Path
from fastapi import UploadFile


class BaseDocumentParser(ABC):
    """Abstract base class for document parsers."""
    
    @abstractmethod
    async def parse(self, file: UploadFile) -> str:
        """Parse document and return text content."""
        pass


class PDFParser(BaseDocumentParser):
    """PDF document parser."""
    
    async def parse(self, file: UploadFile) -> str:
        """Parse PDF document."""
        try:
            from PyPDF2 import PdfReader
            import io
            
            content = await file.read()
            await file.seek(0)  # Reset file position
            
            pdf = PdfReader(io.BytesIO(content))
            text_parts = []
            
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)
            
            return "\n\n".join(text_parts)
        except Exception as e:
            return f"Error parsing PDF: {str(e)}"


class WordParser(BaseDocumentParser):
    """Word document parser."""
    
    async def parse(self, file: UploadFile) -> str:
        """Parse Word document."""
        try:
            from docx import Document
            import io
            
            content = await file.read()
            await file.seek(0)
            
            doc = Document(io.BytesIO(content))
            text_parts = []
            
            for para in doc.paragraphs:
                if para.text.strip():
                    text_parts.append(para.text)
            
            return "\n\n".join(text_parts)
        except Exception as e:
            return f"Error parsing Word document: {str(e)}"


class MarkdownParser(BaseDocumentParser):
    """Markdown document parser."""
    
    async def parse(self, file: UploadFile) -> str:
        """Parse Markdown document - just return as-is."""
        content = await file.read()
        await file.seek(0)
        return content.decode('utf-8')


class TextParser(BaseDocumentParser):
    """Plain text parser."""
    
    async def parse(self, file: UploadFile) -> str:
        """Parse plain text document."""
        content = await file.read()
        await file.seek(0)
        return content.decode('utf-8')


def get_document_parser(filename: str) -> BaseDocumentParser:
    """Get appropriate parser based on file extension."""
    ext = Path(filename).suffix.lower()
    
    parsers = {
        '.pdf': PDFParser(),
        '.docx': WordParser(),
        '.doc': WordParser(),
        '.md': MarkdownParser(),
        '.txt': TextParser(),
    }
    
    return parsers.get(ext, TextParser())
