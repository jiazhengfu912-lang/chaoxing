# -*- coding: utf-8 -*-
"""Issue #612 的回归测试：未开放章节不再无限重试."""
import os
import sys
import threading
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import main  # noqa: E402


class DummyChaoxing:
    """仅提供 process_chapter 所需的最小接口，不发任何网络请求."""

    def __init__(self, job_info):
        """初始化测试替身，保存固定的任务点数据."""
        self.job_info = job_info
        self.rate_limiter = _NoopRateLimiter()
        self.get_job_list_calls = 0
        self.include_completed_videos = None

    def get_job_list(self, course, point, include_completed_videos=False):
        self.get_job_list_calls += 1
        self.include_completed_videos = include_completed_videos
        return self.job_info["jobs"], self.job_info["job_info"]


class _NoopRateLimiter:
    def limit_rate(self, *args, **kwargs):
        return None


class JobProcessorTestCase(unittest.TestCase):
    def setUp(self):
        main.logger.remove()  # 关闭所有 handler，避免测试日志刷屏

    def _make_processor(self, job_info, notopen_action="retry", max_tries=3):
        course = {"title": "课程"}
        point = {"title": "章节", "has_finished": False}
        task = main.ChapterTask(index=0, point=point, course=course)
        config = {
            "speed": 1.0,
            "jobs": 1,
            "notopen_action": notopen_action,
            "retry_interval": 0.01,
        }
        processor = main.JobProcessor(DummyChaoxing(job_info), [task], config)
        processor.max_tries = max_tries
        return processor, task

    def _run_with_timeout(self, processor, timeout=5.0):
        """在独立线程中运行 run()，超时抛出异常，避免旧代码无限重试导致测试永久卡死."""
        exception = {}

        def target():
            try:
                processor.run()
            except BaseException as exc:  # noqa: BLE001 - 子线程异常需在主线程重新抛出
                exception["exc"] = exc

        thread = threading.Thread(target=target)
        thread.daemon = True
        thread.start()
        thread.join(timeout)
        if thread.is_alive():
            self.fail(
                f"JobProcessor.run() 超过 {timeout}s 未返回，疑似无限重试（Issue #612）"
            )
        if exception:
            raise exception["exc"]

    def _not_open_job_info(self):
        return {"jobs": [], "job_info": {"notOpen": True}}

    def _error_job_info(self):
        # 未知任务类型会走 ERROR 分支，不依赖网络。
        return {"jobs": [{"type": "unknown"}], "job_info": {}}

    def test_not_open_does_not_retry_forever(self):
        processor, _ = self._make_processor(self._not_open_job_info(), max_tries=3)
        self._run_with_timeout(processor)

    def test_not_open_tries_increment(self):
        processor, task = self._make_processor(self._not_open_job_info(), max_tries=3)
        self._run_with_timeout(processor)
        self.assertEqual(task.tries, 3)

    def test_not_open_stops_after_max_tries(self):
        processor, task = self._make_processor(self._not_open_job_info(), max_tries=3)
        self._run_with_timeout(processor)
        self.assertEqual(task.tries, 3)
        self.assertTrue(processor.task_queue.empty())
        self.assertTrue(processor.retry_queue.empty())
        self.assertEqual(processor.task_queue.unfinished_tasks, 0)

    def test_not_open_queue_joins_normally(self):
        for _ in range(3):
            processor, _ = self._make_processor(self._not_open_job_info(), max_tries=3)
            self._run_with_timeout(processor)

    def test_not_open_continue_skips_without_retry(self):
        processor, task = self._make_processor(
            self._not_open_job_info(), notopen_action="continue", max_tries=3
        )
        self._run_with_timeout(processor)
        self.assertEqual(task.tries, 0)
        self.assertTrue(processor.retry_queue.empty())

    def test_error_retry_behavior_unchanged(self):
        processor, task = self._make_processor(self._error_job_info(), max_tries=3)
        self._run_with_timeout(processor)
        self.assertEqual(task.tries, 3)
        self.assertIn(task, processor.failed_tasks)

    def test_success_does_not_retry(self):
        # 目录页显示已完成的章节也要复核任务卡；无待完成任务时不应重试。
        course = {"title": "课程"}
        point = {"title": "章节", "has_finished": True}
        task = main.ChapterTask(index=0, point=point, course=course)
        config = {
            "speed": 1.0,
            "jobs": 1,
            "notopen_action": "retry",
            "retry_interval": 0.01,
        }
        chaoxing = DummyChaoxing({"jobs": [], "job_info": {}})
        processor = main.JobProcessor(chaoxing, [task], config)
        processor.max_tries = 3
        self._run_with_timeout(processor)
        self.assertEqual(task.tries, 0)
        self.assertTrue(processor.retry_queue.empty())
        self.assertEqual(chaoxing.get_job_list_calls, 1)

    def test_catalog_completed_chapter_processes_unfinished_video(self):
        course = {"title": "课程"}
        point = {"title": "PPT 和视频章节", "has_finished": True}
        video_job = {"type": "video", "jobid": "video-1"}
        chaoxing = DummyChaoxing({"jobs": [video_job], "job_info": {}})

        with patch.object(main, "process_job", return_value=main.StudyResult.SUCCESS) as process_job:
            result = main.process_chapter(chaoxing, course, point, 1.0)

        self.assertEqual(result, main.ChapterResult.SUCCESS)
        self.assertEqual(chaoxing.get_job_list_calls, 1)
        process_job.assert_called_once_with(
            chaoxing,
            course,
            video_job,
            {},
            1.0,
            replay_all_videos=False,
        )

    def test_replay_all_chapter_requests_all_videos_and_forces_playback(self):
        course = {"title": "课程"}
        point = {"title": "已完成章节", "has_finished": True}
        video_job = {"type": "video", "jobid": "video-completed"}
        chaoxing = DummyChaoxing({"jobs": [video_job], "job_info": {}})

        with patch.object(main, "process_job", return_value=main.StudyResult.SUCCESS) as process_job:
            result = main.process_chapter(
                chaoxing,
                course,
                point,
                1.0,
                replay_all_videos=True,
            )

        self.assertEqual(result, main.ChapterResult.SUCCESS)
        self.assertTrue(chaoxing.include_completed_videos)
        process_job.assert_called_once_with(
            chaoxing,
            course,
            video_job,
            {},
            1.0,
            replay_all_videos=True,
        )

    def test_chapter_processes_multiple_videos_in_order(self):
        course = {"title": "课程"}
        point = {"title": "包含两个视频的章节", "has_finished": True}
        video_jobs = [
            {"type": "video", "jobid": "video-1"},
            {"type": "video", "jobid": "video-2"},
        ]
        chaoxing = DummyChaoxing({"jobs": video_jobs, "job_info": {}})

        with patch.object(main, "process_job", return_value=main.StudyResult.SUCCESS) as process_job:
            result = main.process_chapter(chaoxing, course, point, 1.0)

        self.assertEqual(result, main.ChapterResult.SUCCESS)
        self.assertEqual(
            [call.args[2]["jobid"] for call in process_job.call_args_list],
            ["video-1", "video-2"],
        )


if __name__ == "__main__":
    unittest.main()
