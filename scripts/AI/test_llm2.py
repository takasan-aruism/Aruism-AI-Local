import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, AutoConfig
import time
import gc
import os
from datetime import datetime

# 本番テストプロンプト
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

def step1_check_environment():
    """Step 1: 環境チェック"""
    print("="*60)
    print("Step 1: 環境チェック")
    print("="*60)
    
    # CUDA確認
    print(f"CUDA利用可能: {torch.cuda.is_available()}")
    print(f"GPU数: {torch.cuda.device_count()}")
    
    for i in range(torch.cuda.device_count()):
        props = torch.cuda.get_device_properties(i)
        print(f"\nGPU {i}: {props.name}")
        print(f"  総メモリ: {props.total_memory / 1024**3:.1f}GB")
        print(f"  現在の使用量: {torch.cuda.memory_allocated(i) / 1024**3:.1f}GB")
    
    return torch.cuda.is_available() and torch.cuda.device_count() >= 2

def step2_load_model():
    """Step 2: モデルロード（診断と同じ設定）"""
    print("\n" + "="*60)
    print("Step 2: モデルロード")
    print("="*60)
    
    model_path = "/workspace/engine/qwen/Qwen3-32B"
    
    try:
        # 設定を確認
        print("設定を読み込み中...")
        config = AutoConfig.from_pretrained(model_path, local_files_only=True)
        print(f"✅ モデルサイズ: {config.num_hidden_layers}層")
        
        # 診断で成功した設定でロード
        print("\nモデルをロード中...")
        print("（診断で成功したdevice_map='auto'を使用）")
        
        start_time = time.time()
        
        model = AutoModelForCausalLM.from_pretrained(
            model_path,
            device_map="auto",  # 診断で成功
            torch_dtype=torch.float16,  # 診断で成功
            trust_remote_code=True,
            local_files_only=True
        )
        
        load_time = time.time() - start_time
        print(f"✅ ロード完了！（{load_time:.1f}秒）")
        
        # メモリ状況
        print("\nGPUメモリ使用状況:")
        for i in range(torch.cuda.device_count()):
            allocated = torch.cuda.memory_allocated(i) / 1024**3
            print(f"  GPU {i}: {allocated:.1f}GB使用")
        
        return model
        
    except Exception as e:
        print(f"❌ エラー: {str(e)}")
        return None

def step3_batch8_test(model):
    """Step 3: バッチサイズ8での本番試験"""
    print("\n" + "="*60)
    print("Step 3: バッチサイズ8での本番試験")
    print("="*60)
    
    model_path = "/workspace/engine/qwen/Qwen3-32B"
    
    # トークナイザー
    tokenizer = AutoTokenizer.from_pretrained(model_path, local_files_only=True)
    tokenizer.padding_side = "left"
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    
    batch_size = 8
    print(f"バッチサイズ: {batch_size}")
    print("本番プロンプトで試験を実行します...")
    
    try:
        # メッセージ形式に変換
        messages = [{"role": "user", "content": TEST_PROMPT}]
        text = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )
        
        # バッチ準備（8個）
        prompts = [text] * batch_size
        
        # トークン化
        inputs = tokenizer(
            prompts, 
            return_tensors="pt", 
            padding=True,
            truncation=True,
            max_length=2048
        )
        input_ids = inputs.input_ids.to(model.device)
        attention_mask = inputs.attention_mask.to(model.device)
        
        print(f"入力形状: {input_ids.shape}")
        print(f"入力トークン数: {input_ids.shape[1]}")
        
        # メモリチェック
        allocated = torch.cuda.memory_allocated(0) / 1024**3
        print(f"GPU0メモリ: {allocated:.1f}GB")
        
        # 推論
        print("\n🤖 推論を実行中...")
        torch.cuda.synchronize()
        start_time = time.time()
        
        with torch.inference_mode():
            outputs = model.generate(
                input_ids,
                attention_mask=attention_mask,
                max_new_tokens=1500,  # 十分な長さ
                temperature=0.7,
                top_p=0.95,
                do_sample=True,
                pad_token_id=tokenizer.pad_token_id,
                use_cache=True,
                repetition_penalty=1.1
            )
        
        torch.cuda.synchronize()
        inference_time = time.time() - start_time
        
        # 最初の応答のみデコード
        response = tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # プロンプト部分を除去
        if text in response:
            response = response.split(text)[-1].strip()
        
        # 統計計算
        total_output_tokens = 0
        for i in range(batch_size):
            output_length = outputs[i].shape[0] - input_ids.shape[1]
            total_output_tokens += output_length
        
        avg_output_tokens = total_output_tokens / batch_size
        tokens_per_second = total_output_tokens / inference_time
        
        print(f"\n✅ 推論完了!")
        print(f"  時間: {inference_time:.2f}秒")
        print(f"  総出力トークン数: {total_output_tokens}")
        print(f"  平均出力トークン数: {avg_output_tokens:.1f}")
        print(f"  速度: {tokens_per_second:.1f} tokens/秒")
        
        # 結果の分析
        print("\n📊 応答の分析:")
        analyze_response(response)
        
        # 結果を保存
        save_results(response, inference_time, total_output_tokens, tokens_per_second, batch_size)
        
        return tokens_per_second
        
    except Exception as e:
        print(f"  ❌ エラー: {str(e)}")
        import traceback
        traceback.print_exc()
        return 0

