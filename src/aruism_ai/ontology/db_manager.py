######################################################################
# Aruism AI Project - Graph Database Manager
#
# バージョン: 2.2 (create_concept_nodeへのメソッド名変更)
# 最終更新日: 2025-06-23
######################################################################

from neo4j import GraphDatabase
from .models import Concept, Relationship

class GraphDBManager:
    """
    Neo4jグラフデータベースとの接続と操作を管理するクラス。
    """
    def __init__(self, uri, user, password):
        try:
            self.driver = GraphDatabase.driver(uri, auth=(user, password))
        except Exception as e:
            print(f"データベースへの接続に失敗しました: {e}")
            self.driver = None

    def close(self):
        if self.driver is not None:
            self.driver.close()

    def execute_query(self, query: str):
        if self.driver is None: return
        with self.driver.session() as session:
            session.run(query)

    # ▼▼▼ [修正点] メソッド名を create_meaning_node から create_concept_node に変更 ▼▼▼
    def create_concept_node(self, node: Concept):
        if self.driver is None: return
        with self.driver.session() as session:
            session.execute_write(self._create_and_return_node, node)

    def create_relationship(self, rel: Relationship):
        if self.driver is None: return
        with self.driver.session() as session:
            session.execute_write(self._create_and_return_relationship, rel)
            
    def update_node_properties(self, concept_id: str, properties: dict):
        if self.driver is None or not properties: return
        def work(tx, c_id, props):
            query = (
                "MATCH (c:Concept {concept_id: $concept_id}) "
                "SET c += $props"
            )
            tx.run(query, concept_id=c_id, props=props)
        with self.driver.session() as session:
            session.execute_write(work, concept_id, properties)

    @staticmethod
    def _create_and_return_relationship(tx, rel: Relationship):
        query = (
            "MATCH (a:Concept {concept_id: $source_id}), (b:Concept {concept_id: $target_id}) "
            f"MERGE (a)-[r:`{rel.relationship_type}`]->(b) "
            "SET r += $props"
        )
        props = {"strength": rel.strength}
        if rel.axis:
            props["axis"] = rel.axis
        if rel.source_of_data:
            props["source_of_data"] = rel.source_of_data
        tx.run(query, source_id=rel.source_concept_id, target_id=rel.target_concept_id, props=props)

    @staticmethod
    def _create_and_return_node(tx, node: Concept):
        query = (
            "MERGE (c:Concept {concept_id: $concept_id}) "
            "SET c += $props "
            "RETURN c.concept_id AS concept_id"
        )
        props = {
            "canonical_name_ja": node.canonical_name_ja,
            "symbol": node.symbol,
            "category": node.category,
            "canonical_name_en": node.canonical_name_en,
            "description_ja": node.description_ja,
            "description_en": node.description_en,
            "wordnet_synset_id": node.wordnet_synset_id,
            "abstraction_level": node.abstraction_level,
            "aruism_category": node.aruism_category,
            "resonance_potential": node.resonance_potential,
            "source": node.source,
            "confidence": node.confidence,
            "version": node.version,
            "sentiment_positive": node.sentiment_positive,
            "sentiment_negative": node.sentiment_negative,
        }
        props_without_none = {k: v for k, v in props.items() if v is not None}
        tx.run(query, concept_id=node.concept_id, props=props_without_none)
       
    def update_node_properties_by_wordnet_id(self, wordnet_id: str, properties: dict):
        """
        指定されたwordnet_synset_idを持つノードを見つけ、プロパティを更新する。
        """
        if self.driver is None or not properties:
            return

        def work(tx, w_id, props):
            query = (
                "MATCH (c:Concept {wordnet_synset_id: $wordnet_id}) "
                "SET c += $props"
            )
            tx.run(query, wordnet_id=w_id, props=props)

        with self.driver.session() as session:
            session.execute_write(work, wordnet_id, properties)

    def update_node_properties_by_wordnet_id(self, wordnet_id: str, properties: dict):
        """
        指定されたwordnet_synset_idを持つノードを見つけ、プロパティを更新する。
        """
        if self.driver is None or not properties:
            return

        def work(tx, w_id, props):
            query = (
                "MATCH (c:Concept {wordnet_synset_id: $wordnet_id}) "
                "SET c += $props"
            )
            tx.run(query, wordnet_id=w_id, props=props)

        with self.driver.session() as session:
            session.execute_write(work, wordnet_id, properties)