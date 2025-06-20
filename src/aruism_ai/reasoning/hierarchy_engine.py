######################################################################
# Aruism AI Project - Hierarchy Engine
#
# このファイルは、「存在の階層性」の原則に基づき、
# 概念間の上位・下位関係を辿る機能を定義します。
#
# 参照ドキュメント: Aruism_AI_Project_11_Cognitive_Architecture_Design.txt
# バージョン: 0.1
# 作成日: 2025-06-18
######################################################################

import os
import sys

# プロジェクトのルートディレクトリをシステムパスに追加
sys.path.append(os.getcwd())

from src.ontology.db_manager import GraphDBManager

class HierarchyEngine:
    """
    存在の階層性の原則に基づいた推論を行うエンジン。
    """
    def __init__(self, db_manager: GraphDBManager):
        self.db_manager = db_manager
        if self.db_manager.driver is None:
            raise ConnectionError("データベースドライバーが初期化されていません。")
        print("HierarchyEngineが初期化されました。")

    def trace_upwards(self, concept_name_ja: str):
        """
        指定された日本語の概念名から、上位概念を再帰的に辿り、
        その階層パスをリストとして返します。
        """
        print(f"\n--- 「{concept_name_ja}」の上位階層を検索します ---")

        # ★★★ ここが修正点です ★★★
        query = (
            "MATCH (start:Meaning)-[r:Is_A*]->(parent:Meaning) "
            "WHERE start.canonical_name_ja CONTAINS $start_node_name "
            "RETURN parent.canonical_name_ja AS parent_name"
        )
        # ★★★ ここまで ★★★
        
        def work(tx, name):
            # 念のため、同じ名前のノードが複数見つかる可能性を考慮し、LIMIT 1を追加
            result = tx.run(query + " LIMIT 1", start_node_name=name)
            return [record["parent_name"] for record in result]

        with self.db_manager.driver.session() as session:
            parent_names = session.execute_read(work, concept_name_ja)
            
            if parent_names:
                print("上位階層が見つかりました。")
                return parent_names
            else:
                print("上位階層が見つかりませんでした。")
                return []
                
# このファイルが直接実行された場合にのみ以下のコードが動きます（テスト用）
if __name__ == '__main__':
    # --- 設定 ---
    NEO4J_URI = "neo4j://localhost:7687"
    NEO4J_USER = "neo4j"
    NEO4J_PASSWORD = "11dr34SSAAa_$$aae"  # ご自身のパスワードに変更してください

    # --- 実行 ---
    db_manager = GraphDBManager(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)

    if db_manager.driver:
        engine = HierarchyEngine(db_manager)

        # テストしたい概念名
        # WordNetからインポートした「ハワイ島」は「島」の上位概念を持つはずです。
        concept_to_test = "ハワイ島"
        
        parents = engine.trace_upwards(concept_to_test)
        
        if parents:
            # 見つかった上位概念を矢印で繋いで表示
            path_str = " -> ".join(parents)
            print("\n--- 検出された階層パス ---")
            print(f"{concept_to_test} -> {path_str}")
        
        db_manager.close()