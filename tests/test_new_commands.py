import pytest
from click.testing import CliRunner
from pathlib import Path

from src.ai_docify.cli import main


@pytest.fixture
def runner():
    """Fixture for invoking the CLI."""
    return CliRunner()


# --- Tests for the 'clean' command ---


def test_clean_directory_does_not_exist(runner):
    """Test the clean command when the output directory does not exist."""
    with runner.isolated_filesystem():
        result = runner.invoke(main, ["clean", "--output-dir", "non_existent_dir"])
        assert result.exit_code == 0
        assert "Directory non_existent_dir not found" in result.output


def test_clean_empty_directory(runner):
    """Test the clean command when the output directory is empty."""
    with runner.isolated_filesystem():
        Path("ai_output").mkdir()
        result = runner.invoke(main, ["clean"])
        assert result.exit_code == 0
        assert "is already empty" in result.output


def test_clean_with_files_and_confirmation(runner):
    """Test the clean command with files, confirming deletion."""
    with runner.isolated_filesystem():
        output_dir = Path("ai_output")
        output_dir.mkdir()
        (output_dir / "file1.txt").touch()
        (output_dir / "file2.txt").touch()

        result = runner.invoke(main, ["clean"], input="y\n")

        assert result.exit_code == 0
        assert "Successfully deleted 2 file(s)" in result.output
        assert not (output_dir / "file1.txt").exists()
        assert not (output_dir / "file2.txt").exists()


def test_clean_with_files_and_abort(runner):
    """Test the clean command with files, aborting deletion."""
    with runner.isolated_filesystem():
        output_dir = Path("ai_output")
        output_dir.mkdir()
        (output_dir / "file1.txt").touch()

        result = runner.invoke(main, ["clean"], input="n\n")

        assert result.exit_code == 0
        assert "Aborted by user" in result.output
        assert (output_dir / "file1.txt").exists()


def test_clean_with_yes_flag(runner):
    """Test the clean command using the --yes flag."""
    with runner.isolated_filesystem():
        output_dir = Path("ai_output")
        output_dir.mkdir()
        (output_dir / "file1.txt").touch()

        result = runner.invoke(main, ["clean", "--yes"])

        assert result.exit_code == 0
        assert "Successfully deleted 1 file(s)" in result.output
        assert not (output_dir / "file1.txt").exists()


# --- Tests for the 'strip' command ---


@pytest.fixture
def mock_strip_file(tmp_path):
    """Fixture for a dummy source file to be stripped."""
    file_path = tmp_path / "strip_test.py"
    file_path.write_text('def my_func():\n    """This is a docstring."""\n    pass\n')
    return str(file_path)


def test_strip_success(runner, mock_strip_file):
    """Test a successful run of the strip command."""
    with runner.isolated_filesystem():
        # The mock_strip_file is in a temporary directory, so we need to copy it
        # into the isolated filesystem to test the output directory creation.
        source_file = Path("my_script_to_strip.py")
        source_file.write_text(Path(mock_strip_file).read_text())

        result = runner.invoke(main, ["strip", str(source_file)])

        assert result.exit_code == 0
        assert "Successfully stripped docstrings" in result.output

        stripped_dir = Path("stripped_scripts")
        assert stripped_dir.is_dir()

        output_file = stripped_dir / "my_script_to_strip_strip.py"
        assert output_file.is_file()

        content = output_file.read_text()
        assert '"""This is a docstring."""' not in content
        assert "def my_func" in content


def test_strip_file_not_found(runner):
    """Test that the strip command handles a non-existent file path."""
    result = runner.invoke(main, ["strip", "non_existent_file.py"])
    assert result.exit_code != 0
    assert "Error: Invalid value for 'FILEPATH'" in result.output
