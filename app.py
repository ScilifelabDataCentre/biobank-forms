"""Main app for the Data Tracker."""

import logging

import flask
import flask_cors

import config
import utils

app = flask.Flask(__name__)  # pylint: disable=invalid-name
appconf = config.init()
app.config.update(appconf)

cors = flask_cors.CORS(app, resources={r"/forms/": {"origins": "*"}})

@app.before_request
def prepare():
    """Open the database connection and get the current user."""
    flask.g.dbclient = utils.get_dbclient(flask.current_app.config)
    flask.g.db = utils.get_db(flask.g.dbclient, flask.current_app.config)


@app.after_request
def finalize(response):
    """Finalize the response and clean up."""
    # close db connection
    if hasattr(flask.g, 'dbserver'):
        flask.g.dbserver.close()
    # add some headers for protection
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    return response


@app.route('/heartbeat/', methods=['GET'])
def heartbeat():
    return flask.Response(status=200)


PAGE = '''<html>
 <body>
  Data successfully added. <a href="PLACEHOLDER">Back to the form.</a>
 </body>
</html>'''

@app.route('/forms/add_biobank/', methods=['GET'])
def add_biobank_form():
    args = dict(flask.request.args)
    if not (token := args.get('token')) or\
       token not in flask.current_app.config.get('tokens'):
        return flask.Response(status=401)
    args['timestamp'] = utils.make_timestamp()
    flask.g.db['responsesAddBiobank'].insert_one(args)
    if 'originUrl' in args:
        page = PAGE.replace('PLACEHOLDER', args['originUrl'])
    else:
        page = PAGE.replace('<a href="PLACEHOLDER">Back to the form.</a>', '')
    return flask.Response(page, status=200)


@app.route('/forms/add_collection/', methods=['GET'])
def add_collection_form():
    args = dict(flask.request.args)
    if not (token := args.get('token')) or\
       token not in flask.current_app.config.get('tokens'):
        return flask.Response(status=401)
    args['timestamp'] = utils.make_timestamp()
    flask.g.db['responsesAddCollection'].insert_one(args)
    return flask.Response(status=200)

@app.route('/forms/<entry>/list/', methods=['GET'])
def get_entry_list(entry):
    args = dict(flask.request.args)
    if not (token := args.get('token')) or\
       token != flask.current_app.config.get('getToken'):
        return flask.Response(status=401)
    if entry == 'add_biobank':
        hits = list(flask.g.db['responsesAddBiobank'].find({}, {'_id': 0}))
    elif entry == 'add_collection':
        hits = list(flask.g.db['responsesAddCollection'].find({}, {'_id': 0}))
    else:
        return flask.Response(status=404)
    return flask.jsonify(hits)


@app.errorhandler(400)
def error_bad_request(_):
    """Make sure a simple 400 is returned instead of an html page."""
    return flask.Response(status=400)


@app.errorhandler(401)
def error_unauthorized(_):
    """Make sure a simple 401 is returned instead of an html page."""
    return flask.Response(status=401)


@app.errorhandler(403)
def error_forbidden(_):
    """Make sure a simple 403 is returned instead of an html page."""
    return flask.Response(status=403)


@app.errorhandler(404)
def error_not_found(_):
    """Make sure a simple 404 is returned instead of an html page."""
    return flask.Response(status=404)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
else:
    # Assume this means it's handled by gunicorn
    gunicorn_logger = logging.getLogger('gunicorn.error')
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)
