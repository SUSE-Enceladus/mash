from base import BaseService


class BasePublisherService(BaseService):
    exchange = 'publisher'

    def publish_image(self, ch, method, properties, body):
        raise NotImplementedError(
            'Publish Image must be implemented in child classes.'
        )
