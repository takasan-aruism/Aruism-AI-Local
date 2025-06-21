######################################################################
# Aruism AI Project - Unit Tests for Hierarchy Engine
# バージョン: 2.1 (モック戦略を修正した最終版)
# 作成日: 2025-06-22
######################################################################

import pytest
from unittest.mock import MagicMock, PropertyMock, patch
import logging

from aruism_ai.reasoning.hierarchy_engine import HierarchyEngine
from aruism_ai.ontology.db_manager import GraphDBManager
from neo4j.exceptions import ServiceUnavailable, Neo4jError

# テスト用の定数
TEST_CONCEPT = "ハワイ島"
TEST_HIERARCHY = ["島", "陸地", "地理的特徴"]
TEST_AXIS_GEOGRAPHICAL = "地理的分類"

class TestHierarchyEngine:
    """HierarchyEngineの包括的なユニットテストクラス"""

    def setup_method(self, method):
        self.mock_db_manager = MagicMock(spec=GraphDBManager)
        self.mock_driver = MagicMock()
        type(self.mock_db_manager).driver = PropertyMock(return_value=self.mock_driver)
        self.engine = HierarchyEngine(self.mock_db_manager)

    # ================== 正常系テスト ==================
    def test_trace_upwards_simple_hierarchy(self):
        """[正常系] 単純な階層構造が正しく取得されるケース"""
        mock_session = self.mock_driver.session.return_value.__enter__.return_value
        # [修正点] execute_read の戻り値を直接設定する
        mock_session.execute_read.return_value = TEST_HIERARCHY
        hierarchy = self.engine.trace_upwards(TEST_CONCEPT)
        assert hierarchy == TEST_HIERARCHY
        # execute_read が正しい引数で呼ばれたことを確認
        mock_session.execute_read.assert_called_once()
        assert mock_session.execute_read.call_args[0][1] == TEST_CONCEPT.lower()

    def test_trace_upwards_with_axis(self):
        """[正常系] 軸指定での階層探索"""
        geographical_hierarchy = ["島", "陸地", "地球表面"]
        mock_session = self.mock_driver.session.return_value.__enter__.return_value
        mock_session.execute_read.return_value = geographical_hierarchy
        hierarchy = self.engine.trace_upwards(TEST_CONCEPT, axis=TEST_AXIS_GEOGRAPHICAL)
        assert hierarchy == geographical_hierarchy
        # execute_read に軸パラメータが渡されたことを確認
        assert mock_session.execute_read.call_args[0][2] == TEST_AXIS_GEOGRAPHICAL

    def test_trace_upwards_no_hierarchy(self):
        """[正常系] 階層が存在しない場合に空リストを返すケース"""
        mock_session = self.mock_driver.session.return_value.__enter__.return_value
        mock_session.execute_read.return_value = []
        hierarchy = self.engine.trace_upwards("階層のない概念")
        assert hierarchy == []

    # ================== 異常系テスト ==================
    def test_initialization_failure_no_driver(self):
        """[異常系] driverがNoneの場合、初期化時にエラーが発生"""
        type(self.mock_db_manager).driver = PropertyMock(return_value=None)
        with pytest.raises(ConnectionError):
            HierarchyEngine(self.mock_db_manager)

    def test_trace_upwards_empty_input(self):
        """[異常系] 空文字列が入力された場合のテスト"""
        with pytest.raises(ValueError):
            self.engine.trace_upwards("")

    def test_trace_upwards_none_input(self):
        """[異常系] Noneが入力された場合のテスト"""
        with pytest.raises(ValueError):
            self.engine.trace_upwards(None)

    def test_trace_upwards_db_connection_error(self):
        """[異常系] データベース接続エラーのテスト"""
        mock_session = self.mock_driver.session.return_value.__enter__.return_value
        # [修正点] execute_read の副作用として例外を設定
        mock_session.execute_read.side_effect = ServiceUnavailable("Database connection lost")
        with pytest.raises(RuntimeError, match="階層探索に失敗しました"):
            self.engine.trace_upwards(TEST_CONCEPT)

    def test_trace_upwards_neo4j_error(self):
        """[異常系] Neo4j固有エラーのテスト"""
        mock_session = self.mock_driver.session.return_value.__enter__.return_value
        
        # ▼▼▼ [修正点] Neo4jErrorの正しいインスタンス化の方法に修正 ▼▼▼
        neo4j_err = Neo4jError("Cypher syntax error")
        
        mock_session.execute_read.side_effect = neo4j_err
        with pytest.raises(RuntimeError, match="階層探索に失敗しました"):
            self.engine.trace_upwards(TEST_CONCEPT)
            
    # ================== エッジケーステスト ==================
    def test_trace_upwards_with_whitespace(self):
        """[エッジケース] 前後の空白を含む概念名の処理"""
        concept_with_spaces = "  概念名  "
        mock_session = self.mock_driver.session.return_value.__enter__.return_value
        mock_session.execute_read.return_value = ["上位"]
        
        hierarchy = self.engine.trace_upwards(concept_with_spaces)
        
        assert hierarchy == ["上位"]
        # 無害化された後の名前が渡されていることを確認
        assert mock_session.execute_read.call_args[0][1] == "概念名"