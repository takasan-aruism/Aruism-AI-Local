#!/usr/bin/env python3
"""
アルイズムAI データベース連携テストスクリプト
段階的にDB機能をテストし、問題を特定・解決します
"""

import os
import sys
import json
import logging
from datetime import datetime

# プロジェクトルートをパスに追加
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(PROJECT_ROOT)

from aruism_ai.ontology.db_manager import GraphDBManager

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class DBIntegrationTester:
    """DB連携機能を段階的にテストするクラス"""
    
    def __init__(self):
        self.db_manager = None
        self.test_results = []
        
    def connect_to_db(self):
        """Step 1: データベースへの接続をテスト"""
        print("\n=== Step 1: データベース接続テスト ===")
        try:
            NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD")
            if not NEO4J_PASSWORD:
                print("❌ 環境変数 NEO4J_PASSWORD が設定されていません")
                print("   実行方法: NEO4J_PASSWORD=your_password python test_db_integration.py")
                return False
                
            self.db_manager = GraphDBManager(
                uri="bolt://arism-db:7687",  # Docker環境の場合
                # uri="bolt://localhost:7687",  # ローカル環境の場合
                user="neo4j",
                password=NEO4J_PASSWORD
            )
            
            # 接続テスト
            test_query = "RETURN 1 as test"
            result = self.db_manager.execute_query(test_query)
            
            if result and result[0]['test'] == 1:
                print("✅ データベースへの接続に成功しました")
                self.test_results.append(("DB接続", True, "成功"))
                return True
            else:
                print("❌ データベース接続は確立しましたが、テストクエリが失敗しました")
                self.test_results.append(("DB接続", False, "クエリ失敗"))
                return False
                
        except Exception as e:
            print(f"❌ データベース接続エラー: {e}")
            self.test_results.append(("DB接続", False, str(e)))
            return False
    
    def check_schema(self):
        """Step 2: 必要なスキーマの存在を確認"""
        print("\n=== Step 2: スキーマ確認 ===")
        
        # ノードラベルの確認
        try:
            query = "CALL db.labels() YIELD label RETURN label"
            result = self.db_manager.execute_query(query)
            labels = [r['label'] for r in result]
            
            print(f"既存のノードラベル: {labels}")
            
            required_labels = ['Concept', 'Hierarchy']
            missing_labels = [l for l in required_labels if l not in labels]
            
            if not missing_labels:
                print("✅ 必要なノードラベルが存在します")
                self.test_results.append(("スキーマ確認", True, "OK"))
            else:
                print(f"⚠️  不足しているラベル: {missing_labels}")
                print("   → 初回実行の場合は正常です。これから作成します。")
                self.test_results.append(("スキーマ確認", True, "初期状態"))
                
            return True
            
        except Exception as e:
            print(f"❌ スキーマ確認エラー: {e}")
            self.test_results.append(("スキーマ確認", False, str(e)))
            return False
    
    def create_test_concept(self, concept_id="TEST001"):
        """Step 3: テスト用コンセプトを作成"""
        print(f"\n=== Step 3: テストコンセプト '{concept_id}' を作成 ===")
        
        try:
            # 既存のテストデータを削除
            delete_query = """
            MATCH (c:Concept {concept_id: $concept_id})
            DETACH DELETE c
            """
            self.db_manager.execute_query(delete_query, concept_id=concept_id)
            
            # 新しいテストコンセプトを作成
            create_query = """
            CREATE (c:Concept {
                concept_id: $concept_id,
                canonical_name_ja: $name_ja,
                canonical_name_en: $name_en,
                symbol: $symbol,
                created_at: datetime(),
                test_flag: true
            })
            RETURN c
            """
            
            result = self.db_manager.execute_query(
                create_query,
                concept_id=concept_id,
                name_ja="テスト概念",
                name_en="Test Concept",
                symbol="試"
            )
            
            if result:
                print(f"✅ テストコンセプト '{concept_id}' を作成しました")
                self.test_results.append(("コンセプト作成", True, concept_id))
                return True
            else:
                print("❌ コンセプト作成に失敗しました")
                self.test_results.append(("コンセプト作成", False, "作成失敗"))
                return False
                
        except Exception as e:
            print(f"❌ コンセプト作成エラー: {e}")
            self.test_results.append(("コンセプト作成", False, str(e)))
            return False
    
    def add_hierarchy_to_concept(self, concept_id="TEST001"):
        """Step 4: コンセプトに階層構造を追加"""
        print(f"\n=== Step 4: コンセプト '{concept_id}' に階層構造を追加 ===")
        
        test_hierarchy = {
            "temporal": {
                "新": {
                    "1": {"concept": "生成", "english": "Generation"},
                    "2": {"concept": "変化", "english": "Change"},
                    "3": {"concept": "創発", "english": "Emergence"}
                },
                "古": {
                    "1": {"concept": "存在", "english": "Existence"},
                    "2": {"concept": "継続", "english": "Continuity"},
                    "3": {"concept": "伝統", "english": "Tradition"}
                }
            }
        }
        
        try:
            # 階層データをJSON文字列として保存
            update_query = """
            MATCH (c:Concept {concept_id: $concept_id})
            SET c.hierarchy_data = $hierarchy_json
            RETURN c
            """
            
            result = self.db_manager.execute_query(
                update_query,
                concept_id=concept_id,
                hierarchy_json=json.dumps(test_hierarchy, ensure_ascii=False)
            )
            
            if result:
                print("✅ 階層構造を追加しました")
                print(f"   追加した軸: {list(test_hierarchy.keys())}")
                self.test_results.append(("階層追加", True, "成功"))
                return True
            else:
                print("❌ 階層構造の追加に失敗しました")
                self.test_results.append(("階層追加", False, "追加失敗"))
                return False
                
        except Exception as e:
            print(f"❌ 階層追加エラー: {e}")
            self.test_results.append(("階層追加", False, str(e)))
            return False
    
    def verify_data(self, concept_id="TEST001"):
        """Step 5: 保存されたデータを検証"""
        print(f"\n=== Step 5: データ検証 ===")
        
        try:
            query = """
            MATCH (c:Concept {concept_id: $concept_id})
            RETURN c.concept_id as id,
                   c.canonical_name_ja as name_ja,
                   c.hierarchy_data as hierarchy
            """
            
            result = self.db_manager.execute_query(query, concept_id=concept_id)
            
            if result:
                data = result[0]
                print(f"✅ コンセプト '{data['id']}' のデータを確認しました")
                print(f"   名前: {data['name_ja']}")
                
                if data['hierarchy']:
                    hierarchy = json.loads(data['hierarchy'])
                    print(f"   階層軸: {list(hierarchy.keys())}")
                    self.test_results.append(("データ検証", True, "完全"))
                else:
                    print("   ⚠️  階層データが見つかりません")
                    self.test_results.append(("データ検証", False, "階層なし"))
                    
                return True
            else:
                print(f"❌ コンセプト '{concept_id}' が見つかりません")
                self.test_results.append(("データ検証", False, "データなし"))
                return False
                
        except Exception as e:
            print(f"❌ データ検証エラー: {e}")
            self.test_results.append(("データ検証", False, str(e)))
            return False
    
    def prepare_for_m0001(self):
        """Step 6: M0001登録の準備"""
        print("\n=== Step 6: M0001登録準備 ===")
        
        try:
            # M0001が既に存在するか確認
            check_query = """
            MATCH (c:Concept {concept_id: 'M0001'})
            RETURN c
            """
            existing = self.db_manager.execute_query(check_query)
            
            if existing:
                print("⚠️  M0001は既に存在します")
                print("   既存データを確認してください")
                self.test_results.append(("M0001準備", True, "既存"))
            else:
                print("✅ M0001を新規登録できます")
                self.test_results.append(("M0001準備", True, "新規可能"))
                
            return True
            
        except Exception as e:
            print(f"❌ M0001準備エラー: {e}")
            self.test_results.append(("M0001準備", False, str(e)))
            return False
    
    def run_all_tests(self):
        """全テストを順番に実行"""
        print("="*60)
        print("アルイズムAI データベース連携テスト")
        print("="*60)
        
        # Step 1: DB接続
        if not self.connect_to_db():
            return False
            
        # Step 2: スキーマ確認
        if not self.check_schema():
            return False
            
        # Step 3: テストコンセプト作成
        if not self.create_test_concept():
            return False
            
        # Step 4: 階層追加
        if not self.add_hierarchy_to_concept():
            return False
            
        # Step 5: データ検証
        if not self.verify_data():
            return False
            
        # Step 6: M0001準備確認
        if not self.prepare_for_m0001():
            return False
            
        # テスト結果サマリー
        print("\n" + "="*60)
        print("テスト結果サマリー")
        print("="*60)
        
        success_count = sum(1 for _, success, _ in self.test_results if success)
        total_count = len(self.test_results)
        
        for test_name, success, detail in self.test_results:
            status = "✅" if success else "❌"
            print(f"{status} {test_name}: {detail}")
            
        print(f"\n合計: {success_count}/{total_count} 成功")
        
        if success_count == total_count:
            print("\n🎉 全てのテストが成功しました！")
            print("次のステップ: M0001の登録に進めます")
            return True
        else:
            print("\n⚠️  一部のテストが失敗しました")
            print("エラーを確認して修正してください")
            return False
    
    def cleanup(self):
        """テストデータのクリーンアップ"""
        if self.db_manager:
            try:
                cleanup_query = """
                MATCH (c:Concept {test_flag: true})
                DETACH DELETE c
                """
                self.db_manager.execute_query(cleanup_query)
                print("\n✅ テストデータをクリーンアップしました")
            except Exception as e:
                print(f"\n⚠️  クリーンアップエラー: {e}")
            finally:
                self.db_manager.close()


def main():
    """メイン実行関数"""
    tester = DBIntegrationTester()
    
    try:
        success = tester.run_all_tests()
        
        if success:
            print("\n" + "="*60)
            print("次のステップ:")
            print("1. python run_hierarchy_generation.py M0001")
            print("   でM0001の階層生成を実行できます")
            print("="*60)
            
    except KeyboardInterrupt:
        print("\n\nテストが中断されました")
    except Exception as e:
        print(f"\n予期しないエラー: {e}")
        logging.exception("詳細なエラー情報:")
    finally:
        tester.cleanup()


if __name__ == "__main__":
    main()
