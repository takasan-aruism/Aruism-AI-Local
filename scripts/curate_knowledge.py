######################################################################
# Aruism AI Project - Knowledge Curation Script
#
# 「アリズム原典」などの根源的知識を、構造化データとして
# 手動で知識ベースに登録するためのスクリプト。
#
# バージョン: 1.1 (クリーン版)
# 作成日: 2025-06-22
######################################################################

from aruism_ai.ontology.db_manager import GraphDBManager
from aruism_ai.ontology.models import MeaningID, Relationship

def register_chapter1_section1(db_manager: GraphDBManager):
    """
    「第一章一節 あるは、ある」の内容を知識ベースに登録する。
    """
    print("\n--- 「第一章一節 あるは、ある」の登録を開始 ---")

    node_aru = MeaningID(
        meaning_id="M_ARU_001", canonical_name={"ja": "ある", "en": "Aru / Be"},
        description={"ja": "全ての存在、現象、意識、価値の根源となる根本的な認識。"}, is_abstract=True
    )
    node_watashi = MeaningID(
        meaning_id="M_SELF_001", canonical_name={"ja": "私", "en": "I / Self"},
        description={"ja": "自己を指し示す、主観的な存在。"}, is_abstract=True
    )
    node_anata = MeaningID(
        meaning_id="M_OTHER_001", canonical_name={"ja": "あなた", "en": "You / Other"},
        description={"ja": "他者を指し示す、対称的な存在。"}, is_abstract=True
    )

    print("概念ノードを作成します...")
    db_manager.create_meaning_node(node_aru)
    db_manager.create_meaning_node(node_watashi)
    db_manager.create_meaning_node(node_anata)
    print(" -> 完了")

    rel_watashi_is_aru = Relationship("M_SELF_001", "M_ARU_001", "HAS_STATE_OF")
    rel_anata_is_aru = Relationship("M_OTHER_001", "M_ARU_001", "HAS_STATE_OF")
    rel_self_other_symmetric = Relationship("M_SELF_001", "M_OTHER_001", "Symmetric_To")

    print("関係性を作成します...")
    db_manager.create_relationship(rel_watashi_is_aru)
    db_manager.create_relationship(rel_anata_is_aru)
    db_manager.create_relationship(rel_self_other_symmetric)
    print(" -> 完了")

    print("--- 登録が完了しました。 ---\n")

def main():
    """メイン実行関数"""
    NEO4J_URI = "bolt://localhost:7687"
    NEO4J_USER = "neo4j"
    # !!! ご自身のNeo4jのパスワードを再度ご確認ください !!!
    NEO4J_PASSWORD = "11dr34SSAAa_$$aae" 

    db_manager = GraphDBManager(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    if db_manager.driver:
        try:
            print("既存のデータをクリアします...")
            db_manager.execute_query("MATCH (n) DETACH DELETE n")
            print(" -> 完了")
            
            register_chapter1_section1(db_manager)
        finally:
            db_manager.close()
    else:
        print("データベースへの接続に失敗したため、処理を中止しました。")

if __name__ == '__main__':
    main()