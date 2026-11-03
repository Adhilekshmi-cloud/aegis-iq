"""HTML document extractor using BeautifulSoup for Aegis Knowledge System."""

import logging
from pathlib import Path
from typing import Any, Dict, List

from bs4 import BeautifulSoup

from app.ingestion.registry import ExtractionResult

logger = logging.getLogger(__name__)


class HTMLExtractor:
    """Extracts structured text, tables, headings, and metadata from HTML files."""

    def can_handle(self, file_path: Path) -> bool:
        """Check if file has an HTML extension."""
        return file_path.suffix.lower() in (".html", ".htm", ".xhtml")

    async def extract(self, file_path: Path) -> ExtractionResult:
        """Extract content from an HTML document.

        Args:
            file_path: Path to HTML file.

        Returns:
            ExtractionResult instance.
        """
        if not file_path.exists():
            return ExtractionResult(
                text="",
                confidence=0.0,
                errors=[f"File does not exist: {file_path}"],
            )

        try:
            content_bytes = file_path.read_bytes()
            # Try utf-8 first, fallback to latin-1
            try:
                html_text = content_bytes.decode("utf-8")
            except UnicodeDecodeError:
                html_text = content_bytes.decode("latin-1", errors="replace")

            soup = BeautifulSoup(html_text, "html.parser")
        except Exception as exc:
            logger.error("Failed to parse HTML %s: %s", file_path.name, exc)
            return ExtractionResult(
                text="",
                confidence=0.0,
                errors=[f"Failed to parse HTML: {str(exc)}"],
            )

        # 1. Extract metadata from <meta> and <title> tags
        metadata: Dict[str, Any] = {
            "filename": file_path.name,
            "title": file_path.stem.replace("_", " ").title(),
        }

        title_tag = soup.find("title")
        if title_tag and title_tag.string:
            metadata["title"] = title_tag.string.strip()

        for meta in soup.find_all("meta"):
            name = meta.get("name") or meta.get("property")
            content = meta.get("content")
            if name and content:
                key = name.lower().replace(":", "_").replace("-", "_")
                metadata[key] = content.strip()

        # 2. Extract tables before stripping tags
        tables: List[Dict[str, Any]] = []
        for tbl_tag in soup.find_all("table"):
            headers: List[str] = []
            th_tags = tbl_tag.find_all("th")
            if th_tags:
                headers = [th.get_text(separator=" ", strip=True) for th in th_tags]

            rows: List[List[str]] = []
            tr_tags = tbl_tag.find_all("tr")
            for tr in tr_tags:
                td_tags = tr.find_all("td")
                if td_tags:
                    row_data = [td.get_text(separator=" ", strip=True) for td in td_tags]
                    # If no th tags were found earlier, treat the first row of td's as headers if plausible
                    if not headers and len(rows) == 0:
                        headers = row_data
                    else:
                        rows.append(row_data)

            if headers and rows:
                tables.append({"headers": headers, "rows": rows})

        # 3. Extract sections by headings (h1 - h6)
        sections: List[Dict[str, Any]] = []
        for heading_tag in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
            h_text = heading_tag.get_text(strip=True)
            # Find sibling text until next heading
            content_nodes = []
            for sibling in heading_tag.next_siblings:
                if sibling.name in ["h1", "h2", "h3", "h4", "h5", "h6"]:
                    break
                if hasattr(sibling, "get_text"):
                    s_text = sibling.get_text(separator=" ", strip=True)
                    if s_text:
                        content_nodes.append(s_text)
                elif isinstance(sibling, str):
                    s_str = sibling.strip()
                    if s_str:
                        content_nodes.append(s_str)

            sec_content = "\n".join(content_nodes).strip()
            if h_text:
                sections.append({
                    "heading": h_text,
                    "content": sec_content,
                    "page": 1,
                })

        # 4. Remove scripts, styles, noscript, nav, footer
        for tag in soup(["script", "style", "noscript", "nav", "footer", "header"]):
            tag.decompose()

        # 5. Extract cleaned text
        body = soup.find("body") or soup
        text_lines = []
        for element in body.descendants:
            if element.name in ["p", "div", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6"]:
                elem_text = element.get_text(separator=" ", strip=True)
                if elem_text and (not text_lines or text_lines[-1] != elem_text):
                    text_lines.append(elem_text)

        full_text = "\n\n".join(text_lines)
        if not full_text:
            full_text = soup.get_text(separator="\n\n", strip=True)

        return ExtractionResult(
            text=full_text,
            tables=tables,
            metadata=metadata,
            sections=sections,
            images=[],
            extraction_method="beautifulsoup",
            confidence=0.95,
            errors=[],
            page_count=1,
            raw_content=full_text,
        )
