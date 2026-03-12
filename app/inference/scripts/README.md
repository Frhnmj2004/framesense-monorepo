# Inference scripts

## RunPod one-shot setup

On a fresh RunPod (or any GPU box with CUDA), from the repo root:

```bash
cd /workspace/framesense-monorepo
bash app/inference/scripts/setup_runpod.sh
```

This will:

1. **Pull** the latest FrameSense code (`git pull`; or clone if `GIT_REPO_URL` is set and repo missing).
2. **Install** system packages: `ffmpeg`, `git`.
3. **Install** PyTorch with CUDA 12.6 from the official wheel index.
4. **Install** SAM 3 from the Facebook Research repo (clone + `pip install .`).
5. **Install** app dependencies from `app/inference/requirements.txt`.
6. **Create** `.env` from `.env.example` if missing (you must set `HF_TOKEN` for SAM 3).
7. **Start** the inference server: `uvicorn main:app --host 0.0.0.0 --port 8000`.

Optional env vars:

- `REPO_ROOT` – path to the monorepo (default: `/workspace/framesense-monorepo`).
- `GIT_REPO_URL` – required only when the repo is not present (e.g. first run on a blank pod); e.g. `https://github.com/YOUR_USER/framesense-monorepo.git`.

Example for a blank pod (clone + setup):

```bash
export GIT_REPO_URL=https://github.com/YOUR_USER/framesense-monorepo.git
bash app/inference/scripts/setup_runpod.sh
```

Example when repo is already at `/workspace/framesense-monorepo`:

```bash
cd /workspace/framesense-monorepo
bash app/inference/scripts/setup_runpod.sh
```
