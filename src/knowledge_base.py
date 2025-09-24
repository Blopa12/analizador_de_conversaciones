"""
Knowledge base management for storing and retrieving opportunities and insights
"""

import sqlite3
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
import os

from ai_analyzer import Opportunity
from content_extractor import ContentItem


class KnowledgeBase:
    """Manages the database for storing opportunities, content items, and insights"""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or os.getenv('DB_PATH', 'data/customer_insights.db')
        self._ensure_db_directory()
        self._init_database()

    def _ensure_db_directory(self):
        """Ensure the database directory exists"""
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)

    def _init_database(self):
        """Initialize the database with required tables"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Create content_items table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS content_items (
                    id TEXT PRIMARY KEY,
                    content_type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    metadata TEXT,
                    source_file TEXT NOT NULL,
                    timestamp DATETIME,
                    customer_id TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Create opportunities table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS opportunities (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    category TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    frequency INTEGER NOT NULL DEFAULT 1,
                    sources TEXT NOT NULL,
                    keywords TEXT NOT NULL,
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL,
                    processing_date DATETIME NOT NULL,
                    status TEXT DEFAULT 'nueva',
                    comments TEXT DEFAULT '',
                    merged_from TEXT
                )
            ''')

            # Create file_processing_log table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS file_processing_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_name TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    file_type TEXT NOT NULL,
                    file_size INTEGER,
                    processed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    items_extracted INTEGER DEFAULT 0,
                    opportunities_found INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'completed'
                )
            ''')

            # Create insights_cache table for storing AI-generated insights
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS insights_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    query_type TEXT NOT NULL,
                    query_params TEXT,
                    insight TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    expires_at DATETIME
                )
            ''')

            # Update existing tables with new columns if they don't exist
            self._update_schema_if_needed(cursor)

            conn.commit()

    def _update_schema_if_needed(self, cursor):
        """Update existing database schema with new columns"""
        try:
            # Check if new columns exist in opportunities table
            cursor.execute("PRAGMA table_info(opportunities)")
            columns = [row[1] for row in cursor.fetchall()]

            # Add processing_date column if it doesn't exist
            if 'processing_date' not in columns:
                cursor.execute('''
                    ALTER TABLE opportunities ADD COLUMN processing_date DATETIME
                ''')
                # Update existing records with created_at as processing_date
                cursor.execute('''
                    UPDATE opportunities SET processing_date = created_at WHERE processing_date IS NULL
                ''')
                print("Added processing_date column to opportunities table")

            # Add status column if it doesn't exist
            if 'status' not in columns:
                cursor.execute('''
                    ALTER TABLE opportunities ADD COLUMN status TEXT
                ''')
                # Update existing records with 'nueva' as default status
                cursor.execute('''
                    UPDATE opportunities SET status = 'nueva' WHERE status IS NULL
                ''')
                print("Added status column to opportunities table")

            # Add comments column if it doesn't exist
            if 'comments' not in columns:
                cursor.execute('''
                    ALTER TABLE opportunities ADD COLUMN comments TEXT
                ''')
                # Update existing records with empty comments
                cursor.execute('''
                    UPDATE opportunities SET comments = '' WHERE comments IS NULL
                ''')
                print("Added comments column to opportunities table")

        except Exception as e:
            print(f"Warning: Could not update schema: {str(e)}")

    def store_content_items(self, content_items: List[ContentItem]) -> int:
        """
        Store content items in the database

        Args:
            content_items: List of ContentItem objects to store

        Returns:
            Number of items stored
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            stored_count = 0
            for item in content_items:
                try:
                    cursor.execute('''
                        INSERT OR REPLACE INTO content_items
                        (id, content_type, content, metadata, source_file, timestamp, customer_id)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        item.id,
                        item.content_type,
                        item.content,
                        json.dumps(item.metadata),
                        item.source_file,
                        item.timestamp,
                        item.customer_id
                    ))
                    stored_count += 1
                except Exception as e:
                    print(f"Warning: Failed to store content item {item.id}: {str(e)}")

            conn.commit()
            return stored_count

    def store_opportunities(self, opportunities: List[Opportunity]) -> int:
        """
        Store opportunities in the database

        Args:
            opportunities: List of Opportunity objects to store

        Returns:
            Number of opportunities stored
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            stored_count = 0
            for opp in opportunities:
                try:
                    cursor.execute('''
                        INSERT OR REPLACE INTO opportunities
                        (id, title, description, category, severity, frequency, sources, keywords, created_at, updated_at, processing_date, status, comments, merged_from)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        opp.id,
                        opp.title,
                        opp.description,
                        opp.category,
                        opp.severity,
                        opp.frequency,
                        json.dumps(opp.sources),
                        json.dumps(opp.keywords),
                        opp.created_at,
                        opp.updated_at,
                        getattr(opp, 'processing_date', opp.created_at),
                        getattr(opp, 'status', 'nueva'),
                        getattr(opp, 'comments', ''),
                        json.dumps(opp.merged_from) if opp.merged_from else None
                    ))
                    stored_count += 1
                except Exception as e:
                    print(f"Warning: Failed to store opportunity {opp.id}: {str(e)}")

            conn.commit()
            return stored_count

    def get_opportunities(
        self,
        category: Optional[str] = None,
        severity: Optional[str] = None,
        min_frequency: Optional[int] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve opportunities from the database

        Args:
            category: Filter by category
            severity: Filter by severity
            min_frequency: Minimum frequency threshold
            limit: Maximum number of results

        Returns:
            List of opportunity dictionaries
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            query = "SELECT * FROM opportunities WHERE 1=1"
            params = []

            if category:
                query += " AND category = ?"
                params.append(category)

            if severity:
                query += " AND severity = ?"
                params.append(severity)

            if min_frequency:
                query += " AND frequency >= ?"
                params.append(min_frequency)

            query += " ORDER BY frequency DESC, severity DESC"

            if limit:
                query += " LIMIT ?"
                params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()

            # Convert to dictionaries
            columns = [desc[0] for desc in cursor.description]
            opportunities = []

            for row in rows:
                opp_dict = dict(zip(columns, row))
                # Parse JSON fields
                opp_dict['sources'] = json.loads(opp_dict['sources'])
                opp_dict['keywords'] = json.loads(opp_dict['keywords'])
                if opp_dict['merged_from']:
                    opp_dict['merged_from'] = json.loads(opp_dict['merged_from'])

                # Set defaults for new fields if they don't exist
                if 'processing_date' not in opp_dict or opp_dict['processing_date'] is None:
                    opp_dict['processing_date'] = opp_dict['created_at']
                if 'status' not in opp_dict or opp_dict['status'] is None:
                    opp_dict['status'] = 'nueva'
                if 'comments' not in opp_dict or opp_dict['comments'] is None:
                    opp_dict['comments'] = ''

                opportunities.append(opp_dict)

            return opportunities

    def get_content_items(
        self,
        content_type: Optional[str] = None,
        customer_id: Optional[str] = None,
        source_file: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve content items from the database

        Args:
            content_type: Filter by content type
            customer_id: Filter by customer ID
            source_file: Filter by source file
            limit: Maximum number of results

        Returns:
            List of content item dictionaries
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            query = "SELECT * FROM content_items WHERE 1=1"
            params = []

            if content_type:
                query += " AND content_type = ?"
                params.append(content_type)

            if customer_id:
                query += " AND customer_id = ?"
                params.append(customer_id)

            if source_file:
                query += " AND source_file = ?"
                params.append(source_file)

            query += " ORDER BY created_at DESC"

            if limit:
                query += " LIMIT ?"
                params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()

            # Convert to dictionaries
            columns = [desc[0] for desc in cursor.description]
            items = []

            for row in rows:
                item_dict = dict(zip(columns, row))
                # Parse JSON metadata
                if item_dict['metadata']:
                    item_dict['metadata'] = json.loads(item_dict['metadata'])
                items.append(item_dict)

            return items

    def log_file_processing(
        self,
        file_name: str,
        file_path: str,
        file_type: str,
        file_size: int,
        items_extracted: int,
        opportunities_found: int,
        status: str = 'completed'
    ):
        """Log file processing results"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO file_processing_log
                (file_name, file_path, file_type, file_size, items_extracted, opportunities_found, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (file_name, file_path, file_type, file_size, items_extracted, opportunities_found, status))
            conn.commit()

    def get_processing_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get file processing history"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM file_processing_log
                ORDER BY processed_at DESC
                LIMIT ?
            ''', (limit,))

            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in rows]

    def get_summary_stats(self) -> Dict[str, Any]:
        """Get summary statistics about the knowledge base"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            stats = {}

            # Total content items
            cursor.execute("SELECT COUNT(*) FROM content_items")
            stats['total_content_items'] = cursor.fetchone()[0]

            # Content items by type
            cursor.execute('''
                SELECT content_type, COUNT(*)
                FROM content_items
                GROUP BY content_type
            ''')
            stats['items_by_type'] = dict(cursor.fetchall())

            # Total opportunities
            cursor.execute("SELECT COUNT(*) FROM opportunities")
            stats['total_opportunities'] = cursor.fetchone()[0]

            # Opportunities by category
            cursor.execute('''
                SELECT category, COUNT(*)
                FROM opportunities
                GROUP BY category
            ''')
            stats['opportunities_by_category'] = dict(cursor.fetchall())

            # Opportunities by severity
            cursor.execute('''
                SELECT severity, COUNT(*)
                FROM opportunities
                GROUP BY severity
            ''')
            stats['opportunities_by_severity'] = dict(cursor.fetchall())

            # Top keywords
            cursor.execute("SELECT keywords FROM opportunities")
            all_keywords = []
            for row in cursor.fetchall():
                keywords = json.loads(row[0])
                all_keywords.extend(keywords)

            from collections import Counter
            keyword_counts = Counter(all_keywords)
            stats['top_keywords'] = keyword_counts.most_common(10)

            # Files processed
            cursor.execute("SELECT COUNT(*) FROM file_processing_log")
            stats['files_processed'] = cursor.fetchone()[0]

            return stats

    def search_opportunities(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Search opportunities by text query

        Args:
            query: Search query
            limit: Maximum number of results

        Returns:
            List of matching opportunity dictionaries
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Simple text search in title and description
            search_query = f"%{query}%"
            cursor.execute('''
                SELECT * FROM opportunities
                WHERE title LIKE ? OR description LIKE ? OR keywords LIKE ?
                ORDER BY frequency DESC, severity DESC
                LIMIT ?
            ''', (search_query, search_query, search_query, limit))

            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            opportunities = []

            for row in rows:
                opp_dict = dict(zip(columns, row))
                # Parse JSON fields
                opp_dict['sources'] = json.loads(opp_dict['sources'])
                opp_dict['keywords'] = json.loads(opp_dict['keywords'])
                if opp_dict['merged_from']:
                    opp_dict['merged_from'] = json.loads(opp_dict['merged_from'])

                opportunities.append(opp_dict)

            return opportunities

    def cache_insight(self, query_type: str, query_params: Dict[str, Any], insight: str, expires_hours: int = 24):
        """Cache an AI-generated insight"""
        expires_at = datetime.now().timestamp() + (expires_hours * 3600)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO insights_cache (query_type, query_params, insight, expires_at)
                VALUES (?, ?, ?, ?)
            ''', (query_type, json.dumps(query_params), insight, expires_at))
            conn.commit()

    def get_cached_insight(self, query_type: str, query_params: Dict[str, Any]) -> Optional[str]:
        """Retrieve a cached insight if available and not expired"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT insight FROM insights_cache
                WHERE query_type = ? AND query_params = ? AND expires_at > ?
                ORDER BY created_at DESC
                LIMIT 1
            ''', (query_type, json.dumps(query_params), datetime.now().timestamp()))

            result = cursor.fetchone()
            return result[0] if result else None

    def update_opportunity_status(self, opportunity_id: str, status: str) -> bool:
        """Update the status of an opportunity"""
        valid_statuses = ['nueva', 'descartada', 'en_proceso', 'solucionada', 'bloqueada']
        if status not in valid_statuses:
            raise ValueError(f"Invalid status. Must be one of: {valid_statuses}")

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE opportunities
                SET status = ?, updated_at = ?
                WHERE id = ?
            ''', (status, datetime.now(), opportunity_id))

            success = cursor.rowcount > 0
            conn.commit()
            return success

    def update_opportunity_comments(self, opportunity_id: str, comments: str) -> bool:
        """Update the comments of an opportunity"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE opportunities
                SET comments = ?, updated_at = ?
                WHERE id = ?
            ''', (comments, datetime.now(), opportunity_id))

            success = cursor.rowcount > 0
            conn.commit()
            return success

    def get_opportunities_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        status: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get opportunities within a date range

        Args:
            start_date: Start of date range
            end_date: End of date range
            status: Optional status filter
            limit: Maximum number of results

        Returns:
            List of opportunity dictionaries
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            query = "SELECT * FROM opportunities WHERE processing_date BETWEEN ? AND ?"
            params = [start_date, end_date]

            if status:
                query += " AND status = ?"
                params.append(status)

            query += " ORDER BY processing_date DESC, frequency DESC"

            if limit:
                query += " LIMIT ?"
                params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()

            # Convert to dictionaries
            columns = [desc[0] for desc in cursor.description]
            opportunities = []

            for row in rows:
                opp_dict = dict(zip(columns, row))
                # Parse JSON fields
                opp_dict['sources'] = json.loads(opp_dict['sources'])
                opp_dict['keywords'] = json.loads(opp_dict['keywords'])
                if opp_dict['merged_from']:
                    opp_dict['merged_from'] = json.loads(opp_dict['merged_from'])

                # Set defaults for new fields if they don't exist
                if 'processing_date' not in opp_dict or opp_dict['processing_date'] is None:
                    opp_dict['processing_date'] = opp_dict['created_at']
                if 'status' not in opp_dict or opp_dict['status'] is None:
                    opp_dict['status'] = 'nueva'
                if 'comments' not in opp_dict or opp_dict['comments'] is None:
                    opp_dict['comments'] = ''

                opportunities.append(opp_dict)

            return opportunities