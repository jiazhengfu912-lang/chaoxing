# -*- coding: utf-8 -*-
"""回归测试：目录页完成状态不能跳过未完成的视频附件。"""
import json
import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.base import Chaoxing, SessionManager  # noqa: E402
from api.decode import decode_course_card  # noqa: E402


class DecodeCourseCardTestCase(unittest.TestCase):
    def test_unfinished_video_without_job_field_is_still_queued(self):
        payload = {
            "defaults": {"knowledgeid": "chapter-1"},
            "attachments": [
                {
                    "isPassed": False,
                    "type": "video",
                    "jobid": "video-without-job",
                    "mid": "mid-1",
                    "objectId": "object-1",
                    "property": {"name": "未完成视频"},
                }
            ],
        }
        html = "<script>mArg=" + json.dumps(payload, separators=(",", ":")) + ";</script>"

        jobs, _ = decode_course_card(html)

        self.assertEqual(
            [(job["type"], job["jobid"]) for job in jobs],
            [("video", "video-without-job")],
        )

    def test_completed_ppt_does_not_hide_unfinished_video(self):
        payload = {
            "defaults": {"knowledgeid": "chapter-1"},
            "attachments": [
                {"isPassed": True, "job": True, "type": "document", "jobid": "ppt-1"},
                {
                    "isPassed": True,
                    "job": True,
                    "type": "video",
                    "jobid": "video-completed",
                    "property": {"name": "已完成视频"},
                },
                {
                    "isPassed": False,
                    "job": True,
                    "type": "video",
                    "jobid": "video-1",
                    "mid": "mid-1",
                    "playTime": 0,
                    "otherInfo": "nodeId_1-cpi_1",
                    "property": {"name": "未完成视频", "objectid": "object-1", "rt": "1"},
                },
            ],
        }
        html = "<script>mArg=" + json.dumps(payload, separators=(",", ":")) + ";</script>"

        with patch("api.decode.logger.info") as log_info:
            jobs, job_info = decode_course_card(html)

        self.assertEqual(job_info["knowledgeid"], "chapter-1")
        self.assertEqual([(job["type"], job["jobid"]) for job in jobs], [("video", "video-1")])
        log_info.assert_any_call("视频已观看：已完成视频")
        log_info.assert_any_call("视频未观看，将开始观看：未完成视频")

    def test_replay_all_includes_completed_videos_but_not_completed_documents(self):
        payload = {
            "defaults": {"knowledgeid": "chapter-1"},
            "attachments": [
                {"isPassed": True, "job": True, "type": "document", "jobid": "ppt-1"},
                {
                    "isPassed": True,
                    "job": True,
                    "type": "video",
                    "jobid": "video-completed",
                    "mid": "mid-completed",
                    "playTime": 90_000,
                    "objectId": "object-completed",
                    "property": {"name": "已完成视频"},
                },
                {
                    "isPassed": False,
                    "job": True,
                    "type": "video",
                    "jobid": "video-unfinished",
                    "mid": "mid-unfinished",
                    "playTime": 30_000,
                    "objectId": "object-unfinished",
                    "property": {"name": "未完成视频"},
                },
            ],
        }
        html = "<script>mArg=" + json.dumps(payload, separators=(",", ":")) + ";</script>"

        jobs, _ = decode_course_card(html, include_completed_videos=True)

        self.assertEqual(
            [job["jobid"] for job in jobs],
            ["video-completed", "video-unfinished"],
        )


class GetJobListTestCase(unittest.TestCase):
    class _Response:
        status_code = 200
        text = ""

    class _Session:
        def get(self, *args, **kwargs):
            return GetJobListTestCase._Response()

    def _get_jobs(self, has_finished):
        chaoxing = Chaoxing()
        course = {"courseId": "course-1", "clazzId": "class-1", "cpi": "cpi-1"}
        point = {"id": "chapter-1", "title": "章节", "has_finished": has_finished}
        with patch.object(SessionManager, "get_session", return_value=self._Session()), patch.object(
            chaoxing.rate_limiter, "limit_rate"
        ), patch.object(chaoxing, "study_emptypage") as study_emptypage:
            jobs, job_info = chaoxing.get_job_list(course, point)
        return jobs, job_info, study_emptypage

    def test_completed_chapter_without_unfinished_jobs_does_not_mark_empty_page(self):
        jobs, job_info, study_emptypage = self._get_jobs(has_finished=True)

        self.assertEqual(jobs, [])
        self.assertEqual(job_info, {})
        study_emptypage.assert_not_called()

    def test_unfinished_empty_page_keeps_existing_completion_behavior(self):
        jobs, job_info, study_emptypage = self._get_jobs(has_finished=False)

        self.assertEqual(jobs, [])
        self.assertEqual(job_info, {})
        study_emptypage.assert_called_once()


if __name__ == "__main__":
    unittest.main()
