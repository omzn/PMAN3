#!/usr/bin/perl
# $Id: install.cgi,v 1.1 2010/03/08 01:18:56 o-mizuno Exp $
# =================================================================================
#                        PMAN 3 - Paper MANagement system
#
#                                    INSTALLER       
#
#              (c) 2002-2010 Osamu Mizuno, All right researved.
# 
my $VERSION = "3.1 Beta 8";
# 
# =================================================================================
use strict;
use utf8;

my $doc;
&first_page;
if (utf8::is_utf8($doc)) {
    utf8::encode($doc);
}
print $doc;
exit 0;

sub check_module {
	my $module = $_[0];	
	# モジュールが存在すれば読み込む
	eval "use $module;";
	if ($@) {
		return 0;
	} else {
		return 1;
	}
}

sub first_page {
    $doc .= <<EOM;
Content-Type: text/html; charset=utf-8

<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN"
    "http://www.w3.org/TR/html4/loose.dtd">
<html>
    <head>
    <title>PMAN3 Installer</title>
    <META http-equiv="Content-Type" content="text/html; charset=utf-8">
    <meta http-equiv="Pragma" content="no-cache"> 
    <meta http-equiv="Content-Style-Type" content="text/css" />
    <link rel="stylesheet" type="text/css" href="css/pman.css" />
    </head>
    <body>
      <div id="container">
        <div id="header">
	    <a class="logo" href="http://se.is.kit.ac.jp/~o-mizuno/pman3.html"><img class="logo" src="img/logo.png" /></a>
            <h1>PMAN3 インストーラ</h1>
        </div>
        <div id="contents">

<h3>必要条件を確認します．</h3>
<table>
EOM

    my $req = 0;
    my $is_sqlite3 = "OK: インストール済";
    if (`which sqlite3` eq "") {
	$is_sqlite3 = '<span class="red"><b>NG: インストールされていません</b></span>';
	$req ++;
    }
    
    $doc .= <<EOM;
<tr>
<td class="fieldHead">sqlite3の利用可否</td>
<td class="fieldBody">$is_sqlite3</td>
</tr>
EOM

    my @required_modules = (
	'CGI', 
	'DBI', 
	'DBD::SQLite',
	'CGI::Session',
	'CGI::Cookie',
	'HTML::Template',
	'HTML::Scrubber',
	'HTML::Entities',
	'URI::Escape',
	'Encode',
	'Digest::MD5',
	'MIME::Types',
	'Time::HiRes',
    );
    my %installed;

    foreach (@required_modules) {    
	if (&check_module($_)) {
	    $installed{$_} = "OK: インストール済";
	} else {
	    $installed{$_} = '<span class="red"><b>NG: インストールされていません</b></span>';
	    $req ++;
	}
	$doc .= <<EOM;
<tr>
<td class="fieldHead">$_</td>
<td class="fieldBody">$installed{$_}</td>
</tr>
EOM
    }

    if ($req == 0) {
	$doc .= <<EOM;
<tr>
<td class="fieldHead"></td>
<td class="fieldBody">必要条件は全て揃っています．</td>
</tr>
</table>
<h3>初期設定</h3>
<p>ここで設定した情報は後から設定メニューで変更することもできます．パスワードだけは必ず設定してください．</p>
<table>
<form method="POST" script="./install.cgi">
<tr>
<td class="fieldHead">サイト名</td>
<td class="fieldBody"><input type="text" name="site_name" /></td>
</tr>
<tr>
<td class="fieldHead">管理者名</td>
<td class="fieldBody"><input type="text" name="maintainer_name" /></td>
</tr>
<tr>
<td class="fieldHead">管理者URL</td>
<td class="fieldBody"><input type="text" name="maintainer_url" /></td>
</tr>
<tr>
<td class="fieldHead">管理者パスワード</td>
<td class="fieldBody"><input type="text" name="password" /></td>
</tr>
<tr>
  <td class="fieldHead">セッションDBの利用<br />
  セッション遷移にデータベースを利用します．</td> 
  <td class="fieldBody">
  <select name="use_DBforSession" >
  <option selected="selected" value="1">使用する</option>
  <option value="0">使用しない</option>
  </select>  </td>
</tr>
<tr>
  <td class="fieldHead">キャッシュの利用<br />
  一度表示したクエリの表示が高速になります．</td> 
  <td class="fieldBody">
  <select name="use_cache" >
  <option selected="selected" value="1">使用する</option>
  <option value="0">使用しない</option>
  </select>  </td>
</tr>
EOM

        $doc .= <<EOM;
<tr>
<td class="fieldHead"></td>
<td class="fieldBody"><input type="submit" /></td>
</tr>
</form>
</table>
EOM

    } else {
    $doc .= <<EOM;
<tr>
<td class="fieldHead"></td>
<td class="fieldBody">必要条件が揃っていません．インストールしてから再度install.cgiを実行してください．</td>
</tr>
</table>
EOM
    }
    $doc .= <<EOM;
        </div>
        <div id="footer">
            <p class="center">
PMAN3 is created by <a href="http://se.is.kit.ac.jp/~o-mizuno/">o-mizuno</a>.<br />
<a href="http://www-ise4.ist.osaka-u.ac.jp/~o-mizuno/pman3.html">PMAN 3.1</a> - Paper MANagement system / (C) 2002-2010, <a href="http://se.is.kit.ac.jp/~o-mizuno/">Osamu Mizuno</a> / All rights reserved.
</p>
        </div>
      </div>
    </body>
</html>
EOM
}

sub second_page {
    require CGI;
    my $cgi = new CGI;


    $doc .= <<EOM;
Content-Type: text/html; charset=utf-8

<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN"
    "http://www.w3.org/TR/html4/loose.dtd">
<html>
    <head>
    <title>PMAN3 Installer</title>
    <META http-equiv="Content-Type" content="text/html; charset=utf-8">
    <meta http-equiv="Pragma" content="no-cache"> 
    <meta http-equiv="Content-Style-Type" content="text/css" />
    <link rel="stylesheet" type="text/css" href="css/pman.css" />
    </head>
    <body>
      <div id="container">
        <div id="header">
	    <a class="logo" href="http://se.is.kit.ac.jp/~o-mizuno/pman3.html"><img class="logo" src="img/logo.png" /></a>
            <h1>PMAN3 インストーラ</h1>
        </div>
        <div id="contents">
EOM

    $doc .= <<EOM;
        </div>
        <div id="footer">
            <p class="center">
PMAN3 is created by <a href="http://se.is.kit.ac.jp/~o-mizuno/">o-mizuno</a>.<br />
<a href="http://www-ise4.ist.osaka-u.ac.jp/~o-mizuno/pman3.html">PMAN 3.1</a> - Paper MANagement system / (C) 2002-2010, <a href="http://se.is.kit.ac.jp/~o-mizuno/">Osamu Mizuno</a> / All rights reserved.
</p>
        </div>
      </div>
    </body>
</html>
EOM
}
