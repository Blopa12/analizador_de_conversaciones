"""
Streamlit web interface for the Customer Feedback Analyzer
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import sys
import tempfile
import os
from datetime import datetime
import json

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

try:
    from src.main import CustomerFeedbackAnalyzer
except ImportError:
    # Fallback for different import paths
    import sys
    sys.path.insert(0, str(src_path))
    from main import CustomerFeedbackAnalyzer


def initialize_analyzer():
    """Initialize the analyzer"""
    api_key = os.getenv('ANTHROPIC_API_KEY') or st.secrets.get('ANTHROPIC_API_KEY')
    if not api_key:
        st.error("⚠️ API Key de Anthropic no configurada. Configure ANTHROPIC_API_KEY en las variables de entorno o en Streamlit secrets.")
        st.stop()

    analyzer = CustomerFeedbackAnalyzer(api_key=api_key)
    # Debug: show supported formats
    st.sidebar.info(f"🔧 Formatos soportados: {analyzer.file_processor.supported_formats}")
    return analyzer


def main():
    st.set_page_config(
        page_title="Analizador de Feedback de Clientes",
        page_icon="🔍",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    st.title("🔍 Analizador de Feedback de Clientes con IA")
    st.markdown("*Identifica oportunidades y dolores en conversaciones, tickets y sugerencias*")

    # Initialize analyzer (without caching for debug)
    try:
        analyzer = initialize_analyzer()
    except Exception as e:
        st.error(f"Error inicializando el sistema: {str(e)}")
        st.stop()

    # Sidebar navigation
    st.sidebar.title("🎯 Navegación")
    page = st.sidebar.radio(
        "Seleccione una página:",
        ["📊 Dashboard", "📁 Procesar Archivos", "🔍 Buscar Oportunidades", "⚙️ Gestionar Oportunidades", "💬 Chat con IA", "📜 Historial"]
    )

    if page == "📊 Dashboard":
        show_dashboard(analyzer)
    elif page == "📁 Procesar Archivos":
        show_file_processor(analyzer)
    elif page == "🔍 Buscar Oportunidades":
        show_search_page(analyzer)
    elif page == "⚙️ Gestionar Oportunidades":
        show_manage_opportunities_page(analyzer)
    elif page == "💬 Chat con IA":
        show_chat_page(analyzer)
    elif page == "📜 Historial":
        show_history_page(analyzer)


def show_dashboard(analyzer):
    """Show the main dashboard"""
    st.header("📊 Dashboard de Insights")

    # Get stats
    stats = analyzer.get_summary()

    # Key metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="📝 Total Elementos",
            value=stats.get('total_content_items', 0),
            help="Conversaciones, tickets y sugerencias procesadas"
        )

    with col2:
        st.metric(
            label="💡 Oportunidades",
            value=stats.get('total_opportunities', 0),
            help="Dolores y oportunidades identificadas"
        )

    with col3:
        st.metric(
            label="📁 Archivos Procesados",
            value=stats.get('files_processed', 0),
            help="Número de archivos analizados"
        )

    with col4:
        # Calculate average opportunities per file
        avg_opps = 0
        if stats.get('files_processed', 0) > 0:
            avg_opps = round(stats.get('total_opportunities', 0) / stats.get('files_processed', 1), 1)

        st.metric(
            label="📈 Promedio Oportunidades",
            value=f"{avg_opps}/archivo",
            help="Promedio de oportunidades por archivo"
        )

    # Charts section
    if stats.get('total_opportunities', 0) > 0:
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("📊 Oportunidades por Categoría")
            if stats.get('opportunities_by_category'):
                category_data = stats['opportunities_by_category']
                fig_cat = px.pie(
                    values=list(category_data.values()),
                    names=list(category_data.keys()),
                    title="Distribución por Categoría"
                )
                st.plotly_chart(fig_cat, use_container_width=True)

        with col2:
            st.subheader("⚠️ Oportunidades por Severidad")
            if stats.get('opportunities_by_severity'):
                severity_data = stats['opportunities_by_severity']
                colors = {'low': '#28a745', 'medium': '#ffc107', 'high': '#fd7e14', 'critical': '#dc3545'}

                fig_sev = px.bar(
                    x=list(severity_data.keys()),
                    y=list(severity_data.values()),
                    title="Distribución por Severidad",
                    color=list(severity_data.keys()),
                    color_discrete_map=colors
                )
                st.plotly_chart(fig_sev, use_container_width=True)

        # Top keywords
        if stats.get('top_keywords'):
            st.subheader("🏷️ Palabras Clave Más Frecuentes")
            keywords_df = pd.DataFrame(
                stats['top_keywords'][:10],
                columns=['Palabra Clave', 'Frecuencia']
            )

            fig_keywords = px.bar(
                keywords_df,
                x='Frecuencia',
                y='Palabra Clave',
                orientation='h',
                title="Top 10 Palabras Clave"
            )
            fig_keywords.update_layout(yaxis={'categoryorder': 'total ascending'})
            st.plotly_chart(fig_keywords, use_container_width=True)

        # Recent opportunities
        st.subheader("🆕 Oportunidades Recientes")
        recent_opps = analyzer.knowledge_base.get_opportunities(limit=5)

        if recent_opps:
            for opp in recent_opps:
                severity_color = {
                    'low': '🟢',
                    'medium': '🟡',
                    'high': '🟠',
                    'critical': '🔴'
                }.get(opp['severity'], '⚪')

                category_icon = {
                    'pain_point': '😣',
                    'improvement_opportunity': '💡',
                    'feature_request': '⭐'
                }.get(opp['category'], '📝')

                with st.expander(f"{severity_color} {category_icon} {opp['title']} (x{opp['frequency']})"):
                    st.write(f"**Descripción:** {opp['description']}")
                    st.write(f"**Categoría:** {opp['category']}")
                    st.write(f"**Severidad:** {opp['severity']}")
                    if opp['keywords']:
                        st.write(f"**Keywords:** {', '.join(opp['keywords'][:5])}")
        else:
            st.info("No hay oportunidades registradas aún. Procese algunos archivos para comenzar.")

    else:
        st.info("🚀 ¡Bienvenido! Comience subiendo archivos en la sección 'Procesar Archivos' para ver insights aquí.")


def show_file_processor(analyzer):
    """Show the file processing page"""
    st.header("📁 Procesar Archivos")
    st.markdown("Suba archivos en formato **XLSX**, **XLS**, **CSV**, **DOCX** o **PDF** para análisis.")

    # File uploader
    uploaded_files = st.file_uploader(
        "Seleccione archivos para procesar",
        type=['xlsx', 'xls', 'csv', 'docx', 'pdf'],
        accept_multiple_files=True,
        help="Formatos soportados: Excel (.xlsx, .xls), CSV (.csv), Word (.docx), PDF (.pdf)"
    )

    if uploaded_files:
        st.success(f"✅ {len(uploaded_files)} archivo(s) seleccionado(s)")

        # Processing options
        col1, col2 = st.columns(2)
        with col1:
            show_progress = st.checkbox("Mostrar progreso detallado", value=True)
        with col2:
            auto_deduplicate = st.checkbox("Auto-deduplicación de oportunidades", value=True)

        if st.button("🚀 Procesar Archivos", type="primary", use_container_width=True):
            process_uploaded_files(analyzer, uploaded_files, show_progress)

    # Processing stats
    st.subheader("📊 Estado del Sistema")
    stats = analyzer.get_summary()

    col1, col2, col3 = st.columns(3)
    with col1:
        st.info(f"📝 **{stats.get('total_content_items', 0)}** elementos procesados")
    with col2:
        st.info(f"💡 **{stats.get('total_opportunities', 0)}** oportunidades identificadas")
    with col3:
        st.info(f"📁 **{stats.get('files_processed', 0)}** archivos analizados")


def process_uploaded_files(analyzer, uploaded_files, show_progress):
    """Process uploaded files"""
    progress_bar = st.progress(0)
    status_text = st.empty()
    results_container = st.container()

    total_files = len(uploaded_files)
    successful = 0
    failed = 0

    for i, uploaded_file in enumerate(uploaded_files):
        # Update progress
        progress = (i + 1) / total_files
        progress_bar.progress(progress)
        status_text.text(f"Procesando {i+1}/{total_files}: {uploaded_file.name}")

        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{uploaded_file.name.split('.')[-1]}") as tmp_file:
            tmp_file.write(uploaded_file.getbuffer())
            tmp_file_path = tmp_file.name

        try:
            # Debug: check file extension
            file_ext = os.path.splitext(uploaded_file.name)[1].lower()
            st.write(f"🐛 Debug: Archivo {uploaded_file.name}, extensión: {file_ext}")

            # Show processing info for large files
            with st.spinner(f"Procesando {uploaded_file.name}..."):
                st.info("Para archivos grandes, el sistema procesará máximo 500 elementos para evitar timeouts.")
                result = analyzer.process_file(tmp_file_path, verbose=show_progress)

            if result['status'] == 'success':
                successful += 1
                with results_container:
                    st.success(f"✅ {uploaded_file.name}: {result['stored_items']} elementos, {result['stored_opportunities']} oportunidades")
            else:
                failed += 1
                with results_container:
                    st.error(f"❌ {uploaded_file.name}: {result.get('error', 'Error desconocido')}")

        except Exception as e:
            failed += 1
            with results_container:
                st.error(f"❌ {uploaded_file.name}: {str(e)}")
        finally:
            # Clean up temp file
            try:
                os.unlink(tmp_file_path)
            except:
                pass

    # Final status
    status_text.text(f"✅ Completado: {successful} exitosos, {failed} fallidos")

    if successful > 0:
        st.balloons()


def show_search_page(analyzer):
    """Show the search page"""
    st.header("🔍 Buscar Oportunidades")

    # Search interface
    col1, col2 = st.columns([3, 1])

    with col1:
        search_query = st.text_input(
            "Buscar en oportunidades:",
            placeholder="Ej: login, problemas de rendimiento, nueva funcionalidad..."
        )

    with col2:
        search_limit = st.number_input("Resultados", min_value=1, max_value=50, value=10)

    # Filters
    with st.expander("🎛️ Filtros Avanzados"):
        col1, col2, col3 = st.columns(3)

        with col1:
            filter_category = st.selectbox(
                "Categoría:",
                ["Todas", "pain_point", "improvement_opportunity", "feature_request"]
            )

        with col2:
            filter_severity = st.selectbox(
                "Severidad:",
                ["Todas", "low", "medium", "high", "critical"]
            )

        with col3:
            min_frequency = st.number_input("Frecuencia mínima:", min_value=1, value=1)

    # Search button
    if st.button("🔍 Buscar", type="primary") or search_query:
        if search_query:
            results = analyzer.search_opportunities(search_query, search_limit)
        else:
            # Get filtered results
            category = None if filter_category == "Todas" else filter_category
            severity = None if filter_severity == "Todas" else filter_severity

            results = analyzer.knowledge_base.get_opportunities(
                category=category,
                severity=severity,
                min_frequency=min_frequency,
                limit=search_limit
            )

        # Display results
        if results:
            st.subheader(f"📋 Resultados ({len(results)} encontrados)")

            for i, opp in enumerate(results, 1):
                severity_color = {
                    'low': '🟢',
                    'medium': '🟡',
                    'high': '🟠',
                    'critical': '🔴'
                }.get(opp['severity'], '⚪')

                category_icon = {
                    'pain_point': '😣',
                    'improvement_opportunity': '💡',
                    'feature_request': '⭐'
                }.get(opp['category'], '📝')

                with st.expander(f"{severity_color} {category_icon} {i}. {opp['title']} (frecuencia: {opp['frequency']})"):
                    col1, col2 = st.columns([2, 1])

                    with col1:
                        st.write(f"**Descripción:** {opp['description']}")
                        if opp['keywords']:
                            st.write(f"**Keywords:** {', '.join(opp['keywords'])}")

                    with col2:
                        st.info(f"**Categoría:** {opp['category']}")
                        st.info(f"**Severidad:** {opp['severity']}")
                        st.info(f"**Fuentes:** {len(opp['sources'])}")
        else:
            st.warning("No se encontraron oportunidades que coincidan con su búsqueda.")


def show_chat_page(analyzer):
    """Show the chat interface"""
    st.header("💬 Chat con IA - Insights de Clientes")
    st.markdown("Haga preguntas sobre los datos de feedback de sus clientes.")

    # Initialize chat history
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []

    # Chat input
    user_input = st.chat_input("Escriba su pregunta aquí...")

    # Display suggested questions
    if not st.session_state.chat_history:
        st.subheader("💡 Preguntas Sugeridas:")
        suggestions = analyzer.chatbot.suggest_questions()

        cols = st.columns(2)
        for i, suggestion in enumerate(suggestions[:6]):  # Show 6 suggestions
            col = cols[i % 2]
            if col.button(f"💭 {suggestion}", key=f"suggestion_{i}"):
                user_input = suggestion

    # Process user input
    if user_input:
        # Add user message to history
        st.session_state.chat_history.append({"role": "user", "content": user_input})

        # Get AI response
        with st.spinner("🧠 Procesando..."):
            response_data = analyzer.chatbot.chat(user_input)
            ai_response = response_data.get('response', 'Lo siento, no pude generar una respuesta.')

            # Add AI response to history
            st.session_state.chat_history.append({"role": "assistant", "content": ai_response})

    # Display chat history
    for message in st.session_state.chat_history:
        if message["role"] == "user":
            with st.chat_message("user"):
                st.write(message["content"])
        else:
            with st.chat_message("assistant"):
                st.write(message["content"])

    # Clear chat button
    if st.session_state.chat_history:
        if st.button("🗑️ Limpiar Conversación"):
            st.session_state.chat_history = []
            st.rerun()


def show_manage_opportunities_page(analyzer):
    """Show opportunity management page"""
    st.header("⚙️ Gestión de Oportunidades")
    st.markdown("Administra el estado y comentarios de las oportunidades identificadas")

    # Date range filter
    st.subheader("🗓️ Filtrar por Fechas")
    col1, col2 = st.columns(2)

    with col1:
        start_date = st.date_input(
            "Fecha inicio",
            value=datetime.now() - pd.Timedelta(days=30),
            help="Fecha de inicio del rango"
        )

    with col2:
        end_date = st.date_input(
            "Fecha fin",
            value=datetime.now(),
            help="Fecha de fin del rango"
        )

    # Status filter
    status_filter = st.selectbox(
        "Filtrar por estado:",
        ["Todos", "nueva", "en_proceso", "solucionada", "descartada", "bloqueada"],
        help="Filtrar oportunidades por estado"
    )

    # Get opportunities
    if st.button("🔍 Buscar Oportunidades"):
        start_datetime = datetime.combine(start_date, datetime.min.time())
        end_datetime = datetime.combine(end_date, datetime.max.time())

        status = None if status_filter == "Todos" else status_filter

        opportunities = analyzer.knowledge_base.get_opportunities_by_date_range(
            start_datetime, end_datetime, status=status
        )

        if opportunities:
            st.success(f"✅ Encontradas {len(opportunities)} oportunidades")

            for i, opp in enumerate(opportunities):
                status_color = {
                    'nueva': '🆕',
                    'en_proceso': '⚙️',
                    'solucionada': '✅',
                    'descartada': '❌',
                    'bloqueada': '🔒'
                }.get(opp['status'], '❓')

                severity_color = {
                    'low': '🟢',
                    'medium': '🟡',
                    'high': '🟠',
                    'critical': '🔴'
                }.get(opp['severity'], '⚪')

                category_icon = {
                    'pain_point': '😣',
                    'improvement_opportunity': '💡',
                    'feature_request': '⭐'
                }.get(opp['category'], '📝')

                with st.expander(f"{status_color} {severity_color} {category_icon} {opp['title']} (x{opp['frequency']})"):
                    col1, col2 = st.columns([2, 1])

                    with col1:
                        st.write(f"**Descripción:** {opp['description']}")
                        st.write(f"**Categoría:** {opp['category']}")
                        st.write(f"**Keywords:** {', '.join(opp['keywords'][:5])}")
                        st.write(f"**Fecha procesamiento:** {opp['processing_date'][:10]}")

                    with col2:
                        st.info(f"**Estado actual:** {opp['status']}")
                        st.info(f"**Severidad:** {opp['severity']}")
                        st.info(f"**Fuentes:** {len(opp['sources'])}")

                    # Edit controls
                    st.markdown("---")
                    st.subheader("🛠️ Editar Oportunidad")

                    edit_col1, edit_col2 = st.columns(2)

                    with edit_col1:
                        new_status = st.selectbox(
                            "Cambiar estado:",
                            ["nueva", "en_proceso", "solucionada", "descartada", "bloqueada"],
                            index=["nueva", "en_proceso", "solucionada", "descartada", "bloqueada"].index(opp['status']),
                            key=f"status_{opp['id']}"
                        )

                        if st.button(f"💾 Actualizar Estado", key=f"update_status_{opp['id']}"):
                            success = analyzer.knowledge_base.update_opportunity_status(opp['id'], new_status)
                            if success:
                                st.success(f"✅ Estado actualizado a: {new_status}")
                                st.rerun()
                            else:
                                st.error("❌ Error al actualizar estado")

                    with edit_col2:
                        current_comments = opp.get('comments', '')
                        new_comments = st.text_area(
                            "Comentarios:",
                            value=current_comments,
                            height=100,
                            key=f"comments_{opp['id']}"
                        )

                        if st.button(f"💬 Actualizar Comentarios", key=f"update_comments_{opp['id']}"):
                            success = analyzer.knowledge_base.update_opportunity_comments(opp['id'], new_comments)
                            if success:
                                st.success("✅ Comentarios actualizados")
                                st.rerun()
                            else:
                                st.error("❌ Error al actualizar comentarios")

                    if current_comments:
                        st.info(f"💬 **Comentarios actuales:** {current_comments}")

        else:
            st.warning("No se encontraron oportunidades en el rango de fechas seleccionado")

    # Summary stats by status
    st.subheader("📊 Resumen por Estado")
    all_opportunities = analyzer.knowledge_base.get_opportunities()

    if all_opportunities:
        status_counts = {}
        for opp in all_opportunities:
            status = opp.get('status', 'nueva')
            status_counts[status] = status_counts.get(status, 0) + 1

        status_df = pd.DataFrame(list(status_counts.items()), columns=['Estado', 'Cantidad'])

        fig = px.bar(status_df, x='Estado', y='Cantidad', title="Oportunidades por Estado")
        st.plotly_chart(fig, use_container_width=True)

        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.metric("🆕 Nuevas", status_counts.get('nueva', 0))
        with col2:
            st.metric("⚙️ En Proceso", status_counts.get('en_proceso', 0))
        with col3:
            st.metric("✅ Solucionadas", status_counts.get('solucionada', 0))
        with col4:
            st.metric("❌ Descartadas", status_counts.get('descartada', 0))
        with col5:
            st.metric("🔒 Bloqueadas", status_counts.get('bloqueada', 0))


def show_history_page(analyzer):
    """Show processing history"""
    st.header("📜 Historial de Procesamiento")

    history = analyzer.get_processing_history()

    if history:
        # Convert to DataFrame for better display
        df = pd.DataFrame(history)

        # Format the display
        df['Status'] = df['status'].apply(lambda x: '✅ Exitoso' if x == 'completed' else '❌ Error')
        df['Fecha'] = pd.to_datetime(df['processed_at']).dt.strftime('%Y-%m-%d %H:%M:%S')
        df['Tamaño (MB)'] = (df['file_size'] / 1024 / 1024).round(2)

        # Select columns to display
        display_df = df[[
            'file_name', 'file_type', 'Status', 'Fecha',
            'Tamaño (MB)', 'items_extracted', 'opportunities_found'
        ]].rename(columns={
            'file_name': 'Archivo',
            'file_type': 'Tipo',
            'items_extracted': 'Elementos',
            'opportunities_found': 'Oportunidades'
        })

        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True
        )

        # Summary stats
        st.subheader("📊 Resumen del Historial")
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            total_files = len(df)
            st.metric("Total Archivos", total_files)

        with col2:
            successful = len(df[df['status'] == 'completed'])
            st.metric("Exitosos", successful)

        with col3:
            total_size = df['file_size'].sum() / 1024 / 1024  # MB
            st.metric("Tamaño Total", f"{total_size:.1f} MB")

        with col4:
            total_opportunities = df['opportunities_found'].sum()
            st.metric("Total Oportunidades", total_opportunities)

    else:
        st.info("No hay historial de procesamiento disponible.")


if __name__ == "__main__":
    main()