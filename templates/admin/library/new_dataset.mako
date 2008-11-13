<%inherit file="/base.mako"/>

<% import os %>

%if msg:
    <p class="ok_bgr">${msg}</p></td></tr>
%endif

<div class="toolForm" id="new_dataset">
    <div class="toolFormTitle">Create a new library dataset</div>
    <div class="toolFormBody">
        <form name="tool_form" action="${h.url_for( controller='admin', action='dataset' )}" enctype="multipart/form-data" method="post">
            <input type="hidden" name="folder_id" value="${folder_id}">
            <div class="form-row">
                <label>File:</label>
                <div style="float: left; width: 250px; margin-right: 10px;">
                    <input type="file" name="file_data">
                </div>
                <div class="toolParamHelp" style="clear: both;">
                    Upload a single file.  Use the "Server Directory" feature below to upload an entire directory of files.
                </div>
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <label>URL/Text:</label>
                <div style="float: left; width: 250px; margin-right: 10px;">
                    <textarea name="url_paste" rows="5" cols="35"></textarea>
                </div>
                <div class="toolParamHelp" style="clear: both;">
                    Specify a list of URLs (one per line) or paste the contents of a file.
                </div>
                <div style="clear: both"></div>
            </div>
            %if trans.app.config.library_import_dir is not None:
                <div class="form-row">
                    <label>Server Directory</label>
                    <div style="float: left; width: 250px; margin-right: 10px;">
                        <select name="server_dir">
                            <option>None</option>
                            %for dir in os.listdir( trans.app.config.library_import_dir ):
                                <option>${dir}</option>
                            %endfor
                        </select>
                    </div>
                    <div class="toolParamHelp" style="clear: both;">
                        Upload all files in a subdirectory of <strong>${trans.app.config.library_import_dir}</strong> on the Galaxy server.
                    </div>
                    <div style="clear: both"></div>
                </div>
            %endif
            <div class="form-row">
                <label>Convert spaces to tabs:</label>
                <div style="float: left; width: 250px; margin-right: 10px;">
                    <div>
                        <input type="checkbox" name="space_to_tab" value="Yes">Yes
                    </div>
                </div>
                <div class="toolParamHelp" style="clear: both;">
                    Use this option if you are manually entering intervals.
                </div>
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <label>File Format:</label>
                <div style="float: left; width: 250px; margin-right: 10px;">
                    <select name="extension">
                        <option value="auto" selected>Auto-detect</option>
                        %for file_format in file_formats:
                            <option value="${file_format}">${file_format}</option>
                        %endfor
                    </select>
                </div>
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <label>Genome:</label>
                <div style="float: left; width: 250px; margin-right: 10px;">
                    <select name="dbkey">
                        %for dbkey in dbkeys:
                            %if dbkey[1] == last_used_build:
                                <option value="${dbkey[1]}" selected>${dbkey[0]}</option>
                            %else:
                                <option value="${dbkey[1]}">${dbkey[0]}</option>
                            %endif
                        %endfor
                    </select>
                </div>
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <div style="float: left; width: 250px; margin-right: 10px;">
                    <label>Restrict dataset access to specific roles:</label>
                    <select name="roles" multiple="true" size="5">
                        %for role in roles:
                            <option value="${role.id}">${role.name}</option>
                        %endfor
                    </select>
                </div>
                <div class="toolParamHelp" style="clear: both;">
                    Multi-select list - hold the appropriate key while clicking to select multiple roles.  More restrictions can be applied after the upload is complete.  Selecting no roles makes a dataset public.
                </div>
            </div>
            <div style="clear: both"></div>
            <div class="form-row">
                <input type="submit" class="primary-button" name="new_dataset_button" value="Add Dataset(s) to Folder">
            </div>
        </form>
    </div>
</div>
