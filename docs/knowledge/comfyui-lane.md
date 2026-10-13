# ComfyUI lane

Máy này (M2, 8GB RAM, ~5GB đĩa trống) **không chạy ComfyUI**. Nó chỉ là client: `gen.ComfyUI`
gọi HTTP sang máy khác, phần còn lại của pipeline (matte → tier-1 → tier-2 → sheet →
calibrate → import_unity) không đổi một dòng.

```
python3 tools/artpipe/run.py --out out --tier2 generate --provider comfyui \
    --model sd_turbo.safetensors --variants 4 --seed 1000
```

Địa chỉ server lấy theo thứ tự: `--host` → `$COMFYUI_URL` → `http://127.0.0.1:8188`.
Server ở xa (tunnel/reverse proxy) thì đặt thêm `$COMFYUI_TOKEN`, provider sẽ gửi
`Authorization: Bearer`. Không có token thì **không** gửi header rỗng.

## Graph là dữ liệu, không phải code

`workflows/*.json` phải là **API format** (ComfyUI → Export (API)). Format UI (`nodes`/`links`)
bị `/prompt` từ chối.

artpipe chỉ thay đúng những thứ **bắt buộc phải khác nhau giữa các ảnh**:

| chuỗi | nguồn |
|---|---|
| `{{PROMPT}}` | `prompt.build()` từ art-direction |
| `{{NEGATIVE}}` | `generation.negative_prompt` trong art-direction |
| `{{SEED}}` | `--seed` + chỉ số biến thể |
| `{{CKPT}}` | `--model` |
| `{{WIDTH}}` / `{{HEIGHT}}` | `icon.canvas.width` |

Mọi thứ còn lại — sampler, steps, cfg, scheduler, node ControlNet/LoRA sau này — **do người
sửa trong UI**, và được **đọc ngược ra** vào provenance chứ không bị ghi đè. Nghĩa là cái
graph đang chạy luôn là cái graph trong file, không có tham số ẩn ở tầng Python.

`model_version` trong provenance = sha256 của graph đã thay. Đổi sampler = đổi generator,
nên nó phải đổi theo; cùng một checkpoint qua hai graph khác nhau **không phải** cùng một
máy sinh.

Thiếu `{{PROMPT}}`/`{{SEED}}`/`{{CKPT}}` → provider **từ chối chạy**. Đây là lỗi đắt nhất
của lane này: graph vẫn chạy ngon nhưng bỏ qua seed thì ra 20 ảnh giống hệt nhau kèm 20
file provenance khai 20 seed khác nhau, và không check pixel nào ở dưới phát hiện được.
`selftest.py` mục 6 kiểm chuyện này offline, không cần server.

## Dựng máy build

Đĩa là ràng buộc thật, không phải tiền:

- `icon_txt2img.json` — `CheckpointLoaderSimple`, cần file `sd_turbo.safetensors` (~2.5GB)
  trong `ComfyUI/models/checkpoints/`.
- `icon_txt2img_diffusers.json` — `DiffusersLoader`, dùng lại thư mục diffusers đã có sẵn
  trong cache HuggingFace, khỏi tải lại:
  ```
  ln -s ~/.cache/huggingface/hub/models--stabilityai--sd-turbo/snapshots/<hash> \
        ~/ComfyUI/models/diffusers/sd-turbo
  python3 tools/artpipe/run.py --out out generate --provider comfyui \
      --workflow tools/artpipe/workflows/icon_txt2img_diffusers.json --model sd-turbo
  ```

torch đã có trong `tools/artpipe/.venv` (~950MB, cho tier 2) — chạy ComfyUI bằng chính
interpreter đó thì không phải tải torch lần hai.

## CI/CD

Workflow nằm ở **sanne-kit**: `sanne-kit/.github/workflows/artpipe.yml` (artpipe là tool dùng chung,
không thuộc game nào). Mỗi mẻ checkout thêm thư mục project của game vào `game/<project>` (sparse,
không LFS) bằng secret `GAME_REPO_TOKEN`, rồi mọi bước `run:` chạy với
`working-directory: game/<project>` và `ARTPIPE_PROJECT` trỏ vào đó. `upload-artifact` ghi
`game/<project>/out/...` (nó tính từ gốc workspace, không theo `working-directory`).

