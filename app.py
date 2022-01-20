import json
import os
import subprocess

from flask import Flask, render_template, request, Response, redirect, flash, url_for, jsonify, send_from_directory, send_file
from flask_socketio import SocketIO, emit
from flask_uploads import UploadSet, configure_uploads, IMAGES, patch_request_class
from flask_fontawesome import FontAwesome
from flask_wtf import FlaskForm
from flask_wtf.csrf import CSRFProtect, CSRFError
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import Form, StringField, SubmitField, TextAreaField, BooleanField, SelectField, FormField
from wtforms.validators import DataRequired
import forms
from flask_dropzone import Dropzone
from werkzeug.utils import secure_filename
from pygtail import Pygtail
import logging.config, os, sys, time
import logging
from dotenv import load_dotenv
from datetime import datetime, timedelta
import pandas as pd
from pathlib import Path
import excel2json
import hashlib

app = Flask(__name__)

load_dotenv()


# logging.config.dictConfig({
#     "version": 1,
#     "disable_existing_loggers": False,
#     'formatters': {
#         'colored': {
#             '()': 'colorlog.ColoredFormatter',  # colored output
#             # --> %(log_color)s is very important, that's what colors the line
#             'format': '[%(asctime)s,%(lineno)s] %(log_color)s[%(message)s]',
#             'log_colors': {
#                 'DEBUG': 'green',
#                 'INFO': 'cyan',
#                 'WARNING': 'yellow',
#                 'ERROR': 'red',
#                 'CRITICAL': 'bold_red',
#             },
#         },
#         'simple': {
#                 'format': '[%(asctime)s,%(lineno)s] [%(message)s]',
#             },
#     },
#     "handlers": {
#         "console": {
#             "class": "colorlog.StreamHandler",
#             "level": "INFO",
#             "formatter": "colored",
#             "stream": "ext://sys.stdout"
#         },
#         "file": {
#             "class": "logging.handlers.RotatingFileHandler",
#             "level": "INFO",
#             "formatter": "simple",
#             "filename": 'STD_OUTPUT.log'
#         },
#     },
#     "root": {"level": "INFO",
#              "handlers": ["console", "file"]
#              }
# })

# LOGGER = logging.getLogger()

app.config.update(
    FLASK_APP=os.getenv("FLASK_APP"),
    DEBUG=os.getenv("DEBUG"),
    SECRET_KEY=os.getenv("SECRET_KEY"),
    WTF_CSRF_SECRET_KEY=os.getenv("WTF_CSRF_SECRET_KEY"),
    JSON_AS_ASCII=False,
    JSONIFY_PRETTYPRINT_REGULAR=True,
    DROPZONE_ALLOWED_FILE_CUSTOM=True,
    DROPZONE_ALLOWED_FILE_TYPE=os.getenv("DROPZONE_ALLOWED_FILE_TYPE"),
    DROPZONE_INPUT_NAME="file",
    DROPZONE_MAX_FILE_SIZE=int(os.getenv("DROPZONE_MAX_FILE_SIZE")),
    DROPZONE_MAX_FILES=int(os.getenv("DROPZONE_MAX_FILES")),
    DROPZONE_TIMEOUT=int(os.getenv("DROPZONE_TIMEOUT")) * 60 * 1000,
    DROPZONE_DEFAULT_MESSAGE="Upload",
    DROPZONE_ENABLE_CSRF=True,
    DROPZONE_SERVE_LOCAL=True,
    FONTAWESOME_SERVE_LOCAL=True,
)

