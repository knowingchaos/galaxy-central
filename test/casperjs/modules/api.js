// =================================================================== module object, exports
/** Creates a new api module object.
 *  @param {SpaceGhost} spaceghost a spaceghost instance
 *  @exported
 */
exports.create = function createAPI( spaceghost, apikey ){
    return new API( spaceghost );
};

/** User object constructor.
 *  @param {SpaceGhost} spaceghost  a spaceghost instance
 *  @param {String} apikey          apikey for use when not using session authentication
 */
var API = function API( spaceghost, apikey ){
    this.spaceghost = spaceghost;
    this.apikey = apikey;

    this.encodedIdExpectedLength = 16;
    this.jQueryLocation = '../../static/scripts/libs/jquery/jquery.js';

    this.configuration = new ConfigurationAPI( this );
    this.histories  = new HistoriesAPI( this );
    this.hdas       = new HDAAPI( this );
    this.tools      = new ToolsAPI( this );
    this.workflows  = new WorkflowsAPI( this );
    this.users      = new UsersAPI( this );
    this.visualizations = new VisualizationsAPI( this );
    this.dataset_collections = new DatasetCollectionsAPI( this );
};
exports.API = API;

API.prototype.toString = function toString(){
    return ( this.spaceghost + '.API:'
        + (( this.apikey )?( this.apikey ):( '(session)' )) );
};

// ------------------------------------------------------------------- APIError
APIError.prototype = new Error();
APIError.prototype.constructor = Error;
/** @class Thrown when Galaxy the API returns an error from a request */
function APIError( msg, status ){
    Error.apply( this, arguments );
    this.name = "APIError";
    this.message = msg;
    this.status = status;
}
API.prototype.APIError = APIError;
exports.APIError = APIError;

/* ------------------------------------------------------------------- TODO:
    can we component-ize this to become the basis for js-based api binding/resource

*/
// =================================================================== INTERNAL
var utils = require( 'utils' );

API.prototype._ajax = function _ajax( url, options ){
    options = options || {};
    options.async = false;

    // PUT data needs to be stringified in jq.ajax and the content changed
    //TODO: server side handling could change this?
    if( ( options.type && [ 'PUT', 'POST' ].indexOf( options.type ) !== -1 )
    &&  ( options.data ) ){
        options.contentType = 'application/json';
        options.data = JSON.stringify( options.data );
    }

    this.ensureJQuery( '../../static/scripts/libs/jquery/jquery.js' );
    var resp = this.spaceghost.evaluate( function( url, options ){
        return jQuery.ajax( url, options );
    }, url, options );
    //this.spaceghost.debug( 'resp: ' + this.spaceghost.jsonStr( resp ) );

    if( resp.status !== 200 ){
        // grrr... this doesn't lose the \n\r\t
        //throw new APIError( resp.responseText.replace( /[\s\n\r\t]+/gm, ' ' ).replace( /"/, '' ) );
        this.spaceghost.debug( 'api error response status code: ' + resp.status );
        throw new APIError( resp.responseText, resp.status );
    }
    return JSON.parse( resp.responseText );
};

// =================================================================== MISC
API.prototype.isEncodedId = function isEncodedId( id ){
    if( typeof id !== 'string' ){ return false; }
    if( id.match( /[g-zG-Z]/ ) ){ return false; }
    return ( id.length === this.encodedIdExpectedLength );
};

// ------------------------------------------------------------------- is type or throw err
API.prototype.ensureId = function ensureId( id ){
    if( !this.isEncodedId( id ) ){
        throw new APIError( 'ID is not a valid encoded id: ' + id );
    }
    return id;
};

API.prototype.ensureObject = function ensureObject( obj ){
    if( !utils.isObject( obj ) ){
        throw new APIError( 'Not a valid object: ' + obj );
    }
    return obj;
};

