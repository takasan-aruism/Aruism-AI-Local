######################################################################
# Aruism AI Project - Philosophical Integrity Daemon
#
# このファイルは、グラフデータベースの状態がAruismの哲学に準拠して
# いるかを検証する、監視プログラムの機能を定義します。
#
# 参照ドキュメント: Aruism_AI_Project_11_Cognitive_Architecture_Design.txt
# バージョン: 0.2
# 作成日: 2025-06-18
######################################################################

from neo4j import GraphDatabase
import os
import sys

# プロジェクトのルートディレクトリをシステムパスに追加
sys.path.append(os.getcwd())

from src.ontology.db_manager import GraphDBManager

class PhilosophicalIntegrityDaemon:
    """
    知識ベースがAruismの原則に整合しているかを検証するデーモン。
    """
    def __init__(self, db_manager: GraphDBManager):
        """
        デーモンを初期化します。
        :param db_manager: データベース操作を行うためのGraphDBManagerインスタンス
        """
        self.db_manager = db_manager
        if self.db_manager.driver is None:
            raise ConnectionError("データベースドライバーが初期化されていません。")
        print("PhilosophicalIntegrityDaemonが初期化されました。")

    def find_orphan_nodes(self):
        """
        「ある」(M5001)の原則に違反する孤児ノードを検出します。
        """
        print("\n--- 哲学的整合性チェック(1)：孤児ノードの検出を開始 ---")
        with self.db_manager.driver.session() as session:
            orphans = session.execute_read(self._find_and_return_orphans)
            
            if not orphans:
                print("孤児ノードは見つかりませんでした。整合性は保たれています。")
            else:
                print(f"警告：{len(orphans)}件の孤児ノードが検出されました。")
                for orphan in orphans:
                    print(f"  - ID: {orphan['meaning_id']}, Name: {orphan['name']}")
            return orphans

    # ★★★ ここからが新しいメソッドです ★★★
    def check_for_unsymmetrical_value_nodes(self):
        """
        「対称性」の原則に基づき、価値軸（axis_sentiment）を持つにもかかわらず、
        Symmetric_Toの関係性を持たないノードを検出します。
        """
        print("\n--- 哲学的整合性チェック(2)：非対称な価値ノードの検出を開始 ---")
        with self.db_manager.driver.session() as session:
            unsymmetrical_nodes = session.execute_read(self._find_unsymmetrical_nodes)

            if not unsymmetrical_nodes:
                print("非対称な価値ノードは見つかりませんでした。")
            else:
                print(f"警告：{len(unsymmetrical_nodes)}件の非対称な価値ノードが検出されました。")
                for node in unsymmetrical_nodes:
                    print(f"  - ID: {node['meaning_id']}, Name: {node['name']}, Sentiment: {node['sentiment']}")
            return unsymmetrical_nodes
    # ★★★ ここまでが新しいメソッドです ★★★

    @staticmethod
    def _find_and_return_orphans(tx):
        """
        孤児ノードを検出するためのCypherクエリを実行するトランザクション関数。
        """
        query = (
            "MATCH (n:Meaning) "
            "WHERE n.meaning_id <> 'M5001' AND NOT (n)--() "
            "RETURN n.meaning_id AS meaning_id, n.canonical_name_ja AS name"
        )
        result = tx.run(query)
        return [record for record in result]

    # ★★★ ここからが新しい静的メソッドです ★★★
    @staticmethod
    def _find_unsymmetrical_nodes(tx):
        """
        非対称な価値ノードを検出するためのCypherクエリを実行するトランザクション関数。
        """
        query = (
            "MATCH (n:Meaning) "
            "WHERE n.axis_sentiment IS NOT NULL AND NOT (n)-[:Symmetric_To]-() "
            "RETURN n.meaning_id AS meaning_id, n.canonical_name_ja AS name, n.axis_sentiment as sentiment"
        )
        result = tx.run(query)
        return [record for record in result]
    # ★★★ ここまでが新しい静的メソッドです ★★★


# このファイルが直接実行された場合にのみ以下のコードが動きます（テスト用）
if __name__ == '__main__':
    # --- 設定 ---
    NEO4J_URI = "neo4j://localhost:7687"
    NEO4J_USER = "neo4j"
    NEO4J_PASSWORD = "11dr34SSAAa_$$aae"  # ご自身のパスワードに変更してください

    # --- 実行 ---
    db_manager = GraphDBManager(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)

    if db_manager.driver:
        daemon = PhilosophicalIntegrityDaemon(db_manager)
        
        # 既存のチェックを実行
        daemon.find_orphan_nodes()
        
        # ★★★ 修正点：新しいチェックも実行する ★★★
        daemon.check_for_unsymmetrical_value_nodes()
        
        db_manager.close()