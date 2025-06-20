from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import time
import os
import logging
from datetime import datetime

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ChatGPTAutomation:
    def __init__(self, request_file_path="review_request.txt"):
        self.request_file_path = request_file_path
        self.driver = None
        self.wait = None

    def setup_driver(self):
        """ブラウザドライバーの設定と起動"""
        options = Options()
        
        # ★★★ ここが最終修正箇所です ★★★
        # このプロジェクト専用の新しいプロフィールフォルダを作成・指定する
        project_root = os.getcwd()
        profile_dir = os.path.join(project_root, "chrome-profile") # プロジェクト内に専用フォルダを作成
        options.add_argument(f"--user-data-dir={profile_dir}")
        logging.info(f"自動操作専用のChromeプロフィールを使用します: {profile_dir}")
        
        # 標準Seleniumを使用
        self.driver = webdriver.Chrome(options=options)
        self.wait = WebDriverWait(self.driver, 20)
        logging.info("ブラウザを起動しました")

    def read_request_content(self):
        if not os.path.exists(self.request_file_path): raise FileNotFoundError(f"'{self.request_file_path}' が見つかりません")
        with open(self.request_file_path, "r", encoding="utf-8") as f: content = f.read().strip()
        if not content: raise ValueError(f"'{self.request_file_path}' の中身が空です")
        logging.info(f"リクエスト内容を読み込みました（{len(content)}文字）")
        return content
    
    def find_and_fill_textarea(self, content):
        selectors = [(By.ID, "prompt-textarea"), (By.CSS_SELECTOR, "textarea[placeholder*='Message']")]
        for by, selector in selectors:
            try:
                textarea = self.wait.until(EC.visibility_of_element_located((by, selector)))
                textarea.clear()
                textarea.send_keys(content)
                logging.info(f"テキストを入力しました（セレクタ: {by}={selector}）")
                return textarea
            except:
                continue
        raise TimeoutException("テキストエリアが見つかりません")
    
    def send_message(self):
        try:
            send_button = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-testid="send-button"]')))
            self.driver.execute_script("arguments[0].click();", send_button)
            logging.info("メッセージを送信しました")
        except:
            raise TimeoutException("送信ボタンが見つからないか、クリックできませんでした")

    def run(self):
        """メイン実行処理"""
        try:
            content = self.read_request_content()
            self.setup_driver()
            
            self.driver.get("https://chat.openai.com/")
            logging.info("ChatGPTを開きました")
            
            # 最初の実行では、ここでログインが必要になります
            logging.info("サイトの準備が整うまで最大60秒待機します...")
            logging.info("★★★ もしログイン画面が表示されたら、この時間内に手動でログインを完了してください ★★★")
            time.sleep(60) # 初回ログインのための十分な待機時間
            
            self.find_and_fill_textarea(content)
            time.sleep(1)
            self.send_message()
            
            logging.info("✅ 投稿が完了しました！")
            
        except Exception as e:
            logging.error(f"エラーが発生しました: {e}", exc_info=True)
            if self.driver:
                screenshot_path = f"error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                self.driver.save_screenshot(screenshot_path)
                logging.info(f"スクリーンショットを保存: {screenshot_path}")
            
        finally:
            if self.driver:
                input("\nEnterキーを押すとブラウザを閉じます...")
                self.driver.quit()
                logging.info("ブラウザを終了しました")

if __name__ == "__main__":
    # 不要なライブラリのアンインストールを推奨
    # pip uninstall undetected-chromedriver
    # seleniumの更新を推奨
    # pip install --upgrade selenium
    automation = ChatGPTAutomation()
    automation.run()