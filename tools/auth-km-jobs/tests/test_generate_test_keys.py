"""Test the generation of test keys."""

from typer.testing import CliRunner

from auth_km_jobs.__main__ import app

runner = CliRunner()


def test_generate_test_keys_single_sets():
    result = runner.invoke(app, ["generate-test-keys"])  # default: 1 each
    assert result.exit_code == 0, result.output

    keys = [line.split("=", 1)[0] for line in result.output.splitlines()]
    assert keys == [
        'JWK_PRIV', 'JWK_PUB',
        'C4GH_PRIV', 'C4GH_PRIV_RAW', 'C4GH_PUB',
        'TOKEN', 'TOKEN_HASH']


def test_generate_test_keys_multiple_sets():
    result = runner.invoke(app, [
        "generate-test-keys", "--num-jwk", "2", "--num-c4gh", "2", "--num-tokens", "2"
    ])
    assert result.exit_code == 0, result.output

    keys = [line.split("=", 1)[0] for line in result.output.splitlines()]
    assert keys == [
        'JWK_1_PRIV', 'JWK_1_PUB', 'JWK_2_PRIV', 'JWK_2_PUB',
        'C4GH_1_PRIV', 'C4GH_1_PRIV_RAW', 'C4GH_1_PUB',
        'C4GH_2_PRIV', 'C4GH_2_PRIV_RAW', 'C4GH_2_PUB',
        'TOKEN_1', 'TOKEN_1_HASH', 'TOKEN_2', 'TOKEN_2_HASH']
