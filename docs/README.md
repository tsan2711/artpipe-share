# Kho kiến thức artpipe

Mọi thứ đã học được khi làm art cho hai game thật (NanoSwarm, June/Skyborne): vì sao pipeline làm như thế, những chỗ
đã trả giá, và **dữ liệu thật** (spec phong cách, manifest, script) để bắt chước.

> Một số đoạn nói về máy render cũ của tác giả (PC Windows, runner GitHub, `remote.py`, `sanne-kit`). Repo này không cần
> những thứ đó — Colab/Kaggle + `generate.py` / `animate.py` thay thế. Giữ nguyên vì phần "vì sao" vẫn đúng.

## Kiến thức (`knowledge/`)

| File | Đọc khi |
|---|---|
| [lessons-icons.md](knowledge/lessons-icons.md) | **Đọc đầu tiên.** Chọn lệnh nào, đọc `report.json` ra sao, 6 chỗ đã trả giá (cfg=1 làm negative vô dụng, màu nền ngấm vào vật, đo sai đại lượng…) |
| [comfyui-lane.md](knowledge/comfyui-lane.md) | Graph ComfyUI là dữ liệu: `{{PROMPT}}`/`{{SEED}}`/`{{CKPT}}`, provenance, cách dựng máy render, sự cố máy thật |
| [anim-lane.md](knowledge/anim-lane.md) | Làn animation: anchor → Wan 2.2 → BiRefNet → spritesheet; manifest; vòng lặp; VFX |
| [checks-spec.md](knowledge/checks-spec.md) | Từng phép chấm tầng 1 đo gì, ngưỡng lấy từ đâu, đối chứng âm |
| [lessons-render-machine.md](knowledge/lessons-render-machine.md) | Chọn / đổi máy render (PC, GPU thuê, Colab/Kaggle) |
| [mesh-trial-2026-08-20.md](knowledge/mesh-trial-2026-08-20.md) | Thử làn 3D (ảnh → mesh Hunyuan3D) — kết quả + vì sao chưa dùng |

## Dữ liệu thật của hai game (`examples/`)

### NanoSwarm — idle colony mobile (`examples/nanoswarm/`)

| File | Là gì |
|---|---|
| `art-direction.md` | spec phong cách đầy đủ (bảng màu, viền, ~200 mô tả hình `subtype_shape` cho HUD, entity, anim frame, IAP, cây nâng cấp, gacha) |
| `nanoswarm-*.yaml` | 7 manifest đã chạy: icon HUD, UI, entity sprite, anim harvester (sinh từng frame — **cách cũ, đã bỏ**, xem anim-lane) |
| `gen_frontline_art.py` | **bộ gacha-chibi trong bộ sưu tập**: prompt nhân vật chibi gacha + icon painterly, Animagine + RMBG-2.0 |
| `gen_gacha_painterly.py` | icon shop/gacha kiểu painterly, ghép nền + khung bằng PIL |
| `gen_commander_ai.py` | **img2img có "điểm neo"**: vẽ lại phác thảo vector thành tranh tay ở vài mức denoise → chọn 1 làm anchor cho làn anim |
| `explore-findings.md` | ghi chép khám phá phong cách (cái gì Bi chọn, cái gì bị loại, vì sao) |

### June — Skyborne, PC (`examples/june/`)

| File | Là gì |
|---|---|
| `art-direction.md` | spec "Golden Hour Witch": 2 trục nghĩa của icon (màu = hệ, hình = kiểu spell), modifier trung tính, độ hiếm = quầng sáng, checks |
| `theme-cute-pastel.yaml` | theme đã sinh 21 icon trong bộ sưu tập `pastel-rpg` (checkpoint + graph + seed khoá trong một file) |

## Animation mẫu (`../artpipe/anims/`)

| Manifest | Thử gì |
|---|---|
| `smoke.yaml` | nhân vật mẫu (MIT, mor-o) idle + walk — bài kiểm máy render |
| `test-adventurer.yaml` | anchor do Animagine tự vẽ (`anchor_gen`) rồi **khoá lại** làm điểm neo cho mọi animation |
| `test-vfx.yaml` | VFX thuần (lửa, nổ…) vẽ trên nền đen → alpha theo độ sáng, hợp blend Additive |
