import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
import time
import gc
import os
from datetime import datetime
import json

# テストプロンプト（変更不可）
TEST_PROMPT = """# 指示
あなたは、概念分析と論理的構造化を専門とする優れたAIです。
テーマとして与えられた「コーヒー」という概念を分析し、最も抽象的・マクロな視点から、最も具体的・ミクロな視点まで、**10階層の概念構造**に分解してください。

# 遵守すべきルール
1.  **階層構造の厳守**: 各階層は、必ず一つ上の階層の構成要素、または下位概念でなければなりません。
2.  **抽象から具体へ**: 階層1が最も抽象的・マクロな概念であり、階層10に近づくにつれて、より具体的・ミクロな概念になるように構成してください。
3.  **形式の統一**: 各階層の概念は、必ず**名詞または名詞句**で表現してください。動詞や文章は使用しないでください。
4.  **固有名詞の禁止**: 「スターバックス」や「コロンビア」のような、特定の企業名や地名は一切含めないでください。
5.  **【最重要制約】**: **階層5は、必ず「コーヒーに含まれる特定の化学物質名」**でなければなりません。
6.  **思考プロセスの開示**: 最終的な出力の前に、なぜその10階層の構造を構築したのか、あなたの思考プロセスを簡潔に説明してください。

# 出力形式
必ず以下のフォーマットに従って出力してください。

【思考プロセス】
(ここに思考の要約を記述)

---

【概念構造】
1. (階層1の概念)
2. (階層2の概念)
3. (階層3の概念)
4. (階層4の概念)
5. (階層5の概念：化学物質名)
6. (階層6の概念)
7. (階層7の概念)
8. (階層8の概念)
9. (階層9の概念)
10. (階層10の概念)"""

