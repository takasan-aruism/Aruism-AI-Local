######################################################################
# Aruism AI Project - WordNet Importer
# バージョン: 1.4 (関係性取りこぼし防止ロジックを含む最終確定版)
# 作成日: 2025-06-18
######################################################################

import sqlite3
import os
import sys
from tqdm import tqdm

sys.path.append(os.getcwd())
from src.ontology.db_manager import GraphDBManager
from src.ontology.models import MeaningID, Relationship

class WordNetImporter:
    def __init__(self, sqlite_path, db_manager: GraphDBManager):
        self.sqlite_path = sqlite_path
        self.db_manager = db_manager
        self.synsets_to_import = {} 
        try:
            self.conn = sqlite3.connect(self.sqlite_path)
            self.conn.row_factory = sqlite3.Row
            self.cursor = self.conn.cursor()
            print(f"日本語WordNetデータベース({self.sqlite_path})への接続に成功しました。")
        except sqlite3.Error as e:
            print(f"日本語WordNetデータベースへの接続に失敗しました: {e}")
            self.conn = None

    def close(self):
        if self.conn:
            self.conn.close()
            print("日本語WordNetデータベース接続を閉じました。")

    def run_import(self, concept_names: list):
        if not self.conn:
            return

        print("--- ステップ1: ターゲット概念とその階層情報を収集 ---")
        for name in tqdm(concept_names, desc="階層情報収集中"):
            self._collect_hierarchy_for_concept(name)
        
        print(f"\n--- ステップ2: 収集した{len(self.synsets_to_import)}件の全ノードをDBにインポート ---")
        for synset_id, preferred_name in tqdm(self.synsets_to_import.items(), desc="ノードをインポート中"):
            self._import_node(synset_id, preferred_name)

        print("\n--- ステップ3: ノード間の関係性をDBにインポート ---")
        self._import_relationships()

    def _collect_hierarchy_for_concept(self, concept_name: str):
        query = "SELECT s.synset FROM sense s JOIN word w ON s.wordid = w.wordid WHERE w.lemma = ? AND s.lang = 'jpn' LIMIT 1"
        self.cursor.execute(query, (concept_name,))
        res = self.cursor.fetchone()
        if not res: 
            print(f"\n警告: '{concept_name}' はWordNetに見つかりませんでした。")
            return
        
        current_synset_id = res['synset']
        if current_synset_id not in self.synsets_to_import:
            self.synsets_to_import[current_synset_id] = concept_name
        
        while current_synset_id:
            parent_query = "SELECT synset2 FROM synlink WHERE synset1 = ? AND link = 'hype' LIMIT 1"
            self.cursor.execute(parent_query, (current_synset_id,))
            parent_res = self.cursor.fetchone()
            if parent_res:
                current_synset_id = parent_res['synset2']
                if current_synset_id not in self.synsets_to_import:
                    self.synsets_to_import[current_synset_id] = None
            else:
                break

    def _import_node(self, synset_id: str, preferred_name: str or None):
        query_def = "SELECT name FROM synset WHERE synset = ?"
        self.cursor.execute(query_def, (synset_id,))
        def_res = self.cursor.fetchone()
        english_name = def_res['name'] if def_res else ""

        query_name = "SELECT lemma FROM word w JOIN sense s ON w.wordid = s.wordid WHERE s.synset = ? AND s.lang = 'jpn' LIMIT 1"
        self.cursor.execute(query_name, (synset_id,))
        name_res = self.cursor.fetchone()
        japanese_name = name_res['lemma'] if name_res else None

        final_node_name = preferred_name or japanese_name or english_name or synset_id
        
        node = MeaningID(
            meaning_id=synset_id, 
            canonical_name={"ja": final_node_name}, 
            description={"ja": english_name}
        )
        self.db_manager.create_meaning_node(node)

    def _import_relationships(self):
        if not self.synsets_to_import:
            return
        
        # GPTのコードと私の修正案を統合した最終ロジック
        initial_ids = tuple(self.synsets_to_import.keys())
        if not initial_ids:
            return

        placeholders = ','.join('?' for _ in initial_ids)
        query = f"""
            SELECT synset1, synset2, link FROM synlink
            WHERE (synset1 IN ({placeholders}) OR synset2 IN ({placeholders}))
            AND link IN ('hype', 'anto')
        """
        params = initial_ids + initial_ids
        self.cursor.execute(query, params)
        links = self.cursor.fetchall()
        
        imported_count = 0
        for link in tqdm(links, desc="関係性をインポート中"):
            source_id, target_id = link['synset1'], link['synset2']

            # 関係性の両端ノードがインポート対象に含まれているか確認し、
            # 含まれていなければ動的に追加する
            if source_id not in self.synsets_to_import:
                self.synsets_to_import[source_id] = None
                self._import_node(source_id, None)
            if target_id not in self.synsets_to_import:
                self.synsets_to_import[target_id] = None
                self._import_node(target_id, None)

            type_map = {'hype': 'Is_A', 'anto': 'Symmetric_To'}
            relationship_type = type_map.get(link['link'])

            if relationship_type:
                rel = Relationship(
                    source_meaning_id=source_id,
                    target_meaning_id=target_id,
                    relationship_type=relationship_type,
                    source_of_data="WordNet_Targeted_Import"
                )
                self.db_manager.create_relationship(rel)
                imported_count += 1
        print(f"--- {imported_count}件の関係性のインポート処理が完了しました ---")

if __name__ == '__main__':
    PROJECT_ROOT = os.getcwd()
    SQLITE_DB_PATH = os.path.join(PROJECT_ROOT, "data", "wnjpn.db")
    NEO4J_URI = "neo4j://localhost:7687"
    NEO4J_USER = "neo4j"
    NEO4J_PASSWORD = "11dr34SSAAa_$$aae"
    core_concepts = ["人工知能", "労働", "人間", "進化", "影響", "経済", "哲学", "善", "悪", "愛", "科学"]

    db_manager = GraphDBManager(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    if db_manager.driver:
        print("【重要】データベースをクリアします...")
        db_manager.execute_query("MATCH (n) DETACH DELETE n")
        
        importer = WordNetImporter(SQLITE_DB_PATH, db_manager)
        if importer.conn:
            importer.run_import(core_concepts)
            importer.close()
        
        db_manager.close()