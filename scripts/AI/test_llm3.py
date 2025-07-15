#!/usr/bin/env python3
"""
【簡素化版】Aruism AI CSV Generation Test Script
"""

import os
import sys
import logging
import requests
from datetime import datetime

# --- 定数定義 ---
LLAMA_API_URL = os.environ.get("LLAMA_API_URL", "http://aristo-engine:8080/completion")
CSV_TEST_PROMPT = """# 指示
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

def main():
    """スクリプトのメイン実行部"""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    logging.info("=== 簡素化版 CSV生成テスト開始 ===")

    # 1. プロンプトの準備
    system_prompt = "You are a philosophical sage. Output ONLY valid CSV data as specified."
    full_prompt = (
        f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n"
        f"{system_prompt}<|eot|>"
        f"<|start_header_id|>user<|end_header_id|>\n"
        f"{CSV_TEST_PROMPT}<|eot|>"
        f"<|start_header_id|>assistant<|end_header_id|>\n"
    )

    # 2. AIへのリクエスト
    try:
        logging.info(f"AIエンジン ({LLAMA_API_URL}) にリクエストを送信します...")
        response = requests.post(
            LLAMA_API_URL,
            headers={"Content-Type": "application/json"},
            json={
                "prompt": full_prompt,
                "n_predict": 8192,
                "temperature": 0.2,
                "stop": ["<|eot|>", "<|end_of_text|>"]
            },
            timeout=1800  # 30分
        )
        response.raise_for_status()
        logging.info("AIからの応答を受信しました。")

        csv_content = response.json().get("content", "").strip()

        # 3. CSVファイルへの保存
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"M0001_M0099_hierarchy_{timestamp}.csv"
        
        # スクリプトと同じディレクトリに保存
        script_dir = os.path.dirname(os.path.abspath(__file__))
        output_path = os.path.join(script_dir, output_filename)

        with open(output_path, 'w', encoding='utf-8', newline='') as f:
            f.write(csv_content)

        logging.info(f"CSVファイルを保存しました: {output_path}")
        print(f"テスト成功。出力ファイル: {output_path}")

    except requests.exceptions.RequestException as e:
        logging.error(f"AIエンジンへの接続に失敗しました: {e}")
        logging.error("`docker-compose ps`コマンドでaristo-engineコンテナが正常に起動しているか確認してください。")
        sys.exit(1)
    except Exception as e:
        logging.error(f"予期せぬエラーが発生しました: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()