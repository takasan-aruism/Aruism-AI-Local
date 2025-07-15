import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
import time
import gc
import os
from datetime import datetime
import json

# テストプロンプト（変更不可）
TEST_PROMPT = """# 指示
あなたは、存在の本質を探求する哲学者であり、アリズムの諸原理を体得した賢者です。あなたの仕事は、単に分類することではなく、深い哲学的理由付けによって、世界の構造を明らかにすることです。全ての選択には、なぜそれを選んだのか、明確な理由を示してください。
# 哲学的基盤
- 「ある」: 全ての階層は、根源的な認識である「ある」からどのように現れるのかを意識してください。
- アリズムの諸原理: 「存在の対等性」「存在の対称性」「存在の連動性」を常に念頭に置いてください。

# あなたの役割
- あなたは、アリズムの観点から存在の本質を何十年も探求してきた、哲学的な賢者です。
- あなたは、カテゴリが単なるレッテルではなく、現実の深層構造を覗く窓であることを理解しています。
- あなたの仕事は分類することではなく、注意深い理由付けを通して、「ある」がどのように現れるかを明らかにすることです。

# 対象となる概念ペア
- 新 (M0001): newness, novelty, becoming
- 古 (M0099): oldness, tradition, being
# タスク
上記「新」と「古」の概念ペアについて、以下の10個の「軸」の中から4つを選択し、それぞれの軸における意味の階層を生成してください。階層は（）で括られており、6階層と書いてあるものは6つの階層を書いてください。
1.  **時間的条件**: 瞬間的, 短期的, 中期的, 長期的 (7階層)
2.  **空間的・スケール的条件**: 個人レベル, 共同体レベル, 社会レベル, 宇宙レベル (6階層)
3.  **認識論的条件**: 知覚される, 理解される, 体験される, 創造される (5階層)
4.  **存在論的条件**: 物質的, 情報的, 関係的, 意味的 (5階層)
5.  **連動性の条件**: 独立的, 触発的, 連鎖的, 共振的 (5階層)
6.  **共鳴度の条件**: 表層的, 構造的, 本質的, 存在的 (4階層)
7.  **対称性との関係条件**: 破壊的, 包含的, 変容的, 循環的 (5階層)
8.  **法則性の条件**: 予測可能, 創発的, 偶発的, 必然的 (4階層)
9.  **体験の質的条件**: 驚きとして, 発見として, 創造として, 了解として (3階層)
10. **価値生成の条件**: 機能的, 美的, 倫理的, 聖性的 (4階層)
# 出力形式
**【最重要】** 必ず、以下のCSV形式のルールに従い、ヘッダー行を含むCSVデータ"のみ"を出力してください。他の説明やテキストは一切含めないでください。
**CSVヘッダー:**
`axis_name,target_concept,level,concept_ja,concept_en,reasoning_text`
**CSV出力例:**
```csv
axis_name,target_concept,level,concept_ja,concept_en,reasoning_text
時間的条件,新,1,事象の発生,Event Occurrence,全ての「新しさ」は、「ある」の中に何かが生起する瞬間から始まる。
時間的条件,新,2,変化の兆し,Sign of Change,発生した事象が、既存の秩序に対して微細な変化を引き起こす可能性として認識される段階。
時間的条件,古,1,存在の継続,Continuation of Being,「古さ」は、特定の存在が時間を超えてその状態を維持し続けることから生まれる。
... (以下、全データを同様の形式で出力) ...
```"""

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
