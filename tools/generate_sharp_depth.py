#!/usr/bin/env python3
"""Generate a web-ready disparity map with Apple's SHARP model.

SHARP model weights are subject to Apple's research-only model license:
https://github.com/apple-aiml-research/ml-sharp/blob/main/LICENSE_MODEL
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image, ImageFilter
from sharp.models import PredictorParams, create_predictor
from sharp.utils import io


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--device", choices=("mps", "cpu", "cuda"), default="mps")
    parser.add_argument("--dtype", choices=("float16", "float32"), default="float16")
    parser.add_argument("--internal-resolution", type=int, default=1536)
    parser.add_argument("--vit-chunk", type=int, default=4)
    parser.add_argument("--resolution", type=int, default=760)
    return parser.parse_args()


@torch.no_grad()
def main() -> None:
    args = parse_args()
    device = torch.device(args.device)
    dtype = torch.float16 if args.dtype == "float16" else torch.float32

    print("Loading predictor...", flush=True)
    state_dict = torch.load(args.checkpoint, map_location="cpu", weights_only=True, mmap=True)
    predictor = create_predictor(PredictorParams())
    predictor.to(dtype=dtype)
    predictor.load_state_dict(state_dict)
    del state_dict
    predictor.eval().to(device)

    patch_encoder = predictor.monodepth_model.monodepth_predictor.encoder.patch_encoder
    original_forward = patch_encoder.forward

    def chunked_forward(patches: torch.Tensor):
        outputs = []
        intermediates: dict[int, list[torch.Tensor]] = {}
        for chunk in patches.split(args.vit_chunk):
            output, features = original_forward(chunk)
            outputs.append(output)
            for layer, feature in features.items():
                intermediates.setdefault(layer, []).append(feature)
        return (
            torch.cat(outputs, dim=0),
            {layer: torch.cat(items, dim=0) for layer, items in intermediates.items()},
        )

    patch_encoder.forward = chunked_forward

    print("Loading image...", flush=True)
    image, _, _ = io.load_rgb(args.input)
    image_pt = torch.from_numpy(image.copy()).to(device=device, dtype=dtype).permute(2, 0, 1) / 255.0
    _, height, width = image_pt.shape

    internal_width = args.internal_resolution
    image_resized = F.interpolate(
        image_pt[None],
        size=(internal_width, internal_width),
        mode="bilinear",
        align_corners=True,
    )
    print("Running SHARP inference...", flush=True)
    monodepth = predictor.monodepth_model(image_resized)
    disparity = monodepth.disparity[0].max(dim=0).values.float()
    low, high = torch.quantile(
        disparity.flatten(),
        torch.tensor([0.02, 0.98], device=device, dtype=disparity.dtype),
    )
    normalized = ((disparity - low) / (high - low).clamp(min=1e-6)).clamp(0, 1)
    normalized = normalized.pow(0.86)
    normalized = F.interpolate(
        normalized[None, None],
        size=(args.resolution, args.resolution),
        mode="bilinear",
        align_corners=False,
    )[0, 0]

    depth_array = (normalized.detach().cpu().numpy() * 255).astype(np.uint8)
    depth_image = Image.fromarray(depth_array, mode="L").filter(ImageFilter.GaussianBlur(0.7))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    depth_image.save(args.output, optimize=True)
    print(f"Wrote {args.output} ({args.output.stat().st_size / 1024:.1f} KiB)")


if __name__ == "__main__":
    main()
