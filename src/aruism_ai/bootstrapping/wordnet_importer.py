# src/aruism_ai/bootstrapping/hierarchy_updater.py

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
        tx.run("MATCH (c:Concept {concept_id: $concept_id})-[r:HAS_AXIS]->(a:Axis) DETACH DELETE a", concept_id=concept_id)
        
        query = """
        MATCH (c:Concept {concept_id: $concept_id})
        CREATE (a:Axis {name: $axis_name})
        CREATE (c)-[:HAS_AXIS]->(a)
        WITH a
        UNWIND $levels AS level_props
        CREATE (h:HierarchyLevel {
            level: toInteger(level_props.level), 
            concept: level_props.concept,
            english: level_props.english
        })
        CREATE (a)-[:HAS_LEVEL {level: toInteger(level_props.level)}]->(h)
        RETURN count(h) AS created_count
        """
        result = tx.run(query, concept_id=concept_id, axis_name=axis_name, levels=list(levels_data.values()))
        return result.single()["created_count"]

    def run_update(self, concept_id: str, json_file_path: str):
        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                full_data = json.load(f)

            with self.db_manager.driver.session(database="neo4j") as session:
                for axis_name, axis_data in full_data.items():
                    if axis_name.startswith("_"): continue
                    
                    for target_concept_key in ['新', '古']:
                        if target_concept_key in axis_data:
                            levels_data = axis_data[target_concept_key]
                            
                            # Determine the correct concept_id
                            target_id = concept_id if target_concept_key == '新' else "M0099" # Assuming M0099 is '古'

                            created_count = session.execute_write(self._update_hierarchy_transaction, target_id, axis_name, levels_data)
                            logging.info(f"成功: コンセプトID '{target_id}' の軸 '{axis_name}' に {created_count} 個の階層レベルを格納しました。")

        except Exception as e:
            logging.error(f"アップデート中にエラー: {e}", exc_info=True)

if __name__ == '__main__':
    # ... (main block for direct execution) ...
    pass