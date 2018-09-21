import json
import sys
import uuid

from amqpstorm import Connection
from flask import Flask, jsonify, request, make_response
from jsonschema import validate

from mash.services.jobcreator import schema
from mash.services.base_config import BaseConfig

app = Flask(__name__, static_url_path='/static')
module = sys.modules[__name__]

connection = None
channel = None
config = None

amqp_host = None
amqp_user = None
amqp_pass = None

schemas = {
    'add_account': {
        'azure': schema.add_account_azure,
        'ec2': schema.add_account_ec2,
        'gce': schema.add_account_gce
    },
    'delete_account': {
        'azure': schema.delete_account,
        'ec2': schema.delete_account,
        'gce': schema.delete_account
    },
    'add_job': {
        'azure': schema.azure_job_message,
        'ec2': schema.ec2_job_message,
        'gce': schema.gce_job_message
    }
}


def connect():
    module.connection = Connection(
        amqp_host,
        amqp_user,
        amqp_pass,
        kwargs={'heartbeat': 600}
    )
    module.channel = connection.channel()
    channel.confirm_deliveries()


def get_config():
    module.config = BaseConfig()
    module.amqp_host = config.get_amqp_host()
    module.amqp_user = config.get_amqp_user()
    module.amqp_pass = config.get_amqp_pass()


def publish(exchange, routing_key, message):
    """
    Publish message to the provided exchange with the routing key.
    """
    if not config:
        get_config()

    if not channel or channel.is_closed:
        connect()

    channel.basic.publish(
        body=message,
        routing_key=routing_key,
        exchange=exchange,
        properties={
            'content_type': 'application/json',
            'delivery_mode': 2
        },
        mandatory=True
    )


def validate_request(flask_request, endpoint):
    # Python 3.4 + 3.5 json module requires string not bytes
    flask_request.data = flask_request.data.decode()
    message = json.loads(flask_request.data)
    provider = message.get('provider')

    if provider not in ['azure', 'ec2']:
        raise Exception('{} is not a valid provider.'.format(provider))

    validate(message, schemas[endpoint][provider])
    return message


def error_response(error):
    return make_response(jsonify({'error': str(error)}), 400)


def status_response(status_msg, status_code):
    return make_response(jsonify({'status': status_msg}), status_code)


@app.route("/add_account", methods=["POST"])
def add_account():
    try:
        result = validate_request(request, 'add_account')
    except Exception as error:
        return error_response(error)

    publish(
        'jobcreator', 'add_account', json.dumps(result, sort_keys=True)
    )
    return status_response('Add account request submitted.', 200)


@app.route("/delete_account", methods=["POST"])
def delete_account():
    try:
        result = validate_request(request, 'delete_account')
    except Exception as error:
        return error_response(error)

    publish(
        'jobcreator', 'delete_account', json.dumps(result, sort_keys=True)
    )
    return status_response('Delete account request submitted.', 200)


@app.route("/add_job", methods=["POST"])
def add_job():
    try:
        result = validate_request(request, 'add_job')
    except Exception as error:
        return error_response(error)

    job_id = str(uuid.uuid4())
    result['job_id'] = job_id

    publish(
        'jobcreator', 'job_document', json.dumps(result, sort_keys=True)
    )

    msg = {
        'job_id': job_id,
        'status': 'Add job request submitted.'
    }
    # Cannot use jsonify with multiple keys, need sorted dump for py3.4
    response = make_response(json.dumps(msg, sort_keys=True), 200)
    response.headers['Content-Type'] = 'application/json; charset=utf-8'
    response.headers['mimetype'] = 'application/json'
    return response


@app.route("/delete_job/<job_id>", methods=["POST"])
def delete_job(job_id):
    content = {'job_delete': job_id}
    publish('jobcreator', 'job_document', json.dumps(content, sort_keys=True))
    return status_response('Delete job request submitted.', 200)
