# -*- coding: utf-8 -*-
"""回归测试：非任务视频播放到结尾后必须退出并处理下一个任务。"""
import json
import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.base import Chaoxing, SessionManager, StudyResult  # noqa: E402


class _Response:
    def __init__(self, data):
        self.status_code = 200
        self._data = data
        self.text = json.dumps(data)
        self.url = "https://example.invalid/progress"

    def json(self):
        return self._data


class _Session:
    def __init__(self, has_job_limit=False, max_progress_requests=2):
        self.headers = {}
        self.cookies = {}
        self.progress_params = []
        self.has_job_limit = has_job_limit
        self.max_progress_requests = max_progress_requests

    def get(self, url, params=None, headers=None):
        if "/ananas/status/" in url:
            return _Response(
                {
                    "status": "success",
                    "dtoken": "dtoken",
                    "crc": "crc",
                    "key": "key",
                    "duration": 10,
                }
            )

        self.progress_params.append(dict(params or {}))
        if len(self.progress_params) > self.max_progress_requests:
            raise AssertionError("视频到达 100% 后仍在重复上报")
        return _Response(
            {
                "isPassed": False,
                "videoTimeLimit": False,
                "hasJobLimit": self.has_job_limit,
            }
        )


class _ProgressBar:
    def __init__(self):
        self.n = 0
        self.leave = False

    def refresh(self):
        return None

    def close(self):
        return None


class VideoCompletionTestCase(unittest.TestCase):
    def setUp(self):
        self.chaoxing = Chaoxing()
        self.course = {
            "clazzId": "class-1",
            "courseId": "course-1",
            "cpi": "cpi-1",
        }
        self.job = {
            "type": "video",
            "jobid": "",
            "name": "非任务视频.mp4",
            "otherinfo": "nodeId_1-cpi_1-rt_d",
            "objectid": "object-1",
            "playTime": 10_000,
            "rt": "0.9",
            "videoFaceCaptureEnc": "",
            "attDuration": "",
            "attDurationEnc": "",
        }

    def test_instant_completion_probe_does_not_skip_non_task_video(self):
        session = _Session()
        with patch.object(self.chaoxing.video_log_limiter, "limit_rate"), patch.object(
            self.chaoxing, "get_uid", return_value="user-1"
        ):
            passed, state = self.chaoxing.video_progress_log(
                session,
                self.course,
                self.job,
                {},
                "dtoken",
                10,
                10,
                _isdrag=4,
            )

        self.assertFalse(passed)
        self.assertEqual(state, 200)

    def test_non_task_video_returns_after_real_playback_reaches_end(self):
        session = _Session()
        with patch.object(SessionManager, "get_session", return_value=session), patch.object(
            self.chaoxing.video_log_limiter, "limit_rate"
        ), patch.object(self.chaoxing, "get_uid", return_value="user-1"), patch(
            "api.base.time.sleep", return_value=None
        ), patch("api.base.tqdm", return_value=_ProgressBar()):
            result = self.chaoxing.study_video(
                self.course,
                self.job,
                {},
                _speed=1.0,
                _type="Video",
            )

        self.assertEqual(result, StudyResult.SUCCESS)
        self.assertEqual(
            [params["isdrag"] for params in session.progress_params],
            [4, 3],
        )

    def test_formal_video_stops_after_bounded_final_confirmations(self):
        session = _Session(has_job_limit=True, max_progress_requests=4)
        formal_job = dict(self.job, jobid="video-job-1")
        with patch.object(SessionManager, "get_session", return_value=session), patch.object(
            self.chaoxing.video_log_limiter, "limit_rate"
        ), patch.object(self.chaoxing, "get_uid", return_value="user-1"), patch(
            "api.base.time.sleep", return_value=None
        ), patch("api.base.tqdm", return_value=_ProgressBar()):
            result = self.chaoxing.study_video(
                self.course,
                formal_job,
                {},
                _speed=1.0,
                _type="Video",
            )

        self.assertEqual(result, StudyResult.TIMEOUT)
        self.assertEqual(len(session.progress_params), 4)


if __name__ == "__main__":
    unittest.main()
