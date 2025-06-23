######################################################################
# Aruism AI Project - Genesis Importer
#
# 「原初の概念リスト」(CSV)を知識ベースに登録する、最初のインポーター。
#
# バージョン: 1.0
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

    def run_import(self, filepath: str):
        """指定されたCSVファイルを読み込み、内容をDBにインポートする。"""
        if not self.db_manager:
            logging.error("DBManagerが提供されていません。")
            return

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f, delimiter=';')
                data = list(reader)

            # パス1: 全てのConceptノードを作成
            print("\n--- パス1: 全ての概念ノードを作成します ---")
            for row in tqdm(data, desc="ノード作成中"):
                node = Concept(
                    concept_id=row['concept_id'],
                    symbol=row['symbol'],
                    canonical_name_ja=row['axis_kanji'],
                    category=row['category'],
                    source=['genesis_import']
                )
                # メソッド名を create_concept_node に変更（より正確に）
                self.db_manager.create_concept_node(node)
            
            # パス2: 全てのSymmetric_To関係性を作成
            print("\n--- パス2: 対称関係を作成します ---")
            for row in tqdm(data, desc="関係性作成中"):
                source_id = row['concept_id']
                target_id = row['symmetric_concept_id']
                if source_id and target_id:
                    rel = Relationship(
                        source_concept_id=source_id,
                        target_concept_id=target_id,
                        relationship_type="Symmetric_To",
                        source_of_data="genesis_import"
                    )
                    self.db_manager.create_relationship(rel)

            print("\n--- 原初の概念のインポートが完了しました ---")

        except FileNotFoundError:
            logging.error(f"ファイルが見つかりません: {filepath}")
        except Exception as e:
            logging.error(f"予期せぬエラーが発生しました: {e}", exc_info=True)

# 実行ブロック
if __name__ == '__main__':
    db_manager = None
    try:
        PROJECT_ROOT = find_project_root()
        CSV_PATH = os.path.join(PROJECT_ROOT, "data", "AruismBaseDBTable.csv")
        
        NEO4J_URI = "bolt://localhost:7687"
        NEO4J_USER = "neo4j"
        NEO4J_PASSWORD = "11dr34SSAAa_$$aae" # ご自身のパスワード

        db_manager = GraphDBManager(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
        if db_manager.driver:
            print("\n【重要】データベースをクリアします...")
            db_manager.execute_query("MATCH (n) DETACH DELETE n")
            print(" -> 完了")

            importer = GenesisImporter(db_manager)
            importer.run_import(CSV_PATH)
    except Exception as e:
        print(f"メイン処理でエラーが発生しました: {e}")
    finally:
        if db_manager:
            db_manager.close()
            print("データベース接続を閉じました。")