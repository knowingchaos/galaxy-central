<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/requests/common/common.mako" import="common_javascripts" />
<%namespace file="/requests/common/common.mako" import="render_samples_grid" />
<%namespace file="/requests/common/common.mako" import="render_request_type_sample_form_grids" />

<%def name="stylesheets()">
    ${parent.stylesheets()}
    ${h.css( "library" )}
</%def>

<%def name="javascripts()">
   ${parent.javascripts()}
   ${common_javascripts()}
</%def>

<%
    from galaxy.web.framework.helpers import time_ago

    is_admin = cntrller == 'requests_admin' and trans.user_is_admin()
    is_complete = request.is_complete
    is_submitted = request.is_submitted
    is_unsubmitted = request.is_unsubmitted
    can_add_samples = is_unsubmitted
    can_edit_request = ( is_admin and not request.is_complete ) or request.is_unsubmitted
    can_delete_samples = request.samples and not is_complete
    can_edit_samples = request.samples and ( is_admin or not is_complete )
    can_reject = is_admin and is_submitted
    can_submit = request.samples and is_unsubmitted
    can_undelete = request.deleted
%>

<br/><br/>

<ul class="manage-table-actions">
    %if can_submit:
        <li><a class="action-button" confirm="More samples cannot be added to this request after it is submitted. Click OK to submit." href="${h.url_for( controller='requests_common', action='submit_request', cntrller=cntrller, id=trans.security.encode_id( request.id ) )}">Submit request</a></li>
    %endif
    <li><a class="action-button" id="request-${request.id}-popup" class="menubutton">Request Actions</a></li>
    <div popupmenu="request-${request.id}-popup">
        %if can_undelete:
            <a class="action-button" href="${h.url_for( controller='requests_common', action='undelete_request', cntrller=cntrller, id=trans.security.encode_id( request.id ) )}">Undelete this request</a>
        %endif
        %if can_edit_request:
            <a class="action-button" href="${h.url_for( controller='requests_common', action='edit_basic_request_info', cntrller=cntrller, id=trans.security.encode_id( request.id ) )}">Edit this request</a>
        %endif
        <a class="action-button" href="${h.url_for( controller='requests_common', action='view_request_history', cntrller=cntrller, id=trans.security.encode_id( request.id ) )}">View history</a>
        %if can_reject:
            <a class="action-button" href="${h.url_for( controller='requests_admin', action='reject_request', cntrller=cntrller, id=trans.security.encode_id( request.id ) )}">Reject this request</a>
        %endif
    </div>
</ul>

%if request.is_rejected:
    <p>
        <font color="red"><b>${request.last_comment}</b></font>
    </p>
%endif

%if is_admin and is_submitted and request.samples_without_library_destinations:
    <p>
        <font color="red"><b><i>Select a target data library and folder for a sample before selecting it's datasets to transfer from the sequencer</i></b></font>
    </p>
%endif

%if message:
    ${render_msg( message, status )}
%endif

<div class="toolForm">
    <div class="toolFormTitle">Sequencing request "${request.name}"</div>
    <div class="toolFormBody">
        <div class="form-row">
            <label>Current state:</label>
            <a href="${h.url_for( controller='requests_common', action='view_request_history', cntrller=cntrller, id=trans.security.encode_id( request.id ) )}">${request.state}</a>
            <div style="clear: both"></div>
        </div>
        <div class="form-row">
            <label>Description:</label>
            ${request.desc}
            <div style="clear: both"></div>
        </div>
        <div class="form-row">
            <label>User:</label>
            ${request.user.email}
            <div style="clear: both"></div>
        </div>
        <div class="form-row">
            <label>Sequencer configuration:</label>
            ${request.type.name}
            <div style="clear: both"></div>
        </div>
        <div class="form-row">
            <h4><img src="/static/images/fugue/toggle-expand.png" alt="Show" onclick="showContent(this);" style="cursor:pointer;"/> More</h4>
            <div style="display:none;">
                %for index, rd in enumerate( request_widgets ):
                    <%
                        field_label = rd[ 'label' ]
                        field_value = rd[ 'value' ]
                    %>
                    <div class="form-row">
                        <label>${field_label}:</label>                   
                        ${field_value}     
                    </div>
                    <div style="clear: both"></div>
                %endfor
                <div class="form-row">
                    <label>Date created:</label>
                    ${request.create_time}
                    <div style="clear: both"></div>
                </div>
                <div class="form-row">
                    <label>Last updated:</label>
                    ${time_ago( request.update_time )}
                    <div style="clear: both"></div>
                </div>
                <div class="form-row">
                    <label>Email recipients:</label>
                    <%
                        if request.notification:
                            emails = ', '.join( request.notification[ 'email' ] )
                        else:
                            emails = ''
                    %>
                    ${emails}
                    <div style="clear: both"></div>
                </div>
                <div class="form-row">
                    <label>Send email when state changes to:</label>
                    <%
                        if request.notification:
                            states = []
                            for ss in request.type.states:
                                if ss.id in request.notification[ 'sample_states' ]:
                                    states.append( ss.name )
                            states = ', '.join( states )
                        else:
                            states = ''
                    %>
                    ${states}
                    <div style="clear: both"></div>
                </div>
                %if request.samples and request.is_submitted:
                    <script type="text/javascript">
                        // Updater
                        updater( {${ ",".join( [ '"%s" : "%s"' % ( s.id, s.state.name ) for s in request.samples ] ) }});
                    </script>
                %endif
            </div>
        </div>
    </div>
</div>
<p/>
%if displayable_sample_widgets:
    <%
        grid_header = '<h3>Samples</h3>'
        render_buttons = can_edit_samples
    %>
    ${render_samples_grid( cntrller, request, displayable_sample_widgets=displayable_sample_widgets, action='view_request', editing_samples=False, encoded_selected_sample_ids=[], render_buttons=render_buttons, grid_header=grid_header )}
    ## Render the other grids
    <% trans.sa_session.refresh( request.type.sample_form ) %>
    %for grid_index, grid_name in enumerate( request.type.sample_form.layout ):
        ${render_request_type_sample_form_grids( grid_index, grid_name, request.type.sample_form.grid_fields( grid_index ), displayable_sample_widgets=displayable_sample_widgets, editing_samples=False )}
    %endfor
%else:
    There are no samples.
    %if can_add_samples:
        <ul class="manage-table-actions">
            <li><a class="action-button" href="${h.url_for( controller='requests_common', action='add_sample', cntrller=cntrller, request_id=trans.security.encode_id( request.id ), add_sample_button='Add sample' )}">Add sample</a></li>
        </ul>
    %endif
%endif
