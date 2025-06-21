######################################################################
# Aruism AI Project - Unit Tests for PhilosophersLoop
#
# バージョン: 1.1 (モック設定を修正した最終版)
# 作成日: 2025-06-22
######################################################################

import pytest
# ▼▼▼ [修正点] patch を unittest.mock からインポートする ▼▼▼
from unittest.mock import MagicMock, mock_open, patch

from aruism_ai.integrity.philosophers_loop import PhilosophersLoop

class TestPhilosophersLoop:
    """PhilosophersLoopのユニットテストクラス"""

    # [修正点] setup_methodは、各テストで異なるセットアップが必要なため、削除します。

    # ▼▼▼ [修正点] このテスト専用に、_load_forbidden_wordsメソッドを直接モックする ▼▼▼
    @patch.object(PhilosophersLoop, '_load_forbidden_words', return_value=["民族浄化"])
    def test_block_response_containing_forbidden_word(self, mock_load_words):
        """
        [レイヤー1: リスク管理] 応答に禁止ワードが含まれる場合、
        その応答をブロックし、代替メッセージを返すことをテストする。
        """
        # 1. ループのインスタンスを生成
        #    この時、_load_forbidden_words がモックに置き換えられている
        loop = PhilosophersLoop()
        
        # 2. テスト対象の文章
        original_text = "他の宗教を認めない場合、その存在の断絶という執念には極めて大きな負荷が生じ、民族浄化という形で私たちは経験してきた。"
        expected_response = "[倫理規定により、この応答は表示できません]"

        # 3. メソッド実行
        corrected_text = loop.review_and_correct(original_text)

        # 4. 検証
        assert corrected_text == expected_response
        # 内部で _load_forbidden_words が呼ばれたことを確認
        mock_load_words.assert_called_once()

    def test_loads_forbidden_words_from_file(self):
        """
        [レイヤー1: 拡張性] 設定ファイルから禁止ワードを正しく読み込めるかテストする。
        """
        mock_file_content = '["禁止ワード1", "禁止ワード2", "ヘイトスピーチ"]'
        
        # [修正点] このテストでは builtins.open をモックする
        with patch("builtins.open", mock_open(read_data=mock_file_content)) as mock_file:
            loop = PhilosophersLoop(config_path="config/forbidden_words.json")

            assert loop.forbidden_words == ["禁止ワード1", "禁止ワード2", "ヘイトスピーチ"]
            mock_file.assert_called_once_with("config/forbidden_words.json", "r", encoding="utf-8")