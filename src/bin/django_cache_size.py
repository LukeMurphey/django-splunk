
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
from modular_input import Field, FieldValidationException, ModularInput

import re
import logging
from logging import handlers
import httplib
import hashlib
import socket
import json
import sys
import time
import os

def setup_logger():
    """
    Setup a logger.
    """
    
    logger = logging.getLogger('web_availability_modular_input')
    logger.propagate = False # Prevent the log messages from being duplicated in the python.log file
    logger.setLevel(logging.INFO)
    
    file_handler = handlers.RotatingFileHandler(make_splunkhome_path(['var', 'log', 'splunk', 'cache_size_modular_input.log']), maxBytes=25000000, backupCount=5)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    file_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    
    return logger

logger = setup_logger()

class PathField(Field):
    """
    Represents a file path.
    """
    
    def to_python(self, value):
        Field.to_python(self, value)
        return value
    
    def to_string(self, value):
        return value

class DurationField(Field):
    """
    The duration field represents a duration as represented by a string such as 1d for a 24 hour period.
    
    The string is converted to an integer indicating the number of seconds.
    """
    
    DURATION_RE = re.compile("(?P<duration>[0-9]+)\s*(?P<units>[a-z]*)", re.IGNORECASE)
    
    MINUTE = 60
    HOUR   = 60 * MINUTE
    DAY    = 24 * HOUR
    WEEK   = 7 * DAY
    
    UNITS = {
             'w'       : WEEK,
             'week'    : WEEK,
             'd'       : DAY,
             'day'     : DAY,
             'h'       : HOUR,
             'hour'    : HOUR,
             'm'       : MINUTE,
             'min'     : MINUTE,
             'minute'  : MINUTE,
             's'       : 1
             }
    
    def to_python(self, value):
        Field.to_python(self, value)
        
        # Parse the duration
        m = DurationField.DURATION_RE.match(value)

        # Make sure the duration could be parsed
        if m is None:
            raise FieldValidationException("The value of '%s' for the '%s' parameter is not a valid duration" % (str(value), self.name))
        
        # Get the units and duration
        d = m.groupdict()
        
        units = d['units']
        
        # Parse the value provided
        try:
            duration = int(d['duration'])
        except ValueError:
            raise FieldValidationException("The duration '%s' for the '%s' parameter is not a valid number" % (d['duration'], self.name))
        
        # Make sure the units are valid
        if len(units) > 0 and units not in DurationField.UNITS:
            raise FieldValidationException("The unit '%s' for the '%s' parameter is not a valid unit of duration" % (units, self.name))
        
        # Convert the units to seconds
        if len(units) > 0:
            return duration * DurationField.UNITS[units]
        else:
            return duration

    def to_string(self, value):        
        return str(value)

