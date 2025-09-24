"""
AI-powered analysis module for identifying opportunities and pain points
"""

import anthropic
from typing import List, Dict, Any, Optional
import json
import re
from dataclasses import dataclass, asdict
from datetime import datetime
import os
from dotenv import load_dotenv

from content_extractor import ContentItem

load_dotenv()


@dataclass
class Opportunity:
    """Represents an identified opportunity or pain point"""
    id: str
    title: str
    description: str
    category: str  # 'pain_point', 'improvement_opportunity', 'feature_request'
    severity: str  # 'low', 'medium', 'high', 'critical'
    frequency: int  # How many times this opportunity has been identified
    sources: List[str]  # IDs of content items that mention this opportunity
    keywords: List[str]  # Key terms associated with this opportunity
    created_at: datetime
    updated_at: datetime
    processing_date: datetime  # Date when the file was processed
    status: str  # 'nueva', 'descartada', 'en_proceso', 'solucionada', 'bloqueada'
    comments: str  # Comments about this opportunity
    merged_from: List[str] = None  # IDs of opportunities merged into this one

    def __post_init__(self):
        if self.merged_from is None:
            self.merged_from = []
        if not hasattr(self, 'processing_date') or self.processing_date is None:
            self.processing_date = datetime.now()
        if not hasattr(self, 'status') or self.status is None:
            self.status = 'nueva'
        if not hasattr(self, 'comments') or self.comments is None:
            self.comments = ''


