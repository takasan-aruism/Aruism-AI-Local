######################################################################
# Aruism AI Project - WordNet Importer
#
# バージョン: 4.0 (大規模データ対応・メモリ効率化版)
# 作成日: 2025-06-25
######################################################################
import sqlite3
import os
from tqdm import tqdm
import logging
from typing import List, Dict, Any, Generator
import gc  # ガベージコレクション用

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

class WordNetStreamingImporter:
    def __init__(self, sqlite_path: str, db_manager: GraphDBManager):
        self.db_manager = db_manager
        self.batch_size = 100  # 一度に処理する概念数
        self.write_threshold = 500  # この数に達したら書き込む
        
        try:
            # 読み取り専用で接続
            self.conn = sqlite3.connect(f'file:{sqlite_path}?mode=ro', uri=True)
            self.conn.row_factory = sqlite3.Row
            # カーソルを複数用意（並行処理用）
            self.cursor = self.conn.cursor()
            self.sub_cursor = self.conn.cursor()  # サブクエリ用
            logging.info("日本語WordNetデータベースへの接続に成功しました。")
        except sqlite3.Error as e:
            logging.error(f"日本語WordNetデータベースへの接続に失敗しました: {e}")
            self.conn = None
    
    def close(self):
        if self.conn:
            self.conn.close()

    def get_genesis_concepts_stream(self) -> Generator[Dict[str, Any], None, None]:
        """Genesis概念をストリーミングで取得"""
        offset = 0
        while True:
            query = """
            MATCH (n:Concept)
            WHERE 'AruismBaseDBTable_Genesis' IN n.source_of_data
            RETURN n.concept_id as concept_id, n.canonical_name_ja as name
            SKIP $skip LIMIT $limit
            """
            
            result = self.db_manager.execute_query(
                query, 
                {"skip": offset, "limit": self.batch_size}
            )
            
            if not result:
                break
                
            for row in result:
                yield row
                
            if len(result) < self.batch_size:
                break
                
            offset += self.batch_size

    def process_batch(self, concepts_batch: List[Dict[str, Any]]) -> tuple:
        """バッチ単位で概念を処理"""
        updates_batch = []
        new_parents_batch = []
        relationships_batch = []
        
        for concept in concepts_batch:
            concept_id = concept['concept_id']
            concept_name = concept['name']

            # synset IDを取得
            query_synset = """
            SELECT s.synset 
            FROM sense s 
            JOIN word w ON s.wordid = w.wordid 
            WHERE w.lemma = ? AND s.lang = 'jpn' 
            LIMIT 1
            """
            self.sub_cursor.execute(query_synset, (concept_name,))
            res = self.sub_cursor.fetchone()
            
            if not res:
                continue
                
            synset_id = res['synset']

            # 英語の定義を取得
            query_def = """
            SELECT def 
            FROM synset_def 
            WHERE synset = ? AND lang = 'eng' 
            LIMIT 1
            """
            self.sub_cursor.execute(query_def, (synset_id,))
            def_res = self.sub_cursor.fetchone()
            english_def = def_res['def'] if def_res else ""

            # プロパティ更新情報
            properties_to_update = {
                "wordnet_synset_id": synset_id,
                "description_en": english_def,
            }
            updates_batch.append({
                "concept_id": concept_id, 
                "properties": properties_to_update
            })
            
            # 上位概念（hypernym）を取得（制限付き）
            parent_query = """
            SELECT synset2 
            FROM synlink 
            WHERE synset1 = ? AND link = 'hype'
            LIMIT 5  -- 上位概念は最大5個まで
            """
            self.sub_cursor.execute(parent_query, (synset_id,))
            
            for parent_res in self.sub_cursor.fetchall():
                parent_synset_id = parent_res['synset2']
                
                # 親ノードの情報を取得
                parent_info_query = """
                SELECT s.name, sd.def 
                FROM synset s 
                LEFT JOIN synset_def sd ON s.synset = sd.synset AND sd.lang = 'eng' 
                WHERE s.synset = ?
                """
                self.sub_cursor.execute(parent_info_query, (parent_synset_id,))
                parent_info = self.sub_cursor.fetchone()
                
                query_jpn_name = """
                SELECT lemma 
                FROM word w 
                JOIN sense s ON w.wordid = s.wordid 
                WHERE s.synset = ? AND s.lang = 'jpn' 
                LIMIT 1
                """
                self.sub_cursor.execute(query_jpn_name, (parent_synset_id,))
                jpn_name_res = self.sub_cursor.fetchone()
                
                japanese_name = jpn_name_res['lemma'] if jpn_name_res else (
                    parent_info['name'].split(';')[0] if parent_info else parent_synset_id
                )

                new_parents_batch.append({
                    "concept_id": parent_synset_id,
                    "canonical_name_ja": japanese_name,
                    "description_en": parent_info['def'] if parent_info and parent_info['def'] else "",
                    "source": "wordnet_hypernym_import"
                })

                relationships_batch.append({
                    "source_id": concept_id,
                    "target_id": parent_synset_id,
                    "type": "Is_A"
                })
        
        return updates_batch, new_parents_batch, relationships_batch

    def write_batch_to_neo4j(self, updates, parents, relationships):
        """バッチデータをNeo4jに書き込む"""
        if updates:
            self.db_manager.batch_update_node_properties(updates)
            logging.info(f"{len(updates)}件のノードプロパティを更新")

        if parents:
            # 重複を除外
            unique_parents = list({p['concept_id']: p for p in parents}.values())
            self.db_manager.batch_create_concept_nodes(unique_parents)
            logging.info(f"{len(unique_parents)}件の親ノードを作成")

        if relationships:
            self.db_manager.batch_create_relationships(relationships)
            logging.info(f"{len(relationships)}件の関係性を作成")

    def run_streaming_enrichment(self):
        """ストリーミング処理でエンリッチを実行"""
        if not self.conn:
            logging.error("DB接続がないため、処理を中断します。")
            return

        # カウンター初期化
        total_concepts = 0
        processed_concepts = 0
        
        # まず総数を取得（進捗表示用）
        count_result = self.db_manager.execute_query("""
            MATCH (n:Concept)
            WHERE 'AruismBaseDBTable_Genesis' IN n.source_of_data
            RETURN count(n) as count
        """)
        
        if count_result:
            total_concepts = count_result[0]['count']
            logging.info(f"処理対象: {total_concepts}件の概念")

        # バッファを初期化
        all_updates = []
        all_parents = []
        all_relationships = []
        
        # プログレスバーを表示
        with tqdm(total=total_concepts, desc="WordNet情報処理中") as pbar:
            concepts_batch = []
            
            # ストリーミングで概念を取得
            for concept in self.get_genesis_concepts_stream():
                concepts_batch.append(concept)
                
                # バッチサイズに達したら処理
                if len(concepts_batch) >= self.batch_size:
                    updates, parents, relationships = self.process_batch(concepts_batch)
                    
                    # バッファに追加
                    all_updates.extend(updates)
                    all_parents.extend(parents)
                    all_relationships.extend(relationships)
                    
                    # 書き込み閾値に達したらDBに書き込み
                    if len(all_updates) >= self.write_threshold:
                        self.write_batch_to_neo4j(all_updates, all_parents, all_relationships)
                        
                        # バッファをクリア
                        all_updates = []
                        all_parents = []
                        all_relationships = []
                        
                        # メモリを解放
                        gc.collect()
                    
                    # プログレスバーを更新
                    pbar.update(len(concepts_batch))
                    processed_concepts += len(concepts_batch)
                    
                    # バッチをクリア
                    concepts_batch = []
            
            # 残りの概念を処理
            if concepts_batch:
                updates, parents, relationships = self.process_batch(concepts_batch)
                all_updates.extend(updates)
                all_parents.extend(parents)
                all_relationships.extend(relationships)
                pbar.update(len(concepts_batch))
            
            # 残りのデータを書き込み
            if all_updates or all_parents or all_relationships:
                self.write_batch_to_neo4j(all_updates, all_parents, all_relationships)
        
        logging.info(f"全ての処理が完了しました。処理済み: {processed_concepts}件")

