from mash.utils.json_format import JsonFormat


class TestJsonFormat(object):
    def test_json_load(self):
        with open('../data/job1.json') as file_handle:
            assert JsonFormat.json_load(
                file_handle
            )['obsjob']['id'] == '123'

    def test_json_loads(self):
        assert JsonFormat.json_loads('["a", "b"]') == ['a', 'b']
        assert JsonFormat.json_loads('{"foo": "bar"}') == {
            'foo': 'bar'
        }

    def test_json_message(self):
        message = '{"obsjob_delete": "4711"}'
        dump_load = JsonFormat.json_loads(
            JsonFormat.json_message(message)
        )
        assert dump_load == message
