import ConfigParser
import logging
import os
import re
import tool_shed.util.shed_util_common as suc
from tool_shed.util import import_util
from galaxy.web.form_builder import build_select_field
from galaxy.webapps.tool_shed.model import directory_hash_id

from galaxy import eggs
eggs.require( 'mercurial' )

from mercurial import commands
from mercurial import hg
from mercurial import patch
from mercurial import ui

log = logging.getLogger( __name__ )

VALID_REPOSITORYNAME_RE = re.compile( "^[a-z0-9\_]+$" )

def build_allow_push_select_field( trans, current_push_list, selected_value='none' ):
    options = []
    for user in trans.sa_session.query( trans.model.User ):
        if user.username not in current_push_list:
            options.append( user )
    return build_select_field( trans,
                               objs=options,
                               label_attr='username',
                               select_field_name='allow_push',
                               selected_value=selected_value,
                               refresh_on_change=False,
                               multiple=True )

def change_repository_name_in_hgrc_file( hgrc_file, new_name ):
    config = ConfigParser.ConfigParser()
    config.read( hgrc_file )
    config.read( hgrc_file )
    config.set( 'web', 'name', new_name )
    new_file = open( hgrc_file, 'wb' )
    config.write( new_file )
    new_file.close()

def create_hgrc_file( trans, repository ):
    # At this point, an entry for the repository is required to be in the hgweb.config file so we can call repository.repo_path( trans.app ).
    # Since we support both http and https, we set push_ssl to False to override the default (which is True) in the mercurial api.  The hg
    # purge extension purges all files and directories not being tracked by mercurial in the current repository.  It'll remove unknown files
    # and empty directories.  This is not currently used because it is not supported in the mercurial API.
    repo = hg.repository( suc.get_configured_ui(), path=repository.repo_path( trans.app ) )
    fp = repo.opener( 'hgrc', 'wb' )
    fp.write( '[paths]\n' )
    fp.write( 'default = .\n' )
    fp.write( 'default-push = .\n' )
    fp.write( '[web]\n' )
    fp.write( 'allow_push = %s\n' % repository.user.username )
    fp.write( 'name = %s\n' % repository.name )
    fp.write( 'push_ssl = false\n' )
    fp.write( '[extensions]\n' )
    fp.write( 'hgext.purge=' )
    fp.close()

def create_repository( trans, name, type, description, long_description, user_id, category_ids=[] ):
    # Add the repository record to the database.
    repository = trans.app.model.Repository( name=name,
                                             type=type,
                                             description=description,
                                             long_description=long_description,
                                             user_id=user_id )
    # Flush to get the id.
    trans.sa_session.add( repository )
    trans.sa_session.flush()
    # Determine the repository's repo_path on disk.
    dir = os.path.join( trans.app.config.file_path, *directory_hash_id( repository.id ) )
    # Create directory if it does not exist.
    if not os.path.exists( dir ):
        os.makedirs( dir )
    # Define repo name inside hashed directory.
    repository_path = os.path.join( dir, "repo_%d" % repository.id )
    # Create local repository directory.
    if not os.path.exists( repository_path ):
        os.makedirs( repository_path )
    # Create the local repository.
    repo = hg.repository( suc.get_configured_ui(), repository_path, create=True )
    # Add an entry in the hgweb.config file for the local repository.
    lhs = "repos/%s/%s" % ( repository.user.username, repository.name )
    trans.app.hgweb_config_manager.add_entry( lhs, repository_path )
    # Create a .hg/hgrc file for the local repository.
    create_hgrc_file( trans, repository )
    flush_needed = False
    if category_ids:
        # Create category associations
        for category_id in category_ids:
            category = trans.sa_session.query( trans.model.Category ) \
                                       .get( trans.security.decode_id( category_id ) )
            rca = trans.app.model.RepositoryCategoryAssociation( repository, category )
            trans.sa_session.add( rca )
            flush_needed = True
    if flush_needed:
        trans.sa_session.flush()
    message = "Repository <b>%s</b> has been created." % str( repository.name )
    return repository, message

