"""Visualization router."""

import logging

from fastapi import APIRouter, HTTPException, status

from app.db.manager import get_connection_manager
from app.models.dtos import GraphEdge, GraphNode, VisualizeRequest, VisualizeResponse
from app.services.visualize import get_visualization_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/visualize", tags=["Visualization"])


@router.post("/{connection_id}", response_model=VisualizeResponse)
async def visualize_tables(connection_id: str, request: VisualizeRequest) -> VisualizeResponse:
    """Generate relationship graph data for tables.

    Args:
        connection_id: Connection identifier
        request: Visualization request with table names and schema

    Returns:
        Visualization response with nodes and edges

    Raises:
        HTTPException: If connection not found or visualization fails
    """
    manager = get_connection_manager()
    conn_info = manager.get_connection(connection_id)

    if not conn_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "CONNECTION_NOT_FOUND",
                    "message": f"Connection {connection_id} not found or expired",
                    "details": None,
                }
            },
        )

    try:
        # SQLite has no schemas; avoid passing schema names that break introspection
        effective_schema = None if conn_info.dialect == "sqlite" else request.schema

        service = get_visualization_service()
        graph = service.generate_graph(
            engine=conn_info.engine,
            schema=effective_schema,
            table_names=request.tables,
        )

        return VisualizeResponse(
            nodes=[
                GraphNode(
                    id=node["id"],
                    label=node["label"],
                    columns=node.get("columns", []),
                )
                for node in graph["nodes"]
            ],
            edges=[
                GraphEdge(
                    source=edge["source"],
                    target=edge["target"],
                    label=edge["label"],
                    source_column=edge.get("source_column"),
                    target_column=edge.get("target_column"),
                    cardinality=edge.get("cardinality"),
                )
                for edge in graph["edges"]
            ],
        )
    except Exception as e:
        logger.error(f"Visualization failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "VISUALIZATION_FAILED",
                    "message": f"Failed to generate visualization: {e}",
                    "details": None,
                }
            },
        )

