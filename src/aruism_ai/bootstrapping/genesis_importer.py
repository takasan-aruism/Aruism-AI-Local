######################################################################
# Aruism AI Project - Genesis Importer
# バージョン: 1.3 (実際のインポート実行版)
######################################################################
import os
import csv
from tqdm import tqdm
import logging
from aruism_ai.ontology.db_manager import GraphDBManager
from aruism_ai.ontology.models import Concept, Relationship

def find_project_root(marker_file='pyproject.toml'):
    current_path = os.path.abspath(__file__)
    while True:
        parent_path = os.path.dirname(current_path)
        if os.path.exists(os.path.join(parent_path, marker_file)):
            return parent_path
        if parent_path == current_path:
            raise FileNotFoundError(f"Project root with '{marker_file}' not found.")
        current_path = parent_path

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
        CREATE (n:Concept) SET n = concept_props
        """
        concepts_data = [c.to_dict() for c in concepts_batch]
        self.db_manager.execute_query(query, concepts=concepts_data)

    def create_relationships_in_batch(self, relationships_batch):
        query = """
        UNWIND $relationships as rel
        MATCH (source:Concept {concept_id: rel.source_concept_id})
        MATCH (target:Concept {concept_id: rel.target_concept_id})
        CREATE (source)-[:Symmetric_To {source_of_data: rel.source_of_data}]->(target)
        """
        relationships_data = [r.to_dict() for r in relationships_batch]
        self.db_manager.execute_query(query, relationships=relationships_data)

    def run_import(self, filepath: str):
        if not self.db_manager or not self.db_manager.driver:
            logging.error("DBManagerが初期化されていないか、接続に失敗しています。")
            return
        
        if not os.path.exists(filepath):
            logging.error(f"CSVファイルが見つかりません: {filepath}")
            print(f"ファイルが存在しません: {filepath}")
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
                    symbol=row['symbol'],
                    canonical_name_ja=row['axis_kanji'],
                    category=row['category'],
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
            
            print("\n--- 原初の概念のインポートが完了しました ---")
        except FileNotFoundError:
            logging.error(f"ファイルが見つかりません: {filepath}")
        except Exception as e:
            logging.error(f"予期せぬエラーが発生しました: {e}", exc_info=True)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    db_manager = None
    try:
        PROJECT_ROOT = find_project_root()
        
        # CSVファイルのパスを設定
        # まず一般的な名前で試す
        possible_csv_names = [
            "AruismBaseDBTable_Genesis.csv",
            "AruismBaseDBTable.csv", 
            "genesis_data.csv",
            "genesis.csv"
        ]
        
        CSV_PATH = None
        for csv_name in possible_csv_names:
            test_path = os.path.join(PROJECT_ROOT, "data", csv_name)
            if os.path.exists(test_path):
                CSV_PATH = test_path
                print(f"CSVファイルを発見: {CSV_PATH}")
                break
        
        if not CSV_PATH:
            print("エラー: 以下のファイルのいずれも見つかりませんでした:")
            for csv_name in possible_csv_names:
                test_path = os.path.join(PROJECT_ROOT, "data", csv_name)
                print(f"  - {test_path}")
            print("\ndataディレクトリの内容:")
            data_dir = os.path.join(PROJECT_ROOT, "data")
            if os.path.exists(data_dir):
                for file in os.listdir(data_dir):
                    print(f"  - {file}")
            else:
                print("  dataディレクトリが存在しません")
            exit(1)

        # Neo4j接続設定
        NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
        NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
        NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD")

        if not NEO4J_PASSWORD:
            raise ValueError("環境変数 NEO4J_PASSWORD が設定されていません。ターミナルで 'export NEO4J_PASSWORD=\"あなたのパスワード\"' を実行してください。")

        db_manager = GraphDBManager(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
        
        if db_manager.driver:
            importer = GenesisImporter(db_manager)
            importer.run_import(CSV_PATH)

    except Exception as e:
        logging.error(f"メイン処理でエラーが発生しました: {e}", exc_info=True)
    finally:
        if db_manager:
            db_manager.close()
            print("データベース接続を閉じました。")
