######################################################################
# Aruism AI Project - Unit Tests for Graph Database Manager
# バージョン: 1.1 (AIチームレビュー反映版)
# 最終更新日: 2025-06-22
######################################################################

import pytest
from unittest.mock import patch, MagicMock

# ▼▼▼ [修正点] importパスを 'aruism_ai.' 基準に統一 ▼▼▼
from aruism_ai.ontology.models import MeaningID, Relationship
from aruism_ai.ontology.db_manager import GraphDBManager

# --- テスト用の定数 ---
TEST_URI = "neo4j://testhost:7687"
TEST_USER = "testuser"
TEST_PASSWORD = "11dr34SSAAa_$$aae"

class TestGraphDBManager:
    """GraphDBManagerのユニットテストクラス"""

    def setup_method(self, method):
        """各テストメソッドの実行前に呼び出されるセットアップ"""
        self.mock_driver_patch = patch('aruism_ai.ontology.db_manager.GraphDatabase.driver')
        self.mock_driver = self.mock_driver_patch.start()
        self.db_manager = GraphDBManager(TEST_URI, TEST_USER, TEST_PASSWORD)
        self.db_manager.driver = self.mock_driver

    def teardown_method(self, method):
        """各テストメソッドの実行後に呼び出されるクリーンアップ"""
        self.mock_driver_patch.stop()

    def test_successful_connection(self):
        """[正常系] データベースへの接続が成功するケースをテスト"""
        self.mock_driver.assert_called_once_with(TEST_URI, auth=(TEST_USER, TEST_PASSWORD))
        assert self.db_manager.driver is not None

    def test_close_connection(self):
        """[正常系] データベース接続を閉じる機能のテスト"""
        self.db_manager.close()
        self.db_manager.driver.close.assert_called_once()
        
    def test_create_meaning_node(self):
        """
        [正常系/存在の核] MeaningIDノード作成機能をテスト
        Aruism認知アーキテクチャ設計書 §2.1, §3.2 の検証
        """
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
        """
        [正常系/存在の連動性] Relationship作成機能をテスト
        Aruism認知アーキテクチャ設計書 §2.4, §3.4 の検証
        """
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
        [異常系] データベースへの接続が失敗するケースをテスト
        """
        # ▼▼▼ [修正点] patchのパスを 'aruism_ai.' 基準に統一 ▼▼▼
        with patch('aruism_ai.ontology.db_manager.GraphDatabase.driver') as mock_failing_driver:
            mock_failing_driver.side_effect = ConnectionError("DB接続失敗の模擬エラー")
            failed_manager = GraphDBManager(TEST_URI, TEST_USER, TEST_PASSWORD)
            assert failed_manager.driver is None