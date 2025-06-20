######################################################################
# Aruism AI Project - Frequency Provider
#
# このファイルは、テキストコーパスから単語の出現頻度を分析する
# 機能を定義します。
#
# バージョン: 0.1
# 作成日: 2025-06-18
######################################################################

import os
import sys
import re
from janome.tokenizer import Tokenizer
from collections import Counter

# プロジェクトのルートディレクトリをシステムパスに追加
sys.path.append(os.getcwd())

class FrequencyProvider:
    """
    テキストデータから単語の出現頻度を分析するクラス。
    """
    def __init__(self):
        self.tokenizer = Tokenizer()
        self.word_counts = Counter()
        print("FrequencyProviderが初期化されました。")

    def _cleanup_text(self, text: str) -> str:
        """
        青空文庫のテキストからルビや注釈などを除去する前処理。
        """
        text = re.sub(r'《.*?》', '', text) # ルビの削除
        text = re.sub(r'［＃.*?］', '', text) # 注釈の削除
        text = text.strip()
        return text

    def analyze_text_file(self, filepath: str):
        """
        指定されたテキストファイルを形態素解析し、単語の出現頻度をカウントします。
        :param filepath: 解析するテキストファイルのパス
        """
        print(f"\n--- テキストファイル「{os.path.basename(filepath)}」の頻度分析を開始します ---")
        try:
            with open(filepath, 'r', encoding='shift_jis') as f:
                text = self._cleanup_text(f.read())
            
            # 名詞、動詞、形容詞、副詞のみをカウント対象とする
            target_pos = ['名詞', '動詞', '形容詞', '副詞']
            
            tokens = self.tokenizer.tokenize(text)
            words = [
                token.base_form for token in tokens 
                if token.part_of_speech.split(',')[0] in target_pos
            ]
            
            self.word_counts.update(words)
            print(f"分析が完了しました。ユニーク単語数: {len(self.word_counts)}")

        except FileNotFoundError:
            print(f"エラー: ファイルが見つかりません。パス: {filepath}")
        except Exception as e:
            print(f"エラーが発生しました: {e}")

    def get_top_n_words(self, n=20):
        """
        出現頻度が高い上位n件の単語と、その回数を返します。
        """
        return self.word_counts.most_common(n)

# このファイルが直接実行された場合にのみ以下のコードが動きます（テスト用）
if __name__ == '__main__':
    # --- 設定 ---
    PROJECT_ROOT = os.getcwd()
    TEXT_FILE_PATH = os.path.join(PROJECT_ROOT, "data", "yumejuya.txt")
    
    # --- 実行 ---
    provider = FrequencyProvider()
    
    # テキストファイルを分析
    provider.analyze_text_file(TEXT_FILE_PATH)
    
    # 結果の表示
    top_words = provider.get_top_n_words(20)
    
    if top_words:
        print("\n--- 単語出現頻度トップ20 ---")
        for word, count in top_words:
            print(f"{word}: {count}回")