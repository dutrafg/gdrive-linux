"""Multi-account, direction, external drive and safe filtering tests."""
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from sync_profiles import effective_profiles, validate_profiles, normalize_profile, ensure_external_volume_present
from sync_filters import filtered_inventory, parse_entry
from background_sync import run_profiles, run_once, read_json, job_key

class ProfileTests(unittest.TestCase):
    def test_distinct_accounts_and_external_folders(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            jobs = validate_profiles([
                {"account":"personal", "folder":str(home/"p"), "mode":"bidirectional"},
                {"account":"work", "folder":str(home/"external"/"w"), "mode":"download"}])
            self.assertEqual(len(jobs), 2)
            self.assertEqual(jobs[1]["mode"], "download")

    def test_reject_nested_and_duplicate_folders(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                validate_profiles([
                    {"account":"a","folder":str(Path(tmp)/"drive")},
                    {"account":"b","folder":str(Path(tmp)/"drive"/"nested")}])

    def test_reject_same_remote_with_two_active_profiles(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                validate_profiles([
                    {"account":"same","folder":str(Path(tmp)/"one")},
                    {"account":"same","folder":str(Path(tmp)/"two")}])

    def test_single_account_legacy_migrates(self):
        jobs = effective_profiles({"auto_sync_enabled":True, "account":"demo",
                                   "folder":"/tmp/only-drive"})
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]["mode"], "bidirectional")

    def test_profiles_opt_out(self):
        self.assertEqual(effective_profiles({
            "auto_sync_enabled": True,"sync_profiles": [],
            "profiles_configured": True}), [])

    def test_missing_external_media_volume_is_refused(self):
        with patch("sync_profiles.Path.is_mount", return_value=False):
            with self.assertRaisesRegex(ValueError, "não está montado"):
                ensure_external_volume_present("/media/testuser/UNPLUGGED/folder")

    def test_rejects_home_as_sync_root(self):
        with self.assertRaisesRegex(ValueError, "pasta pessoal"):
            normalize_profile({"account": "personal", "folder": str(Path.home())})

    def test_rejects_symlink_profile_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            dest = base / "destination"
            dest.mkdir()
            alias = base / "alias"
            alias.symlink_to(dest, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "simbólica"):
                normalize_profile({"account": "personal", "folder": str(alias)})

    def test_rejects_virtual_drive_inside_mirror(self):
        with self.assertRaisesRegex(ValueError, "montagem FUSE"):
            normalize_profile({"account":"drive",
                               "folder":str(Path.home()/"DriveOnline"/"drive")})

    def test_selective_ignore_patterns(self):
        inventory={"Documentos/cv.odt":1, "Documentos/file.tmp":2,
                   "Fotos/photo.jpg":3, "Cache/a.bin":4}
        wanted=filtered_inventory(inventory, ["Documentos/"], ["*.tmp"])
        self.assertEqual(wanted, {"Documentos/cv.odt":1})

    def test_no_unsafe_filter_patterns(self):
        for value in ("../private", "a\\x00b", "/root", "!important"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_entry(value)

@unittest.skipUnless(shutil.which("rclone"), "requires rclone installed")
class MultiAccountRcloneIntegration(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root=Path(self.temp.name)
        self.state=root/"state"
        self.backup=root/"backups"
        self.personal=root/"personal"
        self.work=root/"mounted-data-disk"/"work"
        self.remote_personal=root/"remote-personal"
        self.remote_work=root/"remote-work"
        for folder in (self.personal,self.work,self.remote_personal,self.remote_work):
            folder.mkdir(parents=True)
        config_path=root/"rclone.conf"
        config_path.write_text("[personal]\ntype = alias\nremote = "+str(self.remote_personal)+
                               "\n[work]\ntype = alias\nremote = "+str(self.remote_work)+"\n")
        p=patch.dict(os.environ,{"RCLONE_CONFIG":str(config_path)})
        p.start();self.addCleanup(p.stop)
        self.config={"auto_sync_enabled":True,"sync_profiles":[
            {"account":"personal", "folder":str(self.personal), "mode":"upload",
             "sync_includes":["Documentos/"],"sync_excludes":["*.tmp"]},
            {"account":"work", "folder":str(self.work), "mode":"download"}],
            "profiles_configured":True}
        (self.personal/"Documentos").mkdir()
        (self.personal/"Documentos"/"cv.odt").write_text("hello")
        (self.personal/"Documentos"/"unfinished.tmp").write_text("partial")
        (self.personal/"photos.jpg").write_text("ignore")
        (self.remote_personal/"cloud-exclusive.txt").write_text("do not download")
        (self.remote_work/"work.txt").write_text("from cloud")
        (self.work/"local-only.txt").write_text("do not upload")

    def test_two_accounts_preserve_direction_filters_and_folder(self):
        result=run_profiles(self.config, state_base=self.state,
                            backup_base=self.backup)
        self.assertEqual(result["state"],"ok",result)
        self.assertEqual(result["copied"],2)
        self.assertEqual((self.remote_personal/"Documentos"/"cv.odt").read_text(),"hello")
        self.assertFalse((self.remote_personal/"Documentos"/"unfinished.tmp").exists())
        self.assertFalse((self.remote_personal/"photos.jpg").exists())
        self.assertFalse((self.personal/"cloud-exclusive.txt").exists())
        self.assertEqual((self.work/"work.txt").read_text(),"from cloud")
        self.assertFalse((self.remote_work/"local-only.txt").exists())
        self.assertEqual(len(result["profiles"]),2)

    def test_excluded_old_file_is_not_archived_after_filter_change(self):
        p=self.config["sync_profiles"][0]
        p["mode"]="bidirectional"
        p["sync_includes"]=[]
        run_profiles(self.config, state_base=self.state,backup_base=self.backup)
        (self.personal/"Documentos"/"cv.odt").unlink()
        p["sync_includes"]=["Fotos/"]
        p["auto_archive_deletions"]=True
        run_profiles(self.config,state_base=self.state,backup_base=self.backup)
        self.assertTrue((self.remote_personal/"Documentos"/"cv.odt").exists())

if __name__=="__main__":
    unittest.main()
