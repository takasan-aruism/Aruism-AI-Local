#!/usr/bin/env python3
"""
CSV生成テストスクリプト（修正版）
概念ペアの動的指定に対応
"""

import os
import sys
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

# ペルソナ定義
PERSONAS = {
    "sage": {
        "en": """You are an ancient sage, wise in the ways of dualistic thinking and synthesis. 
Your role is to analyze conceptual oppositions and create meaningful hierarchies that bridge contradictions.
You speak with clarity and depth, revealing hidden connections between opposites.""",
        "ja": "あなたは古の賢者であり、二元論的思考と統合の道に精通しています。"
    },
    "philosopher": {
        "en": """You are a contemporary philosopher specializing in dialectical reasoning. 
Your expertise lies in identifying tensions between concepts and synthesizing them into higher-order frameworks.
You approach each analysis with rigorous logic and creative insight.""",
        "ja": "あなたは弁証法的推論を専門とする現代の哲学者です。"
    }
}

# CSVテストプロンプト（タスク指示部分）
CSV_TEST_PROMPT = """
## TASK: Concept Pair Analysis and Hierarchy Generation

You will analyze a pair of opposing concepts and generate hierarchical structures along multiple analytical axes.

### Instructions:

1. **Axis Selection**: From the following 8 predefined axes, select the 4 most relevant for analyzing the given concept pair:
   - Temporal (時間): Evolution and change over time
   - Spatial (空間): Physical and metaphorical space relationships  
   - Causal (因果): Cause-effect relationships and dependencies
   - Psychological (心理): Mental and emotional dimensions
   - Social (社会): Collective and interpersonal aspects
   - Logical (論理): Formal reasoning and structural relationships
   - Phenomenological (現象): Experiential and perceptual qualities
   - Ontological (存在): Fundamental nature of being and reality

2. **Hierarchy Generation**: For each selected axis, create a 10-level hierarchy:
   - Level 1: Most abstract synthesis of the concept pair
   - Levels 2-9: Progressive refinement and specification
   - Level 10: Most concrete manifestation

3. **CSV Format Requirements**:
   - Headers: Axis,Level,Concept_1,Synthesis,Concept_2,Explanation
   - 40 total rows (4 axes × 10 levels each)
   - Proper CSV formatting with comma separation
   - No extra whitespace or formatting characters

### Output Format:

Generate your response in two parts:

1. **Analysis Section**: Brief explanation of:
   - Why you selected these 4 axes
   - How each axis reveals different aspects of the concept pair
   - The synthesis approach for each axis

2. **CSV Section**: The complete 40-row CSV data with the exact headers specified above.

Begin your CSV section with:
```csv
Axis,Level,Concept_1,Synthesis,Concept_2,Explanation
```

Remember: Each row should progress from abstract (Level 1) to concrete (Level 10) within its axis.
"""

