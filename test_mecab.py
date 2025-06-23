import MeCab

# 基本的な動作確認
tagger = MeCab.Tagger()
result = tagger.parse("美しい花が咲いている")
print(result)