from mash.services.api.app import create_app
from mash.services.api.config import Config

application = create_app(Config())

if __name__ == '__main__':
    application.run(port=5000)
