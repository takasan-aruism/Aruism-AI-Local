######################################################################
# Aruism AI Project - Unit Tests for Graph Database Manager
#
# このファイルは、GraphDBManagerクラスのユニットテストを定義します。
# データベースへの実際の接続は行わず、モッキングを用いて
# データベースドライバとのやり取りが正しく行われるかを検証します。
#
# 参照ドキュメント: Aruism_AI_Project_06_Testing_and_Evaluation_Plan.txt
# バージョン: 1.0
# 作成日: 2025-06-21
######################################################################

import pytest
from unittest.mock import patch, MagicMock

# プロジェクトのルートからの絶対パスでモジュールをインポート
from aruism_ai.ontology.models import MeaningID, Relationship
from aruism_ai.ontology.db_manager import GraphDBManager

# --- テスト用の定数 ---
TEST_URI = "neo4j://testhost:7687"
TEST_USER = "testuser"
TEST_PASSWORD = "testpassword"


class TestGraphDBManager:
    """GraphDBManagerのユニットテストクラス"""

    def setup_method(self, method):
        """各テストメソッドの実行前に呼び出されるセットアップ"""
        # モックを使って、実際のDB接続を行わないようにする
        self.mock_driver_patch = patch('aruism_ai.ontology.db_manager.GraphDatabase.driver')
        self.mock_driver = self.mock_driver_patch.start()
        
        # db_managerのインスタンスを作成
        self.db_manager = GraphDBManager(TEST_URI, TEST_USER, TEST_PASSWORD)
        # db_managerが持つdriverインスタンスをモックに差し替える
        self.db_manager.driver = self.mock_driver

    def teardown_method(self, method):
        """各テストメソッドの実行後に呼び出されるクリーンアップ"""
        self.mock_driver_patch.stop()

    def test_successful_connection(self):
        """データベースへの接続が成功するケースのテスト"""
        self.mock_driver.assert_called_once_with(TEST_URI, auth=(TEST_USER, TEST_PASSWORD))
        assert self.db_manager.driver is not None

    def test_close_connection(self):
        """データベース接続を閉じる機能のテスト"""
        self.db_manager.close()
        self.db_manager.driver.close.assert_called_once()
        
    def test_create_meaning_node(self):
        """MeaningIDノード作成機能のテスト"""
        test_node = MeaningID(
            meaning_id="M_TEST_001",
            canonical_name={"ja": "テスト概念", "en": "Test Concept"},
            description={"ja": "これはテスト用の概念です。"},
            is_abstract=True
        )
        mock_session = MagicMock()
        self.db_manager.driver.session.return_value.__enter__.return_value = mock_session
        self.db_manager.create_meaning_node(test_node)
        mock_session.execute_write.assert_called_once_with(
            self.db_manager._create_and_return_node, test_node
        )

    def test_create_relationship(self):
        """Relationship（関係性）作成機能のテスト"""
        test_rel = Relationship(
            source_meaning_id="M_SRC_001",
            target_meaning_id="M_TGT_001",
            relationship_type="Is_A_Test_Of",
            source_of_data="UnitTest"
        )
        mock_session = MagicMock()
        self.db_manager.driver.session.return_value.__enter__.return_value = mock_session
        self.db_manager.create_relationship(test_rel)
        mock_session.execute_write.assert_called_once_with(
            self.db_manager._create_and_return_relationship, test_rel
        )

    def test_connection_failure(self):
        """
        [異常系テスト] データベースへの接続が失敗するケースをテスト
        GraphDatabase.driverが例外を発生させた場合に、
        self.driverがNoneのままであることを確認する。
        """
        with patch('aruism_ai.ontology.db_manager.GraphDatabase.driver') as mock_failing_driver:
            mock_failing_driver.side_effect = ConnectionError("DB接続失敗の模擬エラー")
            failed_manager = GraphDBManager(TEST_URI, TEST_USER, TEST_PASSWORD)
            assert failed_manager.driver is None