# /workspace/Aruism-AI-Local/src/aruism_ai/bootstrapping/genesis_importer.py (修正版)

import os
import csv
from tqdm import tqdm
import logging
import sys

# プロジェクトルートをパスに追加
SRC_PATH = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(SRC_PATH)
PROJECT_ROOT = os.path.dirname(SRC_PATH)

from aruism_ai.ontology.db_manager import GraphDBManager
from aruism_ai.ontology.models import Concept, Relationship

class GenesisImporter:
    def __init__(self, db_manager: GraphDBManager):
        self.db_manager = db_manager
        self.batch_size = 100

    def clear_database(self):
        print("\n【重要】データベースをクリアします...")
        try:
            count_query = "MATCH (n) RETURN count(n) as count"
            result = self.db_manager.execute_query(count_query)
            if result and result[0]['count'] > 0:
                self.db_manager.execute_query("MATCH (n) DETACH DELETE n")
                print(" -> 完了")
            else:
                print(" -> すでに空です")
        except Exception as e:
            logging.error(f"データベースクリア中にエラー: {e}")
            raise

    def create_concepts_in_batch(self, concepts_batch):
        query = """
        UNWIND $concepts as concept_props
        MERGE (c:Concept {concept_id: concept_props.concept_id})
        ON CREATE SET c = concept_props
        ON MATCH SET c += concept_props
        """
        concepts_data = [c.to_dict() for c in concepts_batch]
        self.db_manager.execute_query(query, concepts=concepts_data)

    def create_relationships_in_batch(self, relationships_batch):
        query = """
        UNWIND $relationships as rel
        MATCH (source:Concept {concept_id: rel.source_concept_id})
        MATCH (target:Concept {concept_id: rel.target_concept_id})
        MERGE (source)-[:Symmetric_To {source_of_data: rel.source_of_data}]->(target)
        """
        relationships_data = [r.to_dict() for r in relationships_batch]
        self.db_manager.execute_query(query, relationships=relationships_data)

    def run_import(self, filepath: str):
        if not self.db_manager or not self.db_manager.driver:
            logging.error("DBManagerが初期化されていないか、接続に失敗しています。")
            return
            
        try:
            self.clear_database()
            with open(filepath, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f, delimiter=';')
                data = list(reader)
            
            print(f"\n{len(data)}行のデータを読み込みました")
            print("\n--- インデックスを作成します ---")
            self.db_manager.execute_query("CREATE INDEX concept_id_index IF NOT EXISTS FOR (c:Concept) ON (c.concept_id)")
            
            print("\n--- パス1: 全ての概念ノードを作成します ---")
            concepts = []
            for row in tqdm(data, desc="ノード準備中"):
                node = Concept(
                    concept_id=row['concept_id'],
                    symbol=row.get('symbol', ''),
                    canonical_name_ja=row.get('axis_kanji', row.get('kanji_axis', '')),
                    category=row.get('category', ''),
                    source_of_data=['AruismBaseDBTable_Genesis']
                )
                concepts.append(node)
                if len(concepts) >= self.batch_size:
                    self.create_concepts_in_batch(concepts)
                    concepts = []
            if concepts:
                self.create_concepts_in_batch(concepts)
            
            print("\n--- パス2: 対称関係を作成します ---")
            relationships = []
            for row in tqdm(data, desc="関係性準備中"):
                if row.get('symmetric_concept_id'):
                    rel = Relationship(
                        source_concept_id=row['concept_id'],
                        target_concept_id=row['symmetric_concept_id'],
                        relationship_type="Symmetric_To",
                        source_of_data="genesis_import"
                    )
                    relationships.append(rel)
                    if len(relationships) >= self.batch_size:
                        self.create_relationships_in_batch(relationships)
                        relationships = []
            if relationships:
                self.create_relationships_in_batch(relationships)
            
            # 最終確認
            result = self.db_manager.execute_query("MATCH (c:Concept) RETURN COUNT(c) as count")
            if result:
                 print(f"\n✓ 作成されたコンセプト数: {result[0]['count']}")
            
            result = self.db_manager.execute_query("MATCH ()-[r:Symmetric_To]->() RETURN COUNT(r) as count")
            if result:
                print(f"✓ 作成された対称関係数: {result[0]['count']}")
            
            print("\n--- 原初の概念のインポートが完了しました ---")
            
        except Exception as e:
            logging.error(f"予期せぬエラーが発生しました: {e}", exc_info=True)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    db_manager = None
    try:
        data_dir = os.path.join(PROJECT_ROOT, "data")
        csv_path = os.path.join(data_dir, "AruismBaseDBTable.csv")
        
        if not os.path.exists(csv_path):
            print(f"エラー: CSVファイルが見つかりません: {csv_path}")
            exit(1)

        # --- ここから修正 ---
        # 環境変数から接続情報を取得
        NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://aristo-db:7687")
        NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
        NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD")
        # --- ここまで修正 ---

        if not NEO4J_PASSWORD:
            print("エラー: 環境変数 NEO4J_PASSWORD が設定されていません。")
            exit(1)

        print(f"Neo4jに接続中: {NEO4J_URI}")
        db_manager = GraphDBManager(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
        
        if db_manager.driver:
            print("✓ データベース接続成功")
            importer = GenesisImporter(db_manager)
            importer.run_import(csv_path)
        else:
            print("✗ データベース接続失敗")

    except Exception as e:
        logging.error(f"メイン処理でエラーが発生しました: {e}", exc_info=True)
    finally:
        if db_manager:
            db_manager.close()
            print("データベース接続を閉じました。")