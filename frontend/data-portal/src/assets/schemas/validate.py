"""Transpilation and validation script for GHGA metadata files."""

import io
import os
import sys
import traceback
from contextlib import redirect_stderr, redirect_stdout

original_argv = list(sys.argv)
schema_filename, in_filename = args_js.to_py() 

def validate():
    """Validate the JSON using schemapack."""

    success = False
    stdout = io.StringIO()
    stderr = io.StringIO()

    sys.argv = [
        "schemapack",
        "validate",
        "--schemapack",
        schema_filename,
        "--datapack",
        in_filename,
    ]

    try:
        from schemapack.__main__ import cli as schemapack_main_func

        # Redirect stdout/stderr for schemapack specifically
        with redirect_stdout(stdout), redirect_stderr(stderr):
            schemapack_main_func()

        # Determine validation success based on exit code or stderr content
        errors = stderr.getvalue().strip()
        success = "error" not in errors.lower()

    except SystemExit as e:
        if e.code == 0:
            success = True

        else:
            success = False
            print(
                f"[Python] ERROR: schemapack exited with code {e.code} (validation failure)."
            )
    except ImportError as e:
        stderr.write(f"ImportError during schemapack: {str(e)}")
    except Exception as e:
        tb = traceback.format_exc()
        stderr.write(
            f"Exception during schemapack: {type(e).__name__}: {str(e)}\nTraceback:\n{tb}"
        )
    finally:
        sys.argv = original_argv

    return {
        "success": success,
        "output": stdout.getvalue(),
        "error_message": stderr.getvalue(),
    }

def main():
    """Main entry point for the validation script."""

    results = validate()
    success= results["success"]
    return results

main()
