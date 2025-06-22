######################################################################
# Aruism AI Project - Unit Tests for CaseFrame Importer
#
# バージョン: 1.2 (最終版)
# 作成日: 2025-06-22
######################################################################
import pytest
import xml.etree.ElementTree as ET
import gzip
from unittest.mock import MagicMock, patch, mock_open

from aruism_ai.bootstrapping.caseframe_importer import CaseFrameImporter
from aruism_ai.ontology.db_manager import GraphDBManager

class TestCaseFrameImporter:
    """CaseFrameImporterのユニットテストクラス"""

    # ▼▼▼ [修正点] 不要になった test_parse_single_entry を削除 ▼▼▼

    def test_run_import_calls_db_manager_correctly(self):
        """
        [正常系/統合] run_importがファイルを解析し、
        db_managerのメソッドを正しく呼び出すかテストする。
        """
        xml_content_str = """<?xml version="1.0" encoding="UTF-8"?>
        <caseframedata>
            <entry headword="コーチ/こーち">
                <caseframe id="コーチ/こーち:名1">
                    <argument case="所属格">
                        <component frequency="1108">チーム/ちーむ</component>
                    </argument>
                </caseframe>
            </entry>
        </caseframedata>
        """
        
        mock_db_manager = MagicMock(spec=GraphDBManager)
        
        with patch("gzip.open", mock_open(read_data=xml_content_str.encode('utf-8'))) as mock_gzip_file:
            importer = CaseFrameImporter(mock_db_manager)
            importer.run_import("dummy/path/to/file.xml.gz")

        assert mock_db_manager.create_meaning_node.call_count == 2
        assert mock_db_manager.create_relationship.call_count == 1
        
        args, kwargs = mock_db_manager.create_relationship.call_args
        created_rel = args[0]
        
        # ▼▼▼ [修正点] アサーションを、パーサーの正しい挙動に合わせる ▼▼▼
        assert created_rel.source_concept_id == "コーチ"
        assert created_rel.target_concept_id == "チーム" # 「/ちーむ」が除去された正しい名前
        assert created_rel.relationship_type == "所属格"
        assert created_rel.strength == 1108