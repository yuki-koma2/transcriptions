# ワークフローパターン

## QRコード処理フロー
1. QRコードをスキャン・テキストデータを取得
2. SimpleQrTextコンポーネントでテキスト処理
3. useJsonValidationでZodスキーマ検証
4. 検証済みデータをプレビュー表示
5. useSaveRequestでFirebaseに保存

## 認証フロー
1. ログイン画面で認証情報入力
2. Firebase認証を使用してユーザー検証
3. AuthProviderでトークン管理
4. useAuthTokenでAPIリクエスト時のトークン付与
5. 認証失敗時はログイン画面にリダイレクト

## テストパターン
1. カスタムフックの単体テスト
2. Zodスキーマの検証テスト
3. E2Eテストでユーザーフローの検証
4. モックを使用したFirebase依存テスト
