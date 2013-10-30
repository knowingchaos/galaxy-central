define(["mvc/history/history-model","mvc/dataset/hda-base","mvc/dataset/hda-edit"],function(d,b,a){var c=Backbone.View.extend(LoggableMixin).extend({HDAView:a.HDAEditView,tagName:"div",className:"history-panel",fxSpeed:400,events:{"click .icon-button.tags":"loadAndDisplayTags","click .message-container":"clearMessages"},datasetsSelector:".datasets-list",emptyMsgSelector:".empty-history-message",msgsSelector:".message-container",initialize:function(e){e=e||{};if(e.logger){this.logger=e.logger}this.log(this+".initialize:",e);this._setUpListeners();this.hdaViews={};this.indicator=new LoadingIndicator(this.$el);if(this.model){this._setUpWebStorage(e.initiallyExpanded,e.show_deleted,e.show_hidden);this._setUpModelEventHandlers()}if(e.onready){e.onready.call(this)}},_setUpListeners:function(){this.on("error",function(f,i,e,h,g){this.errorHandler(f,i,e,h,g)});this.on("loading-history",function(){this.showLoadingIndicator("loading history...")});this.on("loading-done",function(){this.hideLoadingIndicator()});this.once("rendered",function(){this.trigger("rendered:initial",this);return false});this.on("switched-history current-history new-history",function(){if(_.isEmpty(this.hdaViews)){this.trigger("empty-history",this)}});if(this.logger){this.on("all",function(e){this.log(this+"",arguments)},this)}},errorHandler:function(g,j,f,i,h){var e=this._parseErrorMessage(g,j,f,i,h);if(j&&j.status===0&&j.readyState===0){}else{if(j&&j.status===502){}else{if(!this.$el.find(this.msgsSelector).is(":visible")){this.once("rendered",function(){this.displayMessage("error",e.message,e.details)})}else{this.displayMessage("error",e.message,e.details)}}}},_parseErrorMessage:function(h,l,g,k,j){var f=Galaxy.currUser,e={message:this._bePolite(k),details:{user:(f instanceof User)?(f.toJSON()):(f+""),source:(h instanceof Backbone.Model)?(h.toJSON()):(h+""),xhr:l,options:(l)?(_.omit(g,"xhr")):(g)}};_.extend(e.details,j||{});if(l&&_.isFunction(l.getAllResponseHeaders)){var i=l.getAllResponseHeaders();i=_.compact(i.split("\n"));i=_.map(i,function(m){return m.split(": ")});e.details.xhr.responseHeaders=_.object(i)}return e},_bePolite:function(e){e=e||_l("An error occurred while getting updates from the server");return e+". "+_l("Please contact a Galaxy administrator if the problem persists.")},loadCurrentHistory:function(f){var e=this;return this.loadHistoryWithHDADetails("current",f).then(function(h,g){e.trigger("current-history",e)})},switchToHistory:function(h,g){var e=this,f=function(){return jQuery.post(galaxy_config.root+"api/histories/"+h+"/set_as_current")};return this.loadHistoryWithHDADetails(h,g,f).then(function(j,i){e.trigger("switched-history",e)})},createNewHistory:function(g){var e=this,f=function(){return jQuery.post(galaxy_config.root+"api/histories",{current:true})};return this.loadHistory(undefined,g,f).then(function(i,h){e.trigger("new-history",e)})},loadHistoryWithHDADetails:function(h,g,f,j){var e=this,i=function(k){return e.getExpandedHdaIds(k.id)};return this.loadHistory(h,g,f,j,i)},loadHistory:function(h,g,f,k,i){this.trigger("loading-history",this);g=g||{};var e=this;var j=d.History.getHistoryData(h,{historyFn:f,hdaFn:k,hdaDetailIds:g.initiallyExpanded||i});return this._loadHistoryFromXHR(j,g).fail(function(n,l,m){e.trigger("error",e,n,g,_l("An error was encountered while "+l),{historyId:h,history:m||{}})}).always(function(){e.trigger("loading-done",e)})},_loadHistoryFromXHR:function(g,f){var e=this;g.then(function(h,i){e.setModel(h,i,f)});g.fail(function(i,h){e.render()});return g},setModel:function(g,e,f){f=f||{};if(this.model){this.model.clearUpdateTimeout();this.stopListening(this.model);this.stopListening(this.model.hdas)}this.hdaViews={};if(Galaxy&&Galaxy.currUser){g.user=Galaxy.currUser.toJSON()}this.model=new d.History(g,e,f);this._setUpWebStorage(f.initiallyExpanded,f.show_deleted,f.show_hidden);this._setUpModelEventHandlers();this.trigger("new-model",this);this.render();return this},refreshHdas:function(f,e){if(this.model){return this.model.refresh(f,e)}return $.when()},_setUpWebStorage:function(f,e,g){this.storage=new PersistentStorage(this._getStorageKey(this.model.get("id")),{expandedHdas:{},show_deleted:false,show_hidden:false});this.log(this+" (prev) storage:",JSON.stringify(this.storage.get(),null,2));if(f){this.storage.set("exandedHdas",f)}if((e===true)||(e===false)){this.storage.set("show_deleted",e)}if((g===true)||(g===false)){this.storage.set("show_hidden",g)}this.show_deleted=this.storage.get("show_deleted");this.show_hidden=this.storage.get("show_hidden");this.trigger("new-storage",this.storage,this);this.log(this+" (init'd) storage:",this.storage.get())},_getStorageKey:function(e){if(!e){throw new Error("_getStorageKey needs valid id: "+e)}return("history:"+e)},clearWebStorage:function(){for(var e in sessionStorage){if(e.indexOf("history:")===0){sessionStorage.removeItem(e)}}},getStoredOptions:function(f){if(!f||f==="current"){return(this.storage)?(this.storage.get()):({})}var e=sessionStorage.getItem(this._getStorageKey(f));return(e===null)?({}):(JSON.parse(e))},getExpandedHdaIds:function(e){var f=this.getStoredOptions(e).expandedHdas;return((_.isEmpty(f))?([]):(_.keys(f)))},_setUpModelEventHandlers:function(){this.model.on("error error:hdas",function(f,h,e,g){this.errorHandler(f,h,e,g)},this);this.model.on("change:nice_size",this.updateHistoryDiskSize,this);if(Galaxy&&Galaxy.quotaMeter){this.listenTo(this.model,"change:nice_size",function(){Galaxy.quotaMeter.update()})}this.model.hdas.on("add",this.addHdaView,this);this.model.hdas.on("change:deleted",this.handleHdaDeletionChange,this);this.model.hdas.on("change:visible",this.handleHdaVisibleChange,this);this.model.hdas.on("change:purged",function(e){this.model.fetch()},this);this.model.hdas.on("state:ready",function(f,g,e){if((!f.get("visible"))&&(!this.storage.get("show_hidden"))){this.removeHdaView(this.hdaViews[f.id])}},this)},addHdaView:function(h){this.log("add."+this,h);var f=this;if(!h.isVisible(this.storage.get("show_deleted"),this.storage.get("show_hidden"))){return}$({}).queue([function g(j){var i=f.$el.find(f.emptyMsgSelector);if(i.is(":visible")){i.fadeOut(f.fxSpeed,j)}else{j()}},function e(j){f.scrollToTop();var i=f.$el.find(f.datasetsSelector);f.createHdaView(h).$el.hide().prependTo(i).slideDown(f.fxSpeed)}])},createHdaView:function(g){var f=g.get("id"),e=this.storage.get("expandedHdas").get(f),h=new this.HDAView({model:g,expanded:e,hasUser:this.model.hasUser(),logger:this.logger});this._setUpHdaListeners(h);this.hdaViews[f]=h;return h.render()},_setUpHdaListeners:function(f){var e=this;f.on("body-expanded",function(g){e.storage.get("expandedHdas").set(g,true)});f.on("body-collapsed",function(g){e.storage.get("expandedHdas").deleteKey(g)});f.on("error",function(h,j,g,i){e.errorHandler(h,j,g,i)})},handleHdaDeletionChange:function(e){if(e.get("deleted")&&!this.storage.get("show_deleted")){this.removeHdaView(this.hdaViews[e.id])}},handleHdaVisibleChange:function(e){if(e.hidden()&&!this.storage.get("show_hidden")){this.removeHdaView(this.hdaViews[e.id])}},removeHdaView:function(f){if(!f){return}var e=this;f.$el.fadeOut(e.fxSpeed,function(){f.off();f.remove();delete e.hdaViews[f.model.id];if(_.isEmpty(e.hdaViews)){e.$el.find(e.emptyMsgSelector).fadeIn(e.fxSpeed,function(){e.trigger("empty-history",e)})}})},render:function(g){var e=this,f;if(this.model){f=this.renderModel()}else{f=this.renderWithoutModel()}$(e).queue("fx",[function(h){if(e.$el.is(":visible")){e.$el.fadeOut(e.fxSpeed,h)}else{h()}},function(h){e.$el.empty();if(f){e.$el.append(f.children())}e.$el.fadeIn(e.fxSpeed,h)},function(h){e._setUpBehaviours();if(g){g.call(this)}e.trigger("rendered",this)}]);return this},renderModel:function(){var e=$("<div/>");var f=(!Galaxy.currUser.isAnonymous())?(c.templates.historyPanel):(c.templates.anonHistoryPanel);e.append(f(this.model.toJSON()));e.find("[title]").tooltip({placement:"bottom"});if(!this.model.hdas.length||!this.renderItems(e.find(this.datasetsSelector))){e.find(this.emptyMsgSelector).show()}return e},renderWithoutModel:function(){var e=$("<div/>"),f=$("<div/>").addClass("message-container").css({"margin-left":"4px","margin-right":"4px"});return e.append(f)},renderItems:function(f){this.hdaViews={};var e=this,g=this.model.hdas.getVisible(this.storage.get("show_deleted"),this.storage.get("show_hidden"));_.each(g,function(h){f.prepend(e.createHdaView(h).$el)});return g.length},_setUpBehaviours:function(){if(!this.model||!Galaxy.currUser||Galaxy.currUser.isAnonymous()){return}var e=this,f=this.$el.find(".history-controls .annotation-display");this.$el.find(".history-controls .icon-button.annotate").click(function(){if(f.is(":hidden")){f.slideDown(e.fxSpeed)}else{f.slideUp(e.fxSpeed)}return false});this.$el.find(".history-name").make_text_editable({on_finish:function(g){e.$el.find(".history-name").text(g);e.model.save({name:g}).fail(function(){e.$el.find(".history-name").text(e.model.previous("name"))})}});this.$el.find(".history-controls .annotation").make_text_editable({use_textarea:true,on_finish:function(g){e.$el.find(".history-controls .annotation").text(g);e.model.save({annotation:g}).fail(function(){e.$el.find(".history-controls .annotation").text(e.model.previous("annotation"))})}})},updateHistoryDiskSize:function(){this.$el.find(".history-size").text(this.model.get("nice_size"))},collapseAllHdaBodies:function(){_.each(this.hdaViews,function(e){e.toggleBodyVisibility(null,false)});this.storage.set("expandedHdas",{})},toggleShowDeleted:function(){this.storage.set("show_deleted",!this.storage.get("show_deleted"));this.render();return this.storage.get("show_deleted")},toggleShowHidden:function(){this.storage.set("show_hidden",!this.storage.get("show_hidden"));this.render();return this.storage.get("show_hidden")},loadAndDisplayTags:function(g){var e=this,f=this.$el.find(".history-controls .tags-display"),h=f.find(".tags");if(f.is(":hidden")){if(!jQuery.trim(h.html())){var i=jQuery.ajax(e.model.tagUrl());i.fail(function(l,j,k){e.log("Error loading tag area html",l,k,j);e.trigger("error",e,l,null,_l("Error loading tags"))});i.done(function(j){h.html(j);h.find("[title]").tooltip();f.slideDown(e.fxSpeed)})}else{f.slideDown(e.fxSpeed)}}else{f.slideUp(e.fxSpeed)}return false},showLoadingIndicator:function(f,e,g){e=(e!==undefined)?(e):(this.fxSpeed);if(!this.indicator){this.indicator=new LoadingIndicator(this.$el,this.$el.parent())}if(!this.$el.is(":visible")){this.indicator.show(0,g)}else{this.$el.fadeOut(e);this.indicator.show(f,e,g)}},hideLoadingIndicator:function(e,f){e=(e!==undefined)?(e):(this.fxSpeed);if(this.indicator){this.indicator.hide(e,f)}},displayMessage:function(j,k,i){var g=this;this.scrollToTop();var h=this.$el.find(this.msgsSelector),e=$("<div/>").addClass(j+"message").html(k);if(!_.isEmpty(i)){var f=$('<a href="javascript:void(0)">Details</a>').click(function(){Galaxy.modal.show(g.messageToModalOptions(j,k,i));return false});e.append(" ",f)}return h.html(e)},messageToModalOptions:function(i,k,h){var e=this,j=$("<div/>"),g={title:"Details"};function f(l){l=_.omit(l,_.functions(l));return["<table>",_.map(l,function(n,m){n=(_.isObject(n))?(f(n)):(n);return'<tr><td style="vertical-align: top; color: grey">'+m+'</td><td style="padding-left: 8px">'+n+"</td></tr>"}).join(""),"</table>"].join("")}if(_.isObject(h)){g.body=j.append(f(h))}else{g.body=j.html(h)}g.buttons={Ok:function(){Galaxy.modal.hide();e.clearMessages()}};return g},clearMessages:function(){var e=this.$el.find(this.msgsSelector);e.empty()},scrollPosition:function(){return this.$el.parent().scrollTop()},scrollTo:function(e){this.$el.parent().scrollTop(e)},scrollToTop:function(){this.$el.parent().scrollTop(0);return this},scrollIntoView:function(f,g){if(!g){this.$el.parent().parent().scrollTop(f);return this}var e=window,h=this.$el.parent().parent(),j=$(e).innerHeight(),i=(j/2)-(g/2);$(h).scrollTop(f-i);return this},scrollToId:function(f){if((!f)||(!this.hdaViews[f])){return this}var e=this.hdaViews[f].$el;this.scrollIntoView(e.offset().top,e.outerHeight());return this},scrollToHid:function(e){var f=this.model.hdas.getByHid(e);if(!f){return this}return this.scrollToId(f.id)},connectToQuotaMeter:function(e){if(!e){return this}this.listenTo(e,"quota:over",this.showQuotaMessage);this.listenTo(e,"quota:under",this.hideQuotaMessage);this.on("rendered rendered:initial",function(){if(e&&e.isOverQuota()){this.showQuotaMessage()}});return this},showQuotaMessage:function(){var e=this.$el.find(".quota-message");if(e.is(":hidden")){e.slideDown(this.fxSpeed)}},hideQuotaMessage:function(){var e=this.$el.find(".quota-message");if(!e.is(":hidden")){e.slideUp(this.fxSpeed)}},connectToOptionsMenu:function(e){if(!e){return this}this.on("new-storage",function(g,f){if(e&&g){e.findItemByHtml(_l("Include Deleted Datasets")).checked=g.get("show_deleted");e.findItemByHtml(_l("Include Hidden Datasets")).checked=g.get("show_hidden")}});return this},toString:function(){return"HistoryPanel("+((this.model)?(this.model.get("name")):(""))+")"}});c.templates={historyPanel:Handlebars.templates["template-history-historyPanel"],anonHistoryPanel:Handlebars.templates["template-history-historyPanel-anon"]};return{HistoryPanel:c}});