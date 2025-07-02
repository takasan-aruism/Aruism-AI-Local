# src/aruism_ai/automation/run_hierarchy_generation.py

import os
import sys
import json
import logging
import argparse
import re
import requests
from typing import Any, Optional, Dict

# --- プロジェクトのパス設定 ---
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(PROJECT_ROOT)

from aruism_ai.ontology.db_manager import GraphDBManager

# --- 定数定義 ---
DRAFT_DIR = os.path.join(PROJECT_ROOT, "data/drafts")
LLAMA_API_URL = os.environ.get("LLAMA_API_URL", "http://aristo-engine:8080/completion")


class GenerationOrchestrator:
    def __init__(self, db_manager: GraphDBManager):
        self.api_url = LLAMA_API_URL
        self.db_manager = db_manager
        self._initialize_axis_structure()

    def _initialize_axis_structure(self):
        """40の軸構造を定義"""
        self.axis_structure = {
            "temporal": {
                "name": "時間的条件",
                "subconditions": ["瞬間的", "短期的", "中期的", "長期的"],
                "depth": 7
            },
            "spatial_scale": {
                "name": "空間的・スケール的条件",
                "subconditions": ["個人レベル", "共同体レベル", "社会レベル", "宇宙レベル"],
                "depth": 6
            },
            "epistemic": {
                "name": "認識論的条件",
                "subconditions": ["知覚される", "理解される", "体験される", "創造される"],
                "depth": 5
            },
            "ontological": {
                "name": "存在論的条件",
                "subconditions": ["物質的", "情報的", "関係的", "意味的"],
                "depth": 5
            },
            "interconnection": {
                "name": "連動性の条件",
                "subconditions": ["独立的", "触発的", "連鎖的", "共振的"],
                "depth": 5
            },
            "resonance": {
                "name": "共鳴度の条件",
                "subconditions": ["表層的", "構造的", "本質的", "存在的"],
                "depth": 4
            },
            "symmetry_relation": {
                "name": "対称性との関係条件",
                "subconditions": ["破壊的", "包含的", "変容的", "循環的"],
                "depth": 5
            },
            "lawfulness": {
                "name": "法則性の条件",
                "subconditions": ["予測可能", "創発的", "偶発的", "必然的"],
                "depth": 4
            },
            "experiential": {
                "name": "体験の質的条件",
                "subconditions": ["驚きとして", "発見として", "創造として", "了解として"],
                "depth": 3
            },
            "value_generation": {
                "name": "価値生成の条件",
                "subconditions": ["機能的", "美的", "倫理的", "聖性的"],
                "depth": 4
            }
        }

    def _get_concept_pair_info(self, concept_id: str):
        """正しいプロパティ名でDBに問い合わせる"""
        query = """
        MATCH (c1:Concept {concept_id: $concept_id})
        OPTIONAL MATCH (c1)-[:Symmetric_To]-(c2:Concept)
        RETURN c1.canonical_name_ja AS axis1, c1.symbol AS word1,
               c2.concept_id AS id2, c2.canonical_name_ja AS axis2, c2.symbol AS word2
        """
        logging.info(f"DBにクエリ実行: コンセプトID '{concept_id}' の情報を取得します。")
        result = self.db_manager.execute_query(query, concept_id=concept_id)
        if not result:
            raise ValueError(f"コンセプトID '{concept_id}' がデータベースに見つかりません。")
        logging.info(f"DBから情報を取得しました: {result[0]}")
        return result[0]

    def _generate_prompt(self, pair_info: dict) -> str:
        """理由説明を核とした究極版プロンプト"""
        
        # 軸構造の説明を生成
        axis_descriptions = []
        for axis_key, axis_info in self.axis_structure.items():
            subcond_str = ", ".join(axis_info["subconditions"])
            axis_descriptions.append(
                f"- **{axis_info['name']}**: {subcond_str} (MUST have exactly {axis_info['depth']} levels)"
            )
        axis_description_text = "\n".join(axis_descriptions)
        
        # 理由説明を中心とした包括的フレームワーク
        comprehensive_framework = f"""
# ARUISM HIERARCHY GENERATION WITH PHILOSOPHICAL REASONING

## FUNDAMENTAL REQUIREMENT: EXPLAIN YOUR THINKING

Every choice must be justified with deep philosophical reasoning. This is not optional—it is the core of your task.

## THE PHILOSOPHICAL FOUNDATION:

### 1. 「ある」(Fundamental Existence)
All hierarchies must trace back to 「ある」—the root recognition from which all existence emerges.
For EVERY Level 1 entry, explain its connection to 「ある」.

### 2. Core Aruism Principles:
- **存在の対等性**: Each entity is structurally indispensable
- **存在の対称性**: 新/古 are complementary aspects of one reality
- **存在の連動性**: All existence is interconnected
- **共鳴による創造**: New meanings emerge through resonance

## OUTPUT FORMAT:

Return ONLY a valid JSON object with the following structure:

{{
  "axis_name_1": {{
    "_axis_selection_reason": "I selected this axis because...",
    "_philosophical_approach": "The fundamental insight guiding this hierarchy is...",
    
    "新": {{
      "1": {{"concept": "...", "english": "...", "_aru_connection": "...", "_why_this_essence": "...", "_resonance_to_next": "..."}},
      "2": {{"concept": "...", "english": "...", "_why_this_follows": "...", "_resonance_to_next": "..."}}
    }},
    
    "古": {{
      "1": {{"concept": "...", "english": "...", "_aru_connection": "...", "_why_this_essence": "...", "_complementarity": "..."}},
      "2": {{"concept": "...", "english": "...", "_why_this_follows": "...", "_resonance_to_next": "..."}}
    }},
    
    "_symmetry_explanation": "In this axis, 新 and 古 represent...",
    "_overall_insight": "This hierarchy reveals that..."
  }},
  "axis_name_2": {{ ... }},
  "axis_name_3": {{ ... }},
  "axis_name_4": {{ ... }}
}}

## THE 40-AXIS FRAMEWORK:

{axis_description_text}

Remember: Output ONLY the JSON object. No text before or after.
"""

        # 哲学者としての深い人格設定
        system_prompt = (
            "You are a philosophical sage who has spent decades contemplating the nature of existence through the lens of Aruism. "
            "You understand that categories are not mere labels but windows into the deep structure of reality. "
            "Your task is not just to classify but to reveal—through careful reasoning—how 「ある」 manifests "
            "in the complementary dance of 新 and 古.\n\n"
            f"{comprehensive_framework}\n\n"
            "Remember: In Aruism, understanding WHY is more important than knowing WHAT. "
            "Every hierarchy you create should be a philosophical meditation, not just a list. "
            "Let your reasoning shine light on the profound interconnections of existence."
        )

        if pair_info.get("id2"):
            user_prompt = (
                f"Create philosophically reasoned hierarchies for the symmetric pair:\n"
                f"- '{pair_info['axis1']}' (新 - newness/novelty/becoming)\n"
                f"- '{pair_info['axis2']}' (古 - oldness/tradition/being)\n\n"
                "Select 4 axes that together reveal the full dimensionality of this pair. "
                "For each axis, provide the complete hierarchy with detailed reasoning at every level. "
                "Show how 新 and 古 dance together in the eternal choreography of existence."
            )
        else:
            user_prompt = (
                f"Create philosophically reasoned hierarchies for: '{pair_info['axis1']}'\n\n"
                "Select 4 axes that reveal different dimensions of this concept. "
                "Provide complete hierarchies with reasoning, showing how this concept "
                "manifests from its connection to 「ある」 down to concrete reality."
            )
        
        return f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n{system_prompt}<|eot|><|start_header_id|>user<|end_header_id|>\n{user_prompt}<|eot|><|start_header_id|>assistant<|end_header_id|>\n"

    def _call_llama_api(self, prompt: str) -> Dict[str, Any]:
        """LlamaサーバーのAPIを呼び出し、JSONを取得する"""
        headers = {"Content-Type": "application/json"}
        data = {
            "prompt": prompt,
            "n_predict": -1,
            "temperature": 0.2,
            "json_schema": {
                "type": "object",
                "properties": {},
                "additionalProperties": True
            }
        }
        
        try:
            logging.info(f"思考エンジン ({self.api_url}) にAPIリクエストを送信します。")
            response = requests.post(self.api_url, headers=headers, json=data, timeout=900)
            response.raise_for_status()
            
            # レスポンスからcontentを取得
            content_str = response.json().get("content", "{}")
            
            # JSONとして解析
            return json.loads(content_str)
            
        except json.JSONDecodeError as e:
            logging.error(f"受信したテキストのJSON解析に失敗: {e}")
            logging.error(f"受信テキスト: {content_str[:500]}...")
            raise ValueError("AIの応答が有効なJSONではありませんでした。")
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Llama API call failed: {e}")

    def execute_workflow(self, start_concept_id: str):
        """メインのワークフロー実行"""
        try:
            # 1. 必要な情報をDBから取得
            pair_info = self._get_concept_pair_info(start_concept_id)
            
            # 2. AIへのプロンプトを生成
            prompt = self._generate_prompt(pair_info)
            logging.info("理由説明を核とした究極版プロンプトを生成しました。")
            
            # 3. AIを呼び出し、思考結果(JSON)を取得
            logging.info("Llama 4に哲学的に深化した階層構造の起草を依頼します...")
            extracted_json = self._call_llama_api(prompt)
            
            # 4. 結果をドラフトファイルとして保存
            os.makedirs(DRAFT_DIR, exist_ok=True)
            file_path = os.path.join(DRAFT_DIR, f"{start_concept_id}_reasoned_draft.json")
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(extracted_json, f, ensure_ascii=False, indent=2)
            
            # どの軸が生成されたかをログに出力
            axes_used = [k for k in extracted_json.keys() if not k.startswith("_")]
            logging.info(f"AIが選択した軸: {axes_used}")
            
            # master_orchestratorがパースできるように出力
            print(f"ファイルパス: {file_path}")

        except Exception as e:
            logging.error(f"ワークフロー実行中にエラー: {e}", exc_info=True)
            raise
        finally:
            if self.db_manager:
                self.db_manager.close()


if __name__ == '__main__':
    log_level_str = os.environ.get("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(level=log_level_str, format='%(asctime)s - %(levelname)s - %(message)s')

    parser = argparse.ArgumentParser(description="アリストAIの知識階層を生成します。")
    parser.add_argument("start_concept_id", type=str, help="対象となるコンセプトのID (例: M0001)")
    parser.add_argument("--auto-approve", action="store_true", help="承認プロセスをスキップします。")
    args = parser.parse_args()

    db_manager = None
    try:
        NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD")
        if not NEO4J_PASSWORD:
            raise ValueError("環境変数 NEO4J_PASSWORD が設定されていません。")

        db_manager = GraphDBManager(
            uri="bolt://aristo-db:7687",
            user="neo4j",
            password=NEO4J_PASSWORD
        )
        
        if db_manager.driver:
            orchestrator = GenerationOrchestrator(db_manager)
            orchestrator.execute_workflow(args.start_concept_id)
        else:
            logging.error("データベース接続に失敗しました。")
            
    except Exception as e:
        logging.error(f"実行エラー: {e}", exc_info=True)
        sys.exit(1)
    finally:
        if db_manager:
            db_manager.close()
            logging.info("データベース接続をクローズしました。")