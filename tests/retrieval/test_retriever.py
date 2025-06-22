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
# tests/retrieval/test_retriever.py 内

    def test_retrieves_data_for_multiple_concepts(self):
        """[正常系] 複数の概念を含むクエリを正しく処理できるかテスト"""
        query_text = "善と悪の因果関係は？"
        
        # ▼▼▼ [修正点] Tokenizerが返すリストに「因果」「関係」を追加 ▼▼▼
        concepts = ["善", "悪", "因果", "関係"]
        self.mock_tokenizer_instance.tokenize.return_value = [
            MagicMock(surface=concepts[0], part_of_speech='名詞'),
            MagicMock(surface="と", part_of_speech='助詞'),
            MagicMock(surface=concepts[1], part_of_speech='名詞'),
            MagicMock(surface="の", part_of_speech='助詞'),
            MagicMock(surface=concepts[2], part_of_speech='名詞'),
            MagicMock(surface=concepts[3], part_of_speech='名詞'),
        ]
        
        # ▼▼▼ [修正点] 各エンジンが新しい概念にも対応できるように修正 ▼▼▼
        def hierarchy_side_effect(concept):
            return {"善": ["道徳的概念"], "悪": ["非道徳的概念"]}.get(concept, [])
        def symmetry_side_effect(concept):
            return {"善": "悪", "悪": "善"}.get(concept)
        def causality_side_effect(concept):
            return {
                "善": {"causes": [], "effects": ["幸福"]},
                "悪": {"causes": ["無知"], "effects": []}
            }.get(concept, {"causes": [], "effects": []}) # 未知の概念には空の情報を返す

        self.mock_hierarchy_engine.trace_upwards.side_effect = hierarchy_side_effect
        self.mock_symmetry_engine.get_symmetric_concept.side_effect = symmetry_side_effect
        self.mock_causal_engine.trace_causality.side_effect = causality_side_effect

        # ▼▼▼ [修正点] 期待されるJSONにも「因果」「関係」の項目を追加 ▼▼▼
        expected_json = {
            "main_concepts": {
                "善": {
                    "raw_concept": "善", "hierarchy": ["道徳的概念"], "symmetry": "悪",
                    "causality": {"causes": [], "effects": ["幸福"]}
                },
                "悪": {
                    "raw_concept": "悪", "hierarchy": ["非道徳的概念"], "symmetry": "善",
                    "causality": {"causes": ["無知"], "effects": []}
                },
                "因果": {
                    "raw_concept": "因果", "hierarchy": [], "symmetry": None,
                    "causality": {"causes": [], "effects": []}
                },
                "関係": {
                    "raw_concept": "関係", "hierarchy": [], "symmetry": None,
                    "causality": {"causes": [], "effects": []}
                }
            },
            "query": query_text
        }

        result = self.retriever.retrieve(query_text)
        assert result == expected_json