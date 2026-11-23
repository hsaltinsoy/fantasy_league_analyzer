import os

from app import create_app

app = create_app()

if __name__ == '__main__':
    # The Werkzeug debugger allows arbitrary code execution; keep it opt-in and local only.
    debug = os.environ.get('FLASK_DEBUG', '0').lower() in ('1', 'true', 'yes')
    app.run(host='127.0.0.1', debug=debug)
