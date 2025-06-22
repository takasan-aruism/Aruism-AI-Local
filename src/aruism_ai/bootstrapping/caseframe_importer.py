######################################################################
# Aruism AI Project - CaseFrame Importer
#
# バージョン: 2.0 (最終実行可能版)
# 作成日: 2025-06-22
######################################################################
import xml.etree.ElementTree as ET
import gzip
from tqdm import tqdm
import logging
import os

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

class CaseFrameImporter:
    def __init__(self, db_manager: GraphDBManager):
        self.db_manager = db_manager
        self.imported_concepts = set()

    def _parse_headword(self, headword_text: str) -> str:
        """ "コーチ/こーち" のような表記から "コーチ" の部分だけを抽出する """
        if not headword_text: return ""
        return headword_text.split('/')[0]

    def _create_concept_if_not_exists(self, concept_name: str, source: str):
        """指定された概念がまだインポートされていなければ、新しいConceptノードを作成する"""
        parsed_name = self._parse_headword(concept_name)
        if parsed_name and parsed_name not in self.imported_concepts:
            node = Concept(
                concept_id=parsed_name,
                canonical_name_ja=parsed_name,
                source=[source]
            )
            self.db_manager.create_meaning_node(node)
            self.imported_concepts.add(parsed_name)
    def _normalize_relationship_type(self, case_name: str) -> str:
        """
        "必須格(属性)格" のような文字列から、Cypherで無効な文字を除去する。
        """
        # ()?+ などの記号を単純に除去する
        return re.sub(r'[()?+]', '', case_name)
        
    def run_import(self, filepath: str):
        """指定されたgzipped XMLファイルを逐次解析し、内容をDBにインポートする。"""
        if not self.db_manager:
            logging.error("DBManagerが提供されていません。インポートを中止します。")
            return

        print(f"\n--- 格フレームファイル({filepath})のインポートを開始します ---")
        
        try:
            with gzip.open(filepath, 'rb') as f:
                context = ET.iterparse(f, events=('end',))
                for event, elem in tqdm(context, desc="格フレームを解析・インポート中"):
                    if elem.tag == 'entry':
                        headword_raw = elem.get('headword')
                        if not headword_raw: continue
                        
                        headword = self._parse_headword(headword_raw)
                        self._create_concept_if_not_exists(headword, "caseframe_headword")

                        for caseframe_node in elem.findall('caseframe'):
                            for argument_node in caseframe_node.findall('argument'):
                                case_type = argument_node.get('case')
                                if not case_type: continue
                                
                                for component_node in argument_node.findall('component'):
                                    component_raw = component_node.text
                                    frequency = component_node.get('frequency')
                                    if not component_raw or not frequency: continue

                                    self._create_concept_if_not_exists(component_raw, "caseframe_component")
                                    
                                    rel = Relationship(
                                        source_concept_id=headword,
                                        target_concept_id=self._parse_headword(component_raw),
                                        relationship_type=case_type,
                                        strength=float(frequency),
                                        source_of_data="KyotoUniv_NCF"
                                    )
                                    self.db_manager.create_relationship(rel)
                        elem.clear()

            print("\n--- 格フレームのインポートが完了しました ---")

        except FileNotFoundError:
            logging.error(f"ファイルが見つかりません: {filepath}")
        except Exception as e:
            logging.error(f"予期せぬエラーが発生しました: {e}", exc_info=True)

# ▼▼▼ このスクリプトを直接実行するためのメインブロック ▼▼▼
if __name__ == '__main__':
    db_manager = None
    try:
        PROJECT_ROOT = find_project_root()
        # README.txtに記載のファイル名を指定
        CASEFRAME_PATH = os.path.join(PROJECT_ROOT, "data", "kyoto-univ-web-ncf-0.5.xml.gz")
        
        # 念のため、ユーザーが解凍している場合も考慮
        if not os.path.exists(CASEFRAME_PATH):
            unzipped_path = CASEFRAME_PATH.replace(".gz", "")
            if os.path.exists(unzipped_path):
                CASEFRAME_PATH = unzipped_path
            else:
                raise FileNotFoundError(f"格フレームファイルが見つかりません: {CASEFRAME_PATH}")

        NEO4J_URI = "bolt://localhost:7687"
        NEO4J_USER = "neo4j"
        NEO4J_PASSWORD = "11dr34SSAAa_$$aae" # ご自身のパスワード

        db_manager = GraphDBManager(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
        if db_manager.driver:
            importer = CaseFrameImporter(db_manager)
            importer.run_import(CASEFRAME_PATH)

    except Exception as e:
        print(f"メイン処理でエラーが発生しました: {e}")
    finally:
        if db_manager:
            db_manager.close()
            print("データベース接続を閉じました。")