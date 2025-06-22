######################################################################
# Aruism AI Project - Basic Language Pattern Engine
#
# バージョン: 0.6 (方法要求パターン追加)
# 作成日: 2025-06-22
######################################################################

import re

class PatternEngine:
    def __init__(self):
        """
        パターンエンジンを初期化し、正規表現パターンをコンパイルする。
        """
        self.patterns = [
            {
                "pattern_id": "definition_what_is_x",
                "regex": re.compile(r"(.+?)とは何か？"),
                "slots": ["X"]
            },
            {
                "pattern_id": "comparison_x_and_y",
                "regex": re.compile(r"(.+?)と(.+?)の違いは？"),
                "slots": ["X", "Y"]
            },
            {
                "pattern_id": "example_request_of_x",
                "regex": re.compile(r"(.+?)の例を教えて"),
                "slots": ["X"]
            },
            {
                "pattern_id": "reason_why_is_x_y",
                "regex": re.compile(r"なぜ(.+?)は(.+?)のですか？"),
                "slots": ["X", "Y"]
            },
            # ▼▼▼ [新機能] 「方法要求パターン」をここに追加 ▼▼▼
            {
                "pattern_id": "how_to_do_y_to_x",
                "regex": re.compile(r"(.+?)を(.+?する)にはどうすればいいですか？"),
                "slots": ["X", "Y"]
            },
            {
                "pattern_id": "is_x_y_question",
                "regex": re.compile(r"(.+?)は(.+?)ですか？"),
                "slots": ["X", "Y"]
            },
            # (is_x_y_question パターンの最後の }, の後に追加)
            {
                "pattern_id": "statement_x_is_y",
                "regex": re.compile(r"(.+?)は(.+?)です"),
                "slots": ["X", "Y"]
            },
            # (statement_x_is_y パターンの最後の }, の後に追加)
            {
                "pattern_id": "possession_y_of_x",
                "regex": re.compile(r"(.+?)の(.+)"),
                "slots": ["X", "Y"]
            },
            # (possession_y_of_x パターンの最後の }, の後に追加)
            {
                "pattern_id": "command_do_y_to_x",
                "regex": re.compile(r"(.+?)を(.+?)して"),
                "slots": ["X", "Y"]
            },
            # (command_do_y_to_x パターンの最後の }, の後に追加)
            {
                "pattern_id": "causation_y_by_x",
                "regex": re.compile(r"(.+?)によって(.+)"),
                "slots": ["X", "Y"]
            },
            # (causation_y_by_x パターンの最後の }, の後に追加)
            {
                "pattern_id": "conditional_if_x_then_y",
                "regex": re.compile(r"もし(.+?)ならば、?(.+)"),
                "slots": ["X", "Y"]
            },
        ]

    def match(self, text: str) -> dict | None:
        """
        与えられたテキストにマッチする最初のパターンを探し、結果を返す。
        """
        for pattern in self.patterns:
            match = pattern["regex"].fullmatch(text.strip())
            
            if match:
                captured_groups = match.groups()
                matches = dict(zip(pattern["slots"], captured_groups))
                
                return {
                    "pattern_id": pattern["pattern_id"],
                    "matches": matches
                }
        
        return None