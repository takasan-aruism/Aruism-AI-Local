import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
import time
import gc
import os

def setup_tensor_parallel():
    """テンソル並列の環境設定"""
    # NCCLデバッグ情報を有効化
    os.environ["NCCL_DEBUG"] = "INFO"
    os.environ["CUDA_VISIBLE_DEVICES"] = "0,1"
    
    # GPUの確認
    print(f"利用可能なGPU数: {torch.cuda.device_count()}")
    for i in range(torch.cuda.device_count()):
        print(f"  GPU {i}: {torch.cuda.get_device_name(i)}")
    print()

def final_batch_test_tensor_parallel():
    """テンソル並列版バッチ処理テスト"""
    print("=== 🚀 テンソル並列版バッチ処理テスト ===\n")
    
    setup_tensor_parallel()
    
    model_path = "/workspace/engine/qwen/Qwen3-32B-AWQ"
    
    # テンソル並列用のdevice_map設定
    # モデルを2つのGPUに分散
    device_map = {
        "model.embed_tokens": 0,
        "model.layers.0": 0,
        "model.layers.1": 0,
        "model.layers.2": 0,
        "model.layers.3": 0,
        "model.layers.4": 0,
        "model.layers.5": 0,
        "model.layers.6": 0,
        "model.layers.7": 0,
        "model.layers.8": 0,
        "model.layers.9": 0,
        "model.layers.10": 0,
        "model.layers.11": 0,
        "model.layers.12": 0,
        "model.layers.13": 0,
        "model.layers.14": 0,
        "model.layers.15": 0,
        "model.layers.16": 1,
        "model.layers.17": 1,
        "model.layers.18": 1,
        "model.layers.19": 1,
        "model.layers.20": 1,
        "model.layers.21": 1,
        "model.layers.22": 1,
        "model.layers.23": 1,
        "model.layers.24": 1,
        "model.layers.25": 1,
        "model.layers.26": 1,
        "model.layers.27": 1,
        "model.layers.28": 1,
        "model.layers.29": 1,
        "model.layers.30": 1,
        "model.layers.31": 1,
        "model.norm": 1,
        "lm_head": 1,
    }
    
    # モデルロード（テンソル並列設定）
    print("テンソル並列でモデルをロード中...")
    try:
        # オプション1: 自動device_map
        model = AutoModelForCausalLM.from_pretrained(
            model_path,
            device_map="auto",  # 自動でGPUに分散
            torch_dtype=torch.float16,
            trust_remote_code=True,
            local_files_only=True,
            offload_folder="/tmp/offload",
            offload_state_dict=False,
            max_memory={0: "15GB", 1: "15GB"}  # 各GPUの最大メモリ
        )
    except:
        # オプション2: 手動device_map
        print("自動device_mapが失敗。手動設定を試行...")
        model = AutoModelForCausalLM.from_pretrained(
            model_path,
            device_map=device_map,
            torch_dtype=torch.float16,
            trust_remote_code=True,
            local_files_only=True
        )
    
    # モデルの配置を確認
    print("\nモデルの配置:")
    for name, param in model.named_parameters():
        print(f"  {name}: GPU {param.device}")
        if "layers.16" in name:  # 最初の分割点だけ表示
            break
    
    tokenizer = AutoTokenizer.from_pretrained(
        model_path,
        local_files_only=True,
        trust_remote_code=True
    )
    
    # 重要：左パディング設定
    tokenizer.padding_side = "left"
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    
    print("✅ テンソル並列モデルロード完了\n")
    
    # テストプロンプト（32個用意）
    test_prompts = [
        "Pythonでウェブサーバーを作る方法を教えてください。",
        "機械学習モデルの評価指標について説明してください。",
        "データベースの正規化とは何ですか？",
        "RESTful APIの設計原則を教えてください。",
        "非同期プログラミングの利点は何ですか？",
        "オブジェクト指向プログラミングの特徴を説明してください。",
        "セキュリティのベストプラクティスを教えてください。",
        "マイクロサービスアーキテクチャとは何ですか？",
        "Dockerコンテナの基本的な使い方を教えてください。",
        "GitとGitHubの違いは何ですか？",
        "SQLとNoSQLデータベースの違いを説明してください。",
        "機械学習と深層学習の違いは何ですか？",
        "HTTPとHTTPSの違いを教えてください。",
        "クラウドコンピューティングの利点は何ですか？",
        "アジャイル開発手法について説明してください。",
        "ブロックチェーン技術の仕組みを教えてください。",
    ] * 2  # 32個にするため2倍
    
    # バッチサイズ32でテスト
    batch_size = 32
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
    
    # GPU使用状況（開始時）
    print(f"\n💾 GPU使用状況（開始時）:")
    for i in range(torch.cuda.device_count()):
        allocated = torch.cuda.memory_allocated(i) / 1024**3
        total = torch.cuda.get_device_properties(i).total_memory / 1024**3
        print(f"  GPU {i}: {allocated:.2f}GB / {total:.2f}GB ({allocated/total*100:.1f}%)")
    
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
        
        # 生成
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
    
    # 理論値での計算
    theoretical_tokens = max_new_tokens * batch_size
    theoretical_tps = theoretical_tokens / avg_time
    
    # 実測値での計算
    actual_tps = avg_actual_tokens / avg_time
    
    print(f"\n{'='*60}")
    print("📊 最終結果（テンソル並列）")
    print('='*60)
    print(f"  平均時間: {avg_time:.2f}秒")
    print(f"  理論トークン数: {theoretical_tokens}")
    print(f"  実際トークン数: {avg_actual_tokens:.0f}")
    print(f"  理論速度: {theoretical_tps:.1f} tokens/秒")
    print(f"  実測速度: {actual_tps:.1f} tokens/秒")
    print(f"  単一GPU比較: 438.0 tokens/秒（参考値）")
    print(f"  性能向上率: {theoretical_tps/438.0*100:.1f}%")
    
    # GPU使用状況（終了時）
    print(f"\n💾 GPU使用状況（終了時）:")
    for i in range(torch.cuda.device_count()):
        allocated = torch.cuda.memory_allocated(i) / 1024**3
        total = torch.cuda.get_device_properties(i).total_memory / 1024**3
        print(f"  GPU {i}: {allocated:.2f}GB / {total:.2f}GB ({allocated/total*100:.1f}%)")
    
    return model, tokenizer, theoretical_tps

# 追加テスト：バッチサイズ別の性能確認（テンソル並列版）
def batch_size_comparison_tensor_parallel(model, tokenizer):
    """テンソル並列でのバッチサイズ別性能比較"""
    print("\n\n=== 📊 テンソル並列バッチサイズ別性能比較 ===")
    
    test_prompt = "Pythonでリストを操作する方法を教えてください。"
    batch_sizes = [8, 16, 32, 48, 64]  # より大きなバッチサイズも試す
    results = {}
    
    for batch_size in batch_sizes:
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
            print(f"\n  バッチサイズ {batch_size}:")
            for i in range(torch.cuda.device_count()):
                allocated = torch.cuda.memory_allocated(i) / 1024**3
                total = torch.cuda.get_device_properties(i).total_memory / 1024**3
                print(f"    GPU {i}: {allocated:.2f}GB / {total:.2f}GB")
            
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
    print("\n📊 テンソル並列結果まとめ:")
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
    # テンソル並列版テスト
    model, tokenizer, speed = final_batch_test_tensor_parallel()
    
    # 追加の比較テスト
    print("\n追加テストを実行します...")
    batch_size_comparison_tensor_parallel(model, tokenizer)