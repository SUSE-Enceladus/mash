from mash.utils.json_format import JsonFormat


class TestJsonFormat(object):
    def test_json_load_byteified(self):
        with open('../data/job1.json') as file_handle:
            assert JsonFormat.json_load_byteified(
                file_handle
            )['obsjob']['id'] == '123'

    def test_json_loads_byteified(self):
        assert JsonFormat.json_loads_byteified('["a", "b"]') == ['a', 'b']
        assert JsonFormat.json_loads_byteified('{"foo": "bar"}') == {
            'foo': 'bar'
        }

    def test_json_message(self):
        message = '{"obsjob_delete": "4711"}'
        dump_load = JsonFormat.json_loads_byteified(
            JsonFormat.json_message(message)
        )
        assert dump_load == message