// ------------------------------------------------------------------- jquery
// using jq for the ajax in this module - that's why these are here
//TODO:?? could go in spaceghost
API.prototype.hasJQuery = function hasJQuery(){
    return this.spaceghost.evaluate( function pageHasJQuery(){
        var has = false;
        try {
            has = typeof ( jQuery + '' ) === 'string';
        } catch( err ){}
        return has;
    });
};

API.prototype.ensureJQuery = function ensureJQuery(){
    if( !this.hasJQuery() ){
        var absLoc = this.spaceghost.options.scriptDir + this.jQueryLocation,
            injected = this.spaceghost.page.injectJs( absLoc );
        if( !injected ){
            throw new APIError( 'Could not inject jQuery' );
        }
    }
};


// =================================================================== CONFIGURATION
var ConfigurationAPI = function ConfigurationAPI( api ){
    this.api = api;
};
ConfigurationAPI.prototype.toString = function toString(){
    return this.api + '.ConfigurationAPI';
};

// -------------------------------------------------------------------
ConfigurationAPI.prototype.urlTpls = {
    index   : 'api/configuration'
};

ConfigurationAPI.prototype.index = function index( deleted ){
    this.api.spaceghost.info( 'configuration.index' );

    return this.api._ajax( this.urlTpls.index, {
        data : {}
    });
};


// =================================================================== HISTORIES
var HistoriesAPI = function HistoriesAPI( api ){
    this.api = api;
};
HistoriesAPI.prototype.toString = function toString(){
    return this.api + '.HistoriesAPI';
};

// -------------------------------------------------------------------
HistoriesAPI.prototype.urlTpls = {
    index   : 'api/histories',
    show    : 'api/histories/%s',
    create  : 'api/histories',
    delete_ : 'api/histories/%s',
    undelete: 'api/histories/deleted/%s/undelete',
    update  : 'api/histories/%s'
};

HistoriesAPI.prototype.index = function index( deleted ){
    this.api.spaceghost.info( 'histories.index: ' + (( deleted )?( 'w deleted' ):( '(wo deleted)' )) );

    deleted = deleted || false;
    return this.api._ajax( this.urlTpls.index, {
        data : { deleted: deleted }
    });
};

HistoriesAPI.prototype.show = function show( id, deleted ){
    this.api.spaceghost.info( 'histories.show: ' + [ id, (( deleted )?( 'w deleted' ):( '' )) ] );

    id = ( id === 'most_recently_used' )?( id ):( this.api.ensureId( id ) );
    deleted = deleted || false;
    return this.api._ajax( utils.format( this.urlTpls.show, id ), {
        data : { deleted: deleted }
    });
};

HistoriesAPI.prototype.create = function create( payload ){
    this.api.spaceghost.info( 'histories.create: ' + this.api.spaceghost.jsonStr( payload ) );

    // py.payload <-> ajax.data
    payload = this.api.ensureObject( payload );
    return this.api._ajax( utils.format( this.urlTpls.create ), {
        type : 'POST',
        data : payload
    });
};

HistoriesAPI.prototype.delete_ = function delete_( id, purge ){
    this.api.spaceghost.info( 'histories.delete: ' + [ id, (( purge )?( '(purge!)' ):( '' )) ] );

    // py.payload <-> ajax.data
    var payload = ( purge )?({ purge: true }):({});
    return this.api._ajax( utils.format( this.urlTpls.delete_, this.api.ensureId( id ) ), {
        type : 'DELETE',
        data : payload
    });
};

HistoriesAPI.prototype.undelete = function undelete( id ){
    //throw ( 'unimplemented' );
    this.api.spaceghost.info( 'histories.undelete: ' + id );

    return this.api._ajax( utils.format( this.urlTpls.undelete, this.api.ensureId( id ) ), {
        type : 'POST'
    });
};

HistoriesAPI.prototype.update = function create( id, payload ){
    this.api.spaceghost.info( 'histories.update: ' + id + ',' + this.api.spaceghost.jsonStr( payload ) );

    // py.payload <-> ajax.data
    id = this.api.ensureId( id );
    payload = this.api.ensureObject( payload );
    url = utils.format( this.urlTpls.update, id );

    return this.api._ajax( url, {
        type : 'PUT',
        data : payload
    });
};


