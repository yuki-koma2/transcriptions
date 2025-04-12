# Firebase連携パターン

## 基本構成
- Firebaseクライアント設定は`src/lib/firebase/`ディレクトリに集約
- 認証関連の処理は`useAuthToken`フックに集約
- Firestoreデータ変換ロジックは`lib/converter/`に配置

## 認証フロー
1. ログイン画面で認証情報入力
2. Firebase認証を使用してユーザー検証
3. AuthProviderでトークン管理
4. useAuthTokenでAPIリクエスト時のトークン付与
5. 認証失敗時はログイン画面にリダイレクト

## データアクセスパターン
- リポジトリパターンを使用（`connectRequestRepository.ts`）
- サービス層でビジネスロジックを実装（`connectRequestService.ts`）
- データ変換処理は専用のコンバーターで実装

## テスト戦略
- モックを使用したFirebase依存テスト
- リポジトリとサービスの単体テスト
- E2Eテストでの認証フロー検証
