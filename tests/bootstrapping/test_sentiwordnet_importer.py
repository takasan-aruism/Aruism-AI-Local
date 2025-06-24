import pytest
from unittest.mock import MagicMock, patch, mock_open
from aruism_ai.bootstrapping.sentiwordnet_importer import SentiWordNetImporter

class TestSentiWordNetImporter:
    def test_updates_sentiment_scores(self):
        mock_db_manager = MagicMock()
        importer = SentiWordNetImporter(mock_db_manager)

        senti_data = "a\t00001740\t0.5\t0.25\tterm#1\tgloss\n"
        
        # mock_openを正しく設定
        m_open = mock_open(read_data=senti_data)
        with patch("builtins.open", m_open):
            importer.run_update("dummy/path")

        mock_db_manager.batch_update_node_properties_by_synset.assert_called_once()
        batch_data = mock_db_manager.batch_update_node_properties_by_synset.call_args.args[0]
        
        assert len(batch_data) == 1
        assert batch_data[0]['properties']['sentiment_positive'] == 0.5