// =================================================================== HDAS
var HDAAPI = function HDAAPI( api ){
    this.api = api;
};
HDAAPI.prototype.toString = function toString(){
    return this.api + '.HDAAPI';
};

// -------------------------------------------------------------------
HDAAPI.prototype.urlTpls = {
    index   : 'api/histories/%s/contents',
    show    : 'api/histories/%s/contents/%s',
    create  : 'api/histories/%s/contents',
    update  : 'api/histories/%s/contents/%s'
};

HDAAPI.prototype.index = function index( historyId, ids ){
    this.api.spaceghost.info( 'hdas.index: ' + [ historyId, ids ] );
    var data = {};
    if( ids ){
        ids = ( utils.isArray( ids ) )?( ids.join( ',' ) ):( ids );
        data.ids = ids;
    }

    return this.api._ajax( utils.format( this.urlTpls.index, this.api.ensureId( historyId ) ), {
        data : data
    });
};

HDAAPI.prototype.show = function show( historyId, id, deleted ){
    this.api.spaceghost.info( 'hdas.show: ' + [ historyId, id, (( deleted )?( 'w/deleted' ):( '' )) ] );

    id = ( id === 'most_recently_used' )?( id ):( this.api.ensureId( id ) );
    deleted = deleted || false;
    return this.api._ajax( utils.format( this.urlTpls.show, this.api.ensureId( historyId ), id ), {
        data : { deleted: deleted }
    });
};

HDAAPI.prototype.create = function create( historyId, payload ){
    this.api.spaceghost.info( 'hdas.create: ' + [ historyId, this.api.spaceghost.jsonStr( payload ) ] );

    // py.payload <-> ajax.data
    payload = this.api.ensureObject( payload );
    return this.api._ajax( utils.format( this.urlTpls.create, this.api.ensureId( historyId ) ), {
        type : 'POST',
        data : payload
    });
};

HDAAPI.prototype.update = function create( historyId, id, payload ){
    this.api.spaceghost.info( 'hdas.update: ' + [ historyId, id, this.api.spaceghost.jsonStr( payload ) ] );

    // py.payload <-> ajax.data
    historyId = this.api.ensureId( historyId );
    id = this.api.ensureId( id );
    payload = this.api.ensureObject( payload );
    url = utils.format( this.urlTpls.update, historyId, id );

    return this.api._ajax( url, {
        type : 'PUT',
        data : payload
    });
};


// =================================================================== TOOLS
var ToolsAPI = function HDAAPI( api ){
    this.api = api;
};
ToolsAPI.prototype.toString = function toString(){
    return this.api + '.ToolsAPI';
};

// -------------------------------------------------------------------
ToolsAPI.prototype.urlTpls = {
    index   : 'api/tools',
    show    : 'api/tools/%s',
    create  : 'api/tools'
};

ToolsAPI.prototype.index = function index( in_panel, trackster ){
    this.api.spaceghost.info( 'tools.index: ' + [ in_panel, trackster ] );
    var data = {};
    // in_panel defaults to true, trackster defaults to false
    if( in_panel !== undefined ){
        data.in_panel = ( in_panel )?( true ):( false );
    }
    if( in_panel !== undefined ){
        data.trackster = ( trackster )?( true ):( false );
    }
    return this.api._ajax( utils.format( this.urlTpls.index ), {
        data : data
    });
};

ToolsAPI.prototype.show = function show( id ){
    this.api.spaceghost.info( 'tools.show: ' + [ id ] );
    var data = {};

    data.io_details = true;

    return this.api._ajax( utils.format( this.urlTpls.show, id ), {
        data : data
    });
};

