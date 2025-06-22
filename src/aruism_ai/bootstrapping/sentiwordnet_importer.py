######################################################################
# Aruism AI Project - SentiWordNet Importer
#
# バージョン: 2.0 (新Conceptモデル・プロジェクト標準準拠版)
# 最終更新日: 2025-06-22
######################################################################

import os
from tqdm import tqdm

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
    """
    SentiWordNetのデータを解析し、Neo4jのConceptノードに感情スコアを追記するクラス。
    """
    def __init__(self, sentiwordnet_path, db_manager: GraphDBManager):
        self.sentiwordnet_path = sentiwordnet_path
        self.db_manager = db_manager

    def parse_and_update_scores(self):
        """
        SentiWordNetファイルを解析し、データベースのノードプロパティを更新します。
        """
        print("\n--- SentiWordNetのスコア更新を開始します ---")
        updated_count = 0
        
        try:
            with open(self.sentiwordnet_path, 'r', encoding='utf-8') as f:
                for line in tqdm(f, desc="SentiWordNetを解析中"):
                    if line.strip().startswith('#') or not line.strip():
                        continue
                    
                    parts = line.strip().split('\t')
                    if len(parts) < 5: continue # SynsetTerms列があるので5未満
                        
                    pos, offset_id, pos_score_str, neg_score_str = parts[0], parts[1], parts[2], parts[3]
                    
                    try:
                        pos_score = float(pos_score_str)
                        neg_score = float(neg_score_str)
                    except ValueError:
                        continue # スコアが数値でない場合はスキップ

                    # スコアが両方0の場合は更新不要（効率化）
                    if pos_score == 0.0 and neg_score == 0.0:
                        continue
                        
                    # ConceptノードのID形式（例: 00001740-n）に変換
                    concept_id = f"{offset_id.zfill(8)}-{pos}"
                    
                    properties_to_update = {
                        "sentiment_positive": pos_score,
                        "sentiment_negative": neg_score
                    }
                    self.db_manager.update_node_properties(concept_id, properties_to_update)
                    updated_count += 1
                        
            print(f"--- {updated_count}件のノードに感情スコアを付与しました ---")
            
        except FileNotFoundError:
            print(f"エラー: SentiWordNetファイルが見つかりません。パス: {self.sentiwordnet_path}")
        except Exception as e:
            print(f"エラーが発生しました: {e}")

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
            importer = SentiWordNetImporter(SENTIWORDNET_PATH, db_manager)
            importer.parse_and_update_scores()
    except Exception as e:
        print(f"メイン処理でエラーが発生しました: {e}")
    finally:
        if db_manager:
            db_manager.close()