Runner tự dựng phải đăng ký vào **repo sanne-kit** (một runner chỉ thuộc một repo với tài khoản
cá nhân). Đổi repo = gỡ đăng ký cũ rồi `config.cmd` lại với token mới:

```
gh api -X POST repos/tsan2711/sanne-kit/actions/runners/registration-token --jq .token
# trên PC, trong thư mục actions-runner:
.\config.cmd remove --token <token gỡ của repo cũ>
.\config.cmd --url https://github.com/tsan2711/sanne-kit --token <token> --labels comfyui --unattended
```

Hai job vì cần hai loại máy:

- **verify** (GitHub-hosted, chạy mọi push đụng `Tools/artpipe/**`):
  `selftest.py` — tier-1, hợp đồng graph, cổng authoring Unity. Không cài torch: tier 2 tự
  bỏ qua khi thiếu dep, tải 2GB mỗi push để kiểm 9 luật pixel là làm cổng nhanh thành cổng chậm.
- **generate** (self-hosted runner **trên máy ComfyUI**, label `comfyui`): render thật,
  đẩy `icons/ raw/ prov/ report.json sheet.html` lên artifact 14 ngày.

Chỉ chạy khi người bấm (`workflow_dispatch`) hoặc khi máy model tự bắn tín hiệu:

```
curl -X POST -H "Authorization: Bearer $GH_TOKEN" \
     -H "Accept: application/vnd.github+json" \
     https://api.github.com/repos/tsan2711/sanne-kit/dispatches \
     -d '{"event_type":"model-updated","client_payload":{"checkpoint":"sdxl_icon.safetensors","variants":"4","project":"June"}}'
```

### Bấm từ Mac, render trên PC

`remote.py` là mảnh còn lại: bắn workflow, chờ, tải artifact về đúng cấu trúc `--out` mà
`run.py` sinh ra tại chỗ.

```
python3 tools/artpipe/remote.py --out out --variants 4
python3 tools/artpipe/sheet.py out
python3 tools/artpipe/import_unity.py out/icons --apply
```

Ba máy ba vai: Mac soạn prompt + import vào Unity, PC render, GitHub làm đường truyền.
Token lấy từ `$GITHUB_TOKEN` hoặc mượn `gh auth token`. `--no-wait` để bắn rồi đi làm việc
khác, `--attach <run_id>` để quay lại lấy kết quả.

Mỗi lần bắn, `remote.py` gắn một nhãn ngẫu nhiên vào tên run (`run-name:` trong yaml) rồi
tìm lại đúng run đó. API dispatch trả 204 không thân, nên nếu chọn "run mới nhất" thì hai mẻ
chạy chồng nhau sẽ nhận nhầm kết quả của nhau.

**Nếu hai máy nhìn thấy nhau qua mạng thì không cần đường này** — trỏ thẳng nhanh hơn nhiều:

```
COMFYUI_URL=http://192.168.1.x:8188 python3 tools/artpipe/run.py --out out \
    generate --provider comfyui
```

Cái đắt của đường CI không phải tiền mà là vòng phản hồi: commit → push → chờ runner → chờ
artifact. Hợp với "bắn cả mẻ 21 asset rồi đi làm việc khác", không hợp với "sửa một chữ trong
prompt rồi xem lại".

### Đổi máy render — không sửa code, không sửa workflow

`artpipe` chỉ là **client HTTP** của ComfyUI, nên "máy render" là một URL chứ không phải
một cái máy. Ba cấu hình, đổi giữa chúng chỉ là đổi biến trên GitHub:

| | dùng khi | phải khai |
|---|---|---|
| **A. GPU thuê ngoài** (mặc định) | máy GPU ở xa, không dựng runner | secret `COMFYUI_URL`, `COMFYUI_TOKEN` |
| **B. Runner ngay trên máy GPU** | muốn nhanh, không qua internet hai lần | var `ARTPIPE_RUNNER` = `["self-hosted","comfyui"]`, var `ARTPIPE_PYTHON` |
| **C. Máy mượn tạm tại chỗ** | như B, thêm CA công ty | như B |

Với A thì job chạy trên runner Linux của GitHub, không cài gì trên máy GPU ngoài ComfyUI.

**Không có bước nào trong pipeline gắn với một máy cụ thể.** Cụ thể là:

