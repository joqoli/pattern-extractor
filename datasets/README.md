# Pattern Extractor Dataset Workspace

This directory stores downloaded benchmark, training, and validation data for the project. It is intentionally not committed with large files by default.

## Layout

```text
datasets/
├── embroidery/
│   ├── openembroidery/
│   ├── embroidize/
│   ├── design-palace/
│   ├── embroideres/
│   ├── creative-fabrica/
│   └── annthegran/
├── texture/
│   ├── dtd/
│   ├── kth-tips/
│   └── tpr/
├── fashion/
│   ├── deepfashion2/
│   ├── fashionpedia/
│   ├── modanet/
│   ├── atr/
│   └── lip/
├── historical/
│   └── project-gutenberg/
├── community/
│   └── thingiverse/
└── README.md
```

## Notes

- The repository intentionally keeps the data directory outside Git for large downloads.
- Use `make datasets` to prepare the dataset tree and instructions for each source.
- License and access limits are documented in `docs/DATASETS.md` and `server/data/dataset_manifest.json`.
