var DENSITY=200,FEATURE_LEVELS=10,DATA_ERROR="There was an error in indexing this dataset. ",DATA_NOCONVERTER="A converter for this dataset is not installed. Please check your datatypes_conf.xml file.",DATA_NONE="No data for this chrom/contig.",DATA_PENDING="Currently indexing... please wait",DATA_LOADING="Loading data...",CACHED_TILES_FEATURE=10,CACHED_TILES_LINE=30,CACHED_DATA=5,CONTEXT=$("<canvas></canvas>").get(0).getContext("2d"),PX_PER_CHAR=CONTEXT.measureText("A").width,RIGHT_STRAND,LEFT_STRAND;var right_img=new Image();right_img.src="/static/images/visualization/strand_right.png";right_img.onload=function(){RIGHT_STRAND=CONTEXT.createPattern(right_img,"repeat")};var left_img=new Image();left_img.src="/static/images/visualization/strand_left.png";left_img.onload=function(){LEFT_STRAND=CONTEXT.createPattern(left_img,"repeat")};var right_img_inv=new Image();right_img_inv.src="/static/images/visualization/strand_right_inv.png";right_img_inv.onload=function(){RIGHT_STRAND_INV=CONTEXT.createPattern(right_img_inv,"repeat")};var left_img_inv=new Image();left_img_inv.src="/static/images/visualization/strand_left_inv.png";left_img_inv.onload=function(){LEFT_STRAND_INV=CONTEXT.createPattern(left_img_inv,"repeat")};var Cache=function(a){this.num_elements=a;this.clear()};$.extend(Cache.prototype,{get:function(b){var a=this.key_ary.indexOf(b);if(a!=-1){this.key_ary.splice(a,1);this.key_ary.push(b)}return this.obj_cache[b]},set:function(b,c){if(!this.obj_cache[b]){if(this.key_ary.length>=this.num_elements){var a=this.key_ary.shift();delete this.obj_cache[a]}this.key_ary.push(b)}this.obj_cache[b]=c;return c},clear:function(){this.obj_cache={};this.key_ary=[]}});var View=function(b,d,c,a){this.vis_id=c;this.dbkey=a;this.title=d;this.chrom=b;this.tracks=[];this.label_tracks=[];this.max_low=0;this.max_high=0;this.track_id_counter=0;this.zoom_factor=3;this.min_separation=30;this.has_changes=false;this.reset()};$.extend(View.prototype,{add_track:function(a){a.view=this;a.track_id=this.track_id_counter;this.tracks.push(a);if(a.init){a.init()}a.container_div.attr("id","track_"+a.track_id);this.track_id_counter+=1},add_label_track:function(a){a.view=this;this.label_tracks.push(a)},remove_track:function(a){this.has_changes=true;a.container_div.fadeOut("slow",function(){$(this).remove()});delete this.tracks[this.tracks.indexOf(a)]},update_options:function(){this.has_changes=true;var b=$("ul#sortable-ul").sortable("toArray");for(var c in b){var e=b[c].split("_li")[0].split("track_")[1];$("#viewport").append($("#track_"+e))}for(var d in view.tracks){var a=view.tracks[d];if(a&&a.update_options){a.update_options(d)}}},reset:function(){this.low=this.max_low;this.high=this.max_high;$(".yaxislabel").remove()},redraw:function(f){var d=this.high-this.low,b=this.low,e=this.high;if(b<this.max_low){b=this.max_low}if(e>this.max_high){e=this.max_high}if(d<this.min_separation){e=b+this.min_separation}this.low=Math.floor(b);this.high=Math.ceil(e);this.resolution=Math.pow(10,Math.ceil(Math.log((this.high-this.low)/200)/Math.LN10));this.zoom_res=Math.pow(FEATURE_LEVELS,Math.max(0,Math.ceil(Math.log(this.resolution,FEATURE_LEVELS)/Math.log(FEATURE_LEVELS))));$("#overview-box").css({left:(this.low/(this.max_high-this.max_low))*$("#overview-viewport").width(),width:Math.max(12,(this.high-this.low)/(this.max_high-this.max_low)*$("#overview-viewport").width())}).show();$("#low").val(commatize(this.low));$("#high").val(commatize(this.high));if(!f){for(var c=0,a=this.tracks.length;c<a;c++){if(this.tracks[c]&&this.tracks[c].enabled){this.tracks[c].draw()}}for(var c=0,a=this.label_tracks.length;c<a;c++){this.label_tracks[c].draw()}}},zoom_in:function(b,c){if(this.max_high===0||this.high-this.low<this.min_separation){return}var d=this.high-this.low,e=d/2+this.low,a=(d/this.zoom_factor)/2;if(b){e=b/c.width()*(this.high-this.low)+this.low}this.low=Math.round(e-a);this.high=Math.round(e+a);this.redraw()},zoom_out:function(){if(this.max_high===0){return}var b=this.high-this.low,c=b/2+this.low,a=(b*this.zoom_factor)/2;this.low=Math.round(c-a);this.high=Math.round(c+a);this.redraw()}});var Track=function(a,b){this.name=a;this.parent_element=b;this.init_global()};$.extend(Track.prototype,{init_global:function(){this.header_div=$("<div class='track-header'>").text(this.name);this.content_div=$("<div class='track-content'>");this.container_div=$("<div />").addClass("track").append(this.header_div).append(this.content_div);this.parent_element.append(this.container_div)},init_each:function(c,b){var a=this;a.enabled=false;a.data_queue={};a.tile_cache.clear();a.data_cache.clear();if(!a.content_div.text()){a.content_div.text(DATA_LOADING)}a.container_div.removeClass("nodata error pending");if(a.view.chrom){$.getJSON(data_url,c,function(d){if(!d||d==="error"||d.kind==="error"){a.container_div.addClass("error");a.content_div.text(DATA_ERROR);if(d.message){var f=a.view.tracks.indexOf(a);var e=$("<a href='javascript:void(0);'></a>").attr("id",f+"_error");e.text("Click to view error");$("#"+f+"_error").live("click",function(){show_modal("Trackster Error","<pre>"+d.message+"</pre>",{Close:hide_modal})});a.content_div.append(e)}}else{if(d==="no converter"){a.container_div.addClass("error");a.content_div.text(DATA_NOCONVERTER)}else{if(d.data!==undefined&&(d.data===null||d.data.length===0)){a.container_div.addClass("nodata");a.content_div.text(DATA_NONE)}else{if(d==="pending"){a.container_div.addClass("pending");a.content_div.text(DATA_PENDING);setTimeout(function(){a.init()},5000)}else{a.content_div.text("");a.content_div.css("height",a.height_px+"px");a.enabled=true;b(d);a.draw()}}}}})}else{a.container_div.addClass("nodata");a.content_div.text(DATA_NONE)}}});var TiledTrack=function(){this.left_offset=200};$.extend(TiledTrack.prototype,Track.prototype,{draw:function(){var i=this.view.low,e=this.view.high,f=e-i,d=this.view.resolution;var k=$("<div style='position: relative;'></div>"),l=this.content_div.width()/f,h;this.content_div.children(":first").remove();this.content_div.append(k),this.max_height=0;var a=Math.floor(i/d/DENSITY);while((a*DENSITY*d)<e){var j=this.content_div.width()+"_"+l+"_"+a;var c=this.tile_cache.get(j);if(c){var g=a*DENSITY*d;var b=(g-i)*l;if(this.left_offset){b-=this.left_offset}c.css({left:b});k.append(c);this.max_height=Math.max(this.max_height,c.height());this.content_div.css("height",this.max_height+"px")}else{this.delayed_draw(this,j,i,e,a,d,k,l)}a+=1}},delayed_draw:function(c,e,a,f,b,d,g,h){setTimeout(function(){if(!(a>c.view.high||f<c.view.low)){tile_element=c.draw_tile(d,b,g,h);if(tile_element){c.tile_cache.set(e,tile_element);c.max_height=Math.max(c.max_height,tile_element.height());c.content_div.css("height",c.max_height+"px")}}},50)}});var LabelTrack=function(a){Track.call(this,null,a);this.track_type="LabelTrack";this.hidden=true;this.container_div.addClass("label-track")};$.extend(LabelTrack.prototype,Track.prototype,{draw:function(){var c=this.view,d=c.high-c.low,g=Math.floor(Math.pow(10,Math.floor(Math.log(d)/Math.log(10)))),a=Math.floor(c.low/g)*g,e=this.content_div.width(),b=$("<div style='position: relative; height: 1.3em;'></div>");while(a<c.high){var f=(a-c.low)/d*e;b.append($("<div class='label'>"+commatize(a)+"</div>").css({position:"absolute",left:f-1}));a+=g}this.content_div.children(":first").remove();this.content_div.append(b)}});var ReferenceTrack=function(){this.track_type="ReferenceTrack";Track.call(this,null,$("#top-labeltrack"));TiledTrack.call(this);this.hidden=true;this.height_px=12;this.container_div.addClass("reference-track");this.dummy_canvas=$("<canvas></canvas>").get(0).getContext("2d");this.data_queue={};this.data_cache=new Cache(CACHED_DATA);this.tile_cache=new Cache(CACHED_TILES_LINE)};$.extend(ReferenceTrack.prototype,TiledTrack.prototype,{get_data:function(d,b){var c=this,a=b*DENSITY*d,f=(b+1)*DENSITY*d,e=d+"_"+b;if(!c.data_queue[e]){c.data_queue[e]=true;$.ajax({url:reference_url,dataType:"json",data:{chrom:this.view.chrom,low:a,high:f,dbkey:this.view.dbkey},success:function(g){c.data_cache.set(e,g);delete c.data_queue[e];c.draw()},error:function(h,g,i){console.log(h,g,i)}})}},draw_tile:function(f,b,j,n){var g=b*DENSITY*f,d=DENSITY*f,e=$("<canvas class='tile'></canvas>"),m=e.get(0).getContext("2d"),i=f+"_"+b;if(n>PX_PER_CHAR){if(this.data_cache.get(i)===undefined){this.get_data(f,b);return}var l=this.data_cache.get(i);if(l===null){return}e.get(0).width=Math.ceil(d*n+this.left_offset);e.get(0).height=this.height_px;e.css({position:"absolute",top:0,left:(g-this.view.low)*n+this.left_offset});for(var h=0,k=l.length;h<k;h++){var a=Math.round(h*n);m.fillText(l[h],a+this.left_offset,10)}j.append(e);return e}}});var LineTrack=function(c,a,b){this.track_type="LineTrack";Track.call(this,c,$("#viewport"));TiledTrack.call(this);this.height_px=100;this.dataset_id=a;this.data_cache=new Cache(CACHED_DATA);this.tile_cache=new Cache(CACHED_TILES_LINE);this.prefs={min_value:undefined,max_value:undefined,mode:"Line"};if(b.min_value!==undefined){this.prefs.min_value=b.min_value}if(b.max_value!==undefined){this.prefs.max_value=b.max_value}if(b.mode!==undefined){this.prefs.mode=b.mode}};$.extend(LineTrack.prototype,TiledTrack.prototype,{init:function(){var a=this,b=a.view.tracks.indexOf(a);a.vertical_range=undefined;this.init_each({stats:true,chrom:a.view.chrom,low:null,high:null,dataset_id:a.dataset_id},function(c){a.container_div.addClass("line-track");data=c.data;if(isNaN(parseFloat(a.prefs.min_value))||isNaN(parseFloat(a.prefs.max_value))){a.prefs.min_value=data.min;a.prefs.max_value=data.max;$("#track_"+b+"_minval").val(a.prefs.min_value);$("#track_"+b+"_maxval").val(a.prefs.max_value)}a.vertical_range=a.prefs.max_value-a.prefs.min_value;a.total_frequency=data.total_frequency;$("#linetrack_"+b+"_minval").remove();$("#linetrack_"+b+"_maxval").remove();var e=$("<div />").addClass("yaxislabel").attr("id","linetrack_"+b+"_minval").text(a.prefs.min_value);var d=$("<div />").addClass("yaxislabel").attr("id","linetrack_"+b+"_maxval").text(a.prefs.max_value);d.css({position:"relative",top:"25px",left:"10px"});d.prependTo(a.container_div);e.css({position:"relative",top:a.height_px+55+"px",left:"10px"});e.prependTo(a.container_div)})},get_data:function(d,b){var c=this,a=b*DENSITY*d,f=(b+1)*DENSITY*d,e=d+"_"+b;if(!c.data_queue[e]){c.data_queue[e]=true;$.ajax({url:data_url,dataType:"json",data:{chrom:this.view.chrom,low:a,high:f,dataset_id:this.dataset_id,resolution:this.view.resolution},success:function(g){data=g.data;c.data_cache.set(e,data);delete c.data_queue[e];c.draw()},error:function(h,g,i){console.log(h,g,i)}})}},draw_tile:function(p,r,c,e){if(this.vertical_range===undefined){return}var s=r*DENSITY*p,a=DENSITY*p,b=$("<canvas class='tile'></canvas>"),v=p+"_"+r;if(this.data_cache.get(v)===undefined){this.get_data(p,r);return}var j=this.data_cache.get(v);if(j===null){return}b.css({position:"absolute",top:0,left:(s-this.view.low)*e});b.get(0).width=Math.ceil(a*e+this.left_offset);b.get(0).height=this.height_px;var o=b.get(0).getContext("2d"),k=false,l=this.prefs.min_value,g=this.prefs.max_value,n=this.vertical_range,t=this.total_frequency,d=this.height_px,m=this.prefs.mode;o.beginPath();if(data.length>1){var f=Math.ceil((data[1][0]-data[0][0])*e)}else{var f=10}var u,h;for(var q=0;q<data.length;q++){u=(data[q][0]-s)*e;h=data[q][1];if(m=="Intensity"){if(h===null){continue}if(h<=l){h=l}else{if(h>=g){h=g}}h=255-Math.floor((h-l)/n*255);o.fillStyle="rgb("+h+","+h+","+h+")";o.fillRect(u,0,f,this.height_px)}else{if(h===null){if(k&&m==="Filled"){o.lineTo(u,d)}k=false;continue}else{if(h<=l){h=l}else{if(h>=g){h=g}}h=Math.round(d-(h-l)/n*d);if(k){o.lineTo(u,h)}else{k=true;if(m==="Filled"){o.moveTo(u,d);o.lineTo(u,h)}else{o.moveTo(u,h)}}}}}if(m==="Filled"){if(k){o.lineTo(u,d)}o.fill()}else{o.stroke()}c.append(b);return b},gen_options:function(n){var a=$("<div />").addClass("form-row");var h="track_"+n+"_minval",l=$("<label></label>").attr("for",h).text("Min value:"),b=(this.prefs.min_value===undefined?"":this.prefs.min_value),m=$("<input></input>").attr("id",h).val(b),k="track_"+n+"_maxval",g=$("<label></label>").attr("for",k).text("Max value:"),j=(this.prefs.max_value===undefined?"":this.prefs.max_value),f=$("<input></input>").attr("id",k).val(j),e="track_"+n+"_mode",d=$("<label></label>").attr("for",e).text("Display mode:"),i=(this.prefs.mode===undefined?"Line":this.prefs.mode),c=$('<select id="'+e+'"><option value="Line" id="mode_Line">Line</option><option value="Filled" id="mode_Filled">Filled</option><option value="Intensity" id="mode_Intensity">Intensity</option></select>');c.children("#mode_"+i).attr("selected","selected");return a.append(l).append(m).append(g).append(f).append(d).append(c)},update_options:function(d){var a=$("#track_"+d+"_minval").val(),c=$("#track_"+d+"_maxval").val(),b=$("#track_"+d+"_mode option:selected").val();if(a!==this.prefs.min_value||c!==this.prefs.max_value||b!==this.prefs.mode){this.prefs.min_value=parseFloat(a);this.prefs.max_value=parseFloat(c);this.prefs.mode=b;this.vertical_range=this.prefs.max_value-this.prefs.min_value;$("#linetrack_"+d+"_minval").text(this.prefs.min_value);$("#linetrack_"+d+"_maxval").text(this.prefs.max_value);this.tile_cache.clear();this.draw()}}});var FeatureTrack=function(c,a,b){this.track_type="FeatureTrack";Track.call(this,c,$("#viewport"));TiledTrack.call(this);this.height_px=100;this.container_div.addClass("feature-track");this.dataset_id=a;this.zo_slots={};this.show_labels_scale=0.001;this.showing_details=false;this.vertical_detail_px=10;this.vertical_nodetail_px=3;this.default_font="9px Monaco, Lucida Console, monospace";this.inc_slots={};this.data_queue={};this.s_e_by_tile={};this.tile_cache=new Cache(CACHED_TILES_FEATURE);this.data_cache=new Cache(20);this.prefs={block_color:"black",label_color:"black",show_counts:false};if(b.block_color!==undefined){this.prefs.block_color=b.block_color}if(b.label_color!==undefined){this.prefs.label_color=b.label_color}if(b.show_counts!==undefined){this.prefs.show_counts=b.show_counts}};$.extend(FeatureTrack.prototype,TiledTrack.prototype,{init:function(){var a=this,b=a.view.max_low+"_"+a.view.max_high;a.mode="Auto";if(a.mode_div){a.mode_div.remove()}this.init_each({low:a.view.max_low,high:a.view.max_high,dataset_id:a.dataset_id,chrom:a.view.chrom,resolution:this.view.resolution},function(d){a.mode_div=$("<div class='right-float menubutton popup' />").text("Display Mode");a.header_div.append(a.mode_div);a.mode="Auto";var c=function(e){a.mode_div.text(e);a.mode=e;a.tile_cache.clear();a.draw()};make_popupmenu(a.mode_div,{Auto:function(){c("Auto")},Dense:function(){c("Dense")},Squish:function(){c("Squish")},Pack:function(){c("Pack")}});a.data_cache.set(b,d);a.draw()})},get_data:function(a,d){var b=this,c=a+"_"+d;if(!b.data_queue[c]){b.data_queue[c]=true;$.getJSON(data_url,{chrom:b.view.chrom,low:a,high:d,dataset_id:b.dataset_id,resolution:this.view.resolution,mode:this.mode},function(e){b.data_cache.set(c,e);delete b.data_queue[c];b.draw()})}},incremental_slots:function(a,h,c,r){if(!this.inc_slots[a]){this.inc_slots[a]={};this.inc_slots[a].w_scale=1/a;this.inc_slots[a].mode=r;this.s_e_by_tile[a]={}}var n=this.inc_slots[a].w_scale,z=[],l=0,b=$("<canvas></canvas>").get(0).getContext("2d"),o=this.view.max_low;var B=[];if(this.inc_slots[a].mode!==r){delete this.inc_slots[a];this.inc_slots[a]={mode:r,w_scale:n};delete this.s_e_by_tile[a];this.s_e_by_tile[a]={}}for(var w=0,x=h.length;w<x;w++){var g=h[w],m=g[0];if(this.inc_slots[a][m]!==undefined){l=Math.max(l,this.inc_slots[a][m]);B.push(this.inc_slots[a][m])}else{z.push(w)}}for(var w=0,x=z.length;w<x;w++){var g=h[z[w]],m=g[0],s=g[1],d=g[2],q=g[3],e=Math.floor((s-o)*n),f=Math.ceil((d-o)*n);if(q!==undefined&&!c){var t=b.measureText(q).width;if(e-t<0){f+=t}else{e-=t}}var v=0;while(true){var p=true;if(this.s_e_by_tile[a][v]!==undefined){for(var u=0,A=this.s_e_by_tile[a][v].length;u<A;u++){var y=this.s_e_by_tile[a][v][u];if(f>y[0]&&e<y[1]){p=false;break}}}if(p){if(this.s_e_by_tile[a][v]===undefined){this.s_e_by_tile[a][v]=[]}this.s_e_by_tile[a][v].push([e,f]);this.inc_slots[a][m]=v;l=Math.max(l,v);break}v++}}return l},rect_or_text:function(m,n,f,l,b,d,j,e,h){m.textAlign="center";var i=Math.round(n/2);if((this.mode==="Pack"||this.mode==="Auto")&&d!==undefined&&n>PX_PER_CHAR){m.fillStyle=this.prefs.block_color;m.fillRect(j,h+1,e,9);m.fillStyle="#eee";for(var g=0,k=d.length;g<k;g++){if(b+g>=f&&b+g<=l){var a=Math.floor(Math.max(0,(b+g-f)*n));m.fillText(d[g],a+this.left_offset+i,h+9)}}}else{m.fillStyle=this.prefs.block_color;m.fillRect(j,h+4,e,3)}},draw_tile:function(X,h,n,ak){var E=h*DENSITY*X,ad=(h+1)*DENSITY*X,D=DENSITY*X;var ae=E+"_"+ad;var z=this.data_cache.get(ae);if(z===undefined){this.data_queue[[E,ad]]=true;this.get_data(E,ad);return}var a=Math.ceil(D*ak),L=$("<canvas class='tile'></canvas>"),Z=this.prefs.label_color,f=this.prefs.block_color,m=this.mode,V=(m==="Squish")||(m==="Dense")&&(m!=="Pack")||(m==="Auto"&&(z.extra_info==="no_detail")),P=this.left_offset,aj,s,al;if(z.dataset_type==="summary_tree"){s=30}else{if(m==="Dense"){s=15;al=10}else{al=(V?this.vertical_nodetail_px:this.vertical_detail_px);s=this.incremental_slots(this.view.zoom_res,z.data,V,m)*al+15;aj=this.inc_slots[this.view.zoom_res]}}L.css({position:"absolute",top:0,left:(E-this.view.low)*ak-P});L.get(0).width=a+P;L.get(0).height=s;n.parent().css("height",Math.max(this.height_px,s)+"px");var A=L.get(0).getContext("2d");A.fillStyle=f;A.font=this.default_font;A.textAlign="right";if(z.dataset_type=="summary_tree"){var K,H=55,ac=255-H,g=ac*2/3,R=z.data,C=z.max,l=z.avg;if(R.length>2){var b=Math.ceil((R[1][0]-R[0][0])*ak)}else{var b=50}for(var ag=0,w=R.length;ag<w;ag++){var T=Math.ceil((R[ag][0]-E)*ak);var S=R[ag][1];if(!S){continue}K=Math.floor(ac-(S/C)*ac);A.fillStyle="rgb("+K+","+K+","+K+")";A.fillRect(T+P,0,b,20);if(this.prefs.show_counts){if(K>g){A.fillStyle="black"}else{A.fillStyle="#ddd"}A.textAlign="center";A.fillText(R[ag][1],T+P+(b/2),12)}}n.append(L);return L}var ai=z.data;var af=0;for(var ag=0,w=ai.length;ag<w;ag++){var M=ai[ag],J=M[0],ah=M[1],U=M[2],F=M[3];if(ah<=ad&&U>=E){var W=Math.floor(Math.max(0,(ah-E)*ak)),B=Math.ceil(Math.min(a,Math.max(0,(U-E)*ak))),Q=(m==="Dense"?0:aj[J]*al);if(z.dataset_type==="bai"){A.fillStyle=f;if(M[4] instanceof Array){var t=Math.floor(Math.max(0,(M[4][0]-E)*ak)),I=Math.ceil(Math.min(a,Math.max(0,(M[4][1]-E)*ak))),r=Math.floor(Math.max(0,(M[5][0]-E)*ak)),p=Math.ceil(Math.min(a,Math.max(0,(M[5][1]-E)*ak)));if(M[4][1]>=E&&M[4][0]<=ad){this.rect_or_text(A,ak,E,ad,M[4][0],M[4][2],t+P,I-t,Q)}if(M[5][1]>=E&&M[5][0]<=ad){this.rect_or_text(A,ak,E,ad,M[5][0],M[5][2],r+P,p-r,Q)}if(r>I){A.fillStyle="#999";A.fillRect(I+P,Q+5,r-I,1)}}else{A.fillStyle=f;this.rect_or_text(A,ak,E,ad,ah,F,W+P,B-W,Q)}if(m!=="Dense"&&!V&&ah>E){A.fillStyle=this.prefs.label_color;if(h===0&&W-A.measureText(F).width<0){A.textAlign="left";A.fillText(J,B+2+P,Q+8)}else{A.textAlign="right";A.fillText(J,W-2+P,Q+8)}A.fillStyle=f}}else{if(z.dataset_type==="interval_index"){if(V){A.fillRect(W+P,Q+5,B-W,1)}else{var v=M[4],O=M[5],Y=M[6],e=M[7];var u,aa,G=null,am=null;if(O&&Y){G=Math.floor(Math.max(0,(O-E)*ak));am=Math.ceil(Math.min(a,Math.max(0,(Y-E)*ak)))}if(m!=="Dense"&&F!==undefined&&ah>E){A.fillStyle=Z;if(h===0&&W-A.measureText(F).width<0){A.textAlign="left";A.fillText(F,B+2+P,Q+8)}else{A.textAlign="right";A.fillText(F,W-2+P,Q+8)}A.fillStyle=f}if(e){if(v){if(v=="+"){A.fillStyle=RIGHT_STRAND}else{if(v=="-"){A.fillStyle=LEFT_STRAND}}A.fillRect(W+P,Q,B-W,10);A.fillStyle=f}for(var ae=0,d=e.length;ae<d;ae++){var o=e[ae],c=Math.floor(Math.max(0,(o[0]-E)*ak)),N=Math.ceil(Math.min(a,Math.max((o[1]-E)*ak)));if(c>N){continue}u=5;aa=3;A.fillRect(c+P,Q+aa,N-c,u);if(G!==undefined&&!(c>am||N<G)){u=9;aa=1;var ab=Math.max(c,G),q=Math.min(N,am);A.fillRect(ab+P,Q+aa,q-ab,u)}}}else{u=9;aa=1;A.fillRect(W+P,Q+aa,B-W,u);if(M.strand){if(M.strand=="+"){A.fillStyle=RIGHT_STRAND_INV}else{if(M.strand=="-"){A.fillStyle=LEFT_STRAND_INV}}A.fillRect(W+P,Q,B-W,10);A.fillStyle=prefs.block_color}}}}}af++}}n.append(L);return L},gen_options:function(i){var a=$("<div />").addClass("form-row");var e="track_"+i+"_block_color",k=$("<label />").attr("for",e).text("Block color:"),l=$("<input />").attr("id",e).attr("name",e).val(this.prefs.block_color),j="track_"+i+"_label_color",g=$("<label />").attr("for",j).text("Text color:"),h=$("<input />").attr("id",j).attr("name",j).val(this.prefs.label_color),f="track_"+i+"_show_count",c=$("<label />").attr("for",f).text("Show summary counts"),b=$('<input type="checkbox" style="float:left;"></input>').attr("id",f).attr("name",f).attr("checked",this.prefs.show_counts),d=$("<div />").append(b).append(c);return a.append(k).append(l).append(g).append(h).append(d)},update_options:function(e){var b=$("#track_"+e+"_block_color").val(),d=$("#track_"+e+"_label_color").val(),c=$("#track_"+e+"_mode option:selected").val(),a=$("#track_"+e+"_show_count").attr("checked");if(b!==this.prefs.block_color||d!==this.prefs.label_color||a!==this.prefs.show_counts){this.prefs.block_color=b;this.prefs.label_color=d;this.prefs.show_counts=a;this.tile_cache.clear();this.draw()}}});var ReadTrack=function(c,a,b){FeatureTrack.call(this,c,a,b);this.track_type="ReadTrack";this.vertical_detail_px=10;this.vertical_nodetail_px=5};$.extend(ReadTrack.prototype,TiledTrack.prototype,FeatureTrack.prototype,{});