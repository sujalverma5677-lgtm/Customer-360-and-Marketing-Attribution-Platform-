"""
Identity Resolution Engine
Resolves fragmented customer identifiers (cookies, device IDs, hashed emails, CRM IDs)
into a unified canonical customer profile using Graph Connected Components (Disjoint Set Union).
"""

import os
from collections import defaultdict
from typing import Dict, List, Set, Tuple
import pandas as pd
import numpy as np


class DisjointSetUnion:
    """Disjoint Set Union (DSU) / Union-Find with path compression and union by rank."""
    def __init__(self):
        self.parent: Dict[str, str] = {}
        self.rank: Dict[str, int] = {}

    def find(self, item: str) -> str:
        if item not in self.parent:
            self.parent[item] = item
            self.rank[item] = 0
            return item
        if self.parent[item] != item:
            self.parent[item] = self.find(self.parent[item])
        return self.parent[item]

    def union(self, item1: str, item2: str):
        root1 = self.find(item1)
        root2 = self.find(item2)
        if root1 == root2:
            return

        if self.rank[root1] < self.rank[root2]:
            self.parent[root1] = root2
        elif self.rank[root1] > self.rank[root2]:
            self.parent[root2] = root1
        else:
            self.parent[root2] = root1
            self.rank[root1] += 1


class IdentityResolver:
    """
    Enterprise Identity Graph Resolution Engine.
    Processes identifier pairs across GA4 web sessions, mobile devices, CRM, and transactions.
    """
    def __init__(self):
        self.dsu = DisjointSetUnion()
        self.node_metadata: Dict[str, Dict] = {}
        self.edges: List[Dict] = []

    def add_edge(self, id_type_1: str, val_1: str, id_type_2: str, val_2: str, source: str, confidence: float = 1.0):
        if not val_1 or not val_2 or pd.isna(val_1) or pd.isna(val_2):
            return

        node1 = f"{id_type_1}:{str(val_1).strip()}"
        node2 = f"{id_type_2}:{str(val_2).strip()}"

        if node1 == node2:
            self.dsu.find(node1)
            return

        self.dsu.union(node1, node2)
        self.edges.append({
            "source_node": node1,
            "target_node": node2,
            "edge_source": source,
            "confidence_score": confidence
        })

    def build_graph_from_dataframes(self, df_ga4: pd.DataFrame, df_crm_customers: pd.DataFrame) -> pd.DataFrame:
        """
        Extract identity linkages from:
        1. GA4 events where user_pseudo_id co-occurs with user_id or email_hash
        2. CRM customer table where customer_id maps to email_hash
        """
        print("Building Identity Graph edges from GA4 and CRM data...")
        
        # 1. CRM linkages: customer_id <-> email_hash
        for _, row in df_crm_customers.iterrows():
            cust_id = row.get("customer_id")
            email_hash = row.get("email_hash")
            if cust_id and email_hash:
                self.add_edge("customer_id", cust_id, "email_hash", email_hash, source="CRM_REGISTRATION", confidence=1.0)

        # 2. GA4 linkages: user_pseudo_id <-> user_id, user_pseudo_id <-> email_hash
        ga4_links = df_ga4[df_ga4["user_id"].notna() | df_ga4["email_hash"].notna()]
        for _, row in ga4_links.iterrows():
            pseudo_id = row.get("user_pseudo_id")
            user_id = row.get("user_id")
            email_hash = row.get("email_hash")

            if pseudo_id and user_id:
                self.add_edge("user_pseudo_id", pseudo_id, "customer_id", user_id, source="GA4_AUTH_SESSION", confidence=0.98)

            if pseudo_id and email_hash:
                self.add_edge("user_pseudo_id", pseudo_id, "email_hash", email_hash, source="GA4_CHECKOUT_EVENT", confidence=0.95)

            if user_id and email_hash:
                self.add_edge("customer_id", user_id, "email_hash", email_hash, source="GA4_AUTH_USER", confidence=1.0)

        # Also add standalone pseudo_ids (anonymous visitors) so they are in the graph
        for pseudo_id in df_ga4["user_pseudo_id"].dropna().unique():
            node = f"user_pseudo_id:{str(pseudo_id).strip()}"
            self.dsu.find(node)

        print(f"Total graph edges created: {len(self.edges):,}")
        return self._resolve_clusters()

    def _resolve_clusters(self) -> pd.DataFrame:
        """
        Groups nodes by connected component root and elects a canonical customer ID.
        Priority for canonical ID:
        1. customer_id (e.g. CUST-10001)
        2. email_hash (e.g. email_hash:abc123)
        3. user_pseudo_id (e.g. anon:987654)
        """
        clusters = defaultdict(list)
        all_nodes = list(self.dsu.parent.keys())

        for node in all_nodes:
            root = self.dsu.find(node)
            clusters[root].append(node)

        resolved_records = []

        for root, nodes in clusters.items():
            # Determine canonical customer ID
            cust_ids = [n.split(":", 1)[1] for n in nodes if n.startswith("customer_id:")]
            email_hashes = [n.split(":", 1)[1] for n in nodes if n.startswith("email_hash:")]
            pseudo_ids = [n.split(":", 1)[1] for n in nodes if n.startswith("user_pseudo_id:")]

            if cust_ids:
                canonical_id = cust_ids[0]
                resolution_type = "AUTHENTICATED_CRM"
                confidence = 1.0
            elif email_hashes:
                canonical_id = f"LEAD_{email_hashes[0][:12]}"
                resolution_type = "PROBABILISTIC_EMAIL"
                confidence = 0.90
            else:
                canonical_id = f"ANON_{pseudo_ids[0]}"
                resolution_type = "ANONYMOUS_COOKIE"
                confidence = 0.70

            for node in nodes:
                node_type, node_val = node.split(":", 1)
                resolved_records.append({
                    "identifier_type": node_type,
                    "identifier_value": node_val,
                    "canonical_customer_id": canonical_id,
                    "resolution_type": resolution_type,
                    "confidence_score": confidence,
                    "cluster_size": len(nodes),
                    "total_devices_linked": len(pseudo_ids),
                    "is_known_customer": 1 if cust_ids else 0
                })

        df_resolved = pd.DataFrame(resolved_records)
        print(f"Resolved {len(clusters):,} unique identity clusters across {len(df_resolved):,} node identifiers.")
        return df_resolved


def run_identity_resolution(raw_data_dir: str = "data/raw", output_dir: str = "data/processed"):
    os.makedirs(output_dir, exist_ok=True)
    df_ga4 = pd.read_csv(os.path.join(raw_data_dir, "raw_ga4_events.csv"))
    df_crm_cust = pd.read_csv(os.path.join(raw_data_dir, "raw_crm_customers.csv"))

    resolver = IdentityResolver()
    df_identity_mapping = resolver.build_graph_from_dataframes(df_ga4, df_crm_cust)

    # Save identity resolution outputs
    df_identity_mapping.to_csv(os.path.join(output_dir, "int_identity_mapping.csv"), index=False)
    pd.DataFrame(resolver.edges).to_csv(os.path.join(output_dir, "int_identity_graph_edges.csv"), index=False)
    print(f"Saved identity resolution outputs to {output_dir}")
    return df_identity_mapping


if __name__ == "__main__":
    import sys
    base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    run_identity_resolution(
        raw_data_dir=os.path.join(base_path, "data", "raw"),
        output_dir=os.path.join(base_path, "data", "processed")
    )
