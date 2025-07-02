# scripts/manual_hierarchy_loader.py

import os
import sys
import json

sys.path.append('/workspace/Aruism-AI-Local')
from src.aruism_ai.ontology.db_manager import GraphDBManager

# JSONファイルを読み込む
with open('/workspace/Aruism-AI-Local/data/drafts/M0001_reasoned_draft.json', 'r') as f:
    data = json.load(f)

# データベース接続
db = GraphDBManager(
    uri='bolt://aristo-db:7687',
    user='neo4j',
    password=os.environ.get('NEO4J_PASSWORD')
)

print("既存データをクリア中...")
# 既存データをクリア
db.execute_query('MATCH (a:Axis) DETACH DELETE a')
db.execute_query('MATCH (h:HierarchyLevel) DETACH DELETE h')

print("\n新しいデータを挿入中...")

# 各軸を処理
for axis_name, axis_data in data.items():
    if axis_name.startswith('_'):
        continue
    
    print(f"\n処理中: {axis_name}")
    
    # 新と古それぞれを処理
    for concept_type in ['新', '古']:
        if concept_type not in axis_data:
            continue
            
        concept_id = 'M0001' if concept_type == '新' else 'M0099'
        levels = axis_data[concept_type]
        
        # Axisノードを作成
        db.execute_query("""
            MERGE (c:Concept {concept_id: $concept_id})
            MERGE (a:Axis {name: $axis_name, concept_id: $concept_id})
            MERGE (c)-[:HAS_AXIS]->(a)
        """, concept_id=concept_id, axis_name=axis_name)
        
        # 各レベルを処理
        for level_num, level_data in levels.items():
            if not level_num.isdigit():
                continue
                
            concept_ja = level_data.get('concept', '')
            concept_en = level_data.get('english', '')
            
            # HierarchyLevelノードを作成
            db.execute_query("""
                MATCH (a:Axis {name: $axis_name, concept_id: $concept_id})
                CREATE (h:HierarchyLevel {
                    level: toInteger($level_num),
                    concept: $concept_ja,
                    english: $concept_en,
                    concept_id: $concept_id,
                    axis_name: $axis_name
                })
                CREATE (a)-[:HAS_LEVEL {level: toInteger($level_num)}]->(h)
            """, axis_name=axis_name, concept_id=concept_id, 
                level_num=level_num, concept_ja=concept_ja, concept_en=concept_en)
            
            print(f"  {concept_type} レベル{level_num}: {concept_ja}")

print("\n処理完了！")
db.close()