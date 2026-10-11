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
    "L-Axis X": Axis(AxisDirection.X),
    "L-Axis Y": Axis(AxisDirection.Y),
    "L-Axis Z": Axis(AxisDirection.Z),
    "R-Axis X": Axis(AxisDirection.RX),
    "R-Axis Y": Axis(AxisDirection.RY),
    "R-Axis Z": Axis(AxisDirection.RZ),
}

SLIDER_TO_AXIS_TYPES = {
    "Slider X": AxisSlider(0),
    "Slider Y": AxisSlider(1),
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

XML_DECLARATION_RE = re.compile(r"^\s*<\?xml[^>]*\?>", re.IGNORECASE)
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
            process_xml_file(xml, pc)

        return pc

    def handle_valid_file(self, file):
        self.data.append(file)


def process_xml_file(file: Path, profile_collection: ProfileCollection):
    try:
        content = file.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        _logger.warning("Unable to decode Flight Simulator profile %s", file)
        return

    device_xml = parse_device_xml(content)
    if device_xml is None:
        _logger.warning("No Device element found in Flight Simulator profile %s", file)
        return

    process_device(device_xml, profile_collection)


def parse_device_xml(content: str) -> eT.Element | None:
    """Return the Device node from an FS2020 or MSFS 2024 profile export.

    Flight Simulator profile files are often XML fragments rather than strictly valid XML:
    Version, FriendlyName and Device can all exist as top-level siblings. Wrapping the fragment
    lets ElementTree parse both those exports and regular XML documents.
    """
    content = XML_DECLARATION_RE.sub("", content, count=1).strip()
    if not content:
        return None

    try:
        root = eT.fromstring(content)
    except eT.ParseError:
        try:
            root = eT.fromstring(f"<Profile>{content}</Profile>")
        except eT.ParseError as exc:
            _logger.warning("Unable to parse Flight Simulator XML: %s", exc)
            return None

    if root.tag == "Device":
        return root

    return root.find(".//Device")


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
        existing_input = dev.get_input(
            dev.resolve_type(control.base_control), control.base_control.identifier
        )

        if existing_input and not control.modifiers:
            if existing_input.command:
                existing_input.command = f"{existing_input.command} | {control.action}"
            else:
                existing_input.command = f"{control.action}"
            continue

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
        actions = context.findall("Action")

        for action in actions:
            action_name_raw = action.get("ActionName")
            if action_name_raw is None:
                continue

            action_name = split_action_name(action_name_raw)

            for binding_name in ("Primary", "Secondary"):
                binding = action.find(binding_name)
                if binding is None:
                    continue

                action_keys = binding.findall("KEY")
                if not action_keys:
                    continue

                control, modifiers = process_action_keys(action_keys)
                if control is None or modifiers is None:
                    continue

                controls.append(Control(action_name, control, modifiers))

    return controls


def process_action_keys(keys: list[eT.Element]) -> tuple:
    if not keys:
        return (None, None)

    main_control = parse_joystick_bind_information(keys[0].get("Information"))
    if main_control is None:
        return (None, None)

    modifiers = []
    for key in keys[1:]:
        modifier = parse_joystick_bind_information(key.get("Information"))
        if modifier is None:
            return (None, None)
        modifiers.append(modifier)

    return (main_control, modifiers)


def parse_joystick_bind_information(bind_information: str | None):
    """Convert an FS2020/MSFS 2024 KEY Information value into an input control."""
    if bind_information is None:
        return None

    data = bind_information.replace("Joystick", "", 1).strip()
    data = " ".join(data.split())

    if data.startswith("Button "):
        try:
            return Button(int(data.removeprefix("Button ")))
        except ValueError:
            _logger.debug("Invalid joystick button binding: %s", bind_information)
            return None

    if data.startswith("Pov "):
        direction_name = re.sub(r"[\s-]+", "_", data.removeprefix("Pov ").strip())
        direction = HAT_DIR_TO_DIR.get(direction_name)
        return Hat(1, direction) if direction is not None else None

    axis_name = data.rstrip("+-").strip()
    if axis_name in AXIS_TO_AXIS_TYPES:
        return AXIS_TO_AXIS_TYPES[axis_name]

    if axis_name in SLIDER_TO_AXIS_TYPES:
        return SLIDER_TO_AXIS_TYPES[axis_name]

    _logger.debug("Unexpected control type: %s", bind_information)
    return None


def split_action_name(name_key: str):
    splits = [x for x in name_key.split("_") if x not in ["KEY", "AXIS"]]
    return " ".join(splits).title()


def file_check(file):
    import os

    _logger.debug(f"File access: {os.stat(file).st_mode}")
    with open(file, "rb") as b:
        header = b.read(256).lstrip(b"\xef\xbb\xbf").lstrip()
        return header.startswith((b"<?xml", b"<Version", b"<Device"))


def check_folders(folders):
    """Find profile files in both FS2020 WGS folders and MSFS 2024 export folders."""
    valid_files = []
    for path in folders:
        if path.is_file():
            if file_check(path):
                valid_files.append(path)
            continue

        if not path.is_dir():
            continue

        for file in path.iterdir():
            _logger.debug(f"Processing file {file}")
            if file.is_file() and file_check(file):
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
