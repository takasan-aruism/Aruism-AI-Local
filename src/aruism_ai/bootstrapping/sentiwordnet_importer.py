######################################################################
# Aruism AI Project - SentiWordNet Importer
#
# このファイルは、SentiWordNetのデータを解析し、
# 既存のMeaningIDノードに感情スコアを付与する機能を定義します。
#
# 参照ドキュメント: Aruism_AI_Project_11_Cognitive_Architecture_Design.txt
# バージョン: 0.1
# 作成日: 2025-06-18
######################################################################

import os
import sys
from tqdm import tqdm

# プロジェクトのルートディレクトリをシステムパスに追加
sys.path.append(os.getcwd())

from src.ontology.db_manager import GraphDBManager

class SentiWordNetImporter:
    """
    SentiWordNetのデータを解析し、Neo4jのノードに感情スコアを追記するクラス。
    """
    def __init__(self, sentiwordnet_path, db_manager: GraphDBManager):
        self.sentiwordnet_path = sentiwordnet_path
        self.db_manager = db_manager

    def parse_and_update_scores(self):
        """
        SentiWordNetファイルを解析し、データベースのノードを更新します。
        """
        print("\n--- SentiWordNetのスコア更新を開始します ---")
        updated_count = 0
        
        try:
            with open(self.sentiwordnet_path, 'r', encoding='utf-8') as f:
                # tqdmでファイル全体をラップし、行数の進捗を表示
                for line in tqdm(f, desc="SentiWordNetを解析中"):
                    # コメント行や空行はスキップ
                    if line.strip().startswith('#') or not line.strip():
                        continue
                    
                    parts = line.strip().split('\t')
                    if len(parts) < 4:
                        continue
                        
                    pos = parts[0]
                    offset_id = parts[1]
                    pos_score = float(parts[2])
                    neg_score = float(parts[3])
                    
                    # AruismのMeaningID形式（例: 00001740-n）に変換
                    # SentiWordNetのIDは8桁の数字なので、ゼロパディングします
                    meaning_id = f"{offset_id.zfill(8)}-{pos}"
                    
                    # ポジティブスコアとネガティブスコアから単一の感情スコアを計算
                    sentiment_score = pos_score - neg_score
                    
                    # スコアが0でない場合のみ更新（効率化のため）
                    if sentiment_score != 0:
                        properties_to_update = {
                            # Aruismの「価値軸」の一つとして感情スコアを保存
                            "axis_sentiment": sentiment_score
                        }
                        self.db_manager.update_node_properties(meaning_id, properties_to_update)
                        updated_count += 1
                        
            print(f"--- {updated_count}件のノードに感情スコアを付与しました ---")
            
        except FileNotFoundError:
            print(f"エラー: SentiWordNetファイルが見つかりません。パス: {self.sentiwordnet_path}")
        except Exception as e:
            print(f"エラーが発生しました: {e}")

# このファイルが直接実行された場合にのみ以下のコードが動きます
if __name__ == '__main__':
    # --- 設定 ---
    PROJECT_ROOT = os.getcwd()
    # ★★★ 注意：ファイルパスはご自身の環境に合わせて確認してください ★★★
    SENTIWORDNET_PATH = os.path.join(PROJECT_ROOT, "data", "SentiWordNet_3.0.0.txt")
    
    NEO4J_URI = "neo4j://localhost:7687"
    NEO4J_USER = "neo4j"
    NEO4J_PASSWORD = "11dr34SSAAa_$$aae" # ご自身のパスワードに変更してください

    # --- 実行 ---
    db_manager = GraphDBManager(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)

    if db_manager.driver:
        importer = SentiWordNetImporter(SENTIWORDNET_PATH, db_manager)
        importer.parse_and_update_scores()
        db_manager.close()