import pytest
from click.testing import CliRunner
from unittest.mock import patch, MagicMock

from src.ai_docify.cli import main

@pytest.fixture
def runner():
    """Fixture for invoking the CLI."""
    return CliRunner()

@pytest.fixture
def mock_file(tmp_path):
    """Fixture for a dummy source file."""
    file_path = tmp_path / "my_script.py"
    file_path.write_text("def my_func(): pass")
    return str(file_path)

@patch("src.ai_docify.cli.validate_model")
@patch("src.ai_docify.cli.estimate_cost")
@patch("src.ai_docify.cli.generate_documentation")
@patch("src.ai_docify.cli.write_output_file")
@patch("src.ai_docify.cli.prompt_confirmation")
def test_cli_success_with_confirmation(
    mock_prompt, mock_write, mock_generate, mock_estimate, mock_validate, runner, mock_file
):
    """Test a successful run where the user confirms."""
    mock_validate.return_value = True
    mock_estimate.return_value = {"tokens": 100, "input_cost": 0.001, "currency": "USD"}
    mock_prompt.return_value = True
    mock_generate.return_value = ("# Documented code", {"input_tokens": 100, "output_tokens": 200})
    
    result = runner.invoke(
        main,
        [mock_file, "--provider", "openai", "--model", "gpt-4", "--mode", "rewrite"],
    )

    assert result.exit_code == 0
    assert "Estimation" in result.output
    mock_prompt.assert_called_once()
    mock_generate.assert_called_once()
    mock_write.assert_called_once()
    assert "Successfully generated documentation!" in result.output
    assert "Final Usage Report" in result.output

@patch("src.ai_docify.cli.validate_model")
@patch("src.ai_docify.cli.estimate_cost")
@patch("src.ai_docify.cli.generate_documentation")
@patch("src.ai_docify.cli.write_output_file")
@patch("src.ai_docify.cli.prompt_confirmation")
def test_cli_success_with_yes_flag(
    mock_prompt, mock_write, mock_generate, mock_estimate, mock_validate, runner, mock_file
):
    """Test a successful run using the --yes flag to skip confirmation."""
    mock_validate.return_value = True
    mock_estimate.return_value = {"tokens": 100, "input_cost": 0.001, "currency": "USD"}
    mock_generate.return_value = ("# Documented code", {"input_tokens": 100, "output_tokens": 200})

    result = runner.invoke(
        main,
        [mock_file, "--provider", "openai", "--model", "gpt-4", "--mode", "rewrite", "--yes"],
    )

    assert result.exit_code == 0
    mock_prompt.assert_not_called()
    mock_generate.assert_called_once()
    assert "Successfully generated documentation!" in result.output

@patch("src.ai_docify.cli.validate_model")
@patch("src.ai_docify.cli.estimate_cost")
@patch("src.ai_docify.cli.prompt_confirmation")
def test_cli_user_aborts(mock_prompt, mock_estimate, mock_validate, runner, mock_file):
    """Test scenario where the user aborts at the confirmation prompt."""
    mock_validate.return_value = True
    mock_estimate.return_value = {"tokens": 100, "input_cost": 0.001, "currency": "USD"}
    mock_prompt.return_value = False

    result = runner.invoke(
        main,
        [mock_file, "--provider", "openai", "--model", "gpt-4"],
    )

    assert result.exit_code == 0
    assert "Aborted by user" in result.output

@patch("src.ai_docify.cli.validate_model")
def test_cli_invalid_model(mock_validate, runner, mock_file):
    """Test that the CLI exits if the model is not configured."""
    mock_validate.return_value = False
    
    result = runner.invoke(
        main,
        [mock_file, "--provider", "openai", "--model", "invalid-model"],
    )

    assert result.exit_code == 1
    assert "Error: Model 'invalid-model'' is not configured for provider 'openai' in your \npricing.json.\n" in result.output

def test_cli_file_not_found(runner):
    """Test that Click handles a non-existent file path."""
    result = runner.invoke(
        main,
        ["non_existent_file.py", "--provider", "openai", "--model", "gpt-4"],
    )
    
    assert result.exit_code != 0
    assert "Error: Invalid value for 'FILEPATH'" in result.output

@patch("src.ai_docify.cli.validate_model")
@patch("src.ai_docify.cli.estimate_cost")
@patch("src.ai_docify.cli.generate_documentation")
@patch("src.ai_docify.cli.prompt_confirmation")
def test_cli_api_error(
    mock_prompt, mock_generate, mock_estimate, mock_validate, runner, mock_file
):
    """Test handling of an API error during generation."""
    mock_validate.return_value = True
    mock_estimate.return_value = {"tokens": 100, "input_cost": 0.001, "currency": "USD"}
    mock_prompt.return_value = True
    mock_generate.return_value = ("Error: API is down", {})

    result = runner.invoke(
        main,
        [mock_file, "--provider", "openai", "--model", "gpt-4", "--yes"],
    )

    assert result.exit_code == 0
    assert "Error: API is down" in result.output
    assert "Successfully generated documentation!" not in result.output
    assert "Final Usage Report" not in result.output
