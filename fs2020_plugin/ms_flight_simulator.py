import logging
import re
import xml.etree.ElementTree as eT
from dataclasses import dataclass
from pathlib import Path

from joystick_diagrams.input.axis import Axis, AxisDirection, AxisSlider
from joystick_diagrams.input.button import Button
from joystick_diagrams.input.hat import Hat, HatDirection
from joystick_diagrams.input.profile_collection import ProfileCollection

_logger = logging.getLogger(__name__)

AXIS_TO_AXIS_TYPES = {
    "R-Axis X-": Axis(AxisDirection.RX),
    "R-Axis X+": Axis(AxisDirection.RX),
    "L-Axis X": Axis(AxisDirection.X),
    "L-Axis Y": Axis(AxisDirection.Y),
    "R-Axis Z-": Axis(AxisDirection.RZ),
    "R-Axis Z+": Axis(AxisDirection.RZ),
    "Axis X": Axis(AxisDirection.X),
    "Axis Y": Axis(AxisDirection.Y),
    "Axis Z": Axis(AxisDirection.Z),
    "Rotation X": Axis(AxisDirection.RX),
    "Rotation Y": Axis(AxisDirection.RY),
    "Rotation Z": Axis(AxisDirection.RZ),
    "Slider X": AxisSlider(1),
    "Slider Y": AxisSlider(2),
}

HAT_DIR_TO_DIR = {
    "Up": HatDirection.U,
    "Up_Right": HatDirection.UR,
    "Right": HatDirection.R,
    "Down_Right": HatDirection.DR,
    "Down": HatDirection.D,
    "Down_Left": HatDirection.DL,
    "Left": HatDirection.L,
    "Up_Left": HatDirection.UL,
}

default_profile_name = "Default"


class FS2020Parser:
    def __init__(self, folder_path):
        self.folder_path = Path(folder_path)
        self.data = list()

    def run(self):
        folders = self.folder_path.iterdir()

        _logger.debug(f"Folders detected {folders}")

        pc = ProfileCollection()
        pc.create_profile(default_profile_name)

        xml_files = check_folders(folders)

        _logger.debug(f"XMLs detected {xml_files}")

        for xml in xml_files:
            _logger.debug(f"Processing {xml}")
            try:
                process_xml_file(xml, pc)
            except (OSError, eT.ParseError, ValueError, KeyError) as exc:
                _logger.warning("Skipping invalid input profile %s: %s", xml, exc)

        return pc

    def handle_valid_file(self, file):
        self.data.append(file)


def process_xml_file(file: Path, profile_collection: ProfileCollection):
    # Some FS2020 exports contain non-XML header lines. Prefer valid XML
    # without stripping any lines (MSFS 2024 exports are valid as-is).
    content = file.read_text(encoding="utf-8-sig")
    try:
        xml = eT.fromstring(content)
    except eT.ParseError:
        lines = content.splitlines(keepends=True)
        xml = eT.fromstringlist([line for i, line in enumerate(lines) if i not in (1, 2)])

    for device in ([xml] if xml.tag == "Device" else xml.findall(".//Device")):
        process_device(device, profile_collection)


def process_device(device_xml: eT.Element, collection: ProfileCollection):
    device_name = device_xml.get("DeviceName")
    device_guid = device_xml.get("GUID")

    if device_name is None or device_guid is None:
        return

    profile = collection.get_profile(default_profile_name)

    if profile is None:
        return

    dev = profile.add_device(device_guid, device_name)

    contexts = device_xml.findall("Context")

    controls = process_contexts(contexts)

    for control in controls:
        # Check if we have an existing input for the device
        existing_input = dev.get_input(
            dev.resolve_type(control.base_control), control.base_control.identifier
        )

        # Update the command to prevent overwrite
        if existing_input and not control.modifiers:
            if existing_input.command:
                existing_input.command = f"{existing_input.command} | {control.action}"
            else:
                existing_input.command = f"{control.action}"
            continue

        # Handle modifiers being added to existing controls (where we have overlapping base)
        if existing_input and control.modifiers:
            existing_input.add_modifier(
                {x.identifier for x in control.modifiers}, control.action
            )
        elif control.modifiers:
            dev.add_modifier_to_input(
                control.base_control,
                {x.identifier for x in control.modifiers},
                control.action,
            )
        else:
            dev.create_input(control.base_control, control.action)


def process_contexts(contexts: list[eT.Element]) -> list["Control"]:
    controls = []
    for context in contexts:
        # context_name = context.get("ContextName")

        actions = context.findall("Action")

        # Multiple contexts can be linked, i.e. X- and X+ are just X
        for action in actions:
            action_name_raw = action.get("ActionName")
            if action_name_raw is None:
                continue

            action_name = split_action_name(action_name_raw)

            primary = action.find("Primary")
            if primary is None:
                continue

            primary_action_keys = primary.findall("KEY")

            if primary_action_keys:
                control, modifiers = process_action_keys(primary_action_keys)

                if control is None:
                    continue

                controls.append(Control(action_name, control, modifiers))

    return controls


def process_action_keys(keys: list[eT.Element]) -> tuple:
    if not keys:
        return (None, None)

    if len(keys) == 1:
        ctrl = parse_joystick_bind_information(keys[0].get("Information"))
        return (ctrl, [])
    else:
        controls = list()
        for key in keys:
            parsed = parse_joystick_bind_information(key.get("Information"))
            if parsed is None:
                return (None, None)
            controls.append(parsed)

        if controls:
            main_control = controls.pop(0)

            return (main_control, controls)

        return (None, None)


def parse_joystick_bind_information(bind_information: str | None):
    """Convert FS2020 or MSFS2024 KEY Information into a host input."""
    if not bind_information:
        return None
    data = bind_information.replace("Joystick", "").strip()
    match = re.fullmatch(r"Button\\s*(\\d+)", data, re.IGNORECASE)
    if match:
        return Button(int(match.group(1)))
    match = re.fullmatch(r"Pov\\s*(?:([0-9]+)\\s*)?(Up_Right|Down_Right|Down_Left|Up_Left|Up|Right|Down|Left)", data, re.IGNORECASE)
    if match:
        direction = next((v for k, v in HAT_DIR_TO_DIR.items() if k.lower() == match.group(2).lower()), None)
        return Hat(int(match.group(1) or 1), direction) if direction else None
    axis = AXIS_TO_AXIS_TYPES.get(data)
    if axis is not None:
        return axis
    _logger.warning("Unsupported joystick input: %s", bind_information)
    return None


def split_action_name(name_key: str):
    splits = [x for x in name_key.split("_") if x not in ["KEY", "AXIS"]]
    return " ".join(splits).title()


def file_check(file):
    import os

    _logger.debug(f"File access: {os.stat(file).st_mode}")
    with open(file, "rb") as b:
        _logger.debug("File opened")
        if b.read(5) == b"<?xml":
            return True
    return False


def check_folders(folders):
    valid_files = []
    for folder in folders:
        if folder.is_file():
            if folder.suffix.lower() == ".xml" and file_check(folder):
                valid_files.append(folder)
            continue
        if not folder.is_dir():
            continue
        for file in folder.rglob("*.xml"):
            _logger.debug(f"Processing file {file}")
            if file_check(file):
                valid_files.append(file)

    return valid_files


@dataclass
class Control:
    action: str
    base_control: Button | Axis | AxisSlider | Hat
    modifiers: list[Button | Axis | AxisSlider | Hat]

    def __repr__(self):
        return f"{self.action} | {self.base_control} | {id(self.base_control)}"


if __name__ == "__main__":
    pass
