"""Unit tests for _paths - sibling skill resolution (T1, LOOP-01).

Derived from T1's "Done when" criteria. Every case builds a throwaway skill
layout under a TemporaryDirectory so nothing depends on how this repo happens
to be installed on the machine running the suite.
"""

import importlib.util
import os
import shutil
import tempfile
import unittest

REAL_PATHS_PY = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_paths.py")

_counter = 0


def _load(path):
    """Import _paths.py from an exact path, under a unique module name."""
    global _counter
    _counter += 1
    name = f"_paths_under_test_{_counter}"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _layout(base, with_sibling=True):
    """Create <base>/skills/tlc-loop/scripts/_paths.py (+ optional sibling)."""
    loop_scripts = os.path.join(base, "skills", "tlc-loop", "scripts")
    os.makedirs(loop_scripts)
    shutil.copyfile(REAL_PATHS_PY, os.path.join(loop_scripts, "_paths.py"))
    if with_sibling:
        tlc_scripts = os.path.join(base, "skills", "tlc-spec-driven", "scripts")
        os.makedirs(tlc_scripts)
        with open(os.path.join(tlc_scripts, "validate_tasks.py"), "w") as fh:
            fh.write("# stub\n")
    return os.path.join(loop_scripts, "_paths.py")


class SkillDirResolution(unittest.TestCase):
    def test_resolves_from_a_real_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            mod = _load(_layout(tmp))
            expected = os.path.realpath(os.path.join(tmp, "skills", "tlc-loop"))
            self.assertEqual(mod.skill_dir(), expected)

    def test_resolves_through_a_symlinked_entry(self):
        with tempfile.TemporaryDirectory() as tmp:
            _layout(tmp)
            link = os.path.join(tmp, "linked-tlc-loop")
            os.symlink(os.path.join(tmp, "skills", "tlc-loop"), link)
            mod = _load(os.path.join(link, "scripts", "_paths.py"))
            expected = os.path.realpath(os.path.join(tmp, "skills", "tlc-loop"))
            self.assertEqual(mod.skill_dir(), expected)


class TlcDirResolution(unittest.TestCase):
    def test_returns_the_sibling_tlc_spec_driven_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            mod = _load(_layout(tmp))
            expected = os.path.realpath(os.path.join(tmp, "skills", "tlc-spec-driven"))
            self.assertEqual(mod.tlc_dir(), expected)

    def test_sibling_found_through_a_symlinked_entry(self):
        with tempfile.TemporaryDirectory() as tmp:
            _layout(tmp)
            link = os.path.join(tmp, "linked-tlc-loop")
            os.symlink(os.path.join(tmp, "skills", "tlc-loop"), link)
            mod = _load(os.path.join(link, "scripts", "_paths.py"))
            expected = os.path.realpath(os.path.join(tmp, "skills", "tlc-spec-driven"))
            self.assertEqual(mod.tlc_dir(), expected)


class TlcScript(unittest.TestCase):
    def test_returns_path_to_a_named_script_under_tlc_scripts(self):
        with tempfile.TemporaryDirectory() as tmp:
            mod = _load(_layout(tmp))
            expected = os.path.realpath(
                os.path.join(tmp, "skills", "tlc-spec-driven", "scripts", "validate_tasks.py")
            )
            self.assertEqual(mod.tlc_script("validate_tasks.py"), expected)


class MissingSibling(unittest.TestCase):
    def test_tlc_dir_raises_with_the_attempted_absolute_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            mod = _load(_layout(tmp, with_sibling=False))
            attempted = os.path.realpath(os.path.join(tmp, "skills", "tlc-spec-driven"))
            with self.assertRaises(mod.SiblingSkillError) as ctx:
                mod.tlc_dir()
            self.assertIn(attempted, str(ctx.exception))
            self.assertTrue(os.path.isabs(attempted))

    def test_tlc_dir_error_is_not_a_bare_filenotfounderror(self):
        with tempfile.TemporaryDirectory() as tmp:
            mod = _load(_layout(tmp, with_sibling=False))
            with self.assertRaises(mod.SiblingSkillError) as ctx:
                mod.tlc_dir()
            self.assertNotIsInstance(ctx.exception, FileNotFoundError)

    def test_tlc_script_raises_with_the_attempted_absolute_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            mod = _load(_layout(tmp))
            attempted = os.path.realpath(
                os.path.join(tmp, "skills", "tlc-spec-driven", "scripts", "nope.py")
            )
            with self.assertRaises(mod.SiblingSkillError) as ctx:
                mod.tlc_script("nope.py")
            self.assertIn(attempted, str(ctx.exception))
            self.assertNotIsInstance(ctx.exception, FileNotFoundError)


if __name__ == "__main__":
    unittest.main()
