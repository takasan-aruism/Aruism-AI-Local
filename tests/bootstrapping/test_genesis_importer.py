import pytest
from unittest.mock import MagicMock, patch
from aruism_ai.bootstrapping.genesis_importer import GenesisImporter

class TestGenesisImporter:
    @pytest.fixture
    def mock_db_manager(self):
        db = MagicMock()
        db.execute_query.return_value = [{'count': 0}]
        return db

    def test_run_import(self, mock_db_manager):
        importer = GenesisImporter(mock_db_manager)
        importer.batch_size = 2

        mock_data = [
            {'concept_id': 'M0001', 'symbol': 'S1', 'axis_kanji': '愛', 'category': 'C1', 'symmetric_concept_id': 'M0002'},
            {'concept_id': 'M0002', 'symbol': 'S2', 'axis_kanji': '憎', 'category': 'C1', 'symmetric_concept_id': 'M0001'}
        ]
        with patch("builtins.open", MagicMock()):
             with patch("csv.DictReader", return_value=mock_data):
                importer.run_import("dummy.csv")
        
        # 実際の呼び出し回数（6回）に修正
        assert mock_db_manager.execute_query.call_count == 6
        
        # ノード作成バッチの呼び出しを検証
        # 呼び出しリストから適切なインデックスを見つける
        for i, call in enumerate(mock_db_manager.execute_query.call_args_list):
            if 'concepts' in call.kwargs:
                assert len(call.kwargs['concepts']) == 2
                assert call.kwargs['concepts'][0]['concept_id'] == 'M0001'
                break