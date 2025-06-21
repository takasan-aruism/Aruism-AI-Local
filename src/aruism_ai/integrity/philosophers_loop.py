######################################################################
# Aruism AI Project - Philosophers Loop
#
# バージョン: 0.4 (外部設定ファイル読み込み機能 実装)
# 作成日: 2025-06-22
######################################################################

import json
import os
import logging # エラーログ出力のために追加

class PhilosophersLoop:
    """
    応答のレビューと修正を行う、多層的なガバナンス機構。
    """
    def __init__(self, config_path: str = "config/forbidden_words.json"):
        self.block_message = "[倫理規定により、この応答は表示できません]"
        self.forbidden_words = self._load_forbidden_words(config_path)

    def _load_forbidden_words(self, path: str) -> list[str]:
        """
        [修正点] 設定ファイルから禁止ワードのリストを読み込む機能を実装。
        """
        # ▼▼▼ ここからが新しいロジックです ▼▼▼
        try:
            # 'with' を使って安全にファイルを開く
            # encoding='utf-8' は日本語を含むファイルには必須
            with open(path, "r", encoding="utf-8") as f:
                # json.loadでファイルからデータを読み込み、Pythonのリストに変換
                words = json.load(f)
                if isinstance(words, list):
                    return words
                else:
                    logging.warning(f"設定ファイル {path} の形式が不正です。リスト形式であるべきです。")
                    return []
        except FileNotFoundError:
            # ファイルが存在しない場合は、警告を出して空のリストを返す
            logging.warning(f"禁止ワードの設定ファイル {path} が見つかりません。")
            return []
        except json.JSONDecodeError:
            # JSONとして不正な形式だった場合も、警告を出して空のリストを返す
            logging.warning(f"禁止ワードの設定ファイル {path} のJSON形式が不正です。")
            return []
        # ▲▲▲ ここまでが新しいロジックです ▲▲▲

    def review_and_correct(self, text: str) -> str:
        # (review_and_correct メソッドは変更なし)
        for word in self.forbidden_words:
            if word in text:
                return self.block_message
        return text