def analyze_response(response):
    """応答の分析"""
    has_thinking = "【思考プロセス】" in response
    has_structure = "【概念構造】" in response
    has_chemical = False
    
    print(f"  思考プロセス: {'✅' if has_thinking else '❌'}")
    print(f"  概念構造: {'✅' if has_structure else '❌'}")
    
    if has_structure:
        lines = response.split('\n')
        for line in lines:
            if line.strip().startswith("5."):
                print(f"  階層5の内容: {line.strip()}")
                chemicals = ["カフェイン", "クロロゲン酸", "トリゴネリン", 
                           "caffeine", "chlorogenic acid", "trigonelline"]
                for chem in chemicals:
                    if chem.lower() in line.lower():
                        has_chemical = True
                        break
    
    print(f"  階層5に化学物質: {'✅' if has_chemical else '❌'}")

def save_results(response, time_taken, tokens, speed, batch_size):
    """結果の保存"""
    filename = "output_qwen3_32b.txt"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(f"モデル: Qwen3-32B (フル精度)\n")
        f.write(f"生成時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"バッチサイズ: {batch_size}\n")
        f.write(f"生成時間: {time_taken:.2f}秒\n")
        f.write(f"総出力トークン数: {tokens}\n")
        f.write(f"速度: {speed:.1f} tokens/秒\n")
        f.write("="*60 + "\n\n")
        f.write(response)
    
    print(f"\n💾 結果を {filename} に保存しました")

def main():
    """メイン関数"""
    print("🔬 Qwen3-32B 本番試験（バッチサイズ8）")
    print(f"実行時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Step 1: 環境チェック
    if not step1_check_environment():
        print("\n❌ GPU環境に問題があります")
        return
    
    # メモリクリア
    torch.cuda.empty_cache()
    gc.collect()
    
    # Step 2: モデルロード
    model = step2_load_model()
    if model is None:
        print("\n❌ モデルロードに失敗しました")
        return
    
    # Step 3: バッチ8での本番試験
    speed = step3_batch8_test(model)
    
    # 結果まとめ
    print("\n" + "="*60)
    print("📊 試験結果まとめ")
    print("="*60)
    print(f"\nバッチサイズ8での速度: {speed:.1f} tokens/秒")
    print(f"目標達成: {'✅' if speed >= 30 else '❌'} (目標: 30 tokens/秒)")
    
    print("\n✨ 試験完了！")
    print("他のモデル（QwQ-32B-AWQ, Qwen3-32B-AWQ）との比較が可能です。")

if __name__ == "__main__":
    main()