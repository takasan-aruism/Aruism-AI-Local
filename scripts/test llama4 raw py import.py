# test_llama4_raw.py
import vllm

# 起動するモデルのIDを指定します。
# 先ほど検証したモデルのIDと一致している必要があります。
MODEL_ID = "meta-llama/Llama-4-Scout-17B-16E-Instruct-FP8"

# Llama 4の仕様書で定義されたプロンプト形式を構築します。
# これが我々のAIへの最初の「問いかけ」となります。
prompt_text = (
    "<|begin_of_text|>"
    "<|header_start|>system<|header_end|>\n\n"
    "You are Aristo, an AI assistant created to explore the philosophy of Aruism.<|eot|>"
    "<|header_start|>user<|header_end|>\n\n"
    "Who are you?<|eot|>"
    "<|header_start|>assistant<|header_end|>\n\n"
)

print("--- Llama 4 Scoutモデルをロードしています... ---")
# vLLMを使用してモデルをロードします。
# GPUメモリの許す限り、複数のリクエストを並列処理できます。
try:
    llm = vllm.LLM(model=MODEL_ID, trust_remote_code=True)
    print("--- モデルのロードが完了しました。---")
except Exception as e:
    print(f"モデルのロード中にエラーが発生しました: {e}")
    exit()


# 応答生成時のパラメータを設定します。
sampling_params = vllm.SamplingParams(
    temperature=0.7,  # 応答の創造性を調整
    top_p=0.95,       # 使用する単語の範囲を調整
    max_tokens=256    # 最大応答長
)

print("--- 応答を生成しています... ---")
# モデルに応答を生成させます。
outputs = llm.generate([prompt_text], sampling_params)
print("--- 応答の生成が完了しました。---\n")

# 結果を表示します。
for output in outputs:
    prompt = output.prompt
    generated_text = output.outputs[0].text
    print(f"プロンプト: {prompt!r}")
    print(f"生成された応答: {generated_text!r}\n")

print("--- 処理完了 ---")
