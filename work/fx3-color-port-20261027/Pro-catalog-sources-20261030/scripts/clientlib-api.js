var $jscomp=$jscomp||{};$jscomp.scope={};$jscomp.ASSUME_ES5=!1;$jscomp.ASSUME_NO_NATIVE_MAP=!1;$jscomp.ASSUME_NO_NATIVE_SET=!1;$jscomp.defineProperty=$jscomp.ASSUME_ES5||"function"==typeof Object.defineProperties?Object.defineProperty:function(a,c,d){a!=Array.prototype&&a!=Object.prototype&&(a[c]=d.value)};$jscomp.getGlobal=function(a){return"undefined"!=typeof window&&window===a?a:"undefined"!=typeof global&&null!=global?global:a};$jscomp.global=$jscomp.getGlobal(this);$jscomp.SYMBOL_PREFIX="jscomp_symbol_";
$jscomp.initSymbol=function(){$jscomp.initSymbol=function(){};$jscomp.global.Symbol||($jscomp.global.Symbol=$jscomp.Symbol)};$jscomp.Symbol=function(){var a=0;return function(c){return $jscomp.SYMBOL_PREFIX+(c||"")+a++}}();
$jscomp.initSymbolIterator=function(){$jscomp.initSymbol();var a=$jscomp.global.Symbol.iterator;a||(a=$jscomp.global.Symbol.iterator=$jscomp.global.Symbol("iterator"));"function"!=typeof Array.prototype[a]&&$jscomp.defineProperty(Array.prototype,a,{configurable:!0,writable:!0,value:function(){return $jscomp.arrayIterator(this)}});$jscomp.initSymbolIterator=function(){}};$jscomp.arrayIterator=function(a){var c=0;return $jscomp.iteratorPrototype(function(){return c<a.length?{done:!1,value:a[c++]}:{done:!0}})};
$jscomp.iteratorPrototype=function(a){$jscomp.initSymbolIterator();a={next:a};a[$jscomp.global.Symbol.iterator]=function(){return this};return a};$jscomp.makeIterator=function(a){$jscomp.initSymbolIterator();var c=a[Symbol.iterator];return c?c.call(a):$jscomp.arrayIterator(a)};
$jscomp.polyfill=function(a,c,d,e){if(c){d=$jscomp.global;a=a.split(".");for(e=0;e<a.length-1;e++){var b=a[e];b in d||(d[b]={});d=d[b]}a=a[a.length-1];e=d[a];c=c(e);c!=e&&null!=c&&$jscomp.defineProperty(d,a,{configurable:!0,writable:!0,value:c})}};$jscomp.FORCE_POLYFILL_PROMISE=!1;
$jscomp.polyfill("Promise",function(a){function c(){this.batch_=null}function d(a){return a instanceof b?a:new b(function(f,b){f(a)})}if(a&&!$jscomp.FORCE_POLYFILL_PROMISE)return a;c.prototype.asyncExecute=function(a){null==this.batch_&&(this.batch_=[],this.asyncExecuteBatch_());this.batch_.push(a);return this};c.prototype.asyncExecuteBatch_=function(){var a=this;this.asyncExecuteFunction(function(){a.executeBatch_()})};var e=$jscomp.global.setTimeout;c.prototype.asyncExecuteFunction=function(a){e(a,
0)};c.prototype.executeBatch_=function(){for(;this.batch_&&this.batch_.length;){var a=this.batch_;this.batch_=[];for(var b=0;b<a.length;++b){var c=a[b];delete a[b];try{c()}catch(k){this.asyncThrow_(k)}}}this.batch_=null};c.prototype.asyncThrow_=function(a){this.asyncExecuteFunction(function(){throw a;})};var b=function(a){this.state_=0;this.result_=void 0;this.onSettledCallbacks_=[];var f=this.createResolveAndReject_();try{a(f.resolve,f.reject)}catch(h){f.reject(h)}};b.prototype.createResolveAndReject_=
function(){function a(a){return function(f){c||(c=!0,a.call(b,f))}}var b=this,c=!1;return{resolve:a(this.resolveTo_),reject:a(this.reject_)}};b.prototype.resolveTo_=function(a){if(a===this)this.reject_(new TypeError("A Promise cannot resolve to itself"));else if(a instanceof b)this.settleSameAsPromise_(a);else{a:switch(typeof a){case "object":var f=null!=a;break a;case "function":f=!0;break a;default:f=!1}f?this.resolveToNonPromiseObj_(a):this.fulfill_(a)}};b.prototype.resolveToNonPromiseObj_=function(a){var b=
void 0;try{b=a.then}catch(h){this.reject_(h);return}"function"==typeof b?this.settleSameAsThenable_(b,a):this.fulfill_(a)};b.prototype.reject_=function(a){this.settle_(2,a)};b.prototype.fulfill_=function(a){this.settle_(1,a)};b.prototype.settle_=function(a,b){if(0!=this.state_)throw Error("Cannot settle("+a+", "+b|"): Promise already settled in state"+this.state_);this.state_=a;this.result_=b;this.executeOnSettledCallbacks_()};b.prototype.executeOnSettledCallbacks_=function(){if(null!=this.onSettledCallbacks_){for(var a=
this.onSettledCallbacks_,b=0;b<a.length;++b)a[b].call(),a[b]=null;this.onSettledCallbacks_=null}};var g=new c;b.prototype.settleSameAsPromise_=function(a){var b=this.createResolveAndReject_();a.callWhenSettled_(b.resolve,b.reject)};b.prototype.settleSameAsThenable_=function(a,b){var c=this.createResolveAndReject_();try{a.call(b,c.resolve,c.reject)}catch(k){c.reject(k)}};b.prototype.then=function(a,c){function f(a,b){return"function"==typeof a?function(b){try{d(a(b))}catch(l){e(l)}}:b}var d,e,g=new b(function(a,
b){d=a;e=b});this.callWhenSettled_(f(a,d),f(c,e));return g};b.prototype.catch=function(a){return this.then(void 0,a)};b.prototype.callWhenSettled_=function(a,b){function c(){switch(d.state_){case 1:a(d.result_);break;case 2:b(d.result_);break;default:throw Error("Unexpected state: "+d.state_);}}var d=this;null==this.onSettledCallbacks_?g.asyncExecute(c):this.onSettledCallbacks_.push(function(){g.asyncExecute(c)})};b.resolve=d;b.reject=function(a){return new b(function(b,c){c(a)})};b.race=function(a){return new b(function(b,
c){for(var e=$jscomp.makeIterator(a),f=e.next();!f.done;f=e.next())d(f.value).callWhenSettled_(b,c)})};b.all=function(a){var c=$jscomp.makeIterator(a),e=c.next();return e.done?d([]):new b(function(a,b){function f(b){return function(c){g[b]=c;h--;0==h&&a(g)}}var g=[],h=0;do g.push(void 0),h++,d(e.value).callWhenSettled_(f(g.length-1),b),e=c.next();while(!e.done)})};return b},"es6","es3");window._api={};
var apiDomain="",apiShopOrder="",apiShopCar="",apiSearch="",apiLive="",kfapiDomain=-1<window.location.host.indexOf("pet")?"https://pet.sonystyle.com.cn/":"https://www.sonystyle.com.cn/";
_api.HybrisAPI={login:function(){return apiDomain+"/eSolverOmniChannel/account/login.do"},logout:function(a){return apiShopCar+"/eSolverOmniChannel/account/logout.do?access_token\x3d"+a},readCart:function(a){return apiShopCar+"/eSolverOmniChannel/order/readCart.do?access_token\x3d"+a+"\x26channel\x3dWEB"},addToBasket:function(a){return apiShopCar+"/eSolverOmniChannel/order/addToBasket.do?access_token\x3d"+a+"\x26channel\x3dWEB"},getMemberInfo:function(a){return apiShopCar+"/eSolverOmniChannel/account/getMemberInfo.do?access_token\x3d"+
a+"\x26channel\x3dWEB"},getPersonalDetails:function(a){return apiShopCar+"/eSolverOmniChannel/account/getPersonalDetails.do"},changeCart:function(a){return apiShopCar+"/eSolverOmniChannel/order/changeCart.do?access_token\x3d"+a+"\x26channel\x3dWEB"},checkout:function(a){return apiShopCar+"/eSolverOmniChannel/order/checkout.do?access_token\x3d"+a+"\x26channel\x3dWEB"},miniCartDisplay:function(a){return apiShopCar+"/eSolverOmniChannel/order/miniCartDisplay.do?access_token\x3d"+a+"\x26channel\x3dWEB"},
displayCaptcha:function(){return apiShopCar+"/eSolverOmniChannel/account/displayCaptcha.do"},register:function(){return apiShopCar+"/eSolverOmniChannel/account/register.do"},sendOTP:function(){return apiShopCar+"/eSolverOmniChannel/account/sendOTP.do"},isMobileAvailable:function(){return apiShopCar+"/eSolverOmniChannel/account/isMobileAvailable.do"},isEmailIdExists:function(){return apiShopCar+"/eSolverOmniChannel/account/isEmailIdExists.do"},masterData:function(a){return apiShopCar+"/eSolverOmniChannel/masterData/cityMaster.do?access_token\x3d"+
a}};

