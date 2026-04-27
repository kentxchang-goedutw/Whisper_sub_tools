# Whisper 本地字幕生成工具（Windows）

這是一個在 Windows 上離線/本機執行的 Whisper 字幕生成 GUI 工具（CustomTkinter），可把音訊/影片辨識成 `SRT` 字幕檔，並提供字幕切段規則與常用參數設定。

## 1. 下載與執行（給一般使用者）

1. 到本專案的 GitHub 下載 `dist/SubtitleTool.exe`。
2. 直接執行 `SubtitleTool.exe`。
3. 點「檢查環境」確認目前環境狀態（CUDA、ffmpeg、套件等）。
4. 點「選擇檔案」選擇音訊/影片。
5. 選擇模型與參數後點「開始辨識」。
6. 產生字幕後點「另存 SRT」或在輸出區查看/複製。

注意：
- 第一次使用某個模型（例如 `medium`、`large-v3`）時，會自動下載模型檔（需要網路）。之後會走快取。
- 若公司/學校網路擋 Hugging Face 下載，請先改用可連網環境啟動一次完成下載，或改用原始碼模式自行配置快取路徑。

## 2. 操作流程（一步一步）

1. 「檢查環境」
   - 會顯示 Python 版本、程式執行位置、是否偵測到 `ffmpeg`、是否偵測到 `nvidia-smi`、CUDA 裝置數與建議使用裝置。
2. 「選擇檔案」
   - 支援常見音訊/影片：`mp3/mp4/wav/m4a/ogg/webm/mkv/mov/aac/flac` 等。
3. 參數設定
   - `模型`：`tiny/base/small/medium/large-v3`（越大越準、越吃資源、第一次下載越久）。
   - `語言`：可指定 `zh/en/ja/ko/es` 或讓模型自動判斷。
   - `裝置`：`auto/cuda/cpu`。
   - `compute`：GPU 常用 `float16`；CPU 會自動改用較省資源的型別（程式內有保護邏輯）。
   - `字幕切段`：fine/standard/loose（影響每段最大字數、最大秒數、遇標點切段等）。
4. 「開始辨識」
   - 會在狀態列顯示目前進度與耗時，完成後會顯示可保存的字幕內容。
5. 「另存 SRT」
   - 儲存為 `SRT` 字幕檔。

## 3. 輸出位置

程式預設會建立 `outputs/` 資料夾，用來放輸出字幕檔或你自行保存的檔案。

## 4. 常見問題（Troubleshooting）

### 4.1 ONNXRuntime / VAD 檔案不存在

若出現類似：
`Load model ... faster_whisper/assets/silero_vad_v6.onnx failed. File doesn't exist`

請確認你使用的是本 repo 最新的 `SubtitleTool.exe`。此專案已把 `silero_vad_v6.onnx` 連同 exe 一起打包。

### 4.2 缺少 `cublas64_12.dll`

若出現類似：
`Library cublas64_12.dll is not found or cannot be loaded`

代表該電腦缺少 GPU/CUDA 需要的 NVIDIA runtime。新版程式會在 CUDA 載入失敗時自動改用 `CPU / int8` 繼續辨識；如果一定要用 GPU，請在該電腦安裝相容的 CUDA runtime。

### 4.3 找不到 ffmpeg

如果「檢查環境」顯示 `ffmpeg：未在 PATH 偵測到`：
- 建議安裝 ffmpeg 並加入系統 PATH，再重新開啟程式。
- 若你只在 GUI 裡辨識一般媒體，多數情境下 PyAV 仍能工作，但遇到特殊封裝/編碼時仍建議裝 ffmpeg 以提升相容性。

### 4.4 第一次辨識很久、或卡在下載

第一次用某個模型會下載模型檔：
- 確認網路可連線（公司網路可能封鎖）
- 換小模型先測試（例如 `base` 或 `small`）
- 改用可連線環境先跑一次，下載完成後再帶回離線環境使用

### 4.5 CUDA/GPU 無法用

「檢查環境」顯示 CUDA 裝置數為 0 時：
- 先用 CPU 模式可正常工作（較慢）
- 要用 GPU 需符合你的 NVIDIA 驅動與 CUDA/相關 runtime 相容條件（取決於你安裝的 `ctranslate2`/`onnxruntime` 版本與硬體）

### 4.6 防毒軟體誤判

PyInstaller 打包的 exe 在部分環境可能被誤判：
- 建議從可信任來源下載
- 若公司端點防護會隔離檔案，需由 IT 加白名單

## 5. 從原始碼執行（給開發者）

環境：Windows + Python（建議 3.10+；本專案作者環境為 3.13）。

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python .\app.py
```

## 6. 重新打包 exe（給開發者）

此 repo 已提供可重現打包流程：

```powershell
.\build_exe.ps1
```

輸出：
- `dist/SubtitleTool.exe`

說明：
- 會先用 `tools/make_icon.py` 產生 `assets/app_icon.ico`，再用 PyInstaller 依照 `subtitle_tool.spec` 打包。
- 為避免中文路徑造成 PyInstaller 在 Windows 建置時出錯，打包會在 `%TEMP%` 的 ASCII 路徑完成後再把 exe 複製回本專案的 `dist/`。
