#!/usr/bin/env bash
# Dựng ComfyUI trên một máy Linux có GPU NVIDIA (Colab, Kaggle, máy thuê, PC Linux).
# Thường KHÔNG cần gọi tay — generate.py tự gọi khi chưa có ComfyUI.
#
#   bash setup_comfy.sh --dir /content/ComfyUI --system-python   # Colab / Kaggle
#   bash setup_comfy.sh --dir ~/ComfyUI                          # máy riêng (tạo venv)
#
# Chạy lại lần hai không sao — bước nào xong rồi thì bỏ qua. Model KHÔNG tải ở đây
# (generate.py tải theo preset.yaml của từng preset).
#
# Bài học đã trả giá (giữ nguyên từ bản gốc):
#   * torch PHẢI cài kèm --index-url; `pip install torch` trơn có thể ra bản CPU-only, và
#     nó chỉ lộ ra lúc render chứ không báo lỗi lúc cài.
#   * pip HUỶ TOÀN BỘ khi một gói lỗi → hỏng thì cài từng gói và in ra gói nào bỏ lại.
#   * GPU đời mới (RTX 50xx, Blackwell) cần torch bản cu128+; driver báo CUDA 13 → cu130.
set -euo pipefail

DIR="${HOME}/ComfyUI"
CUDA_TAG=""
SYSTEM_PY=0
while [ $# -gt 0 ]; do
  case "$1" in
    --dir) DIR="$2"; shift 2 ;;
    --cuda) CUDA_TAG="$2"; shift 2 ;;
    # Colab/Kaggle: python sẵn có đã kèm torch CUDA. Tạo venv rồi cài lại torch là ~3GB tải
    # lại MỖI phiên — nên dùng thẳng python của máy.
    --system-python) SYSTEM_PY=1; shift ;;
    *) echo "tham số lạ: $1" >&2; exit 2 ;;
  esac
done

step() { printf '\n\033[36m[%s]\033[0m %s\n' "$1" "$2"; }
ok()   { printf '    \033[32mOK\033[0m  %s\n' "$1"; }
warn() { printf '    \033[33m%s\033[0m\n' "$1"; }

step 0 "Python và git"
command -v git >/dev/null 2>&1 || { echo "cần git"; exit 1; }
PY_BIN="$(command -v python3)"
ok "$("$PY_BIN" --version)"

step 1 "ComfyUI"
if [ -f "$DIR/main.py" ]; then
  ok "đã có $DIR"
else
  git clone --depth 1 https://github.com/comfyanonymous/ComfyUI "$DIR"
  ok "đã tải về $DIR"
fi

step 2 "Môi trường python"
if [ "$SYSTEM_PY" = "1" ]; then
  PY="$PY_BIN"
  ok "--system-python: dùng $PY, không tạo venv"
else
  VENV="$DIR/.venv"
  PY="$VENV/bin/python"
  [ -x "$PY" ] || "$PY_BIN" -m venv "$VENV"
  "$PY" -m pip install --upgrade pip --quiet
  ok "venv $VENV"
fi

step 3 "torch bản CUDA"
if "$PY" -c 'import torch,sys; sys.exit(0 if torch.cuda.is_available() else 1)' 2>/dev/null; then
  ok "torch $("$PY" -c 'import torch; print(torch.__version__)') đã thấy GPU"
else
  if [ -z "$CUDA_TAG" ]; then
    CUDA_TAG=cu126
    v="$(nvidia-smi 2>/dev/null | sed -n 's/.*CUDA Version: *\([0-9]*\)\.\([0-9]*\).*/\1 \2/p' | head -1)"
    maj="${v% *}"; min="${v#* }"
    if [ -n "$maj" ]; then
      if   [ "$maj" -ge 13 ]; then CUDA_TAG=cu130
      elif [ "$maj" -eq 12 ] && [ "$min" -ge 8 ]; then CUDA_TAG=cu128
      fi
    fi
    ok "driver báo CUDA ${maj:-?}.${min:-?} -> $CUDA_TAG"
  fi
  "$PY" -m pip install torch torchvision --index-url "https://download.pytorch.org/whl/$CUDA_TAG" --no-cache-dir
  "$PY" -c 'import torch,sys; sys.exit(0 if torch.cuda.is_available() else 1)' \
    || { echo "torch cài xong nhưng không thấy GPU — máy có GPU NVIDIA chưa? (Colab: Runtime → T4 GPU)"; exit 1; }
  ok "torch $("$PY" -c 'import torch; print(torch.__version__)'), GPU OK"
fi

install_reqs() {   # $1 = file, $2 = nhãn
  if "$PY" -m pip install --quiet -r "$1"; then ok "$2 xong"; return; fi
  warn "$2: cài cả file thất bại — chuyển sang cài từng gói"
  failed=""
  while IFS= read -r line; do
    pkg="$(printf '%s' "$line" | sed 's/#.*//' | xargs || true)"
    [ -z "$pkg" ] && continue
    "$PY" -m pip install "$pkg" --quiet || failed="$failed $pkg"
  done < "$1"
  [ -n "$failed" ] && warn "$2: bỏ lại:$failed" || ok "$2 xong (cài từng gói)"
}

step 4 "Dependencies của ComfyUI"
install_reqs "$DIR/requirements.txt" "ComfyUI"

step 5 "Các gói cho artpipe (tách nền rembg)"
"$PY" -m pip install --quiet pillow numpy pyyaml rembg onnxruntime
ok "xong"

echo "$PY" > "$DIR/.artpipe-python"
ok "python của ComfyUI: $PY (ghi ở $DIR/.artpipe-python)"
