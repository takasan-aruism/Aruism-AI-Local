######################################################################
# Aruism AI Project - Knowledge Linker
#
# このファイルは、私たちのAruism知識ベースと、
# Wikidataのような外部の知識ソースとを連携させる機能を定義します。
#
# 参照ドキュメント: Aruism_AI_Project_11_Cognitive_Architecture_Design.txt
# バージョン: 0.2
# 作成日: 2025-06-18
######################################################################

import os
import sys
from SPARQLWrapper import SPARQLWrapper, JSON
from tqdm import tqdm

# プロジェクトのルートディレクトリをシステムパスに追加
sys.path.append(os.getcwd())

from src.ontology.db_manager import GraphDBManager

class KnowledgeLinker:
    """
    外部の知識ベース（Wikidata等）と連携するためのクラス。
    """
    def __init__(self, db_manager: GraphDBManager):
        self.db_manager = db_manager
        self.sparql_endpoint = "https://query.wikidata.org/sparql"
        self.sparql = SPARQLWrapper(self.sparql_endpoint)
        print("KnowledgeLinkerが初期化されました。")

    def _find_wikidata_qid(self, concept_name_ja: str):
        """
        指定された日本語の概念名から、WikidataのQIDを取得します。
        """
        if not concept_name_ja:
            return None
            
        query = f"""
        SELECT ?item WHERE {{
          ?item rdfs:label "{concept_name_ja}"@ja.
        }}
        LIMIT 1
        """
        self.sparql.setQuery(query)
        self.sparql.setReturnFormat(JSON)
        
        try:
            results = self.sparql.query().convert()
            bindings = results.get("results", {}).get("bindings", [])
            if bindings:
                item_uri = bindings[0].get("item", {}).get("value", "")
                # URIからQIDを抽出 (例: http://www.wikidata.org/entity/Q3947 -> Q3947)
                qid = item_uri.split('/')[-1]
                return qid
            return None
        except Exception:
            return None

    def enrich_nodes_with_wikidata_ids(self, limit=100):
        """
        【このステップで実装】
        データベース内のノードに対し、対応するWikidata QIDを検索して追記します。
        """
        print(f"\n--- ノードのエンリッチメント（Wikidata ID追記）を開始します (上限: {limit}件) ---")
        
        # Wikidata IDがまだないノードを取得
        target_nodes = self.db_manager.fetch_nodes_without_property(
            property_name="external_identifiers_wikidata_qid",
            limit=limit
        )

        if not target_nodes:
            print("エンリッチメント対象のノードが見つかりませんでした。")
            return
            
        updated_count = 0
        for node in tqdm(target_nodes, desc="ノードをエンリッチ中"):
            node_id = node.get("meaning_id")
            node_name = node.get("name")
            
            # WikidataでQIDを検索
            qid = self._find_wikidata_qid(node_name)
            
            if qid:
                # QIDが見つかった場合、ノードのプロパティを更新
                properties_to_update = {
                    "external_identifiers_wikidata_qid": qid
                }
                self.db_manager.update_node_properties(node_id, properties_to_update)
                updated_count += 1
                # print(f"  - {node_name} ({node_id}) -> {qid}")

        print(f"--- {updated_count}件のノードにWikidata IDを追記しました ---")


# このファイルが直接実行された場合にのみ以下のコードが動きます
if __name__ == '__main__':
    # --- 設定 ---
    NEO4J_URI = "neo4j://localhost:7687"
    NEO4J_USER = "neo4j"
    NEO4J_PASSWORD = "11dr34SSAAa_$$aae"  # ご自身のパスワードに変更してください

    # --- 実行 ---
    db_manager = GraphDBManager(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)

    if db_manager.driver:
        linker = KnowledgeLinker(db_manager)
        
        # Wikidata IDを持たないノードを100件エンリッチする
        linker.enrich_nodes_with_wikidata_ids(limit=100)
        
        db_manager.close()