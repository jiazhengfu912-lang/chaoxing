# -*- coding: utf-8 -*-
"""无网络测试：运行方式选择、速度传递和章节并发数。"""
import os
import sys
import threading
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import main  # noqa: E402


class RuntimeOptionsTestCase(unittest.TestCase):
    def setUp(self):
        main.logger.remove()

    def test_single_task_with_original_speed(self):
        config = {"jobs": 4, "speed": 2.0}
        with patch("builtins.input", side_effect=["1", "n", "1"]):
            main.prompt_runtime_options(config)

        self.assertEqual(config["jobs"], 1)
        self.assertEqual(config["speed"], 1.0)
        self.assertEqual(config["video_mode"], "normal")

    def test_multi_task_with_custom_speed(self):
        config = {"jobs": 1, "speed": 1.0}
        with patch("builtins.input", side_effect=["2", "6", "y", "1.5", "2"]):
            main.prompt_runtime_options(config)

        self.assertEqual(config["jobs"], 6)
        self.assertEqual(config["speed"], 1.5)
        self.assertEqual(config["video_mode"], "replay_all")

    def test_multi_task_uses_default_job_count_on_blank_input(self):
        config = {"jobs": 1, "speed": 1.0}
        with patch("builtins.input", side_effect=["2", "", "n", "1"]):
            main.prompt_runtime_options(config)

        self.assertEqual(config["jobs"], 4)
        self.assertEqual(config["speed"], 1.0)

    def test_invalid_runtime_options_are_prompted_again(self):
        config = {"jobs": 1, "speed": 1.0}
        inputs = ["invalid", "2", "1", "abc", "3", "maybe", "y", "2.5", "1.75", "x", "2"]
        with patch("builtins.input", side_effect=inputs), patch("builtins.print"):
            main.prompt_runtime_options(config)

        self.assertEqual(config["jobs"], 3)
        self.assertEqual(config["speed"], 1.75)
        self.assertEqual(config["video_mode"], "replay_all")

    def test_only_argument_free_launch_prompts_runtime_options(self):
        with patch.object(main.sys, "argv", ["main.py"]):
            self.assertTrue(main.should_prompt_runtime_options())
        with patch.object(main.sys, "argv", ["main.py", "-c", "config.ini"]):
            self.assertFalse(main.should_prompt_runtime_options())
        with patch.object(main.sys, "argv", ["main.py", "-u", "user", "-p", "password"]):
            self.assertFalse(main.should_prompt_runtime_options())

    def test_validate_jobs_rejects_non_positive_values(self):
        self.assertEqual(main.validate_jobs(1), 1)
        self.assertEqual(main.validate_jobs("4"), 4)
        for value in (0, -1, True, "invalid"):
            with self.subTest(value=value):
                with self.assertRaises(main.InputFormatError):
                    main.validate_jobs(value)

    def test_validate_video_mode(self):
        self.assertEqual(main.validate_video_mode(None), "normal")
        self.assertEqual(main.validate_video_mode(" REPLAY_ALL "), "replay_all")
        with self.assertRaises(main.InputFormatError):
            main.validate_video_mode("invalid")

    def test_command_line_accepts_replay_all_mode(self):
        with patch.object(main.sys, "argv", ["main.py", "--video-mode", "replay_all"]):
            args = main.parse_args()

        self.assertEqual(args.video_mode, "replay_all")


class MainRuntimeOptionsIntegrationTestCase(unittest.TestCase):
    def setUp(self):
        main.logger.remove()

    def _run_main(self, argv):
        events = []
        common_config = {
            "speed": 1.0,
            "jobs": 1,
            "notopen_action": "retry",
            "add_learning_count": False,
            "target_count": 100,
            "course_list": ["course-id"],
            "use_cookies": False,
        }

        class DummyChaoxing:
            @staticmethod
            def login(**kwargs):
                events.append("login")
                return {"status": True, "msg": "登录成功"}

            @staticmethod
            def get_course_list():
                events.append("course_list")
                return []

        class DummyNotification:
            def config_set(self, config):
                return None

            def get_notification_from_config(self):
                return self

            def init_notification(self):
                return None

            def send(self, message):
                return None

        class DummyJobProcessor:
            def __init__(self, *args):
                events.append("processor_created")

            def run(self):
                events.append("processor_run")

        def record_prompt(config):
            events.append("prompt")

        with patch.object(main.sys, "argv", argv), patch.object(
            main, "init_config", return_value=(common_config, {}, {}, None)
        ), patch.object(main, "init_chaoxing", return_value=DummyChaoxing()), patch.object(
            main, "Notification", DummyNotification
        ), patch.object(main, "JobProcessor", DummyJobProcessor), patch.object(
            main, "prompt_runtime_options", side_effect=record_prompt
        ) as prompt:
            main.main()

        return events, prompt

    def test_argument_free_main_prompts_after_login_before_course_lookup(self):
        events, prompt = self._run_main(["main.py"])

        prompt.assert_called_once()
        self.assertLess(events.index("login"), events.index("prompt"))
        self.assertLess(events.index("prompt"), events.index("course_list"))

    def test_config_or_command_line_main_does_not_prompt(self):
        for argv in (["main.py", "-c", "config.ini"], ["main.py", "-j", "1", "-s", "1.5"]):
            with self.subTest(argv=argv):
                _, prompt = self._run_main(argv)
                prompt.assert_not_called()


