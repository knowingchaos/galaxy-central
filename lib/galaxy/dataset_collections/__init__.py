from .registry import DatasetCollectionTypesRegistry

from galaxy.exceptions import ItemAccessibilityException
from galaxy.web.base.controller import SharableItemSecurityMixin


class DatasetCollectionsService(object, SharableItemSecurityMixin):
    """
    Abstraction for interfacing with dataset collections instance - ideally abstarcts
    out model and plugin details.
    """

    def __init__( self, app ):
        self.type_registry = DatasetCollectionTypesRegistry(app)
        self.model = app.model
        self.security = app.security

    # Would love it if the following methods didn't require trans, some
    # narrower definition of current user perhaps.
    # Interface UserContext { get_roles, get_user, user_is_admin }???
    def create(
        self,
        trans,
        parent,  # PRECONDITION: security checks on ability to add to parent occurred during load.
        name,
        collection_type,
        dataset_identifiers
    ):
        """
        """
        type_plugin = self.__type_plugin( collection_type )
        dataset_instances = self.__load_dataset_instances( trans, dataset_identifiers )
        dataset_collection = type_plugin.build_collection( dataset_instances )
        dataset_collection.name = name
        if isinstance(parent, self.model.History):
            dataset_collection_instance = self.model.HistoryDatasetCollectionAssociation(
                collection=dataset_collection,
                history=parent,
            )
        elif isinstance(parent, self.model.LibraryFolder):
            dataset_collection_instance = self.model.LibraryDatasetCollectionAssociation(
                collection=dataset_collection,
                folder=parent,
            )
        return self.__persist( dataset_collection_instance )

    def __persist( self, dataset_collection_instance ):
        context = self.model.context
        context.add( dataset_collection_instance )
        context.flush()
        return dataset_collection_instance

    def __load_dataset_instances( self, trans, dataset_identifiers ):
        return dict( [ (key, self.__load_dataset_instance( trans, dataset_identifier ) ) for key, dataset_identifier in  dataset_identifiers.iteritems() ] )

    def __load_dataset_instance( self, trans, dataset_identifier ):
        if not isinstance( dataset_identifier, dict ):
            dataset_identifier = dict( src='hda', id=str( dataset_identifier ) )

        # dateset_identifier is dict {src=hda|ldda, id=<encoded_id>}
        src_type = dataset_identifier.get( 'src', 'hda' )
        encoded_id = dataset_identifier.get( 'id', None )
        if not src_type or not encoded_id:
            raise Exception( "Problem decoding dataset identifier %s" % dataset_identifier )
        decoded_id = self.security.decode_id( encoded_id )
        if src_type == 'hda':
            dataset = self.model.context.query( self.model.HistoryDatasetAssociation ).get( decoded_id )
        elif src_type == 'ldda':
            dataset = self.model.context.query( self.model.LibraryDatasetDatasetAssociation ).get( decoded_id )
        # TODO: Handle security. Tools controller doesn't can can_access if can decode id,
        # is it okay to skip such check here?
        return dataset

    def __type_plugin(self, collection_type):
        return self.type_registry.get( collection_type )

    def get_dataset_collection_instance( self, trans, instance_type, id, **kwds ):
        """
        """
        if instance_type == "history":
            return self.__get_history_collection_instance( self, trans, id, **kwds )
        elif instance_type == "library":
            return self.__get_library_collection_instance( self, trans, id, **kwds )

    def __get_history_collection_instance( self, trans, id, check_ownership=False, check_accessible=True ):
        instance_id = int( self.app.security.decode_id( id ) )
        collection_instance = trans.sa_session.query( trans.app.model.HistoryDatasetCollectionAssociation ).get( instance_id )
        collection_instance = self.security_check( trans, collection_instance.history, check_ownership=check_ownership, check_accessible=check_accessible )
        return collection_instance

    def __get_library_collection_instance( self, trans, id, check_ownership=False, check_accessible=True ):
        if check_ownership:
            raise NotImplemented("Functionality (getting library dataset collection with ownership check) unimplemented.")
        instance_id = int( trans.security.decode_id( id ) )
        collection_instance = trans.sa_session.query( trans.app.model.LibraryDatasetCollectionAssociation ).get( instance_id )
        if check_accessible:
            if not trans.app.security_agent.can_access_library_item( trans.get_current_user_roles(), collection_instance, trans.user ):
                raise ItemAccessibilityException( "LibraryDatasetCollectionAssociation is not accessible to the current user", type='error' )
        return collection_instance
