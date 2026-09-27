/**
 * ローカルスクリプトから送られてきたウォッチリスト情報を受け取り、
 * このスクリプトをデプロイしたGoogleアカウント上に新規Googleドキュメントを作成する。
 *
 * デプロイ方法:
 *   1. https://script.google.com/ で新規プロジェクトを作成し、このファイルの内容を貼り付ける
 *   2. 「プロジェクトの設定」→「スクリプト プロパティ」に SHARED_TOKEN を追加し、
 *      ランダムな文字列(合言葉)を設定する。ローカルの .env の APPS_SCRIPT_TOKEN と同じ値にする。
 *   3. 「デプロイ」→「新しいデプロイ」→ 種類「ウェブアプリ」
 *        - 次のユーザーとして実行: 自分
 *        - アクセスできるユーザー: 全員
 *   4. 発行されたウェブアプリのURLを .env の APPS_SCRIPT_URL に設定する
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

    var title = payload.title || '無題のウォッチリスト';
    var items = payload.items || [];

    var doc = DocumentApp.create(title);
    var body = doc.getBody();
    var placeholder = body.getParagraphs()[0]; // create() 直後にある空段落

    items.forEach(function (item, i) {
      var line = (i + 1) + '. ' + item.name;
      if (item.remainingText) {
        line += '（' + item.remainingText + '）';
      }
      var paragraph = body.appendParagraph(line);
      if (item.url) {
        paragraph.editAsText().setLinkUrl(0, line.length - 1, item.url);
      }
    });

    if (items.length > 0 && placeholder.getText() === '') {
      placeholder.removeFromParent();
    }

    doc.saveAndClose();

    return jsonOutput({ ok: true, url: doc.getUrl(), id: doc.getId() });
  } catch (err) {
    return jsonOutput({ ok: false, error: String(err) });
  }
}

function jsonOutput(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(
    ContentService.MimeType.JSON
  );
}
