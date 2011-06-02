'''
This migration script fixes the data corruption caused in the form_values
table (content json field) by migrate script 65.
'''
from sqlalchemy import *
from sqlalchemy.orm import *
from migrate import *
from migrate.changeset import *
from sqlalchemy.exc import *
import binascii

from galaxy.util.json import from_json_string, to_json_string

import logging
log = logging.getLogger( __name__ )

metadata = MetaData( migrate_engine )
db_session = scoped_session( sessionmaker( bind=migrate_engine, autoflush=False, autocommit=True ) )

def _sniffnfix_pg9_hex(value):
    """
    Sniff for and fix postgres 9 hex decoding issue
    """
    try:
        if value[0] == 'x':
            return binascii.unhexlify(value[1:])
        else:
            return value
    except Exception, ex:
        return value

def upgrade():
    print __doc__
    metadata.reflect()
    cmd = "SELECT form_values.id as id, form_values.content as field_values, form_definition.fields as fdfields " \
          + " FROM form_definition, form_values " \
          + " WHERE form_values.form_definition_id=form_definition.id " \
          + " ORDER BY form_values.id"
    result = db_session.execute( cmd )
    corrupted_rows = 0
    for row in result:
        # first check if loading the dict from the json succeeds
        # if that fails, it means that the content field is corrupted.
        try:
            field_values_dict = from_json_string( _sniffnfix_pg9_hex( str( row['field_values'] ) ) )
        except Exception, e:
            corrupted_rows = corrupted_rows + 1
            # content field is corrupted
            fields_list = from_json_string( _sniffnfix_pg9_hex( str( row['fdfields'] ) ) )
            field_values_str = _sniffnfix_pg9_hex( str( row['field_values'] ) )
            try:
                #Encoding errors?  Just to be safe.
                print "Attempting to fix row %s" % row['id']
                print "Prior to replacement: %s" % field_values_str
            except:
                pass
            field_values_dict = {}
            # look for each field name in the values and extract its value (string)
            for index in range( len(fields_list) ):
                field = fields_list[index]
                field_name_key = '"%s": "' % field['name']
                field_index = field_values_str.find( field_name_key )
                if field_index == -1:
                    # if the field name is not present the field values dict then 
                    # inform the admin that this form values cannot be fixed 
                    print "The 'content' field of row 'id' %i does not have the field '%s' in the 'form_values' table and could not be fixed by this migration script." % ( int( field['id'] ), field['name'] )
                else:
                    # check if this is the last field
                    if index == len( fields_list )-1:
                        # since this is the last field, the value string lies between the
                        # field name and the '"}' string at the end, hence len(field_values_str)-2
                        value = field_values_str[ field_index+len( field_name_key ):len( field_values_str )-2 ]
                    else:
                        # if this is not the last field then the value string lies between
                        # this field name and the next field name
                        next_field = fields_list[index+1]
                        next_field_index = field_values_str.find( '", "%s": "' % next_field['name'] )
                        value = field_values_str[ field_index+len( field_name_key ):next_field_index ]
                    # clean up the value string, escape the required quoutes and newline characters
                    value = value.replace( "'", "\''" )\
                                 .replace( '"', '\\\\"' )\
                                 .replace( '\r', "\\\\r" )\
                                 .replace( '\n', "\\\\n" )\
                                 .replace( '\t', "\\\\t" )
                    # add to the new values dict
                    field_values_dict[ field['name'] ] = value
            # update the db
            json_values = to_json_string(field_values_dict)
            cmd = "UPDATE form_values SET content='%s' WHERE id=%i" %( json_values, int( row['id'] ) )
            db_session.execute( cmd )
            try:
                print "Post replacement: %s" % json_values
            except:
                pass
    if corrupted_rows:
        print 'Fixed %i corrupted rows.' % corrupted_rows
    else:
        print 'No corrupted rows found.'

def downgrade():
    pass

