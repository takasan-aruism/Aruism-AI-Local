import pytest
from aruism_ai.resonance.bkt import BayesianKnowledgeTracing

class TestBayesianKnowledgeTracing:

    @pytest.fixture
    def bkt_model(self):
        """テスト用のBKTモデルインスタンスを生成する"""
        return BayesianKnowledgeTracing(
            init=0.25,    # 初期習熟確率 25%
            transit=0.15, # 学習確率 15%
            slip=0.10,    # ミスする確率 10%
            guess=0.20    # 推測で当たる確率 20%
        )

    def test_update_knowledge_state_on_correct_answer(self, bkt_model):
        """[正常系] 正答した場合、習熟確率が正しく上昇するか"""
        prior = 0.5  # 事前確率50%
        observation = True  # 正答した

        posterior = bkt_model.update_knowledge_state(prior, observation)
        
        # 正答した場合、確率は必ず上昇するはず
        assert posterior > prior
        
        # 具体的な計算結果を検証（理論値との比較）
        # P(L|知っている) = 0.5 + (1-0.5)*0.15 = 0.575
        # P(正答|知っている) = 1 - P(S) = 0.9
        # P(正答|知らない) = P(G) = 0.2
        # P(正答) = 0.575 * 0.9 + (1-0.575) * 0.2 = 0.5175 + 0.085 = 0.6025
        # P(事後) = (0.575 * 0.9) / 0.6025 = 0.5175 / 0.6025
        expected_posterior = 0.5175 / 0.6025
        assert posterior == pytest.approx(expected_posterior)

    def test_update_knowledge_state_on_incorrect_answer(self, bkt_model):
        """[正常系] 誤答した場合、習熟確率が正しく下降するか"""
        prior = 0.5  # 事前確率50%
        observation = False # 誤答した

        posterior = bkt_model.update_knowledge_state(prior, observation)

        # 誤答した場合、確率は必ず下降するはず
        assert posterior < prior

        # 具体的な計算結果を検証（理論値との比較）
        # P(L|知っている) = 0.575
        # P(誤答|知っている) = P(S) = 0.1
        # P(誤答|知らない) = 1 - P(G) = 0.8
        # P(誤答) = 0.575 * 0.1 + (1-0.575) * 0.8 = 0.0575 + 0.34 = 0.3975
        # P(事後) = (0.575 * 0.1) / 0.3975 = 0.0575 / 0.3975
        expected_posterior = 0.0575 / 0.3975
        assert posterior == pytest.approx(expected_posterior)