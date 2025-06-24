######################################################################
# Aruism AI Project - Graph Database Manager
# Neo4jデータベースとの全てのやり取りを管理する
#
# バージョン: 2.1 (メソッド名修正版)
# 作成日: 2025-06-25 (再構築・修正)
######################################################################
import logging
from typing import List, Dict, Any, Optional
from neo4j import GraphDatabase, Driver, exceptions

from .models import Concept, Relationship

class GraphDBManager:
    """Neo4jデータベースとの接続と操作を管理するクラス"""

    def __init__(self, uri: str, user: str, password: str | None):
        """
        GraphDBManagerを初期化し、Neo4jドライバを確立する
        """
        self.driver: Optional[Driver] = None
        try:
            self.driver = GraphDatabase.driver(uri, auth=(user, password))
            self.driver.verify_connectivity()
            logging.info(f"Neo4jデータベースへの接続に成功しました: {uri}")
        except exceptions.AuthError as e:
            logging.error(f"Neo4jデータベースの認証に失敗しました: {e}")
        except exceptions.ServiceUnavailable as e:
            logging.error(f"Neo4jデータベースに接続できませんでした: {e}")
        except Exception as e:
            logging.error(f"予期せぬエラーでNeo4jへの接続に失敗しました: {e}")

    def close(self):
        """データベースドライバを閉じる"""
        if self.driver:
            self.driver.close()
            logging.info("Neo4jデータベース接続を閉じました。")

    def execute_query(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        与えられたCypherクエリを実行し、結果を返す
        【変更点】プライベートメソッド(_execute_query)から公開メソッド(execute_query)に変更
        """
        if not self.driver:
            logging.error("データベースドライバが利用できません。クエリを実行できません。")
            return []
            
        try:
            with self.driver.session() as session:
                result = session.run(query, parameters or {})
                return result.data()
        except exceptions.CypherSyntaxError as e:
            logging.error(f"Cypherクエリの構文エラー: {e.query}", exc_info=True)
        except Exception as e:
            logging.error(f"クエリ実行中にエラーが発生しました: {e}", exc_info=True)
        return []

    def create_concept_node(self, concept: Concept):
        """単一のConceptノードを作成またはマージする"""
        query = """
        MERGE (c:Concept {concept_id: $concept_id})
        ON CREATE SET c += $props
        ON MATCH SET c += $props
        """
        props = concept.to_dict()
        concept_id = props.pop('concept_id')
        parameters = {'concept_id': concept_id, 'props': props}
        self.execute_query(query, parameters)

    def update_node_properties(self, concept_id: str, properties: Dict[str, Any]):
        """既存のノードにプロパティを追記・更新する"""
        query = """
        MATCH (c:Concept {concept_id: $concept_id})
        SET c += $properties
        """
        self.execute_query(query, parameters={'concept_id': concept_id, 'properties': properties})

    def create_relationship(self, rel: Relationship):
        """単一の関係性を作成またはマージする"""
        query = f"""
        MATCH (source:Concept {{concept_id: $source_id}})
        MATCH (target:Concept {{concept_id: $target_id}})
        MERGE (source)-[r:{rel.relationship_type}]->(target)
        ON CREATE SET r += $props
        ON MATCH SET r += $props
        """
        props = rel.to_dict()
        source_id = props.pop('source_concept_id')
        target_id = props.pop('target_concept_id')
        props.pop('relationship_type')

        parameters = {
            'source_id': source_id,
            'target_id': target_id,
            'props': props
        }
        self.execute_query(query, parameters)

    def get_all_genesis_concepts(self) -> List[Dict[str, str]]:
        """Genesis Importerによって作成された全ての概念を取得する"""
        query = """
        MATCH (c:Concept)
        WHERE c.source_of_data = 'AruismBaseDBTable_Genesis'
        RETURN c.concept_id AS concept_id, c.canonical_name_ja AS name
        """
        return self.execute_query(query)

    def batch_update_node_properties(self, batch: List[Dict[str, Any]]):
        """ノードのプロパティをバッチで更新する"""
        query = """
        UNWIND $batch AS row
        MATCH (c:Concept {concept_id: row.concept_id})
        SET c += row.properties
        """
        self.execute_query(query, parameters={'batch': batch})

    def batch_create_concept_nodes(self, batch: List[Dict[str, Any]]):
       """Conceptノードをバッチで作成（既に存在する場合はプロパティをマージ）"""
def batch_create_concept_nodes(self, batch: List[Dict[str, Any]]):
    """Conceptノードをバッチで作成（既に存在する場合はプロパティをマージ）"""
    query = """
    UNWIND $batch AS row
    MERGE (c:Concept {concept_id: row.concept_id})
    ON CREATE SET c.canonical_name_ja = row.canonical_name_ja,
                  c.description_en = row.description_en,
                  c.source_of_data = row.source_of_data  # ここを修正
    ON MATCH SET c.canonical_name_ja = COALESCE(c.canonical_name_ja, row.canonical_name_ja),
                 c.description_en = COALESCE(c.description_en, row.description_en),
                 c.source_of_data = c.source_of_data + row.source_of_data # ここを修正 (リストの結合)
    """
    self.execute_query(query, parameters={'batch': batch})
    def batch_create_relationships(self, batch: List[Dict[str, Any]]):
        """関係性をバッチで作成"""
        query = """
        UNWIND $batch AS row
        MATCH (source:Concept {concept_id: row.source_id})
        MATCH (target:Concept {concept_id: row.target_id})
        MERGE (source)-[r:Is_A]->(target)
        ON CREATE SET r.source_of_data = 'WordNet_Import'
        """
        self.execute_query(query, parameters={'batch': batch})