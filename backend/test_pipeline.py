from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent))

from models import Dialogue, Scene, ValidationResult, SchemaValidation


def create_pipeline(genre: str = "叙事"):
    with patch("pipeline.AsyncOpenAI"), patch("prompts.GENRE_GUIDANCE", {}), patch(
        "pipeline._load_genre_guidance", return_value=""
    ), patch("pipeline._load_genre_keywords", return_value=[]):
        import pipeline as pl

        return pl.Pipeline(api_key="test_key", genre=genre)


class TestTextCleaning(unittest.TestCase):
    def setUp(self):
        self.pipeline = create_pipeline()

    def test_normalize_spaces(self):
        result = self.pipeline._clean_text("第一章  开始了    新的旅程")
        self.assertNotIn("  ", result)

    def test_collapse_newlines(self):
        result = self.pipeline._clean_text("第一段\n\n\n\n第二段")
        self.assertNotIn("\n\n\n", result)

    def test_strip_whitespace(self):
        result = self.pipeline._clean_text("  内容  \n\n  ")
        self.assertEqual(result, "内容")


class TestChapterDetection(unittest.TestCase):
    def setUp(self):
        self.pipeline = create_pipeline()

    def test_single_chapter(self):
        text = "第1章 开始\n这是一段内容"
        chapters = self.pipeline._detect_chapters(text)
        self.assertEqual(len(chapters), 1)
        self.assertEqual(chapters[0]["title"], "第1章 开始")

    def test_multiple_chapters(self):
        text = "第1章 开始\n这是第一章的正文内容\n\n第2章 发展\n这是第二章的正文内容\n\n第3章 结束\n这是第三章的正文内容"
        chapters = self.pipeline._detect_chapters(text)
        self.assertEqual(len(chapters), 3)

    def test_chinese_numeral_chapters(self):
        text = "第一章 序章\n这里是序章正文\n\n第二章 正文\n这里是正文内容"
        chapters = self.pipeline._detect_chapters(text)
        self.assertEqual(len(chapters), 2)

    def test_no_chapter_markers(self):
        text = "这是一段没有章节标记的普通文本内容"
        chapters = self.pipeline._detect_chapters(text)
        self.assertEqual(len(chapters), 1)
        self.assertEqual(chapters[0]["title"], "全文")

    def test_chapter_content_boundaries(self):
        text = "第1章 开始\n这是第一章的正文\n第2章 发展\n这是第二章的正文"
        chapters = self.pipeline._detect_chapters(text)
        self.assertEqual(len(chapters), 2)
        self.assertIn("这是第一章的正文", chapters[0]["content"])
        self.assertIn("这是第二章的正文", chapters[1]["content"])


class TestJSONExtraction(unittest.TestCase):
    def setUp(self):
        self.pipeline = create_pipeline()

    def test_pure_json_object(self):
        result = self.pipeline._extract_json('{"key": "value"}')
        self.assertEqual(result, {"key": "value"})

    def test_json_with_markdown_fence(self):
        result = self.pipeline._extract_json('```json\n{"key": "value"}\n```')
        self.assertEqual(result, {"key": "value"})

    def test_json_with_text_surrounding(self):
        result = self.pipeline._extract_json('一些说明文字 {"key": "value"} 更多文字')
        self.assertEqual(result, {"key": "value"})

    def test_json_array(self):
        result = self.pipeline._extract_json('[{"a": 1}, {"b": 2}]')
        self.assertEqual(result, [{"a": 1}, {"b": 2}])

    def test_invalid_json_returns_none(self):
        result = self.pipeline._extract_json("这不是JSON")
        self.assertIsNone(result)


class TestSchemaValidation(unittest.TestCase):
    def setUp(self):
        self.pipeline = create_pipeline()

    def test_valid_scenes_pass(self):
        characters = [{"name": "张三", "id": "C001"}]
        scenes = [
            {
                "scene_id": 1,
                "scene_heading": "第1场 内景 公寓 上午",
                "location": "公寓",
                "time_of_day": "上午",
                "characters_present": ["张三"],
                "action": ["张三醒来"],
                "dialogues": [{"character": "张三", "line": "早上好"}],
            }
        ]
        result, _ = self.pipeline._validate_schema(scenes, characters)
        self.assertTrue(result.passed)

    def test_missing_scene_id_auto_fills(self):
        characters = [{"name": "张三", "id": "C001"}]
        scenes = [
            {
                "scene_heading": "某场景",
                "location": "某地",
                "characters_present": ["张三"],
                "dialogues": [],
            }
        ]
        result, fixed = self.pipeline._validate_schema(scenes, characters)
        self.assertEqual(fixed[0]["scene_id"], 1)

    def test_orphan_character_warns(self):
        characters = [{"name": "张三", "id": "C001"}]
        scenes = [
            {
                "scene_id": 1,
                "scene_heading": "场景1",
                "characters_present": ["李四"],
                "dialogues": [],
            }
        ]
        result, _ = self.pipeline._validate_schema(scenes, characters)
        self.assertGreater(len(result.warnings), 0)

    def test_dialogue_character_not_in_scene_warns(self):
        characters = [{"name": "张三", "id": "C001"}, {"name": "李四", "id": "C002"}]
        scenes = [
            {
                "scene_id": 1,
                "scene_heading": "场景1",
                "characters_present": ["张三"],
                "dialogues": [{"character": "李四", "line": "你好"}],
            }
        ]
        result, _ = self.pipeline._validate_schema(scenes, characters)
        self.assertGreater(len(result.warnings), 0)


