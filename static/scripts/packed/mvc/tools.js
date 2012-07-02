var BaseModel=Backbone.RelationalModel.extend({defaults:{name:null,hidden:false},show:function(){this.set("hidden",false)},hide:function(){this.set("hidden",true)},is_visible:function(){return !this.attributes.hidden}});var Tool=BaseModel.extend({defaults:{description:null,target:null,inputs:[]},relations:[{type:Backbone.HasMany,key:"inputs",relatedModel:"ToolInput",reverseRelation:{key:"tool",includeInJSON:false}}],urlRoot:galaxy_paths.get("tool_url"),copy:function(b){var c=new Tool(this.toJSON());if(b){var a=new Backbone.Collection();c.get("inputs").each(function(d){if(d.get_samples()){a.push(d)}});c.set("inputs",a)}return c},apply_search_results:function(a){(_.indexOf(a,this.attributes.id)!==-1?this.show():this.hide());return this.is_visible()},set_input_value:function(a,b){this.get("inputs").find(function(c){return c.get("name")===a}).set("value",b)},set_input_values:function(b){var a=this;_.each(_.keys(b),function(c){a.set_input_value(c,b[c])})},run:function(){return this._run()},rerun:function(b,a){return this._run({action:"rerun",target_dataset_id:b.id,regions:a})},get_inputs_dict:function(){var a={};this.get("inputs").each(function(b){a[b.get("name")]=b.get("value")});return a},_run:function(c){var d=_.extend({tool_id:this.id,inputs:this.get_inputs_dict()},c);var b=$.Deferred(),a=new ServerStateDeferred({ajax_settings:{url:this.urlRoot,data:JSON.stringify(d),dataType:"json",contentType:"application/json",type:"POST"},interval:2000,success_fn:function(e){return e!=="pending"}});$.when(a.go()).then(function(e){b.resolve(new DatasetCollection().reset(e))});return b}});var ToolInput=Backbone.RelationalModel.extend({defaults:{name:null,label:null,type:null,value:null,num_samples:5},initialize:function(){this.attributes.html=unescape(this.attributes.html)},copy:function(){return new ToolInput(this.toJSON())},get_samples:function(){var b=this.get("type"),a=null;if(b==="number"){a=d3.scale.linear().domain([this.get("min"),this.get("max")]).ticks(this.get("num_samples"))}else{if(b==="select"){a=_.map(this.get("options"),function(c){return c[0]})}}return a}});var ToolCollection=Backbone.Collection.extend({model:Tool});var ToolPanelLabel=BaseModel.extend({});var ToolPanelSection=BaseModel.extend({defaults:{elems:[],open:false},clear_search_results:function(){_.each(this.attributes.elems,function(a){a.show()});this.show();this.set("open",false)},apply_search_results:function(b){var c=true,a;_.each(this.attributes.elems,function(d){if(d instanceof ToolPanelLabel){a=d;a.hide()}else{if(d instanceof Tool){if(d.apply_search_results(b)){c=false;if(a){a.show()}}}}});if(c){this.hide()}else{this.show();this.set("open",true)}}});var ToolSearch=BaseModel.extend({defaults:{spinner_url:"",search_url:"",visible:true,query:"",results:null},initialize:function(){this.on("change:query",this.do_search)},do_search:function(){var c=this.attributes.query;if(c.length<3){this.set("results",null);return}var b=c+"*";if(this.timer){clearTimeout(this.timer)}$("#search-spinner").show();var a=this;this.timer=setTimeout(function(){$.get(a.attributes.search_url,{query:b},function(d){a.set("results",d);$("#search-spinner").hide()},"json")},200)}});var ToolPanel=Backbone.Collection.extend({url:"/tools",tools:new ToolCollection(),parse:function(a){var b=function(e){var d=e.type;if(d==="tool"){return new Tool(e)}else{if(d==="section"){var c=_.map(e.elems,b);e.elems=c;return new ToolPanelSection(e)}else{if(d==="label"){return new ToolPanelLabel(e)}}}};return _.map(a,b)},initialize:function(a){this.tool_search=a.tool_search;this.tool_search.on("change:results",this.apply_search_results,this);this.on("reset",this.populate_tools,this)},populate_tools:function(){var a=this;a.tools=new ToolCollection();this.each(function(b){if(b instanceof ToolPanelSection){_.each(b.attributes.elems,function(c){if(c instanceof Tool){a.tools.push(c)}})}else{if(b instanceof Tool){a.tools.push(b)}}})},clear_search_results:function(){this.each(function(a){if(a instanceof ToolPanelSection){a.clear_search_results()}else{a.show()}})},apply_search_results:function(){var b=this.tool_search.attributes.results;if(b===null){this.clear_search_results();return}var a=null;this.each(function(c){if(c instanceof ToolPanelLabel){a=c;a.hide()}else{if(c instanceof Tool){if(c.apply_search_results(b)){if(a){a.show()}}}else{a=null;c.apply_search_results(b)}}})}});var BaseView=Backbone.View.extend({initialize:function(){this.model.on("change:hidden",this.update_visible,this);this.update_visible()},update_visible:function(){(this.model.attributes.hidden?this.$el.hide():this.$el.show())}});var ToolLinkView=BaseView.extend({tagName:"div",template:Handlebars.templates.tool_link,render:function(){this.$el.append(this.template(this.model.toJSON()));return this}});var ToolPanelLabelView=BaseView.extend({tagName:"div",className:"toolPanelLabel",render:function(){this.$el.append($("<span/>").text(this.model.attributes.name));return this}});var ToolPanelSectionView=BaseView.extend({tagName:"div",className:"toolSectionWrapper",template:Handlebars.templates.panel_section,initialize:function(){BaseView.prototype.initialize.call(this);this.model.on("change:open",this.update_open,this)},render:function(){this.$el.append(this.template(this.model.toJSON()));var a=this.$el.find(".toolSectionBody");_.each(this.model.attributes.elems,function(b){if(b instanceof Tool){var c=new ToolLinkView({model:b,className:"toolTitle"});c.render();a.append(c.$el)}else{if(b instanceof ToolPanelLabel){var d=new ToolPanelLabelView({model:b});d.render();a.append(d.$el)}else{}}});return this},events:{"click .toolSectionTitle > a":"toggle"},toggle:function(){this.model.set("open",!this.model.attributes.open)},update_open:function(){(this.model.attributes.open?this.$el.children(".toolSectionBody").slideDown("fast"):this.$el.children(".toolSectionBody").slideUp("fast"))}});var ToolSearchView=Backbone.View.extend({tagName:"div",id:"tool-search",className:"bar",template:Handlebars.templates.tool_search,events:{click:"focus_and_select","keyup :input":"query_changed"},render:function(){this.$el.append(this.template(this.model.toJSON()));if(!this.model.is_visible()){this.$el.hide()}return this},focus_and_select:function(){this.$el.find(":input").focus().select()},query_changed:function(){this.model.set("query",this.$el.find(":input").val())}});var ToolPanelView=Backbone.View.extend({tagName:"div",className:"toolMenu",initialize:function(){this.collection.tool_search.on("change:results",this.handle_search_results,this)},render:function(){var a=this;var b=new ToolSearchView({model:this.collection.tool_search});b.render();a.$el.append(b.$el);this.collection.each(function(d){if(d instanceof ToolPanelSection){var c=new ToolPanelSectionView({model:d});c.render();a.$el.append(c.$el)}else{if(d instanceof Tool){var e=new ToolLinkView({model:d,className:"toolTitleNoSection"});e.render();a.$el.append(e.$el)}else{if(d instanceof ToolPanelLabel){var f=new ToolPanelLabelView({model:d});f.render();a.$el.append(f.$el)}}}});a.$el.find("a.tool-link").click(function(f){var d=$(this).attr("class").split(/\s+/)[0],c=a.collection.tools.get(d);a.trigger("tool_link_click",f,c)});return this},handle_search_results:function(){var a=this.collection.tool_search.attributes.results;if(a&&a.length===0){$("#search-no-results").show()}else{$("#search-no-results").hide()}}});var ToolFormView=Backbone.View.extend({className:"toolForm",template:Handlebars.templates.tool_form,render:function(){this.$el.children().remove();this.$el.append(this.template(this.model.toJSON()))}});var IntegratedToolMenuAndView=Backbone.View.extend({className:"toolMenuAndView",initialize:function(){this.tool_panel_view=new ToolPanelView({collection:this.collection});this.tool_form_view=new ToolFormView()},render:function(){this.tool_panel_view.render();this.tool_panel_view.$el.css("float","left");this.$el.append(this.tool_panel_view.$el);this.tool_form_view.$el.hide();this.$el.append(this.tool_form_view.$el);var a=this;this.tool_panel_view.on("tool_link_click",function(c,b){c.preventDefault();a.show_tool(b)})},show_tool:function(b){var a=this;b.fetch().done(function(){a.tool_form_view.model=b;a.tool_form_view.render();a.tool_form_view.$el.show();$("#left").width("650px")})}});