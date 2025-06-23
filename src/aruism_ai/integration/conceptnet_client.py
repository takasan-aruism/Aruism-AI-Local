import requests
from typing import List, Dict
import json

class ConceptNetClient:
    """ConceptNet APIクライアント"""
    
    def __init__(self):
        self.base_url = "http://api.conceptnet.io"
        self.cache = {}  # 簡易キャッシュ
        
    def get_concept(self, word: str, lang: str = "ja") -> Dict:
        """概念情報を取得"""
        uri = f"/c/{lang}/{word}"
        
        if uri in self.cache:
            return self.cache[uri]
            
        response = requests.get(f"{self.base_url}{uri}")
        if response.status_code == 200:
            data = response.json()
            self.cache[uri] = data
            return data
        return None
    
    def get_related_concepts(self, word: str, lang: str = "ja") -> List[Dict]:
        """関連概念を取得"""
        data = self.get_concept(word, lang)
        if not data:
            return []
            
        related = []
        for edge in data.get('edges', []):
            related.append({
                'relation': edge['rel']['label'],
                'target': edge['end']['label'],
                'weight': edge['weight']
            })
        return related

# テスト
if __name__ == "__main__":
    client = ConceptNetClient()
    
    # テスト単語
    test_words = ["美しい", "愛", "人工知能"]
    
    for word in test_words:
        print(f"\n【{word}の関連概念】")
        related = client.get_related_concepts(word)
        for r in related[:5]:  # 上位5件
            print(f"  {r['relation']}: {r['target']} (重み: {r['weight']})")