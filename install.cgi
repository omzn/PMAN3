#!/usr/bin/perl
# $Id: install.cgi,v 1.15 2010/03/11 04:00:15 o-mizuno Exp $
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
my $cgi;

my $DB = "./db/bibdat.db";
my $SESS_DB = "./db/sess.db";
my $CACHE_DB = "./db/cache.db";
my $OPTIONS_DB = "./db/config.db";

if (&check_module('CGI')) {
    $cgi = new CGI;
    if ($cgi->param('SECOND') eq "go") {
	&second_page;
    } elsif ($cgi->param('THIRD') eq "go") {
	&third_page;
    } elsif ($cgi->param('FOURTH') eq "go") {
	&fourth_page;
    } elsif ($cgi->param('FINISH') eq "go") {
	&finish_page;
    } else {
	&first_page;
    }
} else {
    &first_page;
}

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
<h3>必要条件確認</h3>
<p>必要条件を確認します．</p>
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
<td class="fieldHead">SQLite3</td>
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
<h3>初期設定 (1/2)</h3>
<p>ここで設定した情報は後から設定メニューで変更することもできます．パスワードだけは必ず設定してください．</p>
<p>PMAN3.0.xをご利用の方も以下の情報を再設定してください．すでに存在するDBはそのまま利用します．</p>
<table>
<form method="POST" script="./install.cgi">
<input type="hidden" name="SECOND" value="go" />
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
    require DBI;
    
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
	<h3>初期設定 (2/2)</h3>
        <ul>
EOM
    my $err = 0;
    my $dbh;
    unless (-d "./db"){
	umask(0);
	mkdir("./db",0777);
    }
    unless (-f $DB) {
	eval {
	    $dbh = DBI->connect("dbi:SQLite:dbname=$DB", undef, undef, 
			       {AutoCommit => 0, RaiseError => 1 });
	    $dbh->{sqlite_unicode} = 1;
	    my $SQL = <<EOM;
CREATE TABLE bib(
id integer primary key autoincrement,
style text not null,
ptype integer not null,
author  text,
editor  text,
key     text,
title   text,
journal text,
booktitle text,
series  text,
volume  text,
number  text,
chapter text,
pages   text,
edition text,
school  text,
type    text,
institution    text,
organization   text,
publisher   text,
address   text,
month   integer,
year   integer,
howpublished   text,
note   text,
annote   text,
abstract   text,
title_e   text,
author_e   text,
editor_e   text,
journal_e   text,
booktitle_e   text,
publisher_e   text,
acceptance   text,
impactfactor   text,
url   text
);
EOM
	$dbh->do($SQL);
    $SQL = <<EOM;
CREATE TABLE ptypes(
pt_id    integer primary key autoincrement,
pt_type  integer not null,
pt_order integer not null,
pt_lang  text not null,
pt_desc  text not null
);
EOM
	$dbh->do($SQL);
    $SQL = <<EOM;
CREATE TABLE files(
id integer primary key autoincrement,
pid integer not null,
filename text not null,
mimetype text not null,
file blob not null,
access integer not null,
file_desc text
);
EOM
	$dbh->do($SQL);
    $SQL = <<EOM;
CREATE TABLE tags(
tag_id integer primary key autoincrement,
paper_id integer not null,
tag text not null
);
EOM
            $dbh->do($SQL);
            $SQL = <<EOM;
CREATE TABLE authors(
id integer primary key autoincrement,
paper_id integer not null,
author_order integer not null,
author_name text not null,
author_key text
);
EOM
            $dbh->do($SQL);
	    $dbh->commit;
	    $dbh->disconnect;
	    chmod(0666,$DB);
        };
	if ($@) {
	    $doc .= "</li><pre>Error: $@</pre>";
	    $err++;
	    unlink($DB);
	} else {
	    $doc .= "<li>文献データベースを作成しました．</li>\n";
	}
    } else {
	    $doc .= "<li>文献データベースはすでに存在します．</li>\n";
    }	

    unless (-f $SESS_DB) {
	my $sdbh;
	if ($cgi->param("use_DBforSession") == 1) {
	    eval {
		$sdbh = DBI->connect("dbi:SQLite:dbname=$SESS_DB", undef, undef, 
				     {AutoCommit => 0, RaiseError => 1 });
		my $SQL = <<EOM;
CREATE TABLE sessions (
id CHAR(32) NOT NULL PRIMARY KEY,
a_session TEXT NOT NULL);
EOM
                $sdbh->do($SQL);
		$sdbh->commit;
		$sdbh->disconnect;
		chmod(0666,$SESS_DB);
	    };
	    if ($@) {
		$doc .= "</li><pre>$@</pre>";
		$err++;
		unlink($SESS_DB);
	    } else {
		$doc .= "<li>セッション管理データベースを作成しました．</li>\n";
	    }
	}
    } else {
	$doc .= "<li>セッション管理データベースはすでに存在します．</li>\n";
    }

    my $texHeader = <<"EOM";
