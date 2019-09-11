def test_api_docs(test_client):
    api_desc = b'MASH provides a set of endpoints for Image Release ' \
               b'automation into Public Cloud Frameworks.'

    response = test_client.get('/api/spec/')
    assert response.status_code == 200
    assert api_desc in response.data

    response = test_client.post('/api/spec/')
    assert response.status_code == 200
    assert api_desc in response.data