class TestMainCharacterValidation(unittest.TestCase):
    def setUp(self):
        self.pipeline = create_pipeline()

    def test_clear_main_character(self):
        characters = [{"name": "主角A", "id": "C001"}, {"name": "配角B", "id": "C002"}]
        scenes = [
            {
                "scene_id": 1,
                "characters_present": ["主角A", "配角B"],
                "action": ["主角A做了一件事", "主角A又做了一件事"],
                "dialogues": [
                    {"character": "主角A", "line": "台词1"},
                    {"character": "主角A", "line": "台词2"},
                ],
            },
            {
                "scene_id": 2,
                "characters_present": ["主角A"],
                "action": ["主角A继续前行"],
                "dialogues": [{"character": "主角A", "line": "台词3"}],
            },
        ]
        chapters = [
            {
                "content": "主角A做了一件事，主角A又做了一件事，主角A在这里出现了很多次，主角A的故事很精彩。" * 10,
                "index": 1,
            },
        ]
        result = self.pipeline._validate_main_character(scenes, characters, chapters)
        self.assertEqual(result.main_character, "主角A")
        self.assertEqual(result.count, 2)
        self.assertEqual(result.status, "验证通过")

    def test_no_characters_found(self):
        result = self.pipeline._validate_main_character([], [], [])
        self.assertEqual(result.count, 0)
        self.assertEqual(result.status, "未找到主角")

    def test_empty_appearance(self):
        scenes = [
            {"scene_id": 1, "characters_present": [], "dialogues": [], "action": []}
        ]
        result = self.pipeline._validate_main_character(scenes, [], [])
        self.assertEqual(result.status, "未找到主角")


class TestYAMLAssembly(unittest.TestCase):
    def setUp(self):
        self.pipeline = create_pipeline()

    def test_basic_yaml_output(self):
        characters = [{"name": "张三", "id": "C001"}]
        chapters = [{"index": 1, "title": "第一章", "content": "测试内容"}]
        scenes = [
            {
                "scene_id": 1,
                "scene_heading": "第1场 内景 公寓 上午",
                "location": "公寓",
                "time_of_day": "上午",
                "characters_present": ["张三"],
                "action": ["张三醒来"],
                "dialogues": [
                    {"character": "张三", "line": "早上好", "parenthetical": ""}
                ],
                "transition": "",
            }
        ]
        validation = ValidationResult(main_character="张三", count=2, status="验证通过")
        schema = SchemaValidation()
        yaml_str, output = self.pipeline._build_output(
            scenes, characters, chapters, validation, schema
        )
        self.assertIn("meta:", yaml_str)
        self.assertIn("script:", yaml_str)
        self.assertIn("scene_id: 1", yaml_str)
        self.assertIn("张三", yaml_str)
        self.assertEqual(output["meta"]["scene_count"], 1)
        self.assertEqual(output["meta"]["character_count"], 1)


class TestModels(unittest.TestCase):
    def test_validation_result_defaults(self):
        vr = ValidationResult()
        self.assertEqual(vr.main_character, "")
        self.assertEqual(vr.count, 0)
        self.assertFalse(vr.retried)

    def test_schema_validation_defaults(self):
        sv = SchemaValidation()
        self.assertTrue(sv.passed)
        self.assertEqual(sv.warnings, [])
        self.assertEqual(sv.errors, [])