# Get project root directory
PROJECT_ROOT = Path(os.path.abspath(os.path.dirname(__file__)))
UPLOAD_FOLDER = PROJECT_ROOT / f'{os.getenv("UPLOAD_FOLDER")}/'
OUTPUT_FOLDER = PROJECT_ROOT / f'{os.getenv("OUTPUT_FOLDER")}/'
CFG_FILENAME_BUY = os.getenv("CFG_FILENAME_BUY")
CFG_FILENAME_SELL = os.getenv("CFG_FILENAME_SELL")
MAIN_PY_COMMAND = os.getenv("MAIN_PY_COMMAND")
BACKTESTER_CFG_BUY = str(UPLOAD_FOLDER / CFG_FILENAME_BUY)
BACKTESTER_CFG_BUY_COMNT = str(OUTPUT_FOLDER / "backtester_config_buy_comments.json")
BACKTESTER_CFG_SELL_COMNT = str(OUTPUT_FOLDER / "backtester_config_sell_comments.json")
BACKTESTER_CFG_SELL = str(UPLOAD_FOLDER / CFG_FILENAME_SELL)
LOG_FILE = str(PROJECT_ROOT / f'{os.getenv("LOG_FILE")}')
file_details_prev = str(OUTPUT_FOLDER / "file_details_prev.csv")
file_details_new = str(OUTPUT_FOLDER / "file_details_new.csv")
ALLOWED_EXTENSIONS = {'json'}
socketio = SocketIO(app)
# Dropzone file uploader initialization
dropzone = Dropzone(app)
csrf = CSRFProtect(app)
fa = FontAwesome(app)

# Initialize LOGGER
logging.basicConfig(filename=LOG_FILE, level=logging.DEBUG)
LOGGER = logging.getLogger(__name__)

files = None


# Validates file by extensions against ALLOWED_EXTENSIONS
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# Scans uploads directory and calculate MD5-Hashes of Buy & Sell JSON files
def get_files_details():
    """Scans files in the uploads folder and returns their MD5-Hash and DateLastModified."""
    files_dict = {}
    for filename in os.listdir(UPLOAD_FOLDER):
        path = str(UPLOAD_FOLDER / filename)
        if os.path.isfile(path) and filename.split('.')[1] == 'json':
            df = pd.read_json(path_or_buf=path)
            # Convert DataFrame to JSON string
            json_str = df.to_string()
            # Calculate MD5-Hash of JSON string
            LOGGER.info(f"Calculating MD5-Hash of JSON file: {filename}")
            md5_hash = hashlib.md5(json_str.encode('utf-8')).hexdigest()
            # Get file's date last modified Unix TimeStamp
            LOGGER.info(f"Getting DateLastModified of JSON file: {filename}")
            file_timestamp = os.path.getmtime(path)
            file_last_modified = datetime.fromtimestamp(file_timestamp).strftime("%Y-%d-%m %H:%M:%S")
            file_dict = {"FileName": filename, "MD5Hash": md5_hash, "DateLastModified": file_last_modified}
            # Divide files by type: Buy and Sell to keep them in two tables on index page
            if 'buy' in filename:
                files_dict["Buy"] = file_dict
            else:
                files_dict["Sell"] = file_dict
    return files_dict


# Check and update hashes record if changes found
def check_hash():
    LOGGER.info(f'Rescanning files')
    print(f'Rescanning files')
    files = get_files_details()
    prev_files = pd.read_csv(file_details_prev, index_col=None)
    prev_file_hashes = [file["MD5Hash"] for file in prev_files.iloc]
    # Validate MD5-Hash and run the test if changes found
    if files['Buy']['MD5Hash'] not in prev_file_hashes or files['Sell']['MD5Hash'] not in prev_file_hashes:
        print('Changes detected')
        print('Updating file details')
        new_details = []
        new_details.append(files['Buy'])
        new_details.append(files['Sell'])
        df = pd.DataFrame(new_details)
        df.to_csv(file_details_prev, index=False)
        return True, files
    else:
        return False, files


