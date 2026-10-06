"""Smoke actual paired scripts and require honest validation-mode reporting."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT=Path(__file__).resolve().parents[1]

class PairedVerificationIntegrationTest(unittest.TestCase):
    def test_real_scripts_report_boundaries_and_full_audit(self):
        with tempfile.TemporaryDirectory() as temp:
            temp=Path(temp)
            archive=temp/'baseline.zip'
            with zipfile.ZipFile(archive,'w') as z:
                for name in ('embedding','association','backend'):
                    z.write(ROOT/'src'/'mnemosis'/f'{name}.py',f'src/mnemosis/{name}.py')
            commands=[('embedding', 'embedding_ingest_eval.py', ['--baseline',str(archive),'--counts','20','--rounds','3'], '--output'),
                      ('graph','ingest_pair_eval.py',['--baseline-archive',str(archive),'--count','20','--rounds','3'],'--out')]
            env=dict(os.environ, PYTHONPATH=os.pathsep.join([str(ROOT/'src'),str(ROOT/'benchmarks'),os.environ.get('PYTHONPATH','')]))
            for name,script,options,out_arg in commands:
                for mode in ('boundary','full'):
                    with self.subTest(script=script,mode=mode):
                        out=temp/f'{name}-{mode}'
                        result=subprocess.run([sys.executable,str(ROOT/'benchmarks'/script),*options,out_arg,str(out),'--verification',mode],env=env,capture_output=True,text=True)
                        self.assertEqual(result.returncode,0,result.stderr)
                        report=json.loads((out/'comparison.json').read_text(encoding='utf-8'))
                        cases=report.get('cases',[report])
                        for case in cases:
                            self.assertTrue(case['complete'])
                            self.assertEqual(case['verification']['full_runs'],6 if mode=='full' else 4)
                            self.assertEqual(case['verification']['sample_runs'],0 if mode=='full' else 2)
                            self.assertEqual(case['verification']['all_runs_exhaustive'],mode=='full')
                            self.assertTrue(case['verification']['result_order_parity'])

if __name__=='__main__': unittest.main()