ToolsAPI.prototype.create = function create( payload ){
    this.api.spaceghost.info( 'tools.create: ' + [ this.api.spaceghost.jsonStr( payload ) ] );

    // py.payload <-> ajax.data
    payload = this.api.ensureObject( payload );
    return this.api._ajax( utils.format( this.urlTpls.create ), {
        type : 'POST',
        data : payload
    });
};


// =================================================================== WORKFLOWS
var WorkflowsAPI = function WorkflowsAPI( api ){
    this.api = api;
};
WorkflowsAPI.prototype.toString = function toString(){
    return this.api + '.WorkflowsAPI';
};

// -------------------------------------------------------------------
WorkflowsAPI.prototype.urlTpls = {
    index   : 'api/workflows',
    show    : 'api/workflows/%s',
    // run a workflow
    create  : 'api/workflows',
    update  : 'api/workflows/%s',

    upload  : 'api/workflows/upload', // POST
    download: 'api/workflows/download/%s' // GET
};

WorkflowsAPI.prototype.index = function index(){
    this.api.spaceghost.info( 'workflows.index: ' + [] );
    var data = {};

    return this.api._ajax( utils.format( this.urlTpls.index ), {
        data : data
    });
};

WorkflowsAPI.prototype.show = function show( id ){
    this.api.spaceghost.info( 'workflows.show: ' + [ id ] );
    var data = {};

    id = ( id === 'most_recently_used' )?( id ):( this.api.ensureId( id ) );
    return this.api._ajax( utils.format( this.urlTpls.show, this.api.ensureId( id ) ), {
        data : data
    });
};

WorkflowsAPI.prototype.create = function create( payload ){
    this.api.spaceghost.info( 'workflows.create: ' + [ this.api.spaceghost.jsonStr( payload ) ] );

    // py.payload <-> ajax.data
    payload = this.api.ensureObject( payload );
    return this.api._ajax( utils.format( this.urlTpls.create ), {
        type : 'POST',
        data : payload
    });
};

WorkflowsAPI.prototype.upload = function create( workflowJSON ){
    this.api.spaceghost.info( 'workflows.upload: ' + [ this.api.spaceghost.jsonStr( workflowJSON ) ] );

    return this.api._ajax( utils.format( this.urlTpls.upload ), {
        type : 'POST',
        data : { 'workflow': this.api.ensureObject( workflowJSON ) }
    });
};


// =================================================================== USERS
var UsersAPI = function UsersAPI( api ){
    this.api = api;
};
UsersAPI.prototype.toString = function toString(){
    return this.api + '.UsersAPI';
};

// -------------------------------------------------------------------
//NOTE: lots of admin only functionality in this section
UsersAPI.prototype.urlTpls = {
    index   : 'api/users',
    show    : 'api/users/%s',
    create  : 'api/users',
    delete_ : 'api/users/%s',
    undelete: 'api/users/deleted/%s/undelete',
    update  : 'api/users/%s'
};

UsersAPI.prototype.index = function index( deleted ){
    this.api.spaceghost.info( 'users.index: ' + (( deleted )?( 'w deleted' ):( '(wo deleted)' )) );

    deleted = deleted || false;
    return this.api._ajax( this.urlTpls.index, {
        data : { deleted: deleted }
    });
};

UsersAPI.prototype.show = function show( id, deleted ){
    this.api.spaceghost.info( 'users.show: ' + [ id, (( deleted )?( 'w deleted' ):( '' )) ] );

    id = ( id === 'current' )?( id ):( this.api.ensureId( id ) );
    deleted = deleted || false;
    return this.api._ajax( utils.format( this.urlTpls.show, id ), {
        data : { deleted: deleted }
    });
};

UsersAPI.prototype.create = function create( payload ){
    this.api.spaceghost.info( 'users.create: ' + this.api.spaceghost.jsonStr( payload ) );

    // py.payload <-> ajax.data
    payload = this.api.ensureObject( payload );
    return this.api._ajax( utils.format( this.urlTpls.create ), {
        type : 'POST',
        data : payload
    });
};

