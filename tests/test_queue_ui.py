import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
from clip_queue import QueueStore
from project_store import write

SETTINGS=dict(mode='Interview',minimum=20,maximum=65,windows=6,vision=False,semantic=True,
              quality='Higher quality',shorts_editor=True,portrait=True)


class QueueUITests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.store=QueueStore(self.root);self.projects=[]
        for i in range(2):
            folder=self.root/'data'/str(i);folder.mkdir();source=folder/'source.mp4';source.write_bytes(b'placeholder')
            project=dict(folder=str(folder),source=str(source),title=f'Video {i}',duration=40)
            write(folder/'project.json',project);write(folder/'ui-settings.json',SETTINGS);self.projects.append(project)
        self.launcher=patch('queue_ui.ensure_runner');self.launch=self.launcher.start()
        self.app=AppTest.from_string(f"from pathlib import Path\nimport streamlit as st\nfrom queue_ui import show\ndef go(page):\n st.session_state.page=page\nshow(Path({str(self.root)!r}),go)",default_timeout=10)

    def tearDown(self):self.launcher.stop();self.tmp.cleanup()

    def test_add_many_reorder_remove_and_start_persist(self):
        app=self.app.run();self.assertFalse(app.exception)
        next(m for m in app.multiselect if m.label=='Videos to add').set_value([p['folder'] for p in self.projects])
        next(b for b in app.button if b.label=='Add videos to queue').click().run()
        self.assertFalse(app.exception)
        a,b=self.store.items();self.assertTrue(a['export_clips'])
        next(button for button in app.button if button.key=='queue-down-'+a['id']).click().run()
        self.assertEqual(self.store.items()[0]['id'],b['id'])
        next(button for button in app.button if button.key=='queue-remove-'+b['id']).click().run()
        self.assertTrue(Path(b['project']['source']).is_file())
        next(button for button in app.button if button.label=='Start queue').click().run()
        self.assertTrue(self.store.enabled());self.launch.assert_called()

    def test_pause_current_and_open_completed_results_with_saved_settings(self):
        item,_=self.store.add(self.projects[0],SETTINGS);self.store.set_enabled(True);self.store.claim()
        result=Path(item['project']['folder'])/'clips-test.json';write(result,[])
        self.store.update(item['id'],result=str(result),progress=.3,label='Reviewing 2 of 4')
        app=self.app.run();self.assertFalse(app.exception)
        next(b for b in app.button if b.label=='Pause after this video').click().run()
        self.assertFalse(self.store.enabled());self.assertEqual(self.store.get(item['id'])['state'],'running')
        self.store.finish(item['id']);app.run()
        next(b for b in app.button if b.label=='Open clips').click().run()
        self.assertEqual(app.session_state['page'],'results')
        self.assertEqual(app.session_state['settings'],SETTINGS)
        self.assertEqual(app.session_state['result_path'],str(result))

    def test_sidebar_queue_opens_without_an_active_project(self):
        app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=15)
        app.session_state['page']='source'
        with patch('queue_ui.show') as show:
            app.run();self.assertFalse(app.exception)
            next(b for b in app.button if b.label=='Video queue').click().run()
            self.assertEqual(app.session_state['page'],'queue');show.assert_called_once()

    def test_closed_lid_requires_charger_and_passes_opt_in_to_runner(self):
        self.store.add(self.projects[0],SETTINGS)
        with patch('queue_power.capability',return_value=(False,'Connect your charger.')):
            app=self.app.run()
            next(c for c in app.checkbox if c.key=='queue-closed-lid').check().run()
            self.assertTrue(next(b for b in app.button if b.label=='Start queue').disabled)
            self.assertFalse(self.store.enabled())
        with patch('queue_power.capability',return_value=(True,'Ready.')):
            app.run()
            next(b for b in app.button if b.label=='Start queue').click().run()
            self.launch.assert_any_call(self.root,closed_lid=True)
            self.assertTrue(self.store.enabled())


if __name__=='__main__':unittest.main()
