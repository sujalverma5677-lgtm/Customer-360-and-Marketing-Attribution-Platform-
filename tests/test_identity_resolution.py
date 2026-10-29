"""
Unit Tests for Identity Resolution Engine
Validates Disjoint Set Union (DSU), Transitive Merges, and Canonical ID Selection.
"""

import os
import sys
import unittest
import pandas as pd

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.identity_resolution.graph_resolver import DisjointSetUnion, IdentityResolver


class TestIdentityResolution(unittest.TestCase):
    def setUp(self):
        self.dsu = DisjointSetUnion()
        self.resolver = IdentityResolver()

    def test_dsu_basic_union_find(self):
        self.dsu.union("nodeA", "nodeB")
        self.assertEqual(self.dsu.find("nodeA"), self.dsu.find("nodeB"))

    def test_dsu_transitive_connectivity(self):
        # A <-> B and B <-> C should merge A and C
        self.dsu.union("nodeA", "nodeB")
        self.dsu.union("nodeB", "nodeC")
        self.assertEqual(self.dsu.find("nodeA"), self.dsu.find("nodeC"))

    def test_canonical_id_election_crm_priority(self):
        # Connect Cookie 111 with Email Hash and CRM CUST-999
        self.resolver.add_edge("user_pseudo_id", "111.999", "email_hash", "hash_abc", "GA4_SESSION")
        self.resolver.add_edge("customer_id", "CUST-999", "email_hash", "hash_abc", "CRM_REG")
        
        df_clusters = self.resolver._resolve_clusters()
        cookie_row = df_clusters[df_clusters["identifier_value"] == "111.999"].iloc[0]
        
        # Canonical ID must be elected as the authenticated CRM customer ID
        self.assertEqual(cookie_row["canonical_customer_id"], "CUST-999")
        self.assertEqual(cookie_row["resolution_type"], "AUTHENTICATED_CRM")
        self.assertEqual(cookie_row["confidence_score"], 1.0)

    def test_canonical_id_anonymous_cluster(self):
        # Unauthenticated browsing session
        self.resolver.add_edge("user_pseudo_id", "anon_cookie_123", "user_pseudo_id", "anon_cookie_123", "GA4_BROWSE")
        df_clusters = self.resolver._resolve_clusters()
        
        row = df_clusters[df_clusters["identifier_value"] == "anon_cookie_123"].iloc[0]
        self.assertTrue(row["canonical_customer_id"].startswith("ANON_"))
        self.assertEqual(row["is_known_customer"], 0)


if __name__ == "__main__":
    unittest.main()
