# terminal-autocomplete

Apple SiliconのMac・zsh・Ghostty向けに、Figのようなターミナルの自動補完を実現するプロジェクトです。

## 目的

FigからAmazon Q Developer CLI、Kiro CLIへ引き継がれたターミナル補完の使い勝手を、自分で継続して使い、改善できる形で実現します。

Kiro CLI 3.0への移行に伴うインライン補完とCLIデスクトップアプリの廃止が、このプロジェクトを始めるきっかけです。詳しくは[Kiroの公式告知](https://kiro.dev/blog/cli-3/)を参照してください。

入力中のコマンドに応じて、サブコマンド・オプション・引数などの候補をターミナル内に表示し、選択して入力できる体験を目指します。

## 初期の対象環境

| 項目 | 対象 |
| --- | --- |
| OS | macOS（対応するバージョンは今後決定） |
| CPU | Apple Silicon（arm64） |
| シェル | zsh |
| ターミナル | Ghostty |

まずはこの組み合わせに絞って、実装と動作検証を進めます。

## 参考にする公開ソース

- [aws/amazon-q-developer-cli-autocomplete](https://github.com/aws/amazon-q-developer-cli-autocomplete)：旧Amazon Q Developer CLIの補完機能を含む実装。MIT OR Apache-2.0で公開されています。
- [withfig/autocomplete](https://github.com/withfig/autocomplete)：各種CLIのサブコマンド・オプション・引数などを記述した補完定義。MITで公開されています。

現在のKiro CLIはクローズドソースのため、旧Amazon Q Developer CLIの公開実装とFigの補完定義を調査の出発点にします。

旧実装では、主に次の部分が参考になります。

| パス | 役割 |
| --- | --- |
| `crates/figterm` | シェルとターミナルの間に入り、入力内容や作業ディレクトリなどを取得する |
| `crates/fig_integrations` | シェルとの連携 |
| `packages/autocomplete-parser` | 補完定義の読み込みと引数の解析 |
| `packages/autocomplete` | 補完候補の生成・絞り込みとReact UI |
| `crates/fig_desktop` | 補完ウィンドウを表示するデスクトップアプリ |
| `crates/fig_input_method` | macOSでのカーソル位置の取得 |

## 現在の状態

開発準備の段階です。アプリの実装、参考ソースの取得、ビルド・実機での動作検証はまだ行っていません。

旧実装をフォークして補完部分を切り出す方法と、必要な部品を再利用して組み直す方法を検討します。採用する構成、依存関係、配布方法は今後決めます。

灰色の文字で続きを提案するインライン補完を含めるかどうかも、今後検討します。

## 開発の進め方

同じタスクを、Claudeによる作業内容の検討、Codexによる実装・テスト・敵対的レビュー、Claudeによる実装内容とテストの外部レビューの順に進めます。

Codexでarenaを使う場合は、候補比較の独立審査もClaudeが担当します。独立審査と実装後の外部レビューは、それぞれ新しいセッションでOpus・xhighを指定して行います。詳しい手順は[Claudeレビューの運用ルール](.agents/claude-review.md)を参照してください。

## ライセンス

本プロジェクトは[MIT License](LICENSE)で公開しています。

公開コードを取り込む際は、各ファイルと依存ライブラリのライセンス条件を確認し、必要な著作権表示・ライセンス文を保持します。
