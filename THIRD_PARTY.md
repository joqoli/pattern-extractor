# Third-Party Inventory

The table below tracks external components that may be integrated into the system. The repository intentionally uses only verified open-source tools or clearly documented optional plugins.

| Project | URL | Version / Commitment | License | How used | Status |
| --- | --- | --- | --- | --- | --- |
| FastAPI | https://github.com/fastapi/fastapi | latest stable | MIT | API backend | planned |
| Torch | https://pytorch.org | latest stable | BSD-3-Clause | ML backends | optional |
| Segment Anything | https://github.com/facebookresearch/segment-anything | main | Apache-2.0 | garment isolation | planned |
| FabricDiffusion | https://github.com/humansensinglab/fabric-diffusion | main | check before use | flattening | optional |
| MaterialPalette | https://github.com/astra-vision/MaterialPalette | main | check before use | material extraction | optional |
| vtracer | https://github.com/visioncortex/vtracer | main | BSD-3-Clause | vectorization | planned |
| imagetracerjs | https://github.com/jankovicsandras/imagetracerjs | main | MIT | vectorization fallback | planned |
| FLUX.1 Kontext LoRAs | Hugging Face links noted in prompt | versioned by model card | likely gated / not default | garment extraction | optional + off by default |

Important:
- Any project with a commercial license restriction or model license limitations must be marked as optional and disabled by default.
- This file is intentionally a working inventory and must be updated when integrations are actually added.
