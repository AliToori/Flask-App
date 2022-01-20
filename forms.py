import json
import os
from flask import Flask, render_template, request, Response, redirect, flash, url_for, jsonify, send_from_directory
from flask_wtf import FlaskForm
from flask_wtf.csrf import CSRFProtect, CSRFError
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import Form, StringField, SubmitField, TextAreaField, BooleanField, SelectField, FormField
from wtforms.validators import DataRequired, Length
from werkzeug.utils import secure_filename
import logging, os, sys, time
from dotenv import load_dotenv
from datetime import datetime, timedelta
import pandas as pd
from pathlib import Path
import excel2json
import hashlib


# Config form
class ConfigForm(FlaskForm):
    """Config form."""
    save_changes = SubmitField('Save changes')
    cancel_changes = SubmitField('Cancel')


# Tester form
class TestForm(FlaskForm):
    """Tester form."""
    buy_sell = SelectField(label='Select file type', validators=[DataRequired()],
                           choices=[('none', 'NONE'),
                                    ('backtester_config_buy', 'BACKTESTER_CFG_BUY'),
                                    ('backtester_config_sell', 'BACKTESTER_CFG_SELL')
                                    ])
    start = SubmitField('START')
    terminate = SubmitField('TERMINATE')


# Download form
class DownloadForm(FlaskForm):
    """Download form."""
    buy_sell = SelectField(label='Select file type', validators=[DataRequired()],
                           choices=[('none', 'NONE'),
                                    ('backtester_config_buy', 'BACKTESTER_CFG_BUY'),
                                    ('backtester_config_sell', 'BACKTESTER_CFG_SELL')
                                    ])
    submit = SubmitField('Submit')


# Rescan form
class RescanForm(FlaskForm):
    """Rescan form."""
    rescan_submit = SubmitField(label='RESCAN', validators=[DataRequired()])
