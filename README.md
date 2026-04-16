[portfolio_README (1).md](https://github.com/user-attachments/files/26789710/portfolio_README.1.md)
# happy-pro-
金開心含回測
# 📐 最適投資組合優化器

結合債券（94檔）、基金（15檔）、自選股票/ETF，計算最適配置比例。

## 功能

- 債券含息總報酬計算（資料不足自動用 VCLT/LQD 補齊）
- 基金淨值從 Google Drive 自動讀取
- 股票/ETF 透過 yfinance 即時抓取
- 相關係數矩陣熱力圖
- 蒙地卡羅有效前緣模擬
- 三種優化策略：最大夏普、最小風險、鎖定目標報酬
- PDF 報告生成（密碼保護）

## 使用方式

1. 輸入密碼登入
2. 側邊欄選擇回測期間與優化目標
3. 選擇債券、基金、自選股票
4. 點擊「開始計算」
5. 查看相關係數、有效前緣、最適組合
6. 下載 PDF 報告

## 設定

需在 Streamlit Secrets 設定：
```
GOOGLE_CREDENTIALS = "..." # 服務帳號 JSON
BOND_FOLDER_ID = "1k0RxJn5KKCTWdTEDZqq0Q5hnfwkuPgGK"
FUND_FOLDER_ID = "1i1-zUzLNnuwo2NVWijubvBICLbladZQO"
```

## 免責聲明

本工具僅供內部教育訓練使用，請勿外流。
