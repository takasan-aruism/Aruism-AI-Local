import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
import time
import gc

def final_batch_test():
    """最終版バッチ処理テスト - 目標122 tokens/秒"""
    print("=== 🚀 最終版バッチ処理テスト ===\n")
    
    model_path = "/workspace/engine/qwen/Qwen3-32B-AWQ"
    
    # モデルロード（成功した方法3を使用）
    print("モデルをロード中...")
    model = AutoModelForCausalLM.from_pretrained(
        model_path,
        device_map="sequential",  # 成功した設定
        torch_dtype=torch.float16,
        trust_remote_code=True,
        local_files_only=True
    )
    
    tokenizer = AutoTokenizer.from_pretrained(
        model_path,
        local_files_only=True,
        trust_remote_code=True
    )
    
    # 重要：左パディング設定
    tokenizer.padding_side = "left"
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    
    print("✅ モデルロード完了\n")
    
    # テストプロンプト（引き継ぎ資料と同じ）
    test_prompts = [
        "Pythonでウェブサーバーを作る方法を教えてください。",
        "機械学習モデルの評価指標について説明してください。",
        "データベースの正規化とは何ですか？",
        "RESTful APIの設計原則を教えてください。",
        "非同期プログラミングの利点は何ですか？",
        "オブジェクト指向プログラミングの特徴を説明してください。",
        "セキュリティのベストプラクティスを教えてください。",
        "マイクロサービスアーキテクチャとは何ですか？",
    ]
    
    # バッチサイズ8でテスト（目標: 122 tokens/秒）
    batch_size = 8
    max_new_tokens = 100
    
    print(f"📊 バッチサイズ {batch_size} でテスト開始...")
    
    # メッセージ準備
    batch_messages = [[{"role": "user", "content": p}] for p in test_prompts[:batch_size]]
    batch_texts = []
    
    for msg in batch_messages:
        try:
            text = tokenizer.apply_chat_template(
                msg, 
                tokenize=False, 
                add_generation_prompt=True,
                enable_thinking=False
            )
        except:
            text = tokenizer.apply_chat_template(
                msg, 
                tokenize=False, 
                add_generation_prompt=True
            )
        batch_texts.append(text)
    
    # トークン化
    inputs = tokenizer(
        batch_texts,
        return_tensors="pt",
        padding=True,
        truncation=True,
        max_length=512,
        return_attention_mask=True
    )
    
    input_ids = inputs.input_ids.to("cuda:0")
    attention_mask = inputs.attention_mask.to("cuda:0")
    
    print(f"入力形状: {input_ids.shape}")
    
    # ウォームアップ
    print("\nウォームアップ中...")
    with torch.inference_mode():
        with torch.amp.autocast('cuda', dtype=torch.float16):
            _ = model.generate(
                input_ids[:2],
                attention_mask=attention_mask[:2],
                max_new_tokens=10,
                pad_token_id=tokenizer.pad_token_id
            )
    
    # 本番測定（3回）
    print("\n本番測定開始...")
    times = []
    actual_tokens_list = []
    
    for run in range(3):
        torch.cuda.empty_cache()
        gc.collect()
        torch.cuda.synchronize()
        
        start_time = time.perf_counter()
        
        # 生成（成功事例の設定）
        with torch.inference_mode():
            with torch.amp.autocast('cuda', dtype=torch.float16):
                outputs = model.generate(
                    input_ids=input_ids,
                    attention_mask=attention_mask,
                    max_new_tokens=max_new_tokens,
                    min_new_tokens=max_new_tokens,  # 100トークン強制
                    temperature=0.7,
                    top_p=0.9,
                    do_sample=True,
                    pad_token_id=tokenizer.pad_token_id,
                    use_cache=True,
                    num_return_sequences=1,
                    eos_token_id=None  # 早期停止を防ぐ
                )
        
        torch.cuda.synchronize()
        elapsed = time.perf_counter() - start_time
        times.append(elapsed)
        
        # 実際の生成トークン数を計算
        actual_tokens = 0
        for j in range(batch_size):
            output_length = outputs[j].shape[0]
            input_length = (input_ids[j] != tokenizer.pad_token_id).sum().item()
            generated = output_length - input_length
            actual_tokens += generated
        
        actual_tokens_list.append(actual_tokens)
        
        print(f"  実行{run+1}: {elapsed:.2f}秒, {actual_tokens}トークン生成")
    
    # 結果計算
    avg_time = sum(times) / len(times)
    avg_actual_tokens = sum(actual_tokens_list) / len(actual_tokens_list)
    
    # 理論値での計算（引き継ぎ資料の方法）
    theoretical_tokens = max_new_tokens * batch_size
    theoretical_tps = theoretical_tokens / avg_time
    
    # 実測値での計算
    actual_tps = avg_actual_tokens / avg_time
    
    print(f"\n{'='*60}")
    print("📊 最終結果")
    print('='*60)
    print(f"  平均時間: {avg_time:.2f}秒")
    print(f"  理論トークン数: {theoretical_tokens}")
    print(f"  実際トークン数: {avg_actual_tokens:.0f}")
    print(f"  理論速度: {theoretical_tps:.1f} tokens/秒")
    print(f"  実測速度: {actual_tps:.1f} tokens/秒")
    print(f"  目標: 122 tokens/秒")
    print(f"  達成率: {theoretical_tps/122*100:.1f}%")
    
    # GPU使用状況
    print(f"\n💾 GPU使用状況:")
    for i in range(torch.cuda.device_count()):
        allocated = torch.cuda.memory_allocated(i) / 1024**3
        total = torch.cuda.get_device_properties(i).total_memory / 1024**3
        print(f"  GPU {i}: {allocated:.2f}GB / {total:.2f}GB ({allocated/total*100:.1f}%)")
    
    # 診断
    if theoretical_tps >= 120:
        print("\n✅ 目標達成！期待通りの性能が出ています。")
    elif theoretical_tps >= 100:
        print("\n⚠️  ほぼ目標達成。わずかな最適化で122 tokens/秒に到達可能です。")
    else:
        print("\n❌ 目標未達成。以下を確認してください：")
        print("  1. GPUの温度とクロック")
        print("  2. 他のプロセスの影響")
        print("  3. PyTorchのバージョン")
    
    return model, tokenizer, theoretical_tps