# Main route, the TESTER page
@app.route('/', methods=['GET', 'POST'])
def index():
    # Our Custom standard form from forms.py
    form = forms.TestForm()
    form_rescan = forms.RescanForm()
    LOGGER.info(f'Tester request: {request.method}')
    print(f'Tester request: {request.method}')
    changes_detected, files = check_hash()
    # If POST request is START TESTING and it has either buy or sell selection
    if 'rescan' in request.form.to_dict():
        # Rescan files in uploads directory and look for changes
        # Check MD5-Hashes of updated files and run the test if changes found
        changes_detected, files = check_hash()
        if changes_detected:
            flash(f'Changes found!: This config will generate new results.', 'success')
            return render_template('index.html', files=files, form=form, form_rescan=form_rescan)
        else:
            flash(f'No changes detected!: You may still run the test but the results will be the same as during the previous run.', 'warning')
            return render_template('index.html', files=files, form=form, form_rescan=form_rescan)
    # If POST request is START TESTING and it has either buy or sell selection
    elif form.validate_on_submit() or form.buy_sell.data in ["buy", "sell"]:
        buy_sell = form.buy_sell.data
        print(f'Selected BUY/SELL file: {buy_sell}')
        process = None
        if form.start.data:
            print(f'Starting test')
            if buy_sell == 'backtester_config_buy':
                # Start with backtester_config_buy.json
                flash(f'Warning!: Buy file testing has been started.', 'warning')
                # Please set your main.py accordingly
                # result = subprocess.check_output("python main.py", shell=True)
                process = subprocess.Popen('python main.py', stdout=subprocess.PIPE, shell=True)
                output, err = process.communicate()
                print(f"Test successful")
                # return output
                return render_template('index.html', files=files, form=form, form_rescan=form_rescan, logs=output)
            elif buy_sell == 'backtester_config_sell':
                # Start testing backtester_config_sell.json
                flash(f'Warning!: Sell file testing has been started.', 'warning')
                # Please set your main.py accordingly
                process = subprocess.Popen('python main.py', stdout=subprocess.PIPE)
                output, err = process.communicate()
                print(f"Test successful")
                # return output
                return render_template('index.html', files=files, form=form, form_rescan=form_rescan, logs=output)
        elif form.terminate.data:
            if process is not None:
                print(f'Terminating test')
                process.kill()
    # If POST request has a file named: file
    elif request.method == 'POST' and 'file' in request.files:
        LOGGER.info(f"POST file: {request.files['file']}")
        file = request.files['file']
        file_name = file.filename
        # Verify file extension and filename according to the ENV <CFG_FILENAME_BUY CFG_FILENAME_SELL >, if doesn't match, refuse to upload
        # if file_name.split('.')[-1] not in ALLOWED_EXTENSIONS:
        if file_name.split('.')[-1] != 'json':
            LOGGER.info(f"Invalid extension: {file_name, file_name.split('.')[-1]}")
            return 'JSON only!', 400  # return the error message, with a proper 4XX code
            # Verify the filename according to ENV <CFG_FILENAME_BUY=Config.py>
        if file_name != CFG_FILENAME_BUY and file_name != CFG_FILENAME_SELL:
            print(f"Incorrect filename: {file_name} != {CFG_FILENAME_BUY}")
            LOGGER.info(f'Incorrect filename: {file_name}')
            return f'Incorrect filename: {file_name}', 400
        if file and allowed_file(file_name):
            filename = secure_filename(file_name)
            file.save(os.path.join(UPLOAD_FOLDER, filename))
            LOGGER.info(f'File has been uploaded: {filename}')
            flash(f'Success!: File has been uploaded. {filename}', 'success')
            return render_template("index.html", files=files, form=form, form_rescan=form_rescan)
    return render_template("index.html", files=files, form=form, form_rescan=form_rescan)


@app.route('/config', methods=['GET', 'POST'])
def config():
    # Our Custom standard form from forms.py
    form = forms.ConfigForm()
    LOGGER.info(f'Config Request: {request.method}')
    print(f'Config Request: {request.method}')
    if form.validate_on_submit():
        data = request.form.to_dict()
        print(f'Config POST Data: {data}')
        if 'submit-buy' in data:
            update_config(buy_sell='buy', data=data)
            update_comment(buy_sell='buy', data=data)
        else:
            update_config(buy_sell='sell', data=data)
            update_comment(buy_sell='sell', data=data)
        flash(f'Success: Changes have been saved.', 'success')
        # return redirect('config.html')
    # buy_data, buy_entry, buy_exit, buy_backtester, sell_data, sell_entry, sell_exit, sell_backtester = get_config_data()
    config_dfs = get_config_dfs()
    comment_dfs = get_comment_dfs()
    # flash(f'Success: Changes have been saved.', 'success')
    return render_template('config.html', form=form, config_dfs=config_dfs, comment_dfs=comment_dfs)