UsersAPI.prototype.delete_ = function delete_( id, purge ){
    this.api.spaceghost.info( 'users.delete: ' + [ id, (( purge )?( '(purge!)' ):( '' )) ] );

    // py.payload <-> ajax.data
    var payload = ( purge )?({ purge: true }):({});
    return this.api._ajax( utils.format( this.urlTpls.delete_, this.api.ensureId( id ) ), {
        type : 'DELETE',
        data : payload
    });
};

UsersAPI.prototype.undelete = function undelete( id ){
    //throw ( 'unimplemented' );
    this.api.spaceghost.info( 'users.undelete: ' + id );

    return this.api._ajax( utils.format( this.urlTpls.undelete, this.api.ensureId( id ) ), {
        type : 'POST'
    });
};

UsersAPI.prototype.update = function create( id, payload ){
    this.api.spaceghost.info( 'users.update: ' + id + ',' + this.api.spaceghost.jsonStr( payload ) );

    // py.payload <-> ajax.data
    id = this.api.ensureId( id );
    payload = this.api.ensureObject( payload );
    url = utils.format( this.urlTpls.update, id );

    return this.api._ajax( url, {
        type : 'PUT',
        data : payload
    });
};


// =================================================================== HISTORIES
var VisualizationsAPI = function VisualizationsAPI( api ){
    this.api = api;
};
VisualizationsAPI.prototype.toString = function toString(){
    return this.api + '.VisualizationsAPI';
};

// -------------------------------------------------------------------
VisualizationsAPI.prototype.urlTpls = {
    index   : 'api/visualizations',
    show    : 'api/visualizations/%s',
    create  : 'api/visualizations',
    //delete_ : 'api/visualizations/%s',
    //undelete: 'api/visualizations/deleted/%s/undelete',
    update  : 'api/visualizations/%s'
};

VisualizationsAPI.prototype.index = function index(){
    this.api.spaceghost.info( 'visualizations.index' );

    return this.api._ajax( this.urlTpls.index );
};

VisualizationsAPI.prototype.show = function show( id ){
    this.api.spaceghost.info( 'visualizations.show' );

    return this.api._ajax( utils.format( this.urlTpls.show, this.api.ensureId( id ) ) );
};

VisualizationsAPI.prototype.create = function create( payload ){
    this.api.spaceghost.info( 'visualizations.create: ' + this.api.spaceghost.jsonStr( payload ) );

    // py.payload <-> ajax.data
    payload = this.api.ensureObject( payload );
    return this.api._ajax( utils.format( this.urlTpls.create ), {
        type : 'POST',
        data : payload
    });
};

VisualizationsAPI.prototype.update = function create( id, payload ){
    this.api.spaceghost.info( 'visualizations.update: ' + id + ',' + this.api.spaceghost.jsonStr( payload ) );

    // py.payload <-> ajax.data
    id = this.api.ensureId( id );
    payload = this.api.ensureObject( payload );
    url = utils.format( this.urlTpls.update, id );

    return this.api._ajax( url, {
        type : 'PUT',
        data : payload
    });
};

// =================================================================== DATASET COLLECTIONS
var DatasetCollectionsAPI = function DatasetCollectionsAPI( api ){
    this.api = api;
};
DatasetCollectionsAPI.prototype.toString = function toString(){
    return this.api + '.DatasetCollectionsAPI';
};

// -------------------------------------------------------------------
DatasetCollectionsAPI.prototype.urlTpls = {
    create  : 'api/dataset_collections',
};

DatasetCollectionsAPI.prototype.create = function create( payload ){
    this.api.spaceghost.info( 'dataset_collections.create: ' + this.api.spaceghost.jsonStr( payload ) );

    // py.payload <-> ajax.data
    payload = this.api.ensureObject( payload );
    return this.api._ajax( utils.format( this.urlTpls.create ), {
        type : 'POST',
        data : payload
    });
};
