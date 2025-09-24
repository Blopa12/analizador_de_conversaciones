"""
Content extraction and parsing module for conversations, tickets, and suggestions
"""

from typing import Dict, List, Any, Optional, Tuple
import re
import pandas as pd
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ContentItem:
    """Represents a single content item (conversation, ticket, suggestion)"""
    id: str
    content_type: str  # 'conversation', 'ticket', 'suggestion'
    content: str
    metadata: Dict[str, Any]
    source_file: str
    timestamp: Optional[datetime] = None
    customer_id: Optional[str] = None


class ContentExtractor:
    """Extracts and parses individual content items from structured data"""

    def __init__(self):
        self.extraction_strategies = {
            'excel': self._extract_from_excel,
            'csv': self._extract_from_excel,  # CSV uses same logic as Excel
            'docx': self._extract_from_docx,
            'pdf': self._extract_from_pdf
        }

    def extract_content_items(
        self,
        processed_file: Dict[str, Any],
        structure_analysis: Dict[str, Any]
    ) -> List[ContentItem]:
        """
        Extract individual content items from processed file data

        Args:
            processed_file: Output from FileProcessor.process_file()
            structure_analysis: Output from DataStructureAnalyzer.analyze_structure()

        Returns:
            List of ContentItem objects
        """
        file_type = processed_file['file_type']
        extractor_func = self.extraction_strategies.get(file_type)

        if not extractor_func:
            raise ValueError(f"No extraction strategy for file type: {file_type}")

        return extractor_func(processed_file, structure_analysis)

    def _extract_from_excel(
        self,
        processed_file: Dict[str, Any],
        structure_analysis: Dict[str, Any]
    ) -> List[ContentItem]:
        """Extract content items from Excel files"""
        items = []
        raw_data = processed_file['raw_data']
        file_name = processed_file['metadata']['file_name']

        for sheet_name, df in raw_data.items():
            if df.empty:
                continue

            sheet_analysis = structure_analysis['sheets'][sheet_name]
            id_columns = sheet_analysis['potential_id_columns']
            content_columns = sheet_analysis['potential_content_columns']

            # If no specific columns identified, use heuristics
            if not id_columns:
                id_columns = self._find_id_columns_heuristic(df)
            if not content_columns:
                content_columns = self._find_content_columns_heuristic(df)

            for index, row in df.iterrows():
                try:
                    # Generate item ID
                    item_id = self._generate_item_id(row, id_columns, index)

                    # Extract content
                    content = self._extract_content_from_row(row, content_columns)

                    if not content:
                        continue

                    # Determine content type
                    content_type = self._determine_content_type(content, row)

                    # Extract metadata
                    metadata = {
                        'sheet': sheet_name,
                        'row_index': index,
                        'all_columns': row.to_dict()
                    }

                    # Try to extract customer information
                    customer_id = self._extract_customer_id(row)

                    # Try to extract timestamp
                    timestamp = self._extract_timestamp(row)

                    item = ContentItem(
                        id=item_id,
                        content_type=content_type,
                        content=content,
                        metadata=metadata,
                        source_file=file_name,
                        timestamp=timestamp,
                        customer_id=customer_id
                    )

                    items.append(item)

                except Exception as e:
                    print(f"Warning: Error processing row {index} in sheet {sheet_name}: {str(e)}")
                    continue

        return items

    def _extract_from_docx(
        self,
        processed_file: Dict[str, Any],
        structure_analysis: Dict[str, Any]
    ) -> List[ContentItem]:
        """Extract content items from Word documents"""
        items = []
        raw_data = processed_file['raw_data']
        file_name = processed_file['metadata']['file_name']

        # Process paragraphs
        current_item = None
        item_counter = 1

        for i, paragraph in enumerate(raw_data['paragraphs']):
            # Check if this paragraph starts a new item
            if self._is_new_item_marker(paragraph):
                # Save previous item if exists
                if current_item:
                    items.append(current_item)

                # Start new item
                item_id = self._extract_id_from_text(paragraph) or f"doc_item_{item_counter}"
                content_type = self._determine_content_type_from_text(paragraph)

                current_item = ContentItem(
                    id=item_id,
                    content_type=content_type,
                    content=paragraph,
                    metadata={'paragraph_start': i, 'source': 'paragraph'},
                    source_file=file_name
                )
                item_counter += 1
            elif current_item:
                # Add to existing item
                current_item.content += "\n" + paragraph
            else:
                # No current item, create one for orphaned content
                item_id = f"doc_item_{item_counter}"
                current_item = ContentItem(
                    id=item_id,
                    content_type='suggestion',  # Default type
                    content=paragraph,
                    metadata={'paragraph_start': i, 'source': 'paragraph'},
                    source_file=file_name
                )
                item_counter += 1

        # Don't forget the last item
        if current_item:
            items.append(current_item)

        # Process tables if any
        for table_idx, table in enumerate(raw_data['tables']):
            if not table or len(table) < 2:  # Skip empty tables or tables with only headers
                continue

            headers = table[0]
            for row_idx, row in enumerate(table[1:], 1):
                if len(row) != len(headers):
                    continue

                row_data = dict(zip(headers, row))
                content = self._extract_content_from_dict(row_data)

                if content:
                    item_id = f"table_{table_idx}_row_{row_idx}"
                    items.append(ContentItem(
                        id=item_id,
                        content_type='conversation',  # Assume tables contain conversations
                        content=content,
                        metadata={'table_index': table_idx, 'row_index': row_idx, 'source': 'table'},
                        source_file=file_name
                    ))

        return items

    def _extract_from_pdf(
        self,
        processed_file: Dict[str, Any],
        structure_analysis: Dict[str, Any]
    ) -> List[ContentItem]:
        """Extract content items from PDF files"""
        items = []
        raw_data = processed_file['raw_data']
        file_name = processed_file['metadata']['file_name']

        for page_data in raw_data:
            page_num = page_data['page']
            content = page_data['content']

            # Split content by potential separators
            sections = self._split_pdf_content(content)

            for i, section in enumerate(sections):
                if not section.strip():
                    continue

                item_id = f"pdf_page_{page_num}_section_{i+1}"
                content_type = self._determine_content_type_from_text(section)

                items.append(ContentItem(
                    id=item_id,
                    content_type=content_type,
                    content=section.strip(),
                    metadata={'page': page_num, 'section': i+1, 'source': 'pdf'},
                    source_file=file_name
                ))

        return items

    def _find_id_columns_heuristic(self, df: pd.DataFrame) -> List[str]:
        """Find potential ID columns using heuristics"""
        id_columns = []

        for col in df.columns:
            col_lower = str(col).lower()
            col_data = df[col].astype(str)

            # Check column name
            if any(keyword in col_lower for keyword in ['id', 'identifier', 'ticket', 'numero', 'folio', 'case']):
                id_columns.append(col)
            # Check if values look like IDs (numbers, alphanumeric codes)
            elif col_data.str.match(r'^[A-Za-z0-9-_]+$').all() and col_data.nunique() > len(df) * 0.8:
                id_columns.append(col)

        return id_columns

    def _find_content_columns_heuristic(self, df: pd.DataFrame) -> List[str]:
        """Find potential content columns using heuristics"""
        content_columns = []

        for col in df.columns:
            col_lower = str(col).lower()
            col_data = df[col].astype(str)

            # Check column name
            if any(keyword in col_lower for keyword in [
                'content', 'message', 'description', 'comment', 'text', 'body',
                'contenido', 'mensaje', 'descripcion', 'comentario', 'texto'
            ]):
                content_columns.append(col)
            # Check if values are long text (average length > 50 characters)
            elif col_data.str.len().mean() > 50:
                content_columns.append(col)

        return content_columns

    def _generate_item_id(self, row: pd.Series, id_columns: List[str], fallback_index: int) -> str:
        """Generate a unique ID for the content item"""
        if id_columns:
            # Use first available ID column
            for col in id_columns:
                if pd.notna(row[col]) and str(row[col]).strip():
                    return str(row[col])

        # Fallback to row index
        return f"item_{fallback_index}"

    def _extract_content_from_row(self, row: pd.Series, content_columns: List[str]) -> str:
        """Extract content from a pandas row"""
        content_parts = []

        if content_columns:
            for col in content_columns:
                if pd.notna(row[col]) and str(row[col]).strip():
                    content_parts.append(str(row[col]).strip())
        else:
            # Use all non-null string columns with reasonable length
            for col, value in row.items():
                if pd.notna(value) and isinstance(value, str) and len(value.strip()) > 10:
                    content_parts.append(value.strip())

        return " | ".join(content_parts)

    def _extract_content_from_dict(self, row_data: Dict[str, str]) -> str:
        """Extract content from a dictionary (table row)"""
        content_parts = []

        for key, value in row_data.items():
            if value and len(value.strip()) > 10:
                content_parts.append(f"{key}: {value.strip()}")

        return " | ".join(content_parts)

    def _determine_content_type(self, content: str, row: pd.Series = None) -> str:
        """Determine the type of content (conversation, ticket, suggestion)"""
        content_lower = content.lower()

        if any(keyword in content_lower for keyword in ['ticket', 'incidente', 'caso', 'error', 'bug', 'problema']):
            return 'ticket'
        elif any(keyword in content_lower for keyword in ['conversacion', 'chat', 'mensaje', 'usuario:', 'agente:']):
            return 'conversation'
        else:
            return 'suggestion'

    def _determine_content_type_from_text(self, text: str) -> str:
        """Determine content type from raw text"""
        text_lower = text.lower()

        if any(keyword in text_lower for keyword in ['ticket', 'incidente', 'caso']):
            return 'ticket'
        elif any(keyword in text_lower for keyword in ['conversacion', 'chat', 'usuario:', 'agente:']):
            return 'conversation'
        else:
            return 'suggestion'

    def _extract_customer_id(self, row: pd.Series) -> Optional[str]:
        """Extract customer ID from row data"""
        for col in row.index:
            col_lower = str(col).lower()
            if any(keyword in col_lower for keyword in ['customer', 'client', 'user', 'cliente', 'usuario']):
                if pd.notna(row[col]) and str(row[col]).strip():
                    return str(row[col])
        return None

    def _extract_timestamp(self, row: pd.Series) -> Optional[datetime]:
        """Extract timestamp from row data"""
        for col in row.index:
            col_lower = str(col).lower()
            if any(keyword in col_lower for keyword in ['date', 'time', 'created', 'fecha', 'hora', 'timestamp']):
                try:
                    return pd.to_datetime(row[col])
                except:
                    continue
        return None

    def _is_new_item_marker(self, text: str) -> bool:
        """Check if text indicates the start of a new item"""
        markers = [
            r'ticket\s*#?\s*\d+',
            r'caso\s*#?\s*\d+',
            r'conversaci[óo]n\s*#?\s*\d+',
            r'id\s*:?\s*[a-zA-Z0-9-_]+',
            r'^\d+\.',  # Numbered list
            r'^-\s+',   # Bullet point
        ]

        for marker in markers:
            if re.search(marker, text.lower()):
                return True

        return False

    def _extract_id_from_text(self, text: str) -> Optional[str]:
        """Extract ID from text using regex patterns"""
        patterns = [
            r'(?:ticket|caso|id)\s*#?\s*([a-zA-Z0-9-_]+)',
            r'#([a-zA-Z0-9-_]+)',
            r'^([a-zA-Z0-9-_]{3,})'
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)

        return None

    def _split_pdf_content(self, content: str) -> List[str]:
        """Split PDF content into logical sections"""
        # Split by common separators
        separators = [
            r'\n\s*---+\s*\n',  # Horizontal lines
            r'\n\s*\*\*\*+\s*\n',  # Asterisk lines
            r'\n\s*===+\s*\n',  # Equal sign lines
            r'\n\s*\d+\.\s+',   # Numbered sections
            r'\n\s*[A-Z][A-Z\s]{10,}\n'  # All caps headers
        ]

        sections = [content]

        for separator in separators:
            new_sections = []
            for section in sections:
                new_sections.extend(re.split(separator, section))
            sections = new_sections

        # Filter out very short sections
        return [s for s in sections if len(s.strip()) > 20]