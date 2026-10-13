---
name: artpipe-render-machine
description: Dựng hoặc đổi máy render cho artpipe (ComfyUI) — PC mượn, GPU thuê ngoài, hay máy chủ chạy 24/24. Dùng khi mẻ báo "không gọi được ComfyUI", khi runner offline, khi chuyển sang nhà cung cấp GPU khác, hoặc khi cần biết máy Mac điều khiển từ xa ra sao.
---

# artpipe — máy render

> artpipe sống ở **sanne-kit** (`Tools/artpipe/`), workflow + runner + biến `ARTPIPE_*` đặt trên
> repo `tsan2711/sanne-kit` (không phải repo game). Mọi lệnh `gh variable`/`gh api .../runners`
> dưới đây chạy với `-R tsan2711/sanne-kit`.

**Mac là bàn điều khiển, máy render là một URL.** Đổi máy = đổi một biến trên GitHub,
không sửa file nào trong repo. Nếu phải sửa mã nguồn để chạy trên máy mới thì đó là bug.

## Máy hiện tại: Colab / Kaggle (từ 2026-10-10, PC Windows `NDV-SANNE` đã nghỉ)

Bi mở `Tools/artpipe/render_node.ipynb` trên Colab (Run all, giữ tab) hoặc Kaggle (Save & Run
All, chạy nền ≤12h). Notebook dựng ComfyUI ở localhost + đăng ký runner `artpipe-colab` /
`artpipe-kaggle` (cách A), tự tắt khi rảnh `IDLE_MIN` phút. Biến repo: `ARTPIPE_RUNNER =
["self-hosted","comfyui"]`, `ARTPIPE_PYTHON = python3`. Secret notebook `ARTPIPE_GH_PAT` (Administration RW + Contents Read — sanne-kit private).

- **Ưu tiên Colab:** `bash Tools/artpipe/colab_up.sh` (Safari + PAT trong Keychain `artpipe-gh-pat`; tab phải mở). Kaggle chỉ là dự phòng khi Colab hết quota. Hai runner cùng online thì job chia ngẫu nhiên — muốn chỉ Colab thì xoá runner artpipe-kaggle qua API.
- Bật Kaggle từ Mac: `bash Tools/artpipe/kaggle_up.sh` (kaggle CLI, ~/.kaggle/access_token; PAT ở dataset private tscute/artpipe-secret).
- Không runner nào online → job xếp hàng, `remote.py` chờ (mặc định 1h). **Nhắc Bi mở notebook**
  trước khi gửi mẻ: `gh api repos/tsan2711/sanne-kit/actions/runners --jq '.runners[]|"\(.name) \(.status)"'`.
- Model trên đĩa tạm, mỗi phiên tải lại; làn anim cần `ANIM=True` lúc mở phiên (T4 chậm với Wan 2.2).
- Đừng phơi ComfyUI qua tunnel (ngrok/cloudflared) để dùng cách B: không xác thực, và Colab free
  cấm giao diện web kiểu SD WebUI.

## Ba cách nối, chọn theo tình huống

| Cách | Khi nào | Phải khai gì |
|---|---|---|
| **A. Runner tự dựng trên máy GPU** | máy sau NAT / không muốn phơi cổng ra Internet | var `ARTPIPE_RUNNER` = `["self-hosted","comfyui"]`, var `ARTPIPE_PYTHON` = đường dẫn python của venv ComfyUI |
| **B. Máy GPU có IP công khai** | GPU thuê ngoài, có IP tĩnh | secret `COMFYUI_URL`, và bỏ var `ARTPIPE_RUNNER` |
| **C. Cùng mạng với Mac** | LAN hoặc Tailscale | không cần CI: `COMFYUI_URL=http://<ip>:8188 python3 <sanne-kit>/Tools/artpipe/run.py ... (từ gốc project game)` |

