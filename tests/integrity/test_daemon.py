######################################################################
# Aruism AI Project - Unit Tests for Philosophical Integrity Daemon
# バージョン: 1.1 (AIチームレビュー反映版)
# 最終更新日: 2025-06-22
######################################################################

import pytest
from unittest.mock import MagicMock, patch

# ▼▼▼ [修正点] importパスを 'aruism_ai.' 基準に統一 ▼▼▼
from aruism_ai.ontology.db_manager import GraphDBManager
from aruism_ai.integrity.daemon import PhilosophicalIntegrityDaemon

class TestPhilosophicalIntegrityDaemon:
    """PhilosophicalIntegrityDaemonのユニットテストクラス"""

    def setup_method(self, method):
        """各テストの前に、モック化されたDBManagerとデーモンをセットアップ"""
        self.mock_db_manager = MagicMock(spec=GraphDBManager)
        self.mock_db_manager.driver = MagicMock()
        self.daemon = PhilosophicalIntegrityDaemon(self.mock_db_manager)

    def test_initialization_success(self):
        """[正常系] デーモンが正常に初期化されるかのテスト"""
        assert self.daemon.db_manager is self.mock_db_manager

    def test_initialization_failure_with_no_driver(self):
        """[異常系] DBドライバがない場合に初期化が失敗するかのテスト"""
        self.mock_db_manager.driver = None
        with pytest.raises(ConnectionError, match="データベースドライバーが初期化されていません。"):
            PhilosophicalIntegrityDaemon(self.mock_db_manager)

    def test_find_orphan_nodes_when_none_found(self):
        """
        [正常系/存在の連動性] 孤児ノードが見つからない場合のテスト
        Aruism原典 §2.4「存在の連動性」に反するノードがないことを確認
        """
        mock_session = self.mock_db_manager.driver.session.return_value.__enter__.return_value
        mock_session.execute_read.return_value = []
        result = self.daemon.find_orphan_nodes()
        mock_session.execute_read.assert_called_once_with(self.daemon._find_and_return_orphans)
        assert result == []

    def test_find_orphan_nodes_when_orphans_exist(self, capsys):
        """
        [分岐/存在の連動性] 孤児ノードが見つかった場合のテスト
        """
        dummy_orphans = [{"meaning_id": "M_ORPHAN_1", "name": "迷子の概念"}]
        mock_session = self.mock_db_manager.driver.session.return_value.__enter__.return_value
        mock_session.execute_read.return_value = dummy_orphans
        result = self.daemon.find_orphan_nodes()
        assert result == dummy_orphans
        captured = capsys.readouterr()
        assert "警告：1件の孤児ノードが検出されました。" in captured.out
        
    def test_check_for_unsymmetrical_nodes_when_none_found(self):
        """
        [正常系/存在の対称性] 非対称な価値ノードが見つからない場合のテスト
        Aruism原典 §2.2「存在の対称性」の原則が守られていることを確認
        """
        mock_session = self.mock_db_manager.driver.session.return_value.__enter__.return_value
        mock_session.execute_read.return_value = []
        result = self.daemon.check_for_unsymmetrical_value_nodes()
        mock_session.execute_read.assert_called_once_with(self.daemon._find_unsymmetrical_nodes)
        assert result == []
        
    def test_check_for_unsymmetrical_nodes_when_nodes_exist(self, capsys):
        """
        [分岐/存在の対称性] 非対称な価値ノードが見つかった場合のテスト
        """
        dummy_nodes = [{"meaning_id": "M_UNSYM_1", "name": "一方的な善", "sentiment": 0.8}]
        mock_session = self.mock_db_manager.driver.session.return_value.__enter__.return_value
        mock_session.execute_read.return_value = dummy_nodes
        result = self.daemon.check_for_unsymmetrical_value_nodes()
        assert result == dummy_nodes
        captured = capsys.readouterr()
        assert "警告：1件の非対称な価値ノードが検出されました。" in captured.out

    # ▼▼▼ [新規追加] レビュー指摘を反映した異常系テスト ▼▼▼
    def test_find_orphan_nodes_handles_db_error(self):
        """
        [異常系] 孤児ノード検索中にDBエラーが発生するケースのテスト
        """
        mock_session = self.mock_db_manager.driver.session.return_value.__enter__.return_value
        # DBクエリ実行時に汎用的な例外を発生させる
        mock_session.execute_read.side_effect = Exception("模擬的なDB接続エラー")

        # 汎用的なExceptionをキャッチするかをテスト
        # (実際のコードでは、より具体的な例外を捕捉し、再raiseすることが望ましい)
        with pytest.raises(Exception, match="模擬的なDB接続エラー"):
            self.daemon.find_orphan_nodes()