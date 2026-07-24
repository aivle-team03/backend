import os
from typing import Optional


def extract_text_from_file(file_path: str, raw_content: Optional[bytes] = None) -> str:
    """
    업로드된 파일(PDF, PPTX, TXT)에서 텍스트를 추출하는 파서 함수
    """
    ext = os.path.splitext(file_path)[1].lower()

    # 1. TXT 파일 파싱
    if ext == ".txt":
        if raw_content:
            try:
                return raw_content.decode("utf-8")
            except UnicodeDecodeError:
                return raw_content.decode("euc-kr", errors="ignore")
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()

    # 2. PDF 파일 파싱 (pdfplumber 또는 pypdf 시도)
    elif ext == ".pdf":
        try:
            import pdfplumber
            text_chunks = []
            with pdfplumber.open(file_path if os.path.exists(file_path) else raw_content) as pdf:
                for page in pdf.pages:
                    txt = page.extract_text()
                    if txt:
                        text_chunks.append(txt)
            if text_chunks:
                return "\n\n".join(text_chunks)
        except Exception:
            pass

        try:
            from pypdf import PdfReader
            reader = PdfReader(file_path)
            text_chunks = [page.extract_text() for page in reader.pages if page.extract_text()]
            if text_chunks:
                return "\n\n".join(text_chunks)
        except Exception:
            pass

    # 3. PPTX 파일 파싱 (python-pptx 시도)
    elif ext in [".pptx", ".ppt"]:
        try:
            from pptx import Presentation
            prs = Presentation(file_path)
            text_chunks = []
            for slide in prs.slides:
                for shape in slide.shapes:
                    if hasattr(shape, "text") and shape.text:
                        text_chunks.append(shape.text)
            if text_chunks:
                return "\n\n".join(text_chunks)
        except Exception:
            pass

    # Fallback: 파일 텍스트 추출이 어렵거나 시도 실패 시 전달된 본문 또는 파일명 활용
    if raw_content:
        try:
            return raw_content.decode("utf-8", errors="ignore")
        except Exception:
            pass

    return f"산업안전보건 수칙 교육 자료 ({os.path.basename(file_path)})"
