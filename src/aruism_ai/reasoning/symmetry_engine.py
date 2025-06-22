######################################################################
# Aruism AI Project - Symmetry Engine
# バージョン: 0.6 (detect_tensionメソッドのバグ修正版)
# 作成日: 2025-06-22
######################################################################

from aruism_ai.ontology.db_manager import GraphDBManager
from janome.tokenizer import Tokenizer
import logging

class SymmetryEngine:
    def __init__(self, db_manager: GraphDBManager):
        self.db_manager = db_manager
        self.tokenizer = Tokenizer()
        if self.db_manager.driver is None:
            raise ConnectionError("データベースドライバーが初期化されていません。")

    # ▼▼▼ Retrieverが必要とする、この新しいメソッドが重要です ▼▼▼
    def get_symmetric_concept(self, concept_name_ja: str) -> str | None:
        """指定された概念の対称概念名をデータベースから検索して返す。"""
        query = (
            "MATCH (a:Meaning {canonical_name_ja: $concept_name})-[r:Symmetric_To]-(b:Meaning) "
            "RETURN b.canonical_name_ja AS symmetric_name"
        )
        def work(tx, name):
            result = tx.run(query, concept_name=name)
            record = result.single()
            return record["symmetric_name"] if record else None
        with self.db_manager.driver.session() as session:
            return session.execute_read(work, concept_name_ja)

    def generate_inverted_question(self, concept_name_ja: str) -> str | None:
        """反転質問を生成します。内部でget_symmetric_conceptを使用。"""
        symmetric_name = self.get_symmetric_concept(concept_name_ja)
        if symmetric_name:
            return f"もし、「{concept_name_ja}」の対称的な存在である「{symmetric_name}」の視点から考えると、どのような意味や価値が見えてくるでしょうか？"
        else:
            return None

    def detect_tension(self, text: str) -> tuple[bool, tuple[str, str] | None]:
        """テキスト内の緊張関係を検出します。"""
        try:
            # (このメソッドのロジックは変更ありません)
            query = "MATCH (a:Meaning)-[:Symmetric_To]-(b:Meaning) RETURN a.canonical_name_ja AS name1, b.canonical_name_ja AS name2"
            def work(tx):
                result = tx.run(query)
                return [(r["name1"], r["name2"]) for r in result]
            with self.db_manager.driver.session() as session:
                symmetric_pairs = session.execute_read(work)
            tokens = [token.surface for token in self.tokenizer.tokenize(text)]
            for pair in symmetric_pairs:
                if pair[0] in tokens and pair[1] in tokens:
                    return True, pair
            return False, None
        except Exception as e:
            logging.error(f"detect_tension中にエラーが発生: {e}")
            raise e