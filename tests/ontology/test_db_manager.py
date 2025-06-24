######################################################################
# Aruism AI Project - Unit Tests for GraphDBManager
# バージョン: 2.1 (最終整合性版)
######################################################################
import pytest
from unittest.mock import MagicMock, patch
from aruism_ai.ontology.models import Concept, Relationship
from aruism_ai.ontology.db_manager import GraphDBManager

@pytest.fixture
def db_manager():
    with patch('neo4j.GraphDatabase.driver'):
        manager = GraphDBManager("bolt://mock", "user", "pass")
        manager.execute_query = MagicMock(return_value=[])
        yield manager

class TestGraphDBManager:
    def test_create_concept_node(self, db_manager):
        test_node = Concept(concept_id="M0001", canonical_name_ja="愛")
        db_manager.create_concept_node(test_node)
        
        db_manager.execute_query.assert_called_once()
        call_kwargs = db_manager.execute_query.call_args.kwargs
        assert call_kwargs['concept_id'] == "M0001"
        assert call_kwargs['props']['canonical_name_ja'] == "愛"

    def test_create_relationship(self, db_manager):
        test_rel = Relationship(source_concept_id="C001", target_concept_id="C002", relationship_type="Is_A")
        db_manager.create_relationship(test_rel)

        db_manager.execute_query.assert_called_once()
        call_kwargs = db_manager.execute_query.call_args.kwargs
        query_string = db_manager.execute_query.call_args.args[0]
        
        assert "MERGE (source)-[r:Is_A]->(target)" in query_string
        assert call_kwargs['source_id'] == "C001"
        assert call_kwargs['target_id'] == "C002"

    def test_batch_methods_exist(self, db_manager):
        assert hasattr(db_manager, 'batch_update_node_properties')
        assert hasattr(db_manager, 'batch_create_concept_nodes')
        assert hasattr(db_manager, 'batch_create_relationships')