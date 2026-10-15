"""Ctrl+A must remain responsive with a full Reconcile page and its target preview."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]


class ReconcileSelectionTest(unittest.TestCase):
    def test_real_qml_ctrl_a_and_target_preview(self):
        with tempfile.TemporaryDirectory() as directory:
            environment=dict(os.environ,TEMP=directory,TMP=directory,PYTHONUTF8='1',
                             PYTHONPATH=os.pathsep.join([str(ROOT/'src'),str(ROOT/'tests')]))
            process=subprocess.Popen([sys.executable,str(ROOT/'tests/reconcile_selection_probe.py')],
                                     cwd=ROOT,env=environment,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                                     text=True,encoding='utf-8')
            try:
                stdout,stderr=process.communicate(timeout=30)
            finally:
                if process.poll() is None:
                    if os.name=='nt':
                        subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],capture_output=True,timeout=10)
                    else:
                        process.kill()
                    process.communicate(timeout=10)
        self.assertEqual(process.returncode,0,stdout+'\n'+stderr)
        self.assertIn('"preview": 1000',stdout)
