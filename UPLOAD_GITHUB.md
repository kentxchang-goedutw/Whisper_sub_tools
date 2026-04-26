# 上傳到 GitHub（含大檔 EXE）

本專案的 `dist/SubtitleTool.exe` 約數百 MB，超過 GitHub 一般 repo 的單檔 100MB 限制，因此已用 **Git LFS** 追蹤 `dist/*.exe`。

## 1. 先確認已安裝 Git LFS

```powershell
git lfs version
git lfs install
```

## 2. 推送到 GitHub（需要互動登入）

因為此環境工具無法彈出瀏覽器登入視窗，請你在「本機互動式 PowerShell」中到此資料夾執行：

```powershell
cd "P:\Public Folder\html\python\本地字幕生成工具"
git push -u origin main
```

第一次推送通常會透過 Git Credential Manager 開啟瀏覽器讓你登入 GitHub。

如果 push 完成後發現 LFS 物件沒有上傳成功，再補跑：

```powershell
git lfs push --all origin main
```

## 3. 讓一般使用者好下載（建議）

Git LFS 對一般使用者不友善。建議你在 GitHub 網站建立 Release，並把 `dist/SubtitleTool.exe` 上傳成 Release Asset。

