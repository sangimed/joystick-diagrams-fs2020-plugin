from fs2020_plugin.ms_flight_simulator import FS2020Parser


MSFS2024_PROFILE = """<?xml version="1.0" encoding="UTF-8"?>
<Version Num="4548"/>
<FriendlyName>X52 Pro - MSFS 2024 Test</FriendlyName>
<Device DeviceName=" Saitek X52 Pro Flight Control System " GUID="{11111111-2222-3333-4444-555555555555}" ProductID="1234">
    <Axes>
        <Axis AxisName="X" AxisSensitivy="0" AxisSensitivyMinus="0" AxisNeutral="0" AxisDeadZone="0" AxisOutDeadZone="0" AxisResponseRate="-1"/>
    </Axes>
    <Context ContextName="AIRCRAFT">
        <Action ActionName="KEY_BRAKES" Flag="2">
            <Primary>
                <KEY Information="Joystick Button 1">0</KEY>
            </Primary>
        </Action>
        <Action ActionName="KEY_GEAR_TOGGLE" Flag="2">
            <Primary>
                <KEY Information="Joystick Button 2">1</KEY>
            </Primary>
            <Secondary>
                <KEY Information="Joystick Button 3">2</KEY>
            </Secondary>
        </Action>
        <Action ActionName="KEY_THROTTLE_AXIS_SET_EX1" Flag="4">
            <Primary>
                <KEY Information="Joystick L-Axis Z ">1058</KEY>
            </Primary>
        </Action>
        <Action ActionName="KEY_MIXTURE_SET" Flag="132">
            <Primary>
                <KEY Information="Joystick R-Axis X ">770</KEY>
            </Primary>
        </Action>
        <Action ActionName="KEY_AXIS_SPOILER_SET" Flag="132">
            <Primary>
                <KEY Information="Joystick Slider X ">514</KEY>
            </Primary>
        </Action>
    </Context>
    <Context ContextName="COCKPIT_GLOBAL_CAMERA">
        <Action ActionName="KEY_COCKPIT_LOOK_UP" Flag="2">
            <Primary>
                <KEY Information="Joystick Pov Up">256</KEY>
            </Primary>
        </Action>
    </Context>
</Device>
"""


def test_msfs2024_export_is_discovered_and_parsed(tmp_path):
    profile_path = tmp_path / "x52-msfs2024.xml"
    profile_path.write_text(MSFS2024_PROFILE, encoding="utf-8")

    collection = FS2020Parser(tmp_path).run()
    profile = collection.get_profile("Default")

    assert profile is not None
    device = profile.get_device("11111111-2222-3333-4444-555555555555")
    assert device is not None

    inputs = device.get_combined_inputs()
    assert inputs["BUTTON_1"].command == "Brakes"
    assert inputs["BUTTON_2"].command == "Gear Toggle"
    assert inputs["BUTTON_3"].command == "Gear Toggle"
    assert inputs["AXIS_Z"].command == "Throttle Set Ex1"
    assert inputs["AXIS_RX"].command == "Mixture Set"
    assert inputs["AXIS_SLIDER_0"].command == "Spoiler Set"
    assert inputs["POV_1_U"].command == "Cockpit Look Up"
