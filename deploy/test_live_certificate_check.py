import datetime, pathlib, subprocess, sys, unittest
from check_live_certificate import classify

class CertificateExpiryTest(unittest.TestCase):
    def test_thresholds(self):
        now=datetime.datetime(2026,1,1,tzinfo=datetime.timezone.utc)
        self.assertEqual(classify(now+datetime.timedelta(days=4),now,3),0)
        self.assertEqual(classify(now+datetime.timedelta(days=3),now,3),1)
        self.assertEqual(classify(now,now,3),2)
        self.assertEqual(classify(now-datetime.timedelta(seconds=1),now,3),2)
    def test_invalid_threshold_rejected_before_network(self):
        for value in ('nan','inf','-1'):
            result=subprocess.run([sys.executable,str(pathlib.Path(__file__).with_name('check_live_certificate.py')),'--warning-days',value],capture_output=True,text=True)
            self.assertEqual(result.returncode,2,value)
            self.assertIn('invalid warning threshold',result.stderr)

if __name__=='__main__':unittest.main()
