var OrderByColumn=Class.create();

OrderByColumn.prototype={
	initialize: function(table,type){
		if(typeof table == "string"){
			table=document.getElementById(table);
		};
		this.type=type;
		this.table=table;
		this.th=$A(this.table.getElementsByTagName("thead")[0].getElementsByTagName("th"));
		this.td=$A(this.table.getElementsByTagName("tbody")[0].getElementsByTagName("td"));
		this.tr=$A(this.table.getElementsByTagName("tbody")[0].getElementsByTagName("tr"));
		
		this.th.each(function(v){
			v.style.cursor="pointer";
			var sp=document.createElement("span");
			sp.className="OBRarrow";
			v.appendChild(sp);
			
			Event.observe(v,"click",function(){
				this.sort(v);
			}.bind(this));
		}.bind(this));
	}
	
	
	,marking: function(th){		
		var current=th.lastChild.innerHTML;
		this.th.each(function(v){
			v.lastChild.innerHTML="";
		});
		switch(current){
			case "":
				th.lastChild.innerHTML="^";
				return "asc";
				break;
				
			case "^":
				th.lastChild.innerHTML="v";
				return "desc";
				break;
				
			case "v":
				th.lastChild.innerHTML="^";
				return "asc";
				break;
		}
	}
	
	,sort: function(th){
		var orderby=this.marking(th);
		
		for(var i=0;this.th[i]; i++){
			if(this.th[i] == th){
				var num=i;
				break;
			}
		}
		
		if(orderby == "asc"){
			this.tr.sort(function(a,b){
				var a2=a.getElementsByTagName("td")[num].innerHTML;
				var b2=b.getElementsByTagName("td")[num].innerHTML;
				
				if(this.type[num] == "number"){
					if(!parseFloat(a2)){
						return 1;
					}else if(!parseFloat(b2)){
						return -1;
					}
					return (parseFloat(a2) - parseFloat(b2));
				}else{
					return (a2.toLowerCase() > b2.toLowerCase()) ? 1 : -1;
				}
			}.bind(this));
		}else{
			this.tr.sort(function(a,b){
				var a2=a.getElementsByTagName("td")[num].innerHTML;
				var b2=b.getElementsByTagName("td")[num].innerHTML;
				if(this.type[num] == "number"){
					if(!parseFloat(a2)){
						return 1;
					}else if(!parseFloat(b2)){
						return -1;
					}
					return (parseFloat(b2) - parseFloat(a2));
				}else{
					return (b2.toLowerCase() > a2.toLowerCase()) ? 1 : -1;
				}
			}.bind(this));
		}
		
		var tbody=this.table.getElementsByTagName("tbody")[0];
		$A(tbody.childNodes).each(function(v){
			v.parentNode.removeChild(v);
		});
		
		this.tr.each(function(v){
			tbody.appendChild(v);
		});
	}
}