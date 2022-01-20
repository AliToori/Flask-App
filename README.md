# backtester_ui_flask_app
<h3>Flask App: Trading Strategy Backtester</h3>


Usage
-
A detailed guide to launch FlaskApp on a Ubuntu VPS: https://www.digitalocean.com/community/tutorials/how-to-deploy-a-flask-application-on-an-ubuntu-vps

ENV Variables
-
<b>FLASK_APP:</b> Main app name. Defaults to BACKTESTER.

<b>DEBUG:</b> Flask server Debug mode. Defaults to True.

<b>SECRET_KEY:</b> Flask app secret key. Defaults to BACKTESTERSECRETKEY.

<b>WTF_CSRF_SECRET_KEY:</b> CSRF secret key. Defaults to BACKTESTERCSRFSECRETKEY
<b>UPLOAD_FOLDER:</b> The folder where JSON Config files will be uploaded. Defaults to "uploads".

<b>OUTPUT_FOLDER:</b> A folder for keeping output files. Defaults to "output"

<b>CFG_FILENAME_BUY:</b> JSON Config BUY file name. Uploading BUY file is being validated based on this name. Defaults to backtester_config_buy.json

<b>CFG_FILENAME_SELL:</b> JSON Config SELL file name. Upload SELL file is being validated based on this name. Defaults to backtester_config_sell.json

<b>LOG_FILE:</b> Main app log file name. Defaults to app.log

<b>MAIN_PY_COMMAND:</b> Python command to launch your .py file for testing. Defaults to "python main.py". 

<b>DROPZONE_ALLOWED_FILE_TYPE:</b> Uploading file type. Defaults to ".json".

<b>DROPZONE_MAX_FILE_SIZE:</b> Uploading file size in MBs. Defaults to 50. 

<b>DROPZONE_MAX_FILES:</b> Maximum number of files to upload at a time. Defaults to 2.

<b>DROPZONE_TIMEOUT:</b> Uploading file timeout in minutes. Defaults to 5. 


UI Elements
-
<h3>TESTER</h5>

<b>HOME:</b> Tester or Home page 

<b>CONFIG:</b> JSON Config files editor.

<b>RESULTS:</b> Results file downloader.

<b>DOWNLOAD:</b> FIle download button.

<b>UPLOAD:</b> File uploads dropzone and button, works both way.

<b>RESCAN:</b> Files scanning button. Checks for possible changes in the JSON files.

<b>DROPDOWN:</b> Dropdown selector for selecting BUY/SELL files for testing.

<b>START:</b> Test run button.

<b>TERMINATE:</b> Test terminate button.

<h3>CONFIG</h5>

<b>JSON Editor:</b> JSON Config file editor with user comments. 

<b>Param:</b> JSON parameter. 

<b>Value:</b> Parameter's value. 

<b>Comment:</b> Parameter's user comment. 

<b>SAVE CHANGES:</b> Saves possible changes made in the editor.

<b>CANCEL:</b> Cancels possible changes made in the editor.

Note: Parameters' keys are not editable.

<h3>RESULTS</h5>

<b>Files:</b> Available JSON Config files for downloading. 

<b>DROPDOWN:</b> Dropdown selector for selecting BUY/SELL files downloading.

<b>DOWNLOAD:</b> Button for downloading BUY/SELL files.

