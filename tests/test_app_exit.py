"""Test that the app exits cleanly without pygame errors."""
import os
import subprocess
import sys
from pathlib import Path


def test_app_exits_cleanly_headless():
    """Verify app can exit cleanly in headless mode without pygame.error."""
    env = os.environ.copy()
    env["SDL_VIDEODRIVER"] = "dummy"
    repo_root = Path(__file__).resolve().parents[1]

    result = subprocess.run(
        [sys.executable, "main.py", "--max-frames", "1"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        env=env,
    )

    # Should exit successfully
    assert result.returncode == 0, f"Exit code {result.returncode}. stderr: {result.stderr}"

    # Should not have pygame.error
    assert "pygame.error" not in result.stderr, f"pygame.error found in stderr: {result.stderr}"
    assert "video system not initialized" not in result.stderr, (
        f"video system not initialized found: {result.stderr}"
    )
