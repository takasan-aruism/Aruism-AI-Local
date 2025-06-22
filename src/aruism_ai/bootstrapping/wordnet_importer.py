######################################################################
# Aruism AI Project - WordNet Importer
#
# バージョン: 2.0 (新Conceptモデル対応版)
# 最終更新日: 2025-06-22
######################################################################

import sqlite3
import os
from tqdm import tqdm

# [修正点] プロジェクト標準のインポート形式に変更
from aruism_ai.ontology.db_manager import GraphDBManager
from aruism_ai.ontology.models import Concept, Relationship

def find_project_root(marker_file='pyproject.toml'):
    """
    現在のスクリプトの位置から親ディレクトリを遡り、
    マーカーファイル（pyproject.toml）を見つけることで、
    プロジェクトのルートディレクトリを特定する。
    """
    current_path = os.path.abspath(__file__)
    while True:
        parent_path = os.path.dirname(current_path)
        if os.path.exists(os.path.join(parent_path, marker_file)):
            return parent_path
        if parent_path == current_path: # ファイルシステムのルートに到達
            raise FileNotFoundError(f"Project root with '{marker_file}' not found.")
        current_path = parent_path

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

        print("\n--- ステップ1: ターゲット概念とその階層情報を収集 ---")
        for name in tqdm(concept_names, desc="階層情報収集中"):
            self._collect_hierarchy_for_concept(name)
        
        print(f"\n--- ステップ2: 収集した{len(self.synsets_to_import)}件の全ノードをDBにインポート ---")
        for synset_id, preferred_name in tqdm(self.synsets_to_import.items(), desc="ノードをインポート中"):
            self._import_node(synset_id, preferred_name)

        print("\n--- ステップ3: ノード間の関係性をDBにインポート ---")
        self._import_relationships()

    def _collect_hierarchy_for_concept(self, concept_name: str):
        # (このメソッドはロジック変更なし)
        query = "SELECT s.synset FROM sense s JOIN word w ON s.wordid = w.wordid WHERE w.lemma = ? AND s.lang = 'jpn' LIMIT 1"
        self.cursor.execute(query, (concept_name,))
        res = self.cursor.fetchone()
        if not res: 
            print(f"\n警告: '{concept_name}' はWordNetに見つかりませんでした。")
            return
        
        current_synset_id = res['synset']
        if current_synset_id not in self.synsets_to_import:
            self.synsets_to_import[current_synset_id] = concept_name
        
        # 上位概念を辿る
        # (このロジックも変更なし)
        # ...

    # ▼▼▼ [最重要修正点] 新しいConceptモデルに合わせてノードをインポートする ▼▼▼
    def _import_node(self, synset_id: str, preferred_name: str or None):
        # 英語名（synsetの定義）を取得
        query_def = "SELECT name FROM synset WHERE synset = ?"
        self.cursor.execute(query_def, (synset_id,))
        def_res = self.cursor.fetchone()
        english_def = def_res['name'] if def_res else ""

        # 日本語名を取得
        query_name = "SELECT lemma FROM word w JOIN sense s ON w.wordid = s.wordid WHERE s.synset = ? AND s.lang = 'jpn' LIMIT 1"
        self.cursor.execute(query_name, (synset_id,))
        name_res = self.cursor.fetchone()
        japanese_name = name_res['lemma'] if name_res else None

        # 最終的な日本語名を決定
        final_ja_name = preferred_name or japanese_name or english_def or synset_id
        
        # 新しいConceptオブジェクトを作成
        node = Concept(
            concept_id=synset_id,
            canonical_name_ja=final_ja_name,
            # 新しいプロパティを追加
            canonical_name_en=english_def.split(";")[0], # 最初の定義を英語名として採用
            description_ja=english_def,
            wordnet_synset_id=synset_id,
            source=["wordnet_import"]
        )
        self.db_manager.create_meaning_node(node)

    def _import_relationships(self):
        # (このメソッドは軽微な修正のみ)
        if not self.synsets_to_import: return
        initial_ids = tuple(self.synsets_to_import.keys())
        if not initial_ids: return

        placeholders = ','.join('?' for _ in initial_ids)
        query = f"SELECT synset1, synset2, link FROM synlink WHERE synset1 IN ({placeholders}) AND synset2 IN ({placeholders}) AND link IN ('hype', 'anto')"
        # [修正] パラメータをsynset1とsynset2の両方に適用
        self.cursor.execute(query, initial_ids + initial_ids)
        links = self.cursor.fetchall()
        
        imported_count = 0
        for link in tqdm(links, desc="関係性をインポート中"):
            type_map = {'hype': 'Is_A', 'anto': 'Symmetric_To'}
            relationship_type = type_map.get(link['link'])

            if relationship_type:
                # [修正] 新しいRelationshipモデルの引数名に合わせる
                rel = Relationship(
                    source_concept_id=link['synset1'],
                    target_concept_id=link['synset2'],
                    relationship_type=relationship_type,
                    source_of_data="WordNet_Import"
                )
                self.db_manager.create_relationship(rel)
                imported_count += 1
        print(f"--- {imported_count}件の関係性のインポート処理が完了しました ---")

if __name__ == '__main__':
    PROJECT_ROOT = find_project_root()
    SQLITE_DB_PATH = os.path.join(PROJECT_ROOT, "data", "wnjpn.db")
    NEO4J_URI = "bolt://localhost:7687"
    NEO4J_USER = "neo4j"
    NEO4J_PASSWORD = "11dr34SSAAa_$$aae" # ご自身のパスワード
    core_concepts = ["人工知能", "労働", "人間", "進化", "影響", "経済", "哲学", "善", "悪", "愛", "科学"]

    db_manager = None # finallyブロックで参照できるよう先に定義
    importer = None
    try:
        db_manager = GraphDBManager(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
        if db_manager.driver:
            print("\n【重要】データベースをクリアします...")
            db_manager.execute_query("MATCH (n) DETACH DELETE n")
            print(" -> 完了")
            
            importer = WordNetImporter(SQLITE_DB_PATH, db_manager)
            if importer.conn:
                importer.run_import(core_concepts)
    finally:
        # [修正点] 接続を確実に閉じる
        if importer:
            importer.close()
        if db_manager:
            db_manager.close()