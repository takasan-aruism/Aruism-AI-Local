######################################################################
# Aruism AI Project - Aruistic Retriever
#
# バージョン: 0.2 (retrieveアルゴリズム実装)
# 最終更新日: 2025-06-22
######################################################################

from janome.tokenizer import Tokenizer
from aruism_ai.reasoning.hierarchy_engine import HierarchyEngine
from aruism_ai.reasoning.symmetry_engine import SymmetryEngine
from aruism_ai.reasoning.causal_engine import CausalEngine

class AruisticRetriever:
    # (__init__ は変更なし)
    def __init__(self, hierarchy_engine: HierarchyEngine, symmetry_engine: SymmetryEngine, causal_engine: CausalEngine):
        self.tokenizer = Tokenizer()
        self.hierarchy_engine = hierarchy_engine
        self.symmetry_engine = symmetry_engine
        self.causal_engine = causal_engine

    def retrieve(self, query_text: str) -> dict:
        """
        クエリテキストを解析し、関連する構造化情報を返す。
        """
        # ▼▼▼ [新機能] ここからが新しいアルゴリズムです ▼▼▼
        
        # 1. テキストから主要概念（名詞）を抽出
        tokens = self.tokenizer.tokenize(query_text)
        main_concepts_text = list(dict.fromkeys(
            [token.surface for token in tokens if token.part_of_speech.startswith('名詞')]
        ))

        retrieved_data = {}
        # 2. 抽出された各概念について、思考エンジン群で情報を収集
        for concept in main_concepts_text:
            hierarchy = self.hierarchy_engine.trace_upwards(concept)
            symmetry = self.symmetry_engine.get_symmetric_concept(concept)
            causality = self.causal_engine.trace_causality(concept)
            
            retrieved_data[concept] = {
                "raw_concept": concept,
                "hierarchy": hierarchy,
                "symmetry": symmetry,
                "causality": causality
            }

        # 3. 最終的なJSON構造を組み立てて返す
        return {
            "main_concepts": retrieved_data,
            "query": query_text
        }