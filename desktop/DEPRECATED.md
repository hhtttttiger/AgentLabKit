# Deprecated: legacy PySide6 Desktop client

The former PySide6 Desktop shell is deprecated and is not the current AgentLab
Desktop product.

Deprecated surface:

- `main.py`
- `app/`
- `ui/`
- `capture/`
- `storage/`
- `utils/`
- the PySide6-specific parts of `core/` and `tools/`

Current product:

- Tauri shell: `frontend/admin/src-tauri/`
- React UI: `frontend/admin/`
- Active Python Local Mode API: `desktop/local/`
- Active Local Mode tools: `desktop/tools/`

The legacy files remain in the repository temporarily for historical reference
and are not covered by the current Desktop product entrypoint or v0.3
acceptance. Do not extend them or add new features there. New Desktop work must
target the Tauri client and preserve the active `desktop/local` and
`desktop/tools` boundaries.
