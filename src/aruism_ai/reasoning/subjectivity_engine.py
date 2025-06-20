######################################################################
# Aruism AI Project - Subjectivity Engine
#
# このファイルは、「主観性オーバーレイ」の原則に基づき、
# ユーザー固有の価値観を知識ベースに記録・操作する機能を定義します。
#
# 参照ドキュメント: Aruism_AI_Project_11_Cognitive_Architecture_Design.txt
# バージョン: 0.1
# 作成日: 2025-06-18
######################################################################

import os
import sys
from typing import Dict

# プロジェクトのルートディレクトリをシステムパスに追加
sys.path.append(os.getcwd())

from src.ontology.db_manager import GraphDBManager
from src.ontology.models import MeaningID, User

class SubjectivityEngine:
    """
    ユーザーの主観的な価値観を扱うエンジン。
    """
    def __init__(self, db_manager: GraphDBManager):
        self.db_manager = db_manager
        if self.db_manager.driver is None:
            raise ConnectionError("データベースドライバーが初期化されていません。")
        print("SubjectivityEngineが初期化されました。")

    def assign_subjective_view(self, user_id: str, concept_name_ja: str, view_properties: Dict):
        """
        指定されたユーザーと概念の間に、主観的な見解を持つ関係性を作成・更新します。
        :param user_id: ユーザーの一意の識別子
        :param concept_name_ja: 対象となる概念の日本語名
        :param view_properties: 関係性に設定する主観的価値観のプロパティ辞書
        """
        print(f"\n--- ユーザー「{user_id}」の「{concept_name_ja}」に対する見解を記録します ---")
        
        # Cypherクエリの作成
        query = (
            "MERGE (u:User {user_id: $user_id}) "
            "MERGE (m:Meaning {canonical_name_ja: $concept_name}) "
            "MERGE (u)-[r:HAS_VIEW_ON]->(m) "
            "SET r += $view_props"
        )
        
        def work(tx, uid, cname, props):
            tx.run(query, user_id=uid, concept_name=cname, view_props=props)
        
        with self.db_manager.driver.session() as session:
            session.execute_write(work, user_id, concept_name_ja, view_properties)
        
        print("見解の記録が完了しました。")

    def evaluate_sentiment(self, text: str) -> dict:
        """
        テキスト全体の主観的な感情の強さを簡易的に評価します。
        （今回はキーワードのマッチングによる仮実装）
        """
        # 感情の強さに関連するキーワード
        strong_keywords = ["愛", "憎", "絶対", "必ず", "決して", "最高", "最低", "重要"]
        moderate_keywords = ["思う", "感じる", "考える", "かもしれない"]
        
        score = 0.5  # デフォルトスコア
        
        # テキスト内のキーワードをチェック
        for keyword in strong_keywords:
            if keyword in text:
                score += 0.15
        
        for keyword in moderate_keywords:
            if keyword in text:
                score += 0.05
        
        # スコアを0.0から1.0の範囲に収める
        final_score = max(0.0, min(1.0, score))
        
        return {"score": final_score}


# このファイルが直接実行された場合にのみ以下のコードが動きます（テスト用）
if __name__ == '__main__':
    # --- 設定 ---
    NEO4J_URI = "neo4j://localhost:7687"
    NEO4J_USER = "neo4j"
    NEO4J_PASSWORD = "11dr34SSAAa_$$aae"  # ご自身のパスワードに変更してください
    
    # --- 実行 ---
    db_manager = GraphDBManager(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    
    if db_manager.driver:
        engine = SubjectivityEngine(db_manager)
        
        # テスト用のデータ
        test_user_id = "タカさん"
        test_concept = "資本主義"
        test_view = {
            "axis_sentiment": -0.8,
            "axis_beauty_ugliness": -0.9,
            "context": "2025年の個人的な見解"
        }
        
        # 主観的な見解を記録するメソッドを呼び出し
        engine.assign_subjective_view(test_user_id, test_concept, test_view)
        
        # evaluate_sentimentのテスト
        test_text = "私は絶対に愛している"
        result = engine.evaluate_sentiment(test_text)
        print(f"感情評価結果: {result}")
        
        db_manager.close()