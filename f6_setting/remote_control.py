from importlib.machinery import SourceFileLoader
from pathlib import Path

module_path = Path(__file__).resolve().parent / '02_f6_setting' / 'remote_control.py'
_spec = SourceFileLoader('remote_control', str(module_path)).load_module()

read_status = _spec.read_status
write_status = _spec.write_status
start_bot = _spec.start_bot
