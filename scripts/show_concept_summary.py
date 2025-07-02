# scripts/show_concept_summary.py

import os
import sys
import argparse
import json

# プロジェクトのルートディレクトリをPythonパスに追加
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(PROJECT_ROOT)

from src.aruism_ai.ontology.db_manager import GraphDBManager

# 40軸の定義
AXIS_DEFINITIONS = {
    "時間的条件": {"subconditions": ["瞬間的", "短期的", "中期的", "長期的"], "depth": 7},
    "空間的・スケール的条件": {"subconditions": ["個人レベル", "共同体レベル", "社会レベル", "宇宙レベル"], "depth": 6},
    "認識論的条件": {"subconditions": ["知覚される", "理解される", "体験される", "創造される"], "depth": 5},
    "存在論的条件": {"subconditions": ["物質的", "情報的", "関係的", "意味的"], "depth": 5},
    "連動性の条件": {"subconditions": ["独立的", "触発的", "連鎖的", "共振的"], "depth": 5},
    "共鳴度の条件": {"subconditions": ["表層的", "構造的", "本質的", "存在的"], "depth": 4},
    "対称性との関係条件": {"subconditions": ["破壊的", "包含的", "変容的", "循環的"], "depth": 5},
    "法則性の条件": {"subconditions": ["予測可能", "創発的", "偶発的", "必然的"], "depth": 4},
    "体験の質的条件": {"subconditions": ["驚きとして", "発見として", "創造として", "了解として"], "depth": 3},
    "価値生成の条件": {"subconditions": ["機能的", "美的", "倫理的", "聖性的"], "depth": 4}
}

def show_concept_summary(concept_id: str):
    """コンセプトの階層データのサマリーを表示"""
    
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
        # コンセプト情報を取得
        query = """
        MATCH (c:Concept {concept_id: $concept_id})
        OPTIONAL MATCH (c)-[:Symmetric_To]-(p:Concept)
        RETURN c, p
        """
        results = db_manager.execute_query(query, concept_id=concept_id)
        
        if not results:
            print(f"コンセプトID '{concept_id}' が見つかりません")
            return
        
        concept = results[0]['c']
        pair = results[0]['p']
        
        print("=" * 60)
        print(f"コンセプト: [{concept['concept_id']}] {concept.get('symbol', '')} {concept.get('canonical_name_ja', '')}")
        if pair:
            print(f"対称ペア: [{pair['concept_id']}] {pair.get('symbol', '')} {pair.get('canonical_name_ja', '')}")
        print("=" * 60)
        
        # 生成された軸を確認
        axis_query = """
        MATCH (c:Concept {concept_id: $concept_id})-[:HAS_AXIS]->(a:Axis)
        OPTIONAL MATCH (a)-[:HAS_LEVEL]->(l:HierarchyLevel)
        WITH a.name as axis_name, count(DISTINCT l) as level_count
        RETURN axis_name, level_count
        ORDER BY axis_name
        """
        
        axis_results = db_manager.execute_query(axis_query, concept_id=concept_id)
        
        print("\n【生成状況サマリー】")
        print("-" * 60)
        print(f"{'軸名':<20} {'期待深度':>8} {'実際':>6} {'状態':>8}")
        print("-" * 60)
        
        generated_axes = {row['axis_name']: row['level_count'] for row in axis_results}
        
        total_expected = 0
        total_actual = 0
        
        for axis_name, info in AXIS_DEFINITIONS.items():
            expected_depth = info['depth']
            actual_depth = generated_axes.get(axis_name, 0)
            total_expected += expected_depth
            total_actual += actual_depth
            
            if actual_depth == 0:
                status = "❌ 未生成"
            elif actual_depth < expected_depth:
                status = "⚠️  不足"
            elif actual_depth == expected_depth:
                status = "✅ 完了"
            else:
                status = "❗ 超過"
            
            print(f"{axis_name:<20} {expected_depth:>8} {actual_depth:>6} {status:>8}")
        
        print("-" * 60)
        print(f"{'合計':<20} {total_expected:>8} {total_actual:>6} ({total_actual/total_expected*100:.1f}%)")
        print("-" * 60)
        
        # 生成された内容の詳細表示
        if generated_axes:
            print("\n【生成された階層（詳細）】")
            
            detail_query = """
            MATCH (c:Concept {concept_id: $concept_id})-[:HAS_AXIS]->(a:Axis)
            OPTIONAL MATCH (a)-[:HAS_LEVEL]->(l:HierarchyLevel)
            RETURN a.name as axis_name, l.concept as concept, l.english as english
            ORDER BY a.name, l.concept
            """
            
            detail_results = db_manager.execute_query(detail_query, concept_id=concept_id)
            
            current_axis = None
            for row in detail_results:
                if row['axis_name'] != current_axis:
                    current_axis = row['axis_name']
                    print(f"\n【{current_axis}】")
                    level_num = 0
                
                if row['concept']:
                    level_num += 1
                    print(f"  レベル {level_num}: {row['concept']} ({row['english']})")
    
    finally:
        db_manager.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="コンセプトの階層生成状況を表示")
    parser.add_argument("concept_id", help="表示するコンセプトのID (例: M0001)")
    args = parser.parse_args()
    
    show_concept_summary(args.concept_id)