######################################################################
# Aruism AI Project - WordNet Importer
#
# バージョン: 2.1 (既存ノードへのエンリッチ機能 実装版)
# 作成日: 2025-06-23
######################################################################
import sqlite3
import os
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

class WordNetImporter:
    def __init__(self, sqlite_path, db_manager: GraphDBManager):
        self.db_manager = db_manager
        try:
            self.conn = sqlite3.connect(sqlite_path)
            self.conn.row_factory = sqlite3.Row
            self.cursor = self.conn.cursor()
        except sqlite3.Error as e:
            logging.error(f"日本語WordNetデータベースへの接続に失敗しました: {e}")
            self.conn = None
    
    def close(self):
        if self.conn:
            self.conn.close()

    def enrich_concept_by_name(self, concept_name: str, concept_id: str):
        """
        単一の概念について、WordNet情報を検索し、DBノードをエンリッチする
        """
        if not self.conn:
            return

        # 1. 日本語名からsynset IDを取得
        query_synset = "SELECT s.synset FROM sense s JOIN word w ON s.wordid = w.wordid WHERE w.lemma = ? AND s.lang = 'jpn' LIMIT 1"
        self.cursor.execute(query_synset, (concept_name,))
        res = self.cursor.fetchone()
        if not res:
            return
        
        synset_id = res['synset']

        # 2. synset IDから英語の定義を取得
        query_def = "SELECT name FROM synset WHERE synset = ?"
        self.cursor.execute(query_def, (synset_id,))
        def_res = self.cursor.fetchone()
        english_def = def_res['name'] if def_res else ""

        # 3. 既存ノードに追記するプロパティを準備
        properties_to_update = {
            "wordnet_synset_id": synset_id,
            "description_en": english_def,
            "description_ja": english_def
        }
        self.db_manager.update_node_properties(concept_id, properties_to_update)

        # 4. 上位概念（hypernym）との関係性を作成
        parent_query = "SELECT synset2 FROM synlink WHERE synset1 = ? AND link = 'hype' LIMIT 1"
        self.cursor.execute(parent_query, (synset_id,))
        parent_res = self.cursor.fetchone()
        if parent_res:
            parent_synset_id = parent_res['synset2']
            self._create_parent_node_if_not_exists(parent_synset_id)
            rel = Relationship(
                source_concept_id=concept_id,
                target_concept_id=parent_synset_id,
                relationship_type="Is_A",
                source_of_data="WordNet_Import"
            )
            self.db_manager.create_relationship(rel)

    def _create_parent_node_if_not_exists(self, synset_id: str):
        """
        親ノードが存在しない場合にのみ、新しいConceptノードとして作成するヘルパー関数
        """
        query_def = "SELECT name FROM synset WHERE synset = ?"
        self.cursor.execute(query_def, (synset_id,))
        def_res = self.cursor.fetchone()
        english_name = def_res['name'] if def_res else synset_id

        query_name = "SELECT lemma FROM word w JOIN sense s ON w.wordid = s.wordid WHERE s.synset = ? AND s.lang = 'jpn' LIMIT 1"
        self.cursor.execute(query_name, (synset_id,))
        name_res = self.cursor.fetchone()
        japanese_name = name_res['lemma'] if name_res else english_name.split(";")[0]

        node = Concept(
            concept_id=synset_id,
            canonical_name_ja=japanese_name,
            wordnet_synset_id=synset_id,
            source=["wordnet_hypernym_import"]
        )
        self.db_manager.create_concept_node(node)

if __name__ == '__main__':
    # このメインブロックは、実際のバッチ処理用に再設計します
    # 現状は、手動でいくつかの概念をエンリッチする例
    db_manager = None
    importer = None
    try:
        PROJECT_ROOT = find_project_root()
        SQLITE_DB_PATH = os.path.join(PROJECT_ROOT, "data", "wnjpn.db")
        NEO4J_URI = "bolt://localhost:7687"
        NEO4J_USER = "neo4j"
        NEO4J_PASSWORD = "11dr34SSAAa_$$aae"

        db_manager = GraphDBManager(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
        if db_manager.driver:
            importer = WordNetImporter(SQLITE_DB_PATH, db_manager)
            if importer.conn:
                # Genesis importerで登録した概念のリスト（一部）
                concepts_to_enrich = {"愛": "M0001", "憎": "M0003", "善": "M0233"}
                for name, cid in tqdm(concepts_to_enrich.items(), desc="概念をエンリッチ中"):
                    importer.enrich_concept_by_name(name, cid)
                print("エンリッチ処理が完了しました。")
    except Exception as e:
        print(f"メイン処理でエラーが発生しました: {e}")
    finally:
        if importer:
            importer.close()
        if db_manager:
            db_manager.close()