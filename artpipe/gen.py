"""Image providers, and the provenance record that comes back with every image.

Mechanism only — a provider takes a prompt and returns bytes plus the facts needed to
reproduce them. It does not know what SKYBORNE looks like, what an icon is, or how a
prompt gets written. Prompt construction is policy and lives elsewhere.

The seed is chosen here rather than left to the provider, because a record that cannot
regenerate its own image is not provenance, it is a receipt.

    export REPLICATE_API_TOKEN=...
    python3 tools/artpipe/gen.py "a red circle on a flat green field" --out /tmp/x
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import random
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path


class ProviderError(RuntimeError):
    pass


class OutOfCredit(ProviderError):
    """Separated from other failures because it is the one a retry can never fix."""


@dataclass
class Generated:
    image: bytes = field(repr=False)
    provider: str = ""
    model_id: str = ""
    model_version: str = ""
    prompt_full: str = ""
    prompt_hash: str = ""
    seed: int = 0
    generated_at: str = ""
    extra: dict = field(default_factory=dict)

    def record(self) -> dict:
        d = asdict(self)
        d.pop("image")
        return d


def _post(url: str, payload: dict, headers: dict, timeout: int = 300) -> dict:
    req = urllib.request.Request(url, json.dumps(payload).encode(), headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        if e.code == 402:
            raise OutOfCredit(f"hết credit: {body[:300]}") from e
        raise ProviderError(f"HTTP {e.code}: {body[:500]}") from e


class Replicate:
    """Replicate's synchronous-when-it-can prediction endpoint.

    `Prefer: wait` returns inline for fast models; anything slower still comes back as a
    queued prediction, so the polling path below is not dead code even for flux-schnell.
    """

    BASE = "https://api.replicate.com/v1/predictions"

    def __init__(self, model: str = "black-forest-labs/flux-schnell",
                 token: str | None = None) -> None:
        self.model = model
        self.token = token or os.environ.get("REPLICATE_API_TOKEN", "")
        if not self.token:
            raise ProviderError("REPLICATE_API_TOKEN chưa được đặt")

    @property
    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
                "Prefer": "wait"}

    def generate(self, prompt: str, seed: int | None = None, **opts) -> Generated:
        seed = random.randrange(2**31 - 1) if seed is None else seed
        inp = {"prompt": prompt, "aspect_ratio": "1:1", "output_format": "png",
               "num_outputs": 1, "seed": seed, **opts}

        d = _post(self.BASE, {"version": self.model, "input": inp}, self._headers)

        deadline = time.time() + 300
        while d.get("status") in ("starting", "processing"):
            if time.time() > deadline:
                raise ProviderError(f"quá 300s vẫn ở trạng thái {d.get('status')}")
            time.sleep(2)
            req = urllib.request.Request(d["urls"]["get"], headers=self._headers)
            with urllib.request.urlopen(req, timeout=60) as r:
                d = json.load(r)

        if d.get("status") != "succeeded":
            raise ProviderError(f"{d.get('status')}: {str(d.get('error'))[:300]}")

        out = d.get("output")
        url = out[0] if isinstance(out, list) else out
        if not url:
            raise ProviderError("prediction thành công nhưng không có ảnh trả về")
        with urllib.request.urlopen(url, timeout=120) as r:
            image = r.read()

        return Generated(
            image=image,
            provider="replicate",
            model_id=self.model,
            model_version=d.get("version", ""),
            prompt_full=prompt,
            prompt_hash=hashlib.sha256(prompt.encode()).hexdigest()[:16],
            seed=seed,
            generated_at=datetime.now(timezone.utc).isoformat(),
            extra={"prediction_id": d.get("id"), "metrics": d.get("metrics", {})},
        )


class LocalSD:
    """Stable Diffusion on this machine's GPU (Apple MPS). No account, no credit, no upload.

    Added after measuring that the machine can in fact do this: the earlier note saying
    local generation was impossible was based on ~4GB free disk, and there is more now.
    ~59s per 512px image on an M2 at one step — slow, but free and unmetered, which beats
    a fast provider with an empty balance.

    sd-turbo is chosen for the shape of this problem, not for quality: it is SD-2.1 sized
    (fits 8GB unified memory), single-step, and **natively 512x512**, which is exactly the
    canvas the art direction specifies. Generating at the target size avoids a resample
    before the checks ever see the image.
    """

    def __init__(self, model: str = "stabilityai/sd-turbo", token: str | None = None) -> None:
        self.model = model
        self._pipe = None

    def _load(self):
        if self._pipe is not None:
            return self._pipe
        try:
            import torch
            from diffusers import AutoPipelineForText2Image
        except ImportError as exc:
            raise ProviderError(
                "provider 'local' cần torch + diffusers trong tools/artpipe/.venv:\n"
                "  tools/artpipe/.venv/bin/pip install torch diffusers accelerate safetensors"
            ) from exc

        device = "mps" if torch.backends.mps.is_available() else "cpu"
        if device == "cpu":
            # Minutes per image instead of a minute. Say so rather than appear to hang.
            print("CẢNH BÁO: không có MPS, chạy CPU — mỗi ảnh sẽ mất vài phút")
        pipe = AutoPipelineForText2Image.from_pretrained(
            self.model, torch_dtype=torch.float16, variant="fp16", use_safetensors=True)
        pipe = pipe.to(device)
        pipe.set_progress_bar_config(disable=True)
        self._pipe = pipe
        return pipe

    def generate(self, prompt: str, seed: int | None = None, **opts) -> Generated:
        import torch

        seed = random.randrange(2**31 - 1) if seed is None else seed
        pipe = self._load()
        steps = int(opts.get("steps", 1))          # sd-turbo is a one-step model
        size = int(opts.get("size", 512))
        img = pipe(prompt=prompt, num_inference_steps=steps, guidance_scale=0.0,
                   width=size, height=size,
                   generator=torch.Generator("cpu").manual_seed(seed)).images[0]

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return Generated(
            image=buf.getvalue(),
            provider="local",
            model_id=self.model,
            model_version="",
            prompt_full=prompt,
            prompt_hash=hashlib.sha256(prompt.encode()).hexdigest()[:16],
            seed=seed,
            generated_at=datetime.now(timezone.utc).isoformat(),
            extra={"steps": steps, "size": size},
        )


class ComfyUI:
    """A running ComfyUI server, driven headlessly over its HTTP API.

    Same weights and same torch as `LocalSD` — what changes is *where the sampling recipe
    lives*. In `LocalSD` the recipe is arguments buried in a Python call; here it is a
    graph file you can open in the browser, rewire, and watch execute. That is the whole
    reason to prefer it: the parts of generation worth iterating on (sampler, ControlNet,
    style reference, img2img) become editable data instead of code.

    So this class deliberately injects only what MUST vary per image — prompt, negative,
    seed, checkpoint, canvas — and treats everything else in the workflow as authored by
    hand. Steps, cfg and sampler are read back OUT of the graph into the provenance record
    rather than pushed into it: whatever the graph says is what actually ran.

    The graph must be **API format** (ComfyUI menu → Export (API)). The UI format is a
    different schema (`nodes`/`links` arrays) and `/prompt` rejects it.

        (cd ~/ComfyUI && tools/artpipe/.venv/bin/python main.py)
        python3 tools/artpipe/run.py generate --provider comfyui --out out/
    """

    #: Values the pipeline substitutes. Anything else in the graph is the author's.
    SENTINELS = ("{{PROMPT}}", "{{NEGATIVE}}", "{{SEED}}", "{{CKPT}}",
                 "{{WIDTH}}", "{{HEIGHT}}")
    REQUIRED = ("{{PROMPT}}", "{{SEED}}", "{{CKPT}}")

    def __init__(self, model: str = "sd_turbo.safetensors", host: str | None = None,
                 workflow: Path | str | None = None, size: int = 512,
                 negative: str = "", token: str | None = None) -> None:
        self.model = model
        # The server is deliberately addressable: this machine has 8GB and ~5GB of disk,
        # so ComfyUI is expected to live on another box (or a tunnel to one) and this is
        # only a client. `localhost` is the default because that is what a self-hosted CI
        # runner on the build machine sees, not because a local install is assumed.
        self.host = (host or os.environ.get("COMFYUI_URL")
                     or "http://127.0.0.1:8188").rstrip("/")
        self.token = token or os.environ.get("COMFYUI_TOKEN", "")
        self.workflow_path = Path(workflow) if workflow else \
            Path(__file__).parent / "workflows" / "icon_txt2img.json"
        if not self.workflow_path.exists():
            raise ProviderError(f"không thấy workflow: {self.workflow_path}")
        self.graph = json.loads(self.workflow_path.read_text("utf-8"))
        self.size = size
        self.negative = negative
        self.client_id = hashlib.sha256(str(self.workflow_path).encode()).hexdigest()[:16]

    # -- graph patching ----------------------------------------------------------------
    @classmethod
    def _substitute(cls, node, values: dict) -> tuple[object, set]:
        """Replace sentinel strings anywhere in the graph, reporting which were found.

        Structural walk rather than text replace on the JSON source, so a sentinel is only
        honoured where it is a whole value — `"{{SEED}}"` becomes the integer 12345, not
        the string "12345", which KSampler would reject.
        """
        if isinstance(node, dict):
            found, out = set(), {}
            for k, v in node.items():
                out[k], f = cls._substitute(v, values)
                found |= f
            return out, found
        if isinstance(node, list):
            found, out = set(), []
            for v in node:
                nv, f = cls._substitute(v, values)
                out.append(nv)
                found |= f
            return out, found
        if isinstance(node, str) and node in values:
            return values[node], {node}
        return node, set()

    def _patch(self, prompt: str, negative: str, seed: int) -> dict:
        values = {"{{PROMPT}}": prompt, "{{NEGATIVE}}": negative, "{{SEED}}": seed,
                  "{{CKPT}}": self.model, "{{WIDTH}}": self.size, "{{HEIGHT}}": self.size}
        graph, found = self._substitute(self.graph, values)

        missing = [s for s in self.REQUIRED if s not in found]
        if missing:
            raise ProviderError(
                f"{self.workflow_path.name} thiếu {', '.join(missing)} — workflow không có "
                f"chỗ nhận prompt/seed/checkpoint thì mỗi ảnh sinh ra sẽ giống hệt nhau và "
                f"provenance ghi sai. Đặt đúng chuỗi đó vào ô tương ứng rồi export lại.")

        # A leftover {{...}} means a typo'd sentinel, which ComfyUI would happily encode as
        # literal text in the prompt. Cheaper to refuse than to review the image later.
        stray = sorted({v for _, v in _walk_strings(graph) if v.startswith("{{")})
        if stray:
            raise ProviderError(f"còn chuỗi thay thế lạ trong workflow: {stray}")
        return graph

    @staticmethod
    def _sampler_settings(graph: dict) -> dict:
        """Read the settings that actually ran back out of the graph, for provenance."""
        for nid, node in graph.items():
            if node.get("class_type", "").startswith("KSampler"):
                inp = node.get("inputs", {})
                return {k: inp[k] for k in ("steps", "cfg", "sampler_name", "scheduler",
                                            "denoise") if k in inp}
        return {}

    # -- HTTP --------------------------------------------------------------------------
    @property
    def _headers(self) -> dict:
        """A remote server usually sits behind a tunnel that wants a bearer token; a
        localhost one wants no header at all. Sending an empty Authorization is worse than
        sending none — some proxies reject it outright."""
        h = {"Content-Type": "application/json"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    def _get(self, path: str, timeout: int = 60) -> bytes:
        req = urllib.request.Request(f"{self.host}{path}", headers=self._headers)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except urllib.error.URLError as exc:
            raise ProviderError(f"không gọi được ComfyUI ở {self.host}: {exc}") from exc

    def generate(self, prompt: str, seed: int | None = None, **opts) -> Generated:
        seed = random.randrange(2**31 - 1) if seed is None else seed
        negative = opts.get("negative", self.negative)
        graph = self._patch(prompt, negative, seed)

        try:
            d = _post(f"{self.host}/prompt", {"prompt": graph, "client_id": self.client_id},
                      self._headers)
        except urllib.error.URLError as exc:
            raise ProviderError(
                f"không gọi được ComfyUI ở {self.host} — server chưa chạy? ({exc})") from exc
        pid = d.get("prompt_id")
        if not pid:
            raise ProviderError(f"/prompt không trả prompt_id: {str(d)[:300]}")

        # Poll history rather than the websocket: the only event this needs is "done", and
        # a second protocol would be a second thing to get wrong.
        deadline = time.time() + int(opts.get("timeout", 900))
        while True:
            hist = json.loads(self._get(f"/history/{pid}") or b"{}")
            if pid in hist:
                break
            if time.time() > deadline:
                raise ProviderError(f"quá {int(opts.get('timeout', 900))}s chưa xong (prompt_id={pid})")
            time.sleep(1.0)

        entry = hist[pid]
        status = entry.get("status", {})
        if status.get("status_str") == "error":
            msgs = [m for m in status.get("messages", []) if "error" in str(m[0])]
            raise ProviderError(f"workflow lỗi: {str(msgs)[:400]}")

        images = [(nid, img) for nid, out in entry.get("outputs", {}).items()
                  for img in out.get("images", []) if img.get("type") != "temp"]
        if not images:
            raise ProviderError(
                "workflow chạy xong nhưng không có ảnh nào ở đầu ra — graph thiếu node "
                "SaveImage (PreviewImage chỉ ghi vào 'temp')")
        _, img = images[-1]
        q = urllib.parse.urlencode({"filename": img["filename"],
                                    "subfolder": img.get("subfolder", ""),
                                    "type": img.get("type", "output")})
        image = self._get(f"/view?{q}", timeout=120)

        return Generated(
            image=image,
            provider="comfyui",
            model_id=self.model,
            # The graph IS the model configuration. Two runs of the "same checkpoint"
            # through different graphs are not the same generator, so the hash of what was
            # actually submitted is the honest version string.
            model_version=hashlib.sha256(
                json.dumps(graph, sort_keys=True).encode()).hexdigest()[:16],
            prompt_full=prompt,
            prompt_hash=hashlib.sha256(prompt.encode()).hexdigest()[:16],
            seed=seed,
            generated_at=datetime.now(timezone.utc).isoformat(),
            extra={"workflow": self.workflow_path.name, "prompt_id": pid,
                   "negative": negative, "size": self.size,
                   **self._sampler_settings(graph)},
        )


def _walk_strings(node, path: str = ""):
    """Every string in the graph, with its path — used to spot leftover sentinels."""
    if isinstance(node, dict):
        for k, v in node.items():
            yield from _walk_strings(v, f"{path}.{k}")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from _walk_strings(v, f"{path}[{i}]")
    elif isinstance(node, str):
        yield path, node


class FalAI:
    """fal.ai queue endpoint — supports FLUX/Schnell and other hosted models.

    Uses the queue API so slow models don't time out. Auth via FAL_KEY env var.
    """

    BASE = "https://queue.fal.run"

    def __init__(self, model: str = "fal-ai/flux/schnell", token: str | None = None) -> None:
        self.model = model
        self.token = token or os.environ.get("FAL_KEY", "")
        if not self.token:
            raise ProviderError("FAL_KEY chưa được đặt")

    @property
    def _headers(self) -> dict:
        return {"Authorization": f"Key {self.token}", "Content-Type": "application/json"}

    def _get(self, url: str) -> dict:
        req = urllib.request.Request(url, headers=self._headers)
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")
            raise ProviderError(f"HTTP {e.code}: {body[:500]}") from e

    def generate(self, prompt: str, seed: int | None = None, **opts) -> Generated:
        seed = random.randrange(2**31 - 1) if seed is None else seed
        payload = {"prompt": prompt, "image_size": "square_hd",
                   "num_images": 1, "seed": seed, "output_format": "png", **opts}

        sub = _post(f"{self.BASE}/{self.model}", payload, self._headers)
        request_id = sub.get("request_id")
        if not request_id:
            raise ProviderError(f"fal.ai no request_id: {str(sub)[:300]}")

        status_url = f"{self.BASE}/{self.model}/requests/{request_id}/status"
        deadline = time.time() + 300
        while True:
            if time.time() > deadline:
                raise ProviderError("fal.ai: quá 300s chưa xong")
            s = self._get(status_url)
            status = s.get("status", "")
            if status == "COMPLETED":
                break
            if status == "FAILED":
                raise ProviderError(f"fal.ai FAILED: {str(s)[:300]}")
            time.sleep(2)

        result = self._get(f"{self.BASE}/{self.model}/requests/{request_id}")
        images = result.get("images", [])
        if not images:
            raise ProviderError("fal.ai: không có ảnh trả về")
        url = images[0].get("url", "")
        if not url:
            raise ProviderError("fal.ai: image url rỗng")

        with urllib.request.urlopen(url, timeout=120) as r:
            image = r.read()

        return Generated(
            image=image,
            provider="fal",
            model_id=self.model,
            model_version="",
            prompt_full=prompt,
            prompt_hash=hashlib.sha256(prompt.encode()).hexdigest()[:16],
            seed=result.get("seed", seed),
            generated_at=datetime.now(timezone.utc).isoformat(),
            extra={"request_id": request_id},
        )


PROVIDERS = {"replicate": Replicate, "local": LocalSD, "comfyui": ComfyUI, "fal": FalAI}

#: Each provider names its models differently — a Replicate slug is not a checkpoint
#: filename. One flag with one default silently pointed the wrong name at the wrong server.
DEFAULT_MODEL = {
    "replicate": "black-forest-labs/flux-schnell",
    "local": "stabilityai/sd-turbo",
    "comfyui": "sd_turbo.safetensors",
    "fal": "fal-ai/flux/schnell",
}


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("prompt")
    ap.add_argument("--out", type=Path, required=True, help="thư mục đích")
    ap.add_argument("--provider", default="replicate", choices=sorted(PROVIDERS))
    ap.add_argument("--model", default=None, help="mặc định theo provider")
    ap.add_argument("--n", type=int, default=1)
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--host", default=None, help="comfyui: địa chỉ server")
    ap.add_argument("--workflow", type=Path, default=None, help="comfyui: file graph API-format")
    args = ap.parse_args()

    kw = {"model": args.model or DEFAULT_MODEL[args.provider]}
    if args.provider == "comfyui":
        kw |= {"host": args.host, "workflow": args.workflow}
    prov = PROVIDERS[args.provider](**kw)
    args.out.mkdir(parents=True, exist_ok=True)

    for i in range(args.n):
        seed = args.seed if args.seed is not None and args.n == 1 else None
        try:
            g = prov.generate(args.prompt, seed=seed)
        except OutOfCredit as e:
            print(f"DỪNG — {e}\nnạp tại https://replicate.com/account/billing")
            return 2
        stem = args.out / f"{g.prompt_hash}_{g.seed}"
        stem.with_suffix(".png").write_bytes(g.image)
        stem.with_suffix(".json").write_text(
            json.dumps(g.record(), indent=2, ensure_ascii=False), "utf-8")
        print(f"[{i + 1}/{args.n}] {stem.with_suffix('.png').name}  seed={g.seed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
