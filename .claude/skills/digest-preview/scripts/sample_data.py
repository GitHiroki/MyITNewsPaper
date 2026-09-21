"""モック用のサンプルデータ（実際の API は叩かない）

デザイン比較用なので内容はダミー。件数・文字量は普段の digest に近づけてある。
"""

SAMPLE: dict[str, list[dict]] = {
    "Zenn トレンド": [
        {
            "title_ja": "ビルドを Rust 製ツールに移行して CI を3分から40秒にした話",
            "url": "https://zenn.dev/example/articles/build-speedup",
            "summary": "webpack から Rust 製バンドラへ移行し、CI のビルド時間を約4分の1に短縮した記録です。移行時に詰まった設定差分も整理されています。",
        },
        {
            "title_ja": "TypeScript 6.0 の型推論まわりで変わったところまとめ",
            "url": "https://zenn.dev/example/articles/ts6-inference",
            "summary": "条件型の推論強化と、既存コードで壊れやすいパターンを実例つきで解説しています。",
        },
        {
            "title_ja": "個人開発を GitHub Actions だけで回す構成",
            "url": "https://zenn.dev/example/articles/actions-only",
            "summary": "サーバーを持たずに定期実行・デプロイ・通知までを Actions に寄せた構成例です。",
        },
    ],
    "GitHub Trending": [
        {
            "title_ja": "opencode-ai/opencode",
            "url": "https://github.com/example/opencode",
            "summary": "ターミナルで動く AI コーディングエージェント。複数モデルに対応しています。",
        },
        {
            "title_ja": "vercel/ai",
            "url": "https://github.com/example/ai",
            "summary": "TypeScript で AI アプリを作るためのツールキットです。",
        },
        {
            "title_ja": "duckdb/duckdb",
            "url": "https://github.com/example/duckdb",
            "summary": "分析用途の組み込み型データベース。単一ファイルで動作します。",
        },
    ],
    "Hacker News": [
        {
            "title_ja": "SQLite が本番データベースとして十分な理由",
            "url": "https://news.ycombinator.com/item?id=00000001",
            "summary": "単一サーバー構成なら SQLite で十分に戦えるという主張と、その限界についての議論です。",
        },
        {
            "title_ja": "大規模モノレポでのビルドキャッシュ戦略",
            "url": "https://news.ycombinator.com/item?id=00000002",
            "summary": "リモートキャッシュの当たり率を上げるための依存関係の切り方を紹介しています。",
        },
    ],
    "dev.to": [
        {
            "title_ja": "コンテナイメージを小さくする10の手順",
            "url": "https://dev.to/example/slim-images",
            "summary": "マルチステージビルドと不要レイヤーの削除で、イメージサイズを大幅に削減する手順です。",
        },
        {
            "title_ja": "はじめての OpenTelemetry 計装",
            "url": "https://dev.to/example/otel-intro",
            "summary": "トレース・メトリクス・ログを最小構成で計装する入門記事です。",
        },
    ],
    "gihyo.jp": [
        {
            "title_ja": "Linux カーネル 6.18 の主な変更点",
            "url": "https://gihyo.jp/article/example/kernel618",
            "summary": "スケジューラとファイルシステムまわりの改善を中心に、実運用への影響を解説しています。",
        },
        {
            "title_ja": "PostgreSQL 19 の新機能を試す",
            "url": "https://gihyo.jp/article/example/pg19",
            "summary": "論理レプリケーションの強化点を手元環境で検証した記事です。",
        },
    ],
    "OpenAI Blog": [
        {
            "title_ja": "エージェント向けの新しい評価フレームワークを公開",
            "url": "https://openai.com/index/example-eval/",
            "summary": "長時間タスクを実行するエージェントの成功率を測るための評価基盤が公開されました。",
        },
        {
            "title_ja": "推論モデルのコストを下げるためのキャッシュ設計",
            "url": "https://openai.com/index/example-cache/",
            "summary": "プロンプトキャッシュの使いどころと、コスト削減の実測値が示されています。",
        },
    ],
    "Google Research Blog": [
        {
            "title_ja": "長文コンテキストの検索精度を上げる新手法",
            "url": "https://research.google/blog/example-longctx/",
            "summary": "100万トークン級の文脈から必要な箇所を取り出す手法と、ベンチマーク結果の報告です。",
        },
    ],
    "The Hacker News": [
        {
            "title_ja": "広く使われる CI ツールに認証バイパスの脆弱性",
            "url": "https://thehackernews.com/example/ci-auth-bypass.html",
            "summary": "セルフホスト構成が影響を受けます。修正版が公開済みで、早期の更新が推奨されています。",
        },
        {
            "title_ja": "npm パッケージを狙った新たなサプライチェーン攻撃",
            "url": "https://thehackernews.com/example/npm-supply-chain.html",
            "summary": "インストール時スクリプトから認証情報を収集する手口が確認されています。",
        },
    ],
    "ITmedia": [
        {
            "title_ja": "国内企業の生成AI導入率、前年から大きく伸びる",
            "url": "https://www.itmedia.co.jp/news/articles/example1.html",
            "summary": "調査によると業務利用が進む一方、社内ルール整備が追いついていない実態も見えてきました。",
        },
        {
            "title_ja": "大手SIer、社内システムの内製化方針を発表",
            "url": "https://www.itmedia.co.jp/news/articles/example2.html",
            "summary": "外注比率を下げ、3年かけて内製体制へ移行する計画です。",
        },
    ],
    "日経XTECH": [
        {
            "title_ja": "基幹システム刷新、移行遅延の原因を分析",
            "url": "https://xtech.nikkei.com/atcl/nxt/example1/",
            "summary": "要件定義の曖昧さとテスト工数の見積もり不足が主因として挙げられています。",
        },
        {
            "title_ja": "自治体の標準準拠システム、移行期限の現在地",
            "url": "https://xtech.nikkei.com/atcl/nxt/example2/",
            "summary": "進捗状況と、間に合わない自治体への対応方針がまとめられています。",
        },
    ],
}
