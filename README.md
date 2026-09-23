# FMラジオストリームURL変更検知

指定したストリームURL管理用XMLを定刻に取得し、`radiru_config > stream_url > data > areajp`配下の東京要素にある`fmhls`を、SQLiteに保存された前回値と比較します。

- URLが同じ場合: `ストリームURLに変更はありませんでした` と実行日時をログ保存
- URLが変わった場合: 変更内容をログ保存し、Push通知後に取得済みURLを更新
- 初回実行時: 変更ありとしてログ保存、Push通知、URL保存を行う
- 実行ログと取得済みURLは別テーブルで管理

## 設定

```sh
cp config.example.ini config.ini
# config.iniのtarget_url、stream_url_pattern、Push通知設定を編集
```

`notification.endpoint`には、ntfyなどHTTP POSTを受け付けるPushサービスのpublish URLを指定します。`token`と`topic`は必要なサービスに合わせて設定してください。

## 実行

```sh
PYTHONPATH=src python3 -m fm_monitor --config config.ini --once
```

Raspberry Piでは、`systemd/radiostream-monitor.service`と`systemd/radiostream-monitor.timer`を`/etc/systemd/system/`へ配置し、`WorkingDirectory`と`ExecStart`を配置先に合わせてから有効化します。

```sh
sudo systemctl daemon-reload
sudo systemctl enable --now radiostream-monitor.timer
systemctl list-timers radiostream-monitor.timer
```

## テスト

外部パッケージなしで実行できます。

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -v
```
