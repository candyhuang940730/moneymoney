# Hydra Underground

這是一套供使用者自行部署的網路安全教學 CTF 網站。目前包含導覽入口、任務中心簡報，以及地下網站的登入首頁與調查簡報彈窗。登入、忘記密碼、FLAG 提交和環境重置功能尚未實作。

## Conda 環境

本專案的 Python 依賴記錄在 `environment.yml`。請由環境使用者自行執行：

```cmd
cd /d "C:\Users\Computer\Documents\CTF\moneymoney"
conda env create -f environment.yml
conda activate hydra-underground
python -m flask --app app run
```

開啟 `http://127.0.0.1:5000/`，從導覽入口前往任務中心或地下網站。也可以直接開啟 `/ctf/` 與 `/site/`。目前登入表單預留 `POST /site/login`，忘記密碼連結預留 `GET /site/forgot-password`；這兩個路由在下一階段由專案開發者實作。

## 目前範圍

- 最外層導覽頁與任務中心的調查簡報、五章路線。
- 地下網站登入首頁，沒有公開註冊入口。
- 故事簡報首次進入時顯示，並可透過頁面按鈕重新開啟。
- 登入與忘記密碼的後端接口規格見 `docs/website-auth-interface.md`。
