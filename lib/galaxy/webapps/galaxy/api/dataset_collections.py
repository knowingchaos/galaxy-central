from galaxy import web

from galaxy.web.base.controller import BaseAPIController
from galaxy.web.base.controller import UsesHistoryMixin
from galaxy.web.base.controller import UsesLibraryMixinItems

from galaxy.dataset_collections.util import api_payload_to_create_params


class DatasetCollectionsController(
    BaseAPIController,
    UsesHistoryMixin,
    UsesLibraryMixinItems,
):

    @web.expose_api
    def index( self, trans, **kwd ):
        trans.response.status = 501
        return 'not implemented'

    @web.expose_api
    def create( self, trans, payload, **kwd ):
        """
        * POST /api/dataset_collections:
            create a new dataset collection instance.

        :type   payload: dict
        :param  payload: (optional) dictionary structure containing:
            * collection_type: dataset colltion type to create.
            * instance_type:   Instance type - 'history' or 'library'.
            * name:            the new dataset collections's name
            * datasets:        object describing datasets for collection
        :rtype:     dict
        :returns:   element view of new dataset collection
        """
        # TODO: Error handling...
        create_params = api_payload_to_create_params( payload )
        instance_type = payload.pop( "instance_type", "history" )
        if instance_type == "history":
            history_id = payload.get( 'history_id' )
            history = self.get_history( trans, history_id, check_ownership=True, check_accessible=False )
            create_params[ "parent" ] = history
        elif instance_type == "library":
            folder_id = payload.get( 'folder_id' )
            library_folder = self.get_library_folder( trans, folder_id, check_accessible=True )
            self.check_user_can_add_to_library_item( trans, library_folder, check_accessible=False )
            create_params[ "parent" ] = library_folder
        else:
            trans.status = 501
            return
        dataset_collection_instance = self.__service( trans ).create( trans=trans, **create_params )
        return dataset_collection_instance.to_dict( view='element' )

    @web.expose_api
    def show( self, trans, instance_type, id, **kwds ):
        dataset_collection_instance = self.__service( trans ).get(
            id=id,
            instance_type=instance_type,
        )
        return dataset_collection_instance.to_dict( view='element' )

    def __service( self, trans ):
        service = trans.app.dataset_collections_service
        return service
