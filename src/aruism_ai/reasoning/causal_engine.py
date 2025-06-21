######################################################################
# Aruism AI Project - Causal Engine
#
# バージョン: 0.2 (プロジェクト標準準拠・堅牢化版)
# 最終更新日: 2025-06-21
# 参照: アリズム原典§2.4「存在の連動性」
######################################################################

# [修正点] import文を 'aruism_ai.' 基準に統一
from aruism_ai.ontology.db_manager import GraphDBManager
from neo4j.exceptions import Neo4jError
import logging

class CausalEngine:
    """
    概念間の因果関係（存在の連動性）を推論するエンジン。
    """
    def __init__(self, db_manager: GraphDBManager):
        self.db_manager = db_manager
        if self.db_manager.driver is None:
            raise ConnectionError("データベースドライバーが初期化されていません。")

    def trace_causality(self, concept_name_ja: str) -> dict:
        """
        指定された概念の原因（上流）と結果（下流）を検索します。
        """
        if not concept_name_ja:
            return {"causes": [], "effects": []}

        # [修正点] CONTAINSから厳密な一致 '=' に変更し、クエリの精度を向上
        causes_query = (
            "MATCH (cause:Meaning)-[:Causes]->(effect:Meaning {canonical_name_ja: $concept_name}) "
            "RETURN cause.canonical_name_ja AS cause_name"
        )
        effects_query = (
            "MATCH (cause:Meaning {canonical_name_ja: $concept_name})-[:Causes]->(effect:Meaning) "
            "RETURN effect.canonical_name_ja AS effect_name"
        )

        def work(tx, name):
            # 2つのクエリを1つのトランザクションで実行
            causes_result = tx.run(causes_query, concept_name=name)
            effects_result = tx.run(effects_query, concept_name=name)
            
            causes = [record["cause_name"] for record in causes_result]
            effects = [record["effect_name"] for record in effects_result]
            
            return {"causes": causes, "effects": effects}
        
        try:
            with self.db_manager.driver.session() as session:
                return session.execute_read(work, concept_name_ja)
        except Neo4jError as e:
            logging.error(f"因果関係の検索中にデータベースエラーが発生: {e}")
            # エラー時も仕様通り空のマップを返すか、例外をraiseするかは設計によるが、
            # ここでは空を返すことで、より安定した挙動とする。
            return {"causes": [], "effects": []}