# src/aruism_ai/automation/master_orchestrator.py

import subprocess
import logging
import os
import sys
import json
import re
from datetime import datetime
from typing import List, Dict, Optional

# --- プロジェクトのパス設定（修正版）---
# このファイル: /workspace/Aruism-AI-Local/aruism_ai/automation/master_orchestrator.py
# PROJECT_ROOTは /workspace/Aruism-AI-Local になる
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(PROJECT_ROOT)

# --- 定数定義（修正版）---
HIERARCHY_GENERATOR_SCRIPT = os.path.join(PROJECT_ROOT, "aruism_ai/automation/run_hierarchy_generation.py")
DRAFT_DIR = os.path.join(PROJECT_ROOT, "data/drafts")
BATCH_LOG_DIR = os.path.join(PROJECT_ROOT, "data/batch_logs")

print(f"階層生成スクリプト: {HIERARCHY_GENERATOR_SCRIPT}")
print(f"ファイル存在確認: {os.path.exists(HIERARCHY_GENERATOR_SCRIPT)}")

class MasterOrchestrator:
    """352シンボル全体の階層生成を統括するマスターオーケストレーター"""
    
    def __init__(self, all_concept_ids: List[str], batch_size: int = 5):
        self.all_ids = all_concept_ids
        self.batch_size = batch_size
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.completed_ids = []
        self.failed_ids = []
        
        # ログディレクトリの作成
        os.makedirs(BATCH_LOG_DIR, exist_ok=True)
        os.makedirs(DRAFT_DIR, exist_ok=True)
        
        logging.info(f"マスターオーケストレーター初期化完了")
        logging.info(f"対象コンセプト数: {len(all_concept_ids)}")
        logging.info(f"バッチサイズ: {batch_size}")
        logging.info(f"セッションID: {self.session_id}")

    def _check_environment(self):
        """実行環境をチェック"""
        if not os.path.exists(HIERARCHY_GENERATOR_SCRIPT):
            raise FileNotFoundError(f"階層生成スクリプトが見つかりません: {HIERARCHY_GENERATOR_SCRIPT}")
        
        # Llama環境のチェック（generator側でも行うが念のため）
        llama_model = "/workspace/llama.cpp/models/Llama-4-Scout-Q8-merged.gguf"
        if not os.path.exists(llama_model):
            logging.warning(f"Llamaモデルが見つかりません: {llama_model}")

    def _parse_generator_output(self, stdout: str) -> Optional[str]:
        """階層生成スクリプトの出力からドラフトファイルパスを抽出"""
        # ファイルパスのパターンを探す
        path_pattern = r'ファイルパス:\s*(.+\.json)'
        match = re.search(path_pattern, stdout)
        if match:
            return match.group(1).strip()
        
        # 別のパターンも試す（DRAFT_DIRを含むパス）
        json_pattern = rf'{DRAFT_DIR}/\S+\.json'
        match = re.search(json_pattern, stdout)
        if match:
            return match.group(0)
        
        return None

    def _save_batch_status(self, batch_num: int, batch_ids: List[str], results: Dict):
        """バッチ処理の結果を保存"""
        status_file = os.path.join(
            BATCH_LOG_DIR, 
            f"batch_{self.session_id}_{batch_num:03d}.json"
        )
        
        status_data = {
            "session_id": self.session_id,
            "batch_number": batch_num,
            "batch_ids": batch_ids,
            "timestamp": datetime.now().isoformat(),
            "results": results,
            "summary": {
                "total": len(batch_ids),
                "completed": len([r for r in results.values() if r.get("status") == "completed"]),
                "failed": len([r for r in results.values() if r.get("status") == "failed"]),
                "skipped": len([r for r in results.values() if r.get("status") == "skipped"])
            }
        }
        
        with open(status_file, 'w', encoding='utf-8') as f:
            json.dump(status_data, f, ensure_ascii=False, indent=2)
        
        logging.info(f"バッチステータスを保存: {status_file}")

    def execute_generation_batch(self, batch_ids: List[str], batch_num: int) -> Dict[str, Dict]:
        """
        指定されたIDのバッチに対して、階層生成スクリプトを順次実行する。
        戻り値: {concept_id: {"status": "completed/failed/skipped", "draft_path": "...", "error": "..."}}
        """
        results = {}
        logging.info(f"バッチ {batch_num} 処理開始: {batch_ids}")

        for i, concept_id in enumerate(batch_ids):
            logging.info(f"[{i+1}/{len(batch_ids)}] コンセプトID '{concept_id}' の処理開始...")
            
            # 既に処理済みかチェック
            existing_draft = os.path.join(DRAFT_DIR, f"{concept_id}_draft.json")
            if os.path.exists(existing_draft):
                logging.info(f"'{concept_id}' は既に処理済みです。スキップします。")
                results[concept_id] = {
                    "status": "skipped",
                    "draft_path": existing_draft,
                    "message": "既存のドラフトあり"
                }
                continue
            
            # 環境変数設定（日本語対応）
            env = os.environ.copy()
            env['LANG'] = 'ja_JP.UTF-8'
            env['LC_ALL'] = 'ja_JP.UTF-8'
            
            command = ["python3", HIERARCHY_GENERATOR_SCRIPT, concept_id]
            
            try:
                # サブプロセスとして実行（対話的入力は自動化できないので注意）
                result = subprocess.run(
                    command, 
                    capture_output=True, 
                    text=True, 
                    encoding='utf-8',
                    env=env,
                    timeout=300  # 5分のタイムアウト
                )
                
                if result.returncode == 0:
                    draft_path = self._parse_generator_output(result.stdout)
                    if draft_path:
                        logging.info(f"'{concept_id}' の処理が正常に完了しました。")
                        results[concept_id] = {
                            "status": "completed",
                            "draft_path": draft_path
                        }
                        self.completed_ids.append(concept_id)
                    else:
                        logging.warning(f"'{concept_id}' の処理は完了しましたが、ドラフトパスを取得できませんでした。")
                        results[concept_id] = {
                            "status": "completed",
                            "draft_path": None,
                            "warning": "ドラフトパスの取得失敗"
                        }
                else:
                    logging.error(f"'{concept_id}' の処理中にエラーが発生しました。")
                    results[concept_id] = {
                        "status": "failed",
                        "error": result.stderr,
                        "returncode": result.returncode
                    }
                    self.failed_ids.append(concept_id)
                    
            except subprocess.TimeoutExpired:
                logging.error(f"'{concept_id}' の処理がタイムアウトしました。")
                results[concept_id] = {
                    "status": "failed",
                    "error": "処理タイムアウト（5分）"
                }
                self.failed_ids.append(concept_id)
                
            except Exception as e:
                logging.error(f"'{concept_id}' の処理中に予期しないエラー: {str(e)}")
                results[concept_id] = {
                    "status": "failed",
                    "error": str(e)
                }
                self.failed_ids.append(concept_id)
        
        # バッチ結果を保存
        self._save_batch_status(batch_num, batch_ids, results)
        
        logging.info(f"バッチ {batch_num} 処理完了")
        return results

    def generate_final_report(self):
        """全体の処理結果レポートを生成"""
        report_path = os.path.join(
            BATCH_LOG_DIR, 
            f"final_report_{self.session_id}.json"
        )
        
        report = {
            "session_id": self.session_id,
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_concepts": len(self.all_ids),
                "completed": len(self.completed_ids),
                "failed": len(self.failed_ids),
                "completion_rate": f"{len(self.completed_ids) / len(self.all_ids) * 100:.1f}%"
            },
            "completed_ids": self.completed_ids,
            "failed_ids": self.failed_ids,
            "batch_size": self.batch_size
        }
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        logging.info(f"最終レポートを生成: {report_path}")
        
        # コンソールにサマリーを表示
        print("\n" + "="*60)
        print("【処理完了サマリー】")
        print(f"総コンセプト数: {len(self.all_ids)}")
        print(f"処理完了: {len(self.completed_ids)}")
        print(f"処理失敗: {len(self.failed_ids)}")
        print(f"完了率: {report['summary']['completion_rate']}")
        print("="*60 + "\n")

    def run_full_process(self, auto_approve: bool = False):
        """
        全てのコンセプトIDに対してAQMサイクルを実行するメインプロセス
        
        Args:
            auto_approve: Trueの場合、承認プロンプトを自動的に'n'で回答（ドラフト生成のみ）
        """
        self._check_environment()
        
        # バッチ分割
        batches = [self.all_ids[i:i + self.batch_size] for i in range(0, len(self.all_ids), self.batch_size)]
        
        logging.info(f"全体を{len(batches)}個のバッチに分割しました。")
        
        for i, batch in enumerate(batches, 1):
            print(f"\n{'='*60}")
            print(f"【バッチ {i}/{len(batches)} 開始】")
            print(f"対象ID: {batch}")
            print(f"{'='*60}\n")
            
            # === ステップ1: 定量的バッチ処理（AI生成） ===
            batch_results = self.execute_generation_batch(batch, i)
            
            # === ステップ2: 定性的レビュー（将来の実装用） ===
            # ここで生成されたドラフトの品質チェックや
            # 相互関係の確認などを行う予定
            
            # === ステップ3: メタ分析（将来の実装用） ===
            # バッチ全体のパターン分析や
            # 知識構造の整合性チェックなどを行う予定
            
            # 進捗表示
            completed_total = len(self.completed_ids)
            print(f"\n現在の進捗: {completed_total}/{len(self.all_ids)} ({completed_total/len(self.all_ids)*100:.1f}%)")
            
            # 次のバッチまで少し待機（APIレート制限対策）
            if i < len(batches):
                import time
                logging.info("次のバッチまで5秒待機...")
                time.sleep(5)
        
        # 最終レポート生成
        self.generate_final_report()

    def resume_from_checkpoint(self):
        """中断したセッションから再開する機能（将来の実装用）"""
        # TODO: batch_logsから前回の状態を読み込んで再開
        pass


# メイン実行部分
if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO, 
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # テスト用の小さなIDリスト
    test_ids = ["M0001", "M0002", "M0003", "M0004", "M0005"]
    
    # 全352シンボルの場合は以下のようにロード
    # from aruism_ai.ontology.db_manager import GraphDBManager
    # db = GraphDBManager()
    # all_ids = db.get_all_concept_ids()  # このメソッドを実装する必要あり
    
    orchestrator = MasterOrchestrator(test_ids, batch_size=2)
    
    # auto_approve=Trueでドラフト生成のみ（承認なし）モードも可能
    orchestrator.run_full_process(auto_approve=False)