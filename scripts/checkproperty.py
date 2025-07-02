# scripts/checkproperty.py

import os
import sys
sys.path.append('/workspace/Aruism-AI-Local')

from src.aruism_ai.ontology.db_manager import GraphDBManager

# データベース接続
db = GraphDBManager(
    uri='bolt://aristo-db:7687',
    user='neo4j', 
    password=os.environ.get('NEO4J_PASSWORD')
)

print("=== データ構造の確認 ===")

# HierarchyLevelノードのプロパティを確認
result = db.execute_query('''
MATCH (c:Concept {concept_id: 'M0001'})-[:HAS_AXIS]->(a)-[:HAS_LEVEL]->(l)
RETURN labels(l)[0] as label, keys(l) as properties, l.concept as concept, l.level as level
LIMIT 5
''')

print(f"検索結果: {len(result)}件\n")

for i, r in enumerate(result):
    print(f"レコード {i+1}:")
    print(f"  ラベル: {r['label']}")
    print(f"  プロパティ: {r['properties']}")
    print(f"  コンセプト: {r['concept']}")
    print(f"  レベル: {r['level']}")
    print("-" * 40)

# HAS_LEVELリレーションのプロパティも確認
print("\n=== リレーションのプロパティ確認 ===")
result2 = db.execute_query('''
MATCH (c:Concept {concept_id: 'M0001'})-[:HAS_AXIS]->(a)-[hl:HAS_LEVEL]->(l)
RETURN keys(hl) as rel_properties, hl.level as rel_level
LIMIT 5
''')

for i, r in enumerate(result2):
    print(f"リレーション {i+1}:")
    print(f"  プロパティ: {r['rel_properties']}")
    print(f"  レベル値: {r['rel_level']}")
    print("-" * 40)

db.close()