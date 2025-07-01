# src/aruism_ai/automation/run_hierarchy_generation.py

import os
import sys
import json
import logging
import argparse
import re
import requests
import subprocess

# --- プロジェクトのパス設定 ---
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(PROJECT_ROOT)

from aruism_ai.ontology.db_manager import GraphDBManager

# --- 定数定義 ---
DRAFT_DIR = os.path.join(PROJECT_ROOT, "data/drafts")
LLAMA_API_URL = os.environ.get("LLAMA_API_URL", "http://aristo-engine:8080/completion")
UPDATER_SCRIPT_PATH = os.path.join(PROJECT_ROOT, "src/aruism_ai/bootstrapping/hierarchy_updater.py")


class GenerationOrchestrator:
    def __init__(self, db_manager: GraphDBManager):
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

## REASONING REQUIREMENTS:

### For Axis Selection:
Explain WHY you chose each axis:
- What unique aspect of 新/古 does this axis reveal?
- How does it differ from other axes?
- Why is it essential for understanding this concept pair?

### For Level 1 (Most Critical):
1. State the philosophical principle
2. Explain its connection to 「ある」
3. Justify why this captures the essence of 新 or 古
4. Show how it relates to its symmetric counterpart

### For Level Progression:
Explain the resonance between levels:
- How does each level emerge from the previous?
- Why this specific progression?
- How does abstraction become concrete?

### For Symmetry:
At each level, explain how 新 and 古:
- Define each other
- Transform into each other
- Create meaning through their relationship

## THE 40-AXIS FRAMEWORK:

{axis_description_text}

## OUTPUT FORMAT (WITH EMBEDDED REASONING):

{{
  "axis_name": {{
    "_axis_selection_reason": "I selected this axis because...",
    "_philosophical_approach": "The fundamental insight guiding this hierarchy is...",
    
    "新": {{
      "1": {{
        "concept": "生成性 (Generativity)",
        "english": "The creative principle of becoming",
        "_aru_connection": "This relates to 「ある」 as its dynamic unfolding...",
        "_why_this_essence": "This captures the essence of 新 because...",
        "_resonance_to_next": "From this principle emerges..."
      }},
      "2": {{
        "concept": "創発 (Emergence)",
        "english": "The arising of novel properties",
        "_why_this_follows": "This emerges from generativity because...",
        "_resonance_to_next": "This manifestation leads to..."
      }}
      // Continue for all levels with reasoning
    }},
    
    "古": {{
      "1": {{
        "concept": "存在性 (Existentiality)",
        "english": "The established principle of being",
        "_aru_connection": "This relates to 「ある」 as its stable manifestation...",
        "_why_this_essence": "This captures the essence of 古 because...",
        "_complementarity": "This complements 生成性 by..."
      }}
      // Parallel structure with reasoning
    }},
    
    "_symmetry_explanation": "In this axis, 新 and 古 represent...",
    "_overall_insight": "This hierarchy reveals that..."
  }}
  // Repeat for each selected axis
}}

## QUALITY CRITERIA:

Your reasoning should demonstrate:
1. **Philosophical Depth**: Not surface associations but deep structural insights
2. **Logical Coherence**: Clear progression from abstract to concrete
3. **Aruism Alignment**: Every choice reflects Aruism principles
4. **Originality**: Fresh perspectives, not clichéd oppositions
5. **Practical Wisdom**: Philosophy that illuminates reality