- Mọi bước trong workflow viết bằng `shell: python`, không phải PowerShell hay bash —
  PowerShell khoá vào Windows, bash khoá vào Linux, Python có ở cả hai.
- `runs-on` đọc từ biến `ARTPIPE_RUNNER`, mặc định `ubuntu-latest`.
- `ARTPIPE_PYTHON` mặc định `python`; runner của GitHub tự cài Python và dependency,
  runner tự dựng thì trỏ vào venv của ComfyUI để dùng lại torch đã có.
- Bước duy nhất còn dính Windows là đổ CA của công ty cho Node, và nó `if: runner.os == 'Windows'`.
- `mesh.py` khớp tên model với tên **server** khai, nên `thư-mục\file.ckpt` (Windows) và
  `thư-mục/file.ckpt` (Linux) đều nhận.

Dựng máy GPU Linux thuê ngoài:

```bash
bash tools/artpipe/setup_gpu.sh                       # ComfyUI + sd-turbo, nghe 0.0.0.0:8188
bash tools/artpipe/setup_gpu.sh --dir /workspace/ComfyUI --hunyuan3d
```

Xong thì khai `COMFYUI_URL` và bật `start.sh`. **ComfyUI không có xác thực** — nghe trên
0.0.0.0 nghĩa là ai biết địa chỉ cũng chạy được job trên GPU đang tính tiền của bạn. Chặn
port theo IP, hoặc đặt sau reverse proxy kiểm Bearer token (`COMFYUI_TOKEN`), hoặc giữ
127.0.0.1 và dựng runner ngay trên máy đó.

### Dựng máy PC bằng một lệnh

```powershell
powershell -ExecutionPolicy Bypass -File setup_pc.ps1
powershell -ExecutionPolicy Bypass -File setup_pc.ps1 -Dir D:\sangcute\ComfyUI -Hunyuan3D
```

Script nhận cả ComfyUI cài sẵn lẫn chưa có, cả `.venv` (Desktop) lẫn `venv` (clone tay).
`-Hunyuan3D` thêm node sinh mesh 3D — **tuỳ chọn, không liên quan tới icon**, và kéo theo
~10GB model.

### Những chỗ đã sụp trên máy thật

Mỗi dòng dưới đây là một lần script chết giữa chừng; đừng gỡ các bước tương ứng ra.

| Lỗi | Nguyên nhân | Đã xử ở đâu |
|---|---|---|
| `ModuleNotFoundError` một gói bất kỳ | pip **huỷ toàn bộ** khi một gói lỗi (hay gặp: `open3d` chưa hỗ trợ 3.12/3.13) → mọi gói nằm sau nó trong file không bao giờ được cài | `Install-Requirements` thử cả file trước, hỏng thì cài từng gói và in ra gói nào bỏ lại |
| `self-signed certificate in certificate chain` | Antivirus/firewall công ty cắt giữa HTTPS | `pip-system-certs` cài **trước mọi thứ khác** (bước 3) |
| `Torch not compiled with CUDA enabled` | `pip install torch` trơn trên Windows lấy bản CPU-only từ PyPI — cài thành công, chỉ lộ ra lúc chạy | bắt buộc `--index-url`, tag CUDA đọc từ `nvidia-smi`, và **kiểm `torch.cuda.is_available()` rồi mới đi tiếp** |
| `is not a supported wheel on this platform` | `.whl` của Hunyuan3D build cho `cp312`, mà ComfyUI Desktop tự tạo venv bằng **3.13** | script chốt cứng Python 3.12, thấy venv khác thì đổi tên thành `*_old` và tạo lại |
| venv rỗng, mọi lệnh sau báo "không thấy python.exe" | `python` trên PATH là bản giả lập của Microsoft Store — chạy được nhưng không tạo nổi venv | bỏ qua mọi python trong `WindowsApps`; venv không ra `python.exe` thì dừng ngay tại đó |
| App tự phá venv sau khi mở lại | ComfyUI Desktop chạy "restoring GPU build" bằng `uv.exe` mỗi lần mở app icon, mà `uv` không đọc bản vá SSL | `start.cmd` gọi thẳng `python -s main.py`, **đừng mở app icon** |
| Dropdown model trống · `Value not in list` · `'collections.OrderedDict' object has no attribute 'nelement'` | ComfyUI Desktop **không** để model trong `<Dir>\models` — nó giữ một thư mục dùng chung và khai đường dẫn trong `%APPDATA%\Comfy Desktop\instance-model-paths\inst-*.yaml`. Chạy `main.py` thiếu `--extra-model-paths-config` thì server lên bình thường nhưng không thấy model nào | script đọc yaml đó, tải checkpoint vào **đúng** thư mục chung, và sinh `start.cmd` kèm đủ `--extra-model-paths-config` / `--input-directory` / `--output-directory` |
| Model tải rồi mà vẫn không thấy | trên máy có **hai** bản ComfyUI, script cài vào bản này còn bản đang nghe cổng 8188 là bản kia | script cảnh báo khi phát hiện bản thứ hai; chạy lại với `-Dir <bản đang chạy>` và sửa biến `ARTPIPE_PYTHON` cho khớp |
| `RuntimeError: Error(s) in loading state_dict for ShapeVAE` | chọn nhầm file model vào node VAELoader của Hunyuan3D (vd `ae.safetensors` của workflow khác — khác kiến trúc) | chọn đúng `hunyuan3d-vae-v2-1\model.fp16.ckpt` |
| `contains custom code in modules.py … trust_remote_code=True` | diffusers chặn model mang code Python riêng | script tự thêm `trust_remote_code=True` vào `hy3dpaint/utils/multiview_utils.py` |
| `A node type is missing` / `no class_type` | node trong workflow mẫu gắn version cũ khác bản đang cài | xoá node đó, thêm lại node cùng tên, nối dây tay |
| `Failed to load PyTorch C extensions` | cài torch dở dang hoặc lẫn version | `pip uninstall -y torch torchvision` rồi cài lại kèm `--no-cache-dir --force-reinstall` |

