######################################################################
# Aruism AI Project - Unit Tests for AruisticRetriever
#
# バージョン: 1.0
# 作成日: 2025-06-22
######################################################################
import pytest
from unittest.mock import MagicMock, patch

from aruism_ai.retrieval.retriever import AruisticRetriever
# Retrieverが依存する全てのエンジンをインポート
from aruism_ai.reasoning.hierarchy_engine import HierarchyEngine
from aruism_ai.reasoning.symmetry_engine import SymmetryEngine
from aruism_ai.reasoning.causal_engine import CausalEngine

class TestAruisticRetriever:
    """AruisticRetrieverのユニットテストクラス"""

    def setup_method(self, method):
        """全ての思考エンジンとTokenizerをモック化してRetrieverを初期化"""
        # 各エンジンのインスタンスをモックとして作成
        self.mock_hierarchy_engine = MagicMock(spec=HierarchyEngine)
        self.mock_symmetry_engine = MagicMock(spec=SymmetryEngine)
        self.mock_causal_engine = MagicMock(spec=CausalEngine)

        # Tokenizerもモック化
        with patch('janome.tokenizer.Tokenizer') as MockTokenizer:
            self.mock_tokenizer_instance = MockTokenizer.return_value
            
            # モック化したエンジン群を使ってRetrieverを初期化
            self.retriever = AruisticRetriever(
                hierarchy_engine=self.mock_hierarchy_engine,
                symmetry_engine=self.mock_symmetry_engine,
                causal_engine=self.mock_causal_engine
            )

    def test_retrieve_for_single_concept(self):
        """[正常系] 単一の概念に関する情報を正しく取得できるかテスト"""
        # 1. 各モックの「返り値」を定義
        query_text = "善について教えて"
        concept = "善"
        
        # Tokenizerは "善" というトークンを返す
        self.mock_tokenizer_instance.tokenize.return_value = [MagicMock(surface=concept, part_of_speech='名詞')]
        
        # 各エンジンは、"善" に対する探索結果を返す
        self.mock_hierarchy_engine.trace_upwards.return_value = ["道徳的概念", "価値"]
        # SymmetryEngineからは対称概念の名前だけを取得する（仮の仕様）
        self.mock_symmetry_engine.get_symmetric_concept.return_value = "悪"
        self.mock_causal_engine.trace_causality.return_value = {"causes": [], "effects": ["幸福"]}

        # 2. 期待されるJSON出力
        expected_json = {
            "main_concepts": {
                "善": {
                    "raw_concept": "善",
                    "hierarchy": ["道徳的概念", "価値"],
                    "symmetry": "悪",
                    "causality": {"causes": [], "effects": ["幸福"]}
                }
            },
            "query": query_text
        }

        # 3. メソッド実行
        result = self.retriever.retrieve(query_text)

        # 4. 検証
        assert result == expected_json
        
        # 各エンジンが正しい概念で呼び出されたことを確認
        self.mock_hierarchy_engine.trace_upwards.assert_called_once_with(concept)
        self.mock_symmetry_engine.get_symmetric_concept.assert_called_once_with(concept)
        self.mock_causal_engine.trace_causality.assert_called_once_with(concept)