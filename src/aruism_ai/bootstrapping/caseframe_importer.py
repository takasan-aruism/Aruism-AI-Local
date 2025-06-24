######################################################################
# Aruism AI Project - CaseFrame Importer
#
# バージョン: 1.0 (メインエンジン実装版)
# 作成日: 2025-06-23
######################################################################
import xml.etree.ElementTree as ET
import gzip
from tqdm import tqdm
import logging
import os
import re

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
        self.processed_concepts = set()

    def _parse_name(self, raw_text: str) -> str:
        """ "コーチ/こーち" のような表記から主要名を抽出 """
        if not raw_text: return ""
        return raw_text.split('/')[0]

    def _create_concept_if_not_exists(self, concept_name: str):
        """指定された概念がまだインポートされていなければ、新しいConceptノードを作成する"""
        parsed_name = self._parse_name(concept_name)
        if parsed_name and parsed_name not in self.processed_concepts:
            node = Concept(
                concept_id=parsed_name, # 簡略化のため、名前をそのままIDとして使用
                canonical_name_ja=parsed_name,
                source=["caseframe_import"]
            )
            self.db_manager.create_concept_node(node)
            self.processed_concepts.add(parsed_name)
    
    def run_import(self, filepath: str):
        """指定されたgzipped XMLファイルを逐次解析し、内容をDBにインポートする。"""
        if not self.db_manager:
            logging.error("DBManagerが提供されていません。")
            return

        print(f"\n--- 格フレームファイル({filepath})のインポートを開始します ---")
        
        try:
            # 1. gzipファイルを逐次的に読み込む
            with gzip.open(filepath, 'rb') as f:
                context = ET.iterparse(f, events=('end',))
                for _, elem in tqdm(context, desc="格フレームを解析・インポート中"):
                    if elem.tag == 'entry':
                        headword_raw = elem.get('headword')
                        if not headword_raw: continue
                        
                        headword = self._parse_name(headword_raw)
                        self._create_concept_if_not_exists(headword)

                        for caseframe_node in elem.findall('caseframe'):
                            for argument_node in caseframe_node.findall('argument'):
                                case_type = argument_node.get('case', '')
                                
                                for component_node in argument_node.findall('component'):
                                    component_raw = component_node.text
                                    frequency = component_node.get('frequency', '0')
                                    
                                    self._create_concept_if_not_exists(component_raw)
                                    
                                    rel = Relationship(
                                        source_concept_id=headword,
                                        target_concept_id=self._parse_name(component_raw),
                                        relationship_type=case_type,
                                        strength=float(frequency),
                                        source_of_data="KyotoUniv_NCF"
                                    )
                                    self.db_manager.create_relationship(rel)
                        # メモリ解放
                        elem.clear()

            print("\n--- 格フレームのインポートが完了しました ---")

        except FileNotFoundError:
            logging.error(f"ファイルが見つかりません: {filepath}")
        except Exception as e:
            logging.error(f"予期せぬエラーが発生しました: {e}", exc_info=True)

if __name__ == '__main__':
    db_manager = None
    try:
        PROJECT_ROOT = find_project_root()
        CASEFRAME_PATH = os.path.join(PROJECT_ROOT, "data", "kyoto-univ-web-ncf-0.5.xml.gz")
        
        if not os.path.exists(CASEFRAME_PATH):
            unzipped_path = CASEFRAME_PATH.replace(".gz", "")
            if os.path.exists(unzipped_path):
                CASEFRAME_PATH = unzipped_path
            else:
                raise FileNotFoundError(f"格フレームファイルが見つかりません: {CASEFRAME_PATH}")

        NEO4J_URI = "bolt://localhost:7687"
        NEO4J_USER = "neo4j"
        NEO4J_PASSWORD = "11dr34SSAAa_$$aae"

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