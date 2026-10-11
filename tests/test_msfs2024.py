"""MSFS 2024 XML regression tests."""

from fs2020_plugin.ms_flight_simulator import (
    FS2020Parser,
    parse_joystick_bind_information,
)
from joystick_diagrams.input.axis import Axis, AxisDirection, AxisSlider
from joystick_diagrams.input.button import Button
from joystick_diagrams.input.hat import Hat, HatDirection

VALID_GUID = "{FE843A40-C4D6-11F1-8001-444553540000}"
OFFICIAL_GUID = "b52fe8d0-9792-11ef-8001-444553540000"


def _single_device(collection):
    profile = collection.get_profile("Default")
    assert profile is not None
    assert len(profile.devices) == 1
    return next(iter(profile.devices.values()))


def test_2024_input_aliases():
    assert parse_joystick_bind_information("Button10") == Button(10)
    assert parse_joystick_bind_information("Joystick Button 9") == Button(9)
    assert parse_joystick_bind_information("Axis X") == Axis(AxisDirection.X)
    assert parse_joystick_bind_information("Axis Z") == Axis(AxisDirection.Z)
    assert parse_joystick_bind_information("Rotation Y") == Axis(AxisDirection.RY)
    assert parse_joystick_bind_information("Rotation Z") == Axis(AxisDirection.RZ)
    assert parse_joystick_bind_information("Slider X") == AxisSlider(1)
    assert parse_joystick_bind_information("Slider Y") == AxisSlider(2)

    # Actual MSFS 2024 custom-export strings from an X52 Pro profile.
    assert parse_joystick_bind_information("Joystick L-Axis Z ") == Axis(
        AxisDirection.Z
    )
    assert parse_joystick_bind_information("Joystick R-Axis X ") == Axis(
        AxisDirection.RX
    )
    assert parse_joystick_bind_information("Joystick R-Axis Y ") == Axis(
        AxisDirection.RY
    )
    assert parse_joystick_bind_information("Joystick R-Axis Z ") == Axis(
        AxisDirection.RZ
    )
    assert parse_joystick_bind_information("JoystickPov Left") == Hat(
        1, HatDirection.L
    )
    assert parse_joystick_bind_information("Pov2 Up Right") == Hat(
        2, HatDirection.UR
    )
    assert parse_joystick_bind_information("unknown input") is None


def test_official_2024_wrapper_primary_secondary_and_modifiers(tmp_path):
    xml = f"""<?xml version="1.0" encoding="utf-8"?>
<DefaulftInput Primary="1" PlatformAvailability="PC">
  <Version Num="4548" />
  <Device DeviceName="Saitek X52 Pro 2024 Planes" GUID="{OFFICIAL_GUID}">
    <Context ContextName="AIRCRAFT">
      <Action ActionName="KEY_GEAR_DOWN">
        <Primary><KEY Information="Button10">9</KEY></Primary>
        <Secondary><KEY Information="Button9">8</KEY></Secondary>
      </Action>
      <Action ActionName="KEY_AXIS_MIXTURE_SET">
        <Primary><KEY Information="Rotation Y">786</KEY></Primary>
      </Action>
      <Action ActionName="KEY_LEAD_POLE_TOGGLE">
        <Primary>
          <KEY Information="Button6">5</KEY>
          <KEY Information="Button5">4</KEY>
        </Primary>
      </Action>
    </Context>
  </Device>
</DefaulftInput>
"""
    profile_file = tmp_path / "Saitek_X52_Pro_2024_Planes.xml"
    profile_file.write_text(xml, encoding="utf-8")

    device = _single_device(FS2020Parser(tmp_path).run())
    inputs = device.get_combined_inputs()

    assert inputs["BUTTON_10"].command == "Gear Down"
    assert inputs["BUTTON_9"].command == "Gear Down"
    assert inputs["AXIS_RY"].command == "Mixture Set"

    modifier_input = inputs["BUTTON_6"]
    assert modifier_input.command == ""
    assert len(modifier_input.modifiers) == 1
    assert modifier_input.modifiers[0].modifiers == {"BUTTON_5"}
    assert modifier_input.modifiers[0].command == "Lead Pole Toggle"


