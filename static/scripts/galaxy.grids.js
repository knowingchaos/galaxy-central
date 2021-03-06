// External dependencies (for module management eventually): jQuery, Backbone, underscore

// This is necessary so that, when nested arrays are used in ajax/post/get methods, square brackets ('[]') are
// not appended to the identifier of a nested array.
jQuery.ajaxSettings.traditional = true;

// dependencies
define(['mvc/ui'], function() {

/**
 * A Galaxy grid.
 */
var Grid = Backbone.Model.extend({
    defaults: {
        url_base: '',
        async: false,
        async_ops: [],
        categorical_filters: [],
        filters: {},
        sort_key: null,
        show_item_checkboxes: false,
        advanced_search: false,
        cur_page: 1,
        num_pages: 1,
        operation: undefined,
        item_ids: undefined
    },

    /**
     * Return true if operation can be done asynchronously.
     */
    can_async_op: function(op) {
        return _.indexOf(this.attributes.async_ops, op) !== -1;
    },

    /**
     * Add filtering criterion.
     */
    add_filter: function(key, value, append) {
        // Update URL arg with new condition.            
        if (append) {
            // Update or append value.
            var cur_val = this.attributes.filters[key],
                new_val;
            if (cur_val === null || cur_val === undefined) {
                new_val = value;
            } 
            else if (typeof(cur_val) == "string") {
                if (cur_val == "All") {
                    new_val = value;
                } else {
                    // Replace string with array.
                    var values = [];
                    values[0] = cur_val;
                    values[1] = value;
                    new_val = values;   
                }
            } 
            else {
                // Current value is an array.
                new_val = cur_val;
                new_val.push(value);
            }
            this.attributes.filters[key] = new_val;
        } 
        else {
            // Replace value.
            this.attributes.filters[key] = value;
        }
    },

    /**
     * Remove filtering criterion.
     */
    remove_filter: function(key, condition) {
        var cur_val = this.attributes.filters[key];
        if (cur_val === null || cur_val === undefined) {
            return false;            
        }

        var removed = true;
        if (typeof(cur_val) === "string") {
            if (cur_val == "All") {
                // Unexpected. Throw error?
                removed = false;
            } 
            else {
                // Remove condition.
                delete this.attributes.filters[key];
            }
        }
        else {
            // Filter contains an array of conditions.
            var condition_index = _.indexOf(cur_val, condition);
            if (condition_index !== -1) {
                cur_val.splice(condition_index, 1);
            }
            else {
                removed = false;
            }
        }

        return removed;
    },

    /**
     * Returns URL data for obtaining a new grid.
     */
    get_url_data: function() {
        var url_data = {
            async: this.attributes.async,
            sort: this.attributes.sort_key,
            page: this.attributes.cur_page,
            show_item_checkboxes: this.attributes.show_item_checkboxes,
            advanced_search: this.attributes.advanced_search
        };

        // Add operation, item_ids only if they have values.
        if (this.attributes.operation) {
            url_data.operation = this.attributes.operation;
        }
        if (this.attributes.item_ids) {
            url_data.id = this.attributes.item_ids;
        }

        // Add filter arguments to data, placing "f-" in front of all arguments.
        var self = this;
        _.each(_.pairs(self.attributes.filters), function(k) {
            url_data['f-' + k[0]] = k[1];
        });

        return url_data;
    }
});

// grid view
var GridView = Backbone.View.extend({

    // model
    grid: null,
    
    // Initialize
    initialize: function(grid)
    {
        this.init_grid(grid);
        this.init_grid_controls();
        
        // Initialize text filters to select text on click and use normal font when user is typing.
        $('input[type=text]').each(function() {
            $(this).click(function() { $(this).select(); } )
                   .keyup(function () { $(this).css("font-style", "normal"); });
        });
    },
    
    // Initialize
    init_grid: function(grid)
    {
        this.grid = grid;
        this.init_grid_elements();
    },
    
    // Initialize grid controls
    init_grid_controls: function() {
        // Initialize submit image elements.
        $('.submit-image').each( function() {
            // On mousedown, add class to simulate click.
            $(this).mousedown( function() {
               $(this).addClass('gray-background'); 
            });
            
            // On mouseup, add class to simulate click.
            $(this).mouseup( function() {
               $(this).removeClass('gray-background'); 
            });
        });
        
        // link
        var self = this;
        
        // Initialize sort links.
        $('.sort-link').each( function() {
            $(this).click( function() {
               self.set_sort_condition( $(this).attr('sort_key') );
               return false;
            });
        });
        
        // Initialize categorical filters.
        $('.categorical-filter > a').each( function() {
            $(this).click( function() {
                self.set_categorical_filter( $(this).attr('filter_key'), $(this).attr('filter_val') );
                return false;
            });
        });
        
        // Initialize text filters.
        $('.text-filter-form').each( function() {
            $(this).submit( function() {
                var column_key = $(this).attr('column_key');
                var text_input_obj = $('#input-' + column_key + '-filter');
                var text_input = text_input_obj.val();
                text_input_obj.val('');
                self.add_filter_condition(column_key, text_input);
                return false;
            });
        });
        
        // Initialize autocomplete for text inputs in search UI.
        var t = $("#input-tags-filter");
        if (t.length) {
            t.autocomplete(this.grid.history_tag_autocomplete_url,
                           { selectFirst: false, autoFill: false, highlight: false, mustMatch: false });
        }

        var t2 = $("#input-name-filter");
        if (t2.length) {
            t2.autocomplete(this.grid.history_name_autocomplete_url,
                            { selectFirst: false, autoFill: false, highlight: false, mustMatch: false });
        }
        
        // Initialize standard, advanced search toggles.
        $('.advanced-search-toggle').each( function() {
            $(this).click( function() {
                $('#standard-search').slideToggle('fast');
                $('#advanced-search').slideToggle('fast');
                return false;
            });
        });
    },

    // Initialize grid elements.
    init_grid_elements : function() {
        // Initialize grid selection checkboxes.
        $(".grid").each( function() {
            var checkboxes = $(this).find("input.grid-row-select-checkbox");
            var check_count = $(this).find("span.grid-selected-count");
            var update_checked = function() {
                check_count.text( $(checkboxes).filter(":checked").length );
            };
            
            $(checkboxes).each( function() {
                $(this).change(update_checked);
            });
            update_checked();
        });
        
        // Initialize ratings.
        if ($('.community_rating_star').length !== 0)
            $('.community_rating_star').rating({});

        // get options
        var options = this.grid.attributes;
        var self = this;
        
        //
        // add page click events
        //
        $('.page-link > a').each( function() {
            $(this).click( function() {
               self.set_page( $(this).attr('page_num') );
               return false;
            });
        });
        
        //
        // add inbound/outbound events
        //
        $(".use-inbound").each( function() {
            $(this).click( function(e) {
                self.execute({
                    href : $(this).attr('href'),
                    inbound : true
                });
                return false;
                
            });
        });
        
        $(".use-outbound").each( function() {
            $(this).click( function(e) {
                self.execute({
                    href : $(this).attr('href')
                });
                return false;
            });
        });
        
        //
        // add operation popup menus
        //
        for (var i in options['items'])
        {
            // get identifiers
            var button = $('#grid-' + i + '-popup');
            button.off();
            var popup = new PopupMenu(button);
            
            // load details
            var item = options['items'][i];
            for (var j in options['operations'])
            {
                // get operation details
                var operation = options['operations'][j];
                var operation_id = operation['label'];
                var operation_settings = item['operation_config'][operation_id];
                var encode_id = item['encode_id'];
                
                // check
                if (operation_settings['allowed'] && operation['allow_popup'])
                {
                    // popup configuration
                    var popupConfig =
                    {
                        html : operation['label'],
                        href : operation_settings['url_args'],
                        target : operation_settings['target'],
                        confirmation_text : operation['confirm'],
                        inbound : operation['inbound']
                    };
                    
                    // add popup function
                    popupConfig.func = function(e)
                    {
                        e.preventDefault();
                        var label = $(e.target).html();
                        var options = this.findItemByHtml(label);
                        self.execute(options);
                    };
                    
                    // add item
                    popup.addItem(popupConfig);
                }
            }
        }
    },

    // Add a condition to the grid filter; this adds the condition and refreshes the grid.
    add_filter_condition: function (name, value) {
        // Do nothing is value is empty.
        if (value === "") {
            return false;
        }
        
        // Add condition to grid.
        this.grid.add_filter(name, value, true);
        
        // Add button that displays filter and provides a button to delete it.
        var t = $("<span>" + value + "<a href='javascript:void(0);'><span class='delete-search-icon' /></span></a>");
        t.addClass('text-filter-val');
        var self = this;
        t.click(function() {
            // Remove filter condition.
            self.grid.remove_filter(name, value);

            // Remove visible element.
            $(this).remove();

            self.go_page_one();
            self.execute();
        });
        
        var container = $('#' + name + "-filtering-criteria");
        container.append(t);
        
        this.go_page_one();
        this.execute();
    },

    // Set sort condition for grid.
    set_sort_condition: function (col_key) {
        // Set new sort condition. New sort is col_key if sorting new column; if reversing sort on
        // currently sorted column, sort is reversed.
        var cur_sort = this.grid.get('sort_key');
        var new_sort = col_key;
        if (cur_sort.indexOf(col_key) !== -1) {
            // Reverse sort.
            if (cur_sort.substring(0,1) !== '-') {
                new_sort = '-' + col_key;
            } else { 
                // Sort reversed by using just col_key.
            }
        }
        
        // Remove sort arrows elements.
        $('.sort-arrow').remove();
        
        // Add sort arrow element to new sort column.
        var sort_arrow = (new_sort.substring(0,1) == '-') ? "&uarr;" : "&darr;";
        var t = $("<span>" + sort_arrow + "</span>").addClass('sort-arrow');
        var th = $("#" + col_key + '-header');
        th.append(t);
        
        // Update grid.
        this.grid.set('sort_key', new_sort);
        this.go_page_one();
        this.execute();
    },

    // Set new value for categorical filter.
    set_categorical_filter: function (name, new_value) {
        // Update filter hyperlinks to reflect new filter value.
        var category_filter = this.grid.get('categorical_filters')[name],
            cur_value = this.grid.get('filters')[name];
        var self = this;
        $("." + name + "-filter").each( function() {
            var text = $.trim( $(this).text() );
            var filter = category_filter[text];
            var filter_value = filter[name];
            if (filter_value == new_value) {
                // Remove filter link since grid will be using this filter. It is assumed that
                // this element has a single child, a hyperlink/anchor with text.
                $(this).empty();
                $(this).addClass("current-filter");
                $(this).append(text);
            } else if (filter_value == cur_value) {
                // Add hyperlink for this filter since grid will no longer be using this filter. It is assumed that
                // this element has a single child, a hyperlink/anchor.
                $(this).empty();
                var t = $("<a href='#'>" + text + "</a>");
                t.click(function() {
                    self.set_categorical_filter( name, filter_value );
                });
                $(this).removeClass("current-filter");
                $(this).append(t);
            }
        });
        
        // Update grid.
        this.grid.add_filter(name, new_value);
        this.go_page_one();
        this.execute();
    },

    // Set page to view.
    set_page: function (new_page) {
        // Update page hyperlink to reflect new page.
        var self = this;
        $(".page-link").each( function() {
            var id = $(this).attr('id'),
                page_num = parseInt( id.split("-")[2], 10 ), // Id has form 'page-link-<page_num>
                cur_page = self.grid.get('cur_page'),
                text;
            if (page_num === new_page) {
                // Remove link to page since grid will be on this page. It is assumed that
                // this element has a single child, a hyperlink/anchor with text.
                text = $(this).children().text();
                $(this).empty();
                $(this).addClass("inactive-link");
                $(this).text(text);
            } 
            else if (page_num === cur_page) {
                // Add hyperlink to this page since grid will no longer be on this page. It is assumed that
                // this element has a single child, a hyperlink/anchor.
                text = $(this).text();
                $(this).empty();
                $(this).removeClass("inactive-link");
                var t = $("<a href='#'>" + text + "</a>");
                t.click(function() {
                    self.set_page(page_num);
                });
                $(this).append(t);
            }
        });

        if (new_page === "all") {
            this.grid.set('cur_page', new_page);
        } else {
            this.grid.set('cur_page', parseInt(new_page, 10));
        }
        this.execute();
    },

    // confirmation/submission of operation request
    submit_operation: function (selected_button, confirmation_text)
    {
        // verify in any item is selected
        var number_of_checked_ids = $('input[name="id"]:checked').length;
        if (!number_of_checked_ids > 0)
            return false;
        
        // collect ids
        var operation_name = $(selected_button).val();
        var item_ids = [];
        $('input[name=id]:checked').each(function() {
            item_ids.push( $(this).val() );
        });
        this.execute({
            operation: operation_name,
            id: item_ids,
            confirmation_text: confirmation_text
        });
        
        // return
        return true;
    },
    
    // execute operations and hyperlink requests
    execute: function (options) {
        // get url
        var id = null;
        var href = null;
        var operation = null;
        var confirmation_text = null;
        var inbound = null;

        // check for options
        if (options)
        {
            // get options
            href = options.href;
            operation = options.operation;
            id = options.id;
            confirmation_text = options.confirmation_text;
            inbound = options.inbound;

            // check if input contains the operation tag
            if (href !== undefined && href.indexOf('operation=') != -1) {
                // Get operation, id in hyperlink's href.
                var href_parts = href.split("?");
                if (href_parts.length > 1) {
                    var href_parms_str = href_parts[1];
                    var href_parms = href_parms_str.split("&");
                    for (var index = 0; index < href_parms.length; index++) {
                        if (href_parms[index].indexOf('operation') != -1) {
                            // Found operation parm; get operation value. 
                            operation = href_parms[index].split('=')[1];
                            operation = operation.replace (/\+/g, ' ');
                        } else if (href_parms[index].indexOf('id') != -1) {
                            // Found id parm; get id value.
                            id = href_parms[index].split('=')[1];
                        }
                    }
                }
            }
        }
        
        // check for operation details
        if (operation && id) {
            // show confirmation box
            if (confirmation_text && confirmation_text != '' && confirmation_text != 'None')
                if(!confirm(confirmation_text))
                    return false;

            // use small characters for operation?!
            operation = operation.toLowerCase();

            // Update grid.
            this.grid.set({
                operation: operation,
                item_ids: id
            });

            // Do operation. If operation cannot be performed asynchronously, redirect to location.
            if (this.grid.can_async_op(operation)) {
                this.update_grid();
            } else {
                this.go_to(inbound, '');
            }
            
            // done
            return false;
        }
        
        // check for href details
        if (href)
        {
            this.go_to(inbound, href);
            return false;
        }
        
        // refresh grid
        if (this.grid.get('async')) {
            this.update_grid();
        } else {
            this.go_to(inbound, '');
        }

        // done
        return false;
    },

    // go to url
    go_to: function (inbound, href) {
        // get aysnc status
        var async = this.grid.get('async');
        this.grid.set('async', false);
        
        // get slide status
        advanced_search = $('#advanced-search').is(":visible");
        this.grid.set('advanced_search', advanced_search);
        
        // get default url
        if(!href)
            href = this.grid.get('url_base') + "?" + $.param(this.grid.get_url_data());
            
        // clear grid of transient request attributes.
        this.grid.set({
            operation: undefined,
            item_ids: undefined,
            async: async
        });
        
        if (inbound) {
            // this currently assumes that there is only a single grid shown at a time
            var $div = $('.grid-header').closest('.inbound');
            if ($div.length !== 0) {
                $div.load(href);
                return;
            }
        }
        
        window.location = href;
    },

    // Update grid.
    update_grid: function () {
        // If there's an operation, do POST; otherwise, do GET.
        var method = (this.grid.get('operation') ? "POST" : "GET" );
        $('.loading-elt-overlay').show(); // Show overlay to indicate loading and prevent user actions.
        var self = this;
        $.ajax({
            type: method,
            url: self.grid.get('url_base'),
            data: self.grid.get_url_data(),
            error: function(response) { alert( "Grid refresh failed" );},
            success: function(response_text) {
                // HACK: use a simple string to separate the elements in the
                // response: (1) table body; (2) number of pages in table; and (3) message.
                var parsed_response_text = response_text.split("*****");
                
                // Update grid body and footer.
                $('#grid-table-body').html(parsed_response_text[0]);
                // FIXME: this does not work at all; what's needed is a function
                // that updates page links when number of pages changes.
                $('#grid-table-footer').html(parsed_response_text[1]);
                
                // Trigger custom event to indicate grid body has changed.
                $('#grid-table-body').trigger('update');
               
                // Hide loading overlay.
                $('.loading-elt-overlay').hide();
                
                // Show message if there is one.
                var message = $.trim( parsed_response_text[2] );
                if (message !== "") {
                    $('#grid-message').html( message ).show();
                    setTimeout( function() { $('#grid-message').hide(); }, 5000);
                }
            },
            complete: function() {
                // Clear grid of transient request attributes.
                self.grid.set({
                    operation: undefined,
                    item_ids: undefined
                });
            }
        });    
    },

    check_all_items: function () {
        var chk_all = document.getElementById('check_all'),
            checks = document.getElementsByTagName('input'),
            total = 0,
            i;
        if ( chk_all.checked === true ) {
            for ( i=0; i < checks.length; i++ ) {
                if ( checks[i].name.indexOf( 'id' ) !== -1) {
                   checks[i].checked = true;
                   total++;
                }
            }
        }
        else {
            for ( i=0; i < checks.length; i++ ) {
                if ( checks[i].name.indexOf( 'id' ) !== -1) {
                   checks[i].checked = false;
                }

            }
        }
        this.init_grid_elements();
    },
    
    // Go back to page one; this is useful when a filter is applied.
    go_page_one: function () {
        // Need to go back to page 1 if not showing all.
        var cur_page = this.grid.get('cur_page');
        if (cur_page !== null && cur_page !== undefined && cur_page !== 'all') {
            this.grid.set('cur_page', 1);
        }               
    }
});

return {
    Grid : Grid,
    GridView : GridView
};

});