# Gets Buy & Sell JSON DataFrames
def get_config_dfs():
    with open(BACKTESTER_CFG_BUY) as f:
        json_str = json.load(f)
        header_dict = {"rule_id": json_str[0]['rule_id'], "rule_side": json_str[0]['rule_side'], "rule_name": json_str[0]['rule_name']}
        header_df = pd.DataFrame(header_dict.items(), columns=["Param", "Value"])
        entry_dict = json_str[0]['entry_params']
        exit__dict = json_str[0]['exit_params']
        data_dict = json_str[0]['data_params']
        backtest_dict = json_str[0]['backtest_params']
        entry_df = pd.DataFrame(entry_dict.items(), columns=["Param", "Value"])
        exit_df = pd.DataFrame(exit__dict.items(), columns=["Param", "Value"])
        data_df = pd.DataFrame(data_dict.items(), columns=["Param", "Value"])
        backtest_df = pd.DataFrame(backtest_dict.items(), columns=["Param", "Value"])
        buy_dfs = {"Header": header_df, "Entry": entry_df, "Exit": exit_df, "Data": data_df, "Backtest": backtest_df}
    with open(BACKTESTER_CFG_SELL) as f:
        json_str = json.load(f)
        header_dict = {"rule_id": json_str[0]['rule_id'], "rule_side": json_str[0]['rule_side'], "rule_name": json_str[0]['rule_name']}
        header_df = pd.DataFrame(header_dict.items(), columns=["Param", "Value"])
        entry_dict = json_str[0]['entry_params']
        exit__dict = json_str[0]['exit_params']
        data_dict = json_str[0]['data_params']
        backtest_dict = json_str[0]['backtest_params']
        entry_df = pd.DataFrame(entry_dict.items(), columns=["Param", "Value"])
        exit_df = pd.DataFrame(exit__dict.items(), columns=["Param", "Value"])
        data_df = pd.DataFrame(data_dict.items(), columns=["Param", "Value"])
        backtest_df = pd.DataFrame(backtest_dict.items(), columns=["Param", "Value"])
        sell_dfs = {"Header": header_df, "Entry": entry_df, "Exit": exit_df, "Data": data_df, "Backtest": backtest_df}
    return {"Buy": buy_dfs, "Sell": sell_dfs}


# Update Buy & Sell JSON
def update_config(buy_sell, data):
    if buy_sell == 'buy':
        with open(BACKTESTER_CFG_BUY) as f:
            json_buy = json.load(f)
            json_buy[0]['rule_id'] = data['rule_id']
            json_buy[0]['rule_side'] = data['rule_side']
            json_buy[0]['rule_name'] = data['rule_name']
            for key, item in json_buy[0]['entry_params'].items():
                if key in data:
                    json_buy[0]['entry_params'][key] = data[key].upper()
            for key, item in json_buy[0]['exit_params'].items():
                if key in data:
                    json_buy[0]['exit_params'][key] = data[key].upper()
            for key, item in json_buy[0]['data_params'].items():
                if key in data:
                    json_buy[0]['data_params'][key] = data[key].upper()
            for key, item in json_buy[0]['backtest_params'].items():
                if key in data:
                    json_buy[0]['backtest_params'][key] = data[key].upper()
            with open(BACKTESTER_CFG_BUY, 'w') as f:
                json.dump(json_buy, f, indent=4)
        LOGGER.info(f'Config buy updated!')
        print(f'Config buy updated!')
    elif buy_sell == 'sell':
        with open(BACKTESTER_CFG_SELL) as f:
            json_sell = json.load(f)
            json_sell[0]['rule_id'] = data['rule_id']
            json_sell[0]['rule_side'] = data['rule_side']
            json_sell[0]['rule_name'] = data['rule_name']
            for key, item in json_sell[0]['entry_params'].items():
                if key in data:
                    json_sell[0]['entry_params'][key] = data[key].upper()
            for key, item in json_sell[0]['exit_params'].items():
                if key in data:
                    json_sell[0]['exit_params'][key] = data[key].upper()
            for key, item in json_sell[0]['data_params'].items():
                if key in data:
                    json_sell[0]['data_params'][key] = data[key].upper()
            for key, item in json_sell[0]['backtest_params'].items():
                if key in data:
                    json_sell[0]['backtest_params'][key] = data[key].upper()
            with open(BACKTESTER_CFG_SELL, 'w') as f:
                json.dump(json_sell, f, indent=4)
        LOGGER.info(f'Config sell updated!')
        print(f'Config sell updated!')


