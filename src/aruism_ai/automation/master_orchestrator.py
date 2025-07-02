# src/aruism_ai/automation/master_orchestrator.py

import subprocess
import logging
import os
import sys
import json
import re
from datetime import datetime
from typing import List, Dict, Optional

# --- プロジェクトのパス設定 ---
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(PROJECT_ROOT)

# --- 定数定義 (更新) ---
AUTOMATION_DIR = os.path.join(PROJECT_ROOT, "aruism_ai", "automation")
HIERARCHY_GENERATOR_SCRIPT = os.path.join(AUTOMATION_DIR, "run_hierarchy_generation.py")
HIERARCHY_UPDATER_SCRIPT = os.path.join(AUTOMATION_DIR, "hierarchy_updater.py") # Updaterのパスを追加
DRAFT_DIR = os.path.join(PROJECT_ROOT, "data", "drafts")
BATCH_LOG_DIR = os.path.join(PROJECT_ROOT, "data", "batch_logs")


class MasterOrchestrator:
    """352シンボル全体の階層生成とDB格納を統括するマスターオーケストレーター"""
    
    def __init__(self, all_concept_ids: List[str], batch_size: int = 5):
        self.all_ids = all_concept_ids
        self.batch_size = batch_size
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.completed_ids = []
        self.failed_ids = []
        
        os.makedirs(BATCH_LOG_DIR, exist_ok=True)
        os.makedirs(DRAFT_DIR, exist_ok=True)
        
        logging.info("マスターオーケストレーター初期化完了")

    def _check_environment(self):
        """実行環境（スクリプトの存在）をチェック"""
        if not os.path.exists(HIERARCHY_GENERATOR_SCRIPT):
            raise FileNotFoundError(f"生成スクリプトが見つかりません: {HIERARCHY_GENERATOR_SCRIPT}")
        if not os.path.exists(HIERARCHY_UPDATER_SCRIPT):
            raise FileNotFoundError(f"更新スクリプトが見つかりません: {HIERARCHY_UPDATER_SCRIPT}")

    def _parse_generator_output(self, stdout: str) -> Optional[str]:
        """生成スクリプトの出力からドラフトファイルパスを抽出"""
        match = re.search(r'ファイルパス:\s*(.+\.json)', stdout)
        return match.group(1).strip() if match else None

    def _run_subprocess(self, command: List[str], timeout: int = 600) -> subprocess.CompletedProcess:
        """サブプロセスを環境変数を設定して実行するヘルパー関数"""
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8' # 標準入出力のエンコーディングを指定
        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding='utf-8',
            env=env,
            timeout=timeout
        )

    def execute_pipeline_for_id(self, concept_id: str, auto_approve_update: bool) -> Dict:
        """単一IDに対して生成→更新のパイプラインを実行"""
        # --- ステップ1: 草案生成 ---
        logging.info(f"'{concept_id}' の草案生成を開始...")
        gen_command = ["python3", HIERARCHY_GENERATOR_SCRIPT, concept_id, "--auto-approve"]
        gen_result = self._run_subprocess(gen_command)

        if gen_result.returncode != 0:
            logging.error(f"'{concept_id}' の草案生成に失敗しました。")
            return {"status": "generation_failed", "error": gen_result.stderr}
        
        draft_path = self._parse_generator_output(gen_result.stdout)
        if not draft_path or not os.path.exists(draft_path):
            logging.error(f"'{concept_id}' のドラフトパスが取得できませんでした。")
            return {"status": "generation_failed", "error": "ドラフトパスの取得失敗"}
        
        logging.info(f"'{concept_id}' の草案生成が完了: {draft_path}")

        if not auto_approve_update:
            approval = input(f"草案 {draft_path} をDBに反映しますか？ (y/n): ").lower()
            if approval != 'y':
                return {"status": "update_skipped", "draft_path": draft_path}

        # --- ステップ2: DB更新 ---
        logging.info(f"'{concept_id}' のDB更新を開始...")
        update_command = ["python3", HIERARCHY_UPDATER_SCRIPT, concept_id, draft_path]
        update_result = self._run_subprocess(update_command, timeout=180) # 更新処理は短めのタイムアウト

        if update_result.returncode != 0:
            logging.error(f"'{concept_id}' のDB更新に失敗しました。")
            return {"status": "update_failed", "draft_path": draft_path, "error": update_result.stderr}
        
        logging.info(f"'{concept_id}' のDB更新が完了しました。")
        return {"status": "completed", "draft_path": draft_path}


    def run_full_process(self, auto_approve_update: bool = False):
        """全てのコンセプトIDに対してパイプラインを実行するメインプロセス"""
        self._check_environment()
        
        batches = [self.all_ids[i:i + self.batch_size] for i in range(0, len(self.all_ids), self.batch_size)]
        logging.info(f"全体を{len(batches)}個のバッチに分割しました。")
        
        for i, batch in enumerate(batches, 1):
            logging.info(f"--- バッチ {i}/{len(batches)} 開始 ---")
            
            for concept_id in batch:
                result = self.execute_pipeline_for_id(concept_id, auto_approve_update)
                
                if result["status"] == "completed":
                    self.completed_ids.append(concept_id)
                else:
                    self.failed_ids.append({"concept_id": concept_id, "details": result})
            
            logging.info(f"--- バッチ {i}/{len(batches)} 完了 ---")
            if i < len(batches):
                import time
                logging.info("次のバッチまで5秒待機...")
                time.sleep(5)
        
        self.generate_final_report()

    def generate_final_report(self):
        """全体の処理結果レポートを生成・表示"""
        report_path = os.path.join(BATCH_LOG_DIR, f"final_report_{self.session_id}.json")
        report = {
            "session_id": self.session_id,
            "summary": {
                "total_concepts": len(self.all_ids),
                "completed": len(self.completed_ids),
                "failed": len(self.failed_ids),
                "completion_rate": f"{len(self.completed_ids) / len(self.all_ids) * 100:.1f}%" if self.all_ids else "N/A"
            },
            "completed_ids": self.completed_ids,
            "failed_details": self.failed_ids
        }
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print("\n" + "="*60)
        print("【処理完了サマリー】")
        print(f"総コンセプト数: {report['summary']['total_concepts']}")
        print(f"処理完了: {report['summary']['completed']}")
        print(f"処理失敗: {report['summary']['failed']}")
        print(f"完了率: {report['summary']['completion_rate']}")
        if self.failed_ids:
            print("\n失敗したID:")
            for item in self.failed_ids:
                print(f"- {item['concept_id']} (理由: {item['details']['status']})")
        print(f"詳細レポート: {report_path}")
        print("="*60 + "\n")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    # テスト対象をM0001のみに絞る
    test_ids = ["M0001"] 

    orchestrator = MasterOrchestrator(test_ids, batch_size=1)

    # auto_approve_update=Trueで全自動実行
    orchestrator.run_full_process(auto_approve_update=True)