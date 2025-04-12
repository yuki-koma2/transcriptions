# firestore DB設計規約


# 概要

FirestoreのDB設計時にきを付けるべきことを記載していく。


---

# Collectionの設計

firestoreの基本単位となるcollectionにおいて共通する設計。

## 命名：トップレベルのコレクションは接尾にCollectionをつける。SUBコレクションはつけない

【 Why 】

firestoreはNoSQLでありつつも特殊な構造をしている。

親子関係をつけることができるものの、取得した後や取得時はどちらが親なのかが判別が難しくなる（できないことはない）

そのため、データとして起点になるTopLevelのcollectionには明示的にわかるように区別する。

【 Example 】

```jsx
<Good>
TopLevelCollection
TopLevelCollection/{documentId}
TopLevelCollection/{documentId}/SubItem
TopLevelCollection/{documentId}/SubItem/{subCollectionDocumentId}
TopLevelCollection/{documentId}/SubItem/{subCollectionDocumentId}/SubSubItem

<Bad>
TopLevelCol
TopLevelCol/{documentId}
TopLevelCol/{documentId}/SubCollecition
TopLevelCol/{documentId}/SubCollecition/{subCollectionDocumentId}
TopLevelCol/{documentId}/SubCollecition/{subCollectionDocumentId}/SubSubCollection
```

## document の id は collection のフィールドに持たない.

【 Why 】

document IDは一意である必要があるが、フィールドにも持つ場合はデータ作成時にクライアント側でdocument idを発行する必要がある。

これはfirestoreの機能を使うことができなくなるほか、フィールド値には一意性を担保できない、

使い方を誤ってフィールドのdocument idでクエリを走らせるとパフォーマンスが悪くなるなどの悪影響が考えられる。

【 Example 】

```markdown
<Good>
path UserCollection/111-1111-1111
data {
			name: "sample name"
			}

<Bad>
path UserCollection/111-1111-1111
data {
			documentId: "111-1111-1111"
			name: "sample name"
			}
```

## 【命名規則】コレクションや外部情報の関係性を表すフィールド

【 Why 】

フィールド名はデータの意味や関連性を直感的に理解できるようにするために重要。
特に他のコレクション、親コレクション、外部情報との関係性を表すフィールドは一貫性を持たせてチーム内で認識を合わせる必要がある。
そのため、命名規則を作成

【命名規則】

- コレクション間の関係を表す場合
    - related + コレクション名 + Id
- コレクションとサブコレクションの関係
    - parent + コレクション名 + Id
- その他
    - 外部で決めたID
        - 〜〜Id
            - sfdcId
            - connectId
    - マスターテーブル
        - Firestoreでマスターを作成する場合
            - mst + コレクション名 + Id

【Example】

```jsx
コレクション間の関係を表す命名規則 requestCollectionと関係を持つ
<Good>
path UserCollection/111-1111-1111
data {
			relatedRequestId: "111-1111-1111"
			name: "sample sub name"
			}

<Bad>
path UserCollection/111-1111-1111
data {
			requestId: "111-1111-1111"
			name: "sample sub name"
			}

コレクションとサブコレクションの関係を表す命名規則
<Good>
path UserCollection/111-1111-1111/Profile/222-aaaa
data {
			parentUserId: "111-1111-1111"
			name: "sample sub name"
			}

<Bad>
path UserCollection/111-1111-1111/Profile/222-aaaa
data {
			userId: "111-1111-1111"
			name: "sample sub name"
			}



マスターテーブルと関係がある場合
<Good>
path facilityCollection/111-1111-1111
data {
			mstFacilityId: "111-1111-1111"
			name: "sample sub name"
			}

<Bad>
path facilityCollection/111-1111-1111
data {
			facilityId: "111-1111-1111"
			name: "sample sub name"
			}

その他 外部システムのIdを使用する場合
<Good>
path userCollection/111-1111-1111
data {
			externalSystemId: "111-1111-1111"
			name: "sample sub name"
			}

<Bad>
path userCollection/111-1111-1111
data {
			customSystemId: "111-1111-1111"
			name: "sample sub name"
			}

マスターテーブルと関係がある場合
<Good>
path userCollection/111-1111-1111
data {
			mstCategoryId: "111-1111-1111"
			name: "sample sub name"
			}

<Bad>
path userCollection/111-1111-1111
data {
			categoryId: "111-1111-1111"
			name: "sample sub name"
			}
```

## サブコレクションには親のdocument Idを持つ。

