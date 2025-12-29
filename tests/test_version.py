from ai_docify import __version__


def test_version():
    """Assert that the package version is a string and not empty."""
    assert isinstance(__version__, str)
    assert len(__version__) > 0
