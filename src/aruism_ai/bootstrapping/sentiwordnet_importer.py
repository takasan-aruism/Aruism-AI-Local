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

class SentiWordNetImporter:
    def __init__(self, db_manager: GraphDBManager):
        self.db_manager = db_manager

    def run_update(self, sentiwordnet_path: str):
        """
        SentiWordNetファイルを解析し、データベースのノードプロパティを更新します。
        """
        if not self.db_manager:
            logging.error("DBManagerが提供されていません。")
            return

        print("\n--- SentiWordNetのスコア更新を開始します ---")
        updated_count = 0
        try:
            with open(sentiwordnet_path, 'r', encoding='utf-8') as f:
                for line in tqdm(f, desc="SentiWordNetを解析中"):
                    if line.strip().startswith('#') or not line.strip():
                        continue
                    
                    parts = line.strip().split('\t')
                    if len(parts) < 5: continue
                        
                    pos, offset_id, pos_score_str, neg_score_str = parts[0], parts[1], parts[2], parts[3]
                    
                    try:
                        pos_score = float(pos_score_str)
                        neg_score = float(neg_score_str)
                    except ValueError:
                        continue

                    if pos_score == 0.0 and neg_score == 0.0:
                        continue
                        
                    # WordNetのsynset ID形式に変換
                    wordnet_synset_id = f"{offset_id.zfill(8)}-{pos}"
                    
                    # 更新するプロパティの辞書を作成
                    properties_to_update = {
                        "sentiment_positive": pos_score,
                        "sentiment_negative": neg_score
                    }
                    
                    # WordNet IDをキーにして、対応するノードのプロパティを更新
                    self.db_manager.update_node_properties_by_wordnet_id(wordnet_synset_id, properties_to_update)
                    updated_count += 1
                        
            print(f"--- {updated_count}件のノードに感情スコアを付与しました ---")
        except FileNotFoundError:
            logging.error(f"エラー: SentiWordNetファイルが見つかりません。パス: {sentiwordnet_path}")
        except Exception as e:
            logging.error(f"エラーが発生しました: {e}", exc_info=True)

if __name__ == '__main__':
    db_manager = None
    try:
        PROJECT_ROOT = find_project_root()
        SENTIWORDNET_PATH = os.path.join(PROJECT_ROOT, "data", "SentiWordNet_3.0.0.txt")
        
        NEO4J_URI = "bolt://localhost:7687"
        NEO4J_USER = "neo4j"
        NEO4J_PASSWORD = "11dr34SSAAa_$$aae" # ご自身のパスワード

        db_manager = GraphDBManager(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
        if db_manager.driver:
            # 最初にwordnet_importerを実行して、wordnet_synset_idを付与しておく必要があります
            print("【前提処理】WordNet Importerによるエンリッチを先に実行してください。")
            # (この部分は手動実行や、より大きなバッチスクリプトで管理するのが望ましい)
            
            importer = SentiWordNetImporter(db_manager)
            importer.run_update(SENTIWORDNET_PATH)
    except Exception as e:
        print(f"メイン処理でエラーが発生しました: {e}")
    finally:
        if db_manager:
            db_manager.close()
            print("データベース接続を閉じました。")