# GraphDBManagerに追加するメソッド
def add_efficient_methods_to_db_manager(db_manager_class):
    """既存のGraphDBManagerクラスに効率的なメソッドを追加"""
    
    def batch_update_node_properties(self, updates_batch):
        """ノードプロパティを効率的に一括更新"""
        query = """
        UNWIND $updates as update
        MATCH (n:Concept {concept_id: update.concept_id})
        SET n += update.properties
        """
        self.execute_query(query, {"updates": updates_batch})
    
    def batch_create_concept_nodes(self, nodes_batch):
        """概念ノードを効率的に一括作成（MERGE使用）"""
        query = """
        UNWIND $nodes as node
        MERGE (n:Concept {concept_id: node.concept_id})
        ON CREATE SET 
            n.canonical_name_ja = node.canonical_name_ja,
            n.description_en = node.description_en,
            n.source_of_data = [node.source]
        ON MATCH SET
            n.source_of_data = 
                CASE 
                    WHEN node.source IN n.source_of_data THEN n.source_of_data
                    ELSE n.source_of_data + node.source
                END
        """
        self.execute_query(query, {"nodes": nodes_batch})
    
    def batch_create_relationships(self, relationships_batch):
        """関係性を効率的に一括作成"""
        query = """
        UNWIND $rels as rel
        MATCH (source:Concept {concept_id: rel.source_id})
        MATCH (target:Concept {concept_id: rel.target_id})
        MERGE (source)-[r:Is_A]->(target)
        """
        self.execute_query(query, {"rels": relationships_batch})
    
    # メソッドを動的に追加
    db_manager_class.batch_update_node_properties = batch_update_node_properties
    db_manager_class.batch_create_concept_nodes = batch_create_concept_nodes
    db_manager_class.batch_create_relationships = batch_create_relationships

if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO, 
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    db_manager = None
    importer = None
    
    try:
        PROJECT_ROOT = find_project_root()
        SQLITE_DB_PATH = os.path.join(PROJECT_ROOT, "data", "wnjpn.db")
        NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
        NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
        NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD")

        if not NEO4J_PASSWORD:
            raise ValueError("環境変数 NEO4J_PASSWORD が設定されていません。")

        # DBManagerのインスタンス化
        db_manager = GraphDBManager(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
        
        # 効率的なメソッドを追加
        add_efficient_methods_to_db_manager(GraphDBManager)
        
        # インポーターの作成と実行
        importer = WordNetStreamingImporter(SQLITE_DB_PATH, db_manager)
        importer.run_streaming_enrichment()

    except Exception as e:
        logging.error(f"メイン処理でエラーが発生しました: {e}", exc_info=True)
    finally:
        if importer:
            importer.close()
        if db_manager:
            db_manager.close()