## TAKE YOUR TIME:
This is philosophical archaeology. Dig deep. Think carefully. 
Your reasoning is more important than the categories themselves.
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
                "Show how 新 and 古 dance together in the eternal choreography of existence.\n\n"
                "Begin with a brief meditation on what 新 and 古 mean in the context of 「ある」."
            )
        else:
            user_prompt = (
                f"Create philosophically reasoned hierarchies for: '{pair_info['axis1']}'\n\n"
                "Select 4 axes that reveal different dimensions of this concept. "
                "Provide complete hierarchies with reasoning, showing how this concept "
                "manifests from its connection to 「ある」 down to concrete reality.\n\n"
                "Begin with a contemplation of this concept's essential nature."
            )
        
        return f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n{system_prompt}<|eot|><|start_header_id|>user<|end_header_id|>\n{user_prompt}<|eot|><|start_header_id|>assistant<|end_header_id|>\n"

    def _call_llama_api(self, prompt: str):
        """LlamaサーバーのAPIを呼び出し、応答からJSONを抽出する"""
        headers = {"Content-Type": "application/json"}
        data = {
            "prompt": prompt,
            "n_predict": 8192,  # 理由説明のため大幅に増加
            "temperature": 0.4,
            "stream": False
        }
        
        logging.info(f"思考エンジン ({LLAMA_API_URL}) にAPIリクエストを送信します。")
        try:
            response = requests.post(LLAMA_API_URL, headers=headers, json=data, timeout=600)
            logging.info(f"API応答ステータスコード: {response.status_code}")
            response.raise_for_status()
            
            api_response_data = response.json()
            content = api_response_data.get("content", "")
            
            if not content:
                raise ValueError("API returned empty content.")

            return self._extract_json_from_output(content)

        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Llama API call failed: {e}")
        except (json.JSONDecodeError, ValueError) as e:
            logging.error(f"Failed to decode or extract JSON from API response: {e}")
            logging.error(f"Received text: {response.text if 'response' in locals() else 'N/A'}")
            raise

    def _extract_json_from_output(self, output: str):
        """AIの出力からJSONを抽出する"""
        logging.debug(f"Attempting to extract JSON from: {output}")
        match = re.search(r'\{.*\}', output, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError as e:
                raise ValueError(f"Could not parse extracted JSON: {e}\nOriginal text: {output}")
        raise ValueError(f"Could not find valid JSON in the output:\n{output}")

    def _validate_hierarchy_depths(self, draft_data: dict):
        """生成された階層の深度を検証"""
        validation_report = []
        for axis_name, axis_data in draft_data.items():
            if axis_name.startswith("_"):  # メタデータはスキップ
                continue
                
            # 軸の正規化
            expected_depth = None
            for key, info in self.axis_structure.items():
                if info["name"] in axis_name or axis_name in info["name"]:
                    expected_depth = info["depth"]
                    break
            
            if expected_depth:
                for concept, hierarchy in axis_data.items():
                    if concept.startswith("_"):  # メタデータはスキップ
                        continue
                    actual_depth = len([k for k in hierarchy.keys() if not k.startswith("_")])
                    if actual_depth != expected_depth:
                        validation_report.append(
                            f"軸 '{axis_name}' の '{concept}': "
                            f"期待される深度 {expected_depth}, 実際の深度 {actual_depth}"
                        )
        
        return validation_report

    def _extract_reasoning_summary(self, draft_data: dict):
        """理由説明の要約を抽出"""
        summary = []
        for axis_name, axis_data in draft_data.items():
            if axis_name.startswith("_"):
                continue
            if "_axis_selection_reason" in axis_data:
                summary.append(f"【{axis_name}】{axis_data['_axis_selection_reason'][:100]}...")
        return summary

    def execute_workflow(self, start_concept_id: str, auto_approve: bool = False):
        """自動化ワークフロー全体を実行する"""
        try:
            pair_info = self._get_concept_pair_info(start_concept_id)
            prompt = self._generate_prompt(pair_info)
            logging.info("理由説明を核とした究極版プロンプトを生成しました。")

            logging.info("Llama 4に哲学的に深化した階層構造の起草を依頼します...")
            draft_data = self._call_llama_api(prompt)
            
            # 結果の分析
            axes_used = [k for k in draft_data.keys() if not k.startswith("_")]
            logging.info(f"AIが選択した軸: {axes_used}")
            
            # 理由説明の要約
            reasoning_summary = self._extract_reasoning_summary(draft_data)
            
            # 階層深度の検証
            validation_issues = self._validate_hierarchy_depths(draft_data)
            if validation_issues:
                print("\n【警告】階層深度の不一致が検出されました：")
                for issue in validation_issues:
                    print(f"  - {issue}")
            
            os.makedirs(DRAFT_DIR, exist_ok=True)
            draft_file_path = os.path.join(DRAFT_DIR, f"{start_concept_id}_reasoned_draft.json")
            with open(draft_file_path, 'w', encoding='utf-8') as f:
                json.dump(draft_data, f, ensure_ascii=False, indent=2)
            
            print("\n" + "="*50)
            print("AIによる哲学的階層構造（理由説明付き）の草案が生成されました。")
            print(f"使用された軸: {', '.join(axes_used)}")
            print(f"ファイルパス: {draft_file_path}")
            
            if reasoning_summary:
                print("\n【軸選択の理由（要約）】")
                for reason in reasoning_summary:
                    print(f"  {reason}")
            
            if not validation_issues:
                print("\n✓ 全ての軸で指定された階層深度が守られています。")
            print("="*50)
            
            # 理由説明を除いた簡潔な表示用データ
            display_data = {}
            for axis_name, axis_data in draft_data.items():
                if not axis_name.startswith("_"):
                    display_data[axis_name] = {}
                    for concept, hierarchy in axis_data.items():
                        if not concept.startswith("_"):
                            display_data[axis_name][concept] = {
                                k: v["concept"] if isinstance(v, dict) else v 
                                for k, v in hierarchy.items() 
                                if not k.startswith("_")
                            }
            
            print("\n【階層構造（理由説明は省略）】")
            print(json.dumps(display_data, ensure_ascii=False, indent=2))
            print("="*50)

            approval = 'y' if auto_approve else input("\nこの内容でデータベースを更新しますか？ (y/n): ").lower()

            if approval == 'y':
                logging.info("承認されました。データベースを更新します。")
                print("【注意】多軸階層のDB保存には新しい更新スクリプトが必要です。")
                
                # 暫定的に最初の軸のみ保存
                first_axis = axes_used[0] if axes_used else None
                if first_axis:
                    subprocess.run([
                        "python3", UPDATER_SCRIPT_PATH,
                        start_concept_id, draft_file_path, pair_info['axis1']
                    ], check=True)

                print("データベースの更新が完了しました。")
            else:
                print("処理は中断されました。")

        except Exception as e:
            logging.error(f"ワークフロー実行中にエラーが発生しました: {e}", exc_info=True)
            sys.exit(1)
if __name__ == '__main__':
    log_level_str = os.environ.get("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(level=log_level_str, format='%(asctime)s - %(levelname)s - %(message)s')

    parser = argparse.ArgumentParser(description="アリストAIの知識階層を半自動で生成・更新します。")
    parser.add_argument("start_concept_id", type=str, help="対象となるコンセプトのID (例: M0001)")
    parser.add_argument("--auto-approve", action="store_true", help="承認プロセスをスキップします。")
    args = parser.parse_args()

    db_manager = None
    try:
        NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD")
        if not NEO4J_PASSWORD:
            raise ValueError("環境変数 NEO4J_PASSWORD が設定されていません。")

        db_manager = GraphDBManager(
            uri="bolt://arism-db:7687",
            user="neo4j",
            password=NEO4J_PASSWORD
        )
        
        if db_manager.driver:
            orchestrator = GenerationOrchestrator(db_manager)
            orchestrator.execute_workflow(args.start_concept_id, args.auto_approve)
        else:
            logging.error("データベース接続に失敗しました。")
            
    except Exception as e:
        logging.error(f"実行エラー: {e}", exc_info=True)
    finally:
        if db_manager:
            db_manager.close()
            logging.info("データベース接続をクローズしました。")