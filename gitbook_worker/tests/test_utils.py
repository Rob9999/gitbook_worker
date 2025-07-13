import shutil
import pytest
from gitbook_worker.src.gitbook_worker.utils import get_pandoc_version, font_available


@pytest.mark.skipif(shutil.which("pandoc") is None, reason="pandoc not installed")
def test_get_pandoc_version_format():
    version = get_pandoc_version()
    assert isinstance(version, tuple)
    assert all(isinstance(v, int) for v in version)


def test_font_available_false():
    assert font_available("DefinitelyMissingFontXYZ") is False
