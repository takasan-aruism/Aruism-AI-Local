######################################################################
# Aruism AI Project - Unit Tests for Graph Database Manager
#
# バージョン: 2.0 (新Conceptモデル対応版)
# 最終更新日: 2025-06-22
######################################################################

import pytest
from unittest.mock import patch, MagicMock

from aruism_ai.ontology.models import Concept, Relationship
from aruism_ai.ontology.db_manager import GraphDBManager

# テスト用の定数
TEST_URI = "bolt://localhost:7687"
TEST_USER = "neo4j"
TEST_PASSWORD = "11dr34SSAAa_$$aae"

class TestGraphDBManager:
    """GraphDBManagerのユニットテストクラス"""

    def setup_method(self, method):
        """各テストメソッドの実行前に呼び出されるセットアップ"""
        # GraphDatabase.driverをモック化
        self.mock_driver_patch = patch('aruism_ai.ontology.db_manager.GraphDatabase.driver')
        self.mock_driver_constructor = self.mock_driver_patch.start()
        
        # driverインスタンスそのものをモックとして作成
        self.mock_driver_instance = MagicMock()
        self.mock_driver_constructor.return_value = self.mock_driver_instance
        
        # テスト対象のインスタンスを作成
        self.db_manager = GraphDBManager(TEST_URI, TEST_USER, TEST_PASSWORD)

    def teardown_method(self, method):
        """各テストメソッドの実行後に呼び出されるクリーンアップ"""
        self.mock_driver_patch.stop()

    def test_create_simple_concept_node(self):
        """[正常系] 単純なConceptノード作成機能をテスト"""
        test_node = Concept(concept_id="C_TEST_001", canonical_name_ja="テスト概念")
        
        mock_session = self.mock_driver_instance.session.return_value.__enter__.return_value
        
        self.db_manager.create_concept_node(test_node)
        
        mock_session.execute_write.assert_called_once_with(
            self.db_manager._create_and_return_node, test_node
        )

    def test_create_relationship(self):
        """[正常系/存在の連動性] Relationship作成機能をテスト"""
        test_rel = Relationship(
            source_concept_id="C_SRC_001",
            target_concept_id="C_TGT_001",
            relationship_type="Is_A_Test_Of"
        )
        mock_session = self.mock_driver_instance.session.return_value.__enter__.return_value
        
        self.db_manager.create_relationship(test_rel)
        
        mock_session.execute_write.assert_called_once_with(
            self.db_manager._create_and_return_relationship, test_rel
        )

    def test_creates_rich_concept_node(self):
        """[新DB仕様] 豊富なプロパティを持つ新しいConceptノードを作成できるかテストする。"""
        # 1. 新しいリッチなノードを定義
        rich_concept = Concept(
            concept_id="C_LOVE_001",
            canonical_name_ja="愛",
            canonical_name_en="love",
            wordnet_synset_id="07543288-n",
            abstraction_level=3,
            resonance_potential=0.85,
            source=["manual"]
        )

        # 2. モックの設定
        mock_tx = MagicMock()
        mock_session = self.mock_driver_instance.session.return_value.__enter__.return_value
        mock_session.execute_write.side_effect = lambda work_func, node: work_func(mock_tx, node)
        
        # 3. メソッド実行
        self.db_manager.create_concept_node(rich_concept)

        # 4. 検証：runメソッドが正しいプロパティで呼ばれたかを確認
        mock_tx.run.assert_called_once()
        args, kwargs = mock_tx.run.call_args
        
        # propsの中に、新しいプロパティが正しく含まれているかを確認
        assert kwargs['props']['canonical_name_ja'] == "愛"
        assert kwargs['props']['wordnet_synset_id'] == "07543288-n"
        assert kwargs['props']['abstraction_level'] == 3
        assert "manual" in kwargs['props']['source']