######################################################################
# Aruism AI Project - Graph Database Manager
# バージョン: 2.2 (最終整合性版)
######################################################################
import logging
from typing import List, Dict, Any, Optional
from neo4j import GraphDatabase, Driver, exceptions
from .models import Concept, Relationship

class GraphDBManager:
    def __init__(self, uri: str, user: str, password: str | None):
        self.driver: Optional[Driver] = None
        try:
            self.driver = GraphDatabase.driver(uri, auth=(user, password))
            self.driver.verify_connectivity()
            logging.info(f"Neo4jデータベースへの接続に成功しました: {uri}")
        except Exception as e:
            logging.error(f"Neo4jへの接続に失敗しました: {e}")

    def close(self):
        if self.driver:
            self.driver.close()

    def execute_query(self, query: str, **kwargs) -> List[Dict[str, Any]]:
        if not self.driver:
            logging.error("データベースドライバが利用できません。")
            return []
        try:
            with self.driver.session() as session:
                result = session.run(query, **kwargs)
                return result.data()
        except Exception as e:
            logging.error(f"クエリ実行中にエラー: {e}", exc_info=True)
            return []

    def create_concept_node(self, concept: Concept):
        query = """
        MERGE (c:Concept {concept_id: $concept_id})
        ON CREATE SET c += $props
        ON MATCH SET c += $props
        """
        props = concept.to_dict()
        concept_id = props.pop('concept_id')
        self.execute_query(query, concept_id=concept_id, props=props)

    def create_relationship(self, rel: Relationship):
        query = f"""
        MATCH (source:Concept {{concept_id: $source_id}})
        MATCH (target:Concept {{concept_id: $target_id}})
        MERGE (source)-[r:{rel.relationship_type}]->(target)
        ON CREATE SET r += $props
        ON MATCH SET r += $props
        """
        props = rel.to_dict()
        self.execute_query(query, 
            source_id=props.pop('source_concept_id'), 
            target_id=props.pop('target_concept_id'), 
            props=props
        )

    def batch_update_node_properties(self, batch: List[Dict[str, Any]]):
        query = """
        UNWIND $batch AS row
        MATCH (c:Concept {concept_id: row.concept_id})
        SET c += row.properties
        """
        self.execute_query(query, batch=batch)

    def batch_create_concept_nodes(self, batch: List[Dict[str, Any]]):
        query = """
        UNWIND $batch as node_props
        MERGE (c:Concept {concept_id: node_props.concept_id})
        SET c += node_props
        """
        self.execute_query(query, batch=batch)

    def batch_create_relationships(self, batch: List[Dict[str, Any]]):
        query = """
        UNWIND $batch AS row
        MATCH (source:Concept {concept_id: row.source_id})
        MATCH (target:Concept {concept_id: row.target_id})
        MERGE (source)<-[r:Is_A]-(target)
        ON CREATE SET r.source_of_data = 'WordNet_Import'
        """
        self.execute_query(query, batch=batch)

# GraphDBManagerクラスの末尾に追記
    def batch_update_node_properties_by_synset(self, batch: list[dict]):
        """wordnet_synset_idをキーにしてプロパティをバッチ更新する"""
        query = """
        UNWIND $batch AS row
        MATCH (c:Concept {wordnet_synset_id: row.wordnet_synset_id})
        SET c += row.properties
        """
        self.execute_query(query, batch=batch)