"""Exercise export logic without importing bpy or starting Blender."""
import ast
from contextlib import contextmanager
import json
from pathlib import Path
from types import SimpleNamespace as NS
import tempfile
import unittest
from unittest.mock import patch
import struct
import zlib

source = Path(__file__).resolve().parents[1] / 'anim2spritesheet.py'
tree = ast.parse(source.read_text())
nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef) or
         (isinstance(node, ast.Import) and all(alias.name != 'bpy' for alias in node.names)) or
         (isinstance(node, ast.ImportFrom) and not node.module.startswith('bpy'))]
api = {}
exec(compile(ast.Module(body=nodes, type_ignores=[]), str(source), 'exec'), api)


class FoundationTests(unittest.TestCase):
    def test_png_roundtrip_and_pack_exact_pixels(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            paths = []
            for index, color in enumerate((b'\xff\x00\x00\xff', b'\x00\xff\x00\x80', b'\x00\x00\xff\x00')):
                path = root / f'{index}.png'
                api['write_png'](path, 2, 1, color * 2)
                self.assertEqual(api['read_png'](str(path)), (2, 1, color * 2))
                paths.append(str(path))
            (root / 'stale.png').write_bytes(b'invalid old frame')
            (root / '.DS_Store').write_bytes(b'unrelated')
            metadata = api['pack_spritesheet'](paths, root / 'sheet.png')
            w, h, pixels = api['read_png'](str(root / 'sheet.png'))
            self.assertEqual((w, h), (4, 2))
            self.assertEqual(metadata['columns'], 2)
            self.assertEqual(pixels[:16], b'\xff\x00\x00\xff' * 2 + b'\x00\xff\x00\x80' * 2)
            self.assertEqual(pixels[16:], b'\x00\x00\xff\x00' * 2 + bytes(8))

    def test_all_png_filters(self):
        original = [bytes(range(16)), bytes(range(16, 32))]
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'filtered.png'
            for mode in range(5):
                raw = bytearray()
                previous = bytes(16)
                for row in original:
                    raw.append(mode)
                    for x, value in enumerate(row):
                        left = row[x - 4] if x >= 4 else 0
                        up = previous[x]
                        corner = previous[x - 4] if x >= 4 else 0
                        p = left + up - corner
                        choices = (left, up, corner)
                        paeth = min(choices, key=lambda v: abs(p - v))
                        predictor = (0, left, up, (left + up) // 2, paeth)[mode]
                        raw.append((value - predictor) & 255)
                    previous = row
                def chunk(kind, payload):
                    return struct.pack('>I', len(payload)) + kind + payload + struct.pack('>I', zlib.crc32(kind + payload))
                path.write_bytes(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', 4, 2, 8, 6, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(raw)) + chunk(b'IEND', b''))
                self.assertEqual(api['read_png'](str(path))[2], b''.join(original))

    def test_inconsistent_frames_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            paths = [str(Path(folder) / f'{i}.png') for i in range(2)]
            for i, path in enumerate(paths):
                api['write_png'](path, i + 1, 1, bytes((i + 1) * 4))
            with self.assertRaisesRegex(ValueError, 'inconsistent'):
                api['pack_spritesheet'](paths, str(Path(folder) / 'sheet.png'))

    def test_engine_versions(self):
        for version, expected in [((4, 0, 2), 'BLENDER_EEVEE'), ((4, 5, 0), 'BLENDER_EEVEE_NEXT'), ((5, 2, 3), 'BLENDER_EEVEE')]:
            api['bpy'] = NS(app=NS(version=version))
            self.assertEqual(api['eevee_engine'](), expected)

    def test_state_restored_on_failure(self):
        class State:
            def __getattr__(self, name):
                setattr(self, name, 'original-' + name)
                return getattr(self, name)
        scene = State()
        scene.render = State()
        scene.render.image_settings = State()
        scene.display = State()
        scene.display.shading = State()
        scene.frame_current, scene.frame_subframe = 7, 0.25
        scene.frame_set = lambda frame, subframe: setattr(scene, 'restored_frame', (frame, subframe))
        context = NS(scene=scene, space_data=None, region_data=None)
        with self.assertRaises(RuntimeError):
            with api['preserved_render_state'](context):
                scene.render.engine = 'changed'
                scene.render.filepath = '/bad/path'
                scene.render.image_settings.color_mode = 'RGB'
                raise RuntimeError('injected failure')
        self.assertEqual(scene.render.engine, 'original-engine')
        self.assertEqual(scene.render.filepath, 'original-filepath')
        self.assertEqual(scene.render.image_settings.color_mode, 'original-color_mode')
        self.assertEqual(scene.restored_frame, (7, 0.25))

    def test_export_failure_and_success(self):
        @contextmanager
        def preserve(_):
            yield
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            old = root / 'existing-export.png'
            old.write_bytes(b'keep')
            scene = NS(render=NS(filepath=folder), keyframe_start=2, keyframe_end=6, keyframe_step=2, frame_set=lambda _: None)
            context = NS(scene=scene)
            reports = []
            operator = NS(report=lambda level, text: reports.append(text))
            def render(_, name, path):
                api['write_png'](path, 1, 1, b'\xff\x00\x00\xff')
            with patch.dict(api, {'bpy': NS(path=NS(abspath=lambda p: p)), 'validate_export': lambda *_: None, 'configure_render': lambda *_: None, 'preserved_render_state': preserve, 'render_frame': lambda *_: (_ for _ in ()).throw(RuntimeError('fail'))}):
                self.assertEqual(api['export_maps'](operator, context, ['Base']), {'CANCELLED'})
                self.assertEqual(list(root.iterdir()), [old])
                api['render_frame'] = render
                self.assertEqual(api['export_maps'](operator, context, ['Base']), {'FINISHED'})
                build = next(root.glob('export-*'))
                manifest = json.loads((build / 'manifest.json').read_text())
                self.assertEqual(manifest['samples'], [2, 4, 6])
                self.assertEqual(len(manifest['maps']['Base']['frames']), 3)
                self.assertEqual(old.read_bytes(), b'keep')
                self.assertFalse(list(root.glob('.model2pixel-*')))


if __name__ == '__main__':
    unittest.main()
