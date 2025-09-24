"""
Main orchestrator for the customer feedback analysis system
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Any
import argparse
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from file_processors import FileProcessor, DataStructureAnalyzer
from content_extractor import ContentExtractor
from ai_analyzer import AIAnalyzer, OpportunityDeduplicator
from knowledge_base import KnowledgeBase
from chat_interface import CustomerInsightsChatbot


class CustomerFeedbackAnalyzer:
    """Main orchestrator for the customer feedback analysis system"""

    def __init__(self, api_key: str = None):
        """
        Initialize the analyzer

        Args:
            api_key: Anthropic API key (if not provided, will use environment variable)
        """
        self.file_processor = FileProcessor()
        self.structure_analyzer = DataStructureAnalyzer()
        self.content_extractor = ContentExtractor()
        self.ai_analyzer = AIAnalyzer(api_key=api_key)
        self.deduplicator = OpportunityDeduplicator()
        self.knowledge_base = KnowledgeBase()
        self.chatbot = CustomerInsightsChatbot(self.knowledge_base, self.ai_analyzer)

        print("✅ Sistema inicializado correctamente")

    def process_file(self, file_path: str, verbose: bool = True) -> Dict[str, Any]:
        """
        Process a single file end-to-end

        Args:
            file_path: Path to the file to process
            verbose: Whether to print progress information

        Returns:
            Dictionary with processing results
        """
        if verbose:
            print(f"\n🔄 Procesando archivo: {file_path}")

        try:
            # Step 1: Process file
            if verbose:
                print("📄 Leyendo archivo...")
            processed_file = self.file_processor.process_file(file_path)

            # Step 2: Analyze structure
            if verbose:
                print("🔍 Analizando estructura...")
            structure_analysis = self.structure_analyzer.analyze_structure(processed_file)

            # Step 3: Extract content items
            if verbose:
                print("📝 Extrayendo contenido...")
            content_items = self.content_extractor.extract_content_items(
                processed_file, structure_analysis
            )

            if verbose:
                print(f"   ➜ Encontrados {len(content_items)} elementos de contenido")

            # Step 4: Analyze content with AI
            if verbose:
                print("🧠 Analizando oportunidades con IA...")
            opportunities = self.ai_analyzer.analyze_content_items(content_items)

            if verbose:
                print(f"   ➜ Identificadas {len(opportunities)} oportunidades iniciales")

            # Step 5: Deduplicate opportunities
            if verbose:
                print("🔗 Eliminando duplicados...")
            deduplicated_opportunities = self.deduplicator.deduplicate_opportunities(opportunities)

            if verbose:
                print(f"   ➜ Oportunidades finales: {len(deduplicated_opportunities)}")

            # Step 6: Store in knowledge base
            if verbose:
                print("💾 Guardando en base de conocimientos...")

            stored_items = self.knowledge_base.store_content_items(content_items)
            stored_opportunities = self.knowledge_base.store_opportunities(deduplicated_opportunities)

            # Log processing
            file_path_obj = Path(file_path)
            self.knowledge_base.log_file_processing(
                file_name=file_path_obj.name,
                file_path=str(file_path_obj.absolute()),
                file_type=processed_file['file_type'],
                file_size=file_path_obj.stat().st_size,
                items_extracted=len(content_items),
                opportunities_found=len(deduplicated_opportunities),
                status='completed'
            )

            if verbose:
                print(f"✅ Procesamiento completado:")
                print(f"   • {stored_items} elementos almacenados")
                print(f"   • {stored_opportunities} oportunidades almacenadas")

            return {
                'file_path': file_path,
                'content_items': len(content_items),
                'opportunities_found': len(opportunities),
                'opportunities_final': len(deduplicated_opportunities),
                'stored_items': stored_items,
                'stored_opportunities': stored_opportunities,
                'processing_time': datetime.now().isoformat(),
                'status': 'success'
            }

        except Exception as e:
            error_msg = f"Error procesando {file_path}: {str(e)}"
            if verbose:
                print(f"❌ {error_msg}")

            # Log error
            try:
                file_path_obj = Path(file_path)
                self.knowledge_base.log_file_processing(
                    file_name=file_path_obj.name,
                    file_path=str(file_path_obj.absolute()),
                    file_type='unknown',
                    file_size=file_path_obj.stat().st_size if file_path_obj.exists() else 0,
                    items_extracted=0,
                    opportunities_found=0,
                    status='error'
                )
            except:
                pass

            return {
                'file_path': file_path,
                'status': 'error',
                'error': error_msg,
                'processing_time': datetime.now().isoformat()
            }

    def process_directory(self, directory_path: str, verbose: bool = True) -> Dict[str, Any]:
        """
        Process all supported files in a directory

        Args:
            directory_path: Path to directory containing files
            verbose: Whether to print progress information

        Returns:
            Dictionary with processing results
        """
        directory = Path(directory_path)

        if not directory.exists() or not directory.is_dir():
            raise ValueError(f"Directory not found or not a directory: {directory_path}")

        # Find supported files
        supported_extensions = ['.xlsx', '.docx', '.pdf']
        files_to_process = []

        for ext in supported_extensions:
            files_to_process.extend(directory.glob(f"*{ext}"))

        if verbose:
            print(f"\n📁 Procesando directorio: {directory_path}")
            print(f"   ➜ Encontrados {len(files_to_process)} archivos soportados")

        results = {
            'directory': directory_path,
            'files_found': len(files_to_process),
            'files_processed': 0,
            'files_successful': 0,
            'files_failed': 0,
            'total_items': 0,
            'total_opportunities': 0,
            'file_results': [],
            'processing_time': datetime.now().isoformat()
        }

        for file_path in files_to_process:
            file_result = self.process_file(str(file_path), verbose=verbose)
            results['file_results'].append(file_result)
            results['files_processed'] += 1

            if file_result['status'] == 'success':
                results['files_successful'] += 1
                results['total_items'] += file_result['stored_items']
                results['total_opportunities'] += file_result['stored_opportunities']
            else:
                results['files_failed'] += 1

        if verbose:
            print(f"\n📊 Resumen del procesamiento:")
            print(f"   • Archivos procesados: {results['files_processed']}")
            print(f"   • Exitosos: {results['files_successful']}")
            print(f"   • Fallidos: {results['files_failed']}")
            print(f"   • Total elementos: {results['total_items']}")
            print(f"   • Total oportunidades: {results['total_opportunities']}")

        return results

    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics from the knowledge base"""
        return self.knowledge_base.get_summary_stats()

    def search_opportunities(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search for opportunities by query"""
        return self.knowledge_base.search_opportunities(query, limit)

    def chat(self, message: str) -> str:
        """Chat with the AI assistant about customer insights"""
        response = self.chatbot.chat(message)
        return response.get('response', 'No se pudo generar respuesta')

    def get_processing_history(self) -> List[Dict[str, Any]]:
        """Get file processing history"""
        return self.knowledge_base.get_processing_history()


def main():
    """Main CLI interface"""
    parser = argparse.ArgumentParser(
        description="Analizador de Feedback de Clientes con IA",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:

1. Procesar un archivo:
   python main.py process-file archivo.xlsx

2. Procesar un directorio:
   python main.py process-directory ./datos/

3. Ver estadísticas:
   python main.py stats

4. Buscar oportunidades:
   python main.py search "login problems"

5. Modo chat interactivo:
   python main.py chat

6. Configurar API key:
   export ANTHROPIC_API_KEY=tu_api_key_aqui
        """
    )

    parser.add_argument(
        'command',
        choices=['process-file', 'process-directory', 'stats', 'search', 'chat', 'history'],
        help='Comando a ejecutar'
    )

    parser.add_argument(
        'target',
        nargs='?',
        help='Archivo, directorio o consulta de búsqueda'
    )

    parser.add_argument(
        '--api-key',
        help='Clave de API de Anthropic (también puede usar ANTHROPIC_API_KEY)'
    )

    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='Modo silencioso (menos output)'
    )

    parser.add_argument(
        '--limit', '-l',
        type=int,
        default=10,
        help='Límite de resultados para búsquedas (default: 10)'
    )

    args = parser.parse_args()

    try:
        # Initialize analyzer
        analyzer = CustomerFeedbackAnalyzer(api_key=args.api_key)

        if args.command == 'process-file':
            if not args.target:
                print("❌ Error: Debe especificar un archivo")
                return 1

            result = analyzer.process_file(args.target, verbose=not args.quiet)
            if result['status'] == 'error':
                return 1

        elif args.command == 'process-directory':
            if not args.target:
                print("❌ Error: Debe especificar un directorio")
                return 1

            result = analyzer.process_directory(args.target, verbose=not args.quiet)
            if result['files_failed'] > 0:
                print(f"⚠️  Advertencia: {result['files_failed']} archivos fallaron")

        elif args.command == 'stats':
            stats = analyzer.get_summary()
            print("\n📊 Estadísticas del Sistema:")
            print(f"   • Total elementos: {stats['total_content_items']}")
            print(f"   • Total oportunidades: {stats['total_opportunities']}")
            print(f"   • Archivos procesados: {stats['files_processed']}")
            print(f"   • Elementos por tipo: {stats['items_by_type']}")
            print(f"   • Oportunidades por categoría: {stats['opportunities_by_category']}")
            print(f"   • Oportunidades por severidad: {stats['opportunities_by_severity']}")

            if stats['top_keywords']:
                print(f"   • Top keywords: {', '.join([f'{kw}({c})' for kw, c in stats['top_keywords'][:5]])}")

        elif args.command == 'search':
            if not args.target:
                print("❌ Error: Debe especificar una consulta de búsqueda")
                return 1

            results = analyzer.search_opportunities(args.target, args.limit)
            print(f"\n🔍 Resultados de búsqueda para: '{args.target}'")
            print(f"    Encontrados: {len(results)} resultados")

            for i, opp in enumerate(results, 1):
                print(f"\n{i}. {opp['title']}")
                print(f"   Categoría: {opp['category']} | Severidad: {opp['severity']} | Frecuencia: {opp['frequency']}")
                print(f"   Descripción: {opp['description'][:100]}...")
                print(f"   Keywords: {', '.join(opp['keywords'][:5])}")

        elif args.command == 'chat':
            print("\n💬 Modo Chat Interactivo")
            print("Escriba 'salir' o 'quit' para terminar")
            print("Escriba 'sugerencias' para ver preguntas sugeridas")
            print("-" * 50)

            while True:
                try:
                    user_input = input("\n🤔 Usted: ").strip()

                    if user_input.lower() in ['salir', 'quit', 'exit']:
                        print("👋 ¡Hasta luego!")
                        break

                    if user_input.lower() in ['sugerencias', 'suggestions']:
                        suggestions = analyzer.chatbot.suggest_questions()
                        print("\n💡 Preguntas sugeridas:")
                        for i, suggestion in enumerate(suggestions, 1):
                            print(f"{i}. {suggestion}")
                        continue

                    if not user_input:
                        continue

                    print("🤖 IA: ", end="")
                    response = analyzer.chat(user_input)
                    print(response)

                except KeyboardInterrupt:
                    print("\n👋 ¡Hasta luego!")
                    break
                except EOFError:
                    break

        elif args.command == 'history':
            history = analyzer.get_processing_history()
            print("\n📜 Historial de Procesamiento:")

            for entry in history[:10]:  # Show last 10
                status_icon = "✅" if entry['status'] == 'completed' else "❌"
                print(f"{status_icon} {entry['file_name']} - {entry['processed_at']}")
                print(f"    Elementos: {entry['items_extracted']}, Oportunidades: {entry['opportunities_found']}")

        return 0

    except KeyboardInterrupt:
        print("\n👋 Operación cancelada por el usuario")
        return 1
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return 1


if __name__ == '__main__':
    exit(main())