class DjangoCacheSize(ModularInput):
    """
    The cache size modular input determines the total size and number of files in the cache.
    """
    
    IGNORE_FILES = ["thumbs.db", ".DS_Store"]
    
    def __init__(self, timeout=30):

        scheme_args = {'title': "Django File Cache Size",
                       'description': "Determines the size of a Django file cache based on the total size and number of files",
                       'use_external_validation': "true",
                       'streaming_mode': "xml",
                       'use_single_instance': "true"}
        
        args = [
                PathField("path", "Django Cache Path", "The path to the directory used by Django for the cache", empty_allowed=False),
                DurationField("interval", "Interval", "The interval defining how often to perform the check; can include time units (e.g. 15m for 15 minutes, 8h for 8 hours)", empty_allowed=False)
                ]
        
        ModularInput.__init__( self, scheme_args, args )
        
        if timeout > 0:
            self.timeout = timeout
        else:
            self.timeout = 5
        
    def output_result(self, path, total_cache_size, number_of_files, stanza, index=None, source=None, sourcetype=None, unbroken=True, close=True, out=sys.stdout ):
        """
        Create a string representing the event.
        
        Argument:
        path -- The path being analyzed
        total_cache_size -- The total size of the cache
        number_of_files -- The number of files
        stanza -- The stanza used for the input
        sourcetype -- The sourcetype
        source -- The source field value
        index -- The index to send the event to
        unbroken -- 
        close -- 
        out -- The stream to send the event to (defaults to standard output)
        """
        
        data = {
                'cache_size': total_cache_size,
                'cache_files': number_of_files,
                'path': path
                }
        
        return self.output_event(data, stanza, index=index, source=source, sourcetype=sourcetype, unbroken=unbroken, close=close, out=out)
        
    def create_event_string(self, data_dict, stanza, sourcetype, source, index, unbroken=False, close=False ):
        """
        Create a string representing the event.
        
        Argument:
        data_dict -- A dictionary containing the fields
        stanza -- The stanza used for the input
        sourcetype -- The sourcetype
        source -- The source field value
        index -- The index to send the event to
        unbroken -- 
        close -- 
        """
        
        # Make the content of the event
        data_str   = ''
        
        for k, v in data_dict.items():
            data_str += ' %s=%s' % (k, v)
        
        # Make the event
        event_dict = {'stanza': stanza,
                      'data' : data_str}
        
        
        if index is not None:
            event_dict['index'] = index
            
        if sourcetype is not None:
            event_dict['sourcetype'] = sourcetype
            
        if source is not None:
            event_dict['source'] = source
        
        event = self._create_event(self.document, 
                                   params=event_dict,
                                   stanza=stanza,
                                   unbroken=False,
                                   close=False)
        
        # If using unbroken events, the last event must have been 
        # added with a "</done>" tag.
        return self._print_event(self.document, event)
        
    def output_event(self, data_dict, stanza, index=None, sourcetype=None, source=None, unbroken=False, close=False, out=sys.stdout ):
        """
        Output the given even so that Splunk can see it.
        
        Arguments:
        data_dict -- A dictionary containing the fields
        stanza -- The stanza used for the input
        sourcetype -- The sourcetype
        source -- The source to use
        index -- The index to send the event to
        unbroken -- 
        close -- 
        out -- The stream to send the event to (defaults to standard output)
        """
        
        output = self.create_event_string(data_dict, stanza, sourcetype, source, index, unbroken, close)
        
        out.write(output)
        out.flush()
        
    @staticmethod
    def get_file_path( checkpoint_dir, stanza ):
        """
        Get the path to the checkpoint file.
        
        Arguments:
        checkpoint_dir -- The directory where checkpoints ought to be saved
        stanza -- The stanza of the input being used
        """
        
        return os.path.join( checkpoint_dir, hashlib.md5(stanza).hexdigest() + ".json" )
        
    @classmethod
    def last_ran( cls, checkpoint_dir, stanza ):
        """
        Determines the date that the analysis was last performed for the given input (denoted by the stanza name).
        
        Arguments:
        checkpoint_dir -- The directory where checkpoints ought to be saved
        stanza -- The stanza of the input being used
        """
        
        fp = None
        
        try:
            fp = open( cls.get_file_path(checkpoint_dir, stanza) )
            checkpoint_dict = json.load(fp)
                
            return checkpoint_dict['last_run']
    
        finally:
            if fp is not None:
                fp.close()
        
    @classmethod
    def needs_another_run(cls, checkpoint_dir, stanza, interval, cur_time=None):
        """
        Determines if the given input (denoted by the stanza name) ought to be executed.
        
        Arguments:
        checkpoint_dir -- The directory where checkpoints ought to be saved
        stanza -- The stanza of the input being used
        interval -- The frequency that the analysis ought to be performed
        cur_time -- The current time (will be automatically determined if not provided)
        """
        
        try:
            last_ran = cls.last_ran(checkpoint_dir, stanza)
            
            return cls.is_expired(last_ran, interval, cur_time)
            
        except IOError as e:
            # The file likely doesn't exist
            return True
        
        except ValueError as e:
            # The file could not be loaded
            return True
        
        # Default return value
        return True
    
    @classmethod
    def save_checkpoint(cls, checkpoint_dir, stanza, last_run):
        """
        Save the checkpoint state.
        
        Arguments:
        checkpoint_dir -- The directory where checkpoints ought to be saved
        stanza -- The stanza of the input being used
        last_run -- The time when the analysis was last performed
        """
        
        fp = None
        
        try:
            fp = open( cls.get_file_path(checkpoint_dir, stanza), 'w' )
            
            d = { 'last_run' : last_run }
            
            json.dump(d, fp)
            
        except Exception:
            logger.exception("Failed to save checkpoint directory") 
            
        finally:
            if fp is not None:
                fp.close()
    
    @staticmethod
    def is_expired( last_run, interval, cur_time=None ):
        """
        Indicates if the last run time is expired based .
        
        Arguments:
        last_run -- The time that the analysis was last done
        interval -- The interval that the analysis ought to be done (as an integer)
        cur_time -- The current time (will be automatically determined if not provided)
        """
        
        if cur_time is None:
            cur_time = time.time()
        
        if (last_run + interval) < cur_time:
            return True
        else:
            return False
        
    @classmethod
    def get_cache_size(cls, path):
        """
        Get the size of a Django file cache.
        
        Argument:
        path -- The path of the Django cache.
        """
        
        logger.debug('Performing cache size analysis, path="%s"', path)
        
        return cls.get_directory_size(path)
    
    @classmethod
    def get_directory_size(cls, path):
        """
        Get the size of a directory.
        
        Argument:
        path -- The path of a directory.
        """
        
        total_size = 0
        number_of_files = 0
        
        for root, directories, files in os.walk(path):
            
            for file in files:
                if file not in cls.IGNORE_FILES:
                    number_of_files = number_of_files + 1
                    file_size_tmp = os.path.getsize( os.path.join(root, file) )
                    total_size = total_size + file_size_tmp
                    
                    logger.debug("File size, %i, %s", file_size_tmp, os.path.join(root, file) )
        
        return total_size, number_of_files
        
    def run(self, stanza, cleaned_params, input_config):
        
        # Make the parameters
        interval   = cleaned_params["interval"]
        path       = cleaned_params["path"]
        sourcetype = "django_file_cache_size"
        index      = cleaned_params["index"]
        source     = stanza
        
        if self.needs_another_run( input_config.checkpoint_dir, stanza, interval ):
            
            # Perform the Django cache file size analysis
            total_size, number_of_files = DjangoCacheSize.get_cache_size(path)
            
            # Send the event
            self.output_result( path, total_size, number_of_files, stanza, index=index, source=source, sourcetype=sourcetype, unbroken=True, close=True )
            
            # Save the checkpoint so that we remember when we last 
            self.save_checkpoint(input_config.checkpoint_dir, stanza, int(time.time()) )
        
if __name__ == '__main__':
    try:
        django_cache_size = DjangoCacheSize()
        django_cache_size.execute()
        sys.exit(0)
    except Exception as e:
        logger.exception("Unhandled exception was caught, this may be due to a defect in the script") # This logs general exceptions that would have been unhandled otherwise (such as coding errors)
        raise e