### Phần B — texture PBR cho Hunyuan3D (nặng, chỉ làm khi cần)

Mesh trơn thì `-Hunyuan3D` là đủ. Muốn **texture PBR** thì hai C++ extension
(`custom_rasterizer`, `mesh_inpaint_processor`) phải nạp được; `.whl` build sẵn trong repo
hay lệch nhị phân với Torch/CUDA mới, lúc đó phải build tại chỗ. Script sẽ báo
*"texture PBR chua dung duoc"* khi rơi vào ca này.

Cần thêm hai thứ cài tay:

1. **Visual Studio Build Tools 2022** — workload *Desktop development with C++*.
   Bản mới hơn (VS "18") **không dùng được**: CUDA 13 chỉ hỗ trợ MSVC trong khoảng
   VS2019–VS2022, và `nvcc` sẽ chết bằng `'cudafe++' died with status 0xC0000005`
   — crash nội bộ, không cờ nào chữa được.
2. **CUDA Toolkit** khớp bản torch (vd 13.0), Installer Type *exe (local)*, Express.

Rồi mở **một** cửa sổ PowerShell và làm hết trong đó (biến `$env:` không sống qua cửa sổ khác):

```powershell
cmd /c '"C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvarsall.bat" x64 && set' |
  ForEach-Object { if ($_ -match "^(.*?)=(.*)$") { Set-Item -Path "env:\$($matches[1])" -Value $matches[2] } }
where cl        # đường dẫn PHẢI chứa 2022\BuildTools

$env:DISTUTILS_USE_SDK = "1"
$env:CUDA_HOME = "C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v13.0"
$env:PATH = "$env:CUDA_HOME\bin;<ComfyUI>\.venv\Scripts;" + $env:PATH
$env:CL = "/std:c++20"          # header Torch mới cần C++17 trở lên
<ComfyUI>\.venv\Scripts\python.exe -m pip install ninja   # thiếu ninja -> file .cu bị đưa nhầm cho cl.exe

cd <ComfyUI>\custom_nodes\ComfyUI-Hunyuan3d-2-1\hy3dpaint\custom_rasterizer
<ComfyUI>\.venv\Scripts\python.exe -m pip install . --no-build-isolation
cd ..\DifferentiableRenderer
<ComfyUI>\.venv\Scripts\python.exe -m pip install . --no-build-isolation
```

