# スキーマ検証パターン

## 基本原則
- すべての入力データはZodスキーマで検証する
- スキーマは階層構造を持つ（base → category → request）
- スキーマテストは__tests__ディレクトリに配置する

## 検証フロー
- `useJsonValidation` → `request.schema.ts` → `category.schema.ts` → `base.schema.ts`

## ベストプラクティス
- 各スキーマは単一責任の原則に従う
- バリデーションエラーメッセージは日本語で統一する
- 複雑なスキーマは小さな部分に分割する
