# yahoo-watchlist-tool

Yahoo!オークションの「ウォッチリスト」の商品名を、残り時間が短い順に並べて
Googleドキュメントへ自動で書き出すツールです。

- ドキュメントのタイトルは、一番残り時間が短い商品の終了日を使って
  `2026年 9月 27日 ヤフオク` の形式になります。
- 実行するたびに新規ドキュメントを作成します。

## 仕組み

```
[ローカルPC] --(Cookieでログイン)--> [Yahoo!オークション ウォッチリスト]
     |
     | 商品名・残り時間・URLを取得し、残り時間の短い順にソート
     v
[ローカルPC] --(HTTP POST: タイトル+アイテム一覧)--> [Google Apps Script Webアプリ]
                                                        |
                                                        v
                                          あなたのGoogleアカウントで
                                          新規Googleドキュメントを作成
```

Yahoo!オークションへのログインは、ブラウザからコピーしたCookieをローカルの
`.env` に保存して使います(ID・パスワードは扱いません)。
Googleドキュメントの作成は、あなた自身のGoogleアカウントでApps Scriptの
ウェブアプリを実行することで行います(OAuthクライアントやサービスアカウントの
発行は不要です)。

> **このリポジトリの開発環境について**: このコードを作成した環境からは
> `auctions.yahoo.co.jp` にも `docs.google.com` にもネットワーク的にアクセスできない
> (アウトバウンド通信がブロックされている)ため、実際のログイン・スクレイピング・
> Apps Script呼び出しの動作確認はできていません。Yahoo!オークションのHTML構造は
> 長年 `Product` 系のクラス名(`li.Product` など)を使っている前提でセレクタを
> 書いていますが、もし動かなければ下記「トラブルシューティング」を参照してください。

## セットアップ

### 1. Google Apps Script のデプロイ

1. https://script.google.com/ で新規プロジェクトを作成
2. `apps_script/Code.gs` の中身を貼り付ける
3. 左メニューの「プロジェクトの設定」→「スクリプト プロパティ」を開き、
   `SHARED_TOKEN` というキーでランダムな文字列(合言葉)を追加する
   - 例: `openssl rand -hex 16` などで生成した文字列
4. 右上の「デプロイ」→「新しいデプロイ」
   - 種類: **ウェブアプリ**
   - 次のユーザーとして実行: **自分**
   - アクセスできるユーザー: **全員**
5. デプロイ後に表示される **ウェブアプリのURL** をメモしておく

このURLは知っている人なら誰でもアクセスできてしまうため、`SHARED_TOKEN` は
他人に教えないでください(このツールではその文字列を「合言葉」として使い、
一致しないリクエストは拒否します)。

### 2. Yahoo!オークションのCookieを取得

1. ブラウザで https://auctions.yahoo.co.jp/my/watchlist にログインした状態で開く
2. 開発者ツール(F12など)→ Networkタブを開いた状態でページを再読み込み
3. `watchlist` へのリクエストをクリックし、Headers内の `cookie` リクエストヘッダーの
   値を丸ごとコピーする

このCookieには有効期限があります。しばらく経って認証エラーになったら、
同じ手順で取得し直してください。

### 3. ローカル環境の準備

```bash
git clone <このリポジトリ>
cd yahoo-watchlist-tool
python -m venv .venv
source .venv/bin/activate   # Windowsは .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

`.env` を編集し、以下を設定する:

- `YAHOO_COOKIE`: 手順2でコピーしたCookie
- `APPS_SCRIPT_URL`: 手順1のウェブアプリURL
- `APPS_SCRIPT_TOKEN`: 手順1で設定した `SHARED_TOKEN` と同じ値

### 4. 実行

```bash
# 内容を確認するだけ(ドキュメントは作らない)
python src/main.py --dry-run

# 実際にGoogleドキュメントを作成する
python src/main.py
```

成功すると作成されたドキュメントのURLが表示されます。

### 5. 定期実行したい場合(任意)

`crontab -e` で例えば1時間ごとに実行する場合:

```
0 * * * * cd /path/to/yahoo-watchlist-tool && .venv/bin/python src/main.py >> run.log 2>&1
```

Cookieが切れると失敗するようになるので、`run.log` を時々確認してください。

## トラブルシューティング

- **「ログインページにリダイレクトされました」というエラーが出る**
  → `YAHOO_COOKIE` が期限切れです。手順2をやり直してください。

- **「ウォッチリストにアイテムが見つかりませんでした」と出る**
  → Yahoo!オークション側のHTML構造が変わり、セレクタが合わなくなっている可能性があります。
    `python src/main.py --save-html` を実行すると `debug_page_1.html` などが
    保存されるので、実際のクラス名を確認し、`src/yahoo_watchlist.py` 冒頭の
    `ITEM_SELECTORS` / `NAME_SELECTORS` / `TIME_SELECTORS` を実際の構造に合わせて
    書き換えてください。

- **Apps Script側で `unauthorized` エラーが返る**
  → `.env` の `APPS_SCRIPT_TOKEN` と、Apps Scriptのスクリプトプロパティ
    `SHARED_TOKEN` が一致しているか確認してください。

## 現状の仕様・制限

- 商品ごとの「残り時間」表示(例: 残り3日20時間)をそのまま解析してソートしています。
  ドキュメントタイトルに使う終了日は、一番残り時間が短い商品について
  「実行時刻 + 残り時間」から計算した概算の日付です。
- 商品名・残り時間・商品ページへのリンクをドキュメントに書き出します。価格は含めていません。
  必要であれば `src/yahoo_watchlist.py` の `WatchlistItem` と `apps_script/Code.gs` を
  拡張してください。
