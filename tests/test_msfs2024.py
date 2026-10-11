"""MSFS 2024 XML regression tests."""
from fs2020_plugin.ms_flight_simulator import (
    FS2020Parser,
    parse_joystick_bind_information,
    process_xml_file,
)
from joystick_diagrams.input.profile_collection import ProfileCollection


def test_2024_inputs():
    assert parse_joystick_bind_information("Button10") is not None
    assert parse_joystick_bind_information("Axis X") is not None
    assert parse_joystick_bind_information("Axis Z") is not None
    assert parse_joystick_bind_information("Rotation Z") is not None
    assert parse_joystick_bind_information("Slider X") is not None
    assert parse_joystick_bind_information("unknown input") is None


def test_2024_device_and_multiple_actions(tmp_path):
    xml = """<?xml version="1.0" encoding="utf-8"?>
<DefaulftInput Primary="1" PlatformAvailability="PC">
  <Device DeviceName="Saitek X52 Pro 2024 Planes" GUID="test-guid">
    <Context ContextName="AIRCRAFT">
      <Action ActionName="KEY_GEAR_DOWN"><Primary><KEY Information="Button10">9</KEY></Primary></Action>
      <Action ActionName="KEY_GEAR_UP"><Primary><KEY Information="Button9">8</KEY></Primary></Action>
      <Action ActionName="KEY_THROTTLE_AXIS_SET_EX1"><Primary><KEY Information="Axis Z">1058</KEY></Primary></Action>
    </Context>
  </Device>
</DefaulftInput>
"""
    folder = tmp_path / "profiles"
    folder.mkdir()
    file = folder / "Saitek_X52_Pro_2024_Planes.xml"
    file.write_text(xml, encoding="utf-8")
    collection = FS2020Parser(tmp_path).run()
    assert collection.get_profile("Default") is not None


def test_direct_xml_file_in_selected_folder(tmp_path):
    (tmp_path / "profile.xml").write_text(
        '<?xml version="1.0"?><DefaulftInput><Device DeviceName="X52" GUID="test" /></DefaulftInput>',
        encoding="utf-8",
    )
    collection = FS2020Parser(tmp_path).run()
    assert collection.get_profile("Default") is not None
