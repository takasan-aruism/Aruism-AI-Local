######################################################################
# Aruism AI Project - Ontological Data Models
#
# このファイルは、Aruism認知アーキテクチャの中核となるデータ構造を
# Pythonのクラスとして定義します。
#
# 参照ドキュメント: Aruism_AI_Project_11_Cognitive_Architecture_Design.txt
# バージョン: 0.1
# 作成日: 2025-06-16
######################################################################

from dataclasses import dataclass, field
from typing import Dict, Optional, List

@dataclass
class MeaningID:
    """
    存在の核：すべてのユニークな概念（「存在」）を表すクラス。
    知識グラフにおけるノードの基本単位。
    """
    meaning_id: str  # 例: "M5001", "M0001"。概念に対する言語に依存しない一意の識別子。
    canonical_name: Dict[str, str]  # 例: {"en": "Beauty", "ja": "美"}。主要言語での人間が読める名称。
    description: Dict[str, str]  # 例: {"ja": "うつくしいこと。きれいなこと。"}。概念の詳細な定義。
    aruism_principle_link: Optional[str] = None  # 例: "Symmetry_Pole_Positive"。哲学における役割を示すタグ（あれば）。
    is_abstract: bool = False  # 具体的な概念（例：「椅子」）と抽象的な概念（例：「正義」）を区別するフラグ。
    default_axis_values: Dict[str, float] = field(default_factory=dict)  # 各価値軸におけるベースラインスコア。
    external_identifiers: Dict[str, str] = field(default_factory=dict)  # WordNet, Wikidata等へのリンク。

@dataclass
class Word:
    """
    字句の平面：各言語の表層的な単語やフレーズと、それが指し示す概念（MeaningID）をマッピングするクラス。
    """
    word_text: str  # 実際の単語やフレーズ。例：「beautiful」、「麗しい」。
    language_code: str  # 言語コード。例：「en」、「ja」。
    meaning_id: str  # この単語が指し示す概念のMeaningID。
    part_of_speech: Optional[str] = None  # 品詞。例：「形容詞」、「名詞」。
    usage_context: Dict[str, str] = field(default_factory=dict)  # 用法に関するメタデータ。例: {"formality": "formal"}。

@dataclass
class AxisDefinition:
    """
    文脈のレンズ：「軸」を定義するクラス。
    これにより、階層性や価値観が条件的であることが表現される。
    """
    axis_id: str  # 軸の一意の識別子。例：「axis_beauty_ugliness」、「axis_corporate_authority」。
    axis_name: Dict[str, str]  # 人間が読める名称。
    axis_type: str  # "Value", "Categorical", "Functional"など。
    description: str  # この軸が何を表すかの説明。

@dataclass
class Relationship:
    """
    関係性の網：概念ノード間を結ぶエッジ（関係性）を定義するクラス。
    「連動性」を実装する。
    """
    source_meaning_id: str  # 関係の始点となるノードのMeaningID。
    target_meaning_id: str  # 関係の終点となるノードのMeaningID。
    relationship_type: str  # 関係性のタイプ。例：Symmetric_To, Is_A, Causes, Influences。
    valid_under_axis_id: Optional[str] = None  # この関係が特定の「軸」の条件下でのみ有効な場合に、そのAxis_IDを指定。
    strength: float = 1.0  # 関係の重みや強度。
    source_of_data: Optional[str] = None  # この関係性の情報源。例：「WordNet_Import」、「Arizm_Learned」。

@dataclass
class User:
    """
    ユーザー自身を表すクラス。主観性の基点となる。
    """
    user_id: str  # ユーザーの一意の識別子 (例: 'タカさん')
    # 将来的に、表示名などの他のプロパティも追加可能