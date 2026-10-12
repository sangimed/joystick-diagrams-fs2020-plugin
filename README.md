# Joystick Diagrams — Flight Simulator 2020 / 2024 Plugin

Parser plugin for [Joystick Diagrams](https://github.com/Rexeh/joystick-diagrams) that reads
Microsoft Flight Simulator 2020 and 2024 keybind XML files and turns them into device profiles the app can draw.

This plugin is **not bundled** with the application. Install it from inside Joystick Diagrams via
**Plugins → Store**, or point the installer at a release ZIP below.

- **Plugin ID:** `a45f6e83-0460-4d05-86c6-ac4a5704361e`
- **Type:** parser
- **Current version:** 0.1.0

## Supported MSFS 2024 profiles

The parser supports both MSFS 2024 profile formats seen in the simulator:

- official packaged profiles wrapped in `DefaulftInput`;
- user/custom exports where `Version`, `FriendlyName`, and `Device` are sibling top-level XML elements.

Supported bindings include:

- `Primary` and `Secondary` assignments;
- buttons in both `Button10` and `Joystick Button 10` forms;
- POV hats, including numbered hats and the compact `JoystickPov Left` form;
- `Axis X/Y/Z`, `Rotation X/Y/Z`, `Slider X/Y`;
- legacy `L-Axis` / `R-Axis` forms used by custom exports;
- modifier/chord bindings containing multiple `KEY` elements;
- multiple context-specific actions on the same button, axis, or modifier chord.

The parser searches the selected folder recursively and merges files that describe the same device
GUID into one Joystick Diagrams device. This makes it possible to select a folder containing both
General and Aircraft/Planes profiles and get a combined control map.

## MSFS 2024 setup

In **Plugins → Flight Simulator 2020 / 2024**, select the directory containing the simulator's XML
input profiles. The parser searches that directory and nested folders automatically.

For example, the default Steam-installed X52 Pro aircraft profile is typically under:

`C:\\Program Files (x86)\\Steam\\steamapps\\common\\MSFS2024\\Packages\\asobo-input-profiles-pc\\InputProfiles\\Categories\\Airplane`

Files under the game installation are the official defaults. To document your actual customized
bindings, select the folder containing your own exported/custom XML profiles instead.

## Repository layout

```text
fs2020_plugin/            # the importable plugin package — this folder is what ships in the release ZIP
  __init__.py
  main.py                 # ParserPlugin entry point + FS2020Settings
  ms_flight_simulator.py  # FS2020Parser core logic for FS2020 + MSFS 2024
  img/icon.png
tests/                    # regression and smoke tests
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
