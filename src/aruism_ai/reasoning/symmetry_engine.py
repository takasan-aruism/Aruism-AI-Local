######################################################################
# Aruism AI Project - Symmetry Engine
#
# このファイルは、「存在の対称性」の原則に基づき、
# 反転質問などを生成する機能を定義します。
#
# 参照ドキュメント: Aruism_AI_Project_11_Cognitive_Architecture_Design.txt
# バージョン: 0.2
# 作成日: 2025-06-19
######################################################################

import os
import sys

# プロジェクトのルートディレクトリをシステムパスに追加
sys.path.append(os.getcwd())

from aruism_ai.ontology.db_manager import GraphDBManager
from janome.tokenizer import Tokenizer

class SymmetryEngine:
    # ( __init__ は変更なし )
    def __init__(self, db_manager: GraphDBManager):
        self.db_manager = db_manager
        self.tokenizer = Tokenizer()
        if self.db_manager.driver is None:
            raise ConnectionError("データベースドライバーが初期化されていません。")

    def generate_inverted_question(self, concept_name_ja: str) -> str | None:
        query = (
            "MATCH (a:Meaning {canonical_name_ja: $concept_name})-[r:Symmetric_To]-(b:Meaning) "
            "RETURN b.canonical_name_ja AS symmetric_name"
        )
        def work(tx, name):
            result = tx.run(query, concept_name=name)
            record = result.single()
            return record["symmetric_name"] if record else None
        
        # ▼▼▼ [修正点] DBエラーを捕捉する try...exceptブロックを追加 ▼▼▼
        try:
            with self.db_manager.driver.session() as session:
                symmetric_name = session.execute_read(work, concept_name_ja)
            
                if symmetric_name:
                    return f"もし、「{concept_name_ja}」の対称的な存在である「{symmetric_name}」の視点から考えると、どのような意味や価値が見えてくるでしょうか？"
                else:
                    return None
        except Exception as e:
            print(f"Error during generate_inverted_question: {e}")
            # エラーが発生した場合は、元の例外を再発生させるか、カスタム例外を発生させる
            raise e

    def detect_tension(self, text: str) -> tuple[bool, tuple[str, str] | None]:
        """
        与えられたテキストの中に、対称的な概念ペアが含まれているか（緊張関係か）を検出します。
        :param text: 分析するテキスト
        :return: 検出された場合、Trueと概念ペアのタプル。されなければFalseとNone。
        """
        print(f"\n--- テキスト内の対称性の緊張を検出します ---")
        
        # まず、データベースから全ての対称関係ペアを取得
        query = "MATCH (a:Meaning)-[:Symmetric_To]-(b:Meaning) RETURN a.canonical_name_ja AS name1, b.canonical_name_ja AS name2"
        
        def work(tx):
            result = tx.run(query)
            return [(r["name1"], r["name2"]) for r in result]

        with self.db_manager.driver.session() as session:
            symmetric_pairs = session.execute_read(work)

        # テキストを単語に分割
        tokens = [token.surface for token in self.tokenizer.tokenize(text)]
        
        # テキスト内に対称ペアが存在するかチェック
        for pair in symmetric_pairs:
            if pair[0] in tokens and pair[1] in tokens:
                print(f"緊張関係を検出しました: {pair}")
                return True, pair
        
        print("対称性の緊張は見つかりませんでした。")
        return False, None
    # ★★★ ここまでが新しいメソッドです ★★★

# このファイルが直接実行された場合にのみ以下のコードが動きます（テスト用）
if __name__ == '__main__':
    # --- 設定 ---
    NEO4J_URI = "neo4j://localhost:7687"
    NEO4J_USER = "neo4j"
    NEO4J_PASSWORD = "11dr34SSAAa_$$aae"  # ご自身のパスワードに変更してください

    # --- 実行 ---
    db_manager = GraphDBManager(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)

    if db_manager.driver:
        engine = SymmetryEngine(db_manager)

        # 1. 以前のテスト（反転質問の生成）
        question = engine.generate_inverted_question("善")
        if question:
            print("\n--- 生成された反転質問 ---")
            print(question)
        
        print("\n" + "="*40 + "\n")

        # 2. 新しい機能のテスト（対称性の緊張を検出）
        test_sentence = "この世には善も悪も存在する。"
        has_tension, pair = engine.detect_tension(test_sentence)
        if has_tension:
            print(f"\n--- 検出結果 ---")
            print(f"文「{test_sentence}」には、{pair}という対称的な概念が含まれています。")

        db_manager.close()