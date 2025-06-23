######################################################################
# Aruism AI Project - Unit Tests for Genesis Importer
#
# バージョン: 1.0
# 作成日: 2025-06-23
######################################################################
import pytest
from unittest.mock import MagicMock, patch, mock_open

from aruism_ai.bootstrapping.genesis_importer import GenesisImporter
from aruism_ai.ontology.db_manager import GraphDBManager

class TestGenesisImporter:
    """GenesisImporterのユニットテストクラス"""

    def test_import_from_csv(self):
        """[正常系] CSVから概念と対称関係を正しくインポートできるかテスト"""
        # 1. 偽のCSVファイル内容を準備
        csv_content = """concept_id;symmetric_concept_id;symbol;axis_kanji;category
M0001;M0003;❤️;愛;emotion
M0003;M0001;💔;憎;emotion
M0004;;😊;幸;emotion
"""
        
        # 2. openとDBManagerをモック化
        mock_db_manager = MagicMock(spec=GraphDBManager)
        
        with patch("builtins.open", mock_open(read_data=csv_content)) as mock_file:
            importer = GenesisImporter(mock_db_manager)
            importer.run_import("dummy/genesis.csv")

        # 3. 検証：DBManagerのメソッドが期待通りに呼ばれたか
        # 3つの概念ノードが作成されるはず
        assert mock_db_manager.create_concept_node.call_count == 3
        
        # M0001 <-> M0003 の2つの対称関係が作成されるはず
        assert mock_db_manager.create_relationship.call_count == 2

        # 呼び出し内容をさらに詳細にチェック（例として最初のノード作成）
        first_call_args, _ = mock_db_manager.create_concept_node.call_args_list[0]
        created_concept = first_call_args[0]
        assert created_concept.concept_id == "M0001"
        assert created_concept.symbol == "❤️"
        assert created_concept.category == "emotion"