# Gets Buy & Sell comments DataFrames
def get_comment_dfs():
    with open(BACKTESTER_CFG_BUY_COMNT) as f:
        json_str = json.load(f)
        header_dict = {"rule_id_comnt": json_str[0]['rule_id_comnt'], "rule_side_comnt": json_str[0]['rule_side_comnt'], "rule_name_comnt": json_str[0]['rule_name_comnt']}
        header_df = pd.DataFrame(header_dict.items(), columns=["Param", "Comment"])
        entry_dict = json_str[0]['entry_params']
        exit__dict = json_str[0]['exit_params']
        data_dict = json_str[0]['data_params']
        backtest_dict = json_str[0]['backtest_params']
        entry_df = pd.DataFrame(entry_dict.items(), columns=["Param", "Comment"])
        exit_df = pd.DataFrame(exit__dict.items(), columns=["Param", "Comment"])
        data_df = pd.DataFrame(data_dict.items(), columns=["Param", "Comment"])
        backtest_df = pd.DataFrame(backtest_dict.items(), columns=["Param", "Comment"])
        buy_dfs = {"Header": header_df, "Entry": entry_df, "Exit": exit_df, "Data": data_df, "Backtest": backtest_df}
    with open(BACKTESTER_CFG_SELL_COMNT) as f:
        json_str = json.load(f)
        header_dict = {"rule_id_comnt": json_str[0]['rule_id_comnt'], "rule_side_comnt": json_str[0]['rule_side_comnt'], "rule_name_comnt": json_str[0]['rule_name_comnt']}
        header_df = pd.DataFrame(header_dict.items(), columns=["Param", "Comment"])
        entry_dict = json_str[0]['entry_params']
        exit__dict = json_str[0]['exit_params']
        data_dict = json_str[0]['data_params']
        backtest_dict = json_str[0]['backtest_params']
        entry_df = pd.DataFrame(entry_dict.items(), columns=["Param", "Comment"])
        exit_df = pd.DataFrame(exit__dict.items(), columns=["Param", "Comment"])
        data_df = pd.DataFrame(data_dict.items(), columns=["Param", "Comment"])
        backtest_df = pd.DataFrame(backtest_dict.items(), columns=["Param", "Comment"])
        sell_dfs = {"Header": header_df, "Entry": entry_df, "Exit": exit_df, "Data": data_df, "Backtest": backtest_df}
    return {"Buy": buy_dfs, "Sell": sell_dfs}


