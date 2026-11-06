var keyword='';
var isCompatible = false;
var detail=new Vue({
	el:"#modelDetail",
	data:{
		modelPath:"",
		enName:"",
		current:0,
		downloadFileList:[],
		id:"",
		announcementList:[],
		troubleList:[],
		faqList:[],
		list:[],
		num:6,
		maker:[],
		proModel:[],
		downType:"",
		downloadNum:0,
		levelOneList:[],
		currentOne:-1,
		current3:9999,
		current2:9999,
		cShow:0,
		eclassList: [],
		eclassnum:6,
		currentLi:0,
		pageSize:6,
		pageSize2:6,
		pageSize3:6,
		pageSize4:6,
		pageSize5:6,
		pageSizeManual:6,
		// 总页数
		totalPageCount:"",
		totalPageCount2:"",
		totalPageCount3:"",
		totalPageCount4:"",
		totalPageCount5:"",
		totalPageCountManual:"",
		// 当前页
		currentPage:1,
		currentPage2:1,
		currentPage3:1,
		currentPage4:1,
		currentPage5:1,
		currentPageManual:1,
		pagingList:[],
		pagingList2:[],
		pagingList3:[],
		pagingList4:[],
		pagingList5:[],
		pagingListManual:[],
		// 省略的符号
		sign:'...',
		// 省略号位置
		signIndex:6,
		isDI:false,
		isXperia: false,
		isDownloadDriver:false,
		totalNumList: true,
		downloaIsShow: true,
		otherIsShow:true,
		serchKeyword: '',
		isSerchResult: false,
		EclasstotalRecords: 0,
		AnnouncementRecords: 0,
		TroubleRecords:0,
		FaqRecords:0,
		DownloadRecords1: 0,
		DownloadRecords2: 0,
		DownloadRecords3: 0,
		DownloadRecords4:0,
		checkedTitle:[{title:'下载中心-固件升级', id:'SONY_CASCH_DOWNLOAD_FIRM'}],
		activeName: '',
		subCategory: '', // 子品类
	},
	mounted:function(){
		let left =  $('.header-type').width() + 95;
		$('.search-btn-pdp').css('left',left)
		// author 需要展示这个新增组件
		if(window.location.host.includes('author')){
			$('#service-pdp .more-functions').hide()
		}else{
			$('#service-pdp .otherFunction-item').length == 0 && $('#service-pdp').hide()
			if($("#service-pdp .otherFunction-item").length>3){
				var length=$("#service-pdp .otherFunction-item").length;
				for(var i=3;i<length;i++){
					$("#service-pdp .otherFunction-item")[3].setAttribute("class","hideFunction-item")
				}
			}else{
				$('#service-pdp .more-functions').hide()
			}
		
		}
		// if($("#service-pdp .otherFunction-item").length>3){
		// 	var length=$("#service-pdp .otherFunction-item").length;
		// 	for(var i=3;i<length;i++){
		// 		$("#service-pdp .otherFunction-item")[3].setAttribute("class","hideFunction-item")
		// 	}
		// }else{
		// 	$('#service-pdp .more-functions').hide()
		// }
		// this.$nextTick(function () {
		// 	window.addEventListener('scroll', this.onScroll)
		// })
		
		// 是否显示轻松上手锚点
		if($("#service-pdp .otherFunction-item").length > 0) {
			$(".search-btn-pdp .enjoyment-anchor").show()
		}
	},
	created:function(){
		this.getAnnouncementList(1);
		this.getEclassList(1);
		this.getCompatibleOne();
		this.getTroubleList(this.currentPage);
		this.getFaqList(1);
		this.isDI = window.location.href.indexOf('/di/') != -1 ? true : false;
		this.isDownloadDriver = (window.location.href.indexOf('/audio/') != -1 || window.location.href.indexOf('/pa/') != -1 || window.location.href.indexOf('/di/') != -1 || window.location.href.indexOf('/professional/') != -1) ? true : false;

		// DI和专业摄像机显示“适配性”  注：此处用“摄像摄录一体机”来判断是否是专业摄像机
		// isCompatible = window.location.href.indexOf('/di/') != -1 ? true : false;
		_subCategoryPath = $("#modelPath")[0].getAttribute("subCategory").split("/")
		this.subCategory = _subCategoryPath[_subCategoryPath.length-1]
		isCompatible = (window.location.href.indexOf('/di/')!==-1 || this.subCategory==='摄像摄录一体机')

		this.isXperia = window.location.href.indexOf('/Xperia/') != -1 ? true : false;
		// this.handleClickIsShow('download-c',0,'下载中心-固件升级',true)
		this.handleAdobeData('products_change')
		this.getDownloadList("SONY_CASCH_DOWNLOAD_FIRM",1,this.currentPage2);
		if(!this.isDownloadDriver) {
			$("#download-c .search-nav ul").css("padding-left","172px");
		}
		this.getBuyFromSonystyle();
		this.imageInit();
	},
	filter:function (){
		formatDate(data.publicationDate,"yyyy-MM-dd");
	},
	methods:{
		handleDownLoadAA(item,name){
			this.handleAdobeData('click:Download', { download_Type:	this.checkedTitle[0].title.split('-')[1], download_Title:	item.title, download_Button: name })
			// adobeDataLayer.push({
			// 	event:'click:Download',	//固定值
			// 	eventInfo:{
			// 		download_Type:	this.checkedTitle[0].title.split('-')[1],
			// 		download_Title:	item.title,
			// 		download_Button: name
			// 	}
			// })	
			// console.log('AA埋点： 下载---',JSON.stringify(adobeDataLayer,null,2));		
		},
		handleOtherAdobeData(dom){
			this.handleAdobeData('click:PDP_Search_Nav',{PDP_Search_Nav: '其他服务-'+$(dom.target).text().trim()})
		},
		handleAdobeData(event, option){
			let adbePageObj = localStorage.getItem('ExactPath') || ''
			if(adbePageObj.length == 0) return
			let productPathArr = adbePageObj.split('/')
			let category = productPathArr[7]
			let subcategory = productPathArr[8]
			let series = productPathArr[9]
			let model = productPathArr[10]
			adobeDataLayer.push({
			  event,	//固定值
			  eventInfo:{
				productObj:	{
				  productCategory: category, //示例 ：tv
				  productSubcategory: subcategory, //示例：productSubcategory
				  productSeries: series, //示例：BRAVIA摄像头
				  productID: model //示例：CMU-BC1
				},
				...option
			  }
			  // PDP_Search_Nav: PDP_Search_Nav //传值内容为：一级列表标题[-二级列表标题]
			})
	  
			console.log('AA埋点：pdp详情页---',JSON.stringify(adobeDataLayer,null,2));
		  },
		// 用于聚合搜索 
		handleSerchKeyword(){
			if(this.serchKeyword.length > 0){
				this.downloadFileList = []
				this.isSerchResult = true
				this.handleFetchFun(true)
			}
		},

		handleFetchFun(flag){
			this.EclasstotalRecords = 0
			this.AnnouncementRecords = 0
			this.TroubleRecords = 0
			this.FaqRecords = 0
			this.DownloadRecords1 = 0
			this.DownloadRecords2 = 0
			this.DownloadRecords3 = 0
			this.DownloadRecords4 = 0
			this.current = 1
			this.getAnnouncementList(1);
			this.getEclassList(1);
			this.getTroubleList(this.currentPage);
			this.getFaqList(1);
			if(flag){
				this.getDownloadList('SONY_CASCH_DOWNLOAD_SOFTWARE',4,1,'noData')
				this.getDownloadList('SONY_CASCH_DOWNLOAD_DRIVER',3,1,'noData')
				this.getManualList(1,"nolist")
			}
			this.getDownloadList('SONY_CASCH_DOWNLOAD_FIRM',1,1)
		},

		resetSerch(){
			this.isSerchResult = false
			this.serchKeyword = ''
			this.EclasstotalRecords = 0
			this.AnnouncementRecords = 0
			this.TroubleRecords = 0
			this.FaqRecords = 0
			this.DownloadRecords1 = 0
			this.DownloadRecords2 = 0
			this.DownloadRecords3 = 0
			this.DownloadRecords4 = 0
			this.downloadFileList = []
			this.handleFetchFun()
		},
		
		handleJumpToEnjoyment() {
			$("html, body").animate({
				scrollTop: $("#service-pdp").offset().top - 100
			}, 500);
		},
		
		handleClickAdaptation(text){
			this.handleAdobeData('click:PDP_Search_Content',{PDP_Search_Nav: text ,PDP_Search_Content: '适配性查看链接',PDP_Search_Content_Url: 'http://support.d-imaging.sony.co.jp/www/cscs/accessories/?area=cn&lang=cs'})
			console.log('AA埋点： 适配性---',JSON.stringify(adobeDataLayer,null,2));
			window.open("http://support.d-imaging.sony.co.jp/www/cscs/accessories/?area=cn&lang=cs");
			// window.location.href = 'http://support.d-imaging.sony.co.jp/www/cscs/accessories/?area=cn&lang=cs'
		},
		// 用于点击切换不同div显示
		handleClickIsShow(dom,num,name,isSend=true){
			this.current = 0
			this.currentLi = num
			// console.log(this.checkedTitle,'this.checkedTitle----show')
			this.activeName = name
			isSend && this.handleAdobeData('click:PDP_Search_Nav',{PDP_Search_Nav: name})
			// this.handleAdobeData('click:PDP_Search_Nav',{PDP_Search_Nav: name})
			// console.log('AA埋点： tab点击',JSON.stringify(adobeDataLayer,null,2));
			let arr = ['download-c','announcement-c','videos','qa-c','faq-c']
			for (let index = 0; index < arr.length; index++) {
				const element = arr[index];
				if(dom == element){
					document.getElementById(dom).style.display = 'block'
				}else{
					document.getElementById(element).style.display = 'none'
				}
			}
			
		},

		/** xgq开始*/
		/** 图片初始化*/
		imageInit:function(){
			if($(".x-details-subImg").length > 0){
				$(".x-details-subImg").last().addClass("img-check");
				this.buyPathInit();
			}else{
				// $(".x-details").hide();
			}
		},
		/** 根据小图标切换大图标*/
		imageChange:function(e){
			$(e.target).addClass('img-check').siblings().removeClass('img-check');
			this.buyPathInit();
		},

		buyPathInit:function(){
			$(".x-details-bigImg").attr("src",$(".img-check").attr("imagePath"));
			//加alt属性
			$(".x-details-bigImg").attr("alt",this.enName+"产品图");
			/*购买链接暂定注释，日后再做安排
            var buyPath = $(".img-check").attr("path");
            if( $('a').is('.x-sonyPath') && buyPath && buyPath.trim() != ''){
                $(".x-sonyPath").show();
                $(".x-sonyPath").attr("href",buyPath+".html");
            }else{
                $(".x-sonyPath").hide();
            }*/
		},
		/** xgq结束 2020-01-09*/
		getTroubleList:function(num){
			var _this=this;
			var pageType="trouble";
			$("#noTrouble1").hide();
			$("#troubleToolBar").hide();
			axios({
				method: 'Get',
				url: "/casch/homePageExt?method=findAllProblems&currentNo="+(num-1)+"&pageSize="+_this.pageSize+"&enName="+$(".content-tit2")[0].innerHTML+"&keyword="+ this.serchKeyword.trim().toLocaleUpperCase(),
				headers: {"Content-Type": "application/json"}
			}).then(function (res) {
				if(_this.serchKeyword.trim().length > 0){
					let reg = new RegExp(_this.serchKeyword.trim(),'gi')
					_this.troubleList=res.data.returnData.Data.map(item => {
						item.title = item.title.replace(reg, str => '<span style="color:#F32D33">'+str+'</span>')
						return item
					})
				}else{
					_this.troubleList=res.data.returnData.Data
				}
				
				// _this.troubleList = res.data.returnData.Data;
				_this.TroubleRecords = res.data.returnData.Page.totalRecords || 0;
				if(res.data.returnData.Data.length > 0){
					_this.totalPageCount = _this.getPageTotal(_this.TroubleRecords);
					_this.init();
					_this.getNavWidth(_this.totalPageCount,$("#troubleToolBar nav"));
					$("#noTrouble1").hide();
					$("#troubleToolBar").show();
				}else{
					$("#noTrouble1").show();
					$("#troubleToolBar").hide();
				}
			});
		},
		getFaqList:function(num){
			var _this=this;
			var enName=$("#modelPath")[0].getAttribute("enName").toLowerCase();
			$("#faqToolBar").hide();
			$("#noFaq").hide();
			var query = this.serchKeyword.trim() == '' ? '' : "&query="+this.serchKeyword;
			axios({
				method: 'Get',
				url: "https://www.sony.com/api/content/support/xz_CN/search?type=faq-article&model="+enName.replace(/ /g,"-")+"&num="+_this.pageSize3+query+"&start="+(num-1)*6,
				//url:"https://www.sony.co.uk/api/content/support/search/"+enName.replace(/ /g,"-")+"?locale=xz_CN&inter-context=false&type=faq-article&num="+_this.pageSize3+query+"&start="+(num-1)*10,
				headers: {"Content-Type": "application/json"}
			}).then(function (res) {
				_this.faqList = res.data.searchResponse.results;
				_this.FaqRecords = res.data.searchResponse.count;
				if(res.data.searchResponse.results.length > 0){
					for(var i=0;i < _this.faqList.length; i++){
						_this.faqList[i].publicationDate = _this.formatDate(_this.faqList[i].publicationDate,"yyyy-MM-dd");
					}
					_this.totalPageCount3 = _this.getPageTotal3(_this.FaqRecords);
					_this.init3();
					// _this.getNavWidth(_this.totalPageCount3,$("#faqToolBar nav"));
					$("#noFaq").hide();
					$("#faqToolBar").show();
				}else{
					$("#noFaq").show();
					$("#faqToolBar").hide();
				}
			});
		},
		getDownloadList:function(downloadType,num,num2,nodata,isSend = false){
			// this.handleClickIsShow('download-c',0,'下载中心-固件升级',false)
			this.handleClickIsShow('download-c',0,'下载中心-固件升级',false)
			let data = [
				{title:'下载中心-产品说明书', id:'SONY_CASCH_DOWNLOAD_MANUAL'},
				{title:'下载中心-软件下载', id:'SONY_CASCH_DOWNLOAD_SOFTWARE'},
				{title:'下载中心-驱动下载', id:'SONY_CASCH_DOWNLOAD_DRIVER'},
				{title:'下载中心-固件升级', id:'SONY_CASCH_DOWNLOAD_FIRM'},
			]
			this.checkedTitle = data.filter(item => item.id == downloadType) 
			this.checkedTitle.length == 0 && (this.checkedTitle = [{title:'下载中心-固件升级', id:'SONY_CASCH_DOWNLOAD_FIRM'}])
			isSend && this.handleAdobeData('click:PDP_Search_Nav', {PDP_Search_Nav: this.checkedTitle[0].title})


			var _this=this;
			_this.downType=downloadType;
			_this.current=num;
			_this.currentPage2 = num2
			_this.modelPath=encodeURIComponent($("#modelPath")[0].getAttribute("path"));
			axios({
				method:'Get',
				url:"/casch/homePageExt?method=findDownLoadPage&currentNo="+(num2-1)+"&pageSize="+_this.pageSize2+"&path="+_this.modelPath+"&downloadType="+_this.downType+"&keyword="+ _this.serchKeyword.trim().toLocaleUpperCase(),
				headers:{"Content-Type":"application/json"}
			}).then(function(res){
				if(_this.serchKeyword.trim()){
					switch (downloadType) {
						case 'SONY_CASCH_DOWNLOAD_FIRM':
							detail.DownloadRecords1 = res.data.returnData.Page.totalRecords || 0
							break;
						case 'SONY_CASCH_DOWNLOAD_DRIVER':
							detail.DownloadRecords2 = res.data.returnData.Page.totalRecords || 0
							break;
						case 'SONY_CASCH_DOWNLOAD_SOFTWARE':
							detail.DownloadRecords3 = res.data.returnData.Page.totalRecords || 0
							break;
					
						default:
							break;
					}
				}
				if(nodata){
					return 
				}
				if(_this.serchKeyword.trim().length > 0){
					let reg = new RegExp(_this.serchKeyword.trim(),'gi')
					detail.downloadFileList=res.data.returnData.Data.map(item => {
						item.title = item.title.replace(reg, str => '<span style="color:#F32D33">'+str+'</span>')
						return item
					})
				}else{
					detail.downloadFileList=res.data.returnData.Data
				}
				detail.DownloadRecords = res.data.returnData.Page.totalRecords
				if(res.data.returnData.Data.length > 0){
					_this.totalPageCount2 = _this.getPageTotal2(detail.DownloadRecords);
					_this.init2();
					_this.getNavWidth2(_this.totalPageCount2);
					$("#noDownload").hide();
					$("#toolBar").show();
					$("#toolBar2").hide();
				}else{
					$("#noDownload").show();
					$("#toolBar").hide();
					$("#toolBar2").hide();
				}
			})
		},
		/*产品说明书新接口*/
		getManualList:function(num,nolist,isSend=false){
			this.checkedTitle = [{title:'下载中心-产品说明书', id:'SONY_CASCH_DOWNLOAD_MANUAL'}]
			this.handleClickIsShow('download-c',0,'下载中心-产品说明书')
			isSend && this.handleAdobeData('click:PDP_Search_Nav', {PDP_Search_Nav: '下载中心-产品说明书'})
			var _this=this;
			_this.current = 2
			_this.currentPageManual =num;
			let modelEnName = $("#modelPath")[0].getAttribute("enName").toLowerCase(); //型号名
			let url = ''
			if(_this.serchKeyword.trim().length > 0){
				url = `https://www.sony.com/api/content/support/xz_CN/search?type=sub-document&model=${modelEnName.replace(/ /g,"-")}&start=${(_this.currentPageManual - 1) * _this.pageSizeManual}&num=${_this.pageSizeManual}&query=${_this.serchKeyword.trim().toLocaleUpperCase()}`
			}else{
				url = `https://www.sony.com/api/content/support/xz_CN/documents/${modelEnName.replace(/ /g,"-")}/languages/xz?start=${(_this.currentPageManual - 1) * _this.pageSizeManual}&num=${_this.pageSizeManual}`
			}
			axios({
				method: 'Get',
				// https://www.sony.com/api/content/support/xz_CN/search?type=sub-document&query=%E5%BD%B1%E5%83%8F&model=ilce-6600m&num=10&start=0
				// url: `/casch/homePageExt?method=instructionDownload&enName=${modelEnName.replace(/ /g,"-")}&keyword=${ _this.serchKeyword.trim().toLocaleUpperCase()}&start=${(_this.currentPageManual - 1) * _this.pageSizeManual}&num=${_this.pageSizeManual}`,
				url: url,
				headers:{"Content-Type":"application/json"}
			}).then(function(res){
				_this.DownloadRecords4 = res.data.searchResponse.count
				if(nolist){
					return
				}
				detail.downloadFileList = res.data.searchResponse.results
				var totalRecords = res.data.searchResponse.count;//总数
				if(res.data.searchResponse.results.length > 0){
					_this.totalPageCountManual = _this.getPageTotalManual(totalRecords);
					_this.initManual();
					_this.getNavWidth(_this.totalPageCountManual,$("#toolBar2 nav"));
					$("#noDownload").hide();
					$("#toolBar").hide();
					$("#toolBar2").show();
				}else{
					$("#noDownload").show();
					$("#toolBar2").hide();
					$("#toolBar").hide();
				}
			})
		},
		/* 产品说明书新分页*/
		getPageTotalManual:function(data){
			var _this=this;
			return Math.floor(data / _this.pageSizeManual) + ((data % _this.pageSizeManual) == 0 ? 0 : 1);
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
		/*产品说明书翻页*/
		next2: function(num){
			var that = this;
			if (num <= 1) that.currentPageManual = 1;
			else if (num >= that.totalPageCountManual) that.currentPageManual = that.totalPageCountManual;
			else that.currentPageManual = num;
			that.getManualList(that.currentPageManual)
		},
		getAnnouncementList:function(num){
			this.id=$(".model-id")[0].getAttribute("id");
			$("#noAnnouncement").hide();
			$("#announcementToolBar").hide();
			axios({
				method:'Get',
				url:`/casch/homePageExt?method=productModelFindAnnouncement&id=${this.id}&currentNo=${(num-1)}&pageSize=6&keyword=${this.serchKeyword.trim().toLocaleUpperCase()}`,
				headers:{"Content-Type":"application/json"}
			}).then(function(res){
				detail.AnnouncementRecords = res.data.returnData.Page.totalRecords || 0;
				if(res.data.returnData.Data && res.data.returnData.Data.length >= 1){
					if(detail.serchKeyword.trim().length > 0){
						let reg = new RegExp(detail.serchKeyword.trim(),'gi')
						detail.announcementList= res.data.returnData.Data.map(item => {
							item.title = item.title.replace(reg, str => '<span style="color:#F32D33">'+str+'</span>')
							return item
						})
					}else{
						detail.announcementList= res.data.returnData.Data
					}
					
					detail.totalPageCount5 = detail.getPageTotal5(detail.AnnouncementRecords);
					detail.init5();
					$("#announcementToolBar").show();
				}else{
					$("#noAnnouncement").show();
					detail.announcementList = []
					$("#announcementToolBar").hide();
				}
			})
		},
		getEclassList:function(num){
			var _this=this;
			axios({
				method: 'Get',
				url: `/casch/homePageExt?method=findAllEclass&enName=${$(".content-tit2")[0].innerHTML}&currentNo=${(num-1)}&pageSize=6&keyword=${this.serchKeyword.trim().toLocaleUpperCase()}`,
				headers: {"Content-Type": "application/json"}
			}).then(function (res) {
				_this.EclasstotalRecords = res.data.returnData.Page.totalRecords || 0;
				if(res.data.returnData.Data.length == 0){
					$("#novideos").show();
					$("#videosToolBar").hide();
					_this.eclassList = []
				}else{
					$("#novideos").hide();
					if(_this.serchKeyword.trim().length > 0){
						let reg = new RegExp(_this.serchKeyword.trim(),'gi')
						_this.eclassList = res.data.returnData.Data.map(item => {
							item.title = item.title.replace(reg, str => '<span style="color:#F32D33">'+str+'</span>')
							return item
						})
					}else{
						_this.eclassList = res.data.returnData.Data
					}
					
					_this.totalPageCount4 = _this.getPageTotal4(_this.EclasstotalRecords);
					_this.init4();
					$("#videosToolBar").show();
				}
			});
		},
		showMore:function(){
			this.num=this.num+6;
		},
		showMoreEclass:function(){
			this.eclassnum=this.eclassnum+6;
		},
		clearMore:function(){
			this.num=6;
		},
		clearMoreEclass:function(){
			this.eclassnum=6;
		},
		getCompatibleOne:function(){
			this.current3=9999;
			this.enName=$(".content-tit2")[0].innerHTML;
			axios({
				method:'Get',
				url:"/casch/outCompatible?method=findMakerByPro&productModel="+ encodeURIComponent($(".content-tit2")[0].innerHTML),
				headers:{"Content-Type":"application/json"}
			}).then(function(res){
				detail.maker=res.data.returnData.Data;
			})
		},
		getList:function(e,number){

			if(this.currentOne != number){
				/*this.cShow=0;*/
				$(".compatibility-model").hide();
				$(".select-div-two-ul").slideUp();
				this.currentOne=number;
				this.current2=9999;
				var path=encodeURIComponent(e.target.getAttribute("path"));
				$("#make").html(e.target.innerHTML);
				setTimeout(function(){
					axios({
						method:'Get',
						url:"/casch/outCompatible?method=findListByMaker&path="+path,
						headers:{"Content-Type":"application/json"}
					}).then(function(res){
						/*index.category=res.data.returnData.Data;*/
						detail.proModel=res.data.returnData.Data;
						/*$(".select-div-two-ul").height((detail.proModel.length*62)+"px");    */
						$("#pro").html("选择详细分类");
						$(".select-div-ul").slideUp();
						setTimeout(function(){
							$(".select-div-two-ul").slideDown();
							$(".select-div-two-ul").scrollTop(0);
						},0)

					})
				},0)
			}
		},
		checkOneSelect:function(){
			$(".select-div-ul").slideToggle();
		},
		checkTwoSelect:function(){
			$(".select-div-two-ul").slideToggle();
		},
		getDetail:function(e,num){
			$(".compatibility-model").show();
			/*this.cShow=1;*/
			/*$(".select-div-two-ul").slideToggle();*/
			var path=e.target.getAttribute("path");
			$("#pro").html(e.target.innerHTML);
			$("#pro").attr('title',e.target.innerHTML);
			$(".compatibility-model-title").html(e.target.innerHTML);
			//解决传值中加号被省略
			path=encodeURIComponent(path);
			axios({
				method:'Get',
				url:"/casch/outCompatible?method=findByModel&path="+path,
				headers:{"Content-Type":"application/json"}
			}).then(function(res){
				/*index.category=res.data.returnData.Data;*/
				detail.levelOneList=res.data.returnData.compatibilityLevelTwoList;

				$(".select-div-two-ul").slideUp();

			})
		},
		onScroll:function() {
			let scrolled = document.documentElement.scrollTop || document.body.scrollTop
			/*var baseHeight = 460;*/
			var baseHeight = $("#fix-nav").height()+$(".header").height()+$("#modelTitle").height()+50;
			var li = $(".fix-nav-ul li");
			var downloadHeight = $("#download-c").height();
			var announceHeight = $("#announcement-c").height();
			var eclassHeight = $("#videos").height();
			var qaHeight = $("#qa-c").height();
			var adaptHeight = $("#adaptation-c").height();
			var faqHeight = $("#faq-c").height();
			if(scrolled <baseHeight+downloadHeight){
				// 通知与公告
				this.currentLi = 0;
			}else if(scrolled <baseHeight+downloadHeight+announceHeight){
				// 常见问题解答
				this.currentLi = 1;
			}else if(scrolled < baseHeight+downloadHeight+announceHeight+eclassHeight){
				// 适配性
				this.currentLi = 2;
			}else if(scrolled < baseHeight+downloadHeight+announceHeight+eclassHeight+qaHeight){
				this.currentLi = 3;
			}else if(scrolled < baseHeight+downloadHeight+announceHeight+eclassHeight+qaHeight+adaptHeight){
				this.currentLi = 4;
			}else if(scrolled < baseHeight+downloadHeight+announceHeight+eclassHeight+qaHeight+adaptHeight+faqHeight){
				this.currentLi = 5;
			}else{
				this.currentLi = 6;
			}
			// 586、1063分别为第二个和第三个锚点对应的距离
			if (scrolled >= 1063) {
			} else if (scrolled < 1063 && scrolled >= 586) {
			} else {
			}
		},
		getNavWidth2:function(count){
			// var $nav = $("#toolBar nav");
			// if(count<9){
			// 	var width = $nav.find("li").width();       //获取nav的宽度
			// 	var new_width=width*(count+2);
			// 	$nav.css("width", new_width);
			// }else{
			// 	$nav.css("width", "420px");
			// }
		},
		getNavWidth:function(count,obj){
//    		    	var $nav = $(".toolBar nav");
			if(count<9){
				var width = obj.find("li").width();       //获取nav的宽度
				var new_width=width*(count+2);
				obj.css("width", new_width);
			}else{
				obj.css("width", "420px");
			}
		},
		getPageTotal2:function(data){
			var _this=this;
			return Math.floor(data / _this.pageSize2) + ((data % _this.pageSize2) == 0 ? 0 : 1);
		},
		getPageTotal:function(data) {
			var _this=this;
			return Math.floor(data / _this.pageSize) + ((data % _this.pageSize) == 0 ? 0 : 1);
		},
		getPageTotal3:function(data) {
			var _this=this;
			return Math.floor(data / _this.pageSize3) + ((data % _this.pageSize3) == 0 ? 0 : 1);
		},
		getPageTotal4:function(data) {
			var _this=this;
			return Math.floor(data / _this.pageSize4) + ((data % _this.pageSize4) == 0 ? 0 : 1);
		},
		getPageTotal5:function(data) {
			var _this=this;
			return Math.floor(data / _this.pageSize5) + ((data % _this.pageSize5) == 0 ? 0 : 1);
		},
		// 跳转到某页码
		next :function(num,type) {
			var that = this;
			if(type == "download"){
				if (num <= 1) that.currentPage2 = 1;
				else if (num >= that.totalPageCount2) that.currentPage2 = that.totalPageCount2;
				else that.currentPage2 = num;
				that.getDownloadList(that.downType,that.current,that.currentPage2);
			}else if(type == "trouble"){
				if (num <= 1) that.currentPage = 1;
				else if (num >= that.totalPageCount) that.currentPage = that.totalPageCount;
				else that.currentPage = num;
				that.getTroubleList(that.currentPage);
			}else if(type == "faq"){
				if (num <= 1) that.currentPage3 = 1;
				else if (num >= that.totalPageCount3) that.currentPage3 = that.totalPageCount3;
				else that.currentPage3 = num;
				that.getFaqList(that.currentPage3);
			}else if(type == "videos"){
				if (num <= 1) that.currentPage4 = 1;
				else if (num >= that.totalPageCount4) that.currentPage4 = that.totalPageCount4;
				else that.currentPage4 = num;
				this.getEclassList(that.currentPage4);
			}else if(type == "announcement"){
				if (num <= 1) that.currentPage5 = 1;
				else if (num >= that.totalPageCount5) that.currentPage5 = that.totalPageCount5;
				else that.currentPage5 = num;
				this.getAnnouncementList(that.currentPage5);
			
			}
		},
		fetchData2 :function(){
			var that=this;
			that.pagingList2 = [];
			var tmp = null;
			if ((that.totalPageCount2) > 8) {
				if (((that.totalPageCount2-1) == (that.totalPageCount2 - that.currentPage2)) && (that.totalPageCount2 - that.currentPage2) > 5) {
					for (var i=1;i<9;i++) {
						if (i < that.signIndex) {
							tmp = {key:i, value:i }
						} else if (i== that.signIndex) {
							tmp = {key:that.sign, value:0 }
						} else if (i == (that.signIndex + 1) ) {
							tmp = {key:that.totalPageCount2 - 1, value:that.totalPageCount2 - 1 }
						} else {
							tmp = {key:that.totalPageCount2, value:that.totalPageCount2 }
						}
						that.pagingList2.push(tmp);
					}
				} else if (((that.totalPageCount2 - that.currentPage2) <= that.signIndex)){
					var starNum = that.totalPageCount2 - 7;
					for (var i=starNum;i<starNum + 8;i++) {
						tmp = {"key":i, "value":i };
						that.pagingList2.push(tmp);
					}
				} else {
					var starNum = that.currentPage2 - 1;
					for (var i=1;i<9;i++) {
						if (i < that.signIndex) {
							tmp = {key:(starNum - 1) + i, value:(starNum - 1) + i }
						} else if (i== that.signIndex) {
							tmp = {key:that.sign, value:0 }
						} else if (i == (that.signIndex + 1) ) {
							tmp = {key:that.totalPageCount2 - 1, value:that.totalPageCount2 - 1 }
						} else {
							tmp = {key:that.totalPageCount2, value:that.totalPageCount2 }
						}
						that.pagingList2.push(tmp);
					}
				}
			} else {
				for (var i =0; i <that.totalPageCount2; i++) {
					tmp = {"key":i+1, "value":i+1 };
					that.pagingList2.push(tmp);
				}
			}
		},
		// 初始化数据
		fetchData :function() {
			var that = this;
			that.pagingList = [];
			var tmp = null;
			if ((that.totalPageCount) > 8) {
				if (((that.totalPageCount-1) == (that.totalPageCount - that.currentPage)) && (that.totalPageCount - that.currentPage) > 5) {
					for (var i=1;i<9;i++) {
						if (i < that.signIndex) {
							tmp = {key:i, value:i }
						} else if (i== that.signIndex) {
							tmp = {key:that.sign, value:0 }
						} else if (i == (that.signIndex + 1) ) {
							tmp = {key:that.totalPageCount - 1, value:that.totalPageCount - 1 }
						} else {
							tmp = {key:that.totalPageCount, value:that.totalPageCount }
						}
						that.pagingList.push(tmp);
					}
				} else if (((that.totalPageCount - that.currentPage) <= that.signIndex)){
					var starNum = that.totalPageCount - 7;
					for (var i=starNum;i<starNum + 8;i++) {
						tmp = {"key":i, "value":i };
						that.pagingList.push(tmp);
					}
				} else {
					var starNum = that.currentPage - 1;
					for (var i=1;i<9;i++) {
						if (i < that.signIndex) {
							tmp = {key:(starNum - 1) + i, value:(starNum - 1) + i }
						} else if (i== that.signIndex) {
							tmp = {key:that.sign, value:0 }
						} else if (i == (that.signIndex + 1) ) {
							tmp = {key:that.totalPageCount - 1, value:that.totalPageCount - 1 }
						} else {
							tmp = {key:that.totalPageCount, value:that.totalPageCount }
						}
						that.pagingList.push(tmp);
					}
				}
			} else {
				for (var i =0; i <that.totalPageCount; i++) {
					tmp = {"key":i+1, "value":i+1 };
					that.pagingList.push(tmp);
				}
			}

		},
		// 初始化数据
		fetchData3 :function() {
			var that = this;
			that.pagingList3 = [];
			var tmp = null;
			if ((that.totalPageCount3) > 8) {
				if (((that.totalPageCount3-1) == (that.totalPageCount3 - that.currentPage3)) && (that.totalPageCount3 - that.currentPage3) > 5) {
					for (var i=1;i<9;i++) {
						if (i < that.signIndex) {
							tmp = {key:i, value:i }
						} else if (i== that.signIndex) {
							tmp = {key:that.sign, value:0 }
						} else if (i == (that.signIndex + 1) ) {
							tmp = {key:that.totalPageCount3 - 1, value:that.totalPageCount3 - 1 }
						} else {
							tmp = {key:that.totalPageCount3, value:that.totalPageCount3 }
						}
						that.pagingList3.push(tmp);
					}
				} else if (((that.totalPageCount3 - that.currentPage3) <= that.signIndex)){
					var starNum = that.totalPageCount3 - 7;
					for (var i=starNum;i<starNum + 8;i++) {
						tmp = {"key":i, "value":i };
						that.pagingList3.push(tmp);
					}
				} else {
					var starNum = that.currentPage3 - 1;
					for (var i=1;i<9;i++) {
						if (i < that.signIndex) {
							tmp = {key:(starNum - 1) + i, value:(starNum - 1) + i }
						} else if (i== that.signIndex) {
							tmp = {key:that.sign, value:0 }
						} else if (i == (that.signIndex + 1) ) {
							tmp = {key:that.totalPageCount3 - 1, value:that.totalPageCount3 - 1 }
						} else {
							tmp = {key:that.totalPageCount3, value:that.totalPageCount3 }
						}
						that.pagingList3.push(tmp);
					}
				}
			} else {
				for (var i =0; i <that.totalPageCount3; i++) {
					tmp = {"key":i+1, "value":i+1 };
					that.pagingList3.push(tmp);
				}
			}

		},
		// 初始化数据
		fetchData4 :function() {
			var that = this;
			that.pagingList4 = [];
			var tmp = null;
			if ((that.totalPageCount4) > 8) {
				if (((that.totalPageCount4-1) == (that.totalPageCount4 - that.currentPage4)) && (that.totalPageCount4 - that.currentPage4) > 5) {
					for (var i=1;i<9;i++) {
						if (i < that.signIndex) {
							tmp = {key:i, value:i }
						} else if (i== that.signIndex) {
							tmp = {key:that.sign, value:0 }
						} else if (i == (that.signIndex + 1) ) {
							tmp = {key:that.totalPageCount4 - 1, value:that.totalPageCount4 - 1 }
						} else {
							tmp = {key:that.totalPageCount4, value:that.totalPageCount4 }
						}
						that.pagingList4.push(tmp);
					}
				} else if (((that.totalPageCount4 - that.currentPage4) <= that.signIndex)){
					var starNum = that.totalPageCount4 - 7;
					for (var i=starNum;i<starNum + 8;i++) {
						tmp = {"key":i, "value":i };
						that.pagingList4.push(tmp);
					}
				} else {
					var starNum = that.currentPage4 - 1;
					for (var i=1;i<9;i++) {
						if (i < that.signIndex) {
							tmp = {key:(starNum - 1) + i, value:(starNum - 1) + i }
						} else if (i== that.signIndex) {
							tmp = {key:that.sign, value:0 }
						} else if (i == (that.signIndex + 1) ) {
							tmp = {key:that.totalPageCount4 - 1, value:that.totalPageCount4 - 1 }
						} else {
							tmp = {key:that.totalPageCount4, value:that.totalPageCount4 }
						}
						that.pagingList4.push(tmp);
					}
				}
			} else {
				for (var i =0; i <that.totalPageCount4; i++) {
					tmp = {"key":i+1, "value":i+1 };
					that.pagingList4.push(tmp);
				}
			}

		},
		// 初始化数据
		fetchData5 :function() {
			var that = this;
			that.pagingList5 = [];
			var tmp = null;
			if ((that.totalPageCount5) > 8) {
				if (((that.totalPageCount5-1) == (that.totalPageCount5 - that.currentPage5)) && (that.totalPageCount5 - that.currentPage5) > 5) {
					for (var i=1;i<9;i++) {
						if (i < that.signIndex) {
							tmp = {key:i, value:i }
						} else if (i== that.signIndex) {
							tmp = {key:that.sign, value:0 }
						} else if (i == (that.signIndex + 1) ) {
							tmp = {key:that.totalPageCount5 - 1, value:that.totalPageCount5 - 1 }
						} else {
							tmp = {key:that.totalPageCount5, value:that.totalPageCount5 }
						}
						that.pagingList5.push(tmp);
					}
				} else if (((that.totalPageCount5 - that.currentPage5) <= that.signIndex)){
					var starNum = that.totalPageCount5 - 7;
					for (var i=starNum;i<starNum + 8;i++) {
						tmp = {"key":i, "value":i };
						that.pagingList5.push(tmp);
					}
				} else {
					var starNum = that.currentPage5 - 1;
					for (var i=1;i<9;i++) {
						if (i < that.signIndex) {
							tmp = {key:(starNum - 1) + i, value:(starNum - 1) + i }
						} else if (i== that.signIndex) {
							tmp = {key:that.sign, value:0 }
						} else if (i == (that.signIndex + 1) ) {
							tmp = {key:that.totalPageCount5 - 1, value:that.totalPageCount5 - 1 }
						} else {
							tmp = {key:that.totalPageCount5, value:that.totalPageCount5 }
						}
						that.pagingList5.push(tmp);
					}
				}
			} else {
				for (var i =0; i <that.totalPageCount5; i++) {
					tmp = {"key":i+1, "value":i+1 };
					that.pagingList5.push(tmp);
				}
			}
		},
		fetchDataManual:function(){
			var that = this;
			that.pagingListManual = [];
			var tmp = null;
			if ((that.totalPageCountManual) > 8) {
				if (((that.totalPageCountManual - 1) == (that.totalPageCountManual - that.currentPageManual))&& (that.totalPageCountManual - that.currentPageManual) > 5) {
					for (var i = 1; i < 9; i++) {
						if (i < that.signIndex) {
							tmp = {
								key : i,
								value : i
							}
						} else if (i == that.signIndex) {
							tmp = {
								key : that.sign,
								value : 0
							}
						} else if (i == (that.signIndex + 1)) {
							tmp = {
								key : that.totalPageCountManual - 1,
								value : that.totalPageCountManual - 1
							}
						} else {
							tmp = {
								key : that.totalPageCountManual,
								value : that.totalPageCountManual
							}
						}
						that.pagingListManual.push(tmp);
					}
				} else if (((that.totalPageCountManual - that.currentPageManual) <= that.signIndex)) {
					var starNum = that.totalPageCountManual - 7;
					for (var i = starNum; i < starNum + 8; i++) {
						tmp = {
							"key" : i,
							"value" : i
						};
						that.pagingListManual.push(tmp);
					}
				} else {
					var starNum = that.currentPageManual - 1;
					for (var i = 1; i < 9; i++) {
						if (i < that.signIndex) {
							tmp = {
								key : (starNum - 1) + i,
								value : (starNum - 1) + i
							}
						} else if (i == that.signIndex) {
							tmp = {
								key : that.sign,
								value : 0
							}
						} else if (i == (that.signIndex + 1)) {
							tmp = {
								key : that.totalPageCountManual - 1,
								value : that.totalPageCountManual - 1
							}
						} else {
							tmp = {
								key : that.totalPageCountManual,
								value : that.totalPageCountManual
							}
						}
						that.pagingListManual.push(tmp);
					}
				}
			} else {
				for (var i = 0; i < that.totalPageCountManual; i++) {
					tmp = {
						"key" : i + 1,
						"value" : i + 1
					};
					that.pagingListManual.push(tmp);
				}
			}
		},
		init2:function(){
			var that = this;
			that.fetchData2();
		},
		init:function () {
			var that = this;
			that.fetchData()
		},
		init3:function () {
			var that = this;
			that.fetchData3()
		},
		init4:function () {
			var that = this;
			that.fetchData4()
		},
		init5:function () {
			var that = this;
			that.fetchData5()
		},
		initManual:function () {
			var that = this;
			that.fetchDataManual()
		},
		toTheTroubleDetail:function(id){
			window.location.href="/content/casch/troubleshooting/"+id+".html"
		},
		toDownload:function(id,type){
			if(type=="SONY_CASCH_DOWNLOAD_FIRM"){
				window.location.href="/content/casch/download/firm/"+id+".html"
			}else if(type=="SONY_CASCH_DOWNLOAD_DRIVER"){
				window.location.href="/content/casch/download/driver/"+id+".html"
			}else if(type=="SONY_CASCH_DOWNLOAD_SOFTWARE"){
				window.location.href="/content/casch/download/software/"+id+".html"
			}else if(type=="SONY_CASCH_DOWNLOAD_GUIDE"){
				window.location.href="/content/casch/download/guide/"+id+".html"
			}
		},
		showPopup:function(paths){
			var path=paths?paths[0]:"#";
			$(".g_buy")[0].setAttribute("href",path);
			//获取页面的实际高度和宽度
			var hei = $(document).height();
			var wid = $(document).width();
			$("#background_div").css("width",wid);
			$("#background_div").css("height",hei);
			$("#popup_div").show();
		},
		formatDate:function (date, datePattern){
			var longDate = new Date(date);
			if (isNaN(longDate)) {
				var formattedDate = '';
			} else {
				var yyyy = longDate.getFullYear().toString();
				var mm = (longDate.getMonth() + 1).toString();
				var dd = longDate.getDate().toString();
				mm = mm.length > 1 ? mm : '0' + mm;
				dd = dd.length > 1 ? dd : '0' + dd;
				formattedDate = datePattern ? datePattern.replace('yyyy', yyyy).replace('MM', mm).replace('dd', dd) : '';
			}
			return formattedDate;
		},
		getBuyFromSonystyle:function(){
			axios({
				method: 'Get',
				url: "/casch/out?method=findBuyFromSonyStyle&enName="+$(".content-tit2")[0].innerHTML,
				headers: {"Content-Type": "application/json"}
			}).then(function(res){
				if(res.data.returnData.Data){
					$("#pathFromSonystyle").attr("href",res.data.returnData.Data+".html");
				}
			})

		}


	}
})