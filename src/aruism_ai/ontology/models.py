######################################################################
# Aruism AI Project - Ontological Data Models
# バージョン: 2.2 (最終整合性版)
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
        data = {k: v for k, v in self.__dict__.items() if v is not None and v != []}
        return data

@dataclass
class Relationship:
    source_concept_id: str
    target_concept_id: str
    relationship_type: str
    
    strength: Optional[float] = None # この行を追加
    source_of_data: Optional[str] = None

    def to_dict(self) -> Dict:
        """dataclassを辞書に変換する（None値は除外）"""
        return {k: v for k, v in self.__dict__.items() if v is not None}