class AIAnalyzer:
    """AI-powered analyzer for identifying opportunities and pain points"""

    def __init__(self, api_key: Optional[str] = None, model: str = None):
        self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY')
        self.model = model or os.getenv('AI_MODEL', 'claude-3-haiku-20240307')
        self.max_opportunities = int(os.getenv('MAX_OPPORTUNITIES_PER_INPUT', '3'))
        self.batch_size = int(os.getenv('AI_BATCH_SIZE', '10'))
        self.max_items_per_file = int(os.getenv('MAX_ITEMS_PER_FILE', '500'))

        if not self.api_key:
            raise ValueError("Anthropic API key is required")

        self.client = anthropic.Anthropic(api_key=self.api_key)

    def analyze_content_items(self, content_items: List[ContentItem], progress_callback=None) -> List[Opportunity]:
        """
        Analyze content items to identify opportunities and pain points

        Args:
            content_items: List of ContentItem objects to analyze
            progress_callback: Optional callback function to report progress

        Returns:
            List of identified Opportunity objects
        """
        # Limit items for very large files
        if len(content_items) > self.max_items_per_file:
            print(f"⚠️  Archivo muy grande ({len(content_items)} elementos). Procesando solo los primeros {self.max_items_per_file} elementos.")
            content_items = content_items[:self.max_items_per_file]

        all_opportunities = []
        total_batches = (len(content_items) + self.batch_size - 1) // self.batch_size

        print(f"🧠 Procesando {len(content_items)} elementos en {total_batches} lotes de {self.batch_size}...")

        # Process items in batches to manage API limits and costs
        for i in range(0, len(content_items), self.batch_size):
            batch_num = (i // self.batch_size) + 1
            batch = content_items[i:i + self.batch_size]

            print(f"   📊 Lote {batch_num}/{total_batches}: Analizando {len(batch)} elementos...")

            batch_opportunities = self._analyze_batch(batch)
            all_opportunities.extend(batch_opportunities)

            if progress_callback:
                progress_callback(batch_num, total_batches)

            print(f"      ✅ Lote {batch_num} completado: {len(batch_opportunities)} oportunidades encontradas")

        return all_opportunities

    def _analyze_batch(self, content_items: List[ContentItem]) -> List[Opportunity]:
        """Analyze a batch of content items using optimized batch processing"""
        if len(content_items) == 1:
            # Single item - use existing method
            try:
                return self._analyze_single_item(content_items[0])
            except Exception as e:
                print(f"      ⚠️  Error analyzing item {content_items[0].id}: {str(e)}")
                return []
        else:
            # Multiple items - use batch analysis
            try:
                return self._analyze_multiple_items(content_items)
            except Exception as e:
                print(f"      ⚠️  Error in batch analysis: {str(e)}")
                # Fallback to individual processing
                opportunities = []
                for item in content_items:
                    try:
                        item_opportunities = self._analyze_single_item(item)
                        opportunities.extend(item_opportunities)
                    except Exception as e:
                        print(f"      ⚠️  Error analyzing item {item.id}: {str(e)}")
                        continue
                return opportunities

    def _analyze_single_item(self, content_item: ContentItem) -> List[Opportunity]:
        """Analyze a single content item to identify opportunities"""

        prompt = self._build_analysis_prompt(content_item)

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1500,
                temperature=0.3,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            # Parse the AI response
            analysis_result = self._parse_ai_response(response.content[0].text)

            # Convert to Opportunity objects
            opportunities = []
            for opp_data in analysis_result.get('opportunities', []):
                opportunity = self._create_opportunity_from_analysis(
                    opp_data,
                    content_item
                )
                opportunities.append(opportunity)

            return opportunities

        except Exception as e:
            print(f"Error in AI analysis for item {content_item.id}: {str(e)}")
            return []

    def _build_analysis_prompt(self, content_item: ContentItem) -> str:
        """Build the analysis prompt for the AI"""

        prompt = f"""
Analiza el siguiente contenido de cliente y identifica dolores, oportunidades de mejora o solicitudes de funcionalidades.

**INFORMACIÓN DEL CONTENIDO:**
- ID: {content_item.id}
- Tipo: {content_item.content_type}
- Cliente: {content_item.customer_id or 'No especificado'}
- Archivo fuente: {content_item.source_file}

**CONTENIDO A ANALIZAR:**
{content_item.content}

**INSTRUCCIONES:**
1. Identifica máximo {self.max_opportunities} oportunidades principales
2. Para cada oportunidad identificada, proporciona:
   - Un título conciso y descriptivo
   - Una descripción detallada del dolor/oportunidad
   - Categoría: "pain_point", "improvement_opportunity", o "feature_request"
   - Severidad: "low", "medium", "high", o "critical"
   - Palabras clave relacionadas (3-5 palabras)

3. Solo identifica oportunidades REALES y ESPECÍFICAS. No inventes problemas.
4. Si no hay oportunidades claras, devuelve una lista vacía.

**FORMATO DE RESPUESTA (JSON):**
{{
    "opportunities": [
        {{
            "title": "Título de la oportunidad",
            "description": "Descripción detallada del dolor o oportunidad identificada",
            "category": "pain_point|improvement_opportunity|feature_request",
            "severity": "low|medium|high|critical",
            "keywords": ["palabra1", "palabra2", "palabra3"]
        }}
    ]
}}

**RESPUESTA:**
"""

        return prompt

    def _parse_ai_response(self, response_text: str) -> Dict[str, Any]:
        """Parse the AI response and extract structured data"""
        try:
            # Try to find JSON in the response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                return json.loads(json_str)
            else:
                print(f"Warning: No JSON found in AI response: {response_text}")
                return {"opportunities": []}

        except json.JSONDecodeError as e:
            print(f"Warning: Failed to parse AI response as JSON: {str(e)}")
            print(f"Response text: {response_text}")
            return {"opportunities": []}

    def _create_opportunity_from_analysis(
        self,
        opp_data: Dict[str, Any],
        content_item: ContentItem,
        processing_date: datetime = None
    ) -> Opportunity:
        """Create an Opportunity object from AI analysis data"""

        now = datetime.now()
        proc_date = processing_date or now

        # Generate unique ID for the opportunity
        opportunity_id = f"opp_{content_item.id}_{hash(opp_data['title']) % 10000}"

        return Opportunity(
            id=opportunity_id,
            title=opp_data.get('title', 'Oportunidad sin título'),
            description=opp_data.get('description', 'Sin descripción'),
            category=opp_data.get('category', 'improvement_opportunity'),
            severity=opp_data.get('severity', 'medium'),
            frequency=1,  # Initial frequency
            sources=[content_item.id],
            keywords=opp_data.get('keywords', []),
            created_at=now,
            updated_at=now,
            processing_date=proc_date,
            status='nueva',
            comments=''
        )

    def analyze_single_content(self, content: str, content_type: str = "suggestion") -> List[Dict[str, Any]]:
        """
        Analyze a single piece of content (utility method for API/interface use)

        Args:
            content: The content text to analyze
            content_type: Type of content ('conversation', 'ticket', 'suggestion')

        Returns:
            List of opportunity dictionaries
        """
        # Create a temporary ContentItem
        temp_item = ContentItem(
            id="temp_analysis",
            content_type=content_type,
            content=content,
            metadata={},
            source_file="direct_input"
        )

        opportunities = self._analyze_single_item(temp_item)
        return [asdict(opp) for opp in opportunities]


class OpportunityDeduplicator:
    """Handles deduplication and similarity merging of opportunities"""

    def __init__(self, similarity_threshold: float = None):
        from sentence_transformers import SentenceTransformer
        import numpy as np
        from sklearn.metrics.pairwise import cosine_similarity

        self.similarity_threshold = similarity_threshold or float(os.getenv('SIMILARITY_THRESHOLD', '0.8'))
        self.model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
        self.cosine_similarity = cosine_similarity

    def deduplicate_opportunities(self, opportunities: List[Opportunity]) -> List[Opportunity]:
        """
        Deduplicate opportunities by merging similar ones

        Args:
            opportunities: List of Opportunity objects

        Returns:
            Deduplicated list of Opportunity objects
        """
        if not opportunities:
            return []

        # Create embeddings for all opportunities
        texts = [f"{opp.title} {opp.description}" for opp in opportunities]
        embeddings = self.model.encode(texts)

        # Find similar opportunities
        similarity_matrix = self.cosine_similarity(embeddings)

        # Group similar opportunities
        groups = self._find_similarity_groups(similarity_matrix, opportunities)

        # Merge opportunities in each group
        merged_opportunities = []
        for group in groups:
            merged_opp = self._merge_opportunity_group(group)
            merged_opportunities.append(merged_opp)

        return merged_opportunities

    def _find_similarity_groups(self, similarity_matrix, opportunities: List[Opportunity]) -> List[List[Opportunity]]:
        """Find groups of similar opportunities"""
        n = len(opportunities)
        visited = [False] * n
        groups = []

        for i in range(n):
            if visited[i]:
                continue

            # Start a new group
            group = [opportunities[i]]
            visited[i] = True

            # Find similar opportunities
            for j in range(i + 1, n):
                if not visited[j] and similarity_matrix[i][j] >= self.similarity_threshold:
                    group.append(opportunities[j])
                    visited[j] = True

            groups.append(group)

        return groups

    def _merge_opportunity_group(self, opportunities: List[Opportunity]) -> Opportunity:
        """Merge a group of similar opportunities into one"""
        if len(opportunities) == 1:
            return opportunities[0]

        # Use the first opportunity as base
        base_opp = opportunities[0]

        # Merge data from other opportunities
        all_sources = []
        all_keywords = set()
        total_frequency = 0
        merged_ids = []

        for opp in opportunities:
            all_sources.extend(opp.sources)
            all_keywords.update(opp.keywords)
            total_frequency += opp.frequency
            if opp.id != base_opp.id:
                merged_ids.append(opp.id)

        # Create merged opportunity
        merged_opp = Opportunity(
            id=base_opp.id,
            title=base_opp.title,  # Keep original title
            description=self._merge_descriptions([opp.description for opp in opportunities]),
            category=base_opp.category,
            severity=self._get_highest_severity([opp.severity for opp in opportunities]),
            frequency=total_frequency,
            sources=list(set(all_sources)),  # Remove duplicates
            keywords=list(all_keywords),
            created_at=min(opp.created_at for opp in opportunities),
            updated_at=datetime.now(),
            processing_date=min(getattr(opp, 'processing_date', opp.created_at) for opp in opportunities),
            status=base_opp.status if hasattr(base_opp, 'status') else 'nueva',
            comments=base_opp.comments if hasattr(base_opp, 'comments') else '',
            merged_from=merged_ids
        )

        return merged_opp

    def _merge_descriptions(self, descriptions: List[str]) -> str:
        """Merge multiple descriptions into one"""
        if len(descriptions) == 1:
            return descriptions[0]

        # Simple merge - could be enhanced with AI summarization
        unique_descriptions = []
        seen = set()

        for desc in descriptions:
            desc_clean = desc.strip().lower()
            if desc_clean not in seen and desc_clean:
                unique_descriptions.append(desc.strip())
                seen.add(desc_clean)

        if len(unique_descriptions) == 1:
            return unique_descriptions[0]
        else:
            return " | ".join(unique_descriptions)

    def _get_highest_severity(self, severities: List[str]) -> str:
        """Get the highest severity from a list"""
        severity_order = {'low': 1, 'medium': 2, 'high': 3, 'critical': 4}

        highest_severity = 'low'
        highest_value = 0

        for severity in severities:
            value = severity_order.get(severity, 0)
            if value > highest_value:
                highest_value = value
                highest_severity = severity

        return highest_severity