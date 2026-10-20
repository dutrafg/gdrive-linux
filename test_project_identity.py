"""Guard the application's independent naming in tracked source and documentation."""
import subprocess
import unittest
from pathlib import Path


class ProjectIdentityTests(unittest.TestCase):
    def test_no_legacy_product_mentions_in_source_or_docs(self):
        root = Path(__file__).resolve().parent
        tracked = subprocess.run(["git", "ls-files"], cwd=root,
                                 capture_output=True, text=True, check=False)
        if tracked.returncode == 0:
            candidates = [root / name for name in tracked.stdout.splitlines()]
        else:
            candidates = list(root.rglob("*"))
        # Compose restricted brand names in memory, without including them in
        # the repository's source files or UI strings themselves.
        disallowed = ("in" + "sync", "i" + "sync")
        offenders = []
        for path in candidates:
            if not path.is_file() or ".git" in path.parts or "__pycache__" in path.parts:
                continue
            if path.stat().st_size > 3 * 1024 * 1024:
                continue
            try:
                contents = path.read_text(encoding="utf-8")
            except (UnicodeError, OSError):
                continue
            if any(word in contents.casefold() for word in disallowed):
                offenders.append(str(path.relative_to(root)))
        self.assertEqual(offenders, [],
                         "Identidade própria: referências externas em arquivos do projeto")


if __name__ == "__main__":
    unittest.main()
