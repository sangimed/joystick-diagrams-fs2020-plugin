# Joystick Diagrams — Flight Simulator 2020 Plugin

Parser plugin for [Joystick Diagrams](https://github.com/Rexeh/joystick-diagrams) that reads
Microsoft Flight Simulator 2020 keybind exports and turns them into device profiles the app can draw.

This plugin is **not bundled** with the application. Install it from inside Joystick Diagrams via
**Plugins → Store**, or point the installer at a release ZIP below.

- **Plugin ID:** `a45f6e83-0460-4d05-86c6-ac4a5704361e`
- **Type:** parser
- **Current version:** 0.0.1

## Repository layout

```
fs2020_plugin/            # the importable plugin package — this folder is what ships in the release ZIP
  __init__.py
  main.py                 # ParserPlugin entry point + FS2020Settings
  ms_flight_simulator.py  # FS2020Parser core logic
  img/icon.png
tests/                    # standalone smoke test
scripts/sign_plugin.py
```

## How it loads in the host

At runtime the host app imports this package and resolves `joystick_diagrams.*` against itself, so
imports of `joystick_diagrams.input.*`, `...plugin_interface`, and `...plugin_settings` stay
**absolute**. Intra-plugin imports (e.g. `from .ms_flight_simulator import FS2020Parser`) are
**relative**.

Installed plugins cannot ship their own PyPI dependencies — they run inside the host's frozen
environment. This plugin needs only the host SDK and the Python standard library.

## Development

```bash
# Install the host package (provides the joystick_diagrams SDK) plus dev tooling
pip install "joystick-diagrams @ git+https://github.com/Rexeh/joystick-diagrams@master"
pip install -e ".[dev]"

pytest tests/
ruff check .
```

## Releasing

Tag a release as `vX.Y.Z` (matching `plugin_meta.version` in `main.py`). The release workflow
zips the `fs2020_plugin/` folder, optionally signs it (see below), computes its SHA-256, and
publishes `fs2020_plugin.zip` as a release asset.

Then update the catalog manifest entry (`download_url` + `sha256`) that the app reads.

### Signing (for first-party "verified" releases)

The store shows this plugin as **Verified** only if the release ZIP contains a valid `plugin.sig`.
Signing uses the project's Ed25519 developer **private** key, stored as the repository/organisation
Actions secret `PLUGIN_SIGNING_KEY` (PEM). The matching public key is baked into the host
(`joystick_diagrams/plugins/plugin_signing.py`). Without the secret the workflow still ships an
**unsigned** ZIP (installs with a trust prompt).
