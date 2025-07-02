# /workspace/Aruism-AI-Local/scripts/test_db_insertion.py

import os
import sys
import json
import logging

# プロジェクトのソースコードをインポートするためのパス設定
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(PROJECT_ROOT, 'src'))

from aruism_ai.ontology.db_manager import GraphDBManager
from aruism_ai.bootstrapping.hierarchy_updater import HierarchyUpdater

# --- このテスト専用のメイン処理 ---
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # 1. テストするコンセプトIDと、AIが生成したと仮定するJSONデータを定義
    CONCEPT_ID_TO_TEST = "M0001"
    
    # AIの生成結果を、テスト用に直接ここに書き込む
    TEST_DRAFT_DATA = {
        "time_conditions": {
            "新": {
                "1": {"concept": "瞬間的 (Momentary)", "english": "The instantaneous arising of novelty"},
                "2": {"concept": "短期的 (Short-term)", "english": "The fleeting nature of new forms"}
            },
            "古": {
                "1": {"concept": "永続的 (Perennial)", "english": "The enduring nature of tradition"},
                "2": {"concept": "歴史的 (Historical)", "english": "The accumulation of past experiences"}
            }
        }
    }
    
    # テスト用JSONデータを一時ファイルに保存
    DRAFT_DIR = os.path.join(PROJECT_ROOT, "data/drafts")
    os.makedirs(DRAFT_DIR, exist_ok=True)
    test_json_path = os.path.join(DRAFT_DIR, f"{CONCEPT_ID_TO_TEST}_db_test_draft.json")
    with open(test_json_path, 'w', encoding='utf-8') as f:
        json.dump(TEST_DRAFT_DATA, f, ensure_ascii=False, indent=2)
    logging.info(f"テスト用のJSONファイルを生成しました: {test_json_path}")

    # 2. データベースへの接続と更新処理の実行
    db_manager = None
    try:
        NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD")
        if not NEO4J_PASSWORD:
            raise ValueError("環境変数 NEO4J_PASSWORD が設定されていません。")

        db_manager = GraphDBManager(
            uri="bolt://arism-db:7687",
            user="neo4j",
            password=NEO4J_PASSWORD
        )
        
        if db_manager.driver:
            logging.info("DB接続成功。階層更新テストを開始します。")
            updater = HierarchyUpdater(db_manager)
            # updaterに、テスト用のコンセプトIDとJSONファイルのパスを渡す
            updater.run_update(CONCEPT_ID_TO_TEST, test_json_path)
            logging.info("階層更新テストが正常に完了しました。")
        else:
            logging.error("DB接続に失敗しました。")
            
    except Exception as e:
        logging.error(f"テスト実行中にエラーが発生しました: {e}", exc_info=True)
    finally:
        if db_manager:
            db_manager.close()
            logging.info("データベース接続をクローズしました。")