class SpeedPropagationTestCase(unittest.TestCase):
    def setUp(self):
        main.logger.remove()

    def test_video_and_audio_receive_selected_speed(self):
        class DummyChaoxing:
            def __init__(self):
                self.calls = []

            def study_video(self, course, job, job_info, _speed, _type, _force_full_playback=False):
                self.calls.append((_speed, _type, _force_full_playback, job.get("playTime")))
                return main.StudyResult.ERROR if _type == "Video" else main.StudyResult.SUCCESS

        chaoxing = DummyChaoxing()
        course = {"title": "课程"}
        job = {"type": "video", "jobid": "job-1"}

        result = main.process_job(chaoxing, course, job, {}, 1.75)

        self.assertEqual(result, main.StudyResult.SUCCESS)
        self.assertEqual(
            chaoxing.calls,
            [(1.75, "Video", False, None), (1.75, "Audio", False, None)],
        )

    def test_replay_all_video_starts_at_zero_and_forces_full_playback(self):
        class DummyChaoxing:
            def __init__(self):
                self.calls = []

            def study_video(self, course, job, job_info, _speed, _type, _force_full_playback=False):
                self.calls.append((job, _type, _force_full_playback))
                return main.StudyResult.SUCCESS

        chaoxing = DummyChaoxing()
        original_job = {
            "type": "video",
            "jobid": "job-1",
            "playTime": 90_000,
        }

        result = main.process_job(
            chaoxing,
            {"title": "课程"},
            original_job,
            {},
            1.0,
            replay_all_videos=True,
        )

        self.assertEqual(result, main.StudyResult.SUCCESS)
        replay_job, media_type, force_full_playback = chaoxing.calls[0]
        self.assertEqual(replay_job["playTime"], 0)
        self.assertEqual(media_type, "Video")
        self.assertTrue(force_full_playback)
        self.assertEqual(original_job["playTime"], 90_000)

    def test_live_receives_selected_speed(self):
        class DummyChaoxing:
            @staticmethod
            def get_uid():
                return "user-id"

        course = {"title": "课程", "clazzId": "class-id", "courseId": "course-id"}
        job = {"type": "live", "jobid": "job-1"}
        job_info = {"knowledgeid": "knowledge-id"}

        with patch.object(main, "Live") as live_class, patch.object(
            main.LiveProcessor, "run_live", return_value=True
        ) as run_live:
            result = main.process_job(DummyChaoxing(), course, job, job_info, 1.5)

        self.assertEqual(result, main.StudyResult.SUCCESS)
        live_class.assert_called_once()
        self.assertEqual(run_live.call_args.args[1], 1.5)


class JobProcessorConcurrencyTestCase(unittest.TestCase):
    def setUp(self):
        main.logger.remove()

    @staticmethod
    def _make_tasks(count):
        course = {"title": "课程"}
        return [
            main.ChapterTask(
                index=index,
                point={"title": f"章节 {index}", "has_finished": False},
                course=course,
            )
            for index in range(count)
        ]

    def test_single_task_mode_does_not_overlap_chapters(self):
        active = 0
        max_active = 0
        lock = threading.Lock()

        def process_chapter(*args):
            nonlocal active, max_active
            with lock:
                active += 1
                max_active = max(max_active, active)
            time.sleep(0.03)
            with lock:
                active -= 1
            return main.ChapterResult.SUCCESS

        processor = main.JobProcessor(None, self._make_tasks(3), {"jobs": 1, "speed": 1.0})
        with patch.object(main, "process_chapter", side_effect=process_chapter):
            processor.run()

        self.assertEqual(len(processor.threads), 1)
        self.assertEqual(max_active, 1)

    def test_multi_task_mode_uses_requested_worker_count(self):
        active = 0
        max_active = 0
        lock = threading.Lock()
        started = threading.Barrier(2)

        def process_chapter(*args):
            nonlocal active, max_active
            with lock:
                active += 1
                max_active = max(max_active, active)
            started.wait(timeout=2)
            with lock:
                active -= 1
            return main.ChapterResult.SUCCESS

        processor = main.JobProcessor(None, self._make_tasks(2), {"jobs": 2, "speed": 1.0})
        with patch.object(main, "process_chapter", side_effect=process_chapter):
            processor.run()

        self.assertEqual(len(processor.threads), 2)
        self.assertEqual(max_active, 2)


if __name__ == "__main__":
    unittest.main()
