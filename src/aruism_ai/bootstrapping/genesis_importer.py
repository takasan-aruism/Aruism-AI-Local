######################################################################
# Aruism AI Project - Genesis Importer
#
# 「原初の概念リスト」(CSV)を知識ベースに登録する、最初のインポーター。
#
# バージョン: 1.1 (メモリ効率化版)
# 作成日: 2025-06-23
######################################################################

import os
import csv
from tqdm import tqdm
import logging
from aruism_ai.ontology.db_manager import GraphDBManager
from aruism_ai.ontology.models import Concept, Relationship

def find_project_root(marker_file='pyproject.toml'):
    """プロジェクトのルートディレクトリを堅牢に特定する。"""
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
        self.batch_size = 100  # バッチサイズを設定

    def clear_database(self):
        """データベースを効率的にクリアする"""
        print("\n【重要】データベースをクリアします...")
        try:
            # まずカウントを取得
            count_query = "MATCH (n) RETURN count(n) as count"
            result = self.db_manager.execute_query(count_query)
            total_nodes = result[0]['count'] if result else 0
            
            if total_nodes == 0:
                print(" -> すでに空です")
                return
            
            # バッチで削除
            batch_size = 1000
            deleted = 0
            
            with tqdm(total=total_nodes, desc="ノード削除中") as pbar:
                while deleted < total_nodes:
                    delete_query = """
                    MATCH (n)
                    WITH n LIMIT $batch_size
                    DETACH DELETE n
                    RETURN count(n) as deleted_count
                    """
                    result = self.db_manager.execute_query(
                        delete_query, 
                        {"batch_size": batch_size}
                    )
                    
                    if result and result[0]['deleted_count'] > 0:
                        batch_deleted = result[0]['deleted_count']
                        deleted += batch_deleted
                        pbar.update(batch_deleted)
                    else:
                        break
                        
            print(" -> 完了")
            
        except Exception as e:
            logging.error(f"データベースクリア中にエラー: {e}")
            raise

    def create_concepts_in_batch(self, concepts_batch):
        """概念ノードをバッチで作成"""
        query = """
        UNWIND $concepts as concept
        CREATE (n:Concept {
            concept_id: concept.concept_id,
            symbol: concept.symbol,
            canonical_name_ja: concept.canonical_name_ja,
            category: concept.category,
            source_of_data: concept.source_of_data
        })
        """
        
        concepts_data = [{
            'concept_id': c.concept_id,
            'symbol': c.symbol,
            'canonical_name_ja': c.canonical_name_ja,
            'category': c.category,
            'source_of_data': c.source_of_data
        } for c in concepts_batch]
        
        self.db_manager.execute_query(query, {"concepts": concepts_data})

    def create_relationships_in_batch(self, relationships_batch):
        """関係性をバッチで作成"""
        query = """
        UNWIND $relationships as rel
        MATCH (source:Concept {concept_id: rel.source_id})
        MATCH (target:Concept {concept_id: rel.target_id})
        CREATE (source)-[:Symmetric_To {
            source_of_data: rel.source_of_data
        }]->(target)
        """
        
        relationships_data = [{
            'source_id': r.source_concept_id,
            'target_id': r.target_concept_id,
            'source_of_data': r.source_of_data
        } for r in relationships_batch]
        
        self.db_manager.execute_query(query, {"relationships": relationships_data})

    def run_import(self, filepath: str):
        """指定されたCSVファイルを読み込み、内容をDBにインポートする。"""
        if not self.db_manager:
            logging.error("DBManagerが提供されていません。")
            return

        try:
            # データベースをクリア
            self.clear_database()
            
            # CSVファイルを読み込み
            with open(filepath, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f, delimiter=';')
                data = list(reader)
            
            # インデックスを作成（パフォーマンス向上のため）
            print("\n--- インデックスを作成します ---")
            self.db_manager.execute_query(
                "CREATE INDEX IF NOT EXISTS FOR (c:Concept) ON (c.concept_id)"
            )
            
            # パス1: 全てのConceptノードをバッチで作成
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
                
                # バッチサイズに達したら作成
                if len(concepts) >= self.batch_size:
                    self.create_concepts_in_batch(concepts)
                    concepts = []
            
            # 残りのノードを作成
            if concepts:
                self.create_concepts_in_batch(concepts)
            
            # パス2: 全てのSymmetric_To関係性をバッチで作成
            print("\n--- パス2: 対称関係を作成します ---")
            relationships = []
            
            for row in tqdm(data, desc="関係性準備中"):
                source_id = row['concept_id']
                target_id = row.get('symmetric_concept_id', '')
                
                if source_id and target_id:
                    rel = Relationship(
                        source_concept_id=source_id,
                        target_concept_id=target_id,
                        relationship_type="Symmetric_To",
                        source_of_data="genesis_import"
                    )
                    relationships.append(rel)
                    
                    # バッチサイズに達したら作成
                    if len(relationships) >= self.batch_size:
                        self.create_relationships_in_batch(relationships)
                        relationships = []
            
            # 残りの関係性を作成
            if relationships:
                self.create_relationships_in_batch(relationships)
            
            print("\n--- 原初の概念のインポートが完了しました ---")
            
        except FileNotFoundError:
            logging.error(f"ファイルが見つかりません: {filepath}")
        except Exception as e:
            logging.error(f"予期せぬエラーが発生しました: {e}", exc_info=True)
            raise

# 実行ブロック
if __name__ == '__main__':
    # ログ設定
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    db_manager = None
    try:
        PROJECT_ROOT = find_project_root()
        CSV_PATH = os.path.join(PROJECT_ROOT, "data", "AruismBaseDBTable.csv")
        
        NEO4J_URI = "bolt://localhost:7687"
        NEO4J_USER = "neo4j"
        NEO4J_PASSWORD = "11dr34SSAAa_$$aae"
        
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