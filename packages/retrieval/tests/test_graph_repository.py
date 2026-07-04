import unittest

from retrieval.model import GraphEdge, GraphNode
from retrieval.engines.local_engine.graph.repository.age import AgeGraphRepository


class FakeAgeGraphRepository(AgeGraphRepository):
    def __init__(self):
        super().__init__(
            dsn="postgresql://fake",
            graph_name="repo_graph",
            schema="rag_runtime",
            create_if_missing=True,
        )
        self.graph_exists = False
        self.node_rows = {}
        self.edge_rows = {}
        self.executed_sql = []
        self.cypher_queries = []

    def _require_driver(self) -> None:
        return None

    def _execute(self, sql, params=()):
        normalized = " ".join(sql.split())
        self.executed_sql.append((normalized, params))
        if "SELECT ag_catalog.create_graph" in normalized:
            self.graph_exists = True
            return

        if f'INSERT INTO "{self.schema}"."{self.NODE_TABLE}"' in normalized:
            graph_name, node_id, name, label, properties, segment_ids = params
            self.node_rows[(graph_name, node_id)] = (node_id, name, label, properties, segment_ids)
            return

        if f'INSERT INTO "{self.schema}"."{self.EDGE_TABLE}"' in normalized:
            graph_name, edge_id, source_id, target_id, relation, properties, segment_ids = params
            self.edge_rows[(graph_name, edge_id)] = (edge_id, source_id, target_id, relation, properties, segment_ids)
            return

    def _fetchone(self, sql, params=()):
        normalized = " ".join(sql.split())
        if "FROM ag_catalog.ag_graph" in normalized:
            return (1,) if self.graph_exists else None
        if f'FROM "{self.schema}"."{self.NODE_TABLE}"' in normalized and "node_id = %s" in normalized:
            return self.node_rows.get((params[0], params[1]))
        if f'FROM "{self.schema}"."{self.EDGE_TABLE}"' in normalized and "edge_id = %s" in normalized:
            return self.edge_rows.get((params[0], params[1]))
        if "COUNT(*)" in normalized and self.NODE_TABLE in normalized:
            graph_name = params[0]
            return (sum(1 for key in self.node_rows if key[0] == graph_name),)
        if "COUNT(*)" in normalized and self.EDGE_TABLE in normalized:
            graph_name = params[0]
            return (sum(1 for key in self.edge_rows if key[0] == graph_name),)
        return None

    def _fetchall(self, sql, params=()):
        normalized = " ".join(sql.split())
        if "GROUP BY label" in normalized:
            return [("Entity", sum(1 for key in self.node_rows if key[0] == params[0]))]
        if "GROUP BY relation" in normalized:
            counts = {}
            for (graph_name, _), row in self.edge_rows.items():
                if graph_name != params[0]:
                    continue
                counts[row[3]] = counts.get(row[3], 0) + 1
            return sorted(counts.items())
        if f'FROM "{self.schema}"."{self.NODE_TABLE}"' in normalized:
            rows = [row for (graph_name, _), row in self.node_rows.items() if graph_name == params[0]]
            if "LOWER(name) LIKE" in normalized:
                lowered = params[1].strip("%")
                rows = [row for row in rows if lowered in row[1].lower() or lowered in row[2].lower() or lowered in row[3].lower()]
            elif "node_id = ANY(%s)" in normalized:
                allowed = set(params[1])
                rows = [row for row in rows if row[0] in allowed]
            elif "AND label = %s" in normalized:
                rows = [row for row in rows if row[2] == params[1]]
            rows.sort(key=lambda row: (row[1], row[0]))
            return rows[: params[-1]] if isinstance(params[-1], int) else rows
        if f'FROM "{self.schema}"."{self.EDGE_TABLE}"' in normalized:
            rows = [row for (graph_name, _), row in self.edge_rows.items() if graph_name == params[0]]
            if "source_id = ANY(%s)" in normalized or "target_id = ANY(%s)" in normalized:
                allowed = set(params[1])
                rows = [row for row in rows if row[1] in allowed or row[2] in allowed]
            elif "AND relation = %s" in normalized:
                rows = [row for row in rows if row[3] == params[1]]
            rows.sort(key=lambda row: (row[3], row[0]))
            return rows[: params[-1]] if params and isinstance(params[-1], int) else rows
        return []

    def _run_cypher(self, query: str) -> None:
        self.cypher_queries.append(" ".join(query.split()))


class TestAgeGraphRepository(unittest.TestCase):
    def setUp(self):
        self.repo = FakeAgeGraphRepository()
        self.alpha = GraphNode(
            id="node-alpha",
            name="Alpha Service",
            label="Entity",
            properties={"file_name": "doc.txt", "confidence": 0.9},
            segment_ids=[1],
        )
        self.beta = GraphNode(
            id="node-beta",
            name="Beta Database",
            label="Entity",
            properties={"file_name": "doc.txt", "confidence": 0.8},
            segment_ids=[2],
        )
        self.edge = GraphEdge(
            id="edge-alpha-beta",
            source_id="node-alpha",
            target_id="node-beta",
            relation="uses",
            properties={"file_name": "doc.txt"},
            segment_ids=[1, 2],
        )

    def test_ensure_graph_creates_graph_once(self):
        self.repo.ensure_graph()
        self.assertTrue(self.repo.graph_exists)
        create_calls = [sql for sql, _ in self.repo.executed_sql if "create_graph" in sql]
        self.assertEqual(len(create_calls), 1)

        self.repo.ensure_graph()
        create_calls = [sql for sql, _ in self.repo.executed_sql if "create_graph" in sql]
        self.assertEqual(len(create_calls), 1)

    def test_upsert_and_query_graph_metadata(self):
        self.repo.upsert_nodes([self.alpha, self.beta])
        self.repo.upsert_edges([self.edge])

        summary = self.repo.get_summary()
        self.assertEqual(summary.backend, "age")
        self.assertEqual(summary.graph_name, "repo_graph")
        self.assertEqual(summary.node_count, 2)
        self.assertEqual(summary.edge_count, 1)
        self.assertEqual(summary.relations["uses"], 1)

        nodes = self.repo.list_nodes(limit=10)
        self.assertEqual(len(nodes), 2)
        self.assertEqual(nodes[0].label, "Entity")

        edges = self.repo.list_edges(relation="uses", limit=10)
        self.assertEqual(len(edges), 1)
        self.assertEqual(edges[0].source_id, "node-alpha")

        subgraph = self.repo.get_subgraph(["node-alpha"], max_hops=1)
        self.assertEqual(len(subgraph.nodes), 2)
        self.assertEqual(len(subgraph.edges), 1)

        search_results = self.repo.search_nodes("alpha", limit=10)
        self.assertEqual(len(search_results), 1)
        self.assertEqual(search_results[0].id, "node-alpha")

        self.assertEqual(len(self.repo.cypher_queries), 3)
        self.assertTrue(any("MERGE (n:Entity" in query for query in self.repo.cypher_queries))
        self.assertTrue(any("MERGE (source)-[r:RELATED" in query for query in self.repo.cypher_queries))

    def test_upsert_merges_segment_ids(self):
        self.repo.upsert_nodes([self.alpha])
        self.repo.upsert_nodes([
            GraphNode(
                id="node-alpha",
                name="Alpha Service",
                label="Entity",
                properties={"owner": "platform"},
                segment_ids=[3],
            )
        ])

        nodes = self.repo.list_nodes(limit=10)
        self.assertEqual(nodes[0].segment_ids, [1, 3])
        self.assertEqual(nodes[0].properties["owner"], "platform")


if __name__ == "__main__":
    unittest.main()
