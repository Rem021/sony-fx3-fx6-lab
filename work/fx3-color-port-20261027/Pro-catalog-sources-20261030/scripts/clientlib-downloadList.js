var path="";
var enName = "";
var downloadType="SONY_CASCH_DOWNLOAD_FIRM";
var category = "";
var download=new Vue({
	el:"#download",
	data:{
		pageSize:5,
		downloadList:[],
		sign:"...",
		signIndex:6,
		totalPageCount:"",
		// 当前页
		currentPage:1,
		// 显示在页面的数组列表
		pagingList:[],
		current:1,
		mode:"",
		product:[],
		category:[],
		categoryPath:"",
		subCategory:[],
		subCategoryPath:"",
		series:[],
		seriesPath:"",
		product:[],
		productPath:"",
		current1:-1,
		current2:-1,
		current3:-1,
		current4:-1,
		index:0,
		ca:"",
		su:"",
		se:"",
		pdp:"",
		disabled:false,
		disabled2:false,
		disabled3:false,
		path:'',
		checkedTitle:[{title:'固件升级', id:'SONY_CASCH_DOWNLOAD_FIRM'}],
	},
	created:function(){
	},
	methods:{
		handleDownLoadAA(item,name){
			let adbePageObj = $("#modelName").attr('path') || this.path
			if(adbePageObj.length == 0) return
			let productPathArr = adbePageObj.split('/')
			let category = productPathArr[7]
			let subcategory = productPathArr[8]
			let series = productPathArr[9]
			let model = productPathArr[10]
			adobeDataLayer.push({
				event:'click:Download',	//固定值
				eventInfo:{
					productObj:	{
						productCategory: category, //示例 ：tv
						productSubcategory: subcategory, //示例：productSubcategory
						productSeries: series, //示例：BRAVIA摄像头
						productID: model //示例：CMU-BC1
					},
					download_Type:	this.checkedTitle[0].title,//传值为当前所在Tab页名称（固件升级/产品说明书/软件下载）
					download_Title:	item.title,//传值为当前下载项标题
					download_Button: name	//传值为当前下载按钮名称（立即下载/在线预览/软件下载/）
				}
			})	
			console.log('AA埋点： 下载---',JSON.stringify(adobeDataLayer,null,2));		
		},
		getPageData:function(num,type){
			let data = [
				{title:'产品说明书', id:'SONY_CASCH_DOWNLOAD_MANUAL'},
				{title:'软件下载', id:'SONY_CASCH_DOWNLOAD_SOFTWARE'},
				{title:'驱动下载', id:'SONY_CASCH_DOWNLOAD_DRIVER'},
				{title:'固件升级', id:'SONY_CASCH_DOWNLOAD_FIRM'},
			]
			this.checkedTitle = data.filter(item => item.id == type) 
			this.checkedTitle.length == 0 && (this.checkedTitle = [{title:'固件升级', id:'SONY_CASCH_DOWNLOAD_FIRM'}])


			var _this=this;
			if(num){
				_this.currentPage=num;
			}
			downloadType=type;
			if(downloadType=="SONY_CASCH_DOWNLOAD_FIRM"){
				_this.current=1;
			}else if(downloadType=="SONY_CASCH_DOWNLOAD_MANUAL"){
				_this.current=2;
				this.getManualList()
				return 
			}else if(downloadType=="SONY_CASCH_DOWNLOAD_DRIVER"){
				_this.current=3;
			}else if(downloadType=="SONY_CASCH_DOWNLOAD_SOFTWARE"){
				_this.current=4;
			}else if(downloadType=="SONY_CASCH_DOWNLOAD_GUIDE"){
				_this.current=5;
			}
			if(enName == undefined){
				enName = ''
			}
		      axios({
		        method: 'Get',
		        url: "/casch/outDownload?method=findPage&currentNo="+(num-1)+"&pageSize="+_this.pageSize+"&downloadType="+downloadType+"&path="+path+"&enName="+enName,
		        headers: {"Content-Type": "application/json"}
		      }).then(function (res) {
		        _this.downloadList = res.data.returnData.Data;
		        $(".search").slideDown();
		        if(_this.downloadList.length==0){
		        	if(path!=""){
		        		$(".no-lists-model").html($("#proList .otherList li.productmodel.check").text());
		        	}else{
		        		if($("#modelName").val().length>0){
		        			$(".no-lists-model").html($("#modelName").val());
		        		}else{
		        			$(".no-lists-model").html(_this.product[0].enName);
		        		}
		        	}
		    		$(".download-no-lists").show();
		    		$("#toolBar").hide();
		        }else{
			        $(".download-no-lists").hide();
			    	$("#toolBar").show();
			        var totalRecords = res.data.returnData.Page.totalRecords;
			        _this.totalPageCount = _this.getPageTotal(totalRecords);
			        _this.init();
			        _this.getNavWidth(_this.totalPageCount);
		        }
		      });
		},
		/*产品说明书新接口*/
		getManualList:function(){
			var _this=this;
			//_this.current=2;
			//downloadType = 'SONY_CASCH_DOWNLOAD_MANUAL'
			var modelEnName = $("#modelName").val().toLowerCase(); //搜索框输入的型号名
			if(!modelEnName){//列表搜索
				modelEnName = $('.check:last')[0].innerText.toLowerCase()
			}
			axios({
				method: 'Get',
				url: "https://www.sony.com/api/content/support/xz_CN/documents/"+modelEnName.replace(/ /g,"-")+"/languages/xz?start="+(_this.currentPage-1)+"&num=2",
				headers:{"Content-Type":"application/json"}
			}).then(function(res){
				//等到接口值返回再去判断有无数据
				if(res.data){
					_this.downloadList = res.data.searchResponse.results;
					_this.current = 2
					var totalRecords = res.data.searchResponse.count;//总数
					if(_this.downloadList.length>0){
						 _this.totalPageCount = _this.getPageTotal(totalRecords);
						 _this.init();
						 _this.getNavWidth(_this.totalPageCount);
						 $(".download-no-lists").hide();
	 	   				$("#toolBar").show();
					}else{
						$(".download-no-lists").show();
		   	        	$("#toolBar").hide();
					}
				}
			})
			
		},
		/*产品说明书时间处理*/
		dateFormat:function(time){
			if(time){
				var date=new Date(time);
				var times=date.getFullYear() + '-' + (date.getMonth() + 1) + '-' + date.getDate() ;
				return times
			}else{
				return ''
			}
		},
		getNavWidth:function(count){
		    //   var $nav = $(".toolBar nav");
		    //   if(count<9){
		    //     var width = $nav.find("li").width();       //获取nav的宽度
		    //     var new_width=width*(count+2);
		    //     $nav.css("width", new_width);
		    //   }else{
		    //     $nav.css("width", "420px");
		    //   }
		    },
	    getPageTotal:function(data) {
	      var _this=this;
	      return Math.floor(data / _this.pageSize) + ((data % _this.pageSize) == 0 ? 0 : 1);
	    },
	    // 跳转到某页码
	    next :function(num) {
	      var _this = this;
	      if (num <= 1) _this.currentPage = 1;
	      else if (num >= _this.totalPageCount) _this.currentPage = _this.totalPageCount;
	      else _this.currentPage = num;
	      if(downloadType == "SONY_CASCH_DOWNLOAD_MANUAL"){
	    	  _this. getManualList() //如果当前类型是产品说明书，调用产品说明书的接口
	      }else{
	          _this.getPageData(_this.currentPage,downloadType);
	      }
	    },
		 // 初始化数据
	    fetchData :function() {
	      var _this = this;
	      _this.pagingList = [];
	      var tmp = null;
	      if ((_this.totalPageCount) > 8) {
	        if (((_this.totalPageCount-1) == (_this.totalPageCount - _this.currentPage)) && (_this.totalPageCount - _this.currentPage) > 5) {
	          for (var i=1;i<9;i++) {
	            if (i < _this.signIndex) {
	              tmp = {key:i, value:i }
	            } else if (i== _this.signIndex) {
	              tmp = {key:_this.sign, value:0 }
	            } else if (i == (_this.signIndex + 1) ) {
	              tmp = {key:_this.totalPageCount - 1, value:_this.totalPageCount - 1 }
	            } else {
	              tmp = {key:_this.totalPageCount, value:_this.totalPageCount }
	            }
	            _this.pagingList.push(tmp)
	          }
	        } else if (((_this.totalPageCount - _this.currentPage) <= _this.signIndex)){
	          var starNum = _this.totalPageCount - 7;
	          for (var i=starNum;i<starNum + 8;i++) {
	            tmp = {"key":i, "value":i };
	            _this.pagingList.push(tmp)
	          }
	        } else {
	          var starNum = _this.currentPage - 1;
	          for (var i=1;i<9;i++) {
	            if (i < _this.signIndex) {
	              tmp = {key:(starNum - 1) + i, value:(starNum - 1) + i }
	            } else if (i== _this.signIndex) {
	              tmp = {key:_this.sign, value:0 }
	            } else if (i == (_this.signIndex + 1) ) {
	              tmp = {key:_this.totalPageCount - 1, value:_this.totalPageCount - 1 }
	            } else {
	              tmp = {key:_this.totalPageCount, value:_this.totalPageCount }
	            }
	            _this.pagingList.push(tmp)
	          }
	        }
	      } else {
	        for (var i =0; i <_this.totalPageCount; i++) {
	          tmp = {"key":i+1, "value":i+1 };
	          _this.pagingList.push(tmp);
	        }
	      }
	    },
	    init:function () {
	      var _this = this;

	      _this.fetchData()
	    },
	    showPopup:function(paths,title){
	    	var path=paths?paths[0]:"#";
	    	$(".g_buy")[0].setAttribute("href",path);
	    	$(".g_buy")[0].setAttribute("name",title);
	    	//获取页面的实际高度和宽度
			var hei = $(document).height();
			var wid = $(document).width();
			$("#background_div").css("width",wid);
			$("#background_div").css("height",hei);
			$("#popup_div").show();
	    },
	    /*toTheDetail:function(id,type){
	    	if(type=="SONY_CASCH_DOWNLOAD_FIRM"){
	    		window.location.href="/content/casch/download/firm/"+id+".html"
	    	}else if(type=="SONY_CASCH_DOWNLOAD_DRIVER"){
	    		window.location.href="/content/casch/download/driver/"+id+".html"
	    	}else if(type=="SONY_CASCH_DOWNLOAD_SOFTWARE"){
	    		window.location.href="/content/casch/download/software/"+id+".html"
	    	}else if(type=="SONY_CASCH_DOWNLOAD_GUIDE"){
	    		window.location.href="/content/casch/download/guide/"+id+".html"
	    	}
	    }*/
		openCategory:function () {
			var _this = this;
			$("#categoryList .box").slideDown();
			$("#subList .box").slideUp();
			$("#seriesList .box").slideUp();
			$("#proList .box").slideUp();
			$("#currentMainCategory")[0].innerHTML="";
			$("#currentMainSub")[0].innerHTML="";
			$("#currentMainSeries")[0].innerHTML="";
			$("#subList h3").addClass("huise");
			$("#seriesList h3").addClass("huise");
			_this.disabled0 = false;
			_this.disabled = false;
			_this.disabled2 = false;
			_this.disabled3 = false;
		},
		openSubCat:function () {
			var _this = this;
			$("#categoryList .box").slideUp();
			$("#subList .box").slideDown();
			$("#seriesList .box").slideUp();
			$("#proList .box").slideUp();
			$("#currentMainSub")[0].innerHTML="";
			$("#currentMainSeries")[0].innerHTML="";
			_this.disabled2 = false;
			_this.disabled3 = false;
		},
		openSeries:function () {
			var _this = this;
			$("#categoryList .box").slideUp();
			$("#subList .box").slideUp();
			$("#seriesList .box").slideDown();
			$("#proList .box").slideUp();
			$("#currentMainSeries")[0].innerHTML="";
			_this.disabled3 = false;
		},
		openPro:function () {
			$("#categoryList .box").slideUp();
			$("#subList .box").slideUp();
			$("#seriesList .box").slideUp();
			$("#proList .box").slideDown();
		}
	}
})