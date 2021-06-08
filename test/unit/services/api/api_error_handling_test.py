from jwt.exceptions import ExpiredSignatureError

from mash.services.api.extensions import handle_jwt_exception


def test_jwt_exception_handling():
    msg = (
        'Signature has expired. Log in again with "mash auth login" '
        'or "mash auth oidc".'
    )
    err = ExpiredSignatureError('Signature has expired')
    resp, code = handle_jwt_exception(err)

    assert code == 401
    assert resp['msg'] == msg
