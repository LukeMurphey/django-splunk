================================================
Overview
================================================

This app provides some views intended to make analyzing the logs from Django apps easier.



================================================
Configuring Django
================================================

You'll need to configure Django in order to create the logs in a format that Splunk for Django accepts. To do so, set a formatter that makes log messages that work with Splunk. You can do this by copying the following into your settings.py file:

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s' #You may need to specify the timezone here. For example: %(asctime)s CST [%(levelname)s] %(name)s: %(message)s
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'null': {
            'level':'DEBUG',
            'class':'django.utils.log.NullHandler',
        },
        'console':{
            'level':'DEBUG',
            'class':'logging.StreamHandler'
        },
        'default': {
            'level':'DEBUG',
            'class':'logging.handlers.RotatingFileHandler',
            'filename': '../var/log/app.log', # Make sure that this path exists, change as necessary
            'maxBytes': 1024*1024*5, # 5 MB
            'backupCount': 5,
            'formatter':'standard',
        }
    },
    'loggers': {
        'django.db': {
            'handlers': ['default'],
            'level': 'DEBUG', # Set this to ERROR on production hosts since the database logs are very verbose
            'propagate': False, 
        },
        '': {
            'handlers': ['default'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'django.request': {
            'handlers': ['default'],
            'level': 'DEBUG', # Set this to ERROR on production hosts if you want to avoid lots of warnings for 404 file-not-found notices
            'propagate': False,
        },
    }
}
This will configure a rotating file handler to the directory ../var/log/app.log. Make sure that this path exists or change it to log to the wherever you would like the log files to exist. Also, make sure to disable propagation of the database logs on production hosts since these logs can be very verbose. 


================================================
Configuring Splunk
================================================

Setup Splunk to monitor the logs files from your Django installation. Make sure to set the sourcetype to "django". See the following page for details on how to monitor files with Splunk:

     http://docs.splunk.com/Documentation/Splunk/latest/Data/MonitorFilesandDirectories


================================================
Getting Support
================================================

Go to the following website if you need support:

     https://github.com/LukeMurphey/django-splunk


================================================
Change History
================================================

+---------+------------------------------------------------------------------------------------------------------------------+
| Version |  Changes                                                                                                         |
+---------+------------------------------------------------------------------------------------------------------------------+
| 0.5     | Initial release                                                                                                  |
|---------|------------------------------------------------------------------------------------------------------------------|
| 0.6     | Added a new overview dashboard, updated the styling, other miscellaneous changes                                 |
|---------|------------------------------------------------------------------------------------------------------------------|
| 0.7     | Updated the overview dashboard to include a messages by severity over time chart                                 |
|         | Combined the table of queries with highest duration with the most common queries table on the database dashboard |
|         | Added parsing of the args field in the database logs                                                             |
|         | Updated the suggested template for the Django configuration                                                      |
|         | Added an improved line-breaker that should ensure events are broken correctly                                    |
|         | The most recent messages list on the overview dashboard now updates correctly with real-time searches            |
|         | Set the colors of the charts to match the content (e.g. critical severity is red)                                |
|         | Fixed issue where modules name with underscores were not being extracted properly                                |
|         | Fixed drill-down on the "messages by severity" panel on the overview dashboard                                   |
|---------|------------------------------------------------------------------------------------------------------------------|
| 0.8     | Renamed the app icon so that it shows up on older versions of Splunk                                             |
|---------|------------------------------------------------------------------------------------------------------------------|
| 0.9     | Updated the README to give an example of using a format string with a timezone specified                         |
|         | Fixed issue where the panel displaying non-web-facing errors would not show results                              |
|---------|------------------------------------------------------------------------------------------------------------------|
| 1.0     | Added extractions for the path that was requested in 404 errors                                                  |
+---------+------------------------------------------------------------------------------------------------------------------+