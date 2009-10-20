#!/usr/bin/env python

import os, sys

# Assume we are run from the galaxy root directory, add lib to the python path
cwd = os.getcwd()
new_path = [ os.path.join( cwd, "lib" ) ]
new_path.extend( sys.path[1:] )
sys.path = new_path

from galaxy import eggs

eggs.require( "nose" )
eggs.require( "NoseHTML" )
eggs.require( "twill==0.9" )
eggs.require( "Paste" )
eggs.require( "PasteDeploy" )
eggs.require( "Cheetah" )

import atexit, logging, os, sys, tempfile
import twill, unittest, time
import os, os.path, subprocess, sys, threading
import httplib
from paste import httpserver
import galaxy.app
from galaxy.app import UniverseApplication
from galaxy.web import buildapp
from galaxy import tools
from galaxy.util import bunch

log = logging.getLogger( "functional_tests.py" )

default_galaxy_test_host = "localhost"
default_galaxy_test_port = "8777"
default_galaxy_locales = 'en'
default_galaxy_test_file_dir = "test-data"

def main():
    
    # ---- Configuration ------------------------------------------------------
    
    galaxy_test_host = os.environ.get( 'GALAXY_TEST_HOST', default_galaxy_test_host )
    galaxy_test_port = os.environ.get( 'GALAXY_TEST_PORT', default_galaxy_test_port )
    if 'HTTP_ACCEPT_LANGUAGE' not in os.environ:
        os.environ['HTTP_ACCEPT_LANGUAGE'] = default_galaxy_locales
    galaxy_test_file_dir = os.environ.get( 'GALAXY_TEST_FILE_DIR', default_galaxy_test_file_dir )
    if not os.path.isabs( galaxy_test_file_dir ):
        galaxy_test_file_dir = os.path.join( os.getcwd(), galaxy_test_file_dir )
    start_server = 'GALAXY_TEST_EXTERNAL' not in os.environ   
    if start_server:
        if 'GALAXY_TEST_DBPATH' in os.environ:
            db_path = os.environ['GALAXY_TEST_DBPATH']
        else: 
            tempdir = tempfile.mkdtemp()
            db_path = os.path.join( tempdir, 'database' )
        file_path = os.path.join( db_path, 'files' )
        try:
            os.makedirs( file_path )
        except OSError:
            pass
        if 'GALAXY_TEST_DBURI' in os.environ:
            database_connection = os.environ['GALAXY_TEST_DBURI']
        else:
            database_connection = 'sqlite:///' + os.path.join( db_path, 'universe.sqlite' )
        if 'GALAXY_TEST_RUNNERS' in os.environ:
            start_job_runners = os.environ['GALAXY_TEST_RUNNERS']
        else:
            start_job_runners = None
        if 'GALAXY_TEST_DEF_RUNNER' in os.environ:
            default_cluster_job_runner = os.environ['GALAXY_TEST_DEF_RUNNER']
        else:
            default_cluster_job_runner = 'local:///'
            
    print "Database connection:", database_connection
    
    # What requires these?        
    os.environ['GALAXY_TEST_HOST'] = galaxy_test_host
    os.environ['GALAXY_TEST_PORT'] = galaxy_test_port
    os.environ['GALAXY_TEST_FILE_DIR'] = galaxy_test_file_dir
            
    # ---- Build Application --------------------------------------------------
       
    app = None
            
    if start_server:
        
        # Build the Universe Application
        app = UniverseApplication( job_queue_workers = 5,
                                   start_job_runners = start_job_runners,
                                   default_cluster_job_runner = default_cluster_job_runner,
                                   id_secret = 'changethisinproductiontoo',
                                   template_path = "templates",
                                   database_connection = database_connection,
                                   file_path = file_path,
                                   tool_config_file = "tool_conf.xml.sample",
                                   datatype_converters_config_file = "datatype_converters_conf.xml.sample",
                                   tool_path = "tools",
                                   tool_parse_help = False,
                                   test_conf = "test.conf",
                                   log_destination = "stdout",
                                   use_heartbeat = False,
                                   allow_user_creation = True,
                                   allow_user_deletion = True,
                                   admin_users = 'test@bx.psu.edu',
                                   library_import_dir = galaxy_test_file_dir,
                                   user_library_import_dir = os.path.join( galaxy_test_file_dir, 'users' ),
                                   global_conf = { "__file__": "universe_wsgi.ini.sample" } )
        
        log.info( "Embedded Universe application started" );
        
    # ---- Run webserver ------------------------------------------------------
    
    server = None
    
    if start_server:
        
        webapp = buildapp.app_factory( dict(), use_translogger = False, app=app )
        server = httpserver.serve( webapp, host=galaxy_test_host, port=galaxy_test_port, start_loop=False )
        t = threading.Thread( target=server.serve_forever )
        t.start()

        # Test if the server is up
        for i in range( 10 ):
            conn = httplib.HTTPConnection( galaxy_test_host, galaxy_test_port )
            conn.request( "GET", "/" )
            if conn.getresponse().status == 200:
                break
            time.sleep( 0.1 )
        else:
            raise Exception( "Test HTTP server did not return '200 OK' after 10 tries" )
            
        log.info( "Embedded web server started" )

    
    # ---- Load toolbox for generated tests -----------------------------------
    
    # We don't add the tests to the path until everything is up and running
    new_path = [ os.path.join( cwd, "test" ) ]
    new_path.extend( sys.path[1:] )
    sys.path = new_path
    
    import functional.test_toolbox
    
    if app:
        # TODO: provisions for loading toolbox from file when using external server
        functional.test_toolbox.toolbox = app.toolbox
    else:
        # FIXME: This doesn't work at all now that toolbox requires an 'app' instance
        #        (to get at datatypes, might just pass a datatype registry directly)
        my_app = bunch.Bunch( datatypes_registry = galaxy.datatypes.registry.Registry() )
        test_toolbox.toolbox = tools.ToolBox( 'tool_conf.xml.test', 'tools', my_app )

    # ---- Find tests ---------------------------------------------------------
    
    log.info( "Functional tests will be run against %s:%s" % ( galaxy_test_host, galaxy_test_port ) )
    
    rval = False
    
    try:
        
        import nose.core
        import nose.config
        import nose.loader
        import nose.plugins.manager
        
        test_config = nose.config.Config( env = os.environ, plugins=nose.plugins.manager.DefaultPluginManager() )
        test_config.configure( sys.argv )
        
        loader = nose.loader.TestLoader( config = test_config )
        
        plug_loader = test_config.plugins.prepareTestLoader( loader )
        if plug_loader is not None:
            loader = plug_loader
        
        tests = loader.loadTestsFromNames( test_config.testNames )
        
        test_runner = nose.core.TextTestRunner(
            stream = test_config.stream,
            verbosity = test_config.verbosity,
            config = test_config)
        
        plug_runner = test_config.plugins.prepareTestRunner( test_runner )
        if plug_runner is not None:
            test_runner = plug_runner
        
        result = test_runner.run( tests )
        
        rval = result.wasSuccessful()
        
    except:
        log.exception( "Failure running tests" )
        
    log.info( "Shutting down" )
    
    # ---- Teardown -----------------------------------------------------------
    
    if server:
        log.info( "Shutting down embedded web server" )
        server.server_close()
        server = None
        log.info( "Embedded web server stopped" )
    if app:
        log.info( "Shutting down app" )
        app.shutdown()
        app = None
        log.info( "Embedded Universe application stopped" )
        
    return rval

if __name__ == "__main__":
    main()
