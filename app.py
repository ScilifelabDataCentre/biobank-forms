"""Main app for the Data Tracker."""

import logging

import requests
import flask
import flask_mail
import flask_cors

import config
import utils

app = flask.Flask(__name__)  # pylint: disable=invalid-name

appconf = config.init()
app.config.update(appconf)
mail = flask_mail.Mail(app)

cors = flask_cors.CORS(app, resources={r"/forms/": {"origins": "*"}})

SUCCESS_PAGE = '''<html>
 <body>
  Data successfully added. Thank you for your contribution. <a href="PLACEHOLDER">Back to the form.</a>
 </body>
</html>'''

FAIL_PAGE = '''<html>
 <body>
  Failed to add data: bad token. <a href="PLACEHOLDER">Back to the form.</a>
 </body>
</html>'''

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


@app.route('/forms/add_biobank/', methods=['GET', 'POST'])
def add_biobank_form():
    if flask.request.method == 'GET':
        args = dict(flask.request.args)
    elif flask.request.method == 'POST':
        args = dict(flask.request.form)
    token = args.get('token')
    if not token or token not in flask.current_app.config.get('tokens'):
        if 'originUrl' in args:
            page = FAIL_PAGE.replace('PLACEHOLDER', args['originUrl'])
        else:
            page = FAIL_PAGE.replace('<a href="PLACEHOLDER">Back to the form.</a>', '')
        return flask.Response(page, status=401)
    args['timestamp'] = utils.make_timestamp()
    flask.g.db['responsesAddBiobank'].insert_one(args)
    if 'originUrl' in args:
        page = SUCCESS_PAGE.replace('PLACEHOLDER', args['originUrl'])
    else:
        page = SUCCESS_PAGE.replace('<a href="PLACEHOLDER">Back to the form.</a>', '')
    return flask.Response(page, status=200)


SUGGESTION_MAIL_BODY = '''New suggestion for the Covid-19 Data Portal:

From: PLACEHOLDER_NAME (PLACEHOLDER_EMAIL)

Type: PLACEHOLDER_TYPE

Description: PLACEHOLDER_DESCRIPTION
'''

SUGGESTION_TYPES = ('Dataset', 'Data_highlight', 'Research_project',
                    'Journal_publication', 'Preprint', 'Funding_opportunity',
                    'Event', 'Other')

@app.route('/forms/suggestion/', methods=['GET', 'POST'])
def suggest_form():
    if flask.request.method == 'GET':
        args = dict(flask.request.args)
    elif flask.request.method == 'POST':
        args = dict(flask.request.form)
    if 'g-recaptcha-response' in args:
        rec_check = requests.post('https://www.google.com/recaptcha/api/siteverify',
                                  {'secret': app.config.get('suggestions')['recaptcha_secret'],
                                   'response': args['g-recaptcha-response']})
        if not rec_check.json()['success']:
            return flask.Response(status=400)
    else:
        return flask.Response(status=400)

    args['timestamp'] = utils.make_timestamp()
    args['types'] = ', '.join(topic for topic in SUGGESTION_TYPES if (topic in args and
                                                                      args[topic] == 'on'))
    flask.g.db['suggestions'].insert_one(args)

    message = flask_mail.Message('New suggestion for the Covid-19 Data Portal',
                                 sender=flask.current_app.config.get('mail')['email'],
                                 recipients=[app.config.get('suggestions')['email_receivers']])
    mail_body = SUGGESTION_MAIL_BODY[:]
    mail_body = mail_body.replace('PLACEHOLDER_NAME', args['Name'])
    mail_body = mail_body.replace('PLACEHOLDER_EMAIL', args['Email'])
    mail_body = mail_body.replace('PLACEHOLDER_DESCRIPTION', args['Description'])
    mail_body = mail_body.replace('PLACEHOLDER_TYPE', args['types'])
    message.body = mail_body
    mail.send(message)
    if 'originUrl' in args:
        page = SUCCESS_PAGE.replace('PLACEHOLDER', args['originUrl'])
    else:
        page = SUCCESS_PAGE.replace('<a href="PLACEHOLDER">Back to the form.</a>', '')
    return flask.Response(page, status=200)



@app.route('/forms/add_collection/', methods=['GET', 'POST'])
def add_collection_form():
    if flask.request.method == 'GET':
        args = dict(flask.request.args)
    elif flask.request.method == 'POST':
        args = dict(flask.request.form)
    token = args.get('token')
    if not token or token not in flask.current_app.config.get('tokens'):
        if 'originUrl' in args:
            page = FAIL_PAGE.replace('PLACEHOLDER', args['originUrl'])
        else:
            page = FAIL_PAGE.replace('<a href="PLACEHOLDER">Back to the form.</a>', '')
        return flask.Response(page, status=401)
    args['timestamp'] = utils.make_timestamp()
    flask.g.db['responsesAddCollection'].insert_one(args)
    if 'originUrl' in args:
        page = SUCCESS_PAGE.replace('PLACEHOLDER', args['originUrl'])
    else:
        page = SUCCESS_PAGE.replace('<a href="PLACEHOLDER">Back to the form.</a>', '')
    return flask.Response(page, status=200)


@app.route('/forms/<entry>/list/', methods=['GET'])
def get_entry_list(entry):
    args = dict(flask.request.args)
    token = args.get('token')
    if not token or token not in flask.current_app.config.get('getToken'):
        return flask.Response(status=401)
    if entry == 'add_biobank':
        hits = list(flask.g.db['responsesAddBiobank'].find({}, {'_id': 0}))
    elif entry == 'add_collection':
        hits = list(flask.g.db['responsesAddCollection'].find({}, {'_id': 0}))
    elif entry == 'suggestion':
        hits = list(flask.g.db['suggestions'].find({}, {'_id': 0}))
    else:
        return flask.Response(status=404)
    return flask.jsonify(hits)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
else:
    # Assume this means it's handled by gunicorn
    gunicorn_logger = logging.getLogger('gunicorn.error')
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)
