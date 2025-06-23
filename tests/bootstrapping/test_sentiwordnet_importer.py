######################################################################
# Aruism AI Project - Unit Tests for SentiWordNet Importer (Refactored)
#
# バージョン: 2.0
# 作成日: 2025-06-23
######################################################################
import pytest
from unittest.mock import MagicMock, patch, mock_open

from aruism_ai.bootstrapping.sentiwordnet_importer import SentiWordNetImporter
from aruism_ai.ontology.db_manager import GraphDBManager

class TestSentiWordNetImporter:
    """SentiWordNetImporter (リファクタリング版) のユニットテストクラス"""

    def test_updates_sentiment_scores(self):
        """
        [正常系] SentiWordNetのデータを解析し、既存ノードの感情スコアを更新できるかテスト
        """
        # 1. DBManagerをモック化
        mock_db_manager = MagicMock(spec=GraphDBManager)
        importer = SentiWordNetImporter(mock_db_manager)
        
        # 2. 偽のSentiWordNetファイル内容を準備
        senti_content = "# POS\tID\tPosScore\tNegScore\tSynsetTerms\tGloss\nn\t07543288\t0.875\t0.125\tlove#1\t a strong positive emotion\n"
        
        # 3. openをモック化してインポート処理を実行
        with patch("builtins.open", mock_open(read_data=senti_content)):
            importer.run_update("dummy/path/to/sentiwordnet.txt")

        # 4. 検証
        # update_node_properties_by_wordnet_idが1回呼ばれるはず
        mock_db_manager.update_node_properties_by_wordnet_id.assert_called_once()

        # 呼び出し内容を詳細に検証
        update_args, _ = mock_db_manager.update_node_properties_by_wordnet_id.call_args
        updated_id, updated_props = update_args[0], update_args[1]

        assert updated_id == "07543288-n"
        assert updated_props["sentiment_positive"] == 0.875
        assert updated_props["sentiment_negative"] == 0.125