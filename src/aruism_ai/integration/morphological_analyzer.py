######################################################################
# Aruism AI Project - Morphological Analyzer
#
# このファイルは、MeCabを使用して日本語テキストの形態素解析を行い、
# 概念抽出や正規化を提供する機能を定義します。
#
# バージョン: 0.1
# 作成日: 2025-06-22
######################################################################

import MeCab
from typing import List, Dict

class MorphologicalAnalyzer:
    """
    MeCabを使用した形態素解析エンジン
    """
    
    def __init__(self):
        mecab_config = "-r /opt/homebrew/etc/mecabrc -d /opt/homebrew/lib/mecab/dic/ipadic"
        self.tagger = MeCab.Tagger()
        print("MorphologicalAnalyzerが初期化されました。")
    
    def analyze(self, text: str) -> List[Dict[str, str]]:
        """
        テキストを形態素解析し、構造化されたデータを返す
        """
        result = self.tagger.parse(text)
        morphemes = []
        
        for line in result.split('\n'):
            if line == 'EOS' or not line:
                continue
                
            parts = line.split('\t')
            if len(parts) < 2:
                continue
                
            surface = parts[0]
            features = parts[1].split(',')
            
            morpheme = {
                'surface': surface,
                'pos': features[0],
                'pos_detail': features[1:6],
                'base_form': features[6] if len(features) > 6 else surface,
                'reading': features[7] if len(features) > 7 else '',
            }
            morphemes.append(morpheme)
            
        return morphemes
    
    def extract_concepts(self, text: str) -> List[Dict[str, str]]:
        """
        テキストから概念語（名詞、動詞、形容詞）を抽出
        """
        morphemes = self.analyze(text)
        concepts = []
        
        for m in morphemes:
            if m['pos'] in ['名詞', '動詞', '形容詞', '形容動詞']:
                concepts.append({
                    'surface': m['surface'],
                    'base': m['base_form'],
                    'pos': m['pos'],
                    'reading': m['reading']
                })
        
        return concepts


# テスト実行
if __name__ == '__main__':
    analyzer = MorphologicalAnalyzer()
    
    test_sentences = [
        "美しい花が咲いている",
        "AIが人間の仕事を奪うかもしれない",
        "愛と憎しみは表裏一体だ"
    ]
    
    for sentence in test_sentences:
        print(f"\n【入力】{sentence}")
        
        # 概念抽出
        concepts = analyzer.extract_concepts(sentence)
        print("抽出された概念：")
        for c in concepts:
            print(f"  {c['surface']} -> {c['base']} ({c['pos']})")