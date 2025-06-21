######################################################################
# Aruism AI Project - Unit Tests for Symmetry Engine
#
# バージョン: 2.3 (モック精度・エラー処理を反映した最終版)
# 作成日: 2025-06-21
######################################################################

import pytest
from unittest.mock import patch, MagicMock, PropertyMock

from aruism_ai.reasoning.symmetry_engine import SymmetryEngine
from aruism_ai.ontology.db_manager import GraphDBManager

# テスト用の定数
TEST_CONCEPT = "善"
TEST_SYMMETRIC = "悪"
TEST_TEXT_WITH_TENSION = "この世界には善と悪の両方が存在する。"
TEST_TEXT_WITHOUT_TENSION = "この世界には善意だけが存在する。"


class TestSymmetryEngine:
    """SymmetryEngineの包括的なユニットテストクラス"""

    @patch('aruism_ai.reasoning.symmetry_engine.Tokenizer')
    def setup_method(self, method, MockTokenizer):
        """各テストメソッドの実行前に呼び出されるセットアップ"""
        self.mock_db_manager = MagicMock(spec=GraphDBManager)
        self.mock_driver = MagicMock()
        type(self.mock_db_manager).driver = PropertyMock(return_value=self.mock_driver)
        self.mock_tokenizer_instance = MockTokenizer.return_value
        self.engine = SymmetryEngine(self.mock_db_manager)

    def teardown_method(self, method):
        pass

    # ================== 正常系テスト ==================

    def test_generate_inverted_question_found(self):
        """[正常系] 対称概念が見つかり、反転質問が正しく生成されるケース"""
        mock_session = self.mock_driver.session.return_value.__enter__.return_value
        mock_session.execute_read.return_value = TEST_SYMMETRIC

        question = self.engine.generate_inverted_question(TEST_CONCEPT)
        assert question == f"もし、「{TEST_CONCEPT}」の対称的な存在である「{TEST_SYMMETRIC}」の視点から考えると、どのような意味や価値が見えてくるでしょうか？"

    def test_generate_inverted_question_not_found(self):
        """[正常系] 対称概念が見つからない場合にNoneを返すケース"""
        mock_session = self.mock_driver.session.return_value.__enter__.return_value
        mock_session.execute_read.return_value = None
        question = self.engine.generate_inverted_question("存在しない概念")
        assert question is None

    def test_detect_tension_found(self):
        """[正常系] テキスト内に対称ペアが存在し、緊張関係が検出されるケース"""
        mock_tokens = [MagicMock(surface=s) for s in [TEST_CONCEPT, "と", TEST_SYMMETRIC]]
        self.mock_tokenizer_instance.tokenize.return_value = mock_tokens
        mock_session = self.mock_driver.session.return_value.__enter__.return_value
        mock_session.execute_read.return_value = [(TEST_CONCEPT, TEST_SYMMETRIC), ("光", "闇")]

        has_tension, pair = self.engine.detect_tension(TEST_TEXT_WITH_TENSION)
        assert has_tension is True
        assert pair == (TEST_CONCEPT, TEST_SYMMETRIC)
        self.mock_tokenizer_instance.tokenize.assert_called_once_with(TEST_TEXT_WITH_TENSION)

    def test_detect_tension_not_found(self):
        """[正常系] テキスト内に対称ペアが存在しない場合のテスト"""
        mock_tokens = [MagicMock(surface="善意")]
        self.mock_tokenizer_instance.tokenize.return_value = mock_tokens
        mock_session = self.mock_driver.session.return_value.__enter__.return_value
        mock_session.execute_read.return_value = [(TEST_CONCEPT, TEST_SYMMETRIC)]
        has_tension, pair = self.engine.detect_tension(TEST_TEXT_WITHOUT_TENSION)
        assert has_tension is False
        assert pair is None

    # ================== 異常系テスト ==================

    def test_generate_inverted_question_empty_input(self):
        """[異常系] 空文字列が入力された場合のテスト"""
        mock_session = self.mock_driver.session.return_value.__enter__.return_value
        mock_session.execute_read.return_value = None
        question = self.engine.generate_inverted_question("")
        assert question is None

    def test_generate_inverted_question_db_error(self):
        """[異常系] データベースエラーが発生した場合のテスト"""
        mock_session = self.mock_driver.session.return_value.__enter__.return_value
        mock_session.execute_read.side_effect = Exception("Database connection lost")
        with pytest.raises(Exception, match="Database connection lost"):
            self.engine.generate_inverted_question(TEST_CONCEPT)

    def test_detect_tension_empty_text(self):
        """[異常系] 空のテキストが入力された場合のテスト"""
        self.mock_tokenizer_instance.tokenize.return_value = []
        mock_session = self.mock_driver.session.return_value.__enter__.return_value
        mock_session.execute_read.return_value = [(TEST_CONCEPT, TEST_SYMMETRIC)]
        has_tension, pair = self.engine.detect_tension("")
        assert has_tension is False
        assert pair is None

    def test_detect_tension_tokenizer_error(self):
        """[異常系] Tokenizerでエラーが発生した場合のテスト"""
        self.mock_tokenizer_instance.tokenize.side_effect = Exception("Tokenizer error")
        with pytest.raises(Exception, match="Tokenizer error"):
            self.engine.detect_tension(TEST_TEXT_WITH_TENSION)

    # ================== エッジケーステスト ==================

    def test_generate_inverted_question_with_special_chars(self):
        """[エッジケース] 特殊文字を含む概念名の処理"""
        special_concept = "「愛」と『憎しみ』"
        expected_symmetric = "対称的な概念"
        mock_session = self.mock_driver.session.return_value.__enter__.return_value
        mock_session.execute_read.return_value = expected_symmetric
        question = self.engine.generate_inverted_question(special_concept)
        assert special_concept in question
        assert expected_symmetric in question

    def test_detect_tension_with_multiple_pairs(self):
        """[エッジケース] 複数の対称ペアが存在する場合、最初のペアが返される"""
        text = "光と闇、善と悪が交錯する世界"
        mock_tokens = [MagicMock(surface=s) for s in ["光", "と", "闇", "、", TEST_CONCEPT, "と", TEST_SYMMETRIC]]
        self.mock_tokenizer_instance.tokenize.return_value = mock_tokens
        mock_session = self.mock_driver.session.return_value.__enter__.return_value
        mock_session.execute_read.return_value = [("光", "闇"), (TEST_CONCEPT, TEST_SYMMETRIC)]
        has_tension, pair = self.engine.detect_tension(text)
        assert has_tension is True
        assert pair == ("光", "闇")

    # ================== 初期化テスト ==================

    @patch('aruism_ai.reasoning.symmetry_engine.Tokenizer')
    def test_init_with_none_driver(self, MockTokenizer):
        """[異常系] driverがNoneの場合、初期化時にエラーが発生"""
        mock_db_manager = MagicMock(spec=GraphDBManager)
        type(mock_db_manager).driver = PropertyMock(return_value=None)
        with pytest.raises(ConnectionError, match="データベースドライバーが初期化されていません"):
            SymmetryEngine(mock_db_manager)

    @patch('aruism_ai.reasoning.symmetry_engine.Tokenizer', side_effect=ImportError("No module named 'janome'"))
    def test_init_tokenizer_import_error(self, MockTokenizer):
        """[異常系] Janomeがインストールされていない場合のシミュレーション"""
        with pytest.raises(ImportError, match="No module named 'janome'"):
            # このコンテキスト内では、Tokenizerのimportが失敗する
            from aruism_ai.reasoning.symmetry_engine import SymmetryEngine as EngineWithImportFail
            EngineWithImportFail(self.mock_db_manager)