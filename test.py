import sys

try:
    import torch
    print("Torch version:", torch.__version__, flush=True)
    print("CUDA available:", torch.cuda.is_available(), flush=True)
    if torch.cuda.is_available():
        print("GPU:", torch.cuda.get_device_name(0), flush=True)
except Exception as e:
    print(f"Error: {e}", file=sys.stderr, flush=True)
    sys.exit(1)