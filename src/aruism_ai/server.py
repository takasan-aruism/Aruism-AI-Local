######################################################################
# Aruism AI Project - Broadcast Server
# バージョン: 4.1.1 (構文エラー修正・堅牢化・ステルス対応)
#
# 概要:
# このサーバーは、指定された複数のAIサービスに対して、
# クリップボードの内容を同時に送信（ブロードキャスト）し、
# 各AIからの返信をまとめて取得（集約）する機能を提供します。
#
# 主な改善点 (v4.1 -> v4.1.1):
# 1. 構文エラーの修正: 報告されたエラーを含む複数の構文上の問題を修正。
# 2. 安定性の向上: ページオブジェクトをヘルパー関数に正しく渡すように修正。
# 3. 接続ロジックの修正: ブラウザコンテキストの処理をより安定化。
# 4. インデントの正規化: 潜在的なエラーの原因となる非標準スペースを削除。
######################################################################

import logging
import os
import sys
import random
from typing import List, Optional, Dict, Any

import pyperclip
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from playwright.sync_api import sync_playwright, Page, BrowserContext, TimeoutError as PlaywrightTimeoutError
from playwright_stealth import stealth_sync

# --- 初期設定 ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(funcName)s] - %(message)s'
)

# --- FastAPIアプリケーションのインスタンス化 ---
app = FastAPI(
    title="Aruism AI Broadcast Server",
    description="複数のAIサービスを自動操作するためのバックエンドAPI (堅牢化・修正版)",
    version="4.1.1",
)

# --- グローバル変数 ---
# BrowserContextはPlaywrightの操作の基盤となる
browser_context: Optional[BrowserContext] = None

# ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★
# AIごとの設定を一元管理 (セレクタ堅牢化版)
# セレクタは「最も安定しているもの」から順に記載する。
# 優先順位: 1. data-testid, 2. ARIA role, 3. label/placeholder, 4. CSSセレクタ
# ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★
AI_CONFIGS: List[Dict[str, Any]] = [
    { # 0: ChatGPT
        "name": "ChatGPT",
        "input_selectors": [
            "textarea[data-testid='prompt-textarea']", # 最も安定
            "textarea[id='prompt-textarea']",
            "textarea[placeholder*='Message']",
        ],
        "send_button_selectors": [
            "button[data-testid='send-button']", # 最も安定
            "button[data-testid*='send']",
            "button"
        ],
        "response_selector": "div[data-message-author-role='assistant'] .markdown", # 回答部分のみを正確に
        "copy_button_selectors": [
            "div[data-message-author-role='assistant']:last-child button[data-testid*='copy']",
            "div[data-message-author-role='assistant']:last-child button[aria-label*='Copy']",
        ],
        "streaming_response_element_selector": "div[data-message-author-role='assistant']:last-child.result-streaming"
    },
    { # 1: Gemini
        "name": "Gemini",
        "input_selectors": [
            "div[role='textbox'][aria-label*='プロンプトを入力']", # ARIA Roleベース
            "div.ProseMirror[contenteditable='true']",
            "div[contenteditable='true']",
        ],
        "send_button_selectors": [
            "button.send-button",
            "button[aria-label*='送信']",
            "button[data-testid*='send']"
        ],
        "response_selector": "div[data-message-author-role='model']",
        "copy_button_selectors": [
            "response-container:last-child button[aria-label*='コピー']",
            "response-container:last-child button[aria-label*='Copy']",
        ],
        "streaming_response_element_selector": "response-container:last-child.loading-animation" # 仮のセレクタ
    },
    { # 2: Grok
        "name": "Grok",
        "input_selectors": [
            "textarea[data-testid='tweet-textarea']",
            "textarea[aria-label*='Grok']",
            "textarea[placeholder*='Ask Grok']",
        ],
        "send_button_selectors": [
            "button[data-testid='send-button']",
            "button"
        ],
        "response_selector": "div[data-testid='chat-message-text']",
        "copy_button_selectors": [
            "article:last-child button[aria-label*='Copy']",
        ],
        "streaming_response_element_selector": "article:last-child.streaming-indicator" # 仮のセレクタ
    },
    { # 3: DeepSeek
        "name": "DeepSeek",
        "input_selectors": [
            "textarea[placeholder^='Message']",
            "textarea#chat-input",
        ],
        "send_button_selectors": [
            "button > svg[data-icon='send']", # SVGを持つボタン
            "button[data-testid*='send']"
        ],
        "response_selector": "div.message-content.assistant", # 仮のクラス
        "copy_button_selectors": [
            "div.message-row.assistant:last-child button[title*='Copy']",
        ],
        "streaming_response_element_selector": "div.message-row.assistant:last-child.blinking-cursor" # 仮のセレクタ
    },
    { # 4: Claude
        "name": "Claude",
        "input_selectors": [
            "div.ProseMirror[contenteditable='true']", # Claudeが使用するリッチテキストエディタ
            "div[role='textbox']",
        ],
        "send_button_selectors": [
            "button[aria-label='Send Message']",
            "button[data-testid*='send']",
        ],
        "response_selector": "div[data-testid*='conversation-turn']:last-child div[data-testid*='message-content']",
        "copy_button_selectors": [
            "div[data-testid*='conversation-turn']:last-child button[aria-label*='Copy']",
        ],
        "streaming_response_element_selector": "div[data-testid*='conversation-turn']:last-child.streaming-dot" # 仮のセレクタ
    }
]


