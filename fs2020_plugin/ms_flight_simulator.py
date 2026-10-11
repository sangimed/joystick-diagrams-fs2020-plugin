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
    "L-Axis X-": Axis(AxisDirection.X),
    "L-Axis X+": Axis(AxisDirection.X),
    "L-Axis Y": Axis(AxisDirection.Y),
    "L-Axis Y-": Axis(AxisDirection.Y),
    "L-Axis Y+": Axis(AxisDirection.Y),
    "L-Axis Z": Axis(AxisDirection.Z),
    "L-Axis Z-": Axis(AxisDirection.Z),
    "L-Axis Z+": Axis(AxisDirection.Z),
    "R-Axis X": Axis(AxisDirection.RX),
    "R-Axis X-": Axis(AxisDirection.RX),
    "R-Axis X+": Axis(AxisDirection.RX),
    "R-Axis Y": Axis(AxisDirection.RY),
    "R-Axis Y-": Axis(AxisDirection.RY),
    "R-Axis Y+": Axis(AxisDirection.RY),
    "R-Axis Z": Axis(AxisDirection.RZ),
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

_AXIS_LOOKUP = {key.casefold(): value for key, value in AXIS_TO_AXIS_TYPES.items()}

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

_HAT_DIR_LOOKUP = {key.casefold(): value for key, value in HAT_DIR_TO_DIR.items()}

default_profile_name = "Default"


class FS2020Parser:
    def __init__(self, folder_path):
        self.folder_path = Path(folder_path)
        self.data = list()

    def run(self):
        pc = ProfileCollection()
        pc.create_profile(default_profile_name)

        if not self.folder_path.exists():
            _logger.warning("Profile path does not exist: %s", self.folder_path)
            return pc

        entries = (
            [self.folder_path]
            if self.folder_path.is_file()
            else self.folder_path.iterdir()
        )
        xml_files = check_folders(entries)

        _logger.debug("XMLs detected %s", xml_files)

        for xml in xml_files:
            _logger.debug("Processing %s", xml)
            try:
                process_xml_file(xml, pc)
            except (OSError, eT.ParseError, ValueError, KeyError) as exc:
                _logger.warning("Skipping invalid input profile %s: %s", xml, exc)

        return pc

    def handle_valid_file(self, file):
        self.data.append(file)


def _parse_xml_content(content: str) -> eT.Element:
    """Parse both normal XML documents and MSFS multi-root profile exports."""
    try:
        return eT.fromstring(content)
    except eT.ParseError as original_error:
        without_declaration = re.sub(
            r"^\s*<\?xml[^>]*\?>",
            "",
            content,
            count=1,
            flags=re.IGNORECASE,
        )
        try:
            return eT.fromstring(f"<ProfileRoot>{without_declaration}</ProfileRoot>")
        except eT.ParseError:
            raise original_error


def process_xml_file(file: Path, profile_collection: ProfileCollection):
    content = file.read_text(encoding="utf-8-sig")
    xml = _parse_xml_content(content)

    devices = [xml] if xml.tag == "Device" else xml.findall(".//Device")
    for device in devices:
        process_device(device, profile_collection)


def _merge_action(existing_command: str, action: str) -> str:
    if not existing_command:
        return action

    commands = [command.strip() for command in existing_command.split(" | ")]
    if action in commands:
        return existing_command

    return f"{existing_command} | {action}"


def process_device(device_xml: eT.Element, collection: ProfileCollection):
    device_name = device_xml.get("DeviceName")
    device_guid = device_xml.get("GUID")

    if device_name is None or device_guid is None:
        return

    profile = collection.get_profile(default_profile_name)

    if profile is None:
        return

    dev = profile.add_device(device_guid, device_name)
    controls = process_contexts(device_xml.findall(".//Context"))

    for control in controls:
        existing_input = dev.get_input(
            dev.resolve_type(control.base_control), control.base_control.identifier
        )

        if existing_input and not control.modifiers:
            existing_input.command = _merge_action(existing_input.command, control.action)
            continue

        if existing_input and control.modifiers:
            existing_input.add_modifier(
                {modifier.identifier for modifier in control.modifiers}, control.action
            )
        elif control.modifiers:
            dev.add_modifier_to_input(
                control.base_control,
                {modifier.identifier for modifier in control.modifiers},
                control.action,
            )
        else:
            dev.create_input(control.base_control, control.action)


def process_contexts(contexts: list[eT.Element]) -> list["Control"]:
    controls = []

    for context in contexts:
        for action in context.findall("Action"):
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

    controls = []
    for key in keys:
        parsed = parse_joystick_bind_information(key.get("Information"))
        if parsed is None:
            return (None, None)
        controls.append(parsed)

    main_control = controls.pop(0)
    return (main_control, controls)


def parse_joystick_bind_information(bind_information: str | None):
    """Convert FS2020 or MSFS 2024 KEY Information into a host input."""
    if not bind_information:
        return None

    data = re.sub(
        r"^Joystick\s*", "", bind_information.strip(), count=1, flags=re.IGNORECASE
    )
    data = " ".join(data.split())

    button_match = re.fullmatch(r"Button\s*(\d+)", data, re.IGNORECASE)
    if button_match:
        return Button(int(button_match.group(1)))

    pov_match = re.fullmatch(r"Pov\s*(?:(\d+)\s*)?(.+)", data, re.IGNORECASE)
    if pov_match:
        direction_name = re.sub(r"[\s-]+", "_", pov_match.group(2)).strip("_")
        direction = _HAT_DIR_LOOKUP.get(direction_name.casefold())
        if direction is not None:
            return Hat(int(pov_match.group(1) or 1), direction)

    axis = _AXIS_LOOKUP.get(data.casefold())
    if axis is not None:
        return axis

    _logger.warning("Unsupported joystick input: %s", bind_information)
    return None


def split_action_name(name_key: str):
    splits = [x for x in name_key.split("_") if x not in ["KEY", "AXIS"]]
    return " ".join(splits).title()


def file_check(file: Path) -> bool:
    try:
        with file.open("rb") as source:
            sample = source.read(256)
    except OSError as exc:
        _logger.warning("Unable to read candidate profile %s: %s", file, exc)
        return False

    sample = sample.removeprefix(b"\xef\xbb\xbf").lstrip()
    return sample.startswith(b"<")


def check_folders(folders):
    valid_files = []

    for entry in sorted(folders, key=lambda path: str(path).casefold()):
        if entry.is_file():
            if entry.suffix.lower() == ".xml" and file_check(entry):
                valid_files.append(entry)
            continue

        if not entry.is_dir():
            continue

        for file in sorted(entry.rglob("*"), key=lambda path: str(path).casefold()):
            if not file.is_file() or file.suffix.lower() != ".xml":
                continue
            _logger.debug("Processing file %s", file)
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
