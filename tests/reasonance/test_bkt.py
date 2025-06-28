import pytest
from unittest.mock import MagicMock, patch, mock_open
from aruism_ai.bootstrapping.caseframe_importer import CaseFrameImporter

import pytest
from unittest.mock import MagicMock, patch, mock_open
from aruism_ai.bootstrapping.caseframe_importer import CaseFrameImporter
from aruism_ai.ontology.models import Relationship

class TestCaseFrameImporter:
    def test_run_import_calls_db_manager_correctly(self):
        mock_db_manager = MagicMock()
        importer = CaseFrameImporter(mock_db_manager)
        
        # 1. Unicode文字列として定義
        xml_string = """<?xml version="1.0" encoding="UTF-8"?>
<entrylist>
    <entry headword="学ぶ/まなぶ">
        <caseframe>
            <argument case="ガ格"><component frequency="1108">人/ひと</component></argument>
            <argument case="ヲ格"><component frequency="850">こと/こと</component></argument>
        </caseframe>
    </entry>
</entrylist>
"""
        # 2. バイト文字列にエンコード
        xml_content_bytes = xml_string.encode('utf-8')
        
        # 3. エンコードしたバイトデータをモックに渡す
        with patch("gzip.open", mock_open(read_data=xml_content_bytes)):
            importer.run_import("dummy/path/to/file.xml.gz")

        # 検証
        assert mock_db_manager.create_concept_node.call_count == 3
        assert mock_db_manager.create_relationship.call_count == 2
        
        last_rel_call = mock_db_manager.create_relationship.call_args_list[1]
        created_rel = last_rel_call.args[0]
        
        assert isinstance(created_rel, Relationship)
        assert created_rel.source_concept_id == "学ぶ"
        assert created_rel.target_concept_id == "こと"
        assert created_rel.relationship_type == "ヲ格"
        # strengthは現在モデルにないため、テストしない
        # assert created_rel.strength == 850.0