class CSVGenerationTester:
    """CSV生成タスクのテスト実行クラス（修正版）"""
    
    def __init__(self, concept_pair_info: Dict[str, str], persona_key: str = "sage"):
        """
        使用するペルソナと、分析対象の概念ペアを指定して初期化
        
        Args:
            concept_pair_info: 概念ペア情報を含む辞書
                - concept_1_name: 概念1の名前
                - concept_1_desc: 概念1の説明
                - concept_2_name: 概念2の名前
                - concept_2_desc: 概念2の説明
            persona_key: 使用するペルソナのキー
        """
        self.model_path = "/workspace/engine/qwen/QwQ-32B-AWQ"
        self.output_dir = Path("/workspace/AIgenerated")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.persona = PERSONAS[persona_key]
        self.concept_pair_info = concept_pair_info  # 概念ペア情報をインスタンス変数として保持
        self.persona_key = persona_key
        
        self.model = None
        self.tokenizer = None
        
        # GPU設定
        self._setup_environment()
    
    def _setup_environment(self):
        """環境設定"""
        os.environ["CUDA_VISIBLE_DEVICES"] = "0,1"
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        print(f"🖥️  GPU数: {torch.cuda.device_count()}")
    
    def load_model(self):
        """モデルとトークナイザーのロード"""
        print("🔧 モデルをロード中...")
        
        try:
            # テンソル並列設定
            from transformers import AutoConfig
            config = AutoConfig.from_pretrained(
                self.model_path,
                local_files_only=True,
                trust_remote_code=True
            )
            
            num_layers = config.num_hidden_layers
            mid_layer = num_layers // 2
            
            device_map = {"model.embed_tokens": 0}
            for i in range(mid_layer):
                device_map[f"model.layers.{i}"] = 0
            for i in range(mid_layer, num_layers):
                device_map[f"model.layers.{i}"] = 1
            device_map["model.norm"] = 1
            device_map["lm_head"] = 1
            
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_path,
                device_map=device_map,
                torch_dtype=torch.float16,
                trust_remote_code=True,
                local_files_only=True
            )
            
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_path,
                local_files_only=True,
                trust_remote_code=True
            )
            
            # パディング設定（バッチ処理用）
            self.tokenizer.padding_side = "left"
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
            
            print("✅ モデルロード完了")
            return True
            
        except Exception as e:
            print(f"❌ エラー: {str(e)}")
            return False
    
    def _prepare_prompt(self) -> str:
        """指定されたペルソナと概念ペア情報を使用して、最終的なプロンプトを組み立てる"""
        system_prompt = self.persona["en"]
        
        # AIへの具体的な「ユーザーからの依頼」メッセージを動的に生成
        user_message = (
            f"Your task is to analyze the following concept pair:\n"
            f"- **{self.concept_pair_info['concept_1_name']}**: {self.concept_pair_info['concept_1_desc']}\n"
            f"- **{self.concept_pair_info['concept_2_name']}**: {self.concept_pair_info['concept_2_desc']}\n\n"
            "Based on your analysis, select the 4 most relevant axes and generate the hierarchies "
            "according to the detailed instructions and CSV format."
        )
        
        # 最終的なプロンプト文字列を完成させる
        full_prompt = (
            f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n"
            f"{system_prompt}\n{CSV_TEST_PROMPT}<|eot_id|>"
            f"<|start_header_id|>user<|end_header_id|>\n"
            f"{user_message}<|eot_id|>"
            f"<|start_header_id|>assistant<|end_header_id|>\n"
        )
        return full_prompt
    
    def generate_response(self, max_new_tokens: int = 4096) -> Optional[List[str]]:
        """プロンプトに対する応答を生成（バッチサイズ8）"""
        if self.model is None:
            print("❌ モデルがロードされていません")
            return None
        
        batch_size = 8
        prompt = self._prepare_prompt()
        print(f"📝 プロンプト長: {len(prompt)} 文字")
        print(f"📊 バッチサイズ: {batch_size}")
        
        # バッチ用にプロンプトを複製
        prompts = [prompt] * batch_size
        
        # トークン化
        inputs = self.tokenizer(
            prompts,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=4096
        )
        
        input_ids = inputs.input_ids.to("cuda:0")
        attention_mask = inputs.attention_mask.to("cuda:0")
        
        print(f"🚀 バッチ生成開始 (最大 {max_new_tokens} トークン)")
        start_time = time.time()
        
        try:
            with torch.inference_mode():
                outputs = self.model.generate(
                    input_ids=input_ids,
                    attention_mask=attention_mask,
                    max_new_tokens=max_new_tokens,
                    temperature=0.2,
                    top_p=0.95,
                    do_sample=True,
                    pad_token_id=self.tokenizer.pad_token_id,
                    use_cache=True,
                    repetition_penalty=1.1
                )
            
            generation_time = time.time() - start_time
            
            # バッチの各応答をデコード
            responses = []
            for i in range(batch_size):
                response = self.tokenizer.decode(outputs[i], skip_special_tokens=True)
                # プロンプト部分を除去
                if prompt in response:
                    response = response.split(prompt)[-1].strip()
                responses.append(response)
            
            total_output_tokens = sum([(outputs[i].shape[0] - input_ids.shape[1]) for i in range(batch_size)])
            avg_output_tokens = total_output_tokens / batch_size
            tokens_per_second = total_output_tokens / generation_time
            
            print(f"✅ バッチ生成完了: {generation_time:.2f}秒")
            print(f"   総出力トークン: {total_output_tokens}")
            print(f"   平均出力トークン: {avg_output_tokens:.1f}")
            print(f"   速度: {tokens_per_second:.1f} tokens/秒")
            
            return responses
            
        except Exception as e:
            print(f"❌ 生成エラー: {str(e)}")
            return None
    
    def save_response(self, responses: List[str]) -> Path:
        """応答をファイルに保存（バッチ対応）"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # メタデータを含むJSONファイル（全バッチの結果）
        output_data = {
            "metadata": {
                "timestamp": timestamp,
                "model": "QwQ-32B-AWQ",
                "persona": self.persona_key,
                "concept_pair": self.concept_pair_info,
                "batch_size": len(responses)
            },
            "responses": responses
        }
        
        json_file = self.output_dir / f"csv_test_{timestamp}_batch.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        # 最初の応答をサンプルとして保存
        response = responses[0]
        txt_file = self.output_dir / f"csv_test_{timestamp}_sample.txt"
        with open(txt_file, 'w', encoding='utf-8') as f:
            f.write(f"Generated: {timestamp}\n")
            f.write(f"Concept Pair: {self.concept_pair_info['concept_1_name']} vs {self.concept_pair_info['concept_2_name']}\n")
            f.write(f"Batch Size: {len(responses)} (showing first response)\n")
            f.write("="*60 + "\n\n")
            f.write(response)
        
        # CSV部分を抽出して保存（最初の応答から）
        if "```csv" in response:
            csv_start = response.find("```csv") + 6
            csv_end = response.find("```", csv_start)
            if csv_end > csv_start:
                csv_content = response[csv_start:csv_end].strip()
                csv_file = self.output_dir / f"csv_test_{timestamp}.csv"
                with open(csv_file, 'w', encoding='utf-8') as f:
                    f.write(csv_content)
                print(f"📊 CSV保存: {csv_file}")
        
        print(f"💾 保存完了: {json_file}")
        return json_file
    
    def execute_test(self) -> Optional[Path]:
        """テストの実行"""
        print("="*60)
        print(f"🧪 CSV生成テスト開始")
        print(f"   概念ペア: {self.concept_pair_info['concept_1_name']} vs {self.concept_pair_info['concept_2_name']}")
        print(f"   ペルソナ: {self.persona_key}")
        print(f"   バッチサイズ: 8")
        print(f"   Temperature: 0.2")
        print("="*60)
        
        # モデルロード
        if not self.load_model():
            return None
        
        # 応答生成（バッチ）
        responses = self.generate_response()
        if responses is None:
            return None
        
        # 結果保存
        output_file = self.save_response(responses)
        
        print("\n✨ テスト完了！")
        return output_file


def main():
    """メイン実行関数"""
    # 今回テストする概念ペアの情報を定義
    concept_to_test = {
        "concept_1_name": "新",
        "concept_1_desc": "newness, novelty, becoming",
        "concept_2_name": "古", 
        "concept_2_desc": "oldness, tradition, being"
    }
    
    # インスタンス化の際に、テスト対象の情報を渡す
    tester = CSVGenerationTester(concept_pair_info=concept_to_test, persona_key="sage")
    output_file = tester.execute_test()
    
    if output_file:
        print(f"\n結果ファイル: {output_file}")
        
        # 他の概念ペアもテストする場合の例
        additional_tests = [
            {
                "concept_1_name": "光",
                "concept_1_desc": "light, illumination, clarity",
                "concept_2_name": "闇",
                "concept_2_desc": "darkness, shadow, mystery"
            },
            {
                "concept_1_name": "秩序",
                "concept_1_desc": "order, structure, harmony",
                "concept_2_name": "混沌",
                "concept_2_desc": "chaos, disorder, entropy"
            }
        ]
        
        # 追加テストを実行するかの確認
        if input("\n追加の概念ペアもテストしますか？ (y/n): ").lower() == 'y':
            for concept_pair in additional_tests:
                print(f"\n{'='*40}")
                tester = CSVGenerationTester(concept_pair_info=concept_pair, persona_key="philosopher")
                tester.execute_test()


if __name__ == "__main__":
    main()