import hashlib,tempfile,unittest
from pathlib import Path
from verify_backup_manifest import EXPECTED,verify

class ManifestTest(unittest.TestCase):
    def test_valid_missing_duplicate_traversal_and_corruption(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            root=Path(directory);lines=[]
            for name in sorted(EXPECTED):
                data=name.encode();(root/name).write_bytes(data)
                lines.append(hashlib.sha256(data).hexdigest()+'  '+name)
            manifest=root/'SHA256SUMS';manifest.write_text('\n'.join(lines)+'\n')
            self.assertEqual(verify(root),3)
            for invalid in (lines[:-1],lines+[lines[0]],lines+['0'*64+'  ../escape']):
                manifest.write_text('\n'.join(invalid)+'\n')
                with self.assertRaises(ValueError):verify(root)
            manifest.write_text('\n'.join(lines)+'\n');(root/'database.sql.gz').write_bytes(b'bad')
            with self.assertRaises(ValueError):verify(root)

    def test_symlink_artifact_and_manifest_rejected(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            root=Path(directory);lines=[]
            for name in sorted(EXPECTED):
                data=name.encode();(root/name).write_bytes(data)
                lines.append(hashlib.sha256(data).hexdigest()+'  '+name)
            manifest=root/'SHA256SUMS';manifest.write_text('\n'.join(lines)+'\n')
            try:
                (root/'outside').write_bytes(b'database.sql.gz')
                (root/'database.sql.gz').unlink()
                (root/'database.sql.gz').symlink_to(root/'outside')
            except OSError as error:self.skipTest('symlink unavailable: '+str(error))
            with self.assertRaises(ValueError):verify(root)
            (root/'database.sql.gz').unlink();(root/'database.sql.gz').write_bytes(b'database.sql.gz')
            manifest.rename(root/'manifest-copy');manifest.symlink_to(root/'manifest-copy')
            with self.assertRaises(ValueError):verify(root)

if __name__=='__main__':unittest.main()
