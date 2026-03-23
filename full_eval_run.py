"""Master script: Reset KB, run evaluation, and report results."""
import subprocess
import sys
import os
import time

os.chdir('c:/Users/anupa/Documents/Project/LabelLens')

print("=" * 60)
print("STEP 1: Reset and Reseed Knowledge Base")
print("=" * 60)

try:
    result = subprocess.run([sys.executable, 'reset_kb.py'], capture_output=True, text=True, timeout=60)
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    if result.returncode != 0:
        print(f"[ERROR] Reset failed with code {result.returncode}")
        sys.exit(1)
except Exception as e:
    print(f"[ERROR] Error resetting KB: {e}")
    sys.exit(1)

print("\n" + "=" * 60)
print("STEP 2: Run RAGAS Evaluation with GPT-3.5-Turbo (10 min)")
print("=" * 60)

try:
    result = subprocess.run(
        [sys.executable, 'evals/run_evaluation.py', '--eval-llm', 'gpt-3.5-turbo'],
        capture_output=True,
        text=True,
        timeout=600
    )
    
    # Check output
    if "Evaluation completed" in result.stdout or "report" in result.stdout.lower():
        print("[OK] Evaluation completed successfully!")
    elif "ERROR" in result.stderr or result.returncode != 0:
        print(f"[ERROR] Evaluation failed")
        print("STDOUT:", result.stdout[-500:] if len(result.stdout) > 500 else result.stdout)
        print("STDERR:", result.stderr[-500:] if len(result.stderr) > 500 else result.stderr)
    else:
        print("[OK] Evaluation ran (check eval_results/ for report)")
    
    # List latest report
    import glob
    reports = sorted(glob.glob('eval_results/eval_report_*.md'), reverse=True)
    if reports:
        latest = os.path.basename(reports[0])
        file_size = os.path.getsize(reports[0])
        print(f"\nLatest report: {latest} ({file_size} bytes)")
        
except subprocess.TimeoutExpired:
    print("[ERROR] Evaluation timed out after 10 minutes")
except Exception as e:
    print(f"[ERROR] Error running evaluation: {e}")

print("\n" + "=" * 60)
print("COMPLETE")
print("=" * 60)
