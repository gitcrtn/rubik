# rubik

Rubik Note

bottle, sqlite3, jinja2, html5, three.js, javascriptの練習がてら作成しました。

main.pyをPython2.7で実行するとサーバーが起動し、
http://localhost:8080/rubikにアクセスするとページを閲覧出来るようになります。

data.dbは無くても初期化時に生成されますが、サンプルとして置いておきます。

ルービックキューブ練習用のメモツールとして作成していましたが、途中でボツにしました。
そのため、解法の登録や編集をする機能や画面が未実装です。
もし機会があれば更新するかもしれません。

キューブのサムネイル生成や、サムネイル編集で、three.jsを使用しています。
WebGL版ではなく、CSS3版を使っているため、iPadなどWebGL非対応の環境でも閲覧可能です。

テスト環境: Windows7 x64, Windows8.1 x64

license: MIT
