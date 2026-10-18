import pets_in_editor


def test_plugin_metadata():
    assert pets_in_editor.PLUGIN_NAME == "Pets in Editor"
    assert pets_in_editor.PLUGIN_VERSION == "0.4.0a1"
    assert pets_in_editor.PLUGIN_AUTHOR == "HiroYokoyama"
    assert pets_in_editor.PLUGIN_DESCRIPTION
    assert pets_in_editor.PLUGIN_CATEGORY == "Utility"
    assert pets_in_editor.PLUGIN_SUPPORTED_MOLEDITPY_VERSION == "4.*"
    assert "Utility" in pets_in_editor.PLUGIN_TAGS
    assert isinstance(pets_in_editor.PLUGIN_DEPENDENCIES, list)
    assert isinstance(pets_in_editor.PLUGIN_OPTIONAL_DEPENDENCIES, list)
    assert pets_in_editor.__version__ == pets_in_editor.PLUGIN_VERSION
    assert pets_in_editor.__author__ == pets_in_editor.PLUGIN_AUTHOR


def test_entry_points_exist():
    assert callable(pets_in_editor.initialize)
    assert callable(pets_in_editor.shutdown)