# --- CORS設定 ---
origins = ["null", "file://", "http://127.0.0.1:8000"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- APIリクエストの型定義 ---
class AiRequest(BaseModel):
    targets: List[int]

# --- ヘルパー関数 (堅牢化版) ---
def find_element(page: Page, selectors: List[str], description: str, ai_name: str):
    """複数のセレクタを試行して単一の要素を見つける（堅牢版）"""
    logging.info(f"[{ai_name}] {description}を検索中...")
    for i, selector in enumerate(selectors):
        try:
            logging.info(f"  試行 {i+1}/{len(selectors)}: '{selector}'")
            element = page.locator(selector).first
            if element.count() > 0:
                if element.is_visible(timeout=1500):
                    logging.info(f"  -> [{ai_name}] {description}を発見: '{selector}'")
                    return element
                else:
                    logging.warning(f"  -> 要素は存在するが非表示: '{selector}'")
            else:
                logging.info(f"  -> 要素は存在せず")
        except Exception as e:
            logging.warning(f"  -> セレクタ '{selector}' でエラー: {e}")
            continue
    logging.error(f"[{ai_name}] {description}が見つかりませんでした。")
    return None

def wait_for_streaming_to_finish(page: Page, config: dict):
    """AIの応答ストリーミングが完了するのを待つ"""
    ai_name = config["name"]
    streaming_selector = config.get("streaming_response_element_selector")
    if not streaming_selector:
        logging.info(f"[{ai_name}] ストリーミング完了待機用のセレクタが未設定。固定時間待機します。")
        page.wait_for_timeout(5000)
        return

    logging.info(f"[{ai_name}] 応答ストリーミングの完了を待機中... (セレクタ: {streaming_selector})")
    try:
        streaming_element = page.locator(streaming_selector).first
        # ストリーミング開始を最大10秒待つ
        streaming_element.wait_for(state='visible', timeout=10000)
        logging.info(f"[{ai_name}] ストリーミング開始を検知。")
        # ストリーミング完了（要素が非表示になる）を最大120秒待つ
        streaming_element.wait_for(state='hidden', timeout=120000)
        logging.info(f"[{ai_name}] ストリーミング完了を検知。")
    except PlaywrightTimeoutError:
        logging.warning(f"[{ai_name}] ストリーミング完了の待機がタイムアウトしました。処理を続行します。")
    except Exception as e:
        logging.error(f"[{ai_name}] ストリーミング待機中にエラー: {e}")

def safe_input_text(page: Page, input_element, text: str, ai_name: str):
    """人間らしく、安全にテキストを入力する"""
    try:
        input_element.click(delay=random.randint(50, 150))
        input_element.fill("")
        page.wait_for_timeout(random.randint(100, 300))
        input_element.type(text, delay=random.randint(30, 80))
        logging.info(f"[{ai_name}] テキスト入力を完了しました。")
        return True
    except Exception as e:
        logging.error(f"[{ai_name}] テキスト入力でエラー: {e}")
        return False

# --- APIエンドポイントの定義 ---

@app.post("/connect_browser", summary="ブラウザへの接続とステルス化")
def connect_browser():
    """
    デバッグモードで実行中のChromeブラウザにPlaywrightを接続し、ステルス化を適用します。
    Chromeは事前に --remote-debugging-port=9222 付きで起動しておく必要があります。
    """
    global browser_context
    try:
        logging.info("実行中のChromeへの接続を試みます (http://localhost:9222)...")
        p = sync_playwright().start()
        browser = p.chromium.connect_over_cdp("http://localhost:9222")
        
        # 修正: 最初に見つかったコンテキストをグローバル変数に格納
        if not browser.contexts:
            raise Exception("ブラウザにアクティブなコンテキストが見つかりません。")
        browser_context = browser.contexts[0]
        
        logging.info("✅ ブラウザへの接続に成功しました。")
        logging.info("全ページにステルス化を適用します...")
        
        for page in browser_context.pages:
            try:
                stealth_sync(page)
                logging.info(f"  -> ページ '{page.title()}' をステルス化しました。")
            except Exception as e:
                logging.error(f"  -> ページ '{page.title()}' のステルス化に失敗: {e}")

        logging.info("✅ ステルス化が完了しました。")
        return {"status": "success", "message": "Browser connected and stealthed successfully."}
    except Exception as e:
        logging.error(f"❌ ブラウザへの接続に失敗しました: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to connect to browser. Make sure Chrome is running with --remote-debugging-port=9222. Error: {e}")

@app.post("/broadcast", summary="クリップボード内容をAIに一斉送信")
def broadcast_to_ais(request: AiRequest):
    if not browser_context:
        raise HTTPException(status_code=400, detail="Browser not connected. Please connect first.")
    
    content = pyperclip.paste()
    if not content:
        raise HTTPException(status_code=400, detail="Clipboard is empty.")

    logging.info(f"▶ {len(request.targets)}個のAIにブロードキャストを開始します...")
    all_pages = browser_context.pages
    
    for target_index in request.targets:
        if not (0 <= target_index < len(AI_CONFIGS)):
            logging.warning(f"インデックス {target_index} の設定は存在しません。スキップします。")
            continue
            
        config = AI_CONFIGS[target_index]
        ai_name = config["name"]
        
        if target_index >= len(all_pages):
            logging.warning(f"[{ai_name}] タブ(インデックス:{target_index})が存在しません。スキップします。")
            continue
            
        page = all_pages[target_index]
        logging.info(f"--- 操作開始: {ai_name} (タブ {target_index}) ---")
        page.bring_to_front()
        page.wait_for_timeout(random.randint(300, 600))
        
        try:
            input_area = find_element(page, config["input_selectors"], "入力欄", ai_name)
            if not input_area:
                continue

            if not safe_input_text(page, input_area, content, ai_name):
                continue
            
            page.wait_for_timeout(random.randint(500, 1000))

            send_button = find_element(page, config["send_button_selectors"], "送信ボタン", ai_name)
            if send_button and send_button.is_enabled():
                send_button.click(delay=random.randint(80, 200))
                logging.info(f"[{ai_name}] 送信ボタンをクリックしました。")
            else:
                logging.warning(f"[{ai_name}] 送信ボタンが見つからないか無効なため、Enterキーでの送信を試みます。")
                input_area.press("Enter")
                logging.info(f"[{ai_name}] Enterキーを送信しました。")
            
        except Exception as e:
            logging.error(f"❌ [{ai_name}] の操作中に予期せぬエラーが発生しました: {e}", exc_info=True)

    return {"status": "success", "message": f"Broadcast request sent for targets: {request.targets}"}


@app.post("/consolidate", summary="AIの返信を収集してクリップボードにコピー")
def consolidate_responses(request: AiRequest):
    if not browser_context:
        raise HTTPException(status_code=400, detail="Browser not connected. Please connect first.")

    logging.info(f"▶ {len(request.targets)}個のAIから返信を収集します...")
    all_pages = browser_context.pages
    # 修正: 空のリストを正しく初期化
    collected_responses: List[str] = []
    
    for target_index in request.targets:
        if not (0 <= target_index < len(AI_CONFIGS)):
            logging.warning(f"インデックス {target_index} の設定は存在しません。スキップします。")
            continue
            
        config = AI_CONFIGS[target_index]
        ai_name = config["name"]

        if target_index >= len(all_pages):
            logging.warning(f"[{ai_name}] タブ(インデックス:{target_index})が存在しません。スキップします。")
            continue
            
        page = all_pages[target_index]
        logging.info(f"--- 収集開始: {ai_name} (タブ {target_index}) ---")
        page.bring_to_front()
        page.wait_for_timeout(random.randint(300, 600))
        
        try:
            wait_for_streaming_to_finish(page, config)

            # 応答要素を複数取得し、最後のものを採用するロジックに変更
            response_elements = page.locator(config["response_selector"])
            
            if response_elements.count() > 0:
                # 最後の要素を取得
                response_text = response_elements.last.inner_text()
                collected_responses.append(f"=== {ai_name} ===\n{response_text.strip()}")
                logging.info(f"[{ai_name}] 応答テキストの取得に成功しました。({len(response_text)}文字)")
            else:
                logging.error(f"❌ [{ai_name}] 応答テキストの取得に失敗しました。")
                collected_responses.append(f"=== {ai_name} ===\n[返信の取得に失敗しました]")

        except Exception as e:
            logging.error(f"❌ [{ai_name}] の処理中にエラーが発生しました: {e}", exc_info=True)
            collected_responses.append(f"=== {ai_name} ===\n[エラー: {str(e)}]")

    if collected_responses:
        consolidated_text = "\n\n\n".join(collected_responses)
        pyperclip.copy(consolidated_text)
        logging.info(f"✅ {len(collected_responses)}個のAI返信をクリップボードにコピーしました。")
        return {
            "status": "success", 
            "message": f"Collected responses from {len(collected_responses)} AIs.",
            "collected_count": len(collected_responses)
        }
    else:
        raise HTTPException(status_code=400, detail="No responses could be collected.")

@app.post("/debug_page", summary="指定ページの要素をデバッグ")
def debug_page_elements(request: AiRequest):
    if not browser_context:
        raise HTTPException(status_code=400, detail="Browser not connected.")
    if not request.targets or len(request.targets) != 1:
        raise HTTPException(status_code=400, detail="Specify exactly one target for debugging.")

    # 修正: リストから最初の要素を取得
    target_index = request.targets[0]
    if not (0 <= target_index < len(AI_CONFIGS)):
        raise HTTPException(status_code=400, detail=f"Invalid target index: {target_index}")

    all_pages = browser_context.pages
    if target_index >= len(all_pages):
        raise HTTPException(status_code=400, detail=f"Tab {target_index} does not exist.")
        
    page = all_pages[target_index]
    page.bring_to_front()
    page.wait_for_timeout(500)

    config = AI_CONFIGS[target_index]
    ai_name = config["name"]
    logging.info(f"--- デバッグ開始: {ai_name} (タブ {target_index}) ---")
    
    # 修正: JavaScript内の構文エラーを修正
    all_elements_props = page.evaluate('''() => {
        const interesting_attrs = ['id', 'class', 'data-testid', 'aria-label', 'role', 'placeholder', 'title', 'name'];
        const elements = [];
        document.querySelectorAll('*').forEach(el => {
            // is visible check
            if (!el.offsetParent && el.tagName.toLowerCase() !== 'body') return;

            const props = {
                tag: el.tagName.toLowerCase(),
                text: el.innerText ? el.innerText.substring(0, 100).trim() : '',
                attributes: {}
            };
            let has_interesting_attr = false;
            interesting_attrs.forEach(attr => {
                if (el.hasAttribute(attr)) {
                    props.attributes[attr] = el.getAttribute(attr);
                    has_interesting_attr = true;
                }
            });
            // タグ名だけでも収集する
            if (has_interesting_attr || ['button', 'textarea', 'input', 'a'].includes(props.tag)) {
                elements.push(props);
            }
        });
        return elements;
    }''')

    debug_info = {
        "ai_name": ai_name,
        "page_url": page.url,
        "page_title": page.title(),
        "element_count": len(all_elements_props),
        "interesting_elements": all_elements_props
    }
    logging.info(f"デバッグ情報を {len(all_elements_props)} 件取得しました。")
    return debug_info

@app.get("/get_ai_configs", summary="AI設定一覧の取得")
def get_ai_configs():
    return {"configs": [{"index": i, "name": c["name"]} for i, c in enumerate(AI_CONFIGS)]}

# --- サーバーの起動 ---
if __name__ == "__main__":
    import uvicorn
    # サーバーをリロードモードで起動するとPlaywrightの接続で問題が起きやすいため、リロードは無効化
    uvicorn.run(app, host="127.0.0.1", port=8000)

