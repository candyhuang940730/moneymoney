# Hydra Underground

這是一套供使用者自行部署的網路安全教學 CTF 網站。目前包含導覽入口、任務中心簡報，以及地下網站的註冊、登入與調查簡報彈窗。忘記密碼、商品頁、FLAG 提交和環境重置功能尚未實作。

## Conda 環境

本專案的 Python 依賴記錄在 `environment.yml`。請由環境使用者自行執行：

```cmd
cd /d "C:\Users\Computer\Documents\CTF\moneymoney"
conda env create -f environment.yml
conda activate hydra-underground
set HYDRA_SECRET_KEY=請換成你自行產生的隨機密鑰
python -m flask --app app run
```

若 Conda 環境已建立，可略過 `conda env create`。啟動前請將 `HYDRA_SECRET_KEY` 設為自己的隨機值。開啟 `http://127.0.0.1:5000/`，從導覽入口前往任務中心或地下網站；也可以直接開啟 `/ctf/`、`/site/` 或 `/site/register`。忘記密碼連結仍預留給後續階段。

## 目前範圍

- 最外層導覽頁與任務中心的調查簡報、五章路線。
- 地下網站可公開註冊買家帳號，並以帳號密碼登入、登出。
- 故事簡報首次進入時顯示，並可透過頁面按鈕重新開啟。
- 註冊、登入與尚未實作的忘記密碼接口狀態見 `docs/website-auth-interface.md`。
