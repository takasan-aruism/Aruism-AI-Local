# scripts/show_concept_data.py

import os
import sys
import argparse

# プロジェクトのルートディレクトリをPythonパスに追加
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(PROJECT_ROOT)

from src.aruism_ai.ontology.db_manager import GraphDBManager


def show_concept_data(concept_id: str):
    """指定されたコンセプトIDの階層データを表示"""
    
    # 環境変数から接続情報を取得
    neo4j_uri = os.environ.get("NEO4J_URI", "bolt://aristo-db:7687")
    neo4j_user = os.environ.get("NEO4J_USER", "neo4j")
    neo4j_password = os.environ.get("NEO4J_PASSWORD")
    
    if not neo4j_password:
        print("エラー: NEO4J_PASSWORD環境変数が設定されていません")
        return
    
    # データベースに接続
    db_manager = GraphDBManager(uri=neo4j_uri, user=neo4j_user, password=neo4j_password)
    
    try:
        # コンセプトとその階層を取得（重複を除去）
        query = """
        MATCH (c:Concept {concept_id: $concept_id})
        OPTIONAL MATCH (c)-[:Symmetric_To]-(p:Concept)
        OPTIONAL MATCH (c)-[:HAS_AXIS]->(a:Axis)
        OPTIONAL MATCH (a)-[:HAS_LEVEL]->(l:HierarchyLevel)
        WITH c, p, a, l
        ORDER BY a.name, l.concept
        RETURN DISTINCT c, p, a, l
        """
        
        results = db_manager.execute_query(query, concept_id=concept_id)
        
        if not results:
            print(f"コンセプトID '{concept_id}' が見つかりません")
            return
        
        # コンセプト情報を表示
        concept = results[0]['c']
        print("=" * 50)
        print(f"コンセプト情報: [{concept['concept_id']}] {concept.get('symbol', '')} {concept.get('canonical_name_ja', '')}")
        print("=" * 50)
        
        # 対称ペアを表示
        if results[0]['p']:
            pair = results[0]['p']
            print(f"  - 対称ペア: [{pair['concept_id']}] {pair.get('symbol', '')} {pair.get('canonical_name_ja', '')}")
        
        # 階層構造を表示
        current_axis = None
        has_hierarchy = False
        level_counter = {}  # 各軸のレベルカウンター
        
        for row in results:
            if row['a']:
                has_hierarchy = True
                axis = row['a']
                level = row['l']
                
                # 新しい軸の場合
                if current_axis != axis['name']:
                    current_axis = axis['name']
                    level_counter[current_axis] = 0
                    print(f"\n【軸: {current_axis}】")
                
                # レベル情報を表示
                if level:
                    level_counter[current_axis] += 1
                    level_num = level_counter[current_axis]
                    concept_ja = level.get('concept', '')
                    concept_en = level.get('english', '')
                    print(f"  レベル {level_num}: {concept_ja} ({concept_en})")
        
        if not has_hierarchy:
            print("\n- 関連する階層構造はありません。")
    
    finally:
        db_manager.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="コンセプトの階層データを表示")
    parser.add_argument("concept_id", help="表示するコンセプトのID (例: M0001)")
    args = parser.parse_args()
    
    show_concept_data(args.concept_id)