`--no-build-isolation` là bắt buộc: không có nó pip dựng môi trường tạm rỗng và build
báo `No module named 'torch'`. Log bị cắt thì `2>&1 | Tee-Object -FilePath build_error.log`
(file ra UTF-16, tìm bằng từ khoá `error C`).

Xong thì **đóng cửa sổ build**, mở cửa sổ mới và chạy `start.cmd` như bình thường.

### Dựng runner

Đăng ký runner trên máy ComfyUI: Settings → Actions → Runners → New self-hosted runner,
thêm label `comfyui`. Secrets cần khai (nếu server không ở localhost của runner):
`COMFYUI_URL`, `COMFYUI_TOKEN`.

Hai điều kiện dễ quên, cả hai đều làm `remote.py` báo 404 hoặc treo:
1. `.github/workflows/artpipe.yml` **phải đã push lên `main`** — GitHub chỉ thấy
   workflow_dispatch trên nhánh mặc định.
2. Runner trên PC phải **online**; job `generate` không có runner thì nằm chờ vô hạn chứ
   không fail.

Job **không** fail khi có ảnh bị loại — đó là dữ liệu, phải xem `sheet.html` mới biết vì sao.
Nó chỉ fail khi **không ảnh nào sống sót**, vì lúc đó lỗi nằm ở checkpoint/graph chứ không
phải ở chất lượng art.

## Sự cố 2026-09-10 — máy có 2 bản ComfyUI, bản đang chạy thật thiếu đồ

> **Cập nhật 2026-09-23 — bảng dưới đã CŨ.** Server đang nghe cổng 8188 hiện là bản
> `D:\sangcute\ComfyUI` (custom_nodes + venv ở đó; model đọc thêm từ thư mục dùng chung của
> Desktop). Đừng tin đường dẫn ghi trong tài liệu — hỏi thẳng server: `GET /internal/folder_paths`
> (thư mục thật) và `GET /system_stats` (`argv`, bản Python). `setup_anim.py` làm đúng việc đó.
> Hai điều đã đo: runner chạy dưới tài khoản KHÔNG ghi được `...\AppData\Local\Comfy-Desktop\
> ComfyUI-Shared\models` ("Access is denied"), và server không có ComfyUI-Manager nên cài custom
> node xong phải khởi động lại ComfyUI bằng tay.

Máy này thực ra có **2 bản ComfyUI cài riêng biệt**, mỗi bản một `venv` và một thư mục
`models`/`custom_nodes` riêng, KHÔNG liên quan tới nhau:

| | Đường dẫn | Vai trò |
|---|---|---|
| Bản Comfy Desktop quản lý (server thật, cổng 8188) | `C:\Users\sanne\ComfyUI` (venv riêng), models dùng chung qua `C:\Users\sanne\AppData\Local\Comfy-Desktop\ComfyUI-Shared\models` | **Đây mới là server mà `mesh.py`/`gen.py` thật sự gọi tới.** |
| Bản cài tay cũ, không chạy | `D:\sangcute\ComfyUI` (venv riêng) | Có sẵn đủ thứ (custom node Hunyuan3D, model DIT/VAE, checkpoint `animagine-xl-4.0-opt.safetensors`) nhưng **không phải server đang chạy** — chỉ dùng làm kho để copy sang bên kia khi thiếu. |

Sau một lần ComfyUI Desktop bị crash (hết RAM) và mở lại, bản server thật
(`C:\Users\sanne\ComfyUI`) hoá ra **thiếu sạch** so với bản kia — không rõ từ bao giờ, có thể
chưa từng đủ, chỉ là chưa ai kiểm tra kỹ. Thiếu 4 thứ, xuất hiện tuần tự (sửa xong cái này lộ
ra cái kia):

1. **Thiếu hẳn checkpoint 2D** `animagine-xl-4.0-opt.safetensors` — copy từ
   `D:\sangcute\ComfyUI\models\checkpoints\` sang `...\ComfyUI-Shared\models\checkpoints\`.
2. **PyTorch không hỗ trợ GPU đời mới** (RTX 5060 Ti, kiến trúc Blackwell, compute capability
   12.0) — bản cài sẵn `torch==2.13.0+cu126` không có kernel cho card này (lỗi
   `CUDA error: no kernel image is available for execution on the device`). Sửa bằng
   `pip install torch==2.13.0+cu130 torchvision==0.28.0+cu130 --index-url
   https://download.pytorch.org/whl/cu130 --force-reinstall --no-deps` (đúng bản `+cu130`,
   pip coi `2.13.0` là "đã cài rồi" nếu không ghi rõ hậu tố build nên phải `--force-reinstall`).
   Lưu ý: torchvision phải khớp bản CUDA của torch, không thì lỗi lúc import
   `comfy.ldm.cosmos.model` (`Detected that PyTorch and torchvision were compiled with
   different CUDA major versions`).
