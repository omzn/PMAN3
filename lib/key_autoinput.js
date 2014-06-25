//著者名からキーを生成
function author_autoinput(){
	//著者名取得
    var namelist;
    var joiner;
    if (!document.edit.edit_author.value.match(/\sand\s/)) {
	namelist = document.edit.edit_author.value.split(",");
	joiner = ",";
    } else {
	namelist = document.edit.edit_author.value.split(" and ");
	joiner = " and ";
    }
    var i;
    for (i=0;i<namelist.length;i++){
	namelist[i] = remove_space(namelist[i]);
    }

    //著者名に対応したキー取得
    var keylist = [];
    for (i=0;i<namelist.length;i++){
	if(keys[namelist[i]]){
	    keylist.push(keys[namelist[i]]);
	}
	else{
	    keylist.push("");
	}
    }
    
    //キー書き込み
    document.edit.edit_author_e.value = keylist.join(joiner);
    document.edit.edit_key.value = keylist.join(joiner);
}
	
//日本語名はスペースを取り除いて正規化
function remove_space(name){
    if(!name.match(/[a-zA-Z]/)){
	name = name.replace(/\s+/g, "");
    }
    name = name.replace(/^\s+/, "");
    name = name.replace(/\s+$/, "");
    return name;
}
