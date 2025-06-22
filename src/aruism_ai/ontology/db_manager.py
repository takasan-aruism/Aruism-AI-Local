######################################################################
# Aruism AI Project - Graph Database Manager
#
# バージョン: 2.0 (新Conceptモデル対応版)
# 最終更新日: 2025-06-22
######################################################################

from .models import Concept, Relationship
from neo4j import GraphDatabase

class GraphDBManager:
    """
    Neo4jグラフデータベースとの接続と操作を管理するクラス。
    """
    def __init__(self, uri, user, password):
        # [修正] このクラスではneo4jドライバを直接インポートしない
        try:
            self.driver = GraphDatabase.driver(uri, auth=(user, password))
        except Exception as e:
            print(f"データベースへの接続に失敗しました: {e}")
            self.driver = None

    def close(self):
        if self.driver is not None:
            self.driver.close()

    def execute_query(self, query: str):
        if self.driver is None:
            print("ドライバーが初期化されていません。")
            return
        with self.driver.session() as session:
            session.run(query)

    # [修正] 型ヒントを Concept に変更
    def create_meaning_node(self, node: Concept):
        if self.driver is None:
            print("ドライバーが初期化されていません。")
            return
        with self.driver.session() as session:
            session.execute_write(self._create_and_return_node, node)

    # [修正] 型ヒントを Relationship に合わせる
    def create_relationship(self, rel: Relationship):
        if self.driver is None:
            print("ドライバーが初期化されていません。")
            return
        with self.driver.session() as session:
            session.execute_write(self._create_and_return_relationship, rel)

    @staticmethod
    def _create_and_return_relationship(tx, rel: Relationship):
        # [修正] source/target のID名をモデルに合わせて変更
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

    # ▼▼▼ [最重要修正点] 新しいConceptモデルの全プロパティを扱えるようにする ▼▼▼
    @staticmethod
    def _create_and_return_node(tx, node: Concept):
        """
        Conceptオブジェクトから、全てのプロパティをDBノードに設定する。
        """
        # MERGEクエリでノードの存在を確認・作成し、IDを基準とする
        # SETクエリで、全てのプロパティを一度に設定する
        query = (
            "MERGE (c:Concept {concept_id: $concept_id}) "
            "SET c += $props "
            "RETURN c.concept_id AS concept_id"
        )
        
        # Conceptオブジェクトの全プロパティを辞書に変換
        # dataclasses.asdict を使うと便利だが、手動で制御する
        props = {
            "canonical_name_ja": node.canonical_name_ja,
            "canonical_name_en": node.canonical_name_en,
            "description_ja": node.description_ja,
            "description_en": node.description_en,
            "wordnet_synset_id": node.wordnet_synset_id,
            "abstraction_level": node.abstraction_level,
            "aruism_category": node.aruism_category,
            "resonance_potential": node.resonance_potential,
            "source": node.source,
            "confidence": node.confidence,
            "version": node.version
        }
        
        # Noneのプロパティはクエリに含まないようにする
        props_without_none = {k: v for k, v in props.items() if v is not None}
        
        tx.run(query, concept_id=node.concept_id, props=props_without_none)
    def update_node_properties(self, concept_id: str, properties: dict):
            """
            指定されたconcept_idを持つノードを見つけ、
            与えられたプロパティ辞書の内容で更新（追加）する。
            """
            if self.driver is None or not properties:
                return

            def work(tx, c_id, props):
                query = (
                    "MATCH (c:Concept {concept_id: $concept_id}) "
                    "SET c += $props"
                )
                tx.run(query, concept_id=c_id, props=props)

            with self.driver.session() as session:
                session.execute_write(work, concept_id, properties)