from io import BytesIO

import pandas as pd
from PyPDF2 import PdfReader
from docx import Document
import streamlit as st


SUPPORTED_TYPES = ["txt", "pdf", "docx", "xlsx", "csv"]


@st.cache_data(show_spinner=False)
def extract_file_text(file_name, file_bytes):
    """Extract readable text and optional tabular preview data from uploaded files."""
    file_type = file_name.split(".")[-1].lower()
    stream = BytesIO(file_bytes)
    preview_df = None

    if file_type == "txt":
        text = file_bytes.decode("utf-8", errors="replace")
    elif file_type == "pdf":
        reader = PdfReader(stream)
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    elif file_type == "docx":
        doc = Document(stream)
        text = "\n".join(paragraph.text for paragraph in doc.paragraphs)
    elif file_type == "xlsx":
        sheets = pd.read_excel(stream, sheet_name=None)
        parts = []
        for sheet_name, df in sheets.items():
            parts.append(f"Sheet: {sheet_name}\n{df.to_string(index=False)}")
        first_sheet = next(iter(sheets.values()), pd.DataFrame())
        preview_df = first_sheet.head(100)
        text = "\n\n".join(parts)
    elif file_type == "csv":
        df = pd.read_csv(stream)
        preview_df = df.head(100)
        text = df.to_string(index=False)
    else:
        raise ValueError(f"Unsupported file type: {file_type}")

    return {
        "name": file_name,
        "type": file_type,
        "text": text.strip(),
        "preview_df": preview_df,
        "size_kb": round(len(file_bytes) / 1024, 1),
    }