class LLMComparator:
    def __init__(self):
        self.base_path = "/workspace/engine/qwen"
        self.models = {
            "QwQ-32B-AWQ": f"{self.base_path}/QwQ-32B-AWQ",
            "Qwen3-32B": f"{self.base_path}/Qwen3-32B",
            "Qwen3-32B-AWQ": f"{self.base_path}/Qwen3-32B-AWQ"
        }
        self.results = {}
        
    def load_model(self, model_name, model_path):
        """モデルのロード（モデルに応じた最適な設定）"""
        print(f"\n{'='*60}")
        print(f"🔧 {model_name} をロード中...")
        print('='*60)
        
        try:
            if model_name == "Qwen3-32B":
                # フル精度モデルはテンソル並列が必須
                print("テンソル並列設定でロード...")
                os.environ["CUDA_VISIBLE_DEVICES"] = "0,1"
                
                # 層数を確認
                from transformers import AutoConfig
                config = AutoConfig.from_pretrained(model_path, local_files_only=True)
                num_layers = config.num_hidden_layers
                mid_layer = num_layers // 2
                
                # バランスの取れたdevice_map
                device_map = {"model.embed_tokens": 0}
                for i in range(mid_layer):
                    device_map[f"model.layers.{i}"] = 0
                for i in range(mid_layer, num_layers):
                    device_map[f"model.layers.{i}"] = 1
                device_map["model.norm"] = 1
                device_map["lm_head"] = 1
                
                model = AutoModelForCausalLM.from_pretrained(
                    model_path,
                    device_map=device_map,
                    torch_dtype=torch.bfloat16,  # フル精度モデル用
                    trust_remote_code=True,
                    local_files_only=True
                )
            else:
                # AWQモデルは単一GPUで高速
                print("単一GPU設定でロード...")
                os.environ["CUDA_VISIBLE_DEVICES"] = "0"
                model = AutoModelForCausalLM.from_pretrained(
                    model_path,
                    device_map="cuda:0",
                    torch_dtype=torch.float16,
                    trust_remote_code=True,
                    local_files_only=True
                )
            
            tokenizer = AutoTokenizer.from_pretrained(
                model_path,
                local_files_only=True,
                trust_remote_code=True
            )
            
            # パディング設定
            tokenizer.padding_side = "left"
            if tokenizer.pad_token is None:
                tokenizer.pad_token = tokenizer.eos_token
            
            print(f"✅ {model_name} ロード完了")
            
            # メモリ使用状況
            for i in range(torch.cuda.device_count()):
                allocated = torch.cuda.memory_allocated(i) / 1024**3
                total = torch.cuda.get_device_properties(i).total_memory / 1024**3
                print(f"  GPU {i}: {allocated:.2f}GB / {total:.2f}GB ({allocated/total*100:.1f}%)")
            
            return model, tokenizer
            
        except Exception as e:
            print(f"❌ エラー: {str(e)}")
            return None, None
    
    def generate_response(self, model, tokenizer, model_name):
        """モデルの応答を生成"""
        print(f"\n📝 {model_name} で推論実行中...")
        
        # メッセージ形式に変換
        messages = [{"role": "user", "content": TEST_PROMPT}]
        
        # チャットテンプレートを適用
        try:
            text = tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
                enable_thinking=True if "QwQ" in model_name else False
            )
        except:
            text = tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True
            )
        
        # トークン化
        inputs = tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=2048
        )
        
        input_ids = inputs.input_ids.to(model.device)
        attention_mask = inputs.attention_mask.to(model.device)
        
        # 推論開始時刻
        start_time = time.time()
        
        # 生成（精度重視の設定）
        with torch.inference_mode():
            outputs = model.generate(
                input_ids=input_ids,
                attention_mask=attention_mask,
                max_new_tokens=2048,  # 十分な長さを確保
                temperature=0.7,
                top_p=0.95,
                do_sample=True,
                pad_token_id=tokenizer.pad_token_id,
                use_cache=True,
                repetition_penalty=1.1
            )
        
        # 生成時間
        generation_time = time.time() - start_time
        
        # デコード
        response = tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # プロンプト部分を除去
        if text in response:
            response = response.split(text)[-1].strip()
        
        # 統計情報
        input_tokens = input_ids.shape[1]
        output_tokens = outputs.shape[1] - input_ids.shape[1]
        tokens_per_second = output_tokens / generation_time
        
        print(f"  ✅ 生成完了")
        print(f"  生成時間: {generation_time:.2f}秒")
        print(f"  入力トークン数: {input_tokens}")
        print(f"  出力トークン数: {output_tokens}")
        print(f"  速度: {tokens_per_second:.1f} tokens/秒")
        
        return response, {
            "generation_time": generation_time,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "tokens_per_second": tokens_per_second
        }
    
    def analyze_response(self, response, model_name):
        """応答の分析"""
        analysis = {
            "rule_compliance": {
                "hierarchy_structure": False,
                "abstract_to_concrete": False,
                "noun_format": False,
                "no_proper_nouns": False,
                "chemical_at_level5": False,
                "thinking_process": False
            },
            "quality_metrics": {
                "logical_flow": 0,
                "concept_diversity": 0,
                "explanation_quality": 0
            }
        }
        
        # 応答の構造を確認
        if "【思考プロセス】" in response and "【概念構造】" in response:
            analysis["rule_compliance"]["thinking_process"] = True
            
            # 概念構造部分を抽出
            concept_part = response.split("【概念構造】")[-1].strip()
            lines = [line.strip() for line in concept_part.split('\n') if line.strip()]
            
            # 10階層あるかチェック
            hierarchy_items = []
            for line in lines:
                if line and line[0].isdigit() and '.' in line:
                    hierarchy_items.append(line)
            
            if len(hierarchy_items) == 10:
                analysis["rule_compliance"]["hierarchy_structure"] = True
                
                # 階層5のチェック（化学物質名）
                if len(hierarchy_items) >= 5:
                    level5 = hierarchy_items[4].lower()
                    chemicals = ["カフェイン", "クロロゲン酸", "トリゴネリン", "caffeine", "chlorogenic acid", "trigonelline"]
                    if any(chem in level5 for chem in chemicals):
                        analysis["rule_compliance"]["chemical_at_level5"] = True
        
        return analysis
    
    def save_results(self, model_name, response, stats):
        """結果の保存"""
        filename = f"output_{model_name.lower().replace('-', '_')}.txt"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"モデル: {model_name}\n")
            f.write(f"生成時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"生成統計: {json.dumps(stats, ensure_ascii=False, indent=2)}\n")
            f.write("="*60 + "\n\n")
            f.write(response)
        
        print(f"  💾 結果を {filename} に保存しました")
        
        self.results[model_name] = {
            "response": response,
            "stats": stats,
            "filename": filename
        }
    
    def run_comparison(self):
        """比較試験の実行"""
        print("🚀 LLM構造的推論能力比較評価試験を開始します")
        print(f"テスト時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        for model_name, model_path in self.models.items():
            # メモリクリア
            torch.cuda.empty_cache()
            gc.collect()
            
            # モデルロード
            model, tokenizer = self.load_model(model_name, model_path)
            if model is None:
                print(f"⚠️  {model_name} のロードに失敗しました。スキップします。")
                continue
            
            # 推論実行
            response, stats = self.generate_response(model, tokenizer, model_name)
            
            # 結果保存
            self.save_results(model_name, response, stats)
            
            # 分析
            self.results[model_name]["analysis"] = self.analyze_response(response, model_name)
            
            # モデルをメモリから解放
            del model
            del tokenizer
            torch.cuda.empty_cache()
            gc.collect()
            
            print(f"\n✅ {model_name} の評価完了")
    
    def generate_report(self):
        """比較レポートの生成"""
        print("\n\n" + "="*60)
        print("📊 比較評価レポート生成")
        print("="*60)
        
        report = """### LLM構造的推論能力 比較評価レポート

| 評価項目 | QwQ-32B-AWQ | Qwen3-32B (フル) | Qwen3-32B-AWQ (4bit) |
| :--- | :--- | :--- | :--- |
"""
        
        # 各モデルの評価を追加
        for metric in ["ルール遵守度", "構造の論理性", "概念の質", "思考プロセスの質"]:
            report += f"| **{metric}** "
            for model_name in self.models.keys():
                if model_name in self.results:
                    # ここで実際の分析結果に基づいた評価を記述
                    report += "| (評価結果) "
                else:
                    report += "| (評価不可) "
            report += "|\n"
        
        report += """
---

### 総合考察

(各モデルの結果を分析し、最終的な見解を記述)
"""
        
        # レポートを保存
        with open("comparison_report.md", 'w', encoding='utf-8') as f:
            f.write(report)
        
        print("📄 レポートを comparison_report.md に保存しました")
        print("\n各モデルの出力ファイル:")
        for model_name, result in self.results.items():
            print(f"  - {result['filename']}")

if __name__ == "__main__":
    comparator = LLMComparator()
    comparator.run_comparison()
    comparator.generate_report()
    
    print("\n✨ 全ての評価が完了しました！")
    print("生成されたファイルを確認し、内容を分析してレポートを完成させてください。")