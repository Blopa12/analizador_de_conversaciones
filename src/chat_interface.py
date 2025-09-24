"""
Conversational AI interface for customer insights
"""

import anthropic
from typing import Dict, Any, List, Optional
import json
import os
from datetime import datetime

from knowledge_base import KnowledgeBase
from ai_analyzer import AIAnalyzer


class CustomerInsightsChatbot:
    """Conversational AI for exploring customer insights and opportunities"""

    def __init__(self, knowledge_base: KnowledgeBase, ai_analyzer: AIAnalyzer):
        self.kb = knowledge_base
        self.ai_analyzer = ai_analyzer
        self.client = anthropic.Anthropic(api_key=ai_analyzer.api_key)
        self.model = ai_analyzer.model

        # Conversation context
        self.conversation_history = []

    def chat(self, user_message: str, use_cache: bool = True) -> Dict[str, Any]:
        """
        Process a user message and return a response with insights

        Args:
            user_message: The user's question or request
            use_cache: Whether to use cached insights

        Returns:
            Dictionary containing response and metadata
        """
        # Check cache first
        if use_cache:
            cached_response = self._get_cached_response(user_message)
            if cached_response:
                return cached_response

        # Get relevant data based on the user's question
        context_data = self._gather_context_data(user_message)

        # Generate response using AI
        response = self._generate_response(user_message, context_data)

        # Cache the response
        self._cache_response(user_message, response)

        # Add to conversation history
        self.conversation_history.append({
            'user_message': user_message,
            'response': response,
            'timestamp': datetime.now().isoformat()
        })

        return response

    def _gather_context_data(self, user_message: str) -> Dict[str, Any]:
        """Gather relevant context data based on the user's message"""
        context = {
            'stats': self.kb.get_summary_stats(),
            'opportunities': [],
            'content_items': [],
            'query_intent': self._classify_query_intent(user_message)
        }

        # Get relevant opportunities based on query intent
        if 'pain' in user_message.lower() or 'problema' in user_message.lower():
            context['opportunities'] = self.kb.get_opportunities(category='pain_point', limit=10)
        elif 'mejora' in user_message.lower() or 'oportunidad' in user_message.lower():
            context['opportunities'] = self.kb.get_opportunities(category='improvement_opportunity', limit=10)
        elif 'funcionalidad' in user_message.lower() or 'feature' in user_message.lower():
            context['opportunities'] = self.kb.get_opportunities(category='feature_request', limit=10)
        elif 'crítico' in user_message.lower() or 'urgente' in user_message.lower():
            context['opportunities'] = self.kb.get_opportunities(severity='critical', limit=10)
        else:
            # General query - get top opportunities
            context['opportunities'] = self.kb.get_opportunities(limit=15)

        # Search for specific terms mentioned in the query
        search_terms = self._extract_search_terms(user_message)
        for term in search_terms:
            search_results = self.kb.search_opportunities(term, limit=5)
            context['opportunities'].extend(search_results)

        # Remove duplicates
        seen_ids = set()
        unique_opportunities = []
        for opp in context['opportunities']:
            if opp['id'] not in seen_ids:
                unique_opportunities.append(opp)
                seen_ids.add(opp['id'])
        context['opportunities'] = unique_opportunities

        return context

    def _classify_query_intent(self, user_message: str) -> str:
        """Classify the intent of the user's query"""
        message_lower = user_message.lower()

        if any(word in message_lower for word in ['estadísticas', 'stats', 'cuántos', 'total', 'resumen']):
            return 'statistics'
        elif any(word in message_lower for word in ['dolor', 'problema', 'pain', 'issue']):
            return 'pain_points'
        elif any(word in message_lower for word in ['mejora', 'oportunidad', 'improvement', 'opportunity']):
            return 'opportunities'
        elif any(word in message_lower for word in ['funcionalidad', 'feature', 'nueva']):
            return 'feature_requests'
        elif any(word in message_lower for word in ['cliente', 'customer', 'usuario', 'user']):
            return 'customer_insights'
        elif any(word in message_lower for word in ['tendencia', 'trend', 'patrón', 'pattern']):
            return 'trends'
        else:
            return 'general'

    def _extract_search_terms(self, user_message: str) -> List[str]:
        """Extract potential search terms from user message"""
        import re

        # Simple keyword extraction - could be enhanced with NLP
        words = re.findall(r'\b\w{4,}\b', user_message.lower())

        # Filter out common words
        stop_words = {
            'cuáles', 'cuales', 'cuántos', 'cuantos', 'tienes', 'tiene', 'puedes', 'puede',
            'mostrar', 'dime', 'dame', 'ayuda', 'help', 'what', 'how', 'many', 'show',
            'tell', 'give', 'explain', 'explica', 'información', 'informacion'
        }

        search_terms = [word for word in words if word not in stop_words and len(word) > 3]
        return search_terms[:5]  # Limit to 5 terms

    def _generate_response(self, user_message: str, context_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate AI response based on context data"""

        prompt = self._build_chat_prompt(user_message, context_data)

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                temperature=0.7,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            ai_response = response.content[0].text

            return {
                'response': ai_response,
                'context_used': {
                    'opportunities_count': len(context_data['opportunities']),
                    'query_intent': context_data['query_intent'],
                    'stats_included': bool(context_data['stats'])
                },
                'timestamp': datetime.now().isoformat(),
                'cached': False
            }

        except Exception as e:
            return {
                'response': f"Lo siento, ocurrió un error al procesar tu consulta: {str(e)}",
                'error': True,
                'timestamp': datetime.now().isoformat()
            }

    def _build_chat_prompt(self, user_message: str, context_data: Dict[str, Any]) -> str:
        """Build the chat prompt for the AI"""

        stats = context_data['stats']
        opportunities = context_data['opportunities'][:10]  # Limit for prompt size
        intent = context_data['query_intent']

        prompt = f"""
Eres un asistente de IA especializado en análisis de feedback de clientes. Tienes acceso a una base de conocimientos con información sobre conversaciones, tickets y sugerencias de clientes.

**CONTEXTO DE LA BASE DE CONOCIMIENTOS:**
- Total de elementos de contenido: {stats.get('total_content_items', 0)}
- Total de oportunidades identificadas: {stats.get('total_opportunities', 0)}
- Archivos procesados: {stats.get('files_processed', 0)}

**DISTRIBUCIÓN POR TIPO:**
{json.dumps(stats.get('items_by_type', {}), indent=2)}

**DISTRIBUCIÓN POR CATEGORÍA:**
{json.dumps(stats.get('opportunities_by_category', {}), indent=2)}

**DISTRIBUCIÓN POR SEVERIDAD:**
{json.dumps(stats.get('opportunities_by_severity', {}), indent=2)}

**PALABRAS CLAVE MÁS FRECUENTES:**
{', '.join([f"{kw} ({count})" for kw, count in stats.get('top_keywords', [])[:10]])}

**OPORTUNIDADES RELEVANTES PARA LA CONSULTA:**
"""

        for i, opp in enumerate(opportunities):
            prompt += f"\n{i+1}. **{opp['title']}**"
            prompt += f"\n   - Categoría: {opp['category']}"
            prompt += f"\n   - Severidad: {opp['severity']}"
            prompt += f"\n   - Frecuencia: {opp['frequency']}"
            prompt += f"\n   - Descripción: {opp['description']}"
            prompt += f"\n   - Palabras clave: {', '.join(opp['keywords'])}"
            prompt += f"\n"

        prompt += f"""

**PREGUNTA DEL USUARIO:**
{user_message}

**INTENCIÓN DETECTADA:** {intent}

**INSTRUCCIONES:**
1. Responde de manera clara y útil en español
2. Usa los datos de la base de conocimientos para respaldar tu respuesta
3. Si el usuario pregunta por estadísticas, proporciona números específicos
4. Si pregunta por oportunidades específicas, menciona las más relevantes
5. Proporciona insights accionables cuando sea posible
6. Mantén un tono profesional pero amigable
7. Si no tienes información suficiente, sé honesto al respecto

**RESPUESTA:**
"""

        return prompt

    def _get_cached_response(self, user_message: str) -> Optional[Dict[str, Any]]:
        """Check for cached response to similar query"""
        cached = self.kb.get_cached_insight('chat_response', {'query': user_message})

        if cached:
            try:
                cached_data = json.loads(cached)
                cached_data['cached'] = True
                return cached_data
            except:
                return None

        return None

    def _cache_response(self, user_message: str, response: Dict[str, Any]):
        """Cache the response for future use"""
        try:
            cache_data = response.copy()
            cache_data['cached'] = False
            self.kb.cache_insight('chat_response', {'query': user_message}, json.dumps(cache_data))
        except Exception as e:
            print(f"Warning: Failed to cache response: {str(e)}")

    def get_conversation_history(self) -> List[Dict[str, Any]]:
        """Get the conversation history"""
        return self.conversation_history

    def clear_conversation_history(self):
        """Clear the conversation history"""
        self.conversation_history = []

    def suggest_questions(self) -> List[str]:
        """Suggest interesting questions the user might ask"""
        stats = self.kb.get_summary_stats()

        suggestions = [
            "¿Cuáles son los principales dolores de nuestros clientes?",
            "¿Qué oportunidades de mejora han mencionado más frecuentemente?",
            "¿Cuántos tickets críticos tenemos registrados?",
            "¿Qué funcionalidades nuevas han solicitado los clientes?",
            "Muéstrame un resumen de las tendencias en el feedback de clientes",
            "¿Qué palabras clave aparecen más en las quejas de clientes?",
            "¿Cuáles son las oportunidades de mayor impacto?",
            "¿Qué patrones veo en las conversaciones de soporte?"
        ]

        # Add dynamic suggestions based on data
        if stats.get('opportunities_by_category', {}).get('pain_point', 0) > 0:
            suggestions.append(f"Tenemos {stats['opportunities_by_category']['pain_point']} puntos de dolor identificados, ¿cuáles son los más críticos?")

        if stats.get('total_content_items', 0) > 100:
            suggestions.append(f"Con {stats['total_content_items']} elementos analizados, ¿qué insights generales puedes darme?")

        return suggestions[:8]  # Return top 8 suggestions