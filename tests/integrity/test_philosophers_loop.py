######################################################################
# Aruism AI Project - Unit Tests for PhilosophersLoop
#
# このファイルは、PhilosophersLoopクラスのユニットテストを定義します。
#
# バージョン: 1.0
# 作成日: 2025-06-22
######################################################################

import pytest
from unittest.mock import MagicMock

# [公式仕様§3.3準拠]
from aruism_ai.integrity.philosophers_loop import PhilosophersLoop

class TestPhilosophersLoop:
    """PhilosophersLoopのユニットテストクラス"""

    def setup_method(self, method):
        """各テストの前にループのインスタンスを作成"""
        self.loop = PhilosophersLoop()

    def test_block_response_containing_forbidden_word(self):
        """
        [レイヤー1: リスク管理] 応答に禁止ワードが含まれる場合、
        その応答をブロックし、代替メッセージを返すことをテストする。
        """
        # 1. テスト対象の文章（アリズムQ&Aからの引用を想定）
        #    この単語は、それ自体が悪なのではなく、文脈におけるリスクをテストするためのものです。
        original_text = "他の宗教を認めない場合、その存在の断絶という執念には極めて大きな負荷が生じ、民族浄化という形で私たちは経験してきた。"
        
        # 2. 期待される応答（ブロック時のメッセージ）
        expected_response = "[倫理規定により、この応答は表示できません]"

        # 3. メソッド実行
        corrected_text = self.loop.review_and_correct(original_text)

        # 4. 検証
        assert corrected_text == expected_response