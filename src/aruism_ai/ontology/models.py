######################################################################
# Aruism AI Project - Ontological Data Models
#
# バージョン: 2.1 (プロパティ名修正版)
# 最終更新日: 2025-06-25
######################################################################

from dataclasses import dataclass, field
from typing import Dict, Optional, List

@dataclass
class Concept:
    """
    存在の核：すべてのユニークな概念（「存在」）を表すクラス。
    """
    concept_id: str
    canonical_name_ja: str
    
    symbol: Optional[str] = None
    category: Optional[str] = None
    canonical_name_en: Optional[str] = None
    description_ja: Optional[str] = None
    description_en: Optional[str] = None
    wordnet_synset_id: Optional[str] = None
    abstraction_level: Optional[int] = None
    aruism_category: Optional[str] = None
    resonance_potential: Optional[float] = None
    
    # 【変更点】プロパティ名を'source'から'source_of_data'に変更し、型もList[str]に統一
    source_of_data: List[str] = field(default_factory=list)
    
    confidence: float = 1.0
    version: int = 1
    sentiment_positive: Optional[float] = None
    sentiment_negative: Optional[float] = None

    def to_dict(self) -> Dict:
        """dataclassを辞書に変換する（None値は除外）"""
        return {k: v for k, v in self.__dict__.items() if v is not None}

@dataclass
class Relationship:
    """
    関係性の網：概念ノード間を結ぶエッジ（関係性）を定義するクラス。
    """
    source_concept_id: str
    target_concept_id: str
    relationship_type: str
    
    axis: Optional[str] = None
    strength: float = 1.0
    source_of_data: Optional[str] = None

    def to_dict(self) -> Dict:
        """dataclassを辞書に変換する（None値は除外）"""
        return {k: v for k, v in self.__dict__.items() if v is not None}

# (以下、他のクラスは変更なし)

@dataclass
class Word:
    # ... 変更なし ...
    pass

@dataclass
class AxisDefinition:
    # ... 変更なし ...
    pass

@dataclass
class User:
    # ... 変更なし ...
    pass