class TestDatabase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from database import DB_PATH, get_auth_db

        cls._real_db = DB_PATH
        cls._test_db = DB_PATH.parent / "app_test.db"

        import database as db_mod

        db_mod.DB_PATH = cls._test_db

        if cls._test_db.exists():
            cls._test_db.unlink()
        for ext in (".db-wal", ".db-shm"):
            p = cls._test_db.with_suffix(ext)
            if p.exists():
                p.unlink()

        from database import init_auth_db

        init_auth_db()

    @classmethod
    def tearDownClass(cls):
        import database as db_mod

        db_mod.DB_PATH = cls._real_db
        if cls._test_db.exists():
            cls._test_db.unlink()
        for ext in (".db-wal", ".db-shm"):
            p = cls._test_db.with_suffix(ext)
            if p.exists():
                p.unlink()

    def setUp(self):
        import database as db_mod

        self._clean_db()

    def _clean_db(self):
        from database import get_auth_db

        conn = get_auth_db()
        conn.execute("DELETE FROM conversions")
        conn.execute("DELETE FROM genres WHERE is_system=0")
        conn.execute("DELETE FROM users")
        conn.commit()
        conn.close()

    def tearDown(self):
        self._clean_db()

    def test_create_and_get_user(self):
        from database import db_create_user, db_get_user_by_username

        user = db_create_user("testuser", "hash123", "token123")
        self.assertEqual(user["username"], "testuser")
        self.assertEqual(user["token"], "token123")

        fetched = db_get_user_by_username("testuser")
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched["username"], "testuser")

    def test_duplicate_user_raises(self):
        from database import db_create_user

        db_create_user("dupuser", "hash", "token")
        with self.assertRaises(ValueError):
            db_create_user("dupuser", "hash2", "token2")

    def test_user_token_verification(self):
        from database import db_create_user, db_get_user_by_token, db_update_user_token

        db_create_user("tokuser", "hash", "token456")
        user = db_get_user_by_token("token456")
        self.assertIsNotNone(user)
        self.assertEqual(user["username"], "tokuser")

        db_update_user_token("tokuser", "newtoken789")
        old = db_get_user_by_token("token456")
        new = db_get_user_by_token("newtoken789")
        self.assertIsNone(old)
        self.assertIsNotNone(new)

    def test_system_genres_seeded(self):
        from database import db_get_system_genres

        genres = db_get_system_genres()
        self.assertGreater(len(genres), 0)
        names = {g["name"] for g in genres}
        self.assertIn("叙事", names)

    def test_user_genre_crud(self):
        from database import (
            db_create_user,
            db_add_user_genre,
            db_get_user_genres,
            db_count_user_genres,
            db_update_user_genre,
            db_delete_user_genre,
        )

        db_create_user("genuser", "hash", "token_gen")

        genre = db_add_user_genre("genuser", "悬疑", "指导文本", ["侦探", "谜题"])
        self.assertEqual(genre["name"], "悬疑")
        self.assertEqual(len(genre["keywords"]), 2)

        count = db_count_user_genres("genuser")
        self.assertEqual(count, 1)

        user_genres = db_get_user_genres("genuser")
        self.assertEqual(len(user_genres), 1)
        self.assertEqual(user_genres[0]["name"], "悬疑")

        updated = db_update_user_genre("genuser", 0, "推理", "新指导", ["侦探"])
        self.assertEqual(updated["name"], "推理")

        deleted = db_delete_user_genre("genuser", 0)
        self.assertEqual(deleted, "推理")

        count = db_count_user_genres("genuser")
        self.assertEqual(count, 0)

    def test_conversion_crud(self):
        from database import (
            db_create_user,
            db_create_conversion,
            db_get_conversion,
            db_list_conversions,
            db_delete_conversion,
            db_update_conversion_progress,
            db_update_conversion_status,
            db_save_conversion_result,
            db_update_conversion_yaml,
        )

        db_create_user("convuser", "hash", "token_conv")

        db_create_conversion("test-task-1", "convuser", "原文", "叙事", "标题1")
        db_update_conversion_progress("test-task-1", {"step": 1, "total": 7, "step_name": "测试", "message": "进行中"})

        conv = db_get_conversion("test-task-1")
        self.assertIsNotNone(conv)
        self.assertEqual(conv["title"], "标题1")

        db_update_conversion_status("test-task-1", "failed", "测试错误")
        conv = db_get_conversion("test-task-1")
        self.assertEqual(conv["status"], "failed")
        self.assertEqual(conv["error"], "测试错误")

        db_save_conversion_result("test-task-1", "yaml内容", '{"key":"val"}', '{"int":"val"}', "清洗后")
        conv = db_get_conversion("test-task-1")
        self.assertEqual(conv["status"], "completed")
        self.assertEqual(conv["yaml_output"], "yaml内容")

        db_update_conversion_yaml("test-task-1", "编辑后的yaml", "convuser")
        conv = db_get_conversion("test-task-1")
        self.assertEqual(conv["yaml_output"], "编辑后的yaml")

        list_result = db_list_conversions("convuser")
        self.assertEqual(len(list_result), 1)

        deleted = db_delete_conversion("test-task-1", "convuser")
        self.assertTrue(deleted)

        list_result = db_list_conversions("convuser")
        self.assertEqual(len(list_result), 0)


if __name__ == "__main__":
    unittest.main()
