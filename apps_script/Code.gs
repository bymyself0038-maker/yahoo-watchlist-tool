/**
 * ローカルスクリプト、またはチャット経由で送られてきたウォッチリスト情報を受け取り、
 * Googleドキュメントに書き込むウェブアプリ。
 *
 * 2通りの動作:
 *   - payload.docUrl (または docId) を指定 → 既存のドキュメントの一番上に追記する
 *     (見出し行 + 商品名のリスト。前回までの内容はそのまま下に残る)
 *   - 指定しない → payload.title のタイトルで新規ドキュメントを作成する
 *
 * デプロイ方法:
 *   1. https://script.google.com/ で新規プロジェクトを作成し、このファイルの内容を貼り付ける
 *   2. 「プロジェクトの設定」→「スクリプト プロパティ」に SHARED_TOKEN を追加し、
 *      ランダムな文字列(合言葉)を設定する。呼び出し側の APPS_SCRIPT_TOKEN と同じ値にする。
 *   3. 「デプロイ」→「新しいデプロイ」→ 種類「ウェブアプリ」
 *        - 次のユーザーとして実行: 自分
 *        - アクセスできるユーザー: 全員
 *   4. 発行されたウェブアプリのURLを呼び出し側の APPS_SCRIPT_URL に設定する
 *
 * SHARED_TOKEN は「誰でも叩けるURL」に対する簡易的なアクセス制御なので、
 * 他人に推測されない値にし、コードやチャットに貼り付けないこと。
 */

function doPost(e) {
  try {
    var payload = JSON.parse(e.postData.contents);

    var sharedToken = PropertiesService.getScriptProperties().getProperty('SHARED_TOKEN');
    if (!sharedToken || payload.token !== sharedToken) {
      return jsonOutput({ ok: false, error: 'unauthorized' });
    }

    var items = payload.items || [];
    var heading = payload.heading || '';
    var docId = extractDocId(payload.docUrl || payload.docId);

    var doc;
    var isNewDoc = !docId;
    if (isNewDoc) {
      doc = DocumentApp.create(payload.title || '無題のウォッチリスト');
    } else {
      doc = DocumentApp.openById(docId);
    }

    var body = doc.getBody();
    var placeholder = isNewDoc ? body.getParagraphs()[0] : null; // create() 直後の空段落

    var lines = [];
    if (heading) {
      lines.push({ text: heading, isHeading: true });
    }
    items.forEach(function (item, i) {
      lines.push({ text: (i + 1) + '. ' + item.name, isHeading: false });
    });
    lines.push({ text: '', isHeading: false }); // 前回までの内容との区切り

    // 常に先頭(index 0)に挿入するので、逆順にたどることで最終的な並びを正しくする
    for (var i = lines.length - 1; i >= 0; i--) {
      var p = body.insertParagraph(0, lines[i].text);
      if (lines[i].isHeading) {
        p.setHeading(DocumentApp.ParagraphHeading.HEADING2);
      }
    }

    if (isNewDoc && items.length > 0 && placeholder.getText() === '') {
      placeholder.removeFromParent();
    }

    doc.saveAndClose();

    return jsonOutput({ ok: true, url: doc.getUrl(), id: doc.getId() });
  } catch (err) {
    return jsonOutput({ ok: false, error: String(err) });
  }
}

function extractDocId(urlOrId) {
  if (!urlOrId) return null;
  var match = String(urlOrId).match(/[-\w]{25,}/);
  return match ? match[0] : urlOrId;
}

function jsonOutput(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(
    ContentService.MimeType.JSON
  );
}
