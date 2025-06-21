######################################################################
# Aruism AI Project - Unit Tests for Symmetry Engine
#
# このファイルは、SymmetryEngineクラスの包括的なユニットテストを定義します。
# 正常系、異常系、エッジケースを網羅し、実運用に耐える品質を保証します。
#
# 参照ドキュメント: Aruism_AI_Project_06_Testing_and_Evaluation_Plan.txt
# バージョン: 2.0
# 作成日: 2025-06-22
######################################################################

import pytest
from unittest.mock import patch, MagicMock, PropertyMock
from typing import Optional

# プロジェクトのルートからの絶対パスでモジュールをインポート
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
        # GraphDBManagerのモックを作成
        self.mock_db_manager = MagicMock(spec=GraphDBManager)
        self.mock_driver = MagicMock()
        
        # driverプロパティを設定（Noneチェックをパスするため）
        type(self.mock_db_manager).driver = PropertyMock(return_value=self.mock_driver)
        
        # Tokenizerのモックインスタンスを作成
        self.mock_tokenizer_instance = MockTokenizer.return_value
        
        # エンジンのインスタンスを作成
        self.engine = SymmetryEngine(self.mock_db_manager)

    def teardown_method(self, method):
        """各テストメソッドの実行後に呼び出されるクリーンアップ"""
        # 特別なクリーンアップは不要（patchデコレータが自動的に処理）
        pass

    # ================== 正常系テスト ==================

    def test_generate_inverted_question_found(self):
        """[正常系] 対称概念が見つかり、反転質問が正しく生成されるケース"""
        # DBからの返り値を設定
        mock_session = self.mock_driver.session.return_value.__enter__.return_value
        mock_result = MagicMock()
        mock_result.single.return_value = {"symmetric_name": TEST_SYMMETRIC}
        mock_session.run.return_value = mock_result

        # メソッド実行
        question = self.engine.generate_inverted_question(TEST_CONCEPT)

        # 検証
        assert question == f"もし、「{TEST_CONCEPT}」の対称的な存在である「{TEST_SYMMETRIC}」の視点から考えると、どのような意味や価値が見えてくるでしょうか？"
        
        # DBクエリが正しく実行されたことを確認
        mock_session.run.assert_called_once()
        args, kwargs = mock_session.run.call_args
        assert TEST_CONCEPT in str(kwargs)

    def test_generate_inverted_question_not_found(self):
        """[正常系] 対称概念が見つからない場合にNoneを返すケース"""
        # DBからの返り値を設定（レコードなし）
        mock_session = self.mock_driver.session.return_value.__enter__.return_value
        mock_result = MagicMock()
        mock_result.single.return_value = None
        mock_session.run.return_value = mock_result

        # メソッド実行
        question = self.engine.generate_inverted_question("存在しない概念")

        # 検証
        assert question is None

    def test_detect_tension_found(self):
        """[正常系] テキスト内に対称ペアが存在し、緊張関係が検出されるケース"""
        # Tokenizerの返り値を設定
        mock_tokens = [
            MagicMock(surface="この"), MagicMock(surface="世界"),
            MagicMock(surface="に"), MagicMock(surface="は"),
            MagicMock(surface="善"), MagicMock(surface="と"),
            MagicMock(surface="悪"), MagicMock(surface="の"),
            MagicMock(surface="両方"), MagicMock(surface="が"),
            MagicMock(surface="存在する"), MagicMock(surface="。")
        ]
        self.mock_tokenizer_instance.tokenize.return_value = mock_tokens

        # DBからの返り値を設定
        mock_session = self.mock_driver.session.return_value.__enter__.return_value
        mock_result = MagicMock()
        mock_result.single.return_value = {"name1": TEST_CONCEPT, "name2": TEST_SYMMETRIC}
        mock_session.run.return_value = mock_result

        # メソッド実行
        has_tension, pair = self.engine.detect_tension(TEST_TEXT_WITH_TENSION)

        # 検証
        assert has_tension is True
        assert pair == (TEST_CONCEPT, TEST_SYMMETRIC)
        self.mock_tokenizer_instance.tokenize.assert_called_once_with(TEST_TEXT_WITH_TENSION)

    def test_detect_tension_not_found(self):
        """[正常系] テキスト内に対称ペアが存在しない場合のテスト"""
        # Tokenizerの返り値を設定
        mock_tokens = [
            MagicMock(surface="この"), MagicMock(surface="世界"),
            MagicMock(surface="に"), MagicMock(surface="は"),
            MagicMock(surface="善意"), MagicMock(surface="だけ"),
            MagicMock(surface="が"), MagicMock(surface="存在する"),
            MagicMock(surface="。")
        ]
        self.mock_tokenizer_instance.tokenize.return_value = mock_tokens

        # DBからの返り値を設定（レコードなし）
        mock_session = self.mock_driver.session.return_value.__enter__.return_value
        mock_result = MagicMock()
        mock_result.single.return_value = None
        mock_session.run.return_value = mock_result

        # メソッド実行
        has_tension, pair = self.engine.detect_tension(TEST_TEXT_WITHOUT_TENSION)

        # 検証
        assert has_tension is False
        assert pair is None

    # ================== 異常系テスト ==================

    def test_generate_inverted_question_empty_input(self):
        """[異常系] 空文字列が入力された場合のテスト"""
        # 空文字列でもDBクエリは実行される（エラーにはならない）
        mock_session = self.mock_driver.session.return_value.__enter__.return_value
        mock_result = MagicMock()
        mock_result.single.return_value = None
        mock_session.run.return_value = mock_result

        # メソッド実行
        question = self.engine.generate_inverted_question("")

        # 検証（Noneが返される）
        assert question is None

    def test_generate_inverted_question_db_error(self):
        """[異常系] データベースエラーが発生した場合のテスト"""
        # DBエラーをシミュレート
        mock_session = self.mock_driver.session.return_value.__enter__.return_value
        mock_session.run.side_effect = Exception("Database connection lost")

        # メソッド実行とエラー検証
        with pytest.raises(Exception) as exc_info:
            self.engine.generate_inverted_question(TEST_CONCEPT)
        
        assert "Database connection lost" in str(exc_info.value)

    def test_detect_tension_empty_text(self):
        """[異常系] 空のテキストが入力された場合のテスト"""
        # 空のトークンリストを返す
        self.mock_tokenizer_instance.tokenize.return_value = []

        # メソッド実行
        has_tension, pair = self.engine.detect_tension("")

        # 検証
        assert has_tension is False
        assert pair is None

    def test_detect_tension_tokenizer_error(self):
        """[異常系] Tokenizerでエラーが発生した場合のテスト"""
        # Tokenizerエラーをシミュレート
        self.mock_tokenizer_instance.tokenize.side_effect = Exception("Tokenizer error")

        # メソッド実行とエラー検証
        with pytest.raises(Exception) as exc_info:
            self.engine.detect_tension(TEST_TEXT_WITH_TENSION)
        
        assert "Tokenizer error" in str(exc_info.value)

    # ================== エッジケーステスト ==================

    def test_generate_inverted_question_with_special_chars(self):
        """[エッジケース] 特殊文字を含む概念名の処理"""
        special_concept = "「愛」と『憎しみ』"
        expected_symmetric = "対称的な概念"
        
        # DBからの返り値を設定
        mock_session = self.mock_driver.session.return_value.__enter__.return_value
        mock_result = MagicMock()
        mock_result.single.return_value = {"symmetric_name": expected_symmetric}
        mock_session.run.return_value = mock_result

        # メソッド実行
        question = self.engine.generate_inverted_question(special_concept)

        # 検証（特殊文字がそのまま保持される）
        assert special_concept in question
        assert expected_symmetric in question

    def test_detect_tension_with_multiple_pairs(self):
        """[エッジケース] 複数の対称ペアが存在する場合、最初のペアが返される"""
        # 複数のペアを含むテキスト
        text = "光と闇、善と悪が交錯する世界"
        
        # Tokenizerの返り値を設定
        mock_tokens = [
            MagicMock(surface="光"), MagicMock(surface="と"),
            MagicMock(surface="闇"), MagicMock(surface="、"),
            MagicMock(surface="善"), MagicMock(surface="と"),
            MagicMock(surface="悪"), MagicMock(surface="が"),
            MagicMock(surface="交錯する"), MagicMock(surface="世界")
        ]
        self.mock_tokenizer_instance.tokenize.return_value = mock_tokens

        # DBからの返り値を設定（最初のペアを返す）
        mock_session = self.mock_driver.session.return_value.__enter__.return_value
        mock_result = MagicMock()
        mock_result.single.return_value = {"name1": "光", "name2": "闇"}
        mock_session.run.return_value = mock_result

        # メソッド実行
        has_tension, pair = self.engine.detect_tension(text)

        # 検証
        assert has_tension is True
        assert pair == ("光", "闇")

    # ================== 初期化テスト ==================

    @patch('aruism_ai.reasoning.symmetry_engine.Tokenizer')
    def test_init_with_none_driver(self, MockTokenizer):
        """[異常系] driverがNoneの場合、初期化時にエラーが発生"""
        # driverをNoneに設定
        mock_db_manager = MagicMock(spec=GraphDBManager)
        type(mock_db_manager).driver = PropertyMock(return_value=None)

        # 初期化を試みる
        with pytest.raises(ConnectionError) as exc_info:
            SymmetryEngine(mock_db_manager)
        
        assert "データベースドライバーが初期化されていません" in str(exc_info.value)

    @patch('aruism_ai.reasoning.symmetry_engine.Tokenizer')
    def test_init_tokenizer_import_error(self, MockTokenizer):
        """[異常系] Janomeがインストールされていない場合のテスト"""
        # Tokenizerのインポートエラーをシミュレート
        MockTokenizer.side_effect = ImportError("No module named 'janome'")

        # 初期化を試みる
        with pytest.raises(ImportError) as exc_info:
            SymmetryEngine(self.mock_db_manager)
        
        assert "janome" in str(exc_info.value)