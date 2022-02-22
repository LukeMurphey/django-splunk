import unittest
import sys
import os
import time
import shutil
import tempfile
try:
    from StringIO import StringIO ## for Python 2
except ImportError:
    from io import StringIO ## for Python 3

sys.path.append( os.path.join("..", "src", "bin") )

from django_cache_size import DjangoCacheSize
from modular_input import Field, FieldValidationException

class TestDjangoCacheSize(unittest.TestCase):
    
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp( prefix="TestDjangoCacheSize" )
        #os.makedirs(self.tmp_dir)
        
    def tearDown(self):
        shutil.rmtree( self.tmp_dir )
        
    def test_get_file_path(self):
        self.assertEquals( DjangoCacheSize.get_file_path( "/Users/lmurphey/Applications/splunk/var/lib/splunk/modinputs/django_cache_size", "django_cache_size://TextCritical.com"), "/Users/lmurphey/Applications/splunk/var/lib/splunk/modinputs/django_cache_size/bef644ab501c51bd214523fe6fe48599.json")
    
    def test_get_cache_size(self):
        
        total_size, number_of_files = DjangoCacheSize.get_cache_size( "cache_test" )
        
        self.assertEquals(number_of_files, 3)
        self.assertEquals(total_size, 12)
        
    def test_save_checkpoint(self):
        DjangoCacheSize.save_checkpoint(self.tmp_dir, "django_cache_size:///var/webapps/textcritical.com", 100)
        self.assertEquals( DjangoCacheSize.last_ran(self.tmp_dir, "django_cache_size:///var/webapps/textcritical.com"), 100)
        
    def test_is_expired(self):
        self.assertFalse( DjangoCacheSize.is_expired(time.time(), 30) )
        self.assertTrue( DjangoCacheSize.is_expired(time.time() - 31, 30) )
        
    def get_test_dir(self):
        return os.path.dirname(os.path.abspath(__file__))
        
    def test_needs_another_run(self):
        
        # Test case where file does not exist
        self.assertTrue( DjangoCacheSize.needs_another_run( "/Users/lmurphey/Applications/splunk/var/lib/splunk/modinputs/django_cache_size", "django_cache_size://DoesNotExist", 60 ) )
        
        # Test an interval right at the earlier edge
        self.assertFalse( DjangoCacheSize.needs_another_run( os.path.join( self.get_test_dir(), "configs" ), "django_cache_size:///var/webapps/textcritical.com", 60, 1365486765 ) )
        
        # Test an interval at the later edge
        self.assertFalse( DjangoCacheSize.needs_another_run( os.path.join( self.get_test_dir(), "configs" ), "django_cache_size:///var/webapps/textcritical.com", 10, 1365486775 ) )
        
        # Test interval beyond later edge
        self.assertTrue( DjangoCacheSize.needs_another_run( os.path.join( self.get_test_dir(), "configs" ), "django_cache_size:///var/webapps/textcritical.com", 10, 1365486776 ) )
        
    def test_output_result(self):
        cache_size_input = DjangoCacheSize(timeout=3)
        
        path = "cache_test"
        total_size, number_of_files = DjangoCacheSize.get_cache_size( path )
        
        out = StringIO()
        
        cache_size_input.output_result(path, total_size, number_of_files, "stanza", "title", unbroken=True, close=True, out=out)
        
        self.assertTrue(out.getvalue().find("cache_size=12") >= 0)