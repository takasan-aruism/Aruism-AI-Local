######################################################################
# Aruism AI Project - Unit Tests for User State Model
#
# バージョン: 1.0
# 作成日: 2025-06-24
######################################################################
import pytest
from unittest.mock import patch
import time

from aruism_ai.reasoning.user_state_model import UserStateModel
from aruism_ai.ontology.models import Concept

class TestUserStateModel:
    """UserStateModelのユニットテストクラス"""

    # ▼▼▼ test_tracks_session_duration全体が、
    # この TestUserStateModel クラスの中に、正しくインデントされている必要があります ▼▼▼
    def test_tracks_session_duration(self):
        """[正常系] 対話のセッション時間を正しく追跡できるか"""
        
        # 'with'ブロックの内側でmodelを生成することで、
        # __init__のタイミングでもtime.time()がモック化される
        with patch('time.time') as mock_time:
            
            # 1. 時間がモック化された環境で、モデルを初期化
            mock_time.return_value = 1000.0
            model = UserStateModel("test_user")
            
            # 2. 最初の対話
            model.log_interaction()
            state = model.get_current_state()
            assert state["session_duration_seconds"] == 0

            # 3. 60秒後の次の対話
            mock_time.return_value = 1060.0
            model.log_interaction()
            state = model.get_current_state()
            assert state["session_duration_seconds"] == 60
    def test_tracks_interaction_count(self):
        """[正常系] 対話の回数を正しく追跡できるか"""
        
        model = UserStateModel("test_user")

        # 3回、インタラクションを記録する
        model.log_interaction()
        model.log_interaction()
        model.log_interaction()
        
        state = model.get_current_state()

        # 検証：state辞書の中に、正しい回数が含まれているか
        assert "interaction_count" in state
        assert state["interaction_count"] == 3
    def test_hedonic_adaptation_to_success(self):
        """[正常系] タスクの連続成功により、「喜び」の増加量が減衰するか"""
        
        model = UserStateModel("test_user")

        # 最初の成功
        model.log_task_outcome(success=True)
        satisfaction1 = model.get_current_state()["satisfaction"] # 満足度
        assert satisfaction1 > 0

        # 2回目の成功
        model.log_task_outcome(success=True)
        satisfaction2 = model.get_current_state()["satisfaction"]
        # 満足度は増加するが、その増加量は1回目より小さいはず
        assert satisfaction2 > satisfaction1
        assert (satisfaction2 - satisfaction1) < satisfaction1

        # 3回目の成功
        model.log_task_outcome(success=True)
        satisfaction3 = model.get_current_state()["satisfaction"]
        # 増加量はさらに小さくなるはず
        assert satisfaction3 > satisfaction2
        assert (satisfaction3 - satisfaction2) < (satisfaction2 - satisfaction1)

#
# --- test_user_state_model.py の末尾に以下を追記 ---
#

# 新しいモデル（AdaptiveResonanceModel）の仮実装
# NOTE: これはテストを先行させるための一時的なものです。
#       実際のロジックは今後実装します。
import math

class AdaptiveResonanceModel:
    """
    ユーザーの共鳴度を動的に計算し、最適な介入を決定するモデル（将来実装）
    """
    def _calculate_flow(self, C: float, S: float) -> float:
        """
        フロー状態を計算する。【改訂版ロジック】
        挑戦(C)とスキル(S)のバランスに加え、両者のレベルの高さも評価する。
        """
        if C == 0 and S == 0:
            return 0.0
        
        # 挑戦とスキルの最大値を10.0と仮定
        MAX_LEVEL = 10.0

        # ガウス関数でバランスを評価
        balance_factor = math.exp(-((C - S)**2) / (2 * 2**2)) # σ=2

        # レベルの高さをCとSの積で評価し、正規化（※クアドラントモデルの反映）
        level_factor = (C * S) / (MAX_LEVEL * MAX_LEVEL)

        return balance_factor * level_factor

# 新しいテストクラスとメソッド
class TestAdaptiveResonanceModel:
    """AdaptiveResonanceModelのユニットテストクラス"""

    def test_flow_distinguishes_apathy_from_flow(self):
        """
        [正常系] フロー計算式が「無関心」と「フロー」を区別できるか。
        - 低挑戦・低スキル（無関心）では低いスコアに、
        - 高挑戦・高スキル（フロー）では高いスコアになることを検証する。
        """
        model = AdaptiveResonanceModel()

        # ケース1：無関心（Apathy）- 低挑戦(C=2), 低スキル(S=2)
        apathy_score = model._calculate_flow(C=2.0, S=2.0)

        # ケース2：フロー（Flow）- 高挑戦(C=8), 高スキル(S=8)
        flow_score = model._calculate_flow(C=8.0, S=8.0)

        # --- 検証 ---
        # 1. フローのスコアは無関心のスコアより有意に高いはず
        assert flow_score > apathy_score * 2 # 少なくとも2倍以上は差がつくはず

        # 2. フローのスコアは高い値（例: 0.5以上）になるはず
        assert flow_score > 0.5

        # 3. 無関心のスコアは低い値（例: 0.3未満）になるはず
        assert apathy_score < 0.3