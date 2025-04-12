# メモリバンクガイド

## 概要
メモリバンクは、プロジェクトの知識を保持し、セッション間で一貫した理解を維持するための重要な仕組みです。すべてのタスクの開始時にメモリバンクファイルを読み込み、プロジェクトの現状と背景を理解します。

## メモリバンク構造

メモリバンクは必須のコアファイルとオプションのコンテキストファイルで構成され、すべてMarkdown形式です。ファイルは明確な階層構造を持ちます：

```mermaid
flowchart TD
    PB[projectbrief.md] --> PC[productContext.md]
    PB --> SP[systemPatterns.md]
    PB --> TC[techContext.md]
    
    PC --> AC[activeContext.md]
    SP --> AC
    TC --> AC
    
    AC --> P[progress.md]
```

### コアファイル（必須）
1. `projectbrief.md`
   - 他のすべてのファイルの基盤となる文書
   - プロジェクト開始時に作成
   - コア要件と目標を定義
   - プロジェクト範囲の真実の源

2. `productContext.md`
   - このプロジェクトが存在する理由
   - 解決する問題
   - どのように機能すべきか
   - ユーザー体験の目標

3. `activeContext.md`
   - 現在の作業の焦点
   - 最近の変更
   - 次のステップ
   - アクティブな決定事項と考慮事項

4. `systemPatterns.md`
   - システムアーキテクチャ
   - 重要な技術的決定
   - 使用中の設計パターン
   - コンポーネント間の関係

5. `techContext.md`
   - 使用されている技術
   - 開発セットアップ
   - 技術的制約
   - 依存関係

6. `progress.md`
   - 動作している機能
   - 構築すべき残りの部分
   - 現在のステータス
   - 既知の問題

### 追加コンテキスト
以下を整理するために、memory-bank/ 内に追加のファイル/フォルダを作成します：
- 複雑な機能のドキュメント
- 統合仕様
- APIドキュメント
- テスト戦略
- デプロイ手順

## コアワークフロー

### プランモード
```mermaid
flowchart TD
    Start[開始] --> ReadFiles[メモリバンクを読む]
    ReadFiles --> CheckFiles{ファイルは完全か？}
    
    CheckFiles -->|いいえ| Plan[計画を作成]
    Plan --> Document[チャットで文書化]
    
    CheckFiles -->|はい| Verify[コンテキストを確認]
    Verify --> Strategy[戦略を立てる]
    Strategy --> Present[アプローチを提示]
```

### アクトモード
```mermaid
flowchart TD
    Start[開始] --> Context[メモリバンクを確認]
    Context --> Update[ドキュメントを更新]
    Update --> Rules[必要に応じて.clinerules更新]
    Rules --> Execute[タスクを実行]
    Execute --> Document[変更を文書化]
```

## ドキュメント更新

メモリバンクの更新は以下の場合に行います：
1. 新しいプロジェクトパターンの発見時
2. 重要な変更の実装後
3. ユーザーが**update memory bank**をリクエストしたとき（すべてのファイルを確認すること）
4. コンテキストの明確化が必要なとき

```mermaid
flowchart TD
    Start[更新プロセス]
    
    subgraph Process
        P1[すべてのファイルを確認]
        P2[現在の状態を文書化]
        P3[次のステップを明確化]
        P4[.clinerules更新]
        
        P1 --> P2 --> P3 --> P4
    end
    
    Start --> Process
```

注：**update memory bank**がトリガーされた場合、一部が更新を必要としない場合でも、すべてのメモリバンクファイルを確認する必要があります。特に現在の状態を追跡するactiveContext.mdとprogress.mdに焦点を当てます。

## プロジェクトインテリジェンス（.clinerules）

.clinerules ファイルは各プロジェクトの学習ジャーナルであり、コードだけでは明らかでない重要なパターン、設定、プロジェクトインテリジェンスを捉えます。ユーザーとプロジェクトの作業を通じて、重要な洞察を発見して文書化します。

```mermaid
flowchart TD
    Start{新しいパターンを発見}
    
    subgraph Learn [学習プロセス]
        D1[パターンを特定]
        D2[ユーザーと検証]
        D3[.clinerules に文書化]
    end
    
    subgraph Apply [使用法]
        A1[.clinerules を読む]
        A2[学習したパターンを適用]
        A3[将来の作業を改善]
    end
    
    Start --> Learn
    Learn --> Apply
```

### 捕捉すべき内容
- 重要な実装パス
- ユーザーの設定とワークフロー
- プロジェクト固有のパターン
- 既知の課題
- プロジェクト決定の進化
- ツール使用パターン

フォーマットは柔軟です - ユーザーとプロジェクトとより効果的に連携するのに役立つ貴重な洞察を捉えることに焦点を当てます。.clinerules はユーザーとの協力を通じてより賢くなっていく生きたドキュメントと考えてください。