3. **Thiếu hẳn custom node Hunyuan3D** (`custom_nodes/ComfyUI-Hunyuan3d-2-1`, cung cấp các node
   `Hy3D21*`) — bản server thật không có thư mục này. Copy nguyên thư mục từ
   `D:\sangcute\ComfyUI\custom_nodes\` sang, rồi `pip install -r requirements.txt` của nó
   (trimesh, open3d, pymeshlab, xatlas, pygltflib, diffusers, accelerate, pytorch-lightning...)
   vào đúng venv `C:\Users\sanne\ComfyUI\venv`. **Phải khởi động lại ComfyUI Desktop SAU KHI**
   copy xong — ComfyUI chỉ quét `custom_nodes/` lúc khởi động, không tự nhận thư mục mới.
4. **Thiếu file trọng số DIT/VAE** (`models/diffusion_models/hunyuan3d-dit-v2-1/model.fp16.ckpt`
   ~7.4GB, `models/vae/hunyuan3d-vae-v2-1/model.fp16.ckpt` ~656MB) — copy từ
   `D:\sangcute\ComfyUI\models\...` sang `ComfyUI-Shared\models\...`. Việc này KHÔNG cần khởi
   động lại — ComfyUI liệt kê file model động mỗi lần gọi `/object_info`.
5. **Thiếu gói Python `pynanoinstantmeshes`** (dùng bởi node `Hy3D21IMRemesh` để dựng lại lưới)
   — cài bằng `pip install pynanoinstantmeshes` vào venv trên. Gói này được import mỗi lần
   node chạy (không cache lúc khởi động ComfyUI), nên KHÔNG cần khởi động lại.

**Cách kiểm tra nhanh máy có đủ đồ chưa** (chạy trước khi bắt đầu một mẻ sinh hàng loạt):

```bash
curl -s http://127.0.0.1:8188/object_info/CheckpointLoaderSimple      # có animagine-xl-4.0-opt.safetensors?
curl -s http://127.0.0.1:8188/object_info/Hy3D21LoadImageWithTransparency  # phải khác "{}"
curl -s http://127.0.0.1:8188/object_info/Hy3D21MeshGenerator | grep hunyuan3d-dit-v2-1
"C:\Users\sanne\ComfyUI\venv\Scripts\python.exe" -c "import torch; x=torch.randn(4,4,device='cuda'); print((x@x).sum())"
```

## Máy render hiện tại: Colab / Kaggle (2026-10-10)

PC Windows đã nghỉ. Máy render giờ là một phiên GPU miễn phí chạy `render_node.ipynb`:
notebook dựng ComfyUI (`setup_gpu.sh --system-python --listen 127.0.0.1`), rồi tự đăng ký
làm runner GitHub `artpipe-colab` / `artpipe-kaggle` (nhãn `comfyui`). Không mở cổng nào.

- Biến repo: `ARTPIPE_RUNNER = ["self-hosted","comfyui"]`, `ARTPIPE_PYTHON = python3`.
- Secret của notebook: `ARTPIPE_GH_PAT` (fine-grained, sanne-kit, Administration RW + Contents Read — repo private: clone + xin token đăng ký).
- Phiên tự tắt khi rảnh `IDLE_MIN` phút hoặc hết `MAX_HOURS`; tắt ngang thì lần sau `--replace` thay bản đăng ký cũ.
- Model nằm trên đĩa tạm: mỗi phiên tải lại (sd-turbo 2.5GB, `SDXL=True` thêm 6.7GB, `ANIM=True` thêm ~24GB).
- Không phiên nào mở thì `remote.py` chờ: job xếp hàng ở GitHub tới khi có runner.
- Kaggle chạy nền được (*Save & Run All*), Colab phải giữ tab.
