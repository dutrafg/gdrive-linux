import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from diagnostics import collect_diagnostics, format_report, run_probe

class DiagnosticsTests(unittest.TestCase):
    def test_missing_tools_reports_actionable_failures(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch("diagnostics.shutil.which", return_value=None), patch(
                    "diagnostics.run_probe", return_value=False):
                checks = collect_diagnostics({"folder": str(Path(tmp)/"missing"),
                                              "account": ""})
        results = {c["name"]: c for c in checks}
        self.assertFalse(results["rclone"]["ok"])
        self.assertFalse(results["Pasta local"]["ok"])
        self.assertFalse(results["Acesso à conta Google"]["ok"])
        self.assertIn("rclone.org", results["rclone"]["detail"])

    @patch("diagnostics.shutil.which", return_value="/usr/bin/rclone")
    @patch("diagnostics.run_probe", return_value=False)
    def test_detects_insecure_rclone_conf_permissions_without_leaking_text(self, probe, which):
        with tempfile.TemporaryDirectory() as root:
            conf = Path(root) / "rclone.conf"
            conf.write_text("access_token=SECRET_TEST", encoding="utf-8")
            conf.chmod(0o644)
            records = collect_diagnostics({
                "rclone_config_file": str(conf), "account": "", "folder": str(root)})
            result = {item["name"]: item for item in records}
            self.assertFalse(result["Proteção do arquivo OAuth"]["ok"])
            self.assertNotIn("SECRET_TEST", format_report(records))

    def test_report_contains_no_tokens(self):
        text = format_report([{"name": "rclone", "ok": True, "detail": "Disponível"},
                              {"name": "FUSE", "ok": False, "detail": "Instale fuse3"}])
        self.assertIn("rclone", text)
        self.assertIn("Instale fuse3", text)

    @patch("diagnostics.subprocess.run")
    def test_probe_uses_argument_list_not_shell(self, run):
        run.return_value.returncode = 0
        self.assertTrue(run_probe(["systemctl", "--user", "show-environment"]))
        self.assertEqual(run.call_args.args[0][0], "systemctl")
        self.assertNotIn("shell", run.call_args.kwargs)

if __name__ == "__main__":
    unittest.main()
