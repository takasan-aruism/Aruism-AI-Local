######################################################################
# Aruism AI Project - Ontological Data Models
#
# バージョン: 2.0 (新DBスキーマ準拠版)
# 最終更新日: 2025-06-22
######################################################################

from dataclasses import dataclass, field
from typing import Dict, Optional, List

# [改名] MeaningID -> Concept
@dataclass
class Concept:
    """
    存在の核：すべてのユニークな概念（「存在」）を表すクラス。
    新DBスキーマに準拠した、リッチなプロパティを持つ。
    """
    concept_id: str
    canonical_name_ja: str
    
    symbol: Optional[str] = None
    category: Optional[str] = None
    # [新プロパティ] 
    canonical_name_en: Optional[str] = None
    description_ja: Optional[str] = None
    description_en: Optional[str] = None
    
    # WordNet連携用
    wordnet_synset_id: Optional[str] = None
    
    # アリズム哲学プロパティ
    abstraction_level: Optional[int] = None # 1=具体的, 5=抽象的
    aruism_category: Optional[str] = None   # 例: 感情, 物理法則
    resonance_potential: Optional[float] = None

    # メタデータ
    source: List[str] = field(default_factory=list) # "manual", "wordnet", "user"
    confidence: float = 1.0
    version: int = 1
    
    sentiment_positive: Optional[float] = None
    sentiment_negative: Optional[float] = None
@dataclass
class Relationship:
    """
    関係性の網：概念ノード間を結ぶエッジ（関係性）を定義するクラス。
    """
    source_concept_id: str
    target_concept_id: str
    relationship_type: str
    
    # [新プロパティ] 軸や強度などをリレーションシップに持たせる
    axis: Optional[str] = None
    strength: float = 1.0
    source_of_data: Optional[str] = None


# (Word, AxisDefinition, Userクラスは、今回の変更範囲では使用しないため、
#  簡潔にするため一旦コメントアウトまたは削除しても構いません。
#  ここでは、将来の拡張のために残しておきます。)

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