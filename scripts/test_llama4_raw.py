# force_dual_gpu.py
import os
import torch
import vllm

if __name__ == "__main__":
    # 明示的に両GPUを指定
    os.environ["CUDA_VISIBLE_DEVICES"] = "0,1"
    
    # GPUの確認
    print(f"利用可能なGPU数: {torch.cuda.device_count()}")
    
    if torch.cuda.device_count() < 2:
        print("警告: 2つのGPUが認識されていません！")
        print("Docker起動コマンドを確認してください:")
        print("docker run --gpus all ...")  # または --gpus '"device=0,1"'
        exit(1)
    
    # 両GPUのメモリ合計を確認
    total_memory = 0
    for i in range(torch.cuda.device_count()):
        mem = torch.cuda.get_device_properties(i).total_memory
        total_memory += mem
        print(f"GPU {i}: {mem/1e9:.1f} GB")
    
    print(f"\n合計GPUメモリ: {total_memory/1e9:.1f} GB")
    
    if total_memory/1e9 < 60:  # 64GBより少ない
        print("警告: 期待されるメモリ容量と一致しません！")
    
    MODEL_ID = "meta-llama/Llama-4-Scout-17B-16E-Instruct"
    
    # 両GPU使用を強制
    llm = vllm.LLM(
        model=MODEL_ID,
        trust_remote_code=True,
        tensor_parallel_size=2,  # 必ず2を指定
        pipeline_parallel_size=1,
        max_model_len=32768,  # 64GBなら余裕
        gpu_memory_utilization=0.85,
        kv_cache_dtype="fp8",
        dtype="half",
        disable_custom_all_reduce=True
    )
    
    print("\n両GPU使用でモデルロード成功！")