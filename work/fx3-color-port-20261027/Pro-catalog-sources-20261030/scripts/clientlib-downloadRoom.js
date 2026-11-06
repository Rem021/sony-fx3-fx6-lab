var downloadRoom=new Vue({
  el:"#downloadRoom",
  data:{
	  downloadURLs:[],
	  downloadHistory:[]
  },
  created:function(){
	  var _this=this;
	  var path=$("#title").attr("path");
	  if(path){
		  axios({
			  method:'Get',
			  url:"/casch/outDownload?method=findOne&path="+path,
			  headers:{"Content-Type":"application/json"}
		  }).then(function(res){
			  var downloadPath = res.data.returnData.Data.downloadPath;
			  var fileSize = res.data.returnData.Data.fileSize;
			  
			  _this.downloadHistory = []
			  if (res.data.returnData.Data.otherDownloadHistory && res.data.returnData.Data.otherDownloadHistory.length > 0) {
				  _this.downloadHistory.push(...res.data.returnData.Data.otherDownloadHistory)
			  }
			  if (res.data.returnData.Data.downloadHistory && res.data.returnData.Data.downloadHistory.length > 0) {
				  _this.downloadHistory.push(...res.data.returnData.Data.downloadHistory)
			  }
			  
			  if(downloadPath!=undefined && downloadPath!=null && downloadPath.length > 0){
				  for(var i=0;i < downloadPath.length;i++){
					  var urlPath = downloadPath[i];
					  var index=urlPath.indexOf("?") != -1 ? urlPath.lastIndexOf("?"):urlPath .length;
					  var urlName = urlPath .substring(urlPath .lastIndexOf("\/") + 1,index);
					  if(urlName == "index.php"){
						  var twoPath = urlPath .substring(0,urlPath .lastIndexOf("\/"));
						  urlName = "DriverLoader_"+twoPath.substring(twoPath .lastIndexOf("\/")+1,twoPath.length);
					  }
					  var urlSize = "";
					  if(fileSize){
						  var sizes = fileSize.split(",");
						  if(sizes.length > i ){
							  urlSize = sizes[i];
						  }
					  }
					  _this.downloadURLs[i]={
						  name:urlName,
						  size:urlSize,
						  path:urlPath
					  }
				  }
				  _this.downloadURLs=Object.assign([], _this.downloadURLs);
			  }
		  });
	  }
	  if($(".download-wrap .messages").html().trim() === ""){
		$(".download-wrap div").remove(".messages");  
	  }
  },
  filters:{
  },
  methods:{
	hidePopup(){
		$(".popbox").hide()
	},
    seeModel:function(){
      $(".models-btn a").toggleClass("active");
      $(".tabUp").toggleClass("tabDown");
      $(".models-item").slideToggle();
    },
    showPopup:function(){
    	$(".btz .continue").html("返回");
    	//获取页面的实际高度和宽度
		$("#background_div").css("width",$(document).width());
		$("#background_div").css("height",$(document).height());
		$("#popup_div").show();
		$('.popbox').show() 
    },
    downCli:function(val){
    	console.log("href:"+val);
		console.log($('.agree').hasClass('check'))
		if($('.agree').hasClass('check')){
			// 勾选了,需要跳转
			window.location.href = val
		}else{
			//获取页面的实际高度和宽度
			var hei = $(document).height();
			var wid = $(document).width();
			$("#background_div").css("width",wid);
			$("#background_div").css("height",hei);
			$(".popbox-download").show();
		}
    	// s_gi(s_account).tl({href:val},"d",s.pageName);
    },
    show:function(){
    	var _this = this;
    	if(!$('#note').is(':visible')){ 
    		$('#note').css({display:'block', top:'-100px'}).animate({top: '+150'}, 800, function(){ 
    			setTimeout(function(){_this.out()},1000);
    		}); 
    	} 
    },
    out:function(){ 
    	$('#note').animate({top:'0'}, 800, function(){ 
    	$(this).css({display:'none', top:'-150'}); 
    	}); 
    },
    isShow:function(e){
    	$(e.target.classList.toggle("sanjiaoUp"))
    	if(e.target.className.includes('sanjiaoUp')){
    		$(e.target.nextElementSibling).slideDown(800); 
    	}else{
    		$(e.target.nextElementSibling).slideUp(800); 
    	}
    },
    changeText:function(e){
    	$(e.target).parent().next().slideToggle();
    	$(e.target).toggleClass("close"); 
    },
    commit:function(){
    	if($(".submit-btn").css('background') != 'rgb(164, 164, 164) none repeat scroll 0% 0% / auto padding-box border-box'){
    		$(".submit-btn").css('background','#a4a4a4');
    		$(".submit-btn").val('正在提交中...');
        	var _this = this;
        	var commitUrl = document.location.toString();
        	var value = $(".question-checkbox").find(".active")[0];
        	var comments =  $(".question-text").find("#textarea")[0].value;
        	var title = $(".detail-page-tit").text();
        	var site = "casch";
        	var type = "SONY_CASCH_DOWNLOAD";
        	var customerID ="";
        	var hasUseful = value && value.innerHTML == '是' ? true : false;
         	var isNotNullComments = comments != null && comments.trim() != '' ?  true : false;
         	if(hasUseful || (isNotNullComments && !hasUseful) || (isNotNullComments && !value)){
         		if(!isNotNullComments){comments='是'}
         		$('#button').attr('disabled',"true")
         		hasUseful = value == undefined ? true : hasUseful;
         		//Commit_Track_EVarLink(hasUseful,isNotNullComments,"download",_pIdFoot,title);
        		axios({
      		        method: 'Get',
      		        url: "/omniapp/storesurvey/feedback/commit?comments="+encodeURI(comments)+"&site="+site+"&commitUrl="+commitUrl+"&type="+type+"&title="+encodeURI(title)+"&customerID="+customerID+"&hasUseful="+hasUseful,
      		      headers: {'Content-Type': 'application/x-www-form-urlencoded;charset=utf-8'},
    		        withCredentials:true
      		      }).then(function (res) {
      		    	  if(res.data.code == 200){
      		    		$('#note').html("感谢您的反馈");
      		    		_this.show();
      		    	  }else if(res.data.code == 404){
      		    		$('#note').html(res.data.message);
      		    		_this.show();
      		    	  }else{
      		    		$('#note').html("已收到反馈，请勿重复提交");
      		    		_this.show();
      		    	  }
      		    	$(".submit-btn").val('提交');
      		    	/*$(".submit-btn").css('background','#0190e1');*/
      		      })	
        	}else{
        		$(".submit-btn").val('提交');
        		$(".submit-btn").css('background','#0190e1');
        		$("#textarea").val("");
        		$("#textarea").attr("placeholder","反馈不能为空!");
        		$('#button').attr('disabled',false)
        		$("#textarea").css('border','1px solid #ff000045');
        		setTimeout(function(){$("#textarea").css('border','1px solid #efefef')},1000);
        	}
    	}
    }
  }
})