#!/usr/bin/env python3
"""TEST transport fault AFTER the actual Native owner accepted input. No host/model mock."""
import importlib.util
import json
from pathlib import Path
import sys

script = Path(__file__).resolve().parents[2] / "skills/delm/Tools/Run.py"
spec = importlib.util.spec_from_file_location("launcher_actual_response_loss", script)
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)
actual_rpc = launcher.native_rpc
lost = False


def rpc(state, actor, operation, **kwargs):
    global lost
    receipt = actual_rpc(state, actor, operation, **kwargs)
    if operation == "input" and not lost:
        assert receipt["result"]["accepted"] is True
        lost = True
        raise RuntimeError("INJECTED_LOST_ACTUAL_NATIVE_RECEIPT")
    return receipt


launcher.native_rpc = rpc
try:
    launcher.main()
except RuntimeError as error:
    if lost and str(error) == "INJECTED_LOST_ACTUAL_NATIVE_RECEIPT":
        print(json.dumps({"actualNativeAccepted": True, "callerReceiptLossInjected": True}))
        sys.exit(42)
    raise
raise AssertionError("Actual Native response loss was not injected")
