import json
import re
from typing import Any, Dict, Iterable, List, Optional, Sequence

from retrieval.model import GraphEdge, GraphNode, GraphSubgraph, GraphSummary
from retrieval.engines.local_engine.graph.repository.base import BaseGraphRepository

try:
    import psycopg  # type: ignore
except ImportError:  # pragma: no cover
    psycopg = None


class AgeGraphRepository(BaseGraphRepository):
    """
    Apache AGE backend with mirrored relational metadata tables.

    AGE stores the graph itself. The metadata tables keep the application-facing
    shape stable for inspection and search without requiring agtype parsing.
    """

    NODE_TABLE = "rag_graph_nodes"
    EDGE_TABLE = "rag_graph_edges"
    AGE_NODE_LABEL = "Entity"
    AGE_EDGE_LABEL = "RELATED"

    def __init__(self, dsn: str, graph_name: str = "rag_graph", schema: str = "public", create_if_missing: bool = True):
        self.dsn = dsn
        self.graph_name = graph_name
        self.schema = schema
        self.create_if_missing = create_if_missing
        self._conn = None
        self._session_ready = False
        self._graph_ready = False

    def ensure_graph(self) -> None:
        self._require_driver()
        if not self.dsn:
            raise RuntimeError("Apache AGE backend requires a PostgreSQL DSN.")

        self._ensure_session()
        if self._graph_ready:
            return

        graph_exists = self._fetchone(
            "SELECT 1 FROM ag_catalog.ag_graph WHERE name = %s",
            (self.graph_name,),
        )
        if graph_exists is None:
            if not self.create_if_missing:
                raise RuntimeError(f'AGE graph "{self.graph_name}" does not exist.')
            self._execute("SELECT ag_catalog.create_graph(%s);", (self.graph_name,))

        self._ensure_metadata_tables()
        self._graph_ready = True

    def upsert_nodes(self, nodes: List[GraphNode]) -> None:
        self.ensure_graph()
        for node in self._merge_node_batch(nodes):
            existing = self._get_node(node.id)
            merged = self._merge_node(existing, node)
            self._upsert_node_metadata(merged)
            self._upsert_age_node(merged)

    def upsert_edges(self, edges: List[GraphEdge]) -> None:
        self.ensure_graph()
        for edge in self._merge_edge_batch(edges):
            existing = self._get_edge(edge.id)
            merged = self._merge_edge(existing, edge)
            self._upsert_edge_metadata(merged)
            self._upsert_age_edge(merged)

    def get_summary(self) -> GraphSummary:
        self.ensure_graph()
        node_count_row = self._fetchone(
            f"SELECT COUNT(*) FROM {self._qualified(self.NODE_TABLE)} WHERE graph_name = %s",
            (self.graph_name,),
        )
        edge_count_row = self._fetchone(
            f"SELECT COUNT(*) FROM {self._qualified(self.EDGE_TABLE)} WHERE graph_name = %s",
            (self.graph_name,),
        )
        label_rows = self._fetchall(
            f"""
            SELECT label, COUNT(*)
            FROM {self._qualified(self.NODE_TABLE)}
            WHERE graph_name = %s
            GROUP BY label
            ORDER BY label
            """,
            (self.graph_name,),
        )
        relation_rows = self._fetchall(
            f"""
            SELECT relation, COUNT(*)
            FROM {self._qualified(self.EDGE_TABLE)}
            WHERE graph_name = %s
            GROUP BY relation
            ORDER BY relation
            """,
            (self.graph_name,),
        )
        return GraphSummary(
            graph_name=self.graph_name,
            backend="age",
            node_count=int(node_count_row[0]) if node_count_row else 0,
            edge_count=int(edge_count_row[0]) if edge_count_row else 0,
            labels={row[0]: int(row[1]) for row in label_rows},
            relations={row[0]: int(row[1]) for row in relation_rows},
        )

    def list_nodes(self, label: str | None = None, limit: int = 100) -> List[GraphNode]:
        self.ensure_graph()
        sql = f"""
            SELECT node_id, name, label, properties::text, segment_ids::text
            FROM {self._qualified(self.NODE_TABLE)}
            WHERE graph_name = %s
        """
        params: List[Any] = [self.graph_name]
        if label:
            sql += " AND label = %s"
            params.append(label)
        sql += " ORDER BY name, node_id LIMIT %s"
        params.append(limit)
        rows = self._fetchall(sql, tuple(params))
        return [self._node_from_row(row) for row in rows]

    def list_edges(self, relation: str | None = None, limit: int = 100) -> List[GraphEdge]:
        self.ensure_graph()
        sql = f"""
            SELECT edge_id, source_id, target_id, relation, properties::text, segment_ids::text
            FROM {self._qualified(self.EDGE_TABLE)}
            WHERE graph_name = %s
        """
        params: List[Any] = [self.graph_name]
        if relation:
            sql += " AND relation = %s"
            params.append(relation)
        sql += " ORDER BY relation, edge_id LIMIT %s"
        params.append(limit)
        rows = self._fetchall(sql, tuple(params))
        return [self._edge_from_row(row) for row in rows]

    def get_subgraph(self, node_ids: List[str], max_hops: int = 1) -> GraphSubgraph:
        self.ensure_graph()
        frontier = {node_id for node_id in node_ids if node_id}
        visited = set(frontier)
        collected_edges: Dict[str, GraphEdge] = {}

        for _ in range(max(0, max_hops)):
            if not frontier:
                break
            edges = self._list_connected_edges(frontier)
            next_frontier = set()
            for edge in edges:
                collected_edges[edge.id] = edge
                if edge.source_id not in visited:
                    next_frontier.add(edge.source_id)
                if edge.target_id not in visited:
                    next_frontier.add(edge.target_id)
            visited.update(next_frontier)
            frontier = next_frontier

        nodes = self._list_nodes_by_ids(visited)
        return GraphSubgraph(nodes=nodes, edges=list(collected_edges.values()))

    def search_nodes(self, query: str, limit: int = 10) -> List[GraphNode]:
        self.ensure_graph()
        lowered = query.strip().lower()
        if not lowered:
            return []

        rows = self._fetchall(
            f"""
            SELECT node_id, name, label, properties::text, segment_ids::text
            FROM {self._qualified(self.NODE_TABLE)}
            WHERE graph_name = %s
              AND (
                LOWER(name) LIKE %s
                OR LOWER(label) LIKE %s
                OR LOWER(properties::text) LIKE %s
              )
            ORDER BY
              CASE
                WHEN LOWER(name) = %s THEN 0
                WHEN LOWER(name) LIKE %s THEN 1
                ELSE 2
              END,
              name,
              node_id
            LIMIT %s
            """,
            (
                self.graph_name,
                f"%{lowered}%",
                f"%{lowered}%",
                f"%{lowered}%",
                lowered,
                f"{lowered}%",
                limit,
            ),
        )
        return [self._node_from_row(row) for row in rows]

    def _ensure_session(self) -> None:
        if self._session_ready:
            return

        self._execute("CREATE EXTENSION IF NOT EXISTS age;")
        self._execute("LOAD 'age';")
        self._execute('SET search_path = ag_catalog, "$user", public;')
        self._session_ready = True

    def _ensure_metadata_tables(self) -> None:
        self._execute(f"CREATE SCHEMA IF NOT EXISTS {self._quote_identifier(self.schema)};")
        self._execute(
            f"""
            CREATE TABLE IF NOT EXISTS {self._qualified(self.NODE_TABLE)} (
                graph_name TEXT NOT NULL,
                node_id TEXT NOT NULL,
                name TEXT NOT NULL,
                label TEXT NOT NULL,
                properties JSONB NOT NULL DEFAULT '{{}}'::jsonb,
                segment_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
                PRIMARY KEY (graph_name, node_id)
            );
            """
        )
        self._execute(
            f"""
            CREATE TABLE IF NOT EXISTS {self._qualified(self.EDGE_TABLE)} (
                graph_name TEXT NOT NULL,
                edge_id TEXT NOT NULL,
                source_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                relation TEXT NOT NULL,
                properties JSONB NOT NULL DEFAULT '{{}}'::jsonb,
                segment_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
                PRIMARY KEY (graph_name, edge_id)
            );
            """
        )
        self._execute(
            f"""
            CREATE INDEX IF NOT EXISTS idx_{self.NODE_TABLE}_graph_label
            ON {self._qualified(self.NODE_TABLE)} (graph_name, label);
            """
        )
        self._execute(
            f"""
            CREATE INDEX IF NOT EXISTS idx_{self.NODE_TABLE}_graph_name
            ON {self._qualified(self.NODE_TABLE)} (graph_name, name);
            """
        )
        self._execute(
            f"""
            CREATE INDEX IF NOT EXISTS idx_{self.EDGE_TABLE}_graph_relation
            ON {self._qualified(self.EDGE_TABLE)} (graph_name, relation);
            """
        )
        self._execute(
            f"""
            CREATE INDEX IF NOT EXISTS idx_{self.EDGE_TABLE}_graph_source_target
            ON {self._qualified(self.EDGE_TABLE)} (graph_name, source_id, target_id);
            """
        )

    def _upsert_node_metadata(self, node: GraphNode) -> None:
        self._execute(
            f"""
            INSERT INTO {self._qualified(self.NODE_TABLE)}
                (graph_name, node_id, name, label, properties, segment_ids)
            VALUES (%s, %s, %s, %s, %s::jsonb, %s::jsonb)
            ON CONFLICT (graph_name, node_id)
            DO UPDATE SET
                name = EXCLUDED.name,
                label = EXCLUDED.label,
                properties = EXCLUDED.properties,
                segment_ids = EXCLUDED.segment_ids;
            """,
            (
                self.graph_name,
                node.id,
                node.name,
                node.label,
                json.dumps(node.properties, ensure_ascii=True),
                json.dumps(node.segment_ids),
            ),
        )

    def _upsert_edge_metadata(self, edge: GraphEdge) -> None:
        self._execute(
            f"""
            INSERT INTO {self._qualified(self.EDGE_TABLE)}
                (graph_name, edge_id, source_id, target_id, relation, properties, segment_ids)
            VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s::jsonb)
            ON CONFLICT (graph_name, edge_id)
            DO UPDATE SET
                source_id = EXCLUDED.source_id,
                target_id = EXCLUDED.target_id,
                relation = EXCLUDED.relation,
                properties = EXCLUDED.properties,
                segment_ids = EXCLUDED.segment_ids;
            """,
            (
                self.graph_name,
                edge.id,
                edge.source_id,
                edge.target_id,
                edge.relation,
                json.dumps(edge.properties, ensure_ascii=True),
                json.dumps(edge.segment_ids),
            ),
        )

    def _upsert_age_node(self, node: GraphNode) -> None:
        query = f"""
        MERGE (n:{self.AGE_NODE_LABEL} {{entity_id: {self._literal(node.id)}}})
        SET n.name = {self._literal(node.name)},
            n.source_label = {self._literal(node.label)},
            n.segment_ids = {self._literal(node.segment_ids)},
            n.payload_json = {self._literal(json.dumps(node.properties, ensure_ascii=True))}
        RETURN n
        """
        self._run_cypher(query)

    def _upsert_age_edge(self, edge: GraphEdge) -> None:
        query = f"""
        MATCH (source:{self.AGE_NODE_LABEL} {{entity_id: {self._literal(edge.source_id)}}}),
              (target:{self.AGE_NODE_LABEL} {{entity_id: {self._literal(edge.target_id)}}})
        MERGE (source)-[r:{self.AGE_EDGE_LABEL} {{edge_id: {self._literal(edge.id)}}}]->(target)
        SET r.relation = {self._literal(edge.relation)},
            r.segment_ids = {self._literal(edge.segment_ids)},
            r.payload_json = {self._literal(json.dumps(edge.properties, ensure_ascii=True))}
        RETURN r
        """
        self._run_cypher(query)

    def _list_connected_edges(self, node_ids: Iterable[str]) -> List[GraphEdge]:
        ids = list(node_ids)
        if not ids:
            return []
        rows = self._fetchall(
            f"""
            SELECT edge_id, source_id, target_id, relation, properties::text, segment_ids::text
            FROM {self._qualified(self.EDGE_TABLE)}
            WHERE graph_name = %s
              AND (source_id = ANY(%s) OR target_id = ANY(%s))
            ORDER BY edge_id
            """,
            (self.graph_name, ids, ids),
        )
        return [self._edge_from_row(row) for row in rows]

    def _list_nodes_by_ids(self, node_ids: Iterable[str]) -> List[GraphNode]:
        ids = list(node_ids)
        if not ids:
            return []
        rows = self._fetchall(
            f"""
            SELECT node_id, name, label, properties::text, segment_ids::text
            FROM {self._qualified(self.NODE_TABLE)}
            WHERE graph_name = %s
              AND node_id = ANY(%s)
            ORDER BY name, node_id
            """,
            (self.graph_name, ids),
        )
        return [self._node_from_row(row) for row in rows]

    def _get_node(self, node_id: str) -> Optional[GraphNode]:
        row = self._fetchone(
            f"""
            SELECT node_id, name, label, properties::text, segment_ids::text
            FROM {self._qualified(self.NODE_TABLE)}
            WHERE graph_name = %s AND node_id = %s
            """,
            (self.graph_name, node_id),
        )
        return self._node_from_row(row) if row else None

    def _get_edge(self, edge_id: str) -> Optional[GraphEdge]:
        row = self._fetchone(
            f"""
            SELECT edge_id, source_id, target_id, relation, properties::text, segment_ids::text
            FROM {self._qualified(self.EDGE_TABLE)}
            WHERE graph_name = %s AND edge_id = %s
            """,
            (self.graph_name, edge_id),
        )
        return self._edge_from_row(row) if row else None

    def _merge_node_batch(self, nodes: Sequence[GraphNode]) -> List[GraphNode]:
        merged: Dict[str, GraphNode] = {}
        for node in nodes:
            merged[node.id] = self._merge_node(merged.get(node.id), node)
        return list(merged.values())

    def _merge_edge_batch(self, edges: Sequence[GraphEdge]) -> List[GraphEdge]:
        merged: Dict[str, GraphEdge] = {}
        for edge in edges:
            merged[edge.id] = self._merge_edge(merged.get(edge.id), edge)
        return list(merged.values())

    def _merge_node(self, existing: Optional[GraphNode], incoming: GraphNode) -> GraphNode:
        if existing is None:
            return incoming.model_copy(deep=True)
        merged = existing.model_copy(deep=True)
        merged.name = incoming.name or existing.name
        merged.label = incoming.label or existing.label
        merged.properties.update(incoming.properties)
        merged.segment_ids = sorted(set(existing.segment_ids + incoming.segment_ids))
        return merged

    def _merge_edge(self, existing: Optional[GraphEdge], incoming: GraphEdge) -> GraphEdge:
        if existing is None:
            return incoming.model_copy(deep=True)
        merged = existing.model_copy(deep=True)
        merged.source_id = incoming.source_id or existing.source_id
        merged.target_id = incoming.target_id or existing.target_id
        merged.relation = incoming.relation or existing.relation
        merged.properties.update(incoming.properties)
        merged.segment_ids = sorted(set(existing.segment_ids + incoming.segment_ids))
        return merged

    def _run_cypher(self, query: str) -> None:
        self._execute(
            "SELECT * FROM ag_catalog.cypher(%s, %s) AS (result agtype);",
            (self.graph_name, query),
        )

    def _execute(self, sql: str, params: Sequence[Any] = ()) -> None:
        conn = self._connection()
        with conn.cursor() as cursor:
            cursor.execute(sql, params)

    def _fetchone(self, sql: str, params: Sequence[Any] = ()) -> Optional[Sequence[Any]]:
        conn = self._connection()
        with conn.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.fetchone()

    def _fetchall(self, sql: str, params: Sequence[Any] = ()) -> List[Sequence[Any]]:
        conn = self._connection()
        with conn.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.fetchall()

    def _connection(self):
        if self._conn is None:
            self._conn = psycopg.connect(self.dsn, autocommit=True)
        return self._conn

    def _node_from_row(self, row: Sequence[Any]) -> GraphNode:
        return GraphNode(
            id=str(row[0]),
            name=str(row[1]),
            label=str(row[2]),
            properties=self._json_value(row[3], default={}),
            segment_ids=self._segment_ids(row[4]),
        )

    def _edge_from_row(self, row: Sequence[Any]) -> GraphEdge:
        return GraphEdge(
            id=str(row[0]),
            source_id=str(row[1]),
            target_id=str(row[2]),
            relation=str(row[3]),
            properties=self._json_value(row[4], default={}),
            segment_ids=self._segment_ids(row[5]),
        )

    def _json_value(self, value: Any, default: Any) -> Any:
        if value is None:
            return default
        if isinstance(value, (dict, list)):
            return value
        if isinstance(value, str):
            return json.loads(value)
        return default

    def _segment_ids(self, value: Any) -> List[int]:
        parsed = self._json_value(value, default=[])
        result: List[int] = []
        for item in parsed:
            try:
                result.append(int(item))
            except (TypeError, ValueError):
                continue
        return result

    def _qualified(self, table_name: str) -> str:
        return f"{self._quote_identifier(self.schema)}.{self._quote_identifier(table_name)}"

    def _quote_identifier(self, identifier: str) -> str:
        return '"' + identifier.replace('"', '""') + '"'

    def _literal(self, value: Any) -> str:
        if value is None:
            return "NULL"
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return str(value)
        if isinstance(value, list):
            return "[" + ", ".join(self._literal(item) for item in value) + "]"
        if isinstance(value, dict):
            items = ", ".join(f"{self._safe_key(key)}: {self._literal(item)}" for key, item in value.items())
            return "{" + items + "}"
        escaped = str(value).replace("\\", "\\\\").replace("'", "\\'")
        return f"'{escaped}'"

    def _safe_key(self, value: Any) -> str:
        key = str(value)
        if re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", key):
            return key
        return json.dumps(key)

    def _require_driver(self) -> None:
        if psycopg is None:
            raise RuntimeError("psycopg is required to use the Apache AGE graph backend.")