Cách C nhanh hơn hẳn vì bỏ được vòng CI. Cách A an toàn nhất vì ComfyUI **không có xác
thực** — phơi cổng ra Internet nghĩa là ai biết địa chỉ cũng chạy job trên GPU đang trả tiền.

```
gh variable set ARTPIPE_RUNNER --body '["self-hosted","comfyui"]'   # cách A
gh variable set ARTPIPE_PYTHON --body '<...>/ComfyUI/.venv/bin/python'
gh secret   set COMFYUI_URL    --body 'http://<ip>:8188'            # cách B
gh variable delete ARTPIPE_RUNNER                                    # quay về cách B
```

## Dựng máy mới

- Linux (GPU thuê): `bash Tools/artpipe/setup_gpu.sh --dir /workspace/ComfyUI --sdxl`
- Windows: `powershell -ExecutionPolicy Bypass -File Tools/artpipe/setup_pc.ps1 -Dir <đường dẫn> -Sdxl`

Cả hai chạy lại được nhiều lần, bước nào xong thì bỏ qua. Chúng cài luôn `rembg onnxruntime`
— thiếu nó thì **mọi ảnh** bị loại ở khâu tách nền.

## Bốn chỗ đã trả giá khi đổi máy

1. **ComfyUI chỉ quét thư mục models lúc KHỞI ĐỘNG.** Tải checkpoint/LoRA xong mà không
   khởi động lại thì server báo `value_not_in_list` — đọc như sai tên file. `ci_probe` nay
   kiểm cả checkpoint lẫn LoRA và nói thẳng câu này.
2. **Số bước lấy mẫu phải khớp LOẠI checkpoint.** Graph của `sd-turbo` (6 bước, cfg 2) chạy
   với SDXL đầy đủ cho ra ảnh nhoè — mẻ vẫn "thành công", bộ kiểm vẫn chấm, chỉ là ảnh vô
   dụng. `ci_probe` nay cảnh báo khi dưới 12 bước mà checkpoint không phải turbo/lightning/lcm.
3. **`ARTPIPE_PYTHON` là biến của repo, không phải của máy.** Đặt nó rồi chạy trên runner
   của GitHub thì job chết vì đường dẫn không tồn tại. `ci_exec.interpreter()` chỉ dùng nó
   khi file có thật, còn không thì quay về `sys.executable`.
4. **Alias `python.exe` của Microsoft Store** chiếm tên `python` trên Windows, in một dòng
   rồi thoát mã 9009. Workflow nay gọi thẳng `ARTPIPE_PYTHON` khi có runner tự dựng.

## Khi mẻ hỏng, đọc theo thứ tự này

```
gh run list -w artpipe.yml -L 3            # run có được tạo không
gh api repos/{owner}/{repo}/actions/runners --jq '.runners[]|"\(.name) \(.status)"'
gh run view <id> --log | grep -a "máy render còn sống không"
```

`ci_probe` chạy **trước** khi tiêu GPU và bắt gần hết các ca đổi máy. Qua được bước đó mà
vẫn hỏng thì mới đọc log của bước `generate + tier1`.

**Client `remote.py` đôi khi treo im lặng lúc tải artifact** (chạy nền không bắt được
output). Run vẫn xong bình thường — lấy tay:

```
gh api repos/{owner}/{repo}/actions/runs/<id>/artifacts --jq '.artifacts[].name'
gh run download <id> -n <tên> -D <thư mục>
```

## Đừng làm

- Đừng commit thư mục `out*/`. Đã lọt một lần: runner checkout ra, upload-artifact gói lại,
  và client nhận `report.json` của mẻ ba ngày trước — ảnh thật, điểm thật, mẻ khác.
- Đừng nhúng đường dẫn máy vào mã nguồn. Quét lại bằng
  `grep -rnE 'D:\\|C:\\actions|/Users/' Tools/artpipe/*.py` — chỉ được phép xuất hiện
  trong chú thích kể lại lỗi cũ.
