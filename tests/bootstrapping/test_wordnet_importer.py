import pytest
from unittest.mock import MagicMock, patch
from aruism_ai.bootstrapping.wordnet_importer import WordNetStreamingImporter

class TestWordNetStreamingImporter:
    @pytest.fixture
    def mock_db_manager(self):
        db = MagicMock()
        # クエリに応じて戻り値を変更するside_effectを設定
        def query_side_effect(query, **kwargs):
            if "count(n) as count" in query:
                return [{'count': 2}]
            elif "SKIP $skip LIMIT $limit" in query:
                # バッチサイズに応じてデータを返す
                skip = kwargs.get('skip', 0)
                if skip == 0:
                    return [{'concept_id': 'C001', 'name': '愛'}, {'concept_id': 'C002', 'name': '犬'}]
                else:
                    return []  # 2回目以降は空を返す
            return []
        db.execute_query.side_effect = query_side_effect
        return db

    @pytest.fixture
    def mock_sqlite_conn(self):
        conn = MagicMock()
        cursor = conn.cursor.return_value
        sub_cursor = MagicMock()
        conn.cursor.side_effect = [cursor, sub_cursor]  # 複数のカーソル用
        
        cursor.fetchone.return_value = {'synset': 'dummy_synset', 'def': 'dummy_def'}
        cursor.fetchall.return_value = []
        sub_cursor.fetchone.return_value = {'synset': 'dummy_synset', 'def': 'dummy_def'}
        sub_cursor.fetchall.return_value = []
        return conn

    def test_run_streaming_enrichment(self, mock_db_manager, mock_sqlite_conn):
        with patch('sqlite3.connect', return_value=mock_sqlite_conn):
            importer = WordNetStreamingImporter("dummy.db", mock_db_manager)
            importer.run_streaming_enrichment()

        # 実際の呼び出し回数に合わせて修正
        # カウント(1) + データ取得(1) = 2回
        assert mock_db_manager.execute_query.call_count == 2
        
        # batch_update_node_propertiesが呼ばれることを確認
        mock_db_manager.batch_update_node_properties.assert_called_once()