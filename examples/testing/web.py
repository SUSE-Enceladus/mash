import json

from flask import Flask, request, Response
from flasgger import Swagger

from orchestrator import OrchestratorService

app = Flask(__name__)
Swagger(app)

orchestrator = OrchestratorService()


@app.route('/mash', methods=['POST'])
def mash():
    """
    Micro Service Based image release API.
    ---
    parameters:
      - name: body
        in: body
        required: true
        schema:
          id: data
          properties:
            image:
              type: string
            provider:
               type: string
    responses:
      200:
        description: Please wait the image will be released
    """
    image = request.json.get('image')
    provider = request.json.get('provider')
    data = json.dumps({'id': image, 'provider': provider})
    orchestrator.start_image_release(data)
    return Response(status=204)


@app.route('/')
def home():
    return """
        <!doctype html>
        <title>Release Orchestrator</title>
        <script src="https://code.jquery.com/jquery-3.2.1.min.js"integrity="sha256-hwg4gsxgFZhOsEEamdOYGBf13FyQuiTwlAQgxVSNgt4="crossorigin="anonymous"></script>
        <style>body { max-width: 500px; margin: auto; padding: 1em; background: black; color: #fff; font: 16px/1.6 menlo, monospace; }</style>
        <p><b>Enter image ID to release!</b></p>
        <p>Image ID: <input id="image" /></p>
        <p>Provider: <input id="provider" /></p>
        <pre id="out"></pre>
        <script>
            $('#provider').keyup(function(e){
                if (e.keyCode == 13) {
                    $.ajax({
                      type: "POST",
                      contentType: "application/json",
                      url: "/mash",
                      data: JSON.stringify({'image': $('#image').val(), 'provider': $(this).val()}),
                      dataType: "json"
                    });
                    $('#image').val('');
                    $(this).val('');
                }
            });
        </script>
    """


if __name__ == '__main__':
    app.run(debug=True)
