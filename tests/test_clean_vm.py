import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('vm', Path(__file__).parents[1] / 'tools/prepare-clean-vm.py')
vm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vm)


class VmBoundary(unittest.TestCase):
    def test_launch_keeps_guest_off_host_devices_and_blocks_egress(self):
        args = vm.launch_arguments(Path('/selected/bin/qemu'), Path('/test/vm'), 22043, 4096, 2, 'kvm')
        self.assertIn('user,id=net0,restrict=on,hostfwd=tcp:127.0.0.1:22043-:22', args)
        self.assertIn('none', args)
        self.assertNotIn('-virtfs', args)
        self.assertNotIn('-fsdev', args)
        self.assertFalse(any('/dev/' in value for value in args))
        self.assertTrue(all('file=/test/vm/' in args[i + 1] for i, value in enumerate(args) if value == '-drive'))

    def test_invalid_ports_resources_and_accelerators_are_rejected(self):
        for port, memory, cpus, mode in [(22, 4096, 2, 'kvm'), (22043, 100000, 2, 'kvm'),
                                        (22043, 4096, 40, 'kvm'), (22043, 4096, 2, 'bogus')]:
            with self.subTest(port=port, memory=memory, cpus=cpus, mode=mode), self.assertRaises(ValueError):
                vm.launch_arguments(Path('/selected/qemu'), Path('/test/vm'), port, memory, cpus, mode)

    def test_changed_base_image_is_rejected_before_tool_execution(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'image'
            path.write_bytes(b'original')
            selected = vm.sha(path)
            path.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'changed selected input'):
                vm.check(path, selected)


if __name__ == '__main__':
    unittest.main()
