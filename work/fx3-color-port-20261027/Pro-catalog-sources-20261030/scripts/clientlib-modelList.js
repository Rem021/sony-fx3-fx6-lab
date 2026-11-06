
var modelList = new Vue({
	el:"#modelList",
	data:{
		product:[],
		category:[],
		categoryPath:"",
		subCategory:[],
		subCategoryPath:"",
		series:[],
		seriesPath:"",
		product:[],
		productPath:"",
		current:-1,
		current2:-1,
		current3:-1,
		index:-1,
		ca:"",
		su:"",
		se:"",
		pdp:"",
		productCategoryShow:false,
		productModelShow:false
	},
	created:function(){
		console.log(this)
		this.getCategoryList(0);
	},
	mounted(){
		$('.modelListInput-list1').hide()
		$('.modelListInput-list2').hide()
	},
	methods:{
		productCategory(){
			
			$('.modelListInput1 img').attr("src",'/etc/designs/casch/images/newHome/topArrow.png')
			$('.modelListInput1').css('border', '1px solid #0090E2')
			
			$('.modelListInput2 img').attr("src",'/etc/designs/casch/images/newHome/bottomArrow.png')
			$('.modelListInput2').css('border', '#ddd')
			$('.modelListInput-list1').show()
			$('.modelListInput-list2').hide()
		},
		productModel(){
			$('.modelListInput2 img').attr("src",'/etc/designs/casch/images/newHome/topArrow.png')
			$('.modelListInput2').css('border', '1px solid #0090E2')

			$('.modelListInput1').css('border', '#ddd')
			$('.modelListInput1 img').attr("src",'/etc/designs/casch/images/newHome/bottomArrow.png')
			$('.modelListInput-list1').hide()
			$('.modelListInput-list2').show()
		},
		getCategoryList:function(num){
			var _this=this;
			_this.current=num;
			console.log(_this.current);
			axios({
				method:'Get',
				url:"/casch/outProduct?method=findCateList",
				headers:{"Content-Type":"application/json"}
			}).then(function(res){
				_this.category=res.data.returnData.Data;
				console.log(_this.category);
				_this.getSubList(null,0,true);
				$(".productmodel").removeClass("check");
			})
		},
		getSubList:function(e,num,boolean){
			var _this=this;
			_this.current=num;
			_this.categoryPath=boolean?this.category[0].path:e.target.getAttribute("path");
			_this.ca = boolean?this.category[0].cnName:e.target.innerHTML;
			var link="/casch/outProduct?method=findSubList&category="+encodeURI(this.categoryPath);
			axios({
				method:'Get',
				url:link,
				headers:{"Content-Type":"application/json"}
			}).then(function(res){
				if(res.data.code=="00"&&res.data.result==true){
					let gujian = res.data.returnData.Data.filter(item => item.enName == '配件')
					let gujianIndex =  res.data.returnData.Data.findIndex(item => item.enName == '配件')
					if(gujianIndex > -1 && (encodeURI(_this.categoryPath) == '/etc/commerce/products/casch/pim/category/tv' || encodeURI(_this.categoryPath) == '/etc/commerce/products/casch/pim/category/pa')){
						res.data.returnData.Data.splice(gujianIndex,1)
						_this.subCategory = [...res.data.returnData.Data, ...gujian];
					}else{
						_this.subCategory = res.data.returnData.Data;
					}
					// _this.subCategory=res.data.returnData.Data;
		            _this.getSeries(null,_this.index,true);
		            $(".productmodel").removeClass("check");
				}
			})
		},
		getSeries:function(e,num,boolean){
			var _this=this;
			_this.current2=num;
			if(boolean==true){
				_this.subCategoryPath=_this.subCategory[0].path;
			}else{
				_this.subCategoryPath=e.target.getAttribute("path");
			}
			_this.su =boolean?this.subCategory[0].enName:e.target.innerHTML;
			if(!boolean){
				$('.modelListInput1 span').text(e.target.innerHTML).css("color","#111")
				$('.modelListInput2 span').text('请选择')
				$('.modelListInput-list1').hide()
				$('.modelListInput1').css('border', '#DDD')
				$('.modelListInput1 img').attr("src",'/etc/designs/casch/images/newHome/bottomArrow.png')
			}
			var link="/casch/outProduct?method=findSeriesList&subCategory="+encodeURI(this.subCategoryPath);
			axios({
				method:'Get',
				url:link,
				headers:{"Content-Type":"application/json"}
			}).then(function(res){
				if(res.data.code=="00"&&res.data.result==true){
					_this.series=res.data.returnData.Data;
					_this.getProList(null,_this.index,true);
					$(".productmodel").removeClass("check");
				}
			})
		},
		getProList:function(e,num,boolean){
			var _this=this;
			_this.current3=num;
			if(boolean==true){
				_this.seriesPath=_this.series[0].path;
			}else{
				_this.seriesPath=e.target.getAttribute("path");
			}
			_this.se =boolean?this.series[0].enName:e.target.innerHTML;
			_this.pdp = _this.ca + ":" + _this.su + ":" + _this.se;
			console.log(_this.pdp);
			var link="/casch/outProduct?method=findProList&series="+encodeURI(this.seriesPath);
			axios({
				method:'Get',
				url:link,
				headers:{"Content-Type":"application/json"}
			}).then(function(res){
				if(res.data.code=="00"&&res.data.result==true){
					_this.product=res.data.returnData.Data;
					$(".productmodel").removeClass("check");
				}
			})
		},
	}
})