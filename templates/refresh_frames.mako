## Include JavaScript code to refresh Galaxy application frames as needed.
<%def name="handle_refresh_frames()">
    <%
        if not refresh_frames: return
    %>

    <script type="text/javascript">
    %if 'everything' in refresh_frames:
        parent.location.href="${h.url_for( controller='root' )}";
    %endif
    %if 'masthead' in refresh_frames:
        ## if ( parent.frames && parent.frames.galaxy_masthead ) {
        ##     parent.frames.galaxy_masthead.location.href="${h.url_for( controller='root', action='masthead')}";
        ## }
        ## else if ( parent.parent && parent.parent.frames && parent.parent.frames.galaxy_masthead ) {
        ##     parent.parent.frames.galaxy_masthead.location.href="${h.url_for( controller='root', action='masthead')}";
        ## }
        
        ## Refresh masthead == user changes (backward compatibility)
        if ( parent.user_changed ) {
            %if trans.user:
                parent.user_changed( "${trans.user.email}", ${int( app.config.is_admin_user( trans.user ) )} );
            %else:
                parent.user_changed( null, false );
            %endif
        }
    %endif
    %if 'history' in refresh_frames:
        if ( parent.frames && parent.frames.galaxy_history ) {
            parent.frames.galaxy_history.location.href="${h.url_for( controller='root', action='history')}";
            if ( parent.force_right_panel ) {
                parent.force_right_panel( 'show' );
            }
        }
    %endif
    %if 'tools' in refresh_frames:
        if ( parent.frames && Galaxy.toolPanel ) {
            // FIXME: refreshing the tool menu does not work with new JS-based approach, 
            // but refreshing the tool menu is not used right now, either.

            if ( parent.force_left_panel ) {
                parent.force_left_panel( 'show' );
            }
        }
    %endif
    </script>
</%def>