######################################################################
# Aruism AI Project - Unit Tests for Causal Engine
#
# このファイルは、CausalEngineクラスのユニットテストを定義します。
#
# バージョン: 1.0
# 作成日: 2025-06-21
######################################################################

import pytest
from unittest.mock import MagicMock, PropertyMock

from aruism_ai.reasoning.causal_engine import CausalEngine
from aruism_ai.ontology.db_manager import GraphDBManager
from neo4j.exceptions import Neo4jError

class TestCausalEngine:
    """CausalEngineのユニットテストクラス"""

    def setup_method(self, method):
        """各テストの前に、モック化されたDBManagerと共にエンジンをセットアップ"""
        self.mock_db_manager = MagicMock(spec=GraphDBManager)
        self.mock_driver = MagicMock()
        type(self.mock_db_manager).driver = PropertyMock(return_value=self.mock_driver)
        self.engine = CausalEngine(self.mock_db_manager)

    def test_initialization_success(self):
        """[正常系] エンジンが正常に初期化されるかのテスト"""
        assert self.engine.db_manager is self.mock_db_manager

    def test_initialization_failure_no_driver(self):
        """[異常系] driverがNoneの場合、初期化時にエラーが発生するかのテスト"""
        type(self.mock_db_manager).driver = PropertyMock(return_value=None)
        with pytest.raises(ConnectionError):
            CausalEngine(self.mock_db_manager)

    # tests/reasoning/test_causal_engine.py 内

    def test_trace_causality_causes_found(self):
        """
        [正常系/存在の連動性] 原因のみが見つかる場合のテスト
        """
        # ▼▼▼ [修正点] 偽のDBレコードを、キーで値が引ける「辞書」で作成する ▼▼▼
        mock_causes_result = [{"cause_name": "雨"}]
        mock_effects_result = []
        
        mock_tx = MagicMock()
        mock_tx.run.side_effect = [mock_causes_result, mock_effects_result]

        mock_session = self.mock_driver.session.return_value.__enter__.return_value
        mock_session.execute_read.side_effect = lambda work_func, name: work_func(mock_tx, name)

        result = self.engine.trace_causality("地面が濡れる")

        assert result == {"causes": ["雨"], "effects": []}
        assert mock_tx.run.call_count == 2

    def test_trace_causality_effects_found(self):
        """[正常系/存在の連動性] 結果のみが見つかる場合のテスト"""
        # ▼▼▼ [修正点] こちらも同様に、偽のDBレコードを「辞書」で作成 ▼▼▼
        mock_causes_result = []
        mock_effects_result = [{"effect_name": "地面が濡れる"}]
        
        mock_tx = MagicMock()
        mock_tx.run.side_effect = [mock_causes_result, mock_effects_result]

        mock_session = self.mock_driver.session.return_value.__enter__.return_value
        mock_session.execute_read.side_effect = lambda work_func, name: work_func(mock_tx, name)

        result = self.engine.trace_causality("雨")
        assert result == {"causes": [], "effects": ["地面が濡れる"]}
        
    def test_trace_causality_none_found(self):
        """[正常系/分岐] 因果関係が何も見つからない場合のテスト"""
        mock_tx = MagicMock()
        mock_tx.run.side_effect = [[], []] # 2回とも空の結果
        mock_session = self.mock_driver.session.return_value.__enter__.return_value
        mock_session.execute_read.side_effect = lambda work_func, name: work_func(mock_tx, name)

        result = self.engine.trace_causality("無関係な概念")
        assert result == {"causes": [], "effects": []}

    def test_trace_causality_db_error(self):
        """[異常系] DB検索中にエラーが発生し、空のマップを返すテスト"""
        mock_session = self.mock_driver.session.return_value.__enter__.return_value
        mock_session.execute_read.side_effect = Neo4jError("DBエラー")
        
        result = self.engine.trace_causality("任意の概念")
        assert result == {"causes": [], "effects": []}

    def test_trace_causality_empty_input(self):
        """[異常系] 空文字列が入力された場合に空のマップを返すテスト"""
        result = self.engine.trace_causality("")
        assert result == {"causes": [], "effects": []}