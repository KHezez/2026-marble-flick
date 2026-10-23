import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import runtime_paths
from save_data import SaveStore

class PackagingPaths(unittest.TestCase):
    def test_frozen_save_beside_exe_not_temporary_bundle(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ,{},clear=True), patch.object(runtime_paths.sys,'frozen',True,create=True), patch.object(runtime_paths.sys,'executable',str(Path(directory)/'MarbleFlick.exe')):
            self.assertEqual(SaveStore().path,Path(directory)/'user_data'/'profile.json')
    def test_override_remains_available(self):
        with patch.dict(os.environ,{'MARBLE_SAVE_PATH':'custom-profile.json'}):
            self.assertEqual(SaveStore().path,Path('custom-profile.json'))
            self.assertEqual(SaveStore('explicit.json').path,Path('explicit.json'))
    def test_readonly_install_falls_back_to_local_appdata(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ,{'LOCALAPPDATA':directory},clear=True), patch.object(runtime_paths.sys,'frozen',True,create=True), patch.object(runtime_paths.sys,'executable',str(Path(directory)/'app'/'MarbleFlick.exe')), patch.object(runtime_paths.tempfile,'TemporaryFile',side_effect=PermissionError):
            self.assertEqual(SaveStore().path,Path(directory)/'MarbleFlick'/'user_data'/'profile.json')

if __name__=='__main__':unittest.main()