# Update Buy & Sell Comments
def update_comment(buy_sell, data):
    if buy_sell == 'buy':
        with open(BACKTESTER_CFG_BUY_COMNT) as f:
            json_buy = json.load(f)
            json_buy[0]['rule_id_comnt'] = data['rule_id_comnt']
            json_buy[0]['rule_side_comnt'] = data['rule_side_comnt']
            json_buy[0]['rule_name_comnt'] = data['rule_name_comnt']
            for key, item in json_buy[0]['entry_params'].items():
                if key in data:
                    json_buy[0]['entry_params'][key] = data[key]
            for key, item in json_buy[0]['exit_params'].items():
                if key in data:
                    json_buy[0]['exit_params'][key] = data[key]
            for key, item in json_buy[0]['data_params'].items():
                if key in data:
                    json_buy[0]['data_params'][key] = data[key]
            for key, item in json_buy[0]['backtest_params'].items():
                if key in data:
                    json_buy[0]['backtest_params'][key] = data[key]
            with open(BACKTESTER_CFG_BUY_COMNT, 'w') as f:
                json.dump(json_buy, f, indent=4)
        LOGGER.info(f'Comments buy updated!')
        print(f'Comments buy updated!')
    elif buy_sell == 'sell':
        with open(BACKTESTER_CFG_SELL_COMNT) as f:
            json_sell = json.load(f)
            json_sell[0]['rule_id_comnt'] = data['rule_id_comnt']
            json_sell[0]['rule_side_comnt'] = data['rule_side_comnt']
            json_sell[0]['rule_name_comnt'] = data['rule_name_comnt']
            for key, item in json_sell[0]['entry_params'].items():
                if key in data:
                    json_sell[0]['entry_params'][key] = data[key]
            for key, item in json_sell[0]['exit_params'].items():
                if key in data:
                    json_sell[0]['exit_params'][key] = data[key]
            for key, item in json_sell[0]['data_params'].items():
                if key in data:
                    json_sell[0]['data_params'][key] = data[key]
            for key, item in json_sell[0]['backtest_params'].items():
                if key in data:
                    json_sell[0]['backtest_params'][key] = data[key]
            with open(BACKTESTER_CFG_SELL_COMNT, 'w') as f:
                json.dump(json_sell, f, indent=4)
        LOGGER.info(f'Comments sell updated!')
        print(f'Comments sell updated!')


@app.route("/files", methods=['GET', 'POST'])
def files():
    """Endpoint to list files on the server."""
    # files = get_files_details()
    return render_template("files.html", files=files)


# Downloads a file from the server
def download(file_path):
    """Download a file from the server"""
    return send_file(path_or_file=file_path, as_attachment=True)


@app.route("/results", methods=['GET', 'POST'])
def results():
    """Endpoint to list and download files on the server."""
    # files = get_files_details()
    # Our Custom standard form from forms.py
    form = forms.DownloadForm()
    LOGGER.info(f'Results: {request.method}')
    print(f'Results: {request.method}')
    # If POST request has buy or sell, download the file
    if form.validate_on_submit() or form.buy_sell.data in ["backtester_config_buy", "backtester_config_sell"]:
        buy_sell = form.buy_sell.data
        if buy_sell == 'none':
            flash(f'Warning!: No file was selected.', 'warning')
            return render_template('results.html', files=files, form=form)
        path = ''
        if buy_sell == 'backtester_config_buy':
            path = BACKTESTER_CFG_BUY
        elif buy_sell == 'backtester_config_sell':
            path = BACKTESTER_CFG_SELL
        if os.path.isfile(path):
            # download(file_path=path)
            flash(f'Success: File is being downloaded.', 'success')
            # return render_template('results.html', files=files, form=form)
            return send_file(path_or_file=path, as_attachment=True)
        else:
            LOGGER.info(f'Requested file not found! {request.method}')
            print(f'Warning!: Requested file not found. {request.method}, {form.buy_sell.data}')
            flash(f'Warning!: Requested file not found.', 'warning')
            return render_template('results.html', files=files, form=form)
    return render_template('results.html', files=files, form=form)


@app.route('/log')
def log():
    with open(LOG_FILE, "r") as f:
        logs = f.readlines()
        # Get last 10000 lines of logs
        if len(logs) > 10000:
            logs = [log for log in logs[10000:-1]]
    # Display log file content on web-page
    LOGGER.info("route =>'/env' - hit!")
    if request.method == 'GET':
        return render_template('log.html', logs=logs)
    else:
        return logs


@app.route('/env')
def env():
    LOGGER.info("route =>'/env' - hit")
    env = {}
    for k, v in request.environ.items():
        env[k] = str(v)
    LOGGER.info("route =>'/env' [env]:\n%s" % env)
    return render_template('env.html', logs=env)


# handle CSRF error
@app.errorhandler(CSRFError)
def csrf_error(e):
    return e.description, 400


if __name__ == '__main__':
    files = get_files_details()
    app.run(debug=True)
