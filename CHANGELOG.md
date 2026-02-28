# Changelog

All notable changes to this project will be documented in this file.

## v0.1.4 – UTF-8 + LF hardening

- Enforce UTF-8 encoding without BOM via pre-commit gate (eject-utf8-bom).
- Enforce LF-only line endings via .gitattributes and renormalization.
- Add normalization drift gate to ensure canonical fixture stability.
- CI aligned with local invariant enforcement.

## v0.1.2 – Install-clean CLI + deterministic normalization

- Installable console script (mttt).
- Deterministic JSON normalization pipeline.
- CI smoke tests + normalization diff assertion.