import unittest
from photo_storage_audit import audit_state, parse_df, parse_storage_sizes, quota_warning

class AuditTests(unittest.TestCase):
    def test_old_orphan_only_and_missing_reference(self):
        ref='11111111-1111-1111-1111-111111111111.jpg'
        missing='22222222-2222-2222-2222-222222222222.png'
        old='33333333-3333-3333-3333-333333333333.png'
        recent='44444444-4444-4444-4444-444444444444.jpg'
        result=audit_state({ref,missing},{ref:1,old:1,recent:99990},100000,3600)
        self.assertEqual(result['missing'],[missing])
        self.assertEqual(result['orphan_candidates'],[old])
        self.assertEqual(result['recent_unreferenced'],1)
    def test_df_parses_and_rejects_bad_output(self):
        self.assertEqual(parse_df('Filesystem 1024-blocks Used Available Capacity Mounted on\n/dev/sda 100 90 10 90% /data\n'),90)
        with self.assertRaises(ValueError):parse_df('invalid')
    def test_quota_boundaries_and_unexpected_sizes(self):
        self.assertEqual(parse_storage_sizes(b'45\x0040\x00'),85)
        self.assertFalse(quota_warning(84,100,85))
        self.assertTrue(quota_warning(85,100,85))
        with self.assertRaises(ValueError): parse_storage_sizes(b'-1\x00')
        with self.assertRaises(ValueError): quota_warning(0,0,85)

if __name__=='__main__':unittest.main()