【 Why 】

firebase sdkから利用する場合はsnapshotの情報からparentのパスが取れるので問題はない。

しかしBQ経由で分析する場合、pathから親のIDを取るのがかなり煩雑になってしまう。

プロダクション的には不要でがあるが、RDBのFKと同じ使い方をすると多少コードも見やすくなるので、この方法を再使用する。

【命名規則】

- parent + コレクション名 + Id

【Example】

```jsx
<Good>
path UserCollection/111-1111-1111/Profile/222-aaaa
data {
			parentUserId: "111-1111-1111"
			name: "sample sub name"
			}

<Bad>
path UserCollection/111-1111-1111/Profile/222-aaaa
data {
			name: "sample sub name"
			}
```

## createAt, updateAt はどのデータにも必ずつける。アプリケーションからは利用しない

作成日時、更新日時はシステムが自動で入れる

監査的な観点から事実のみを入れる。参照は良いが自分で値を設定してはいけない。

この２つは必ず設定する。

【 Why 】

createAt, updateAtはいつそのデータが更新されたのか、作成されたのかという情報を保存する。

データの更新情報を保存する特別なフィールド。

これをアプリケーションから書き換えてしまったり、本番データをいじってしまうと本来の意味とは異なる状態になりバグを生む可能性が大きくなる。

---

# データ型

### 日付型の扱いは用途によって使い分ける

※ これらの日付・日時の扱いに関しては、共通ライブラリーを作成して、それを利用するようにする。

【 Why 】

【Example】

日付のみ必要な場合Date型 string (YYYY/MM/DD or  YYYY-MM-DD)

ユーザーの入力を受けて時分まで必要な場合TimeStamp

ユーザーの入力を受けない場合 server TimeStamp。例

|  | 型 | format | 説明 | 例 |
| --- | --- | --- | --- | --- |
| 日付（年月日） | String | YYYY/MM/DD | 日付のみ必要な場合Date型 | createRoomDate |
| 日時（年月日 時分秒） | Timestamp | Timestamp | ユーザーの入力を受けて時分まで必要な場合などで | activatedAt |
| createAt等システムの記録 | Timestamp | serverTimeStamp | ユーザーの入力を受けず、操作時間を記録する類 | create At , update At |

### Firebase フィールドのnullable、optional、undefinedについて

- 項目を持っていて欲しい、かつ更新時にも確実に持って欲しいフィールド
    - 例えば、parentIdのような後から追加した必須フィールド
    - **該当の型 || undefinedで定義をし、firestoreに追加時にチェックをする。**
        - チェックして項目がない場合はerrorを投げる

- 項目自体はあって欲しいが、値は入ってなくてもいいフィールド
    - nullableを使用

- 項目自体があってもなくてもいい場合（**非推奨**）
    - 例えば、コネクトのfacilityCollectionのid
    - **optionalを使用**


# 命名規則

### 形による命名規則

| 型 | 命名 | example | 備考・考え方 | NG例 |
| --- | --- | --- | --- | --- |
| string (Date/日付) | ~Date | createRoomDate | 日付のみ持つならそれがわかるようにする | createRoomAt |
| TimeStamp | ~At | expiredAt | Timestamp型は全てAtに統一する | expiredDate |
| Boolean | is~ | has~ | 意味が明確な接頭辞 | `isHospitalRead` hiddenForFacility  | true/falseの意味が明確になるように | isHospitalFlag |
| Array<Literal> | 複数系 | `allowedIpAddress` | Listであることが明確になるように複数形で表現する | hospitalList |
| Array<CustomObject> | - | - | 使わない。これをやるならsubCollectionにする。 | -  |
|  |  |  |  |  |

### 特定の項目による命名規則

| フィールド | 命名 | example | 備考・考え方 |
| --- | --- | --- | --- |
| firebase auth UID | ~Uid | userUid | senderUid  | UIDの理由。firebase Uidであることを明示。rulesではfirebase uidと比較することになる。 |
| FK(同一DB) | related + コレクション名 + Id | relatedRequestId |  |
| createAt | - | - | 全てのCollectionで必須 |
| updateAt | - | - | 全てのCollectionで必須 |
| サブコレクションの親Id | parent + コレクション名 + Id | parentRequestId |  |
| 外部のID |  | sfdcId | 外部のIDをそのまま利用 |
| マスターテーブルのID | mst + コレクション名 + Id | mstPrefCodeId |  |
|  |  |  |  |

updateAt