"""
JP_Run_Calibrate_Offline.py — wrapper to run offline calibration with file output.
Run from project root: python Scripts/JP_Run_Calibrate_Offline.py
Output: Scripts/_calibration_offline.txt
"""
import sys, os, io

sys.path.insert(0, os.path.join(os.getcwd(), "Scripts"))

buf = io.StringIO()
old_stdout = sys.stdout
sys.stdout = buf

try:
    from JP_Calibrate_Offline import main
    main()
except Exception as e:
    sys.stdout = old_stdout
    print("ERROR:", e)
    sys.stdout = buf
    import traceback
    traceback.print_exc()

sys.stdout = old_stdout
out_path = os.path.join("Scripts", "_calibration_offline.txt")
with open(out_path, "w", encoding="utf-8") as f:
    f.write(buf.getvalue())
print("Output written to %s (%d bytes)" % (out_path, len(buf.getvalue())))
