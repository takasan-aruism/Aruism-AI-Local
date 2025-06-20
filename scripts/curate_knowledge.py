######################################################################
# Aruism AI Project - Knowledge Curation Script
#
# このファイルは、WordNet等の自動インポートでは補いきれない、
# 重要な概念間の関係性を手動で定義し、データベースに補完（パッチ）します。
######################################################################

import os
from src.ontology.db_manager import GraphDBManager

# --- 設定 ---
NEO4J_URI = "neo4j://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "11dr34SSAAa_$$aae"

# --- ここに、手動で追加したい関係性を定義します ---
# [始点ノード名, 関係性タイプ, 終点ノード名] のリスト
MANUAL_RELATIONSHIPS = [
    ["善", "Symmetric_To", "悪"],
    # 今後、他にも追加したい関係性があれば、ここに追加していく
    # 例: ["人工知能", "Causes", "労働"] # これはあくまで例です
]

def main():
    """
    手動で定義した関係性をデータベースに作成するメイン関数。
    """
    print("--- 知識キュレーションを開始します ---")
    db_manager = GraphDBManager(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    
    if not db_manager.driver:
        print("データベースに接続できません。")
        return

    created_count = 0
    for rel_data in MANUAL_RELATIONSHIPS:
        source_name, rel_type, target_name = rel_data
        
        print(f"  > 関係性を作成中: ({source_name})-[{rel_type}]->({target_name})")
        
        # Cypherクエリで、名前を元にノードをマッチさせ、関係性を作成
        query = (
            "MATCH (a:Meaning {canonical_name_ja: $source}), (b:Meaning {canonical_name_ja: $target}) "
            f"MERGE (a)-[r:{rel_type} {{source_of_data: 'Manual_Curation'}}]->(b)"
        )
        
        try:
            with db_manager.driver.session() as session:
                session.run(query, source=source_name, target=target_name)
            created_count += 1
        except Exception as e:
            print(f"    - エラー: 関係性の作成に失敗しました - {e}")

    print(f"--- {created_count}件の知識キュレーションが完了しました ---")
    db_manager.close()


if __name__ == '__main__':
    main()