# qret-cli-bundle

This package downloads a platform-specific `qret` CLI archive from GitHub Releases and prepends its directory to `PATH` when imported.

```python
import qret_cli_bundle
```

Environment variables:

- `QRET_BUNDLE_REPOSITORY` (default: `QunaSys/quration-cli-bundle`)
- `QRET_BUNDLE_TAG` (default: latest release)