_api.search = {
	getsearchresult: function() {
		return apiSearch + "/b2csearch/esapi/product/getsearchresult"
	},
	autosuggestion: function() {
		return apiSearch + "/b2csearch/esapi/keyword/autosuggestion/"
	},
	getCheckHeaderCouponValid: function() {
		return apiSearch + "/b2csearch/esapi/coupon/check"
	},
	similar: function() {
		return apiSearch + "/b2csearch/esapi/keyword/similar/"
	},
	getAbout: function() {
		return apiSearch + "https://www.sonystyle.com.cn/ssoapps/recom/omniapp/recommend/recommend/fetch"
	},
	price: function() {
		return apiSearch + "/b2csearch/esapi/product/price"
	},
	pricepromotion: function() {
		return apiSearch + "/b2csearch/esapi/product/pricepromotion"
	},
	multipricepromotion: function() {
		return apiSearch + "/b2csearch/esapi/product/multipricepromotion"
	},
	getArea: function(a) {
		return apiSearch + "/b2csearch/esapi/area/areas?parentcode\x3d" + a
	},
	getCouponByProduct8D: function() {
		return apiSearch + "/b2csearch/esapi/coupon/getcouponbyproduct8D"
	},
	getIsInstallmentProduct: function() {
		return apiSearch + "/b2csearch/esapi/installment/getRecommendInstallmentList"
	},
	getInstallmentList: function() {
		return apiSearch +
			"/b2csearch/esapi/installment/getInstallmentList"
	},
	getRecommendInstallmentList: function() {
		return apiSearch + "/b2csearch/esapi/installment/getRecommendInstallmentList"
	},
	getStatue: function() {
		return apiDomain + "/b2csearch/esapi/product/productsaleinfo"
	}
};

