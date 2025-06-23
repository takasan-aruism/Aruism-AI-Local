######################################################################
# Aruism AI Project - Unit Tests for WordNet Importer (Refactored)
#
# バージョン: 2.2 (モック戦略を修正した最終版)
# 作成日: 2025-06-23
######################################################################
import pytest
from unittest.mock import MagicMock, patch
import sqlite3

from aruism_ai.bootstrapping.wordnet_importer import WordNetImporter
from aruism_ai.ontology.db_manager import GraphDBManager

class TestWordNetImporter:
    """WordNetImporter (リファクタリング版) のユニットテストクラス"""

    def setup_method(self, method):
        """DBManagerとSQLite接続をモック化"""
        self.mock_db_manager = MagicMock(spec=GraphDBManager)
        
        self.mock_sqlite_connect = patch('sqlite3.connect').start()
        self.mock_conn = self.mock_sqlite_connect.return_value
        self.mock_cursor = self.mock_conn.cursor.return_value
        
        self.importer = WordNetImporter("dummy_path.db", self.mock_db_manager)

    def teardown_method(self, method):
        """各テスト後にパッチを停止"""
        patch.stopall()

    def test_enriches_existing_concept(self):
        """
        [正常系] 既存のConceptノードに、WordNetの情報を正しく追記できるかテスト
        """
        # 1. 偽のカーソルが返す「答えのリスト」を順番に定義する
        self.mock_cursor.fetchone.side_effect = [
            # 1回目の呼び出し（「愛」のsynset検索）に対する答え
            {'synset': '07543288-n'},
            # 2回目の呼び出し（synsetの英語定義検索）に対する答え
            {'name': 'love; a strong positive emotion'},
            # 3回目の呼び出し（上位概念の検索）に対する答え
            {'synset2': '07541634-n'},
            # 4回目の呼び出し（上位概念の英語定義検索）に対する答え
            {'name': 'emotion'},
            # 5回目の呼び出し（上位概念の日本語名検索）に対する答え
            {'lemma': '感情'}
        ]
        
        # 2. インポート処理を実行
        self.importer.enrich_concept_by_name("愛", "M0001")

        # 3. 検証
        self.mock_db_manager.create_concept_node.assert_called_once()
        self.mock_db_manager.update_node_properties.assert_called_once()
        self.mock_db_manager.create_relationship.assert_called_once()

        # updateの引数が正しいか検証
        update_args, _ = self.mock_db_manager.update_node_properties.call_args
        updated_id, updated_props = update_args[0], update_args[1]
        
        assert updated_id == "M0001"
        assert updated_props["wordnet_synset_id"] == "07543288-n"