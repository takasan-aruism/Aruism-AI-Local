######################################################################
# Aruism AI Project - Unit Tests for Pattern Engine
#
# バージョン: 1.0
# 作成日: 2025-06-22
######################################################################
import pytest
from aruism_ai.reasoning.pattern_engine import PatternEngine

class TestPatternEngine:
    """PatternEngineのユニットテストクラス"""

    def test_matches_definition_pattern(self):
        """[正常系] 「Xとは何か？」という定義要求パターンにマッチするかテスト"""
        
        # 1. エンジンのインスタンスを作成
        engine = PatternEngine()
        
        # 2. テスト対象のテキスト
        text = "アリズムとは何か？"
        
        # 3. パターンマッチングを実行
        result = engine.match(text)
        
        # 4. 期待される結果
        expected = {
            "pattern_id": "definition_what_is_x",
            "matches": {"X": "アリズム"}
        }
        
        # 5. 結果を検証
        assert result is not None
        assert result == expected
    def test_matches_comparison_pattern(self):
        """[正常系] 「XとYの違いは？」という比較要求パターンにマッチするかテスト"""
        engine = PatternEngine()
        text = "「存在」と「ある」の違いは？"
        
        result = engine.match(text)
        
        expected = {
            "pattern_id": "comparison_x_and_y",
            "matches": {"X": "「存在」", "Y": "「ある」"}
        }
        
        assert result is not None
        assert result == expected

    def test_matches_example_request_pattern(self):
        """[正常系] 「Xの例を教えて」という具体例要求パターンにマッチするかテスト"""
        engine = PatternEngine()
        text = "存在の対等性の例を教えて"
        
        result = engine.match(text)
        
        expected = {
            "pattern_id": "example_request_of_x",
            "matches": {"X": "存在の対等性"}
        }
        
        assert result is not None
        assert result == expected
    # tests/reasoning/test_pattern_engine.py に追記

    def test_matches_why_question_pattern(self):
        """[正常系] 「なぜXはYなのですか？」という理由要求パターンにマッチするかテスト"""
        engine = PatternEngine()
        text = "なぜ空は青いのですか？"
        
        result = engine.match(text)
        
        expected = {
            "pattern_id": "reason_why_is_x_y",
            "matches": {"X": "空", "Y": "青い"}
        }
        
        assert result is not None
        assert result == expected

    def test_matches_how_to_do_y_to_x_pattern(self):
        """[正常系] 「XをYするにはどうすればいいですか？」という方法要求パターンにマッチするかテスト"""
        engine = PatternEngine()
        text = "アリズムを実践するにはどうすればいいですか？"
        
        result = engine.match(text)
        
        expected = {
            "pattern_id": "how_to_do_y_to_x",
            "matches": {"X": "アリズム", "Y": "実践する"}
        }
        
        assert result is not None
        assert result == expected
    def test_matches_is_x_y_pattern(self):
        """[正常系] 「XはYですか？」という肯定・否定要求パターンにマッチするかテスト"""
        engine = PatternEngine()
        text = "アリズムは哲学ですか？"
        
        result = engine.match(text)
        
        expected = {
            "pattern_id": "is_x_y_question",
            "matches": {"X": "アリズム", "Y": "哲学"}
        }
        
        assert result is not None
        assert result == expected
    def test_matches_is_x_y_statement_pattern(self):
        """[正常系] 「XはYです」という平叙文パターンにマッチするかテスト"""
        engine = PatternEngine()
        text = "アリズムは構造です"
        
        result = engine.match(text)
        
        expected = {
            "pattern_id": "statement_x_is_y",
            "matches": {"X": "アリズム", "Y": "構造"}
        }
        
        assert result is not None
        assert result == expected
    def test_matches_possession_pattern(self):
        """[正常系] 「XのY」という所有・属性パターンにマッチするかテスト"""
        engine = PatternEngine()
        text = "アリズムの対等性"
        
        result = engine.match(text)
        
        expected = {
            "pattern_id": "possession_y_of_x",
            "matches": {"X": "アリズム", "Y": "対等性"}
        }
        
        assert result is not None
        assert result == expected
    def test_matches_command_pattern(self):
        """[正常系] 「XをYして」という単純命令パターンにマッチするかテスト"""
        engine = PatternEngine()
        text = "アリズムを要約して"
        
        result = engine.match(text)
        
        expected = {
            "pattern_id": "command_do_y_to_x",
            "matches": {"X": "アリズム", "Y": "要約"}
        }
        
        assert result is not None
        assert result == expected
    def test_matches_causation_pattern(self):
        """[正常系] 「XによってY」という原因・手段パターンにマッチするかテスト"""
        engine = PatternEngine()
        text = "アリズムによって救われた"
        
        result = engine.match(text)
        
        expected = {
            "pattern_id": "causation_y_by_x",
            "matches": {"X": "アリズム", "Y": "救われた"}
        }
        
        assert result is not None
        assert result == expected
    def test_matches_conditional_pattern(self):
        """[正常系] 「もしXならばY」という条件節パターンにマッチするかテスト"""
        engine = PatternEngine()
        text = "もしアリズムを了解したならば、世界は変わる"
        
        result = engine.match(text)
        
        expected = {
            "pattern_id": "conditional_if_x_then_y",
            "matches": {"X": "アリズムを了解した", "Y": "世界は変わる"}
        }
        
        assert result is not None
        assert result == expected