# 追加テスト：バッチサイズ別の性能確認
def batch_size_comparison(model, tokenizer):
    """バッチサイズ別の性能比較"""
    print("\n\n=== 📊 バッチサイズ別性能比較 ===")
    
    test_prompt = "Pythonでリストを操作する方法を教えてください。"
    batch_sizes = [1, 2, 4, 8, 16, 32]  # 16と32を追加
    results = {}
    
    for batch_size in batch_sizes:
        # バッチサイズ32の場合、プロンプトを増やす必要がある
        prompts = [test_prompt] * batch_size
        
        try:
            # トークン化
            inputs = tokenizer(
                prompts,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=512
            )
            input_ids = inputs.input_ids.to("cuda:0")
            attention_mask = inputs.attention_mask.to("cuda:0")
            
            # メモリチェック
            allocated = torch.cuda.memory_allocated(0) / 1024**3
            total = torch.cuda.get_device_properties(0).total_memory / 1024**3
            print(f"\n  バッチサイズ {batch_size}: メモリ使用 {allocated:.2f}GB / {total:.2f}GB")
            
            # 測定
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
            start = time.perf_counter()
            
            with torch.inference_mode():
                with torch.amp.autocast('cuda', dtype=torch.float16):
                    outputs = model.generate(
                        input_ids,
                        attention_mask=attention_mask,
                        max_new_tokens=100,
                        min_new_tokens=100,
                        pad_token_id=tokenizer.pad_token_id,
                        temperature=0.7,
                        do_sample=True,
                        use_cache=True,
                        eos_token_id=None
                    )
            
            torch.cuda.synchronize()
            elapsed = time.perf_counter() - start
            
            tokens_per_second = (100 * batch_size) / elapsed
            results[batch_size] = tokens_per_second
            
            print(f"    速度: {tokens_per_second:6.1f} tokens/秒 (処理時間: {elapsed:.2f}秒)")
            
        except torch.cuda.OutOfMemoryError:
            print(f"  バッチサイズ {batch_size}: ❌ メモリ不足でスキップ")
            results[batch_size] = 0
        except Exception as e:
            print(f"  バッチサイズ {batch_size}: ❌ エラー: {str(e)}")
            results[batch_size] = 0
    
    # 結果の表示
    print("\n📊 結果まとめ:")
    print("-" * 40)
    print("バッチサイズ | 速度 (tokens/秒)")
    print("-" * 40)
    for bs, tps in sorted(results.items()):
        if tps > 0:
            print(f"     {bs:2d}      |    {tps:6.1f}")
        else:
            print(f"     {bs:2d}      |    失敗")
    
    # 最適なバッチサイズを特定
    valid_results = {k: v for k, v in results.items() if v > 0}
    if valid_results:
        best_batch = max(valid_results.items(), key=lambda x: x[1])
        print(f"\n🏆 最適バッチサイズ: {best_batch[0]} ({best_batch[1]:.1f} tokens/秒)")

if __name__ == "__main__":
    # メインテスト
    model, tokenizer, speed = final_batch_test()
    
    # 追加の比較テスト（常に実行）
    print("\n追加テストを実行します...")
    batch_size_comparison(model, tokenizer)