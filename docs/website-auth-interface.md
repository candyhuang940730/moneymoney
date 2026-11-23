# 地下網站身分入口介面約定

地下網站目前提供註冊、登入與登出。公開註冊的使用者一律由後端建立為 `buyer`，前端不提供角色欄位。註冊成功後會回到登入頁並顯示一次性提示；不會自動登入。

| 操作 | 路徑 | 表單資料 |
| --- | --- | --- |
| 登入首頁 | `GET /site/` | 無 |
| 註冊頁 | `GET /site/register` | 無 |
| 建立買家帳號 | `POST /site/register` | `username`、`password`、`confirm_password` |
| 登入表單 | `POST /site/login` | `username`、`password` |
| 登出 | `POST /site/logout` | 無 |
| 忘記密碼入口 | `GET /site/forgot-password` | 無 |
| 商品頁 | `GET/POST /site/products` | 暫無 | 已實作正常商品頁面（BTC 計價，身分檢查已註解，以 `products-example.json` 範例檔展示） |

註冊時，帳號需為 3–32 個字元且不可包含空白；密碼需為 8–128 個字元，並與確認密碼相同。後端也會檢查重複帳號。驗證失敗時，註冊頁會顯示錯誤訊息，密碼欄位不會回填。登入使用 Flask Session 記錄使用者 ID。

`GET /site/forgot-password` 尚未實作，現有連結會得到 404；商品頁、環境重置按鈕、FLAG 檢驗器與進度紀錄也留待後續階段。登入、註冊和登出表單仍需 CSRF 保護，應在對外部署前補上。預定挑戰漏洞的具體行為會在相應關卡階段確認。

