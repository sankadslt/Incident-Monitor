from importlib import util
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent

def run_module_from_path(module_path, function_name):
	if not module_path.exists():
		return None

	module_name = module_path.stem.replace(" ", "_")
	spec = util.spec_from_file_location(module_name, module_path)
	if spec is None or spec.loader is None:
		raise RuntimeError(f"Unable to load module from {module_path}")

	module = util.module_from_spec(spec)
	spec.loader.exec_module(module)

	runner = getattr(module, function_name, None)
	if runner is None:
		raise AttributeError(f"Function '{function_name}' not found in {module_path}")

	return runner()

def run_sequence():
	run_module_from_path(
		PROJECT_ROOT / "App" / "Incident Report" / "incident_open_report.py",
		"run_incident_summary",
	)

	run_module_from_path(
		PROJECT_ROOT / "App" / "Incident Conflicts" / "arrears_mismatch_task_creator.py",
		"run_arrears_mismatch_task_creator",
	)

if __name__ == "__main__":
	run_sequence()
