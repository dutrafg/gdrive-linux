"""QA for continuous, conflict-safe Google Drive mirroring (no Google account required)."""
import os
import json
import subprocess
import sys
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from background_sync import (
    build_plan, refresh_baseline, run_once, save_private_json, read_json,
    notify_if_changed, transfer_one, read_baseline,
)

MD5_A = ("md5", "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
MD5_B = ("md5", "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb")
MD5_C = ("md5", "cccccccccccccccccccccccccccccccc")

class SafePlanTests(unittest.TestCase):
    def test_new_files_both_directions(self):
        work, problems = build_plan({"local.txt": MD5_A}, {"remote.txt": MD5_B}, {})
        self.assertEqual(work, [("upload_new", "local.txt"), ("download_new", "remote.txt")])
        self.assertEqual(problems, [])

    def test_local_edit_only_uploads(self):
        work, problems = build_plan({"doc.txt": MD5_B}, {"doc.txt": MD5_A},
                                    {"doc.txt": MD5_A[1]})
        self.assertEqual(work, [("upload_update", "doc.txt")])
        self.assertEqual(problems, [])

    def test_remote_edit_only_downloads(self):
        work, problems = build_plan({"doc.txt": MD5_A}, {"doc.txt": MD5_B},
                                    {"doc.txt": MD5_A[1]})
        self.assertEqual(work, [("download_update", "doc.txt")])
        self.assertEqual(problems, [])

    def test_simultaneous_edit_is_conflict(self):
        work, problems = build_plan({"doc.txt": MD5_B}, {"doc.txt": MD5_C},
                                    {"doc.txt": MD5_A[1]})
        self.assertEqual(work, [])
        self.assertEqual(problems, ["doc.txt"])

    def test_google_native_document_without_md5_requires_export(self):
        remote = {"Planilhas/orcamento": ("metadata", "0", "2026-10-19")}
        actions, conflicts = build_plan({}, remote, {})
        self.assertEqual(actions, [])
        self.assertEqual(conflicts, ["Planilhas/orcamento"])

    def test_only_sha256_remote_is_not_assumed_to_match_local_md5(self):
        actions, conflicts = build_plan({}, {"sensitive.bin": ("sha256", "x"*64)}, {})
        self.assertEqual(actions, [])
        self.assertEqual(conflicts, ["sensitive.bin"])

    def test_initial_difference_is_conflict(self):
        work, problems = build_plan({"doc.txt": MD5_B}, {"doc.txt": MD5_C}, {})
        self.assertEqual(work, [])
        self.assertEqual(problems, ["doc.txt"])

    def test_deletions_are_not_propagated(self):
        for local, cloud in (({}, {"doc.txt": MD5_A}),
                             ({"doc.txt": MD5_A}, {})):
            work, problems = build_plan(local, cloud, {"doc.txt": MD5_A[1]})
            self.assertEqual(work, [])
            self.assertEqual(problems, ["doc.txt"])

    def test_versions_folder_is_never_synced(self):
        work, problems = build_plan(
            {".gdrive-linux-history/backup.txt": MD5_A}, {}, {})
        self.assertEqual(work, [])
        self.assertEqual(problems, [])

    def test_refresh_baseline_after_both_match(self):
        self.assertEqual(
            refresh_baseline({}, {"one.txt": MD5_A}, {"one.txt": MD5_A}),
            {"one.txt": MD5_A[1]})

    def test_corrupt_existing_history_fails_closed(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "existing.json"
            path.write_text("{corrupted", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Histórico"):
                read_baseline(path)

    def test_nonexistent_history_is_first_run(self):
        with tempfile.TemporaryDirectory() as root:
            self.assertEqual(read_baseline(Path(root) / "never.json"), {})

    def test_history_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "snapshot.json"
            path.symlink_to("/etc/passwd")
            with self.assertRaisesRegex(ValueError, "inseguro"):
                read_baseline(path)

    def test_history_invalid_hash_rejected_before_io(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "snapshot.json"
            path.write_text(json.dumps({"md5": {"document.txt": "INVALID"}}))
            with self.assertRaisesRegex(ValueError, "hashes inválidos"):
                read_baseline(path)

    def test_private_file_permissions(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state" / "snap.json"
            save_private_json(path, {"md5": {"doc.txt": MD5_A[1]}})
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(read_json(path)["md5"]["doc.txt"], MD5_A[1])

    @patch("background_sync.subprocess.run")
    @patch("background_sync.shutil.which", return_value="/usr/bin/notify-send")
    def test_notification_only_on_new_conflict(self, which, run):
        self.assertTrue(notify_if_changed(
            {"state": "ok"}, {"state": "conflicts", "conflicts": 2}))
        run.assert_called_once()
        self.assertFalse(notify_if_changed(
            {"state": "conflicts", "conflicts": 2},
            {"state": "conflicts", "conflicts": 2}))

    @patch("background_sync.list_remotes", return_value=["demo"])
    def test_refuses_home_directory_as_mirror(self, remotes):
        from pathlib import Path
        with self.assertRaises(ValueError):
            run_once(config={"auto_sync_enabled": True, "account": "demo",
                             "folder": str(Path.home())})
        remotes.assert_not_called()

    @patch("background_sync.inventories")
    @patch("background_sync.transfer_one", side_effect=RuntimeError(
        "API do Google Drive bloqueou consultas (403)"))
    @patch("background_sync.list_remotes", return_value=["qa_cloud"])
    def test_transfer_error_not_hidden_by_failed_rescan(self, remotes, transfer, inventory):
        with tempfile.TemporaryDirectory() as root:
            local = Path(root) / "local"
            local.mkdir()
            (local / "file.txt").write_text("contents", encoding="utf-8")
            inventory.side_effect = [
                ({"file.txt": MD5_A}, {}),
                RuntimeError("secondary inventory timeout"),
            ]
            with self.assertRaisesRegex(RuntimeError, "403"):
                run_once(
                    config={"auto_sync_enabled": True, "account": "qa_cloud",
                            "folder": str(local)},
                    state_base=Path(root) / "state",
                    backup_base=Path(root) / "backups")
            transfer.assert_called_once()

    @patch("background_sync.inventories")
    @patch("background_sync.transfer_one")
    @patch("background_sync.list_remotes", return_value=["qa_cloud"])
    def test_rescan_failure_still_fails_when_transfer_succeeds(self, remotes, transfer, inventory):
        with tempfile.TemporaryDirectory() as root:
            local = Path(root) / "local"
            local.mkdir()
            inventory.side_effect = [
                ({"file.txt": MD5_A}, {}),
                RuntimeError("remote unavailable"),
            ]
            with self.assertRaisesRegex(RuntimeError, "remote unavailable"):
                run_once(
                    config={"auto_sync_enabled": True, "account": "qa_cloud",
                            "folder": str(local)},
                    state_base=Path(root) / "state",
                    backup_base=Path(root) / "backups")
            transfer.assert_called_once()

    @patch("background_sync.subprocess.run")
    def test_upload_does_not_send_file_edited_after_inventory(self, runner):
        with tempfile.TemporaryDirectory() as root:
            folder = Path(root)
            (folder / "report.docx").write_bytes(b"New LibreOffice edit")
            with self.assertRaisesRegex(RuntimeError, "mudou durante"):
                transfer_one("demo", folder, "upload_update", "report.docx",
                             "revision", backup_base=folder / "archive",
                             expected_local_md5=MD5_A[1])
            runner.assert_not_called()

    @patch("background_sync.subprocess.run")
    def test_download_does_not_overwrite_changed_local_destination(self, runner):
        with tempfile.TemporaryDirectory() as root:
            folder = Path(root)
            (folder / "report.docx").write_bytes(b"Local changes still pending")
            with self.assertRaisesRegex(RuntimeError, "mudou durante"):
                transfer_one("demo", folder, "download_update", "report.docx",
                             "revision", backup_base=folder / "archive",
                             expected_local_md5=MD5_A[1])
            runner.assert_not_called()

    @patch("background_sync.subprocess.run")
    def test_new_download_checks_destination_before_copy(self, runner):
        with tempfile.TemporaryDirectory() as root:
            folder = Path(root)
            (folder / "new.txt").write_text("user created during scan")
            with self.assertRaisesRegex(ValueError, "Destino local já existe"):
                transfer_one("demo", folder, "download_new", "new.txt",
                             "revision", backup_base=folder / "archive")
            runner.assert_not_called()

    def test_disabled_job_does_no_io(self):
        with patch("background_sync.list_remotes") as remotes:
            self.assertEqual(run_once(config={"auto_sync_enabled": False})["state"],
                             "disabled")
            remotes.assert_not_called()

class DurableCheckpointTests(unittest.TestCase):
    """Borrowed from the resilient cloud queue concept, not the clinical app."""

    def test_checkpoint_is_private_and_refuses_symlinks_or_corruption(self):
        from background_sync import read_transfer_checkpoint
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "state" / "job-inflight.json"
            expected = {"version": 1, "planned": 2,
                        "completed": [{"operation": "upload_new", "path": "safe.txt"}]}
            save_private_json(path, expected)
            self.assertEqual(read_transfer_checkpoint(path), expected)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            path.unlink()
            path.symlink_to("/etc/passwd")
            with self.assertRaisesRegex(ValueError, "inseguro"):
                read_transfer_checkpoint(path)
            path.unlink()
            path.write_text('{"version":1,"planned":2,"completed":[{"operation":"upload_new","path":null}]}')
            with self.assertRaisesRegex(ValueError, "caminho inválido"):
                read_transfer_checkpoint(path)

    @patch("background_sync.subprocess.run")
    def test_new_upload_preserves_existing_cloud_file(self, runner):
        with tempfile.TemporaryDirectory() as root:
            folder = Path(root)
            (folder / "created.txt").write_text("local data")
            runner.return_value.returncode = 0
            runner.return_value.stderr = ""
            transfer_one("demo", folder, "upload_new", "created.txt", "run",
                         backup_base=folder / "history")
            command = runner.call_args.args[0]
            self.assertIn("--ignore-existing", command)
            self.assertNotIn("--immutable", command)
            self.assertNotIn("--backup-dir", command)

    @patch("background_sync.list_remotes", return_value=["qa_cloud"])
    @patch("background_sync.transfer_one")
    @patch("background_sync.inventories")
    def test_interrupted_batch_is_checkpointed_then_safely_replanned(
            self, inventory, transfer, remotes):
        from background_sync import job_key
        with tempfile.TemporaryDirectory() as root:
            local = Path(root) / "local"
            local.mkdir()
            state = Path(root) / "state"
            backups = Path(root) / "backups"
            local_set = {"a.txt": MD5_A, "b.txt": MD5_B}
            inventory.side_effect = [
                (local_set, {}),  # plan both uploads
                RuntimeError("cloud disconnected during verification"),
                (local_set, {"a.txt": MD5_A}),  # on restart recheck
                (local_set, local_set),  # final verification
            ]
            transfer.side_effect = [
                None, RuntimeError("network failed after one copy"), None
            ]
            config = {"auto_sync_enabled": True, "account": "qa_cloud",
                      "folder": str(local)}
            with self.assertRaisesRegex(RuntimeError, "network failed"):
                run_once(config=config, state_base=state, backup_base=backups)
            checkpoint = state / (job_key("qa_cloud", local) + "-inflight.json")
            self.assertTrue(checkpoint.is_file())
            self.assertEqual(checkpoint.stat().st_mode & 0o777, 0o600)
            self.assertEqual(read_json(checkpoint)["planned"], 2)
            self.assertEqual(read_json(checkpoint)["completed"],
                             [{"operation": "upload_new", "path": "a.txt"}])
            result = run_once(config=config, state_base=state, backup_base=backups)
            self.assertEqual(result["copied"], 1)
            self.assertEqual(result["pending"], 0)
            self.assertFalse(checkpoint.exists())
            self.assertEqual([call.args[3] for call in transfer.call_args_list],
                             ["a.txt", "b.txt", "b.txt"])

    @patch("background_sync.run_once", side_effect=RuntimeError("Drive offline"))
    def test_error_status_shows_unverified_transfers_without_trusting_them(
            self, run):
        from background_sync import job_key, run_profiles
        with tempfile.TemporaryDirectory() as root:
            local = Path(root) / "local"
            local.mkdir()
            state = Path(root) / "state"
            checkpoint = state / (job_key("qa_cloud", local) + "-inflight.json")
            save_private_json(checkpoint, {
                "version": 1, "planned": 4,
                "completed": [{"operation": "upload_new", "path": "a.txt"}],
            })
            result = run_profiles(
                config={"auto_sync_enabled": True, "account": "qa_cloud",
                        "folder": str(local)},
                state_base=state, backup_base=Path(root) / "backups")
            self.assertEqual(result["state"], "error")
            self.assertEqual(result["pending"], 3)
            self.assertEqual(result["profiles"][0]["unverified_transfers"], 1)
            self.assertEqual(result["profiles"][0]["copied"], 0)

@unittest.skipUnless(shutil.which("rclone"), "requires local rclone")
class RcloneMirrorIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.folder = root / "local"
        self.cloud = root / "cloud"
        self.state = root / "state"
        self.backups = root / "backups"
        self.folder.mkdir()
        self.cloud.mkdir()
        config_path = root / "rclone.conf"
        config_path.write_text(
            "[qa_cloud]\ntype = alias\nremote = " + str(self.cloud) + "\n",
            encoding="utf-8")
        self.env = patch.dict(os.environ, {"RCLONE_CONFIG": str(config_path)})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.config = {"auto_sync_enabled": True, "account": "qa_cloud",
                       "folder": str(self.folder)}

    def run_sync(self):
        return run_once(config=self.config, state_base=self.state,
                        backup_base=self.backups)

    def test_background_cli_without_gtk_window(self):
        """Simulate the systemd oneshot with the desktop application closed."""
        root = Path(self.temp.name)
        home = root / "isolated-home"
        configdir = home / ".config" / "gdrive-linux"
        configdir.mkdir(parents=True)
        (configdir / "settings.json").write_text(
            json.dumps(self.config), encoding="utf-8")
        (self.folder / "created-while-closed.txt").write_text(
            "offline creation", encoding="utf-8")
        env = os.environ.copy()
        env["HOME"] = str(home)
        process = subprocess.run(
            [sys.executable, str(Path(__file__).with_name("background_sync.py")), "--once"],
            env=env, capture_output=True, text=True, timeout=50)
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual((self.cloud / "created-while-closed.txt").read_text(),
                         "offline creation")

    def test_new_upload_race_preserves_destination_and_reports_conflict(self):
        """Old rclone skips a raced cloud path; the verified rescan flags conflict."""
        from background_sync import inventories
        from unittest.mock import patch
        (self.folder / "shared.txt").write_text(
            "local unsent version", encoding="utf-8")
        (self.cloud / "shared.txt").write_text(
            "remote created concurrently", encoding="utf-8")
        actual_local, actual_cloud = inventories("qa_cloud", self.folder)
        # Simulate a Drive file created AFTER the first inventory.
        with patch("background_sync.inventories", side_effect=[
                (actual_local, {}), (actual_local, actual_cloud)]):
            result = self.run_sync()
        self.assertEqual(result["state"], "conflicts")
        self.assertEqual(result["copied"], 0)
        self.assertEqual(result["conflicts"], 1)
        self.assertEqual((self.cloud / "shared.txt").read_text(encoding="utf-8"),
                         "remote created concurrently")
        self.assertEqual((self.folder / "shared.txt").read_text(encoding="utf-8"),
                         "local unsent version")

    def test_selected_folder_receives_and_uploads_new_files(self):
        (self.folder / "saved-locally.txt").write_text("from computer", encoding="utf-8")
        (self.cloud / "created-remotely.txt").write_text("from cloud", encoding="utf-8")
        result = self.run_sync()
        self.assertEqual(result["state"], "ok")
        self.assertEqual(result["copied"], 2)
        self.assertEqual((self.cloud / "saved-locally.txt").read_text(), "from computer")
        self.assertEqual((self.folder / "created-remotely.txt").read_text(), "from cloud")

    def test_edits_propagate_both_ways_with_backups(self):
        (self.folder / "document.txt").write_text("initial", encoding="utf-8")
        self.run_sync()
        (self.folder / "document.txt").write_text("local edit", encoding="utf-8")
        changed = self.run_sync()
        self.assertEqual(changed["copied"], 1)
        self.assertEqual((self.cloud / "document.txt").read_text(), "local edit")
        (self.cloud / "document.txt").write_text("remote edit", encoding="utf-8")
        changed = self.run_sync()
        self.assertEqual(changed["copied"], 1)
        self.assertEqual((self.folder / "document.txt").read_text(), "remote edit")
        self.assertTrue(list(self.backups.rglob("document.txt")))
        self.assertTrue(list((self.cloud / ".gdrive-linux-history").rglob("document.txt")))

    def test_conflicting_edits_remain_untouched(self):
        (self.folder / "shared.txt").write_text("initial", encoding="utf-8")
        self.run_sync()
        (self.folder / "shared.txt").write_text("local edit", encoding="utf-8")
        (self.cloud / "shared.txt").write_text("cloud edit", encoding="utf-8")
        result = self.run_sync()
        self.assertEqual(result["state"], "conflicts")
        self.assertEqual(result["copied"], 0)
        self.assertEqual((self.folder / "shared.txt").read_text(), "local edit")
        self.assertEqual((self.cloud / "shared.txt").read_text(), "cloud edit")

    def test_opt_in_local_deletion_moves_remote_to_recovery(self):
        (self.folder / "document.txt").write_text("recover me", encoding="utf-8")
        self.run_sync()
        (self.folder / "document.txt").unlink()
        self.config["auto_archive_deletions"] = True
        result = self.run_sync()
        self.assertEqual(result["archived"], 1)
        self.assertFalse((self.cloud / "document.txt").exists())
        self.assertTrue(list((self.cloud / ".gdrive-linux-history").rglob("document.txt")))

    def test_edit_during_archival_preserves_new_local_file(self):
        from background_sync import archive_unilateral_deletions
        (self.folder / "keep.txt").write_text("new content", encoding="utf-8")
        # The inventory reports the prior version, but the file changed before
        # the archive action: it must stay visible to the user.
        result = archive_unilateral_deletions(
            "qa_cloud", self.folder, {"keep.txt": MD5_A}, {},
            {"keep.txt": MD5_A[1]}, "test-run", self.backups)
        self.assertEqual(result, [])
        self.assertEqual((self.folder / "keep.txt").read_text(), "new content")
        self.assertFalse(list(self.backups.rglob("keep.txt")))

    def test_opt_in_cloud_deletion_archives_local_copy(self):
        (self.folder / "document.txt").write_text("recover me", encoding="utf-8")
        self.run_sync()
        (self.cloud / "document.txt").unlink()
        self.config["auto_archive_deletions"] = True
        result = self.run_sync()
        self.assertEqual(result["archived"], 1)
        self.assertFalse((self.folder / "document.txt").exists())
        self.assertTrue(list(self.backups.rglob("document.txt")))

    def test_one_way_upload_reports_skipped_downloads(self):
        (self.folder / "local.txt").write_text("from laptop", encoding="utf-8")
        (self.cloud / "remote.txt").write_text("only online", encoding="utf-8")
        self.config["mode"] = "upload"
        status = self.run_sync()
        self.assertEqual(status["state"], "ok")
        self.assertEqual(status["copied"], 1)
        self.assertEqual(status["skipped_direction"], 1)
        self.assertFalse((self.folder / "remote.txt").exists())

    def test_one_way_download_reports_skipped_uploads(self):
        (self.folder / "local.txt").write_text("stay local", encoding="utf-8")
        (self.cloud / "remote.txt").write_text("from Drive", encoding="utf-8")
        self.config["mode"] = "download"
        status = self.run_sync()
        self.assertEqual(status["state"], "ok")
        self.assertEqual(status["copied"], 1)
        self.assertEqual(status["skipped_direction"], 1)
        self.assertFalse((self.cloud / "local.txt").exists())

    def test_large_queue_drains_by_batches(self):
        for i in range(7):
            (self.cloud / ("file" + str(i) + ".txt")).write_text("data", encoding="utf-8")
        first = run_once(config=self.config, state_base=self.state,
                         backup_base=self.backups, max_files=3)
        self.assertEqual(first["copied"], 3)
        self.assertEqual(first["pending"], 4)
        self.assertEqual(first["state"], "partial")
        second = run_once(config=self.config, state_base=self.state,
                          backup_base=self.backups, max_files=3)
        self.assertEqual(second["copied"], 3)
        self.assertEqual(second["pending"], 1)
        self.assertEqual(second["state"], "partial")
        final = run_once(config=self.config, state_base=self.state,
                         backup_base=self.backups, max_files=3)
        self.assertEqual(final["copied"], 1)
        self.assertEqual(final["pending"], 0)
        self.assertEqual(final["state"], "ok")

    def test_deleted_cloud_file_is_not_removed_locally(self):
        (self.folder / "keep.txt").write_text("safe", encoding="utf-8")
        self.run_sync()
        (self.cloud / "keep.txt").unlink()
        result = self.run_sync()
        self.assertEqual(result["conflicts"], 1)
        self.assertTrue((self.folder / "keep.txt").exists())
        self.assertFalse((self.cloud / "keep.txt").exists())

if __name__ == "__main__":
    unittest.main()
