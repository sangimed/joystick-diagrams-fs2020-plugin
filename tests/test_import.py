import fs2020_plugin.main as m


def test_plugin_metadata():
    assert m.ParserPlugin.plugin_meta.name == "Flight Simulator 2020 / 2024"
    assert m.ParserPlugin.plugin_meta.version == "0.1.0"

    # ``id`` is only exposed by newer host builds of PluginMeta; guard so the smoke test
    # passes against hosts that predate the plugin-catalog id field. When present, it must
    # match the plugin's declared GUID.
    plugin_id = getattr(m.ParserPlugin.plugin_meta, "id", None)
    if plugin_id is not None:
        assert str(plugin_id) == "a45f6e83-0460-4d05-86c6-ac4a5704361e"