def create_repository_and_import_archive( trans, repository_archive_dict, import_results_tups ):
    """
    Create a new repository in the tool shed and populate it with the contents of a gzip compressed tar archive that was exported
    as part or all of the contents of a capsule.
    """
    results_message = ''
    name = repository_archive_dict.get( 'name', None )
    username = repository_archive_dict.get( 'owner', None )
    if name is None or username is None:
        results_message += 'Import failed: required repository name <b>%s</b> or owner <b>%s</b> is missing.' % ( str( name ), str( username ))
        import_results_tups.append( ( ( str( name ), str( username ) ), results_message ) )
    else:
        if repository_archive_dict[ 'status' ] is None:
            # The repository does not yet exist in this Tool Shed and the current user is authorized to import
            # the current archive file.
            type = repository_archive_dict.get( 'type', 'unrestricted' )
            description = repository_archive_dict.get( 'description', '' )
            long_description = repository_archive_dict.get( 'long_description', '' )
            # The owner entry in the repository_archive_dict is the public username of the user associated with
            # the exported repository archive.
            user = suc.get_user_by_username( trans.app, username )
            if user is None:
                results_message += 'Import failed: repository owner <b>%s</b> does not have an account in this Tool Shed.' % str( username )
                import_results_tups.append( ( ( str( name ), str( username ) ), results_message ) )
            else:
                user_id = user.id
                # The categories entry in the repository_archive_dict is a list of category names.  If a name does not
                # exist in the current Tool Shed, the category will not be created, so it will not be associated with
                # the repository.
                category_ids = []
                category_names = repository_archive_dict[ 'category_names' ]
                for category_name in category_names:
                    category = suc.get_category_by_name( trans, category_name )
                    if category is None:
                        results_message += 'This Tool Shed does not have the category <b>%s</b> so it will not be associated with this repository.' % \
                            str( category_name )
                    else:
                        category_ids.append( trans.security.encode_id( category.id ) )
                # Create the repository record in the database.
                repository, create_message = create_repository( trans,
                                                                name,
                                                                type,
                                                                description,
                                                                long_description,
                                                                user_id=user_id,
                                                                category_ids=category_ids )
                if create_message:
                    results_message += create_message
                # Populate the new repository with the contents of exported repository archive.
                results_dict = import_util.import_repository_archive( trans, repository, repository_archive_dict )
                import_results_tups.append( ( ( str( name ), str( username ) ), results_message ) )
        else:
            # The repository either already exists in this Tool Shed or the current user is not authorized to create it.
            results_message += 'Import not necessary: repository status for this Tool Shed is: %s.' % str( repository_archive_dict[ 'status' ] )
            import_results_tups.append( ( ( str( name ), str( username ) ), results_message ) )
    return import_results_tups

def validate_repository_name( app, name, user ):
    # Repository names must be unique for each user, must be at least four characters
    # in length and must contain only lower-case letters, numbers, and the '_' character.
    if name in [ 'None', None, '' ]:
        return 'Enter the required repository name.'
    if name in [ 'repos' ]:
        return "The term <b>%s</b> is a reserved word in the tool shed, so it cannot be used as a repository name." % name
    check_existing = suc.get_repository_by_name_and_owner( app, name, user.username )
    if check_existing is not None:
        if check_existing.deleted:
            return 'You have a deleted repository named <b>%s</b>, so choose a different name.' % name
        else:
            return "You already have a repository named <b>%s</b>, so choose a different name." % name
    if len( name ) < 4:
        return "Repository names must be at least 4 characters in length."
    if len( name ) > 80:
        return "Repository names cannot be more than 80 characters in length."
    if not( VALID_REPOSITORYNAME_RE.match( name ) ):
        return "Repository names must contain only lower-case letters, numbers and underscore <b>_</b>."
    return ''