def test_custom_2024_fragment_export(tmp_path):
    # User-created MSFS 2024 exports are XML fragments with Version,
    # FriendlyName and Device as sibling top-level elements.
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Version Num="-1"/>
<FriendlyName PlatformAvailability="1" Locked="false">X52 Pro - Test - Planes</FriendlyName>
<Device DeviceName="X52 Professional H.O.T.A.S." GUID="{VALID_GUID}" ProductID="1890">
  <Context ContextName="AIRCRAFT">
    <Action ActionName="KEY_THROTTLE_AXIS_SET_EX1">
      <Primary><KEY Information="Joystick L-Axis Z ">1058</KEY></Primary>
    </Action>
    <Action ActionName="KEY_AXIS_MIXTURE_SET">
      <Primary><KEY Information="Joystick R-Axis X ">770</KEY></Primary>
    </Action>
    <Action ActionName="KEY_PROP_PITCH_AXIS_SET_EX1">
      <Primary><KEY Information="Joystick R-Axis Y ">786</KEY></Primary>
    </Action>
    <Action ActionName="KEY_AXIS_RUDDER_SET">
      <Primary><KEY Information="Joystick R-Axis Z ">802</KEY></Primary>
    </Action>
    <Action ActionName="KEY_COCKPIT_QUICKVIEW3">
      <Primary><KEY Information="Joystick Pov Right">257</KEY></Primary>
    </Action>
    <Action ActionName="KEY_COCKPIT_QUICKVIEW4">
      <Primary><KEY Information="JoystickPov Left">259</KEY></Primary>
    </Action>
  </Context>
</Device>
"""
    (tmp_path / "X52 Pro - Test - Planes.xml").write_text(xml, encoding="utf-8")

    device = _single_device(FS2020Parser(tmp_path).run())
    inputs = device.get_combined_inputs()

    assert inputs["AXIS_Z"].command == "Throttle Set Ex1"
    assert inputs["AXIS_RX"].command == "Mixture Set"
    assert inputs["AXIS_RY"].command == "Prop Pitch Set Ex1"
    assert inputs["AXIS_RZ"].command == "Rudder Set"
    assert inputs["POV_1_R"].command == "Cockpit Quickview3"
    assert inputs["POV_1_L"].command == "Cockpit Quickview4"


def test_general_and_aircraft_profiles_merge_for_same_device(tmp_path):
    general = f"""<?xml version="1.0"?>
<Version Num="-1"/>
<FriendlyName>General</FriendlyName>
<Device DeviceName="X52 Pro" GUID="{VALID_GUID}">
  <Context ContextName="MODES">
    <Action ActionName="KEY_COCKPIT_RESET">
      <Primary><KEY Information="Joystick Button 5">4</KEY></Primary>
    </Action>
  </Context>
</Device>
"""
    aircraft = f"""<?xml version="1.0"?>
<Version Num="-1"/>
<FriendlyName>Planes</FriendlyName>
<Device DeviceName="X52 Pro" GUID="{VALID_GUID}">
  <Context ContextName="AIRCRAFT">
    <Action ActionName="KEY_AP_MASTER">
      <Primary><KEY Information="Joystick Button 2">1</KEY></Primary>
    </Action>
    <Action ActionName="KEY_AP_MASTER">
      <Secondary><KEY Information="Joystick Button 2">1</KEY></Secondary>
    </Action>
  </Context>
</Device>
"""
    (tmp_path / "General.xml").write_text(general, encoding="utf-8")
    (tmp_path / "Planes.xml").write_text(aircraft, encoding="utf-8")

    device = _single_device(FS2020Parser(tmp_path).run())
    inputs = device.get_combined_inputs()

    assert inputs["BUTTON_5"].command == "Cockpit Reset"
    assert inputs["BUTTON_2"].command == "Ap Master"


def test_recursive_uppercase_xml_and_utf8_bom(tmp_path):
    nested = tmp_path / "nested"
    nested.mkdir()
    profile_file = nested / "PROFILE.XML"
    profile_file.write_bytes(
        b"\xef\xbb\xbf"
        + (
            f'<?xml version="1.0"?><Device DeviceName="X52" GUID="{VALID_GUID}">'
            '<Context ContextName="AIRCRAFT"><Action ActionName="KEY_BRAKES">'
            '<Primary><KEY Information="Joystick Button 1">0</KEY></Primary>'
            "</Action></Context></Device>"
        ).encode()
    )

    device = _single_device(FS2020Parser(tmp_path).run())
    assert device.get_combined_inputs()["BUTTON_1"].command == "Brakes"


def test_direct_xml_file_path_is_supported(tmp_path):
    profile_file = tmp_path / "profile.xml"
    profile_file.write_text(
        f'<?xml version="1.0"?><Device DeviceName="X52" GUID="{VALID_GUID}" />',
        encoding="utf-8",
    )

    device = _single_device(FS2020Parser(profile_file).run())
    assert device.name == "X52"
