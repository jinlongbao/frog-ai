import os
import subprocess
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger("frog-shadow-manager")

class ShadowManager:
    """
    Manages workspace snapshots and rollbacks using Git.
    Ensures that all tool-driven changes are reversible and auditable.
    """
    def __init__(self, workspace_path: str):
        self.workspace_path = workspace_path
        self._ensure_git_init()

    def _ensure_git_init(self):
        """Ensures the workspace is a git repository."""
        if not os.path.exists(os.path.join(self.workspace_path, ".git")):
            logger.info("Initializing new git repository for shadow execution safety.")
            self._run_git(["init"])
            self._run_git(["add", "."])
            self._run_git(["commit", "-m", "Frog Initial Snapshot"])

    def _run_git(self, args: List[str]) -> str:
        """Helper to run git commands in the workspace."""
        try:
            result = subprocess.run(
                ["git"] + args,
                cwd=self.workspace_path,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            logger.error(f"Git command failed: {e.stderr}")
            raise RuntimeError(f"Git error: {e.stderr}")

    def take_snapshot(self, message: str = "Frog Shadow Snapshot"):
        """Takes a snapshot of the current state."""
        try:
            self._run_git(["add", "."])
            # Check if there are changes to commit
            status = self._run_git(["status", "--porcelain"])
            if status:
                self._run_git(["commit", "-m", message])
                logger.info(f"Snapshot taken: {message}")
            else:
                logger.info("No changes to snapshot.")
        except Exception as e:
            logger.warning(f"Failed to take snapshot: {e}")

    def get_diff(self) -> Dict[str, List[str]]:
        """Returns a summary of changes since the last commit."""
        try:
            # We look at the changes in the latest commit
            # Or if we want 'since last snapshot', we assume the last commit IS the snapshot
            raw_diff = self._run_git(["show", "--name-status", "HEAD"])
            
            lines = raw_diff.splitlines()
            changes = {"added": [], "modified": [], "deleted": []}
            
            for line in lines:
                if line.startswith("A\t"):
                    changes["added"].append(line.split("\t")[1])
                elif line.startswith("M\t"):
                    changes["modified"].append(line.split("\t")[1])
                elif line.startswith("D\t"):
                    changes["deleted"].append(line.split("\t")[1])
                    
            return changes
        except Exception as e:
            logger.error(f"Failed to get diff: {e}")
            return {"added": [], "modified": [], "deleted": []}

    def rollback(self):
        """Reverts the workspace to the state of the last commit."""
        try:
            logger.warning("Rolling back workspace to last snapshot...")
            self._run_git(["reset", "--hard", "HEAD^"])
            # Or if we just committed the 'bad' work, we reset to HEAD~1
            logger.info("Rollback complete.")
            return True
        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return False

    def get_last_commit_hash(self) -> str:
        try:
            return self._run_git(["rev-parse", "HEAD"])
        except:
            return ""
