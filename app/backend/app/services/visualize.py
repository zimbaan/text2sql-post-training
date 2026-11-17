"""Service for generating relationship visualization data."""

import logging
from typing import Dict, List, Optional, Set

from sqlalchemy.engine import Engine

from app.db.introspect import introspect_tables

logger = logging.getLogger(__name__)


class VisualizationService:
    """Service for generating table relationship graphs."""

    def generate_graph(
        self,
        engine: Engine,
        schema: Optional[str],
        table_names: List[str],
    ) -> Dict[str, List[dict]]:
        """Generate graph JSON for table relationships.

        Args:
            engine: SQLAlchemy engine
            schema: Schema name (optional)
            table_names: List of table names to include

        Returns:
            Dictionary with 'nodes' and 'edges' lists
        """
        dialect = engine.dialect.name

        # SQLite doesn't use schemas; incoming names may be prefixed like "default.table"
        if dialect == "sqlite":
            schema = None
            table_names = [t.split(".")[-1] for t in table_names]
        elif dialect in ("mysql", "mariadb"):
            # MySQL inspector expects schema separate from table name
            db_name = schema or engine.url.database
            normalized = []
            for t in table_names:
                if "." in t and t.lower().startswith((db_name or "").lower() + "."):
                    normalized.append(t.split(".", 1)[1])
                else:
                    normalized.append(t)
            table_names = normalized

        # Introspect tables
        tables_info = introspect_tables(engine, schema, table_names)

        # Build nodes with column metadata
        nodes = []
        node_ids: Set[str] = set()

        for table in tables_info:
            if "error" in table:
                continue
            table_id = table["name"].lower()
            if table_id not in node_ids:
                fk_map = {fk["column"]: fk for fk in table.get("foreign_keys", [])}
                node_columns = []
                for col in table.get("columns", []):
                    fk = fk_map.get(col["name"])
                    node_columns.append(
                        {
                            "name": col["name"],
                            "type": str(col.get("type", "")),
                            "is_primary_key": col["name"] in table.get("primary_key", []),
                            "is_foreign_key": fk is not None,
                            "ref_table": fk.get("ref_table") if fk else None,
                            "ref_column": fk.get("ref_column") if fk else None,
                        }
                    )

                nodes.append({"id": table_id, "label": table["name"], "columns": node_columns})
                node_ids.add(table_id)

        # Build edges from foreign keys
        edges = []
        edge_set: Set[tuple] = set()

        for table in tables_info:
            if "error" in table:
                continue

            source_id = table["name"].lower()
            foreign_keys = table.get("foreign_keys", [])

            for fk in foreign_keys:
                ref_table = fk.get("ref_table", "").lower()
                column = fk.get("column", "")
                ref_column = fk.get("ref_column", "")

                # Create edge if both tables are in scope
                if ref_table in node_ids and source_id in node_ids:
                    edge_key = (source_id, ref_table, column, ref_column)
                    # Avoid duplicate edges
                    if edge_key not in edge_set:
                        edge_label = f"{table['name']}.{column} -> {fk['ref_table']}.{ref_column}"
                        edges.append(
                            {
                                "source": source_id,
                                "target": ref_table,
                                "label": edge_label,
                                "source_column": column,
                                "target_column": ref_column,
                                "cardinality": "N:1",  # FK side is many, referenced is one
                            }
                        )
                        edge_set.add(edge_key)

        return {
            "nodes": nodes,
            "edges": edges,
        }


# Global service instance
_visualization_service: Optional[VisualizationService] = None


def get_visualization_service() -> VisualizationService:
    """Get or create global visualization service instance."""
    global _visualization_service
    if _visualization_service is None:
        _visualization_service = VisualizationService()
    return _visualization_service