\\documentclass{jarticle}
\\usepackage{times}
\\usepackage{fancyhdr}
\\renewcommand{\\baselinestretch}{0.85}
\\setlength{\\topmargin}{-10mm}
\\setlength{\\oddsidemargin}{0mm}
\\setlength{\\evensidemargin}{0mm}
\\setlength{\\textheight}{23.6cm}
\\setlength{\\textwidth}{16cm}
\\title{\\LARGE\\bf 研究業績リスト}

\\newcommand{\\myName}{} \%ここに名前が挿入される
\\newcommand{\\myAffiliation}{} \%ここに所属が挿入される
\\newcommand{\\myTitle}{} \%ここに肩書きが挿入される
\\author{ \\myAffiliation ~~ \\myTitle  ~~ \\myName }

\\begin{document}
\\maketitle

\\pagestyle{fancy}
\\thispagestyle{fancy}

\\renewcommand{\\headrulewidth}{0.5pt}
\\renewcommand{\\footrulewidth}{0.5pt}
\\renewcommand{\\sectionmark}[1]{\\markright{\#1}}
\\fancyhf{}
\\fancyhead[CE,CO]{\\bf 研究業績リスト}
\\fancyhead[RE,LO]{\\bf \\rightmark}
\\fancyfoot[LE,RO]{\\thepage}
EOM

my $texFooter = <<"EOM";
以上．
\\end{document}
EOM

    require Digest::MD5;
    my %opts = ( 
	use_XML              => 0,
	use_RSS              => 0,
	use_cache            => $cgi->param('use_cache'),
	use_DBforSession     => $cgi->param('use_DBforSession'),
	use_AutoJapaneseTags => 0,
	use_mimetex          => 0,
	use_latexpdf         => 0,
	PASSWD               => Digest::MD5::md5_hex($cgi->param('password')),
	titleOfSite          => $cgi->param('site_name'),
	maintainerName       => $cgi->param('maintainer_name'),
	maintainerAddress    => $cgi->param('maintainer_url'),
	texHeader            => $texHeader,
	texFooter            => $texFooter,
	latexcmd             => "/usr/bin/platex -halt-on-error",
	dvipdfcmd            => "/usr/bin/dvipdfmx -V 4",
    );
    eval {
	my $odbh = DBI->connect("dbi:SQLite:dbname=$OPTIONS_DB", undef, undef, 
				{AutoCommit => 0, RaiseError => 1 });
	$odbh->{sqlite_unicode} = 1;

	my $SQL = "SELECT name FROM sqlite_master WHERE type='table'"; 
	my @dbs = $odbh->selectrow_array($SQL);
	my $sth;
	if (grep(/^config$/,@dbs) == ()) {
	    $SQL = "CREATE TABLE config(id integer primary key autoincrement, name text not null, val text not null)";
	    $sth = $odbh->do($SQL);
	    foreach (keys(%opts)) {
		$SQL = "INSERT INTO config VALUES(null,?,?)";
		$sth = $odbh->prepare($SQL);
		$sth->execute($_,$opts{$_});
	    }
	    $odbh->commit;
	}
    };
    if ($@) {
	$doc .= "</li><pre>$@</pre>";
	$err++;
	unlink($OPTIONS_DB);
    } else {
	$doc .= "<li>設定データベースを作成し，初期設定を書き込みました．</li></ul>\n";
    }

    if ($err == 0) {
	$doc .= <<EOM;
        <p>インストールは成功しました．</p>
        <p>PMAN3にてログイン後，オプション設定メニューから各種の設定を変更できます．</p>
        <p>PMAN3のご利用，誠にありがとうございます．</p>
        <p class="red">なお，install.cgiは必ず削除してください．<p>
        <center><a href="./install.cgi?FINISH=go">[PMAN3の起動]</p></a></center>
        <p>PMAN2.xからデータを引き継がれる場合はこちらへお進みください．</p>
        <center><a href="./install.cgi?THIRD=go">[PMAN2からのデータ移行]</a></p></center>
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

sub third_page {
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
	<h3>PMAN2.xからの移行手続き (1/2)</h3>
<p>現在ご利用中のPMAN2.xからデータの引き継ぎを行います．以下の情報を入力してください．</p>
<table>
<form method="POST" script="./install.cgi">
<input type="hidden" name="FOURTH" value="go" />
<tr>
<td class="fieldHead">PMAN2のデータ(bibdat.csv)格納場所</td>
<td class="fieldBody">URLではなく，サーバ上の絶対パスを指定してください．(例: /path/to/pamn2/data/bibdat.csv)</td>
<td class="fieldBody"><input type="text" name="csv_path" /></td>
</tr>
<tr>
<td class="fieldHead">PMAN2のカテゴリ情報(category.txt)格納場所</td>
<td class="fieldBody">URLではなく，サーバ上の絶対パスを指定してください．(例: /path/to/pamn2/data/category.txt)</td>
<td class="fieldBody"><input type="text" name="ctg_path" /></td>
</tr>
<tr>
<td class="fieldHead">PMAN2のPDFファイル格納ディレクトリ</td>
<td class="fieldBody">URLではなく，サーバ上の絶対パスを指定してください．(例: /path/to/pamn2/data/pdf)</td>
<td class="fieldBody"><input type="text" name="pdf_path" /></td>
</tr>
<tr>
<td class="fieldHead"></td>
<td class="fieldBody"></td>
<td class="fieldBody"><input type="submit" value="データ移行" /></td>
</tr>
</form>
</table>
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

sub fourth_page {
    require DBI;
    require MIME::Types;
    require Encode;

    my $i = 1;

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
	<h3>PMAN2.xからの移行手続き (2/2)</h3>
EOM

    my $csv_path = $cgi->param('csv_path');
    my $ctg_path = $cgi->param('ctg_path');
    my $pdf_path = $cgi->param('pdf_path');
    my $err = 0;

    if ($csv_path eq "" || $ctg_path eq "" || $pdf_path eq "") {
	$doc .= "<p>Error: パスは全て指定してください．</p>";
	$err ++;
    } elsif (!(-f $csv_path && -f $ctg_path && -d $pdf_path)) {
	$doc .= "<p>Error: ファイルまたはディレクトリが存在しません．</p>";
		$err ++;
    } else {

	my $dbh = DBI->connect("dbi:SQLite:dbname=db/bibdat.db", undef, undef, {AutoCommit => 0, RaiseError => 1 });
	$dbh->{sqlite_unicode} = 1;

	my $databaseFile = $csv_path;
	my @db = ();
	open(PDB,$databaseFile);
	my %a_names;

	while (<PDB>) {
	    my $tmp = $_;
	    $tmp =~ s/(?:\x0D\x0A|[\x0D\x0A])?$/,/;
	    my @values = map {/^"(.*)"$/ ? scalar($_ = $1, s/""/"/g, $_) : $_}
	    ($tmp =~ /("[^"]*(?:""[^"]*)*"|[^,]*),/g);  #"
#	    print "$i\n";

	    for (my $j=0;$j<=$#values;$j++) {
		Encode::from_to($values[$j],"euc-jp","utf-8");
		utf8::decode($values[$j]);
	    } 

	    # abstract
	    $values[27]=~s/<BR>/\n/ig;
	    eval { 
		my $sth = $dbh->prepare("INSERT INTO bib VALUES(null,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?);");
		$sth ->execute($values[0], $values[1], $values[4],
			       $values[5], $values[6], $values[7], $values[8], $values[9],
			       $values[10], $values[11], $values[12], $values[13],
			       $values[14], $values[15], $values[16], $values[17],
			       $values[18], $values[19], $values[20], $values[21],
			       $values[22], $values[23], $values[24], $values[25],
			       $values[26], $values[27], $values[28], $values[29],
			       $values[30], $values[31], $values[32], $values[33],
			       $values[34], $values[35], ""); 

		if ($values[3]) {
		    my $refdata =  MIME::Types::by_suffix($values[3]);
		    my ($mediatype, $encoding) = @$refdata;
		    $sth = $dbh->prepare("INSERT INTO files VALUES(null,?,?,?,?,?,null)");
		    open(IN,"$pdf_path/$values[3]");
		    binmode(IN);
		    my $pdf = join('',<IN>);
		    close(IN);
		    $sth ->execute($i,$values[3],$mediatype,$pdf,0); 
		}
	#4(author),6(key),29(author_e)
		my @author = split(/\s*,\s*/,$values[4]);
		my @key = split(/\s*,\s*/,$values[6]);
		my @author_e = split(/\s*,\s*/,$values[29]);
		
		for (my $j=0; $j<=$#author; $j++) {
		    my $a = $author[$j];
		    if (&isJapanese($a)) {
			$a =~ s/\s//g;
			if (defined $key[$j] && $key[$j] ne "") {
			    $sth = $dbh->prepare("INSERT INTO authors VALUES(null,?,?,?,?)");
			    $sth ->execute($i,$j,$a,$key[$j]); 
			} elsif (defined $author_e[$j] && $author_e[$j] ne "") {
			    $sth = $dbh->prepare("INSERT INTO authors VALUES(null,?,?,?,?)");
			    $sth ->execute($i,$j,$a,$author_e[$j]); 
			} else {
			    $sth = $dbh->prepare("INSERT INTO authors VALUES(null,?,?,?,?)");
			    $sth ->execute($i,$j,$a,$a); 
			}
		    } else {
			$sth = $dbh->prepare("INSERT INTO authors VALUES(null,?,?,?,?)");
			$sth ->execute($i,$j,$a,$a); 
		    }
		}

		$dbh->commit;
		$i++;
	
	    }; 

	    if ($@) { 
		$dbh->rollback; $dbh->disconnect; 
		$doc .= "<p>Error: $@</p>";
		$err ++;
	    }
	}

	my $optionFile = $ctg_path;
	open(OPT,$optionFile);
	my $line = <OPT>;
	close(OPT,$optionFile);
	$line =~s/\s*$//;
	Encode::from_to($line, "euc-jp", "utf-8");
	utf8::decode($line);
	my %jlist = split(/\t/,$line);

	foreach (keys(%jlist)) {
	    my ($num,$lang) = split(/,/,$_);
	    my $description = $jlist{$_};

	    eval { 
		my $sth = $dbh->prepare("INSERT INTO ptypes VALUES(null,?,?,?,?);");
		$sth ->execute($num, $num, $lang, $description);
		$dbh->commit;
	    }; 
	    
	    if ($@) { 
		$dbh->rollback; $dbh->disconnect; 
		$doc .= "<p>Error: $@</p>";
		$err ++;
	    }
	} 
	$dbh->disconnect;
    }

    if ($err) {
	$doc .= <<EOM;
        <p>移行手続きは失敗しました．</p>
	<p>エラーの原因を取り除いた後，./db/*.dbを全て消去してから，install.cgiを再起動してはじめから設定をしてください．</p>
EOM
    } else {
	$doc .= "<p> $i 件の業績データを移行しました．</p>";
	$doc .= "<p> 業績分類データを移行しました．</p>";
	$doc .= <<EOM;
        <p>移行手続きは成功しました．</p>
        <p>PMAN3にてログイン後，オプション設定メニューから各種の設定を変更できます．</p>
        <p>PMAN3のご利用，誠にありがとうございます．</p>
        <p class="red">なお，install.cgiは必ず削除してください．<p>
        <center><a href="./install.cgi?FINISH=go">[PMAN3の起動]</a></p></center>
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

sub finish_page {
    print $cgi->redirect("./pman3.cgi?LOGIN=on");
}

# 日本語が含まれていれば1
sub isJapanese {
    my ($str) = @_;
    if (utf8::is_utf8($str)) {
	Encode::_utf8_off($str); # utf8 flagを落とす
    }
    Encode::from_to($str,"utf-8","euc-jp");
    if ($str =~ /[\xA1-\xFE][\xA1-\xFE]/) {
	return 1;
    } else {
	return 0;
    }
}
