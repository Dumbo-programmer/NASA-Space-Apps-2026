"""Run the test suite with or without pytest:  python tests/run_tests.py   (or: pytest tests)"""
import importlib.util, sys, time, traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
failed = passed = 0
for f in sorted(HERE.glob("test_*.py")):
    spec = importlib.util.spec_from_file_location(f.stem, f); mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    for name in sorted(n for n in dir(mod) if n.startswith("test_")):
        t = time.time()
        try:
            getattr(mod, name)(); passed += 1; print(f"PASS  {f.stem}::{name}  ({time.time() - t:.1f}s)")
        except Exception:
            failed += 1; print(f"FAIL  {f.stem}::{name}"); traceback.print_exc()
print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
