######################################################################
# Aruism AI Project - Causal Engine
#
# このファイルは、「存在の連動性」の原則に基づき、
# 概念間の因果関係を辿る機能を定義します。
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

class CausalEngine:
    """
    概念間の因果関係を推論するエンジン。
    """
    def __init__(self, db_manager: GraphDBManager):
        self.db_manager = db_manager
        if self.db_manager.driver is None:
            raise ConnectionError("データベースドライバーが初期化されていません。")
        print("CausalEngineが初期化されました。")

    def trace_causality(self, concept_name_ja: str):
        """
        指定された概念の原因（上流）と結果（下流）を検索します。
        """
        print(f"\n--- 「{concept_name_ja}」の因果関係を検索します ---")

        # 原因（上流）を検索するクエリ
        causes_query = (
            "MATCH (cause:Meaning)-[:Causes]->(effect:Meaning) "
            "WHERE effect.canonical_name_ja CONTAINS $concept_name "
            "RETURN cause.canonical_name_ja AS cause_name"
        )
        
        # 結果（下流）を検索するクエリ
        effects_query = (
            "MATCH (cause:Meaning)-[:Causes]->(effect:Meaning) "
            "WHERE cause.canonical_name_ja CONTAINS $concept_name "
            "RETURN effect.canonical_name_ja AS effect_name"
        )
        # ★★★ ここまで ★★★

        def work(tx, name):
            # 念のため、LIMIT 1を追加
            causes_result = tx.run(causes_query + " LIMIT 1", concept_name=name)
            effects_result = tx.run(effects_query + " LIMIT 1", concept_name=name)
            
            causes = [record["cause_name"] for record in causes_result]
            effects = [record["effect_name"] for record in effects_result]
            
            return {"causes": causes, "effects": effects}
        
        with self.db_manager.driver.session() as session:
            causality_map = session.execute_read(work, concept_name_ja)
            
            if causality_map.get("causes") or causality_map.get("effects"):
                print("因果関係が見つかりました。")
            else:
                print("因果関係が見つかりませんでした。")
            
            return causality_map

# このファイルが直接実行された場合にのみ以下のコードが動きます（テスト用）
if __name__ == '__main__':
    # --- 設定 ---
    NEO4J_URI = "neo4j://localhost:7687"
    NEO4J_USER = "neo4j"
    NEO4J_PASSWORD = "11dr34SSAAa_$$aae"  # ご自身のパスワードに変更してください

    # --- 実行 ---
    db_manager = GraphDBManager(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)

    if db_manager.driver:
        engine = CausalEngine(db_manager)

        # 1. 「地面が濡れる」の原因を探す
        result1 = engine.trace_causality("地面が濡れる")
        print(f"  -> 「地面が濡れる」の原因: {result1.get('causes')}")

        # 2. 「雨」が引き起こす結果を探す
        result2 = engine.trace_causality("雨")
        print(f"  -> 「雨」が引き起こす結果: {result2.get('effects')}")
        
        db_manager.close()