_api.Nps={clientAuthentic:function(a){return kfapiDomain+"/service/aicustomerservice/authentic/clientAuthentic"},aiLog:function(a){return kfapiDomain+"/service/aicustomerservice/log/saveLog"}};function query(a,c,d,e){$.ajax({url:a,contentType:"application/json; charset\x3dUTF-8",type:"post",async:"undefined"===typeof e?!1:!0,data:JSON.stringify(c),dataType:"json",success:function(a){d(a)}})}
function queryGet(a,c,d){$.ajax({url:a,contentType:"application/json; charset\x3dUTF-8",type:"get",async:"undefined"===typeof d?!1:!0,dataType:"json",success:function(a){c(a)}})}function queryPromise(a,c){return new Promise(function(d,e){$.ajax({url:a,contentType:"application/json; charset\x3dUTF-8",type:"post",data:JSON.stringify(c),dataType:"json",success:function(a){a.result&&d(a)}})})}
function queryPromiseWithAuth(a,c,d){return new Promise(function(e,b){$.ajax({url:a,contentType:"application/json; charset\x3dUTF-8",type:"post",data:JSON.stringify(c),beforeSend:function(a){a.setRequestHeader("Authorization","Bearer "+d)},dataType:"json",success:function(a){e(a)},error:function(a){b(a)}})})}
function cartPromise(a,c,d,e){return new Promise(function(b,g){$.ajax({url:a,contentType:"application/json; charset\x3dUTF-8",type:"post",data:JSON.stringify(c),xhrFields:{withCredentials:!0},crossDomain:!0,success:function(a){b(a);void 0!==a.resultMsg&&"00"!=a.resultMsg[0].code&&d&&($(".errorbox .gmg p").eq(0).text(a.resultMsg[0].message),$(".errorbox").bPopup({onClose:function(){void 0!==e&&""!=e&&(window.location.href=e)}}))},error:function(a){a.responseJSON&&"00"!=a.responseJSON.resultMsg[0].code&&
d&&("98"==a.responseJSON.resultMsg[0].code?$("#login").bPopup():($(".errorbox .gmg p").eq(0).text(a.responseJSON.resultMsg[0].message),$(".errorbox").bPopup({onClose:function(){void 0!==e&&""!=e&&(window.location.href=e)}})));g(a)}})})}function cartGetPromise(a){return new Promise(function(c,d){$.ajax({url:a,contentType:"application/json; charset\x3dUTF-8",type:"get",dataType:"json",success:function(a){c(a)},error:function(a){d(a)}})})}
function cartGetPromiseWithData(a,c){return new Promise(function(d,e){$.ajax({url:a,contentType:"application/json; charset\x3dUTF-8",type:"get",data:JSON.stringify(c),dataType:"json",success:function(a){d(a)},error:function(a){e(a)}})})}function queryAxios(a,c,d){return axios({method:d||"post",url:a,data:c})};