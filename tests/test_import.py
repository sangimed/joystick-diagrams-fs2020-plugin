import fs2020_plugin.main as m


def test_plugin_metadata():
    assert m.ParserPlugin.plugin_meta.name == "Flight Simulator 2020"
    assert str(m.ParserPlugin.plugin_meta.id) == "a45f6e83-0460-4d05-86c6-ac4a5704361e"
