
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
import re
import logging
from logging import handlers
import hashlib
import json
import sys
import time
import os

path_to_mod_input_lib = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'modular_input.zip')
sys.path.insert(0, path_to_mod_input_lib)

from modular_input import ModularInput, DurationField, FilePathField

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
                FilePathField("path", "Django Cache Path", "The path to the directory used by Django for the cache", empty_allowed=False, validate_file_existence=False),
                DurationField("interval", "Interval", "The interval defining how often to perform the check; can include time units (e.g. 15m for 15 minutes, 8h for 8 hours)", empty_allowed=False)
                ]

        ModularInput.__init__(self, scheme_args, args, logger_name='cache_size_modular_input', logger_level=logging.DEBUG)
        
        if timeout > 0:
            self.timeout = timeout
        else:
            self.timeout = 5
        
    def output_result(self, path, total_cache_size, number_of_files, stanza, index=None, source=None, sourcetype=None, host=None, unbroken=True, close=True, out=sys.stdout):
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
                'path': path,
                'cache_size': total_cache_size,
                'cache_files': number_of_files,
                }
        
        # Output event with fields
        return self.output_event(data, stanza, index=index, host=host, source=source,
                                 sourcetype=sourcetype, unbroken=unbroken, close=close, out=out)
    @classmethod
    def get_cache_size(cls, path, logger=None):
        """
        Get the size of a Django file cache.
        
        Argument:
        path -- The path of the Django cache.
        """
        
        if logger:
            logger.debug('Performing cache size analysis, path="%s"', path)
        
        return cls.get_directory_size(path)
    
    @classmethod
    def get_directory_size(cls, path, logger=None):
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
                    
                    if logger:
                        logger.debug("File size, %i, %s", file_size_tmp, os.path.join(root, file) )
        
        return total_size, number_of_files
        
    def run(self, stanza, cleaned_params, input_config):
        self.logger.debug("Running")

        # Make the parameters
        interval = cleaned_params["interval"]
        path = cleaned_params["path"]
        sourcetype = cleaned_params.get("sourcetype", "django_file_cache_size")
        index = cleaned_params.get("index", "default")
        source = stanza
        host = cleaned_params.get("host", None)
        
        if self.needs_another_run(input_config.checkpoint_dir, stanza, interval):
            self.logger.debug("needs_another_run")
            # Perform the Django cache file size analysis
            total_size, number_of_files = DjangoCacheSize.get_cache_size(path)
            
            # Send the event
            self.output_result(path, total_size, number_of_files, stanza, host=host, index=index, source=source,
                            sourcetype=sourcetype, unbroken=True, close=True)

            # Get the time that the input last ran
            last_ran = self.last_ran(input_config.checkpoint_dir, stanza)

            # Save the checkpoint so that we remember when we last ran the input
            self.save_checkpoint_data(input_config.checkpoint_dir, stanza,
                                        {
                                            'last_run' : self.get_non_deviated_last_run(last_ran, interval, stanza)
                                        })
        else:
            self.logger.debug("needs_another_run is false")
if __name__ == '__main__':
    try:
        django_cache_size = DjangoCacheSize()
        django_cache_size.execute()
        sys.exit(0)
    except Exception as e:
        # logger.exception("Unhandled exception was caught, this may be due to a defect in the script") # This logs general exceptions that would have been unhandled otherwise (such as coding errors)
        raise e