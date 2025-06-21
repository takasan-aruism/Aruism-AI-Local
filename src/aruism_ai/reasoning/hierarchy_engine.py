######################################################################
# Aruism AI Project - Hierarchy Engine
#
# バージョン: 2.0 (AIチームのテスト仕様準拠版)
# 最終更新日: 2025-06-22
# 参照: アリズム原典§2.6「存在の階層性」
######################################################################

from aruism_ai.ontology.db_manager import GraphDBManager
from neo4j.exceptions import ServiceUnavailable, Neo4jError
import logging
import re

class HierarchyEngine:
    """
    存在の階層性の原則に基づいた推論を行うエンジン。
    軸（観点）に依存した、動的な階層探索をサポートする。
    """
    # [新機能] クラス変数として最大探索深度を定義
    MAX_DEPTH = 10

    def __init__(self, db_manager: GraphDBManager):
        self.db_manager = db_manager
        if self.db_manager.driver is None:
            raise ConnectionError("データベースドライバーが初期化されていません。")

    def _sanitize_concept_name(self, concept_name: str) -> str:
        """
        [新機能] Cypherインジェクションを防ぐため、入力文字列を無害化する。
        """
        # 前後の空白を除去
        sanitized = concept_name.strip()
        # 危険な可能性のある一部の記号を除去（日本語の句読点や括弧は意図的に保持）
        sanitized = re.sub(r'[;{}()|&`]', '', sanitized)
        return sanitized

    def trace_upwards(self, concept_name_ja: str, axis: str = None) -> list[str]:
        """
        指定された概念から上位概念を辿る。軸が指定されれば、その文脈での階層を返す。
        """
        # [新機能] 入力値のバリデーション
        if not concept_name_ja or not isinstance(concept_name_ja, str):
            raise ValueError("concept_name_jaは有効な文字列でなければなりません。")

        # [新機能] 入力値の無害化と正規化（小文字化）
        sanitized_name = self._sanitize_concept_name(concept_name_ja).lower()
        
        # 軸（観点）に応じてCypherクエリを動的に構築
        # 軸が指定されている場合、関係性のプロパティをチェックする
        axis_match_clause = "WHERE r.valid_under_axis = $axis" if axis else ""

        # MATCH句でパスを定義し、可変長の関係を探索
        # RETURN句でパス内の全ノードを返し、順序を維持
        query = (
            f"MATCH path = (start:Meaning)-[:Is_A*1..{self.MAX_DEPTH}]->(parent:Meaning) "
            f"WHERE start.canonical_name_ja = $name "
            # TODO: 軸の仕様が固まり次第、以下のMATCH句は要調整
            # f"{axis_match_clause} "
            "WITH nodes(path) as path_nodes "
            "UNWIND range(1, size(path_nodes)-1) as i "
            "RETURN path_nodes[i].canonical_name_ja as hierarchy"
        )
        
        def work(tx, name, axis_param):
            # 軸がNoneの場合でもパラメータとして渡せるように調整
            params = {"name": name}
            if axis_param:
                params["axis"] = axis_param

            result = tx.run(query, **params)
            # 重複を除きつつ順序を保持
            return list(dict.fromkeys([record["hierarchy"] for record in result]))

        try:
            with self.db_manager.driver.session() as session:
                hierarchy = session.execute_read(work, sanitized_name, axis)
                return hierarchy if hierarchy else []
        except (ServiceUnavailable, Neo4jError) as e:
            # [新機能] Neo4jの具体的な例外を捕捉し、より安定したエラーを返す
            logging.error(f"階層探索中にデータベースエラーが発生: {e}")
            raise RuntimeError(f"階層探索に失敗しました: {getattr(e, 'code', 'N/A')}") from e
        except Exception as e:
            logging.error(f"階層探索中に予期せぬエラーが発生: {e}")
            raise RuntimeError("階層探索中に予期せぬエラーが発生しました") from e