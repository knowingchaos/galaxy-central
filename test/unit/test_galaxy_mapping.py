import unittest
import galaxy.model.mapping as mapping


class MappingTests( unittest.TestCase ):

    def test_annotations( self ):
        model = self.model

        u = model.User( email="annotator@example.com", password="password" )
        self.persist( u )

        def persist_and_check_annotation( annotation_class, **kwds ):
            annotated_association = annotation_class()
            annotated_association.annotation = "Test Annotation"
            annotated_association.user = u
            for key, value in kwds.iteritems():
                setattr(annotated_association, key, value)
            self.persist( annotated_association )
            self.expunge()
            stored_annotation = self.query( annotation_class ).all()[0]
            assert stored_annotation.annotation == "Test Annotation"
            assert stored_annotation.user.email == "annotator@example.com"

        sw = model.StoredWorkflow()
        sw.user = u
        self.persist( sw )
        persist_and_check_annotation( model.StoredWorkflowAnnotationAssociation, stored_workflow=sw )

        workflow = model.Workflow()
        workflow.stored_workflow = sw
        self.persist( workflow )

        ws = model.WorkflowStep()
        ws.workflow = workflow
        self.persist( ws )
        persist_and_check_annotation( model.WorkflowStepAnnotationAssociation, workflow_step=ws )

        h = model.History( name="History for Annotation", user=u)
        self.persist( h )
        persist_and_check_annotation( model.HistoryAnnotationAssociation, history=h )

        d1 = model.HistoryDatasetAssociation( extension="txt", history=h, create_dataset=True, sa_session=model.session )
        self.persist( d1 )
        persist_and_check_annotation( model.HistoryDatasetAssociationAnnotationAssociation, hda=d1 )

        page = model.Page()
        page.user = u
        self.persist( page )
        persist_and_check_annotation( model.PageAnnotationAssociation, page=page )

        visualization = model.Visualization()
        visualization.user = u
        self.persist( visualization )
        persist_and_check_annotation( model.VisualizationAnnotationAssociation, visualization=visualization )

        dataset_collection = model.DatasetCollection(collection_type="pair")
        self.persist( dataset_collection )
        persist_and_check_annotation( model.DatasetCollectionAnnotationAssociation, dataset_collection=dataset_collection )

    def test_ratings( self ):
        model = self.model

        u = model.User( email="rater@example.com", password="password" )
        self.persist( u )

        def persist_and_check_rating( rating_class, **kwds ):
            rating_association = rating_class()
            rating_association.rating = 5
            rating_association.user = u
            for key, value in kwds.iteritems():
                setattr(rating_association, key, value)
            self.persist( rating_association )
            self.expunge()
            stored_annotation = self.query( rating_class ).all()[0]
            assert stored_annotation.rating == 5
            assert stored_annotation.user.email == "rater@example.com"

        sw = model.StoredWorkflow()
        sw.user = u
        self.persist( sw )
        persist_and_check_rating( model.StoredWorkflowRatingAssociation, stored_workflow=sw )

        h = model.History( name="History for Rating", user=u)
        self.persist( h )
        persist_and_check_rating( model.HistoryRatingAssociation, history=h )

        d1 = model.HistoryDatasetAssociation( extension="txt", history=h, create_dataset=True, sa_session=model.session )
        self.persist( d1 )
        persist_and_check_rating( model.HistoryDatasetAssociationRatingAssociation, hda=d1 )

        page = model.Page()
        page.user = u
        self.persist( page )
        persist_and_check_rating( model.PageRatingAssociation, page=page )

        visualization = model.Visualization()
        visualization.user = u
        self.persist( visualization )
        persist_and_check_rating( model.VisualizationRatingAssociation, visualization=visualization )

        dataset_collection = model.DatasetCollection(collection_type="pair")
        self.persist( dataset_collection )
        persist_and_check_rating( model.DatasetCollectionRatingAssociation, dataset_collection=dataset_collection )

    def test_tags( self ):
        model = self.model

        my_tag = model.Tag(name="Test Tag")
        u = model.User( email="tagger@example.com", password="password" )
        self.persist( my_tag, u )

        def tag_and_test( taggable_object, tag_association_class, backref_name ):
            assert len( getattr(self.query( model.Tag ).filter( model.Tag.name == "Test Tag" ).all()[0], backref_name) ) == 0

            tag_association = tag_association_class()
            tag_association.tag = my_tag
            taggable_object.tags = [ tag_association ]
            self.persist( tag_association, taggable_object )

            assert len( getattr(self.query( model.Tag ).filter( model.Tag.name == "Test Tag" ).all()[0], backref_name) ) == 1

        sw = model.StoredWorkflow()
        sw.user = u
        #self.persist( sw )
        tag_and_test( sw, model.StoredWorkflowTagAssociation, "tagged_workflows" )

        h = model.History( name="History for Tagging", user=u)
        tag_and_test( h, model.HistoryTagAssociation, "tagged_histories" )

        d1 = model.HistoryDatasetAssociation( extension="txt", history=h, create_dataset=True, sa_session=model.session )
        tag_and_test( d1, model.HistoryDatasetAssociationTagAssociation, "tagged_history_dataset_associations" )

        page = model.Page()
        page.user = u
        tag_and_test( page, model.PageTagAssociation, "tagged_pages" )

        visualization = model.Visualization()
        visualization.user = u
        tag_and_test( visualization, model.VisualizationTagAssociation, "tagged_visualizations" )

        dataset_collection = model.DatasetCollection(collection_type="pair")
        tag_and_test( dataset_collection, model.DatasetCollectionTagAssociation, "tagged_dataset_collections" )

    def test_collections_in_histories(self):
        model = self.model

        u = model.User( email="mary@example.com", password="password" )
        h1 = model.History( name="History 1", user=u)
        d1 = model.HistoryDatasetAssociation( extension="txt", history=h1, create_dataset=True, sa_session=model.session )
        d2 = model.HistoryDatasetAssociation( extension="txt", history=h1, create_dataset=True, sa_session=model.session )

        c1 = model.DatasetCollection(collection_type="pair", name="HistoryCollectionTest1")
        hc1 = model.HistoryDatasetCollectionAssociation(history=h1, collection=c1)
        dc1 = model.DatasetInstanceDatasetCollectionAssociation(collection=c1, dataset=d1)
        dc2 = model.DatasetInstanceDatasetCollectionAssociation(collection=c1, dataset=d2)

        self.persist( u, h1, d1, d2, c1, hc1, dc1, dc2 )

        loaded_dataset_collection = self.query( model.DatasetCollection ).filter( model.DatasetCollection.name == "HistoryCollectionTest1" ).first()
        self.assertEquals(len(loaded_dataset_collection.datasets), 2)
        assert loaded_dataset_collection.collection_type == "pair"

    def test_collections_in_library_folders(self):
        model = self.model

        u = model.User( email="mary2@example.com", password="password" )
        lf = model.LibraryFolder( name="RootFolder" )
        l = model.Library( name="Library1", root_folder=lf )
        ld1 = model.LibraryDataset( )
        ld2 = model.LibraryDataset( )
        #self.persist( u, l, lf, ld1, ld2, expunge=False )

        ldda1 = model.LibraryDatasetDatasetAssociation( extension="txt", library_dataset=ld1 )
        ldda2 = model.LibraryDatasetDatasetAssociation( extension="txt", library_dataset=ld1 )
        #self.persist(  ld1, ld2, ldda1, ldda2, expunge=False )

        c1 = model.DatasetCollection(collection_type="pair", name="LibraryCollectionTest1")
        dc1 = model.DatasetInstanceDatasetCollectionAssociation(collection=c1, dataset=ldda1)
        dc2 = model.DatasetInstanceDatasetCollectionAssociation(collection=c1, dataset=ldda2)
        self.persist( u, l, lf, ld1, ld2, c1, ldda1, ldda2, dc1, dc2 )

        loaded_dataset_collection = self.query( model.DatasetCollection ).filter( model.DatasetCollection.name == "LibraryCollectionTest1" ).first()
        self.assertEquals(len(loaded_dataset_collection.datasets), 2)
        assert loaded_dataset_collection.collection_type == "pair"

    def test_basic( self ):
        model = self.model

        original_user_count = len( model.session.query( model.User ).all() )

        # Make some changes and commit them
        u = model.User( email="james@foo.bar.baz", password="password" )
        # gs = model.GalaxySession()
        h1 = model.History( name="History 1", user=u)
        #h1.queries.append( model.Query( "h1->q1" ) )
        #h1.queries.append( model.Query( "h1->q2" ) )
        h2 = model.History( name=( "H" * 1024 ) )
        self.persist( u, h1, h2 )
        #q1 = model.Query( "h2->q1" )
        metadata = dict( chromCol=1, startCol=2, endCol=3 )
        d1 = model.HistoryDatasetAssociation( extension="interval", metadata=metadata, history=h2, create_dataset=True, sa_session=model.session )
        #h2.queries.append( q1 )
        #h2.queries.append( model.Query( "h2->q2" ) )
        self.persist( d1 )

        # Check
        users = model.session.query( model.User ).all()
        assert len( users ) == original_user_count + 1
        user = [user for user in users if user.email == "james@foo.bar.baz"][0]
        assert user.email == "james@foo.bar.baz"
        assert user.password == "password"
        assert len( user.histories ) == 1
        assert user.histories[0].name == "History 1"
        hists = model.session.query( model.History ).all()
        hist0 = [history for history in hists if history.name == "History 1"][0]
        hist1 = [history for history in hists if history.name == "H" * 255][0]
        assert hist0.name == "History 1"
        assert hist1.name == ( "H" * 255 )
        assert hist0.user == user
        assert hist1.user is None
        assert hist1.datasets[0].metadata.chromCol == 1
        # The filename test has moved to objecstore
        #id = hist1.datasets[0].id
        #assert hist1.datasets[0].file_name == os.path.join( "/tmp", *directory_hash_id( id ) ) + ( "/dataset_%d.dat" % id )
        # Do an update and check
        hist1.name = "History 2b"
        self.expunge()
        hists = model.session.query( model.History ).all()
        hist0 = [history for history in hists if history.name == "History 1"][0]
        hist1 = [history for history in hists if history.name == "History 2b"][0]
        assert hist0.name == "History 1"
        assert hist1.name == "History 2b"
        # gvk TODO need to ad test for GalaxySessions, but not yet sure what they should look like.

    def test_history_contents( self ):
        model = self.model
        u = model.User( email="contents@foo.bar.baz", password="password" )
        # gs = model.GalaxySession()
        h1 = model.History( name="HistoryContentsHistory1", user=u)

        self.persist( u, h1, expunge=True )

        d1 = self.new_hda( h1, name="1" )
        d2 = self.new_hda( h1, name="2", visible=False )
        d3 = self.new_hda( h1, name="3", deleted=True )
        d4 = self.new_hda( h1, name="4", visible=False, deleted=True )

        def contents_iter_names(**kwds):
            history = model.context.query( model.History ).filter(
                model.History.name == "HistoryContentsHistory1"
            ).first()
            return set( map( lambda hda: hda.name, history.contents_iter( **kwds ) ) )

        assert contents_iter_names() == set( [ "1", "2", "3", "4" ] )
        assert contents_iter_names( deleted=False ) == set( [ "1", "2" ] )
        assert contents_iter_names( visible=True ) == set( [ "1", "3" ] )
        assert contents_iter_names( visible=False ) == set( [ "2", "4" ] )
        assert contents_iter_names( deleted=True, visible=False ) == set( [ "4" ] )

        assert contents_iter_names( ids=[ d1.id, d2.id, d3.id, d4.id ] ) == set( [ "1", "2", "3", "4" ] )
        assert contents_iter_names( ids=[ d1.id, d2.id, d3.id, d4.id ], max_in_filter_length=1 ) == set( [ "1", "2", "3", "4" ] )

        assert contents_iter_names( ids=[ d1.id, d3.id ] ) == set( [ "1", "3" ] )

    def new_hda( self, history, **kwds ):
        return self.persist( self.model.HistoryDatasetAssociation( history=history, create_dataset=True, sa_session=self.model.session, **kwds ), flush=True )

    @classmethod
    def setUpClass(cls):
        # Start the database and connect the mapping
        cls.model = mapping.init( "/tmp", "sqlite:///:memory:", create_tables=True )
        assert cls.model.engine is not None

    @classmethod
    def query( cls, type ):
        return cls.model.session.query( type )

    @classmethod
    def persist(cls, *args, **kwargs):
        session = cls.model.session
        flush = kwargs.get('flush', True)
        for arg in args:
            session.add( arg )
            if flush:
                session.flush()
        if kwargs.get('expunge', not flush):
            cls.expunge()
        return arg  # Return last or only arg.

    @classmethod
    def expunge(cls):
        cls.model.session.flush()
        cls.model.session.expunge_all()


def get_suite():
    suite = unittest.TestSuite()
    suite.addTest( MappingTests( "test_basic" ) )
    return suite
