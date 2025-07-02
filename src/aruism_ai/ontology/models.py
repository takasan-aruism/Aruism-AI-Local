######################################################################
# Aruism AI Project - Ontological Data Models
# バージョン: 2.3 (多軸階層対応版)
######################################################################
from dataclasses import dataclass, field
from typing import Dict, Optional, List

@dataclass
class Concept:
    concept_id: str
    canonical_name_ja: str
    symbol: Optional[str] = None
    category: Optional[str] = None
    canonical_name_en: Optional[str] = None
    description_ja: Optional[str] = None
    description_en: Optional[str] = None
    wordnet_synset_id: Optional[str] = None
    source_of_data: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """dataclassを辞書に変換する（None値や空のリストは除外）"""
        return {k: v for k, v in self.__dict__.items() if v is not None and v != []}

@dataclass
class Relationship:
    source_concept_id: str
    target_concept_id: str
    relationship_type: str
    strength: Optional[float] = None
    source_of_data: Optional[str] = None

    def to_dict(self) -> Dict:
        """dataclassを辞書に変換する（None値は除外）"""
        return {k: v for k, v in self.__dict__.items() if v is not None}

@dataclass
class AxisNode:
    """階層構造の「軸」を表すノード"""
    axis_id: str  # 例: "temporal_conditions"
    name: str     # 例: "時間的条件"

    def to_dict(self) -> Dict:
        return self.__dict__

@dataclass
class LevelNode:
    """階層内の各レベルを表すノード"""
    level_id: str        # 例: "temporal_conditions_M0001_1"
    name_ja: str         # 例: "生成性"
    name_en: str         # 例: "The creative principle of becoming"
    reasoning: str       # _aru_connectionなどの理由説明をJSON文字列として格納

    def to_dict(self) -> Dict:
        return self.__dict__