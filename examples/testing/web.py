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
    responses:
      200:
        description: Please wait the image will be released
    """
    image = request.json.get('image')
    data = json.dumps({'id': image})
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
        <pre id="out"></pre>
        <script>
            $('#image').keyup(function(e){
                if (e.keyCode == 13) {
                    $.ajax({
                      type: "POST",
                      contentType: "application/json",
                      url: "/mash",
                      data: JSON.stringify({'image': $(this).val()}),
                      dataType: "json"
                    });
                    $(this).val('');
                }
            });
        </script>
    """


if __name__ == '__main__':
    app.run(debug=True)
