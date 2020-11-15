from datetime import datetime
from types import SimpleNamespace

from django.test import TestCase

from boticario.logging import BoticarioJSONFormatter


class BoticarioJSONFormatterTest(TestCase):

    def setUp(self):
        self.formatter = BoticarioJSONFormatter()

    def test_add_record_field_sem_record(self):
        extra = {"foo": "bar"}
        record = None
        fieldname = "test"
        self.assertIsNone(self.formatter.add_record_field(extra, record, fieldname))
        self.assertEqual(extra, {"foo": "bar"})  # Não foi modificado

    def test_add_record_field_sem_extra(self):
        extra = None
        record = {}
        fieldname = "test"
        self.assertIsNone(self.formatter.add_record_field(extra, record, fieldname))
        self.assertIsNone(extra)  # Não foi modificado

    def test_add_record_field_add_test_value(self):
        extra = {}
        record = SimpleNamespace()
        record.test = "value"
        fieldname = "test"
        self.formatter.add_record_field(extra, record, fieldname)
        self.assertEqual(extra, {"test": "value"})

    def test_add_record_field_add_test_value_com_destination_name(self):
        extra = {}
        record = SimpleNamespace()
        record.test = "bar"
        fieldname = "test"
        self.formatter.add_record_field(extra, record, fieldname, destination_name="foo")
        self.assertEqual(extra, {"foo": "bar"})

    def test_json_record_remove_request(self):
        message = "Foo"
        extra = {"request": None}
        record = SimpleNamespace()
        return_value = self.formatter.json_record(message, extra, record)
        self.assertNotIn("request", return_value)

    def test_json_record_adiciona_time(self):
        message = "Foo"
        extra = {}
        record = SimpleNamespace()
        return_value = self.formatter.json_record(message, extra, record)
        self.assertIn("time", return_value)
        self.assertTrue(isinstance(return_value["time"], datetime))

    def test_json_record_adiciona_message(self):
        message = "Foo"
        extra = {}
        record = SimpleNamespace()
        return_value = self.formatter.json_record(message, extra, record)
        self.assertIn("message", return_value)
        self.assertEqual(message, return_value["message"])

    def test_json_record_adiciona_propriedades_do_record(self):
        message = "Foo"
        extra = {}
        record = SimpleNamespace()
        record.levelname = "INFO"
        record.filename = "foo.py"
        record.lineno = 42
        record.request_id = "xpto"
        return_value = self.formatter.json_record(message, extra, record)
        self.assertIn("level", return_value)
        self.assertEqual(return_value["level"], "INFO")
        self.assertIn("filename", return_value)
        self.assertEqual(return_value["filename"], "foo.py")
        self.assertIn("lineno", return_value)
        self.assertEqual(return_value["lineno"], 42)
        self.assertIn("request_id", return_value)
        self.assertEqual(return_value["request_id"], "xpto")
