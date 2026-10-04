# Integration Notes

This document captures upstream model and library integrations and their status. It is intentionally conservative: anything not verified as usable is marked as a fallback or documented limitation.

## Status summary

- Segment Anything (SAM): planned, CPU-safe stub available (not production model weights yet)
- FabricDiffusion: planned, optional integration gated by license and hardware availability
- MaterialPalette: planned, optional integration
- Pattern Diffusion / Tiled Diffusion: planned, optional and benchmark-gated
- VTracer / imagetracerjs: planned, vector export path scaffolded

## Required rule

If an upstream project has no usable inference code or weights, the repository will document that fact here and continue with a fallback implementation instead of faking support.

## Prototype fallback behavior

The current repository includes a CPU-safe pipeline skeleton that can run without GPU-heavy dependencies. This ensures core functionality remains possible while heavy models are later integrated behind config gates.
