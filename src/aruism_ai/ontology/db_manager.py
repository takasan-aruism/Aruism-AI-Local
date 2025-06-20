######################################################################
# Aruism AI Project - Graph Database Manager
#
# このファイルは、models.pyで定義されたデータモデルと
# Neo4jグラフデータベースとの間のやり取りを管理するクラスを定義します。
#
# 参照ドキュメント: Aruism_AI_Project_11_Cognitive_Architecture_Design.txt
# バージョン: 0.2
# 作成日: 2025-06-18
######################################################################

import os
from neo4j import GraphDatabase
# ★ 修正点: Relationshipもインポートリストに追加します
from .models import MeaningID, Relationship

class GraphDBManager:
    """
    Neo4jグラフデータベースとの接続と操作を管理するクラス。
    """
    def __init__(self, uri, user, password):
        """
        データベースへの接続を初期化します。
        """
        try:
            self.driver = GraphDatabase.driver(uri, auth=(user, password))
            print("データベースへの接続に成功しました。")
        except Exception as e:
            print(f"データベースへの接続に失敗しました: {e}")
            self.driver = None

    def close(self):
        """
        データベース接続を閉じます。
        """
        if self.driver is not None:
            self.driver.close()
            print("データベース接続を閉じました。")
    def execute_query(self, query):
        """
        任意の読み取り/書き込みクエリを実行します。
        主にデータベースのクリアなど、管理用に使用します。
        """
        if self.driver is None:
            print("ドライバーが初期化されていません。")
            return
            
        with self.driver.session() as session:
            session.run(query)

    def create_meaning_node(self, node: MeaningID):
        """
        MeaningIDオブジェクトから、グラフデータベースにノードを作成します。
        """
        if self.driver is None:
            print("ドライバーが初期化されていません。")
            return

        with self.driver.session() as session:
            result = session.execute_write(self._create_and_return_node, node)
            print(f"ノードを作成しました: {result}")

    # ★ 修正点: このメソッド全体をクラス内に正しくインデントします
    def create_relationship(self, rel: Relationship):
        """
        Relationshipオブジェクトから、グラフデータベースに関係性を作成します。
        """
        if self.driver is None:
            print("ドライバーが初期化されていません。")
            return

        with self.driver.session() as session:
            # ★ 修正点: こちらも execute_write に統一します
            session.execute_write(self._create_and_return_relationship, rel)

    # ★ 修正点: このメソッド全体をクラス内に正しくインデントします
    @staticmethod
    def _create_and_return_relationship(tx, rel: Relationship):
        """
        関係性を作成するためのトランザクション関数。
        """
        properties = {
            "strength": rel.strength,
        }
        if rel.source_of_data:
            properties["source_of_data"] = rel.source_of_data
        if rel.valid_under_axis_id:
            properties["valid_under_axis_id"] = rel.valid_under_axis_id
        
        query = (
            "MATCH (a:Meaning {meaning_id: $source_id}), (b:Meaning {meaning_id: $target_id}) "
            f"MERGE (a)-[r:{rel.relationship_type}]->(b) "
            "SET r += $props"
        )
        
        tx.run(query, source_id=rel.source_meaning_id, target_id=rel.target_meaning_id, props=properties)

    @staticmethod
    def _create_and_return_node(tx, node: MeaningID):
        """
        ノードを作成するためのトランザクション関数。
        """
        properties = {
            "is_abstract": node.is_abstract,
        }
        for key, value in node.canonical_name.items():
            properties[f"canonical_name_{key}"] = value
        for key, value in node.description.items():
            properties[f"description_{key}"] = value
        if node.aruism_principle_link:
            properties["aruism_principle_link"] = node.aruism_principle_link
        # external_identifiersもプロパティに追加
        for key, value in node.external_identifiers.items():
            properties[f"external_identifiers_{key}"] = value

        query = (
            "MERGE (m:Meaning {meaning_id: $meaning_id}) "
            "SET m += $props "
            "RETURN m.meaning_id AS meaning_id, m.canonical_name_ja AS name"
        )
        
        result = tx.run(query, meaning_id=node.meaning_id, props=properties)
        return result.single()


# このファイルが直接実行された場合にのみ以下のコードが動きます（テスト用）
if __name__ == '__main__':
    # Neo4j Desktopで設定したURI、ユーザー名、パスワードを指定してください。
    NEO4J_URI = "neo4j://localhost:7687"
    NEO4J_USER = "neo4j"
    NEO4J_PASSWORD = "11dr34SSAAa_$$aae"  # ご自身のパスワードに変更してください

    db_manager = GraphDBManager(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)

    if db_manager.driver:
        # このファイル単体で実行しても、現在は何もしないようにします。
        # 実際の動作は wordnet_importer.py から呼び出して確認します。
        print("db_manager.py は正常に読み込み可能です。")
        db_manager.close()