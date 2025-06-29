######################################################################
# Aruism AI Project - SentiWordNet Importer
#
# バージョン: 2.1 (既存ノードへのエンリッチ機能 実装版)
# 作成日: 2025-06-23
######################################################################
import os
from tqdm import tqdm
import logging

from aruism_ai.ontology.db_manager import GraphDBManager

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

# （ファイルの先頭部分は変更なし）
class SentiWordNetImporter:
    def __init__(self, db_manager: GraphDBManager):
        self.db_manager = db_manager

    def run_update(self, filepath: str):
        updates_batch = []
        with open(filepath, 'r') as f:
            for line in tqdm(f, desc="SentiWordNetを解析中"):
                if line.startswith('#') or not line.strip():
                    continue
                
                parts = line.strip().split('\t')
                pos, offset, pos_score, neg_score, terms, gloss = parts
                wordnet_synset_id = f"{offset:0>8}-{pos}"

                if float(pos_score) > 0 or float(neg_score) > 0:
                    properties = {
                        "sentiment_positive": float(pos_score),
                        "sentiment_negative": float(neg_score),
                    }
                    updates_batch.append({
                        "wordnet_synset_id": wordnet_synset_id,
                        "properties": properties
                    })
        
        if updates_batch:
            print(f"\n--- SentiWordNetのスコア更新を開始します（{len(updates_batch)}件）---")
            # 新しいバッチメソッドを呼び出す
            self.db_manager.batch_update_node_properties_by_synset(updates_batch)
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    db_manager = None
    try:
        PROJECT_ROOT = find_project_root()
        SENTIWORDNET_PATH = os.path.join(PROJECT_ROOT, "data", "SentiWordNet_3.0.0.txt")
        
        NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
        NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
        NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD")

        if not NEO4J_PASSWORD:
            raise ValueError("環境変数 NEO4J_PASSWORD が設定されていません。")

        db_manager = GraphDBManager(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)

        if db_manager.driver:
            importer = SentiWordNetImporter(db_manager)
            importer.run_update(SENTIWORDNET_PATH)

    except Exception as e:
        logging.error(f"メイン処理でエラーが発生しました: {e}", exc_info=True)
    finally:
        if db_manager:
            db_manager.close()
            print("データベース接続を閉じました。")
