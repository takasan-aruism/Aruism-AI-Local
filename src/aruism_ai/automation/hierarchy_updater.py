# src/aruism_ai/automation/hierarchy_updater.py

import os
import sys
import json
import logging
import argparse

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(PROJECT_ROOT)

from aruism_ai.ontology.db_manager import GraphDBManager


class HierarchyUpdater:
    def __init__(self, db_manager: GraphDBManager):
        self.db_manager = db_manager

    def _update_hierarchy_transaction(self, tx, concept_id, axis_name, levels_data):
        """トランザクション内で階層データを更新"""
        # 既存の階層を削除
        tx.run("MATCH (c:Concept {concept_id: $concept_id})-[r:HAS_AXIS]->(a:Axis) DETACH DELETE a", 
               concept_id=concept_id)
        
        # 新しい階層を作成
        query = """
        MATCH (c:Concept {concept_id: $concept_id})
        CREATE (a:Axis {name: $axis_name})
        CREATE (c)-[:HAS_AXIS]->(a)
        WITH a
        UNWIND $levels AS level_props
        CREATE (h:HierarchyLevel {
            level: level_props.level,
            concept: level_props.concept,
            english: level_props.english
        })
        CREATE (a)-[:HAS_LEVEL {level: toInteger(level_props.level)}]->(h)
        RETURN count(h) AS created_count
        """
        result = tx.run(query, concept_id=concept_id, axis_name=axis_name, levels=list(levels_data.values()))
        return result.single()["created_count"]

    def run_update(self, concept_id: str, json_file_path: str):
        """JSONファイルからデータベースを更新するメインメソッド"""
        try:
            # JSONファイルを読み込む
            with open(json_file_path, 'r', encoding='utf-8') as f:
                full_data = json.load(f)
            
            # データベースセッションを開始
            with self.db_manager.driver.session(database="neo4j") as session:
                update_count = 0
                
                # 各軸のデータを処理
                for axis_name, axis_data in full_data.items():
                    if axis_name.startswith("_"):  # メタデータはスキップ
                        continue
                    
                    # 新と古それぞれの階層を処理
                    for target_concept_key in ['新', '古']:
                        if target_concept_key in axis_data:
                            levels_data = axis_data[target_concept_key]
                            
                            # 適切なコンセプトIDを決定
                            # TODO: 本来は対称ペアのIDをDBから取得すべき
                            if target_concept_key == '新':
                                target_id = concept_id
                            else:
                                # 暫定的に古のIDをM0099と仮定
                                target_id = "M0099"
                            
                            # データベースを更新
                            created_count = session.execute_write(
                                self._update_hierarchy_transaction, 
                                target_id, 
                                axis_name, 
                                levels_data
                            )
                            
                            logging.info(
                                f"成功: コンセプトID '{target_id}' の軸 '{axis_name}' に "
                                f"{created_count} 個の階層レベルを格納しました。"
                            )
                            update_count += 1
                
                logging.info(f"合計 {update_count} 個の軸の更新が完了しました。")

        except Exception as e:
            logging.error(f"アップデート中にエラー: {e}", exc_info=True)
            raise


if __name__ == '__main__':
    log_level_str = os.environ.get("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(level=log_level_str, format='%(asctime)s - %(levelname)s - %(message)s')

    parser = argparse.ArgumentParser(description="生成された階層データをデータベースに格納します。")
    parser.add_argument("concept_id", type=str, help="更新対象のコンセプトID (例: M0001)")
    parser.add_argument("json_file", type=str, help="階層データを含むJSONファイルのパス")
    args = parser.parse_args()

    db_manager = None
    try:
        NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD")
        if not NEO4J_PASSWORD:
            raise ValueError("環境変数 NEO4J_PASSWORD が設定されていません。")

        db_manager = GraphDBManager(
            uri="bolt://aristo-db:7687",
            user="neo4j",
            password=NEO4J_PASSWORD
        )
        
        if db_manager.driver:
            updater = HierarchyUpdater(db_manager)
            updater.run_update(args.concept_id, args.json_file)
        else:
            logging.error("データベース接続に失敗しました。")
            
    except Exception as e:
        logging.error(f"実行エラー: {e}", exc_info=True)
        sys.exit(1)
    finally:
        if db_manager:
            db_manager.close()
            logging.info("データベース接続をクローズしました。")