######################################################################
# Aruism AI Project - User State Model
# ユーザーの動的な状態を管理する
#
# バージョン: 1.0 (主要指標の実装完了)
# 作成日: 2025-06-24
######################################################################
import time
from typing import List
from aruism_ai.ontology.models import Concept

class UserStateModel:
    def __init__(self, user_id: str):
        self.user_id = user_id
        # セッション管理
        self.session_start_time = time.time()
        self.last_interaction_time = self.session_start_time
        self.interaction_count = 0
        # タスク成功率とストレス
        self.successful_tasks = 0
        self.failed_tasks = 0
        self.stress_potential = 0.0
        # 快楽順応モデル
        self.satisfaction = 0.0
        self.last_success_gain = 10.0 # 最初の成功で得られる満足度
        self.adaptation_rate = 0.8    # 成功が続くごとに、喜びが80%に減衰する

    def log_interaction(self):
        """ユーザーとのインタラクションを記録する"""
        self.interaction_count += 1
        self.last_interaction_time = time.time()

    def log_task_outcome(self, success: bool):
        """AIが提案したタスクの成否を記録し、状態を更新する"""
        if success:
            self.successful_tasks += 1
            # [新機能] 快楽順応ロジック
            self.satisfaction += self.last_success_gain
            self.last_success_gain *= self.adaptation_rate # 次の喜びは少しだけ小さくなる
            # 成功はストレスを少し下げる
            self.stress_potential = max(0, self.stress_potential - 5)
        else:
            self.failed_tasks += 1
            # [新機能] ストレス蓄積ロジック
            self.stress_potential += 10

    def get_current_state(self) -> dict:
        """現在のユーザー状態に関する指標を返す"""
        current_time = time.time()
        duration = current_time - self.session_start_time
        
        total_tasks = self.successful_tasks + self.failed_tasks
        success_rate = self.successful_tasks / total_tasks if total_tasks > 0 else 1.0

        return {
            "session_duration_seconds": int(duration),
            "interaction_count": self.interaction_count,
            "task_success_rate": success_rate,
            "stress_potential": self.stress_potential,
            "satisfaction": self.satisfaction
        }