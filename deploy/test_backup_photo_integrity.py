import io
import tarfile
import tempfile
import unittest
from pathlib import Path
from verify_restored_photo_archive import inspect_archive

class RestorePhotoIntegrityTests(unittest.TestCase):
    def test_referenced_missing_duplicate_and_invalid_name(self):
        first='11111111-1111-1111-1111-111111111111.png'
        second='22222222-2222-2222-2222-222222222222.jpg'
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'images.tar.gz'
            with tarfile.open(path,'w:gz') as archive:
                member=tarfile.TarInfo('./'+first);member.size=1
                archive.addfile(member,io.BytesIO(b'x'))
                link=tarfile.TarInfo('./'+first);link.type=tarfile.SYMTYPE;link.linkname='other'
                archive.addfile(link)
            result=inspect_archive(path,[first,second])
            self.assertEqual(result['missing_examples'],[second])
            self.assertEqual(result['duplicate_examples'],[first])
            with self.assertRaises(ValueError):inspect_archive(path,['../not-a-photo'])

if __name__=='__main__':unittest.main()
