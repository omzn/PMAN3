#!/usr/bin/perl
# $Id: pman3.cgi,v 1.94 2010/05/26 06:23:14 o-mizuno Exp $
# =================================================================================
#                        PMAN 3 - Paper MANagement system
#                               
#              (c) 2002-2011 Osamu Mizuno, All right researved.
# 
my $VERSION = "3.2.3 build 20111106";
# 
# =================================================================================
BEGIN {
    unshift(@INC, './lib');
}

use strict;
use utf8;

my $debug=0;

use DBI;
use CGI;
use CGI::Session;
use CGI::Cookie;
use HTML::Template;
use HTML::Scrubber;
use HTML::Entities;
use Encode;
use Digest::MD5 qw/md5_hex/;
use MIME::Types qw/by_suffix/;
use URI::Escape qw/uri_escape_utf8/;
use IO::String;
use BibTeX::Parser;
use BibTeX::Parser::Author;

#=====================================================
# Constants
#=====================================================
my $LIBDIR = "./lib";
my $TMPLDIR = "./tmpl";
my $TMPDIR = "./tmp";
my $DB = "./db/bibdat.db";
my $SESS_DB = "./db/sess.db";
my $CACHE_DB = "./db/cache.db";
my $OPTIONS_DB = "./db/config.db";
my $MIMETEXPATH = "$LIBDIR/mimetex.cgi";
my $IMGTEXPATH = "$LIBDIR/imgtex.fcgi";

#=====================================================
# Options 
#=====================================================
my $PASSWD;

my $titleOfSite;
my $maintainerName;
my $maintainerAddress;
my $texHeader;
my $texFooter;

my $use_cache = 1;
my $use_DBforSession = 0;
my $use_AutoJapaneseTags = 0;
my $use_RSS = 0;
my $use_XML = 0;
my $use_mimetex = 0;
my $use_imgtex = 0;
my $use_latexpdf = 0;

my $latexcmd = "/usr/bin/platex -halt-on-error";
my $dvipdfcmd = "/usr/bin/dvipdfmx -V 4";

my $tmpl_name = "default";

my $title_list;
my $title_table;
my $title_latex ;
my $title_detail;
my $title_bbl ;

my $title_add ;
my $title_bib ;
my $title_edit ;
my $title_category ;
my $title_config  ;

my %opts = ( 
    use_XML              => $use_XML,
    use_RSS              => $use_RSS,
    use_cache            => $use_cache,
    use_DBforSession     => $use_DBforSession,
    use_AutoJapaneseTags => $use_AutoJapaneseTags,
    use_mimetex          => $use_mimetex,
    use_imgtex           => $use_imgtex,
    use_latexpdf         => $use_latexpdf,
    PASSWD               => $PASSWD,
    titleOfSite          => $titleOfSite,
    maintainerName       => $maintainerName,
    maintainerAddress    => $maintainerAddress,
    texHeader            => $texHeader,
    texFooter            => $texFooter,
    latexcmd             => $latexcmd,
    dvipdfcmd            => $dvipdfcmd,
    tmpl_name            => $tmpl_name,
    title_list           => 'List of works',
    title_table          => 'Table of works',
    title_latex          => 'LaTeX list of works',
    title_detail         => 'Detail of a work',
    title_bbl            => 'BibTeX list of works',
    );

&getOptionsDB;

#=====================================================
# Global Variables
#=====================================================
my $httpServerName = $ENV{'SERVER_NAME'};
my $scriptName = $ENV{'SCRIPT_NAME'};

my $query = ""; 
my $cgi = new CGI;
my $session;
my $login;
my %sbk ; 

my $bib;
my %authors_hash;
my %ptype;
my @jname;
my @ptype_order ;
my @bb_order = ( 'title', 'title_e', 'author', 'author_e', 'editor', 
		 'editor_e', 'key', 'journal', 'journal_e', 'booktitle',
		 'booktitle_e', 'series', 'volume', 'number', 'chapter', 
		 'pages', 'edition', 'school', 'type', 'institution', 
		 'organization', 'publisher', 'publisher_e', 'address', 'month', 
		 'year', 'howpublished', 'acceptance', 'impactfactor', 'url', 
		 'note', 'annote', 'abstract' );
my %mlist = ("0,en"=>"","0,ja"=>"",
	     "1,en"=>"January","1,ja"=>"1月","2,en"=>"February","2,ja"=>"2月",
	     "3,en"=>"March","3,ja"=>"3月","4,en"=>"April","4,ja"=>"4月",
	     "5,en"=>"May","5,ja"=>"5月","6,en"=>"June","6,ja"=>"6月",
	     "7,en"=>"July","7,ja"=>"7月","8,en"=>"August","8,ja"=>"8月",
	     "9,en"=>"September","9,ja"=>"9月","10,en"=>"October","10,ja"=>"10月",
	     "11,en"=>"November","11,ja"=>"11月","12,en"=>"December","12,ja"=>"12月");

#=====================================================
# lib/lang.*.plで設定する変数群 (our宣言)
#=====================================================
our %bt;
our %viewMenu;
our %topMenu;
our %msg;

#=====================================================
# Main
#=====================================================

use Time::HiRes qw/gettimeofday tv_interval/;
my $t0 = [Time::HiRes::gettimeofday];

my $dbh;
eval {
    $dbh  = DBI->connect("dbi:SQLite:dbname=$DB", undef, undef, 
			 {AutoCommit => 0, RaiseError => 1 });
    $dbh->{sqlite_unicode} = 1; # これがperl 5.8.5未満では動かない
};
&printError('Database not found. Run install.cgi first.') if ($@);

&manageSession;
&initialLaunch;
# キャッシュ読み込み処理の実装部
#   LOGIN状態でない場合のみ．
#   ここでgenerateURLの内容をキーとしてcacheDBを検索．
#   発見したらその内容をprintして終了．
if ($use_cache) {
    my $page = &getCacheFromCDB;
    if ($page) {
	my $dt = Time::HiRes::tv_interval($t0);
	$page =~ s/Time to show this page: [\d\.]+ seconds\./Time to show this page: $dt seconds\. (cached)/;
#	if (utf8::is_utf8($page)) {
#	    print encode('utf-8', $page);
#	} else {
	    print $page;
#	}
	exit 0;
    }
}
$query = &makeQuery;
&getDataDB($query);
&getPtypeDB;
################################[TIME]
my $t1 = Time::HiRes::tv_interval($t0);
my $t2;
my ($tt1,$tt2,$tt3,$tt4);
################################[TIME]
&printScreen;
################################[TIME]
my $t3;
$t3 = Time::HiRes::tv_interval($t0);
################################[TIME]
&clearSessionParams;
################################[TIME]
#printf STDERR "[TIME] DB:%3.2f s, Format:%3.2f s, Write:%3.2f s",$t1, $t2-$t1, $t3-$t2 ;
#printf STDERR "[TIME FORMAT] %3.2f s, %3.2f s, %3.2f s, %3.2f s",$tt1,$tt2,$tt3,$tt4;
################################[TIME]
$dbh->disconnect;
exit(0);

#=====================================================
# 初期起動での誘導
#=====================================================

sub initialLaunch {
    my $SQL;
    my $info;
    $SQL = "SELECT * FROM ptypes";
    my $res = $dbh->selectrow_array($SQL);
    if ($res == ()) {
	unless ($login) {
	    $info = <<EOM;
<p>初期設定のために，ログインしてください．</p>
<p>Please login for your initial setup.</p>
<p class="login">
<form action="$scriptName" method="POST">
Password: 
<input type="password" name="PASSWD" size="20" />
<input type="submit" value="Login" />
</form>
</p>
EOM
            &printInfo($info);
	}
	if ($session->param('MODE') ne "category") {
	    $info = <<EOM;
<p>カテゴリが設定されていません．「<a href="$scriptName?MODE=category">カテゴリ設定</a>」へ移動してください．</p>
<p>No category is found. Please go to <a href="$scriptName?MODE=category">category setting</a>.</p>
EOM
            &printInfo($info);
	}
    } else {
	$SQL = "SELECT * FROM bib";
	$res = $dbh->selectrow_array($SQL);
	if ($res == () && $session->param('MODE') ne "add") {
	    $info = <<EOM;
<p>文献が１つも登録されていません．「<a href="$scriptName?MODE=add">文献追加</a>」から文献を登録してください．</p>
<p>No publication is registered. Please go to <a href="$scriptName?MODE=add">add publication</a>.</p>
EOM
            &printInfo($info);
	}
    }
}

#=====================================================
# Session 管理
#=====================================================

sub manageSession {
    if (!$use_DBforSession) {
# セッションのゴミ掃除
	if(!opendir(DIR, "$TMPDIR")){
	    die;
	}
# cgisess_の残骸で 3 hours (1/8 day) より古いものを探す
	my @files = grep(/cgisess_/ && -f "$TMPDIR/$_" && ((-M "$TMPDIR/$_") > 1/8) , readdir(DIR));
	closedir(DIR);
	foreach(@files){
	    unlink("$TMPDIR/$_");
	}
    }
# CGI
    $cgi->charset('utf-8');

    # 短縮パラメータ
    if ($cgi->param("D") ne "") {
	$cgi->param("MODE","detail");
	my $param = $cgi->param("D");
	$param=~s/[\"\']//g;
	if (utf8::is_utf8($param)) {
	    utf8::encode($param);
	}
	$cgi->param("ID",$param);
    }
    if ($cgi->param("A") ne "") {
	$cgi->param("FROM","author");
	$cgi->param("LOGIC","and");
	my $param = $cgi->param("A");
	$param=~s/[\"\']//g;
	if (utf8::is_utf8($param)) {
	    utf8::encode($param);
	}
	$cgi->param("SEARCH",$param);
    }
    if ($cgi->param("T") ne "") {
	$cgi->param("FROM","tag");
	$cgi->param("LOGIC","or");
	my $param = $cgi->param("T");
	$param=~s/[\"\']//g;
	if (utf8::is_utf8($param)) {
	    utf8::encode($param);
	}
	$cgi->param("SEARCH",$param);
    }

    # CGIで渡ってきた値をutf-8化
    for my $g ($cgi->param) {
	if ($g ne 'edit_upfile') { # upfileの破壊を防ぐ
	    my $param = $cgi->param($g);
	    #$param = &htmlScrub($param);
	    if (!utf8::is_utf8($param)) { # utf-8 flagが立ってないやつだけ．
		my @v = map {Encode::decode('utf-8',$_)} $cgi->param($g);#$param;
		foreach (@v) {
		    $_=~s/[\"\']//g;
		}
		$cgi->param($g,@v);
	    } else {
		$param =~s/[\"\']//g;
		$cgi->param($g,$param);
	    }
	}
    }
    # この時点で，$cgiの中身はutf8 flag ON

    my $sid = $cgi->param('SID') || $cgi->cookie('SID') || undef ;

    if ($use_DBforSession) {
	unless (-f $SESS_DB) {
	    eval {
		my $sdbh = DBI->connect("dbi:SQLite:dbname=$SESS_DB", undef, undef, 
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
	}
    }

    if ($sid) {
        $session = new CGI::Session("driver:File", $sid, {Directory=>$TMPDIR})
	    if (!$use_DBforSession);
        $session = new CGI::Session("driver:sqlite", $sid, {DataSource=>$SESS_DB}) 
	    if ($use_DBforSession);

	# LOGIN = offであれば，sessionからPASSWD情報を削除．
	if (defined($cgi->param('LOGIN')) && $cgi->param('LOGIN') eq "off") {
	    $cgi->delete('PASSWD');
	    $session->clear('PASSWD');
	}

	# cgiからPASSWDが渡ってきたら，MD5変換して再設定
	if ($cgi->param('PASSWD')) {
	    $cgi->param('PASSWD',md5_hex($cgi->param('PASSWD')));
	}
    } else {
        $session = new CGI::Session("driver:File", undef, {Directory=>$TMPDIR})
	    if (!$use_DBforSession);
	$session = new CGI::Session("driver:sqlite", undef, {DataSource=>$SESS_DB})
	    if ($use_DBforSession);

    }
    $session->expire('+3h');
    my $sp = $session->param_hashref();
#    %sbk = %$sp;
    foreach (keys(%$sp)) {
	$sbk{$_} = $sp->{$_} ;
    }
    # ここで，cgi -> session を突っ込む．PASSWDも突っ込まれたはず．
    $session->save_param($cgi); # OK?


    # 言語設定
    my $l = $session->param('LANG') || "ja";
    require "$LIBDIR/lang.$l.pl";

    $title_add = $msg{'Title_add'};
    $title_bib = $msg{'Title_bib'};
    $title_edit = $msg{'Title_edit'};
    $title_category = $msg{'Title_category'};
    $title_config  = $msg{'Title_config'};

    # ログイン状態設定

    if ($session->param('PASSWD') eq $PASSWD) {
	$login = 1;
    } else {
	$login = 0;
    }

    # 画面表示のない処理へ
    if (defined($session->param('MODE')) && $session->param('MODE') eq "edit2" ) {
	&registEntry();
    }
    if (defined($session->param('MODE')) && $session->param('MODE') eq "add2" ) {
	&registEntry();
    }
    if (defined($session->param('MODE')) && $session->param('MODE') eq "bib2" ) {
	&registEntryByBib();
    }
    if (defined($session->param('MODE')) && $session->param('MODE') eq "delete" ) {
	&deleteEntry();
    }
    if (defined($session->param('MODE')) && $session->param('MODE') eq "category2" ) {
	&modifyCategory();
    }
    if (defined($session->param('MODE')) && $session->param('MODE') eq "config2" ) {
	&doConfigSetting();
    }
    if (defined($session->param('MODE')) && $session->param('MODE') eq "filedelete" ) {
	&deleteFile();
    }
    # ファイルダウンロード処理へ
    if (defined($session->param('DOWNLOAD'))) {
	my ($f,$m,$c,$a) = &downloadFileDB($session->param('DOWNLOAD'));
	$session->clear('DOWNLOAD');
	if ($f && $m && $c && ($a == 0 || $login == 1)) {
	    &printFile($f,$m,$c);
	}
    }


}

sub clearSessionParams {

    if (defined($cgi->param('RSS')) || defined($cgi->param('XML')) || defined($cgi->param('SSI'))) {
	$session->clear();
	$session->flush();
	foreach (keys(%sbk)) {
	    next if ($_=~/^_SESSION_/);
	    $session->param($_,$sbk{$_});
	}
	return;
    }

    my $mode = $session->param('MODE') ;

    $session->clear('RSS');
    $session->clear('XML');
    $session->clear('STATIC');
    $session->clear('SSI');

    if ($mode eq "delete") {
	$session->clear('ID');
	$session->clear('MODE');
    } elsif ($mode eq "add2" || $mode eq "edit2" || $mode eq "bib2") {
	$session->clear('MODE');
    } elsif ($mode eq "filedelete") {
	$session->clear('MODE');
	$session->clear('FID');
    } elsif ($mode eq "config2") {
	$session->clear('MODE');
	$session->clear('tag');
	$session->clear('cache');
	my $sps = $session->param_hashref();
	$session->clear([grep(/opt_/,keys(%$sps))]);
    } elsif ($mode eq "category2") {
	$session->clear('MODE');
	$session->clear('op');
	my $sps = $session->param_hashref();
	$session->clear([grep(/cat_/,keys(%$sps))]);
    } elsif ($mode eq "PDF") {
	$session->param('MODE','latex');
    } 
}

#=====================================================
# CGIから検索条件取得 -> SQLのwhere句生成
#=====================================================
sub makeQuery {

    my $mmode = $session->param('MENU') || "simple";

    my $l = $session->param('LANG') || "ja";
    $l = $dbh->quote($l);

    if ($session->param('LOGIN') eq "on") {
	return;
    }

    if ($session->param('MODE') eq "detail" || $session->param('MODE') eq "edit") {
	my $id = $session->param('ID');
	if ($id=~/^\d+$/) {
	    $id = $dbh->quote($id);
	    return ("WHERE ID=$id AND ptype=pt_type AND pt_lang=$l");
	} else {
	    $session->clear("ID");
	    &printError('"ID" must be an integer.');
	}
    }

    # pman2との互換
    if (defined($cgi->param('FILTER'))) {
	$session->param('SEARCH',&HTML::Entities::decode($cgi->param('FILTER')));
#	$session->param('SEARCH',$session->param('FILTER'));
	$session->clear('FILTER');
    }

    my @cond = ();

    # 種別限定    
    my @pt = (); 
    if (ref($session->param('PTYPE')) eq 'ARRAY') {
	@pt= @{$session->param('PTYPE')};
    } else {
	$pt[0] = $session->param('PTYPE') eq '' ? 'all': $session->param('PTYPE');
    }
    my @newpt;
    for (my $i=0;$i<=$#pt;$i++) {
	push(@newpt,$pt[$i]) if ($pt[$i] ne "all");
    }	
    push(@cond," ptype IN ( ".join(",",@newpt)." ) ") if (@newpt != ());

    # ソート順
    my $order = "ORDER BY ";
    my $od = $session->param('SORT') || "t_descend";
    if ($od eq "ascend") {
	$order .= "year asc,month asc,number asc";
    } elsif ($od eq "descend") {
	$order .= "year desc,month desc,number desc";
    } elsif ($od eq "t_ascend") {
	$order .= "pt_order,year asc,month asc,number asc";
    } elsif ($od eq "t_descend") {
	$order .= "pt_order,year desc,month desc,number desc";
    } elsif ($od eq "y_t_ascend") {
	$order .= "year asc,pt_order,month asc,number asc";
    } elsif ($od eq "y_t_descend") {
	$order .= "year desc,pt_order,month desc,number desc";
    }

    my @smenu = ();
   
    if ($mmode eq "simple") {
	$smenu[0] = "";
    } elsif ($mmode eq "detail") {
	$smenu[0] = "";
	$smenu[1] = "1";
	$smenu[2] = "2";
	$smenu[3] = "3";
    }
    # 検索条件
    for (my $j=0;$j<=$#smenu;$j++) {
	my $s = $session->param("SEARCH$smenu[$j]") ;
	next if ($s =~/^\s*$/);
	$s =~s/^\s*//g; $s =~s/\s*$//g;
	my @ss = split(/\s+/,$s);
	my $lg = $session->param("LOGIC$smenu[$j]") || "and";
	if (!($lg eq "and" || $lg eq "or")) {
	    $session->clear("LOGIC$smenu[$j]");
	    &printError('"Logic" must be and/or. What are you attempting?');
	}
	my $from = $session->param("FROM$smenu[$j]") || "author";
	if ($from eq "author") {     # 著者サーチ
	    for (my $i=0;$i<=$#ss;$i++) {
		$ss[$i] = $dbh->quote("\%$ss[$i]\%");
		my $pids = &getIdFromAuthorsDB($ss[$i]);
		$ss[$i] = " id IN ( $pids ) "; 
	    }
	} elsif ($from eq "1stauthor") {     # 筆頭著者サーチ
	    for (my $i=0;$i<=$#ss;$i++) {
		$ss[$i] = $dbh->quote("\%$ss[$i]\%");
		my $pids = &getIdFromAuthorsDB($ss[$i],0);
		$ss[$i] = " id IN ( $pids ) "; 
	    }
	} elsif ($from eq "year") {  # 出版年サーチ
	    for (my $i=0;$i<=$#ss;$i++) {
		if ($ss[$i]=~/^\d+$/) { # 数字限定
		    $ss[$i] = $dbh->quote($ss[$i]);
		    $ss[$i] = " year=$ss[$i] ";
		} else {
		    $ss[$i]="";
		    $session->clear("SEARCH$smenu[$j]");
		    &printError('"Year" must be an integer.');
		}
	    }
	} elsif ($from eq "title") {  # タイトルサーチ
	    for (my $i=0;$i<=$#ss;$i++) {
		$ss[$i] = $dbh->quote("\%$ss[$i]\%");
		$ss[$i] = " ( title LIKE $ss[$i] OR title_e LIKE $ss[$i] ) "; 
	    }
	} elsif ($from eq "publish") {  # 出版物サーチ
	    for (my $i=0;$i<=$#ss;$i++) {
		$ss[$i] = $dbh->quote("\%$ss[$i]\%");
		$ss[$i] = " ( journal LIKE $ss[$i] OR journal_e LIKE $ss[$i] OR booktitle LIKE $ss[$i] OR booktitle_e LIKE $ss[$i] ) "; 
	    }
	} elsif ($from eq "tag") {  # タグサーチ
	    for (my $i=0;$i<=$#ss;$i++) {
		$ss[$i] = $dbh->quote($ss[$i]);
		my $pids =  &getIdFromTagDB($ss[$i]);
		$ss[$i] = " id IN ( $pids ) "; 
	    }	
	} elsif ($from eq "all") {  # 全サーチ
	    for (my $i=0;$i<=$#ss;$i++) {
		my $w = $dbh->quote("\%$ss[$i]\%");
		my $pidsTag =  &getIdFromTagDB($dbh->quote($ss[$i]));
		if ($pidsTag ne "") {
		    $pidsTag = "OR id IN ( ".$pidsTag." ) ";
		} 
		my $pidsAuthor =  &getIdFromAuthorsDB($w);
		if ($pidsAuthor ne "") {
		    $pidsAuthor = "OR id IN ( ".$pidsAuthor." ) ";
		} 
		$ss[$i] = " ( editor LIKE $w OR editor_e LIKE $w OR series LIKE $w OR volume LIKE $w OR number LIKE $w OR chapter LIKE $w OR pages LIKE $w OR edition LIKE $w OR school LIKE $w OR type LIKE $w OR institution LIKE $w OR organization LIKE $w OR publisher LIKE $w OR publisher_e LIKE $w OR address LIKE $w OR howpublished LIKE $w OR acceptance LIKE $w OR impactfactor LIKE $w OR url LIKE $w OR note LIKE $w OR annote LIKE $w OR abstract LIKE $w OR year LIKE $w OR month LIKE $w OR title LIKE $w OR title_e LIKE $w OR journal LIKE $w OR journal_e LIKE $w OR booktitle LIKE $w OR booktitle_e LIKE $w  $pidsTag $pidsAuthor )"; 
	    }
	} else {
	    return;
	}
	my @sss;
	foreach (@ss) {
	    push(@sss,$_) if ($_ ne "") ;
	}
	push(@cond," ( ".join(" $lg ",@sss)." ) ") if (@sss);
    }
    # 既発表に限る (ログイン前)
    push(@cond," ( year <= 9999 ) ") if ($login == 0);

    # ptypes テーブルと統合
    push(@cond," ptype=pt_type ");
    push(@cond," pt_lang=$l ");

    my $q = "";
    $q = "WHERE ".join(" AND ",@cond) if (@cond) ;
    $q .= " $order";
    my $limit = $session->param('LIMIT');
    if ($limit =~ /^\d+$/ && $limit > 0) {
	$q .= " LIMIT '$limit'";
    }

    return $q;
}

#=====================================================
# DBからデータ取得 
#=====================================================

sub getDataDB {
    my $q = shift ;
    if ($q eq "") {
	return;
    }

    eval {
	# 文献情報取得 -> $bib
	my $SQL = "SELECT id,style,ptype,author,author_e,editor,editor_e,key,
                      title,title_e,journal,journal_e,booktitle,booktitle_e,
                      series,volume,number,chapter,
                      pages,edition,school,type,institution,organization,
                      publisher,publisher_e,
                      address,month,year,howpublished,acceptance,impactfactor,
                      note,annote,abstract,url
               FROM bib,ptypes $q"; 
	$bib = $dbh->selectall_arrayref($SQL,{Columns => {}});
	# ジャーナル種類 -> @jname
	$SQL = "SELECT DISTINCT journal FROM bib ;";
	my $jnl = $dbh->selectall_arrayref($SQL,{Columns => {}});
	foreach (@$jnl) {
	    push(@jname,$$_{'journal'});
	}

	$SQL = "SELECT paper_id,author_name,author_key FROM authors WHERE paper_id IN ( SELECT id FROM bib,ptypes $q ) ORDER BY paper_id,author_order";
	my $a_ref = $dbh->selectall_arrayref($SQL,{Columns => {}});
	foreach (@$a_ref) {
	    push(@{$authors_hash{$_->{'paper_id'}}->{'author_name'}},$_->{'author_name'});
	    push(@{$authors_hash{$_->{'paper_id'}}->{'author_key'}},$_->{'author_key'});
	}

    };
    
    if ($@) {
	$dbh->disconnect;
	my $emsg = "Incomplete query.";
	$emsg .= "<br /> $@ <br /> query: $q" if ($debug);
	&printError($emsg);
    }
 
    return 0;
}

sub getPtypeDB {
    my $SQL;
    eval {
	my $l = $session->param('LANG') || "ja";
	$l = $dbh->quote($l);

	# 業績種類 -> %ptype
	$SQL = "SELECT pt_type,pt_desc FROM ptypes WHERE pt_lang=$l ORDER BY pt_type;"; 
	my $pt = $dbh->selectall_arrayref($SQL,{Columns => {}});
	foreach (@$pt) {
	    $ptype{$$_{'pt_type'}} = $$_{'pt_desc'};
	}
	$SQL = "SELECT pt_type FROM ptypes WHERE pt_lang=$l ORDER BY pt_order ;"; 
	my $ptord = $dbh->selectcol_arrayref($SQL);
	push(@ptype_order,@$ptord);
    };
    
    if ($@) {
	$dbh->disconnect;
	my $emsg = "Incomplete query.";
	$emsg .= "<br /> $@ <br /> query: $SQL" if ($debug);
	&printError($emsg);
    }
 
    return 0;
}

# データ追加
sub insertDB {
    my $sp = shift;
    my $binfile = shift;
    my %q;
    my $SQL;

    foreach my $p (grep(/edit_/,keys(%$sp))) {
	#$$sp{$p}=~s/'/''/g; # 'のエスケープ
	$p=~/^edit_(.+)$/;
	$q{$1}=$$sp{$p};
    }

    #  INSERT INTO bib 
    #         VALUES ...
    eval { 
	$SQL = "INSERT INTO bib VALUES(null,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?);";
	my $sth = $dbh->prepare($SQL);
	$sth ->execute(
	    $q{'style'},$q{'ptype'},$q{'author'},$q{'editor'},$q{'key'},
	    $q{'title'},$q{'journal'},$q{'booktitle'},$q{'series'},$q{'volume'},
	    $q{'number'},$q{'chapter'},$q{'pages'},$q{'edition'},$q{'school'},
	    $q{'type'},$q{'institution'},$q{'organization'},$q{'publisher'},
	    $q{'address'},$q{'month'},$q{'year'},$q{'howpublished'},$q{'note'},
	    $q{'annote'},$q{'abstract'},$q{'title_e'},$q{'author_e'},$q{'editor_e'},
	    $q{'journal_e'},$q{'booktitle_e'},$q{'publisher_e'},$q{'acceptance'},
	    $q{'impactfactor'},$q{'url'}
	    ); 
	$dbh->commit;

	$SQL = "SELECT MAX(id) FROM bib;"; 
	my $maxid = $dbh->selectrow_array($SQL);
	$session->param('ID',$maxid);

    }; 

    if ($@) { 
	$dbh->rollback; $dbh->disconnect; 
	my $emsg = "Incomplete query.";
	$emsg .= "<br /> $@ <br /> query: $SQL" if ($debug);
	&printError($emsg);
    }
}

# データ更新
sub updateDB {
    my $sp = shift;
    my @q;
    my $SQL;

    foreach my $p (grep(/edit_/,keys(%$sp))) {
#	if ($$sp{$p} ne "") {
	    $$sp{$p}=$dbh->quote($$sp{$p});
	    $p=~/^edit_([\w_]+)$/;
	    push(@q,"$1=$$sp{$p}") if ($1 ne 'upfile' && $1 ne 'tags' && $1 ne 'bibentry');
#	}
    }
 
    #  UPDATE bib 
    #         SET style = '...', ptype = '...',
    #         WHERE id = ???
    my $SQL = "UPDATE bib SET ";
    eval {
	$SQL .= join(",",@q);
	my $id = $dbh->quote($$sp{'ID'});
	$SQL .= " WHERE id=$id;";
#	&printError "Error: $@ $SQL";
 	my $sth = $dbh->do($SQL);
	$dbh->commit;
    };

    if ($@) { 
	$dbh->rollback; $dbh->disconnect; 
	my $emsg = "Incomplete query. While inserting an entry.";
	$emsg .= "<br /> $@ <br /> query: $SQL" if ($debug);
	&printError($emsg);
    }
}

# データ削除
sub deleteDB {
    my $id = shift;
    my $SQL = "DELETE FROM bib WHERE id=\'$id\';";
    $SQL   .= "DELETE FROM files WHERE pid=\'$id\';";
    $SQL   .= "DELETE FROM tags WHERE paper_id=\'$id\';";
    $SQL   .= "DELETE FROM authors WHERE paper_id=\'$id\';";
    eval {
 	my $sth = $dbh->do($SQL);
	$dbh->commit;
    };

    if ($@) { 
	$dbh->rollback; $dbh->disconnect; 
	my $emsg = "Incomplete query. While deleting an entry.";
	$emsg .= "<br /> $@ <br /> query: $SQL" if ($debug);
	&printError($emsg);
    }
}

sub getTitleOnlyDB {
    eval {
	# 文献情報取得 -> $bib
	my $SQL = "SELECT id,title,title_e FROM bib";
	$bib = $dbh->selectall_arrayref($SQL,{Columns => {}});
    };
    
    if ($@) {
	$dbh->disconnect;
	my $emsg = "Incomplete query while getting titles.";
	$emsg .= "<br /> $@ <br />" if ($debug);
	&printError($emsg);
    }
 
    return 0;
}

sub insertFileDB {
    my ($paper_id,$fname,$mimetype,$fh,$fa,$desc) = @_;

    my $SQL = "INSERT INTO files VALUES(null,?,?,?,?,?,?)";
    my $sth = $dbh->prepare($SQL);
    eval {
	$sth->execute($paper_id,$fname,$mimetype,$fh,$fa,$desc);
	$dbh->commit;	  
    };

    if ($@) { 
	$dbh->rollback; $dbh->disconnect; 
	my $emsg = "Incomplete query. While inserting a file.";
	$emsg .= "<br /> $@ <br /> query: $SQL" if ($debug);
	&printError($emsg);
    }

}

sub changeAccessFileDB {
    my ($fid,$fa) = @_;

    my $SQL = "UPDATE files SET access=$fa WHERE id=$fid";
    eval {
	my $sth = $dbh->do($SQL);
	$dbh->commit;
    };

    if ($@) { 
	$dbh->rollback; $dbh->disconnect; 
	my $emsg = "Incomplete query. While updating files db.";
	$emsg .= "<br /> $@ <br /> query: $SQL" if ($debug);
	&printError($emsg);
    }
}

sub changeDescFileDB {
    my ($fid,$desc) = @_;

    $desc = $dbh->quote($desc);
    my $SQL = "UPDATE files SET file_desc=$desc WHERE id=$fid";
    eval {
	my $sth = $dbh->do($SQL);
	$dbh->commit;
    };

    if ($@) { 
	$dbh->rollback; $dbh->disconnect; 
	my $emsg = "Incomplete query. While updating files db.";
	$emsg .= "<br /> $@ <br /> query: $SQL" if ($debug);
	&printError($emsg);
    }
}

sub getFileListDB {
    my ($pid,$hash) = @_;

    my $SQL = "SELECT id,filename,access,mimetype,file_desc FROM files WHERE pid=$pid;";

    eval {
	my $f = $dbh->selectall_arrayref($SQL,{Columns => {}});
	foreach (@$f) {
	    if ($_->{'access'}==0) { 
		$hash->{$_->{'id'}.",filename"} = $_->{'filename'};
		$hash->{$_->{'id'}.",mimetype"} = $_->{'mimetype'};
		$hash->{$_->{'id'}.",file_desc"} = $_->{'file_desc'};
		$hash->{$_->{'id'}.",access"} = $_->{'access'};
	    } elsif ($_->{'access'}==1 && $login == 1) {
		$hash->{$_->{'id'}.",filename"} = $_->{'filename'};
		$hash->{$_->{'id'}.",mimetype"} = $_->{'mimetype'};
		$hash->{$_->{'id'}.",file_desc"} = $_->{'file_desc'};
		$hash->{$_->{'id'}.",access"} = $_->{'access'};
	    }		
	}
    };

    if ($@) { 
	$dbh->rollback; $dbh->disconnect; 
	my $emsg = "Incomplete query. While getting a file list.";
	$emsg .= "<br /> $@ <br /> query: $SQL" if ($debug);
	&printError($emsg);
    }
}

# file削除
sub deleteFileDB {
    my $fid = shift;
    my $SQL = "DELETE FROM files WHERE id=\'$fid\' ;";
    eval {
 	my $sth = $dbh->do($SQL);
	$dbh->commit;
    };

    if ($@) { 
	$dbh->rollback; $dbh->disconnect; 
	my $emsg = "Incomplete query. While deleting a file.";
	$emsg .= "<br /> $@ <br /> query: $SQL" if ($debug);
	&printError($emsg);
    }
}

sub getTagListDB {
    my ($pid) = @_;
    my @taglist;

    my $SQL = "SELECT tag FROM tags WHERE paper_id=$pid;";
    eval {
	my $f = $dbh->selectall_arrayref($SQL,{Columns => {}});
	foreach (@$f) {
	    push(@taglist,$_->{'tag'});
	}
    };
    if ($@) { 
	$dbh->rollback; $dbh->disconnect; 
	my $emsg = "Incomplete query. While getting a tag list.";
	$emsg .= "<br /> $@ <br /> query: $SQL" if ($debug);
	&printError($emsg);
    }

    return join(" ",@taglist);
}

sub getIdFromTagDB {
    my ($tag) = @_;
    my @idlist;

    my $SQL = "SELECT paper_id FROM tags WHERE tag=$tag;";
    eval {
	my $f = $dbh->selectall_arrayref($SQL,{Columns => {}});
	foreach (@$f) {
	    push(@idlist,$_->{'paper_id'});
	}
    };
    if ($@) { 
	$dbh->rollback; $dbh->disconnect; 
	my $emsg = "Incomplete query. While getting an id list from tag.";
	$emsg .= "<br /> $@ <br /> query: $SQL" if ($debug);
	&printError($emsg);
    }
    return join(",",@idlist);
}

sub getTop10TagDB {
    my @tf;
    my $SQL = "select tag,count(tag) from tags group by tag order by count(tag) desc;";
    eval {
	my $f = $dbh->selectall_arrayref($SQL,{Columns => {}});
	foreach (@$f) {
	    push(@tf,$_->{'tag'});
	    push(@tf,$_->{'count(tag)'});
	}
    };
    if ($@) { 
	$dbh->rollback; $dbh->disconnect; 
	my $emsg = "Incomplete query. While getting an top 10 list from tag.";
	$emsg .= "<br /> $@ <br /> query: $SQL" if ($debug);
	&printError($emsg);
    }
    return join(",",@tf);
}

# 与えられたid群に関連するタグを抽出
sub getMyTagDB {
    my ($pids) = @_;
    my @tf;
    my $SQL = "SELECT tag,count(tag) FROM tags WHERE paper_id IN ( $pids ) GROUP BY tag ORDER BY count(tag) desc;";
    eval {
	my $f = $dbh->selectall_arrayref($SQL,{Columns => {}});
	foreach (@$f) {
	    push(@tf,$_->{'tag'});
	    push(@tf,$_->{'count(tag)'});
	}
    };
    if ($@) { 
	$dbh->rollback; $dbh->disconnect; 
	my $emsg = "Incomplete query. While getting an top 10 list from tag.";
	$emsg .= "<br /> $@ <br /> query: $SQL" if ($debug);
	&printError($emsg);
    }
    return join(",",@tf);
}

sub updateTagDB {
    my ($pid,$tag) = @_;

    my $SQL = "DELETE FROM tags WHERE paper_id=$pid ;";
    eval {
	my $sth = $dbh->do($SQL);
	$dbh->commit;
	foreach (split(/[,\s]+/,$tag)) {
	    $SQL = "INSERT INTO tags VALUES(null,?,?)";
	    my $sth = $dbh->prepare($SQL);
	    $sth->execute($pid,$_);
	}
	$dbh->commit;	  
    };
    if ($@) { 
	$dbh->rollback; $dbh->disconnect; 
	my $emsg = "Incomplete query. While updating tag DB.";
	$emsg .= "<br /> $@ <br /> query: $SQL" if ($debug);
	&printError($emsg);
    }
}

sub deleteTagDB {
    my $taglistref = shift;
    foreach my $tag (@$taglistref) {
	$tag = $dbh->quote($tag);
	my $SQL = "DELETE FROM tags WHERE tag=$tag ;";
	eval {
	    my $sth = $dbh->do($SQL);
	    $dbh->commit;
	};
	if ($@) { 
	    $dbh->rollback; $dbh->disconnect; 
	    my $emsg = "Error while deleting tag from DB.";
	    $emsg .= "<br /> $@ <br /> query: $SQL" if ($debug);
	    &printError($emsg);
	}
    }
}

sub downloadFileDB {
    my ($id) = @_;

    my $SQL = "SELECT filename,mimetype,file,access FROM files WHERE id=$id;";
    my @ary;
    eval {
	@ary = $dbh->selectrow_array($SQL);
	if (@ary == ()) {
	    return;
	}
    };

    if ($@) { 
	$dbh->rollback; $dbh->disconnect; 
	my $emsg = "Incomplete query. While getting a file entity.";
	$emsg .= "<br /> $@ <br /> query: $SQL" if ($debug);
	&printError($emsg);
    }
    return ($ary[0],$ary[1],$ary[2],$ary[3]);
}


sub getIdFromAuthorsDB {
    my ($author,$ord) = @_;
    my @idlist;

    my $SQL = "SELECT paper_id FROM authors WHERE ( author_name LIKE $author OR author_key LIKE $author) ";
    if (defined $ord) {
	$SQL .= " AND author_order='$ord'";
    }
    eval {
	my $f = $dbh->selectall_arrayref($SQL,{Columns => {}});
	foreach (@$f) {
	    push(@idlist,$_->{'paper_id'});
	}
    };
    if ($@) { 
	$dbh->rollback; $dbh->disconnect; 
	my $emsg = "Incomplete query. While getting an id list from authors.";
	$emsg .= "<br /> $@ <br /> query: $SQL" if ($debug);
	&printError($emsg);
    }
    return join(",",@idlist);
}

sub getAuthorListDB {
    my @al;
    my $SQL = "SELECT author_name,author_key FROM authors WHERE author_key not null GROUP BY author_name;";
    eval {
	my $f = $dbh->selectall_arrayref($SQL,{Columns => {}});
	foreach (@$f) {
	    $_->{'author_name'}=~s/\s//g if (&isJapanese($_->{'author_name'}));
	    push(@al,"\"$_->{'author_name'}\": \"$_->{'author_key'}\"");
	}
    };
    if ($@) { 
	$dbh->rollback; $dbh->disconnect; 
	my $emsg = "Incomplete query. While getting author list from authors.";
	$emsg .= "<br /> $@ <br /> query: $SQL" if ($debug);
	&printError($emsg);
    }
    return join(",\n",@al);
}

sub deleteAuthorDB {
    my ($pid) = @_;

    my $SQL = "DELETE FROM authors WHERE paper_id=$pid ;";
    eval {
	my $sth = $dbh->do($SQL);
	$dbh->commit;
    };
    if ($@) { 
	$dbh->rollback; $dbh->disconnect; 
	my $emsg = "Incomplete query. While deleting author list.";
	$emsg .= "<br /> $@ <br /> query: $SQL" if ($debug);
	&printError($emsg);
    }
}

sub registAuthorDB {
    my ($pid,$a_ord,$a_name,$a_name_e) = @_;
    my $SQL = "";
    eval {
	my $SQL = "INSERT INTO authors VALUES(null,?,?,?,?)";
	my $sth = $dbh->prepare($SQL);
	$sth->execute($pid,$a_ord,$a_name,$a_name_e);
	$dbh->commit;	  
    };
    if ($@) { 
	$dbh->rollback; $dbh->disconnect; 
	my $emsg = "Incomplete query. While inserting author list.";
	$emsg .= "<br /> $@ <br /> query: $SQL" if ($debug);
	&printError($emsg);
    }
}

sub add_categoryDB {
    my $newcatname = shift;

    my $l = $session->param('LANG') || "ja";
    my $SQL = "";
    eval {
	my $SQL = "SELECT MAX(pt_type) FROM ptypes;";
	my $maxptype = $dbh->selectrow_array($SQL);
	$SQL = "SELECT MAX(pt_order) FROM ptypes;";
	my $maxptypeorder = $dbh->selectrow_array($SQL);
	$SQL = "INSERT INTO ptypes VALUES(null,?,?,?,?) ;";
	my $sth = $dbh->prepare($SQL);
	$sth->execute($maxptype+1,$maxptypeorder+1,$l,$newcatname);
	$sth = $dbh->prepare($SQL);
	$sth->execute($maxptype+1,$maxptypeorder+1,($l eq "ja" ? "en" : "ja"),$newcatname);
	$dbh->commit;
    };
    if ($@) { 
	$dbh->rollback; $dbh->disconnect; 
	my $emsg = "Incomplete query. While adding a category.";
	$emsg .= "<br /> $@ <br /> query: $SQL" if ($debug);
	&printError($emsg);
    }
}

sub mov_categoryDB {
    my $delpid = shift;
    my $movpid = shift;

    $movpid = $dbh->quote($movpid);
    $delpid = $dbh->quote($delpid);
    my $SQL = "";
    eval {
	my $SQL = "UPDATE bib SET ptype=$movpid WHERE ptype=$delpid ;";
 	my $sth = $dbh->do($SQL);
	$dbh->commit;
    };
    if ($@) { 
	$dbh->rollback; $dbh->disconnect; 
	my $emsg = "Incomplete query. While moving a category.";
	$emsg .= "<br /> $@ <br /> query: $SQL" if ($debug);
	&printError($emsg);
    }

}
sub del_categoryDB {
    my $pid = shift;
    $pid = $dbh->quote($pid);
    my $SQL = "";
    eval {
	my $SQL = "DELETE FROM ptypes WHERE pt_type=$pid ;";
 	my $sth = $dbh->do($SQL);
	$dbh->commit;
    };
    if ($@) { 
	$dbh->rollback; $dbh->disconnect; 
	my $emsg = "Incomplete query. While deleting a category.";
	$emsg .= "<br /> $@ <br /> query: $SQL" if ($debug);
	&printError($emsg);
    }
}

sub ren_categoryDB {
    my $pid = shift;
    my $name = shift;

    my $l = $session->param('LANG') || "ja";
    $l = $dbh->quote($l);
    $pid = $dbh->quote($pid);
    $name = $dbh->quote($name);
    my $SQL = "";
    eval {
	my $SQL = "UPDATE ptypes SET pt_desc=$name WHERE pt_type=$pid AND pt_lang=$l ;";
 	my $sth = $dbh->do($SQL);
	$dbh->commit;
    };
    if ($@) { 
	$dbh->rollback; $dbh->disconnect; 
	my $emsg = "Incomplete query. While updating a category.";
	$emsg .= "<br /> $@ <br /> query: $SQL" if ($debug);
	&printError($emsg);
    }
}

sub ord_categoryDB {
    my $typ = shift;
    my $new = shift;

    $new = $dbh->quote($new);
    $typ = $dbh->quote($typ);
    my $SQL = "";
    eval {
	my $SQL = "UPDATE ptypes SET pt_order=$new WHERE pt_type=$typ;";
 	my $sth = $dbh->do($SQL);
	$dbh->commit;
    };
    if ($@) { 
	$dbh->rollback; $dbh->disconnect; 
	my $emsg = "Incomplete query. While reordering a category.";
	$emsg .= "<br /> $@ <br /> query: $SQL" if ($debug);
	&printError($emsg);
    }

}

sub getCacheFromCDB {
    # ログインしている場合は常にcache off
    return if ($login == 1);
    return if (defined($cgi->param('LOGIN')) && $cgi->param('LOGIN') eq "on");
    return if (defined($cgi->param('STATIC')));
    return if (defined($cgi->param('XML')));
    return if (defined($cgi->param('RSS')));

    # 非ログイン状態に限り
    my $SQL;
    my $cdbh;
    eval {
	$cdbh = DBI->connect("dbi:SQLite:dbname=$CACHE_DB", undef, undef, 
			     { RaiseError => 1 });
	$cdbh->{sqlite_unicode} = 1;
	$SQL = "SELECT name FROM sqlite_master WHERE type='table'"; 
	my $ref = $cdbh->selectall_arrayref($SQL);
	my @dbs;
	foreach (@$ref) {
	    push(@dbs,$_->[0]);
	}
	if (grep(/^cache$/,@dbs) == ()) {    
	    $SQL = "CREATE TABLE cache(id integer primary key autoincrement, url text not null, page  text);";
	    $cdbh->do($SQL);
	    $cdbh->commit;
	}
    };
    my $url = $cdbh->quote(&generateURL);
    my @p;
    eval {
	$SQL = "SELECT page FROM cache WHERE url=$url ;"; 
	@p = $cdbh->selectrow_array($SQL);
    };    
    if ($@) {
	$cdbh->disconnect;
	my $emsg = "Error while getting from CDB";
	$emsg .= "<br /> $@ <br /> query: $SQL" if ($debug);
	&printError($emsg);
    }
    $cdbh->disconnect;    
    return $p[0];
}

sub storeCacheToCDB {
    return if ($login == 1);
    my $h = shift;
    my $d = shift;
    my $cdbh;
    eval {
	$cdbh = DBI->connect("dbi:SQLite:dbname=$CACHE_DB", undef, undef, 
				{AutoCommit => 0, RaiseError => 1 });
	$cdbh->{sqlite_unicode} = 1;
    };
    my $url = &generateURL;
    my $SQL = '';
    eval {
	$SQL = "INSERT INTO cache VALUES(null,?,?)";
	my $sth = $cdbh->prepare($SQL);
	$sth->execute($url,$$h.$$d);
	$cdbh->commit;
    };
    if ($@) { 
	$cdbh->disconnect; 
	my $emsg = "Error while inserting CDB.";
	$emsg .= "<br /> $@ <br /> query: $SQL" if ($debug);
	&printError($emsg);
    }
    return;
}

sub expireCacheFromCDB {
    if ($use_cache) {
	my $cdbh;
	eval {
	    $cdbh = DBI->connect("dbi:SQLite:dbname=$CACHE_DB", undef, undef, 
				 {AutoCommit => 0, RaiseError => 1 });
	    $cdbh->{sqlite_unicode} = 1;
	};
	return if ($@);
	my $SQL = 'DELETE FROM cache;';
	eval {
	    $cdbh->do($SQL);
	    $cdbh->commit;	  
	};
	if ($@) { 
	    $cdbh->disconnect; 
	my $emsg = "Error while deleting CDB.";
	    $emsg .= "<br /> $@ <br /> query: $SQL" if ($debug);
	    &printError($emsg);
	}
    }
}

sub getOptionsDB {
    my $odbh;
    eval {
	$odbh  = DBI->connect("dbi:SQLite:dbname=$OPTIONS_DB", undef, undef, 
			      {AutoCommit => 0, RaiseError => 1 });
	$odbh->{sqlite_unicode} = 1;
    };
    &printError($@) if ($@) ;
    my $SQL = "SELECT name FROM sqlite_master WHERE type='table'"; 
    eval {
	my $ref = $odbh->selectall_arrayref($SQL);
	my @dbs;
	foreach (@$ref) {
	    push(@dbs,$_->[0]);
	}
	my $sth;
	if (grep(/^config$/,@dbs) == ()) {
	    $SQL = "CREATE TABLE config(id integer primary key autoincrement, name text not null, val text not null)";
	    $sth = $odbh->do($SQL);
	    if(!$sth){
		die($odbh->errstr);
	    }
	    foreach (keys(%opts)) {
		$SQL = "INSERT INTO config VALUES(null,?,?)";
		$sth = $odbh->prepare($SQL);
		$sth->execute($_,$opts{$_});
	    }
	    $odbh->commit;
	}
    };
    &printError($@) if ($@);

    # odbhからoption取得
    foreach my $n (keys(%opts)) {
	my $nq = $odbh->quote($n);
	$SQL = "SELECT val FROM config WHERE name=$nq";
	my @val = $odbh->selectrow_array($SQL);
	if (@val != ()) {
	    eval "\$$n = \'$val[0]\';";
	    print STDERR "$n = $val[0];" if $debug;
	} else {
	    $SQL = "INSERT INTO config VALUES(null,?,?)";
	    my $sth = $odbh->prepare($SQL);
	    $sth->execute($n,$opts{$n});
	    $odbh->commit;
	}
    }

#    $SQL = "SELECT name,val FROM config;";
#    my $optref = $odbh->selectall_arrayref($SQL,{Columns => {}});
#    foreach my $op (@$optref) {
#    	eval "\$$$op{'name'} = \'$$op{'val'}\';";
#    }

    $odbh->disconnect;
}

sub updateOptionsDB {
    my $odbh;
    my $SQL;
    eval {
	$odbh = DBI->connect("dbi:SQLite:dbname=$OPTIONS_DB", undef, undef, 
			     {AutoCommit => 0, RaiseError => 1 });
	$odbh->{sqlite_unicode} = 1;
	my ( $name,$val ) = @_;
	$name = $odbh->quote($name);
	$val = $odbh->quote($val);
	
	$SQL = "UPDATE config SET val=$val WHERE name=$name ;"; 
	$odbh->do($SQL);
	$odbh->commit;
	$odbh->disconnect;
    };
    if ($@) { 
	$odbh->rollback; $odbh->disconnect; 
	my $emsg = "Error while deleting ODB.";
	$emsg .= "<br /> $@ <br /> query: $SQL" if ($debug);
	&printError($emsg);
    }
}

#=====================================================
# 画面描画 
#=====================================================

sub printScreen {

    my $document;
    my $mode = $session->param('MODE') || $session->param('prevMODE') || "list";
    my $lang = $cgi->param('LANG') || $session->param('LANG') || "ja";

    my $doc;

    my $header; my $htmlh;
    if (defined($cgi->param('STATIC'))) {
	eval {
	    $document = HTML::Template->new(filename => "$TMPLDIR/$tmpl_name/static.tmpl"); 
	};
	&printError($@) if ($@);

	my $ttl;
	eval "\$ttl = \$title_$mode;";
	($header,$htmlh) = &printHeader;    
	$document->param(CHARSET => $htmlh);
	$document->param(PAGE_TITLE => $ttl) ; #$msg{"Title_$mode"});
	$document->param(CONTENTS=> &printBody);    
	$document->param(FOOTER=> &printFooter);
	$document->param(MAIN_TITLE => $titleOfSite);

	$doc = $document->output;

    } elsif (defined($cgi->param('SSI'))) {
	eval {
	    $document = HTML::Template->new(filename => "$TMPLDIR/$tmpl_name/none.tmpl");
	};
	if ($@) { 
	    &printError($@);
	}

	($header,$htmlh) = &printHeader;    
	$document->param(CONTENTS=> &printBody);    
	$doc = $document->output;

    } elsif ($use_XML && defined($cgi->param('XML'))) {
	require XML::Simple;
	$header =  $cgi->header(
	    -type => 'text/xml',
	    -charset => 'utf-8'	
	    );
	my $bibhash;
	$bibhash->{'bib'} = [@$bib];

	$doc = XML::Simple::XMLout($bibhash,XMLDecl => 1,NoAttr => 1,RootName => 'bibs');

    } elsif ($use_RSS && defined($cgi->param('RSS'))) {

	my %check ;
	my @opt = $cgi->param('OPT');
	if (@opt != ()) {
	    foreach (@opt) {
		$check{$_} = "checked" if ($_);
	    }	
	} else {
	    @opt = ('underline','abbrev','shortvn','jcr','note');
	    foreach (@opt) {
		$check{$_} = $cgi->cookie($_) if (defined($cgi->cookie($_)));
	    }
#	    $session->param('OPT',keys(%check));
	}

	require XML::RSS;
	$header =  $cgi->header(
	    -type => 'application/rss+xml',
	    -charset => 'utf-8'	
	    );
	my $rss = XML::RSS->new(version => "2.0"); # , encode_output => 0));
	my $url = &generateURL;
	$rss->channel(
	    title => "PMAN3 RSS",
	    link => "http://$httpServerName$url",
	    description => "Search result of PMAN3"
	    );
	my $ssp = $session->param_hashref();
	#my $lang = $cgi->param('LANG') || $session->param('LANG') || "ja";
	foreach (@$bib) {
	    my $id = $_->{'id'};
	    my $aline;
	    if ($ssp->{'MODE'} ne "bbl" ) {
		&createAList(\$aline,\%check,$ssp,$_);
	    } else {
		$aline = &genBib($_);
		$aline = "<pre>".$aline."</pre>";
	    }
	    $rss->add_item(
		title => "[$ptype{$_->{'ptype'}}] $_->{'title'}",
		link => "http://$httpServerName$scriptName?D=$id",
		description => $aline
		);
	}
	$doc = $rss->as_string;
    } else {
	eval {
	    $document = HTML::Template->new(filename => "$TMPLDIR/$tmpl_name/main.tmpl");
	};
	if ($@) { 
	    &printError($@);
	}

	my $ttl;
	eval "\$ttl = \$title_$mode;";

	($header,$htmlh) = &printHeader;    
	$document->param(CHARSET => $htmlh);
	
	$document->param(PAGE_TITLE => $ttl); #$msg{"Title_$mode"});
	
	my ($topm,$searchm,$viewm) = &printMenu;    
	$document->param(TOPMENU => $topm);
	$document->param(SEARCHMENU => $searchm);
	$document->param(VIEWMENU => $viewm);

	$document->param(TAGMENU => &printTagMenu);
	$document->param(MESSAGEMENU => &printMessageMenu);

	$document->param(CONTENTS=> &printBody);    
	$document->param(FOOTER=> &printFooter);
	$document->param(MAIN_TITLE => $titleOfSite);

#######################[TIME]
	$t2 = Time::HiRes::tv_interval($t0);
#######################[TIME]
	
	$doc = $document->output;
	if ($use_cache) {
	    # $header と $doc をDBに保存．
	    if (utf8::is_utf8($doc)) {
		$doc = encode('utf-8', $doc);
	    }
	    &storeCacheToCDB(\$header,\$doc);
	}
    }
    # キャッシュ書き込み処理の実装部
    # LOGIN状態でない場合のみ．
    #   ここでgenerateURLの内容をキーとしてcacheDBを保存．
    print $header;
    if (utf8::is_utf8($doc)) {
	print encode('utf-8', $doc);
    } else {
	print $doc;
    }
}

# エラー表示
sub printError {
    my $message = shift;

    my $document = HTML::Template->new(filename => "$TMPLDIR/$tmpl_name/error.tmpl");
    
    my $l;
    eval {
	$l = $session->param('LANG') || "ja";
    };
    if ($@) {
	$l = "en";
    }
    require "$LIBDIR/lang.$l.pl";

    my ($header,$htmlh) = &printHeader;    
    $document->param(CHARSET => $htmlh);

    my ($topm,$searchm,$viewm) = &printMenu;    
    $document->param(TOPMENU => $topm);
    $document->param(VIEWMENU => $viewm);

    $document->param(CONTENTS=> $message);    
    $document->param(FOOTER=> &printFooter);

    my $doc = $document->output;

    print $header;
    if (utf8::is_utf8($doc)) {
	print encode('utf-8', $doc);
    } else {
	print $doc;
    }

    $dbh->disconnect;
    exit(0);
}

# 初期ガイド表示
sub printInfo {
    my $message = shift;
    my $document = HTML::Template->new(filename => "$TMPLDIR/$tmpl_name/main.tmpl");
    
    my $l;
    eval {
	$l = $session->param('LANG') || "ja";
    };
    if ($@) {
	$l = "en";
    }
    require "$LIBDIR/lang.$l.pl";

    my ($header,$htmlh) = &printHeader;    
    $document->param(CHARSET => $htmlh);
    
    $document->param(MAIN_TITLE => $titleOfSite);
    $document->param(PAGE_TITLE => "Initial Setup");
    
    $document->param(TOPMENU => "");
    $document->param(SEARCHMENU => "");
    $document->param(VIEWMENU => "");
    
    $document->param(TAGMENU => "");
    $document->param(MESSAGEMENU => "no bib is registered.");
    
    $document->param(CONTENTS=> $message);    
    $document->param(FOOTER=> &printFooter);
    
    my $doc = $document->output;

    print $header;
    if (utf8::is_utf8($doc)) {
	print encode('utf-8', $doc);
    } else {
	print $doc;
    }

    $dbh->disconnect;
    exit(0);
}

#=====================================================
# Menu 描画 (MDOE別) 
#=====================================================
sub printMenu {
    my $mode = $session->param('MODE') || $session->param('prevMODE') || "list";
    my $mmode = $session->param('MENU') || "simple";

    # 言語・詳細
    my $topmenu = "<p>";

    if (grep(/^$mode$/,('list','table','latex','bbl'))) {

	my $tabsimple = $mmode eq "simple" ? "activetoptab" : "toptab";
	my $tabdetail = $mmode eq "detail" ? "activetoptab" : "toptab";

	$topmenu .= <<EOM;
  Search:
  <a class=$tabsimple href="$scriptName?MENU=simple;MODE=$mode">$topMenu{'simple'}</a><span class="hide"> | </span>
  <a class=$tabdetail href="$scriptName?MENU=detail;MODE=$mode">$topMenu{'detail'}</a><span class="hide"> || </span>
EOM
    }

    my $lang = $session->param('LANG') || "ja";
    my $taben = $lang eq "en" ? "activetoptab" : "toptab";
    my $tabja = $lang eq "ja" ? "activetoptab" : "toptab";

    $topmenu .= <<EOM;
  Language:
  <a class=$taben href="$scriptName?LANG=en;MODE=$mode">$topMenu{'english'}</a><span class="hide"> | </span>
  <a class=$tabja href="$scriptName?LANG=ja;MODE=$mode">$topMenu{'japanese'}</a><span class="hide"> || </span>
EOM

    $topmenu .= <<EOM;
  Login:
EOM
    if ($login == 1) {
	$topmenu .= <<EOM;
  <a class="toptab" href="$scriptName?LOGIN=off">$topMenu{'logout'}</a><span class="hide"> | </span>
  <a class="toptab" href="$scriptName?MODE=category">$topMenu{'category'}</a><span class="hide"> | </span>
  <a class="toptab" href="$scriptName?MODE=config">$topMenu{'config'}</a><span class="hide"> | </span>
EOM
    } else {
	$topmenu .= <<EOM;
  <a class="toptab" href="$scriptName?LOGIN=on">$topMenu{'login'}</a><span class="hide"> | </span>
EOM
    }
    $topmenu .= <<EOM;
  Help: <a class="toptab" href="http://se.is.kit.ac.jp/~o-mizuno/pman3help.html">$topMenu{'help'}</a><span class="hide"> | </span>
  </p>
EOM

    # 検索メニュー
    my $searchmenu;

    if (grep(/^$mode$/,('list','table','latex','bbl'))) {
	$searchmenu .= <<EOM;
<script type="text/javascript">
function clearFormAll() {
    for (var i=0; i<document.forms.length; ++i) {
        clearForm(document.forms[i]);
    }
}
function clearForm(form) {
    for(var i=0; i<form.elements.length; ++i) {
        clearElement(form.elements[i]);
    }
}
function clearElement(element) {
    switch(element.type) {
        case "text":
        case "password":
        case "textarea":
            element.value = "";
            return;
        case "checkbox":
        case "radio":
            element.checked = false;
            return;
        case "select-one":
        case "select-multiple":
            element.selectedIndex = 0;
            return;
        default:
	return;
    }
}
</script>
<form name="search" method="POST" action="$scriptName">
<input type="hidden" name="MODE" value="$mode" />
<div id="smenu">
EOM

    my $multi = "onChange=\"doument.search.submit();\"";
    $multi = "multiple size=\"7\"" if ($mmode eq "detail") ;

    $searchmenu .= <<EOM;
    <select class="longinput" name="PTYPE" $multi>
EOM

    # PTYPEに応じてメニューを作成 (なぜか異様に面倒なことに)

    my @apt = ();
    if (ref($session->param('PTYPE')) eq 'ARRAY') {
	@apt = @{$session->param('PTYPE')};
    }
    my $pt =    $session->param('PTYPE') eq "" ? 'all' : $session->param('PTYPE');
    if ($mmode eq "simple") {
	if (@apt) {
	    if ($#apt == $#ptype_order) {
		$pt = "all";
	    } else {
		$pt = $apt[0];
	    }
	}

	if ($pt eq "all") {
	    $searchmenu .= "<option value=\"all\" selected>$msg{'all'}</option>";
	} else {
	    $searchmenu .= "<option value=\"all\">$msg{'all'}</option>";
	}
	foreach (@ptype_order) {
	    my $sel = "";
	    if ($pt eq $_) {
		$sel = "selected";
	    }
	    $searchmenu .= "<option value=\"$_\" $sel>$ptype{$_}</option>";
	}
    } else {
	if (@apt) {
	    foreach my $j (@ptype_order) {
		my $sel = "";
		if (grep(/^$j$/,@apt) || grep(/all/,@apt)) {
		    $sel = "selected";
		}
		$searchmenu .= "<option value=\"$j\" $sel>$ptype{$j}</option>";
	    }
	} else {
	    foreach (@ptype_order) {
		my $sel = "";
		if ($pt eq $_ || $pt eq "all") {
		    $sel = "selected";
		}
		$searchmenu .= "<option value=\"$_\" $sel>$ptype{$_}</option>";
	    }
	}	    
    }
    $searchmenu .= <<EOM;
    </select>

    <select class="longinput" name="SORT" onChange="document.search.submit();">
EOM

    my @selected = ();
    if ($session->param('SORT') eq "ascend") {
	$selected[0] = "selected";
    } elsif ($session->param('SORT') eq "descend") {
	$selected[1] = "selected";
    } elsif ($session->param('SORT') eq "t_ascend") {
	$selected[2] = "selected";
    } elsif ($session->param('SORT') eq "y_t_ascend") {
	$selected[4] = "selected";
    } elsif ($session->param('SORT') eq "y_t_descend") {
	$selected[5] = "selected";
    } else {
	$selected[3] = "selected";
    }

    $searchmenu .= <<EOM;
    <option value="ascend"   $selected[0]>$msg{'ascend'}</option>
    <option value="descend"   $selected[1]>$msg{'descend'}</option>
    <option value="t_ascend" $selected[2]>$msg{'t_ascend'}</option>
    <option value="t_descend" $selected[3]>$msg{'t_descend'}</option>
    <option value="y_t_ascend" $selected[4]>$msg{'y_t_ascend'}</option>
    <option value="y_t_descend" $selected[5]>$msg{'y_t_descend'}</option>
    </select>
</div>
<div id="smenu">
EOM
    my @selected = ();
    my $f = $session->param('FROM') || "all";
    if ($f eq "author") {
	$selected[0] = "selected";
    } elsif ($f eq "title") {
	$selected[1] = "selected";
    } elsif ($f eq "publish") {
	$selected[2] = "selected";
    } elsif ($f eq "year") {
	$selected[3] = "selected";
    } elsif ($f eq "tag") {
	$selected[4] = "selected";
    } elsif ($f eq "1stauthor") {
	$selected[5] = "selected";
    } elsif ($f eq "all") {
	$selected[6] = "selected";
    }

    $searchmenu .= <<EOM;
    <span id="searchbox">
      <select class="longinput" name="FROM">
        <option value="all" $selected[6]>$msg{'all'}</option>
        <option value="author" $selected[0]>$msg{'author'}</option>
        <option value="1stauthor" $selected[5]>$msg{'1stauthor'}</option>
        <option value="title" $selected[1]>$msg{'title'}</option>
        <option value="publish" $selected[2]>$msg{'publish'}</option>
        <option value="year" $selected[3]>$msg{'year'}</option>
        <option value="tag" $selected[4]>$msg{'tags'}</option>
      </select>
EOM

    my $search = $session->param('SEARCH') || "" ;
    $search=~s/\"//g;
    utf8::decode($search) if (!utf8::is_utf8($search)) ;
    $searchmenu .= <<EOM;
        <input class="longinput" name="SEARCH" type="text" size="25" value="$search" />
EOM

    my @selected = ();
    my $logic = $session->param('LOGIC') || "and" ;
    if ($logic eq "and") {
	$selected[0] = "selected";
    } elsif ($logic eq "or") {
	$selected[1] = "selected";
    }

    $searchmenu .= <<EOM;
      <select class="shortinput" name="LOGIC">
        <option value="and" $selected[0]>and</option>
        <option value="or" $selected[1]>or</option>
      </select>
    </span>
EOM
    # MENU = detailだったら
    if ($mmode eq "detail") {
	for (my $i = 1;$i<=3;$i++) {
	    my @selected = ();
	    my $f = $session->param("FROM$i") || "all";
	    if ($f eq "author") {
		$selected[0] = "selected";
	    } elsif ($f eq "title") {
		$selected[1] = "selected";
	    } elsif ($f eq "publish") {
		$selected[2] = "selected";
	    } elsif ($f eq "year") {
		$selected[3] = "selected";
	    } elsif ($f eq "tag") {
		$selected[4] = "selected";
	    } elsif ($f eq "1stauthor") {
		$selected[5] = "selected";
	    } elsif ($f eq "all") {
		$selected[6] = "selected";
	    }

	    $searchmenu .= <<EOM;
    <br /><span id="searchbox">
      <select class="longinput" name="FROM$i">
        <option value="all" $selected[6]>$msg{'all'}</option>
        <option value="author" $selected[0]>$msg{'author'}</option>
        <option value="1stauthor" $selected[5]>$msg{'1stauthor'}</option>
        <option value="title" $selected[1]>$msg{'title'}</option>
        <option value="publish" $selected[2]>$msg{'publish'}</option>
        <option value="year" $selected[3]>$msg{'year'}</option>
        <option value="tag" $selected[4]>$msg{'tags'}</option>
      </select>
EOM

            my $search = $session->param("SEARCH$i") || "" ;
	    utf8::decode($search)  if (!utf8::is_utf8($search)) ;;
	    $searchmenu .= <<EOM;
        <input class="longinput" name="SEARCH$i" type="text" size="25" value="$search" />
EOM

            my @selected = ();
	    my $logic = $session->param("LOGIC$i") || "and" ;
	    if ($logic eq "and") {
		$selected[0] = "selected";
	    } elsif ($logic eq "or") {
		$selected[1] = "selected";
	    }
	
	    $searchmenu .= <<EOM;
      <select class="shortinput" name="LOGIC$i">
        <option value="and" $selected[0]>and</option>
        <option value="or" $selected[1]>or</option>
      </select>
    </span>
EOM
	}
    }  

    $searchmenu .= <<EOM;
</div>
<div id="smenu">
<input class="shortinput" type="submit" value="Search">
<input class="shortinput" type="button" value="Clear" onclick="clearFormAll();">
</div>
</form>
EOM
    }

    # ビューメニュー
    my $viewmenu .= <<EOM;
<ul id="menu-menu" class="sf-menu view">
EOM

    if ($login == 1) {
	my $id = $session->param('ID');
	$viewmenu .= <<EOM;
<li class="menu-item"><a href="$scriptName?MODE=add">$viewMenu{'add'}</a></li>
<li class="menu-item"><a href="$scriptName?MODE=bib">$viewMenu{'bib'}</a></li>
EOM
        if ($mode eq "detail") {
	    $viewmenu .= <<EOM;
<li class="menu-item"><a href="$scriptName?MODE=edit;ID=$id">$viewMenu{'edit'}</a></li>
EOM
        }	    

        if ($mode eq "edit") {
	    $viewmenu .= <<EOM;
<li class="menu-item"><a href="$scriptName?MODE=delete;ID=$id" onClick="if( !confirm(\'$msg{'deleteConfirm'}\')) {return false;}">$viewMenu{'delete'}</a></li>
EOM
        }	    
	#$viewmenu .= "<li class=\"hide\"></li>";
    }

    $viewmenu .= <<EOM;
<li class="menu-item"><a href="$scriptName?MODE=list">$viewMenu{'list'}</a></li>
<li class="menu-item"><a href="$scriptName?MODE=table">$viewMenu{'table'}</a></li>
<li class="menu-item"><a href="$scriptName?MODE=latex">$viewMenu{'latex'}</a></li>
<li class="menu-item"><a href="$scriptName?MODE=bbl">$viewMenu{'bbl'}</a></li>
</ul>
EOM

    return ($topmenu,$searchmenu,$viewmenu);
}

sub printMessageMenu {
    return if ($session->param('MODE') =~ /(bib|add|category|config)/);
    my $message;

    my $numOfBib = $#$bib + 1;
    my $url = &generateURL;

    $message .= <<EOM;
<p class="right">$numOfBib $msg{'found'} : <a href="$url">$msg{'URL'}</a> 
: <a href="$url;STATIC">HTML</a> 
EOM
    if ($use_RSS) {
        $message .= <<EOM;
: <a href="$url;LIMIT=10;RSS">RSS</a>
EOM
    }
    if ($use_XML) {
        $message .= <<EOM;
: <a href="$url;XML">XML</a>
EOM
    }
    if ($use_latexpdf && $session->param('MODE') eq "latex") {
        $message .= <<EOM;
: <a href="$scriptName?MODE=PDF">PDF</a>
EOM
    }
    
    $message .= "</p>";
    return $message;
}

# 頻出タグを表示するメニュー
sub printTagMenu {
    return if ($session->param('MODE') =~ /(detail|edit|add|bib|category|config)/);
    my @idlist;
    foreach (@$bib) {
	push(@idlist,$_->{'id'});
    }
    my $tags = &getMyTagDB(join(",",@idlist));
    my @tg = split(/,/,$tags);
    my $pm = $session->param('MODE');
    my @taglist;
    my $max = $#tg >= 59 ? 59 : $#tg;

    # タグの重要度に応じてサイズを変える．
    for (my $i=0;$i<=$max;$i+=2) {
	my $size = ($tg[$i+1] / $tg[1]) * 1.3 + 0.5;
	push(@taglist,"<span style=\"font-size: ${size}em;\"><a href=\"$scriptName?T=".uri_escape_utf8($tg[$i])."\">$tg[$i]<sup>($tg[$i+1])</sup></a></span>");
    } 
    $tags = join(" ",@taglist);
       
    my $msg .= <<EOM;
<p>$msg{'frequenttags'} $tags</p>
EOM
return $msg;
}

#=====================================================
# Body 描画 (MODE別)
#=====================================================
sub printBody {
    my $mode = $session->param('MODE') || $session->param('prevMODE') || "list";
    my $lmode = $session->param('LOGIN') || "off";
    $session->clear('LOGIN');

    if ($mode eq "list" || $mode eq "latex" || $mode eq "table" || $mode eq "bbl") {
	$session->param('prevMODE',$mode);
    }

    # EDIT 判定
    if (($session->param('MODE') eq "edit" || 
	 $session->param('MODE') eq "add" || 
	 $session->param('MODE') eq "bib" || 
	 $session->param('MODE') eq "category" ||
	 $session->param('MODE') eq "config" )
	&& $login != 1) {
	&printError('You must login first.');
    }

    my $body;

#### login処理
    if ($lmode eq "on") {
	    $body .= <<EOM;
<p class="login">
<form action="$scriptName" method="POST">
Password: 
<input type="password" name="PASSWD" size="20" />
<input type="submit" value="Login" />
</form>
</p>
EOM

return $body;
    }
####


    if (@$bib == () && !( $mode eq "add" || $mode eq "bib" || $mode eq "category" || $mode eq "config")) {
	$body .= "<p>$msg{'nothingfound'}</p>";
	return $body;
    }

#### begin mode = list
    if ($mode eq "list") {

	my %check;
	my @opt = $cgi->param('OPT');
	my $lang = $cgi->param('LANG') || $session->param('LANG') || "ja";
	if (@opt != ()) {
	    foreach (@opt) {
		$check{$_} = "checked" if ($_);
	    }	
	} else {
	    @opt = ('underline','abbrev','shortvn','jcr','note');
	    foreach (@opt) {
		$check{$_} = $cgi->cookie($_) if (defined($cgi->cookie($_)));
	    }
	}
#	$session->param('OPT',keys(%check));

	if (!defined($cgi->param('SSI')) && !defined($cgi->param('STATIC')) && !defined($cgi->param('FEED'))) {
	    $body .= <<EOM;
<div class="opt">
<!-- <div class="small"><a href="" onclick="if(document.listoption.style.display == 'none') { document.listoption.style.display = 'block'} else {document.listoption.style.display = 'none'} ;return(false);">$msg{'showDisplayOptions'}Toggle</a></div> -->
<form name="listoption" method="POST">
<input type="checkbox" onclick="this.blur();" onchange="document.listoption.submit();" name="OPT" value="abbrev" $check{'abbrev'} id="c5" /><label for="c5">$msg{'showAbbrev'}</label>
<input type="checkbox" onclick="this.blur();" onchange="document.listoption.submit();" name="OPT" value="underline" $check{'underline'} id="c4" /><label for="c4">$msg{'showUL'}</label>
<input type="checkbox" onclick="this.blur();" onchange="document.listoption.submit();" name="OPT" value="shortvn" $check{'shortvn'} id="c1" /><label for="c1">$msg{'showShortVN'}</label>
<input type="checkbox" onclick="this.blur();" onchange="document.listoption.submit();" name="OPT" value="jcr" $check{'jcr'} id="c2" /><label for="c2">$msg{'showJCR'}</label>
<input type="checkbox" onclick="this.blur();" onchange="document.listoption.submit();" name="OPT" value="note" $check{'note'} id="c3" /><label for="c3">$msg{'showNote'}</label>
<input type="hidden"   name="OPT" value="xx" />
</form>
</div>
<br />
EOM
	}

	$body .= <<EOM;
<dl>
EOM

	my $ssp = $session->param_hashref();

        my $prevPtype = -1;
        my $prevYear = -1;
	my $counter = 1;
	my $s = $session->param('SORT') || "t_descend";
	foreach my $abib (@$bib) {
	    # カテゴリヘッダ表示
	    if ($s =~/y_/) {
		if ($$abib{'year'} != $prevYear) {
		    $prevYear = $$abib{'year'};
		    my $py = $prevYear < 9999 ? $prevYear : ($prevYear == 9999 ? $msg{'accepted'} : $msg{'submitted'});
		    $body .= "<dt class=\"yearhead\">$py</dt>";
		    $counter = 1;
		    $prevPtype = -1;
		}
	    }
	    if ($s =~/t_/) {
		if ($$abib{'ptype'} != $prevPtype) {
		    $prevPtype = $$abib{'ptype'};
		    $body .= "<dt>$ptype{$prevPtype}</dt>";
		    $counter = 1;
		} 
	    }
	    $body .= "<dd><a href=\"$scriptName?D=$$abib{'id'}\">\[$counter\]</a> ";
	    # リスト1行生成
	    if  (!defined($cgi->param('SSI')) && !defined($cgi->param('STATIC'))) {
		&createAList(\$body,\%check,$ssp,$abib,"$scriptName?","$scriptName?");
		$body .= "</dd>\n";
	    } else {
		&createAList(\$body,\%check,$ssp,$abib);
		$body .= "</dd>\n";		
	    }	    
	    $counter ++;
	}

	$body .= <<EOM;
</dl>
EOM
#### end mode = list
#### begin mode = bbl
    } elsif ($mode eq "bbl") {
	$body .= <<EOM;
<textarea class="bibent" rows="50" cols="80">
EOM
	foreach my $abib (@$bib) {
	    $body .= &genBib($abib);
	    $body .= "\n";
	}
	$body .= <<EOM;
</textarea>
EOM
#### end mode = bbl
#### begin mode = latex
    } elsif ($mode eq "latex" || $mode eq "PDF") {

	my $texaff = $cgi->param("texaffi") || $cgi->cookie("texaffi") ;
	my $texttl = $cgi->param("textitle") || $cgi->cookie("textitle") ;
	my $texnme = $cgi->param("texname") || $cgi->cookie("texname") ;

	$texaff =~s/[\\\{\}]//g;
	$texttl =~s/[\\\{\}]//g;
	$texnme =~s/[\\\{\}]//g;

	utf8::decode($texaff)  if (!utf8::is_utf8($texaff)) ;
	utf8::decode($texttl)  if (!utf8::is_utf8($texttl)) ;
	utf8::decode($texnme)  if (!utf8::is_utf8($texnme)) ;

	my %check;
	my @opt = $cgi->param('OPT');
	if (@opt != ()) {
	    foreach (@opt) {
		$check{$_} = "checked" if ($_);
	    }	
	} else {
	    @opt = ('underline','abbrev','shortvn','jcr','note');
	    foreach (@opt) {
		$check{$_} = $cgi->cookie($_) if (defined($cgi->cookie($_)));
	    }
#	    $session->param('OPT',keys(%check));
	}

	$texHeader =~s/myName\}\{\}/myName\}\{$texnme\}/;
	$texHeader =~s/myAffiliation\}\{\}/myAffiliation\}\{$texaff\}/;
	$texHeader =~s/myTitle\}\{\}/myTitle\}\{$texttl\}/;

	$body .= <<EOM;
<div class="opt">
<form name="listoption" method="POST">
<input type="checkbox" onclick="this.blur();" onchange="document.listoption.submit();" name="OPT" value="abbrev" $check{'abbrev'} id="c5" \><label for="c5">$msg{'showAbbrev'}</label>
<input type="checkbox" onclick="this.blur();" onchange="document.listoption.submit();" name="OPT" value="underline" $check{'underline'} id="c4" \><label for="c4">$msg{'showUL'}</label>
<input type="checkbox" onclick="this.blur();" onchange="document.listoption.submit();" name="OPT" value="shortvn" $check{'shortvn'} id="c1" \><label for="c1">$msg{'showShortVN'}</label>
<input type="checkbox" onclick="this.blur();" onchange="document.listoption.submit();" name="OPT" value="jcr" $check{'jcr'} id="c2" \><label for="c2">$msg{'showJCR'}</label>
<input type="checkbox" onclick="this.blur();" onchange="document.listoption.submit();" name="OPT" value="note" $check{'note'} id="c3" \><label for="c3">$msg{'showNote'}</label>
<input type="hidden"   name="OPT" value="xx" \>
</form>
</div>
EOM
	$body .= <<EOM;
<div class="opt">
<form name="texparam" method="POST">
$msg{'texnme'}: <input type="text" name="texname" size="20" value="$texnme" \><br />
$msg{'texaff'}: <input type="text" name="texaffi" size="20" value="$texaff" \><br />
$msg{'texttl'}: <input type="text" name="textitle" size="20" value="$texttl" \><br />
<input type="submit" value="$msg{'save'}" />
</form>
</div>
<p>$msg{'latex_exp'}</p>
<textarea rows="40" cols="80">
EOM

	my $tex .= <<EOM;
$texHeader
EOM


	my $ssp = $session->param_hashref();

        my $prevPtype = -1;
        my $prevYear = 0;
        my $counter = 1;
	my $s = $session->param('SORT') || "t_descend";
        if ($s !~ /t_/) {
	    $tex .= "\\begin\{enumerate\}\n";
	}
	my $subsec = "";
	my $yref = "";
	foreach my $abib (@$bib) {
	    # カテゴリヘッダ表示
	    if ($s =~/y_/) {
		if ($$abib{'year'} != $prevYear) {
		    $prevYear = $$abib{'year'};
		    my $py = $prevYear < 9999 ? $prevYear : ($prevYear == 9999 ? $msg{'accepted'} : $msg{'submitted'});
		    $tex .= "\\end{enumerate}\n" unless ($prevPtype < 0);
		    $tex .= "\\section{$py}\n";
		    $counter = 1;
		    $prevPtype = -1;
		}
		$subsec = "sub";
		$yref = $$abib{'year'}."plus";
	    }
	    if ($s =~/t_/) {
		if ($$abib{'ptype'} != $prevPtype) {
		    if ($prevPtype >= 0) {
			$tex .= "\\end\{enumerate\}\n";
		    }
		    $prevPtype = $$abib{'ptype'};
		    $tex .= <<EOM;
\\${subsec}section\{$ptype{$prevPtype}\}
\\label\{sec:$yref$prevPtype\}

\\renewcommand{\\labelenumi}{[\\ref{sec:$yref$prevPtype}.\\arabic{enumi}]}
\\begin{enumerate}
EOM
		    $counter = 1;
		} 
	    }
	    $tex .= "\\item\n";
	    # リスト1行生成
	    &createAList(\$tex,\%check,$ssp,$abib);
	    $tex .= "\n";
	    $counter ++;
	}

	$tex .= <<EOM;
\\end{enumerate}
$texFooter
EOM

        $body .= <<EOM;
$tex
</textarea>
EOM
        if ($use_latexpdf && $mode eq "PDF") {
	    &doLaTeX($tex);
        } 

#### end mode = latex
#### begin mode = table
    } elsif ($mode eq "table") {
	my $lang=$session->param('LANG') || 'ja';

#	$body .= <<EOM;
#<table class="tableview" id="opttable">
#<form action="$scriptName" method="POST">
#EOM
#        my @bbs = @bb_order;
#	unshift(@bbs,"ptype");
#	unshift(@bbs,"style");
#	unshift(@bbs,"id");
#	for (0..$#bbs) {
#	    if ($_ % 6 == 0) {
#		$body .= "<tr>";
#	    }
#	    my $txt = $msg{"Head_".$bbs[$_]};
#	    $body .= <<EOM;
#<td><input type="checkbox" name="TOPT" id="topt$_" value="$bbs[$_]"><label for="topt$_">$txt</label></td>
#EOM
#	    if ($_ % 6 == 5) {
#		$body .= "</tr>";
#	    }
#	} 
#	$body .= <<EOM;
#</form>
#</table>
#<br />
#EOM

	$body .= <<EOM;
<table class="tableview" id="bibtable">
<thead>
<tr>
  <th class="pth"><br /></th>
  <th class="pth">$msg{'Head_author'}</th>
  <th class="pth">$msg{'Head_title'}</th>
  <th class="pth">$msg{'publish'}</th>
  <th class="pth">$msg{'volnum'}</th>
  <th class="pth">$msg{'Head_pages'}</th>
  <th class="pth">$msg{'yearmonth'}</th>
  <th class="pth">$msg{'ifacc'}</th>
  <th class="pth">File</th>
</tr>
</thead>
<tbody>
EOM
        foreach my $abib (@$bib) {
	    $body .= <<EOM;
<tr>
<td class="pth">$ptype{$$abib{'ptype'}}<br></td>
<td class="ptd">
EOM
            my @aa = split(/\s*(?<!\\),\s*/,($lang eq 'en' && $$abib{'author_e'} ne '' ? 
			     $$abib{'author_e'}	: $$abib{'author'})) ;
	    for (0..$#aa) {
		my $enc = uri_escape_utf8($aa[$_]);
		$enc=~s/\"/\%34/g;
		my $htmenc = HTML::Entities::encode($aa[$_]);
		$aa[$_] = "<a title=\"$htmenc\" href=\"$scriptName?A=$enc\">$aa[$_]</a>";
	    }
	    $body .= join(", ",@aa);
	    my $t = $lang eq 'en' && $$abib{'title_e'} ne '' ? $$abib{'title_e'} 
		: $$abib{'title'};
	    &capitalizePaperTitle(\$t,$mode);
	    my $esct = 	HTML::Entities::encode($t);
	    $body .= <<EOM;
<br /></td>
<td class="ptd"><a title="$esct" href="$scriptName?D=$$abib{'id'}">$t</a><br /></td>
EOM

        if ($$abib{'style'} eq "article") {
	    my $j = $lang eq 'en' && $$abib{'journal_e'} ne '' ? 
		$$abib{'journal_e'} : $$abib{'journal'};
	    $body .= "<td class=\"ptd\">$j<br /></td>";
	} elsif ($$abib{'style'} eq "inproceedings") {
	    my $b = $lang eq 'en' && $$abib{'booktitle_e'} ne '' ? 
		$$abib{'booktitle_e'} : $$abib{'booktitle'};
	    $body .= "<td class=\"ptd\">$b<br></td>";
	} elsif ($$abib{'style'} eq "incollection") {
	    my $e = $lang eq 'en' && $$abib{'editor_e'} ne '' ? 
		$$abib{'editor_e'} : $$abib{'editor'};
	    my $b = $lang eq 'en' && $$abib{'booktitle_e'} ne '' ? 
		$$abib{'booktitle_e'} : $$abib{'booktitle'};
	    $body .= "<td class=\"ptd\">$e$msg{'ed'}, $b<br></td>";
	} elsif ($$abib{'style'} =~ /(in)?book|manual/) {
	    my $p = $lang eq 'en' && $$abib{'publisher_e'} ne '' ? 
		$$abib{'publisher_e'} : $$abib{'publisher'};
	    $body .= "<td class=\"ptd\">$p<br></td>";
	} elsif ($$abib{'style'} =~ /thesis/) {
	    $body .= "<td class=\"ptd\">$$abib{'school'}<br></td>";
	} else {
	    $body .= "<td class=\"ptd\"><br></td>";
	}

	    my $vn = $$abib{'volume'};
	    if ($$abib{'number'} ne "") {
		$vn .= "($$abib{'number'})";
	    }

	    my $yy = $$abib{'year'} == 9999 ? $msg{'accepted'}: ($$abib{'year'} == 10000 ? $msg{'submitted'} : $$abib{'year'});    
	    $yy .= "年" if ($lang eq "ja" && $$abib{'year'} < 9999);
	    my $mm = $mlist{"$$abib{'month'},$lang"};
	    my $yymm = $lang eq "ja" ? "$yy$mm" : "$mm $yy";

        $body .= <<EOM;
<td class="ptd">$vn<br></td>
<td class="ptd">$$abib{'pages'}<br></td>
<td class="ptd">$yymm<br></td>
EOM

        if ($$abib{'style'} eq "article") {
	    $body .= "<td class=\"ptd\">$$abib{'impactfactor'}<br></td>";
	} elsif ($$abib{'style'} eq "inproceedings") {
	    $body .= "<td class=\"ptd\">$$abib{'acceptance'}<br></td>";
	} else {
	    $body .= "<td class=\"ptd\"><br></td>";
	}

	my %efiles;
	&getFileListDB($$abib{'id'},\%efiles);
        # file表示
	if (keys(%efiles)) {
	    $body .= "<td class=\"ptd\">";
	    foreach (sort(grep(/,filename/,keys(%efiles)))) {
		my @ff = split(/,/,$_);
		my $desc = $efiles{$_};
		if ($efiles{$ff[0].",file_desc"} ne "") {
		    $desc = $efiles{$ff[0].",file_desc"};
		}
		$body .= <<EOM;
<a title="$desc" href="$scriptName?DOWNLOAD=$ff[0]">$desc</a><br /> 
EOM
	    }
	    $body .= "</td>";
	} else {
	    $body .= <<EOM;
<td class="ptd"><br /></td>
EOM
        }
	$body .= "</tr>";
    }

	$body .= <<EOM;
</tbody>
</table>
<script type="text/javascript" src="lib/prototype.js"></script>
<script type="text/javascript" src="lib/orderbycolumn.js"></script>
<script type="text/javascript">
<!--
new OrderByColumn("bibtable",["string","string","string","string","string","string","string","string"]);
//-->
</script>
EOM
#### end mode = table
#### begin mode = detail
    } elsif ($mode eq "detail") {

	my %ck;
	$ck{'abbrev'} = 'checked';
	$ck{'underline'} = '';
	$ck{'shortvn'} = 'checked';
	$ck{'jcr'} = '';
	$ck{'note'} = '';
	my $ssp = $session->param_hashref();
	my $abib = shift(@{$bib});
	my $line;
	&createAList(\$line,\%ck,$ssp,$abib);
	my $tline;
	&createAList(\$tline,\%ck,$ssp,$abib,'','',1);
	$titleOfSite .= ": $tline";

	my $svn = uri_escape_utf8("http://".$httpServerName);
	my $scn = uri_escape_utf8(&htmlScrub($scriptName));

	$body .= <<EOM;
    <table>
<tr>
<td colspan="2">
<a href="http://twitter.com/share" class="twitter-share-button" data-count="horizontal">Tweet</a><script type="text/javascript" src="http://platform.twitter.com/widgets.js"></script>
<iframe src="http://www.facebook.com/plugins/like.php?app_id=143903329035904&amp;href=$svn$scn%3FD%3D$$abib{'id'}&amp;send=false&amp;layout=button_count&amp;width=50&amp;show_faces=false&amp;action=recommend&amp;colorscheme=light&amp;font&amp;height=21" scrolling="no" frameborder="0" style="border:none; overflow:hidden; width:150px; height:21px;" allowTransparency="true"></iframe>
</td></tr>
<tr>
<td colspan="2">
$line
</td>
</tr>
<tr>
  <td class="fieldHead">ID</td>
  <td class="fieldBody">$$abib{'id'}</td>
</tr>
<tr>
  <td class="fieldHead">$msg{'category'}</td>
  <td class="fieldBody">$ptype{$$abib{'ptype'}}</td>
</tr>
EOM

	my $tags = &getTagListDB($$abib{'id'});
	
		$body .= <<EOM;
<tr>
  <td class="fieldHead">$msg{'tags'}</td>
  <td class="fieldBody">$tags</td>
</tr>
EOM

        foreach (@bb_order) {
	    $body .= &viewEntry($$abib{'style'},$_,$$abib{$_}) ;
        }


	my %efiles;
	&getFileListDB($$abib{'id'},\%efiles);
        # file表示
	if (keys(%efiles)) {
	    foreach (sort(grep(/,filename/,keys(%efiles)))) {
		my @ff = split(/,/,$_);
		my @hide = ($msg{'open'},$msg{'hidden'});

		my $desc = $efiles{$_};
		if ($efiles{$ff[0].",file_desc"} ne "") {
		    $desc = $efiles{$ff[0].",file_desc"};
		}
		
		$body .= <<EOM;
<tr>
  <td class="fieldHead">$msg{'efile'}</td>
  <td class="fieldBody"><a href="$scriptName?DOWNLOAD=$ff[0]">$desc</a> ($efiles{$ff[0].",mimetype"}) $hide[$efiles{$ff[0].",access"}]</td>
</tr>
EOM
	    }
	} else {
	    $body .= <<EOM;
<tr>
  <td class="fieldHead">$msg{'efile'}</td>
  <td class="fieldBody">$msg{'notavailable'}<br /></td>
</tr>
EOM
        }
	    $body .= <<EOM;
<tr>
  <td class="fieldHead">$msg{'Head_bibent'}</td>
  <td class="fieldBody">
  <pre class="bibent">
EOM

        $body .= &genBib($abib); 
	#"<dt>\@$$abib{'style'}\{paper$$abib{'id'},</dt>";
	#foreach (@bb_order) {
	#    my $aline = "<dd>".&createAbibEntry($$abib{'style'},$_,$$abib{$_});
	#    $aline=~s/\n/<\/dd>/g;
	#    $body .= $aline;
	#}
        #$body .= "<dt>\}</dt>";

	$body .= <<EOM;
  </pre>
  </td>
  </tr>
</table>
EOM
#### end mode = detail
#### begin mode = edit
    } elsif ($mode eq "edit") {

	my $abib = shift(@{$bib});
	$body .= <<EOM;
<form name="edit" enctype="multipart/form-data" method="POST" action="$scriptName">
<input type="hidden" name="MODE" value="edit2">
<input type="hidden" name="edit_style" value="$$abib{'style'}">
<table>
<tr>
  <td width="20%" class="fieldHead">$msg{'category'}</td>
  <td width="80%" class="fieldBody">
EOM
        my $pt = $$abib{'ptype'};
#	$body .= $cgi->popup_menu(-name=>'edit_ptype',
#				  -values=>[@ptype_order],
#				  -default=>"$pt",
#				  -labels=>\%ptype);
	$body .= <<EOM;
<select class="longinput" name="edit_ptype">
EOM
        foreach (@ptype_order) {
	    my $selected = '';
	    $selected = "selected" if ($pt eq $_);
	    $body .= <<EOM;
<option value="$_" $selected>$ptype{$_}</option>
EOM
        }

        $body .= <<EOM;
      </select>
EOM
	$body .= <<EOM;
  </td>
</tr>
EOM
	my $tags = &getTagListDB($$abib{'id'});
	if ($tags eq "") {
	    $tags = &createTags($$abib{'title'},$$abib{'title_e'});
	}
	$body .= <<EOM;
<tr>
  <td class="fieldHead_O">$msg{'tags'}</td>
  <td class="fieldBody">
  <input name="edit_tags" type="text" size="80" value="$tags" /><br />
EOM
	my $tlist = &getTop10TagDB;
	my @tl; my $x=0;
	foreach (split(/,/,$tlist)) {
	    push(@tl,$_) if ($x % 2 == 0);
	    $x++;
	}
	$body .= $cgi->popup_menu(-name=>'tagpop',
				  -values=>["",sort(@tl)],
				  -onChange=>'var taglist=edit.edit_tags.value.split(" "); taglist.push(edit.tagpop.options[edit.tagpop.selectedIndex].value); edit.edit_tags.value = taglist.join(" ");',
				  -default=>""
	);

	$body .= <<EOM;
  </td>
</tr>
EOM
        foreach (@bb_order) {
	    # author, key, author_eだったら，authors_hashを使って第3引数を構成．
	    my $vl;
	    if ($_ eq "author") {
		my @as = @{$authors_hash{"$$abib{'id'}"}->{'author_name'}};
		$vl = join(",",@as);
	    } elsif ($_ eq "key" || $_ eq "author_e" ) {
		my @ks = @{$authors_hash{"$$abib{'id'}"}->{'author_key'}};
		$vl = join(",",@ks);
	    } else {
		$vl = $$abib{$_};
	    }	    
	    $body .= &editEntry($$abib{'style'},$_,$vl) ;
        }


#ファイルのリストを作成
		$body .= <<EOM;
<tr>
  <td class="fieldHead">$msg{'efile'}</td>
  <td class="fieldBody">
  <table>
EOM
	my %efiles;
	&getFileListDB($$abib{'id'},\%efiles);
        # file表示
	if (keys(%efiles)) {
	    foreach (sort(grep(/,filename/,keys(%efiles)))) {
		my @ff = split(/,/,$_);
		my @chk = ("","checked");
		my $desc = $efiles{$ff[0].",file_desc"};

		$body .= <<EOM;
<tr>
  <td><a href="$scriptName?MODE=filedelete;ID=$$abib{'id'};FID=$ff[0]" onClick="if( !confirm(\'$msg{'fileDeleteConfirm'}\')) {return false;}">[$msg{'filedelete'}]</a> $efiles{$_} ($efiles{$ff[0].",mimetype"}) </td>
  <td>$msg{'filedesc'}:<input type="text" name="files_desc_$ff[0]" value="$desc" /></td>
  <td><input type="checkbox" name="files_faccess" value="$ff[0]" id="chk$ff[0]" $chk[$efiles{$ff[0].",access"}]/><label for="chk$ff[0]">$msg{'faccess'}</label></td>
</tr>
EOM
	    }
	}

#ファイルアップロードフォーム
	$body .= <<EOM;
<tr>
<td>
$msg{'uploadfile'}: <input name="edit_upfile" type="file" />
</td>
<td>
$msg{'filedesc'}:<input type="text" name="files_desc_new" value="desc" />
</td>
<td>
<input type="checkbox" name="files_faccess" value="new" id="chknew" /><label for="chknew">$msg{'faccess'}</label>
</td>
</tr>
</table>
</td></tr>
<tr>
  <td class="fieldHead" colspan="2">
  <input type="submit" value="$msg{'doEdit'}" />
  </td>
</tr>
</table>
</form>
EOM
#### end mode = edit
#### begin mode = add
    } elsif ($mode eq "add") {

	$body .= <<EOM;
<table>
<tr>
  <td width="20%" class="fieldHead">$msg{'Head_style'}</td>
  <td width="80%" class="fieldBody">
  <form name="addst" method="POST" action="$scriptName">
EOM
	my $sty = $session->param('edit_style') || 'article';
	$body .= $cgi->popup_menu(-name=>'edit_style',
				  -values=>[keys(%bt)],
				  -default=>$sty,
				  -onChange=>'document.addst.submit();',
				  -labels=>\%bt);
	$session->param('edit_style',$sty);

	$body .= <<EOM;
	<br clear="all" /> $msg{'Exp_style'}
</form>
</td>
</tr>
<tr>
  <td class="fieldHead">$msg{'category'}</td>
  <td class="fieldBody">
<form name="edit" enctype="multipart/form-data" method="POST" action="$scriptName">
<input type="hidden" name="MODE" value="add2">
EOM
        my $pt = 0;

	$body .= $cgi->popup_menu(-name=>'edit_ptype',
				  -values=>[@ptype_order],
				  -default=>$pt,
				  -labels=>\%ptype);

	$body .= <<EOM;
  </td>
</tr>
EOM
	$body .= <<EOM;
<tr>
  <td class="fieldHead_O">$msg{'tags'}</td>
  <td class="fieldBody">
  <input name="edit_tags" type="text" size="80" value="" /><br />
EOM
	my $tlist = &getTop10TagDB;
	my @tl; my $x=0;
	foreach (split(/,/,$tlist)) {
	    push(@tl,$_) if ($x % 2 == 0);
	    $x++;
	}
	$body .= $cgi->popup_menu(-name=>'tagpop',
				  -values=>["",sort(@tl)],
				  -onChange=>'var taglist=edit.edit_tags.value.split(" "); taglist.push(edit.tagpop.options[edit.tagpop.selectedIndex].value); edit.edit_tags.value = taglist.join(" ");',
				  -default=>""
	);

	$body .= <<EOM;
  </td>
</tr>
EOM

        foreach (@bb_order) {
	    $body .= &editEntry($sty,$_,"") ;
        }

	$body .= <<EOM;
<tr>
  <td class="fieldHead_O">$msg{'efile'}</td>
  <td class="fieldBody">
EOM
	$body .= <<EOM;
<table><tr><td>$msg{'uploadfile'}: <input name="edit_upfile" type="file" /> </td>
<td>$msg{'filedesc'}: <input name="files_desc_new" type="text" /> </td>
<td><input type="checkbox" name="files_faccess" value="new" id="chknew"/><label for="chknew">$msg{'faccess'}</label></td>
</tr></table>
</td>
</tr>
<tr>
  <td class="fieldHead" colspan="2">
  <input type="submit" value="$msg{'doEdit'}" />
  </td>
</tr>
</table>
</form>
EOM
#### end mode = add
#### begin mode = bib
    } elsif ($mode eq "bib") {

	$body .= <<EOM;
<table>
<tr>
  <td class="fieldHead">$msg{'category'}</td>
  <td class="fieldBody">
<form name="edit" enctype="multipart/form-data" method="POST" action="$scriptName">
<input type="hidden" name="MODE" value="bib2">
EOM
        my $pt = 0;

	$body .= $cgi->popup_menu(-name=>'edit_ptype',
				  -values=>[@ptype_order],
				  -default=>$pt,
				  -labels=>\%ptype);

	$body .= <<EOM;
  </td>
</tr>
EOM
	$body .= <<EOM;
<tr>
  <td class="fieldHead_O">$msg{'tags'}</td>
  <td class="fieldBody">
  <input name="edit_tags" type="text" size="80" value="" /><br />
EOM
	my $tlist = &getTop10TagDB;
	my @tl; my $x=0;
	foreach (split(/,/,$tlist)) {
	    push(@tl,$_) if ($x % 2 == 0);
	    $x++;
	}
	$body .= $cgi->popup_menu(-name=>'tagpop',
				  -values=>["",sort(@tl)],
				  -onChange=>'var taglist=edit.edit_tags.value.split(" "); taglist.push(edit.tagpop.options[edit.tagpop.selectedIndex].value); edit.edit_tags.value = taglist.join(" ");',
				  -default=>""
	);

	$body .= <<EOM;
  </td>
</tr>
EOM

######### textareaにてbibを入力
	$body .= <<EOM;
<tr>
  <td class="fieldHead">$msg{'Head_enterbib'}</td>
  <td class="fieldBody">
  $msg{'Exp_enterbib'}
  <textarea name="edit_bibentry" cols="60" rows="20"></textarea>
  </td>
</tr>
EOM
#########

	$body .= <<EOM;
<tr>
  <td class="fieldHead_O">$msg{'efile'}</td>
  <td class="fieldBody">
EOM
	$body .= <<EOM;
<table><tr><td>$msg{'uploadfile'}: <input name="edit_upfile" type="file" /> </td>
<td>$msg{'filedesc'}: <input name="files_desc_new" type="text" /> </td>
<td><input type="checkbox" name="files_faccess" value="new" id="chknew"/><label for="chknew">$msg{'faccess'}</label></td>
</tr></table>
</td>
</tr>
<tr>
  <td class="fieldHead" colspan="2">
  <input type="submit" value="$msg{'doEdit'}" />
  </td>
</tr>
</table>
</form>
EOM
#### end mode = bib
#### begin mode = config
    } elsif ($mode eq "config") { 

	my @st;
	&getStoptagFromDB(\@st);
	my $stoptags = join(" ",@st);
	
	$body .= <<EOM;
<h3>$msg{'adminsetting'}</h3>
<table>
<form method="POST" action="$scriptName">
<input type="hidden" name="MODE" value="config2">
<tr>
  <td class="fieldHead" width="25%">$msg{'set_passwd'}</td>
  <td class="fieldBody" width="60%">$msg{'set_passwd_exp'}</td> 
  <td class="fieldBody" width="15%">
  <input type="password" name="opt_PASSWD"/>
  </td>
</tr>
<tr>
  <td class="fieldHead" width="25%"></td>
  <td class="fieldBody" width="60%"></td> 
  <td class="fieldBody" width="15%">
  <input type="submit" value="$msg{doEdit}"/>
  </td>
</tr>
</form>
</table>

<h3>$msg{'optionsetting'}</h3>
<table>
<form method="POST" action="$scriptName">
<input type="hidden" name="MODE" value="config2">
<tr>
  <td class="fieldHead" width="25%">$msg{'set_titleofsite'}</td>
  <td class="fieldBody" width="60%">$msg{'set_titleofsite_exp'}</td> 
  <td class="fieldBody" width="15%">
  <input type="text" name="opt_titleOfSite" value="$titleOfSite"/>
  </td>
</tr>
EOM

foreach my $tt (grep(/^title\_/,keys(%opts))) {
    my $val;
    eval "\$val = \$$tt;";
    $body .= <<EOM;
<tr>
  <td class="fieldHead" width="25%">$msg{"set_${tt}"}</td>
  <td class="fieldBody" width="60%">$msg{"set_${tt}_exp"}</td> 
  <td class="fieldBody" width="15%">
  <input type="text" name="opt_${tt}" value="$val" />
  </td>
</tr>
EOM
}

	$body .= <<EOM;
<tr>
  <td class="fieldHead" width="25%">$msg{'set_maintainername'}</td>
  <td class="fieldBody" width="60%">$msg{'set_maintainername_exp'}</td> 
  <td class="fieldBody" width="15%">
  <input type="text" name="opt_maintainerName" value="$maintainerName"/>
  </td>
</tr>
<tr>
  <td class="fieldHead" width="25%">$msg{'set_maintaineraddress'}</td>
  <td class="fieldBody" width="60%">$msg{'set_maintaineraddress_exp'}</td> 
  <td class="fieldBody" width="15%">
  <input type="text" name="opt_maintainerAddress" value="$maintainerAddress"/>
  </td>
</tr>
<tr>
  <td class="fieldHead" width="25%">$msg{'tmpl'}</td>
  <td class="fieldBody" width="60%">$msg{'tmpl_exp'}</td> 
  <td class="fieldBody" width="15%">
EOM
	$body .= <<EOM;
<select name="opt_tmpl_name">
EOM
        my @tmpls = ();
        opendir(DIR,$TMPLDIR);
	while(my $dir = readdir(DIR)){
	    next if ($dir=~/^\./); 
	    next if ($dir=~/^CVS/); 
	    next if (! -d $TMPLDIR."/".$dir); 
	    push(@tmpls,$dir);
	}
	closedir(DIR);
        foreach ( @tmpls ) {
	    my $selected = '';
	    $selected = "selected" if ($tmpl_name eq $_);
	    $body .= <<EOM;
<option value="$_" $selected>$_</option>
EOM
        }
        $body .= <<EOM;
      </select>
EOM
	$body .= <<EOM;
  </td>
</tr>
<tr>
  <td class="fieldHead" width="25%">$msg{'use_cache'}</td>
  <td class="fieldBody" width="60%">$msg{'use_cache_exp'}</td> 
  <td class="fieldBody" width="15%">
EOM
#
#        $body .= $cgi->popup_menu(-name=>'opt_use_cache',
#				  -default=>"$use_cache",
#				  -values=>['1','0'],
#				  -labels=>{ '1'=>$msg{'use'},
#					     '0'=>$msg{'dontuse'} }
#	);

	$body .= <<EOM;
<select name="opt_use_cache">
EOM
        my %labels = ('1' => $msg{'use'}, '0'=>$msg{'dontuse'});
        for ( 0 .. 1 ) {
	    my $selected = '';
	    $selected = "selected" if ($use_cache == $_);
	    $body .= <<EOM;
<option value="$_" $selected>$labels{$_}</option>
EOM
        }
        $body .= <<EOM;
      </select>
EOM


	$body .= <<EOM;
  </td>
</tr>
<tr>
  <td class="fieldHead" width="25%">$msg{'use_DBforSession'}</td>
  <td class="fieldBody" width="60%">$msg{'use_DBforSession_exp'}</td> 
  <td class="fieldBody" width="15%">
EOM
#        $body .= $cgi->popup_menu(-name=>'opt_use_DBforSession',
#				  -default=>"$use_DBforSession",
#				  -values=>['1','0'],
#				  -labels=>{ '1'=>$msg{'use'},
#					     '0'=>$msg{'dontuse'} }
#	);
	$body .= <<EOM;
<select name="opt_use_DBforSession">
EOM
        %labels = ('1' => $msg{'use'}, '0'=>$msg{'dontuse'});
        for ( 0 .. 1 ) {
	    my $selected = '';
	    $selected = "selected" if ($use_DBforSession == $_);
	    $body .= <<EOM;
<option value="$_" $selected>$labels{$_}</option>
EOM
        }
        $body .= <<EOM;
      </select>
EOM

	$body .= <<EOM;
  </td>
</tr>
<tr>
  <td class="fieldHead" width="25%">$msg{'use_AutoJapaneseTags'}</td>
  <td class="fieldBody" width="60%">$msg{'use_AutoJapaneseTags_exp'}</td> 
  <td class="fieldBody" width="15%">
EOM
    if (&check_module('Text::MeCab')) {
#        $body .= $cgi->popup_menu(-name=>'opt_use_AutoJapaneseTags',
#				  -default=>"$use_AutoJapaneseTags",
#				  -values=>['1','0'],
#				  -labels=>{ '1'=>$msg{'use'},
#					     '0'=>$msg{'dontuse'} }
#	);

	$body .= <<EOM;
<select name="opt_use_AutoJapaneseTags">
EOM
        %labels = ('1' => $msg{'use'}, '0'=>$msg{'dontuse'});
        for ( 0 .. 1 ) {
	    my $selected = '';
	    $selected = "selected" if ($use_AutoJapaneseTags == $_);
	    $body .= <<EOM;
<option value="$_" $selected>$labels{$_}</option>
EOM
        }
        $body .= <<EOM;
      </select>
EOM

    } else {
        $body .= "$msg{'notInstalled'}: Text::MeCab";
    }
	$body .= <<EOM;
  </td>
</tr>
<tr>
  <td class="fieldHead" width="25%">$msg{'use_RSS'}</td>
  <td class="fieldBody" width="60%">$msg{'use_RSS_exp'}</td> 
  <td class="fieldBody" width="15%">
EOM
    if (&check_module('XML::RSS')) {
#        $body .= $cgi->popup_menu(-name=>'opt_use_RSS',
#				  -default=>"$use_RSS",
#				  -values=>['1','0'],
#				  -labels=>{ '1'=>$msg{'use'},
#					     '0'=>$msg{'dontuse'} }
#	);

	$body .= <<EOM;
<select name="opt_use_RSS">
EOM
        %labels = ('1' => $msg{'use'}, '0'=>$msg{'dontuse'});
        for ( 0 .. 1 ) {
	    my $selected = '';
	    $selected = "selected" if ($use_RSS == $_);
	    $body .= <<EOM;
<option value="$_" $selected>$labels{$_}</option>
EOM
        }
        $body .= <<EOM;
      </select>
EOM

    } else {
        $body .= "$msg{'notInstalled'}: XML::RSS";
    }
	$body .= <<EOM;
  </td>
</tr>
<tr>
  <td class="fieldHead" width="25%">$msg{'use_XML'}</td>
  <td class="fieldBody" width="60%">$msg{'use_XML_exp'}</td> 
  <td class="fieldBody" width="15%">
EOM
    if (&check_module('XML::Simple')) {
#        $body .= $cgi->popup_menu(-name=>'opt_use_XML',
#				  -default=>"$use_XML",
#				  -values=>['1','0'],
#				  -labels=>{ '1'=>$msg{'use'},
#					     '0'=>$msg{'dontuse'} }
#	);
	$body .= <<EOM;
<select name="opt_use_XML">
EOM
        %labels = ('1' => $msg{'use'}, '0'=>$msg{'dontuse'});
        for ( 0 .. 1 ) {
	    my $selected = '';
	    $selected = "selected" if ($use_XML == $_);
	    $body .= <<EOM;
<option value="$_" $selected>$labels{$_}</option>
EOM
        }
        $body .= <<EOM;
      </select>
EOM
    } else {
        $body .= "$msg{'notInstalled'}: XML::Simple";
    }
	$body .= <<EOM;
  </td>
</tr>
<tr>
  <td class="fieldHead" width="25%">$msg{'use_imgtex'}</td>
  <td class="fieldBody" width="60%">$msg{'use_imgtex_exp'}</td> 
  <td class="fieldBody" width="15%">
EOM
    if (-f $IMGTEXPATH && -x $IMGTEXPATH) {
#        $body .= $cgi->popup_menu(-name=>'opt_use_mimetex',
#				  -default=>"$use_mimetex",
#				  -values=>['1','0'],
#				  -labels=>{ '1'=>$msg{'use'},
#					     '0'=>$msg{'dontuse'} }
#	);
	$body .= <<EOM;
<select name="opt_use_imgtex">
EOM
        %labels = ('1' => $msg{'use'}, '0'=>$msg{'dontuse'});
        for ( 0 .. 1 ) {
	    my $selected = '';
	    $selected = "selected" if ($use_imgtex == $_);
	    $body .= <<EOM;
<option value="$_" $selected>$labels{$_}</option>
EOM
        }
        $body .= <<EOM;
      </select>
EOM
    } else {
        $body .= "$msg{'notInstalled'}: $IMGTEXPATH";
    }
	$body .= <<EOM;
  </td>
</tr>
<tr>
  <td class="fieldHead" width="25%">$msg{'use_mimetex'}</td>
  <td class="fieldBody" width="60%">$msg{'use_mimetex_exp'}</td> 
  <td class="fieldBody" width="15%">
EOM
    if (-f $MIMETEXPATH && -x $MIMETEXPATH) {
#        $body .= $cgi->popup_menu(-name=>'opt_use_mimetex',
#				  -default=>"$use_mimetex",
#				  -values=>['1','0'],
#				  -labels=>{ '1'=>$msg{'use'},
#					     '0'=>$msg{'dontuse'} }
#	);
	$body .= <<EOM;
<select name="opt_use_mimetex">
EOM
        %labels = ('1' => $msg{'use'}, '0'=>$msg{'dontuse'});
        for ( 0 .. 1 ) {
	    my $selected = '';
	    $selected = "selected" if ($use_mimetex == $_);
	    $body .= <<EOM;
<option value="$_" $selected>$labels{$_}</option>
EOM
        }
        $body .= <<EOM;
      </select>
EOM
    } else {
        $body .= "$msg{'notInstalled'}: $MIMETEXPATH";
    }
	$body .= <<EOM;
  </td>
</tr>
<tr>
  <td class="fieldHead" width="25%"></td>
  <td class="fieldBody" width="60%"></td> 
  <td class="fieldBody" width="15%">
  <input type="submit" value="$msg{doEdit}"/>
  </td>
</tr>
</form>
</table>

<h3>$msg{'texsetting'}</h3>
<table>
<form method="POST" action="$scriptName">
<input type="hidden" name="MODE" value="config2">
<tr>
  <td class="fieldHead" width="25%">$msg{'set_texHeader'}</td>
  <td class="fieldBody" width="75%">$msg{'set_texHeader_exp'}</td> 
</tr>
<tr>
  <td class="fieldBody" width="100%" colspan="2">
  <textarea rows="20" cols="80" name="opt_texHeader">$texHeader</textarea>
  </td>
</tr>
<tr>
  <td class="fieldHead" width="25%">$msg{'set_texFooter'}</td>
  <td class="fieldBody" width="75%">$msg{'set_texFooter_exp'}</td> 
</tr>
<tr>
  <td class="fieldBody" width="100%" colspan="2">
  <textarea rows="5" cols="80" name="opt_texFooter">$texFooter</textarea>
  </td>
</tr>
</table>
<table>
<tr>
  <td class="fieldHead" width="25%">$msg{'use_latexpdf'}</td>
  <td class="fieldBody" width="60%">$msg{'use_latexpdf_exp'}</td> 
  <td class="fieldBody" width="15%">
EOM
#        $body .= $cgi->popup_menu(-name=>'opt_use_latexpdf',
#				  -default=>"$use_latexpdf",
#				  -values=>['1','0'],
#				  -labels=>{ '1'=>$msg{'use'},
#					     '0'=>$msg{'dontuse'} }
#	);
	$body .= <<EOM;
<select name="opt_use_latexpdf">
EOM
        %labels = ('1' => $msg{'use'}, '0'=>$msg{'dontuse'});
        for ( 0 .. 1 ) {
	    my $selected = '';
	    $selected = "selected" if ($use_latexpdf == $_);
	    $body .= <<EOM;
<option value="$_" $selected>$labels{$_}</option>
EOM
        }
        $body .= <<EOM;
      </select>
EOM
	$body .= <<EOM;
  </td>
</tr>
<tr>
  <td class="fieldHead" width="25%">$msg{'set_latexcmd'}</td>
  <td class="fieldBody" width="60%">$msg{'set_latexcmd_exp'}</td> 
  <td class="fieldBody" width="15%">
  <input type="text" name="opt_latexcmd" value="$latexcmd"/>
  </td>
</tr>
<tr>
  <td class="fieldHead" width="25%">$msg{'set_dvipdfcmd'}</td>
  <td class="fieldBody" width="60%">$msg{'set_dvipdfcmd_exp'}</td> 
  <td class="fieldBody" width="15%">
  <input type="text" name="opt_dvipdfcmd" value="$dvipdfcmd"/>
  </td>
</tr>
<tr>
  <td class="fieldHead" width="25%"></td>
  <td class="fieldBody" width="60%"></td>
  <td class="fieldBody" width="15%">
  <input type="submit" value="$msg{doEdit}"/>
  </td>
</tr>
</form>
</table>


<h3>$msg{'tagsetting'}</h3>
<table>
<form method="POST" action="$scriptName">
<input type="hidden" name="MODE" value="config2">
<tr>
  <td class="fieldHead" width="25%">
  <input type="hidden" name="tag" value="merge" />
      $msg{'tag_merge'}
  </td>
  <td class="fieldBody" width="60%">
      $msg{'tag_merge_exp'}
  </td> 
  <td class="fieldBody" width="15%">
    <input type="submit" value="$msg{'merge'}" />
  </td>
</tr>
</form>
<form method="POST" action="$scriptName">
<input type="hidden" name="MODE" value="config2">
<tr>
  <td class="fieldHead" width="25%">
  <input type="hidden" name="tag" value="rebuild" />
      $msg{'tag_rebuild'}
  </td>
  <td class="fieldBody" width="60%">
      $msg{'tag_rebuild_exp'}
  </td> 
  <td class="fieldBody" width="15%">
    <input type="submit" value="$msg{'rebuild'}" />
  </td>
</tr>
</form>
<form method="POST" action="$scriptName">
<input type="hidden" name="MODE" value="config2">
<tr>
  <td class="fieldHead" width="25%">
  <input type="hidden" name="tag" value="remove" />
      $msg{'tag_remove'}
  </td>
  <td class="fieldBody" width="60%">
  <input name="opt_rmtag" type="text"/><br />$msg{'tag_remove_exp'}
  </td> 
  <td class="fieldBody" width="15%">
    <input type="checkbox" name="opt_addstoptag" value="add" checked id="ast" /><label for="ast">$msg{'addstoptag'}</label><br />
    <input type="submit" value="$msg{'del'}" />
  </td>
</tr>
</form>
<form method="POST" action="$scriptName">
<input type="hidden" name="MODE" value="config2">
<tr>
  <td class="fieldHead" width="25%">
  <input type="hidden" name="tag" value="stoptag" />
      $msg{'tag_stoptaglist'}
  </td>
  <td class="fieldBody" width="60%">
  <textarea cols="40" rows="5" name="opt_stoptag">$stoptags</textarea>    
  <br />$msg{'tag_stoptaglist_exp'}
  </td> 
  <td class="fieldBody" width="15%">
    <input type="submit" value="$msg{'doEdit'}" />
  </td>
</tr>
</form>
</table>

<h3>$msg{'cachesetting'}</h3>
<table>
<form method="POST" action="$scriptName">
<input type="hidden" name="MODE" value="config2">
<tr>
  <td class="fieldHead" width="25%">
  <input type="hidden" name="cache" value="delete" />
      $msg{'cache_delete'}
  </td>
  <td class="fieldBody" width="60%">
      $msg{'cache_delete_exp'}
  </td> 
  <td class="fieldBody" width="15%">
    <input type="submit" value="$msg{'del'}" />
  </td>
</tr>
</table>
EOM

#### begin mode = category
    } elsif ($mode eq "category") { 

	$body .= <<EOM;
<form method="POST" action="$scriptName">
<input type="hidden" name="MODE" value="category2">
<table>
<tr>
  <td class="fieldHead" width="25%">
  <input type="hidden" name="op" value="add" />
      $msg{'addcat'}
  </td>
  <td class="fieldBody" width="60%">
      $msg{'namenewcat'}
    <input type="text" width="20" name="cat_new" />
  </td> 
  <td class="fieldBody" width="15%">
    <input type="submit" value="$msg{'add'}" />
  </td>
</tr>
</form>
<form method="POST" action="$scriptName">
<input type="hidden" name="MODE" value="category2" />
<tr>
  <td class="fieldHead">
  <input type="hidden" name="op" value="del" />
      $msg{'delcat'}
  </td>
  <td class="fieldBody">
      $msg{'selectdelcat'}<br />
EOM
	$body .= $cgi->popup_menu(-name=>'cat_del',
				  -values=>[@ptype_order],
				  -labels=>\%ptype);

    $body .= <<EOM;
    <br />
    $msg{'selectmovcat'}
    <br />
EOM

	$body .= $cgi->popup_menu(-name=>'cat_mov',
				  -values=>[@ptype_order],
				  -labels=>\%ptype);

    $body .= <<EOM;
  </td> 
  <td class="fieldBody" width="15%">
    <input type="submit" value="$msg{'del'}" />
  </td>
</tr>
</form>
<form method="POST" action="$scriptName">
<input type="hidden" name="MODE" value="category2" />
<tr>
  <td class="fieldHead">
  <input type="hidden" name="op" value="ren" />
  $msg{'rencat'}
  </td>
  <td class="fieldBody">
    $msg{'selectcat'}<br />
EOM

       $body .= $cgi->popup_menu(-name=>'cat_del',
				  -values=>[@ptype_order],
				  -labels=>\%ptype);

    $body .= <<EOM;
    <br />
    $msg{'namenewcat'}
    <br />
    <input type="text" width="20" name="cat_new" />
  </td> 
  <td class="fieldBody" width="15%">
    <input type="submit" value="$msg{'rencat'}" />
  </td>
</tr>
</form>
<!-- change order -->
<form method="POST" action="$scriptName">
<input type="hidden" name="MODE" value="category2" />
<tr>
  <td class="fieldHead">
  <input type="hidden" name="op" value="ord" />
  $msg{'ordcat'}
  </td>
  <td class="fieldBody">
    $msg{'ordercat'}<br />
    <table>
    <tr><td>$msg{'catname'}</td><td>$msg{'order'}</td><td>$msg{'neworder'}</td></tr>
EOM
       my $i=0;
       foreach (@ptype_order) {
	   $body .= <<EOM;
<tr><td>$ptype{$_}</td><td>$i</td><td><input type="text" width="5" name="cat_ord_$_" /></td></tr>
EOM
           $i++;
       }

       $body .= <<EOM;
  </table> 
  <td class="fieldBody" width="15%">
    <input type="submit" value="$msg{'chgord'}" />
  </td>
</tr>
</form>
</table>
EOM

    }
    return $body;
}

sub printHeader {
    my $c = new CGI::Cookie(-name    =>  'SID',
			    -value   =>  $session->id(),
			    -expires =>  '+3h');
    my $head1 = "Set-Cookie: $c\n";
    if ($cgi->param('texname')) {
	$c = new CGI::Cookie(-name    =>  'texname',
			    -value   =>  $cgi->param('texname'),
			    -expires =>  '+300d');
	$head1 .= "Set-Cookie: $c\n";
    }
    if ($cgi->param('textitle')) {
	$c = new CGI::Cookie(-name    =>  'textitle',
			    -value   =>  $cgi->param('textitle'),
			    -expires =>  '+300d');
	$head1 .= "Set-Cookie: $c\n";
    }
    if ($cgi->param('texaffi')) {
	$c = new CGI::Cookie(-name    =>  'texaffi',
			    -value   =>  $cgi->param('texaffi'),
			    -expires =>  '+300d');
	$head1 .= "Set-Cookie: $c\n";
    }

    my @opt = $cgi->param('OPT');
    if (@opt != ()) {
	my @lop = ('underline','abbrev','shortvn','jcr','note');
	foreach my $p (@lop) {
	    if (grep(/^$p$/,@opt)) {
		$c = new CGI::Cookie(-name    =>  $p,
				     -value   =>  "checked",
				     -expires =>  '+300d');
	    } else {
		$c = new CGI::Cookie(-name    =>  $p,
				     -value   =>  "",
				     -expires =>  '-1d');
	    }
	    $head1 .= "Set-Cookie: $c\n";
	}	
    }

    my $head2;

#    my $charset = $session->param('CHARSET') || $defaultEncoding;
	
    $head1 .= $cgi->header(
	-type => 'text/html',
	-charset => 'utf-8'	
	);
	
    my $url = &generateURL;
    $head2 .= <<EOM;
    <META http-equiv="Content-Type" content="text/html; charset=utf-8">
    <script type="text/x-mathjax-config">
	MathJax.Hub.Config({ tex2jax: { inlineMath: [['$','$'], ["\\(","\\)"]] } });
    </script>
    <script type="text/javascript"
        src="http://cdn.mathjax.org/mathjax/latest/MathJax.js?config=TeX-AMS_HTML">
    </script>
    <meta http-equiv="X-UA-Compatible" CONTENT="IE=EmulateIE7" />
EOM
    if ($use_RSS) {
    $head2 .= <<EOM;
    <link rel="alternate" type="application/rss+xml" title="RSS" href="$url;RSS" />
EOM
    }

    return ($head1,$head2);
}

##==========================================================================##
## Please do not modify copyright notice.
##==========================================================================##
sub printFooter {
    my $drawingTime = Time::HiRes::tv_interval($t0);
    my $footer;
    $footer .=<<EOM;
<p class="center">
This site is maintained by <a href="$maintainerAddress">$maintainerName</a>.<br />
<a href="http://se.is.kit.ac.jp/~o-mizuno/pman3.html">PMAN $VERSION</a> - Paper MANagement system / (C) 2002-2010, <a href="http://se.is.kit.ac.jp/~o-mizuno/">Osamu Mizuno</a> / All rights reserved.
<br />
Time to show this page: $drawingTime seconds.
</p>
EOM

    return $footer;

}

sub createAList {
################################[TIME]
    my $tt0 = [Time::HiRes::gettimeofday];
################################[TIME]

    my ($rbody,$chk,$ssp,$ent,$alink,$tlink,$isTitle) = @_;
    my %check = %{$chk};

    my $lang = $ssp->{'LANG'} || "ja";
    my $mode = $ssp->{'MODE'} || "list";
    my $mmode = $ssp->{'MENU'} ;

    # タイトルの処理
    #   英語モードならtitle_e利用だけど，title_eが無ければtitle
    my $t = ($lang eq "en" && $$ent{'title_e'} ne "") ? $$ent{'title_e'} : $$ent{'title'};
    &capitalizePaperTitle(\$t,$mode);


    $t = ($tlink ne "" ? "<a href=\"".$tlink."D=$$ent{'id'}\">$t</a>" : $t);

################################[TIME]
    $tt1 += Time::HiRes::tv_interval($tt0);
    $tt0 = [Time::HiRes::gettimeofday];
################################[TIME]

    # 著者の処理
    my @authors = (); my @keys = ();
    @authors = @{$authors_hash{"$$ent{'id'}"}->{'author_name'}} if (defined $authors_hash{"$$ent{'id'}"}->{'author_name'});
    @keys = @{$authors_hash{"$$ent{'id'}"}->{'author_key'}} if (defined $authors_hash{"$$ent{'id'}"}->{'author_key'});
    my $astr = join(',',@authors);
    my $isJA = &isJapanese($astr) ;
    # keysを使うか，authorを使うか．
    if ($lang eq 'en' && $isJA && @keys) {
	@authors = @keys;
    }


    # 個々の著者について繰り返し (このへん時間かかるだろ〜)
    for (0..$#authors) {
	my $enc = $authors[$_];
	if($keys[$_] =~ /\S/ ){
#	    if ($keys[$_]=~/^(.+)(?<!\\),(.+)$/) {
#		$keys[$_] = "$2 $1";
#	    }
	    $enc = $keys[$_];
	}	#追加(keyがあればそちらで検索) by Manabe
	$enc =~s/(^\s*|\s*$)//;
	$enc = uri_escape_utf8($enc);
	$enc=~s/\"/\%34/g;

	# 下線処理 (始)
	my $ul1 = '';
	my $ul2 = '';
	my $a = $authors[$_];
	my $k = $keys[$_];

	#my $mmode = $cgi->param('MENU') || $session->param('MENU');
	if ($check{'underline'} ne '') {
	    my @al;
	    my @loop = ('');
	    if ($mmode eq 'detail') {
		push(@loop,1);
		push(@loop,2);
		push(@loop,3);
	    }
	    foreach (@loop) {
		my $f = $ssp->{"FROM$_"};
		if ($f eq 'author') {
		    my $s = $ssp->{"SEARCH$_"};
		    push(@al,split(/\s+/,$s));
		}
	    }
	    foreach (@al) {
		my $q = $_;
		$q =~ s/\\/\\\\/g;
		if ($a=~/$q/i || $k =~/$q/i) {
		    if ($mode eq 'list' || $mode eq 'detail') {
			$ul1 = '<U>'; $ul2 = '</U>';
		    } else {
			$ul1 = '\\underline{'; $ul2 = '}';
		    }
		    last;
		}
	    }
	}
	# 下線処理 (終)

	# 略称作成 (始)
	my $isJ = $isJA; #&isJapanese($authors[$_]);
	if ($authors[$_]=~/(?<!\\),/) {
	    my @as = split(/\s*(?<!\\),\s*/,$authors[$_]);
	    if ($#as == 1) { # Last, First -> First Last
		if ($check{'abbrev'}) {
		    if (!$isJ) {
			my @newas;
			foreach (split(/\s+/,$as[1])) { # First内をスペース分割
			    if ($_ !~/^[a-z]+$/) { # vonなどはそのまま
				$_=~s/^(([^a-zA-Z]*)[a-zA-Z]([^a-zA-Z\.]*)).*$/\U$1\./; # 頭文字だけ残す
				if ($2 eq "" && $3 ne "") {
				    $_=~s/[^A-Z\.]+//;
				}
			    }
			    push(@newas,$_);
			}
			$as[1]=join(' ',@newas);
			$authors[$_] = "$as[1] $as[0]";
		    } else { # 日本語は姓のみ残す
			$authors[$_] = "$as[0]";
		    }
		} else {
		    $authors[$_] = "$as[1] $as[0]";
		}

	    } elsif ($#as == 2) { # von Last, Jr., First -> First von Last Jr.
		if ($check{'abbrev'}) {
		    if (!$isJ) {
			my @newas;
			foreach (split(/\s+/,$as[2])) {
			    if ($_ !~/^[a-z]+$/) { # vonなどはそのまま
				$_=~s/^(([^a-zA-Z]*)[a-zA-Z]([^a-zA-Z\.]*)).*$/\U$1\./; # 頭文字だけ残す
				if ($2 eq "" && $3 ne "") {
				    $_=~s/[^A-Z\.]+//;
				}
			    }
			    push(@newas,$_);
			}
			$as[2]=join(' ',@newas);
			$authors[$_] = "$as[2] $as[0] $as[1]";
		    } else { # 日本語の場合 (たぶんない)
			$authors[$_] = "$as[0]";			
		    }
		} else {
		    $authors[$_] = "$as[2] $as[0] $as[1]";
		}
	    }
	} else { # スペース区切りの名前の場合，英語と日本語で扱いが違う
 	    if ($check{'abbrev'}) {
		my @as = split(/\s+/,$authors[$_]);
		my $firstname = $as[0];
		my $lastname = pop(@as);
		if (!$isJ) { # First Last -> Last
		    my @newas;
		    foreach (@as) {
			if ($_ !~/^[a-z]+$/) { # vonなどはそのまま
			    $_=~s/^(([^a-zA-Z]*)[a-zA-Z]([^a-zA-Z\.]*)).*$/\U$1\./; # 頭文字だけ残す
			    if ($2 eq "" && $3 ne "") {
				$_=~s/[^A-Z\.]+//;
			    }
			}
			push(@newas,$_);
		    }
		    $authors[$_] = join(" ",(@newas,$lastname));
		} else { # 姓 名 → 姓
		    $authors[$_] = $firstname;
		}
	    }
	}
	# 略称作成 (終)

	if ($alink ne '') {
	    if ($authors[$_]=~/\\/) {
		$authors[$_]=&latin_LaTeX2html($authors[$_]);
	    }
	    $authors[$_] = "<a href=\"".$alink."A=$enc\">$ul1$authors[$_]$ul2</a>";
	} else {
	    $authors[$_] = "$ul1$authors[$_]$ul2";
	}
    }
    # 個々の著者の処理終わり

################################[TIME]
    $tt2 += Time::HiRes::tv_interval($tt0);
    $tt0 = [Time::HiRes::gettimeofday];
################################[TIME]

    # 著者の並びを生成
    my $strauth = '';
    if ($#authors > 1) { # 著者が3人以上
	my $lastauthor = pop(@authors);
	$strauth = join(', ',@authors);
	# $str に全角文字が含まれているか判定する
	if ($isJA) {
	    $strauth .= ", $lastauthor";
	} else {
	    $strauth .= ", and $lastauthor";
	}
    } else { # 著者が一人か二人
	# $str に全角文字が含まれているか判定する
	if ($isJA) {
	    $strauth = join(', ',@authors);
	} else {
	    $strauth = join(' and ',@authors);
	}
    }

    # 年月処理
    my $yy = $$ent{'year'} == 9999 ? $msg{'accepted'}: ($$ent{'year'} == 10000 ? $msg{'submitted'} : $$ent{'year'});
    $yy .= "年" if ($lang eq 'ja' && $isJA && $$ent{'year'} < 9999);
    my $mm = ($lang eq 'ja' && $isJA) ? $mlist{"$$ent{'month'},ja"} : $mlist{"$$ent{'month'},en"};
    my $yymm = ($lang eq 'ja' && $isJA) ? "$yy$mm" : "$mm $yy";

    # 巻号処理
    my $vvnn = "";
    if ($check{'shortvn'}) {
	if ($mode eq "list" || $mode eq 'detail') {
	    $vvnn = $$ent{'volume'} eq "" ? "": "<b>$$ent{'volume'}</b>";
	} else {
	    $vvnn = $$ent{'volume'} eq "" ? "": "\{\\bf $$ent{'volume'}\}";
	}
	$vvnn .= $$ent{'number'} eq "" ? "": ( $vvnn eq "" ? $$ent{'number'} : "($$ent{'number'})");
    } else {
	$vvnn .= "volume $$ent{'volume'}" if ($$ent{'volume'} ne '');
	$vvnn .= ', ' if ($$ent{'volume'} ne '' && $$ent{'number'} ne '');
	$vvnn .= "number $$ent{'number'}" if ($$ent{'number'} ne '');
    }
    $vvnn .= ',' if ($vvnn ne '');

    # ページ番号処理
    my $pages = 'pages';
    my $page = 'page';
    if ($check{'shortvn'}) {
	$pages = 'pp.'; $page = 'p.';
    }
    my $pp = ($$ent{'pages'} eq "" ? "": 
	      ($$ent{'pages'}=~/^\d+\-+\d+$/ ? "$pages $$ent{'pages'}," :
	       ($$ent{'pages'}=~/^\d+$/ ? "$page $$ent{'pages'}," :
		"$$ent{'pages'},") ) );

    my $edr;
    my $chp;   
    if ($isJA) {
	$edr = ($$ent{'editor'} eq "" ? "": "$$ent{'editor'}(編),");
	$chp = ($$ent{'chapter'} eq "" ? "": "第$$ent{'chapter'}章,");
    } else {
	$edr = ($$ent{'editor'} eq "" ? "In": "In $$ent{'editor'}, editor,");
	$chp = ($$ent{'chapter'} eq "" ? "": "Chapter $$ent{'chapter'},");
    }
    
    my $bkt = ($lang eq "en" && $$ent{'booktitle_e'} ne "") ? "$$ent{'booktitle_e'},":"$$ent{'booktitle'},";
    
    my $pub = ($lang eq "en" && $$ent{'publisher_e'} ne "") ? "$$ent{'publisher_e'},":"$$ent{'publisher'},";
    
################################[TIME]
    $tt3 += Time::HiRes::tv_interval($tt0);
    $tt0 = [Time::HiRes::gettimeofday];
################################[TIME]

# 各文献スタイルに応じた出力生成
    my $aline = "$strauth, ";

    if ($isTitle) {
	$aline .= "$t, $yymm.";
	$$rbody .= $aline;
	return;
    }
    my $jj = ($lang eq "en" && $$ent{'journal_e'} ne "") ? $$ent{'journal_e'} : $$ent{'journal'};

    my $lquot = "``";
    my $rquot = "''";

    $lquot = $rquot = "&#34;" if ($mode eq "list" || $mode eq 'detail');

    if ($$ent{'style'} eq "article") {
	$aline .= "$lquot$t,$rquot $jj, $vvnn $pp $yymm.";
	if ($check{'jcr'} && $$ent{'impactfactor'} ne "") {
	    $aline .= " (JCR: $$ent{'impactfactor'})";
	}
    } elsif ($$ent{'style'} eq "inproceedings") {
	$aline .= "$lquot$t,$rquot $edr $bkt $vvnn $pp $yymm.";
	if ($$ent{'note'} ne "" && $check{'note'}) {
	    $aline .= " ($$ent{'note'})";
	}
	if ($check{'jcr'} && $$ent{'acceptance'} ne "") {
	    $aline .= " (Acceptance rate: $$ent{'acceptance'})";
	}
    } elsif ($$ent{'style'} eq "incollection") {
	$aline .= "$t, $edr $bkt $chp $pp $pub $yy.";
    } elsif ($$ent{'style'} =~ /(in)?book|manual/) {
	$aline .= "$t, $pub $yy.";
    } elsif ($$ent{'style'} eq "phdthesis") {
	my $phdthesis = 'Ph.D. thesis';
	$phdthesis = '博士学位論文' if ($isJA && $lang eq 'ja');
	$aline .= "$lquot$t,$rquot $phdthesis, $$ent{'school'}, $yy.";
    } elsif ($$ent{'style'} eq "masterthesis") {
	my $mathesis = 'Master thesis';
	$mathesis = '修士学位論文' if ($isJA && $lang eq 'ja');
	$aline .= "$lquot$t,$rquot $mathesis, $$ent{'school'}, $yy.";
    } elsif ($$ent{'style'} eq "techreport") {
	my $tp = "$$ent{'type'}," if ($$ent{'type'});
	$aline .= "$lquot$t,$rquot $tp $vvnn $$ent{'institution'}, $yymm.";
    } elsif ($$ent{'style'} eq "misc") {
	my $how = $$ent{'howpublished'};
	$aline .= "$lquot$t,$rquot $how, $yymm.";
    } else {
	my $note = $$ent{'note'};
	$note .= ',' if ($note ne "");
	$aline .= "$t, $note $yy.";
    }

    if ($mode eq 'list' || $mode eq 'detail') {
	if ($$ent{'year'} > 9999) {
	    $aline = "<span class=\"red\">".$aline."</span>";
	}
    }	

    if ($mode eq 'latex'||$mode eq "PDF") {
	$aline=~s/\%/\\\%/g;
	$aline=~s/\_/\\\_/g;
	$aline=~s/\&/\\\&/g;
    } else {
	$aline=~s/\\\s+/ /;
    }

    $$rbody .= $aline;
    
################################[TIME]
    $tt4 += Time::HiRes::tv_interval($tt0);
################################[TIME]
}

sub capitalizePaperTitle {
    my $string = shift; 
    my $mode = shift;
    my $alwaysLower = "A|AN|ABOUT|AMONG|AND|AS|AT|BETWEEN|BOTH|BUT|BY|FOR|FROM|IN|INTO|OF|ON|THE|THUS|TO|UNDER|WITH|WITHIN";

    # 日本語を含んでいたら数式処理のみ
    if (&isJapanese($$string) && ($mode ne "latex" && $mode ne "PDF")) {
	if ($use_mimetex) {
	    $$string=~s/\$([^\$]*)\$/<img class="math" src="${MIMETEXPATH}\?\1" \/>/g;
	} elsif ($use_imgtex) {
	    $$string=~s/\$([^\$]*)\$/<img class="math" src="${IMGTEXPATH}\?{\$\1\$}" \/>/g;
	} else {
	    $$string=~s/\$([^\$]*)\$/\1/g;
	}
	$$string=~s/\{([^\}]*)\}/\1/g;
	return;
    }

    my @words = split(/\s/,$$string);
    for (my $i=0;$i <= $#words;$i++) {

	# $$に囲まれた部分はそのまま
	if ($words[$i]=~/\$([^\$]*)\$/) {
	    next if ($mode eq "latex" || $mode eq "PDF") ; 
 	    if($use_mimetex) {
		$words[$i]=~s/\$([^\$]*)\$/<img class="math" src="${MIMETEXPATH}\?\1" \/>/g;
 	    } elsif($use_imgtex) {
		$words[$i]=~s/\$([^\$]*)\$/<img class="math" src="${IMGTEXPATH}\?{\$\1\$}" \/>/g;
	    } else {
		$words[$i]=~s/\$([^\$]*)\$/\1/g;
	    }
	    next;
	}
	# {}に囲まれた部分はそのまま
	if ($words[$i]=~/\{([^\}]*)\}/) {
	    next if ($mode eq "latex" || $mode eq "PDF") ; 
	    $words[$i]=~s/\{([^\}]*)\}/\1/g;
	    next;
	}

        if (($words[$i]=~/^($alwaysLower)$/i)&&($i>0)) {
	    $words[$i]= lc($words[$i]);
        } else {
            $words[$i]=~ s/(^\w)/\U$1/xg;
	    $words[$i]=~ s/([\w']+)/\u\L$1/g; #'
        }
    }
    $$string = join(" ",@words);
    return;
}

sub genBibEntry {
    my ($st,$fld,$vl) = @_;
    my $isNeed = "I";

    $isNeed = &bibNeededCheck($st,$fld);
    # print each field
    my $aline = "";
    if ($fld eq "author") {
	if ($isNeed ne "I") {
	    if ($vl =~ /\sand\s/) {
		$vl = join(" and ",split(/\s+and\s+/,$vl));
	    } else {
		$vl = join(" and ",split(/(?<!\\),/,$vl));
	    }
	    $vl =~s/\&/\\\&/g;
	    $aline = sprintf("    %10s = {%s},\n",$fld,$vl);
	}
    } elsif ($fld eq "annote" && $vl ne "") {
	$vl =~s/\&/\\\&/g;
	$aline = sprintf("    %10s = {%s},\n",$fld,$vl);
    } elsif ($fld eq "year" && $vl ne "") {
	if ($isNeed ne "I") {
	    my $y = ($vl == 9999 ? "(to appear)": ($vl == 10000 ? "(submitted)":$vl));
	    $aline = sprintf("    %10s = {%s},\n",$fld,$y);
	}
    } elsif ($fld =~ /_e$/) {
    } elsif ($vl ne "") {
	if ($isNeed ne "I") {
	    $vl =~s/\&/\\\&/g;
	    $vl =~s/\%/\\\%/g;
	    $aline = sprintf("    %10s = {%s},\n",$fld,$vl);
	}
    }
    return $aline;
}

sub viewEntry {
    my ($st,$fld,$vl) = @_;
    my $isNeed = "I";

    $isNeed = &bibNeededCheck($st,$fld);
    my $ent;
    # print each field

    if (grep(/^$fld$/,(
		 "address","author","author_e","booktitle","booktitle_e","chapter", 
		 "edition","editor","editor_e","howpublished","institution",
		 "journal","journal_e","month","note","number","organization",
		 "pages","publisher","publisher_e","school","series","type","volume","acceptance","impactfactor" )
	     )
	) {
	if ($isNeed ne "I") {
	    $ent .= <<EOM;
<tr>
  <td class="fieldHead">
  $msg{"Head_$fld"}
  </td>
  <td class="fieldBody">
  $vl<br />
  </td> 
</tr>
EOM
}
    } elsif (grep(/^$fld$/,(
		      "annote","key"  ) 
		  )
	) {
	$ent .= <<EOM;
<tr>
  <td class="fieldHead">
  $msg{"Head_$fld"}
  </td>
  <td class="fieldBody">
  $vl<br />
  </td> 
</tr>
EOM
    } elsif (grep(/^$fld$/,(
		      "abstract" ) 
		  )
	) {
	$vl=~s/\n/<br \/>/ig;
	if ($use_mimetex) {
	    $vl=~s/\$([^\$]*)\$/<img class="math" src="${MIMETEXPATH}\?\1" \/>/g 
	} elsif ($use_imgtex) {
	    $vl=~s/\$([^\$]*)\$/<img class="math" src="${IMGTEXPATH}\?{\$\1\$}" \/>/g 
        } else {
	}
	$ent .= <<EOM;
<tr>
  <td class="fieldHead">
  $msg{"Head_$fld"}
  </td>
  <td class="fieldBody">
  $vl<br />
  </td> 
</tr>
EOM
    } elsif (grep(/^$fld$/,(
		      "url"  ) 
		  )
	) {
	my $vl_ent = HTML::Entities::encode($vl);
	$ent .= <<EOM;
<tr>
  <td class="fieldHead">
  $msg{"Head_$fld"}
  </td>
  <td class="fieldBody">
  <a href="$vl">$vl_ent</a><br />
  </td> 
</tr>
EOM
    } elsif (grep(/^$fld$/,(
		 "title", "title_e" )
	     )
	) {
	if ($isNeed ne "I") {
	    &capitalizePaperTitle(\$vl);
	    $ent .= <<EOM;
<tr>
  <td class="fieldHead">
  $msg{"Head_$fld"}
  </td>
  <td class="fieldBody">
  $vl<br />
  </td> 
</tr>
EOM
}
    } elsif ($fld eq "year") {
	if ($isNeed ne "I") {
	    my $yy = ($vl == 9999 ? "(to appear)" : ($vl == 10000 ? "(submitted)" : $vl));
	$ent .= <<EOM;
<tr>
  <td class="fieldHead">
  $msg{'Head_year'}
  </td>
  <td class="fieldBody">
      $yy<br />
  </td> 
</tr>
EOM
}
    }
}

sub editEntry {
    my ($st,$fld,$vl) = @_;
    my $lang = $session->param('LANG') || 'ja';

    my $isNeed = "I";
    $isNeed = &bibNeededCheck($st,$fld);

    my $ndd = "";
    $ndd = $msg{'need'} if ($isNeed eq "N");
    $ndd = $msg{'altneed'} if ($isNeed eq "A");

    my $ent;
    if (grep(/^$fld$/,(
		 "address","booktitle","booktitle_e","chapter", 
		 "edition","editor","editor_e","howpublished","institution",
		 "note","number","organization",
		 "pages","publisher","publisher_e","school","series","title",
		 "title_e","type","volume","acceptance","impactfactor"
	     ) ) ) {
	if ($isNeed ne "I") {
	    $ent .= <<EOM;
<tr>
  <td class="fieldHead_$isNeed">
  $msg{"Head_$fld"} $ndd
  </td>
  <td class="fieldBody">
  <input name="edit_$fld" type="text" size="80" value="$vl" /><br />
  $msg{"Exp_$fld"}
  </td> 
</tr>
EOM
        }
    } elsif (grep(/^$fld$/,( 
		      "journal","journal_e"
		  ) ) ) {
	if ($isNeed ne "I") {
	$ent .= <<EOM;
<tr>
  <td class="fieldHead_$isNeed">
  $msg{"Head_$fld"} $ndd
  </td>
  <td class="fieldBody">
  <input name="edit_$fld" type="text" size="80" value="$vl" /><br />
EOM
        my %jn;
	foreach (@jname) {
	    $jn{$_} = $_;
	}
	$jn{""} = "----";
	$ent .= $cgi->popup_menu(-name=>"${fld}sel",
				  -values=>["",sort(@jname)],
				  -default=>"",
				  -labels=>\%jn,
				  -onChange=>"edit.edit_${fld}.value = edit.${fld}sel.options[edit.${fld}sel.selectedIndex].value; "
	);

	$ent .= <<EOM;
  <br clear="all" /> $msg{"Exp_$fld"}
  </td> 
</tr>
EOM
	}
    } elsif (grep(/^$fld$/,( 
		      "annote","url" 
		  ) ) ) {
	$ent .= <<EOM;
<tr>
  <td class="fieldHead_$isNeed">
  $msg{"Head_$fld"} $ndd
  </td>
  <td class="fieldBody">
  <input name="edit_$fld" type="text" size="80" value="$vl" /><br />
  $msg{"Exp_$fld"}
  </td> 
</tr>
EOM
    } elsif (grep(/^$fld$/,( 
		      "author"
		  ) ) ) {

	if ($isNeed ne "I") {
	    $vl = HTML::Entities::encode($vl);
	$ent .= <<EOM;
<tr>
  <td class="fieldHead_$isNeed">
  $msg{"Head_$fld"} $ndd
  </td>
  <td class="fieldBody">
  <input name="edit_$fld" type="text" size="80" value="$vl" onchange="author_autoinput()" /><br />
  $msg{"Exp_$fld"}
  </td> 
</tr>
EOM
	}
    } elsif (grep(/^$fld$/,( 
		      "key"
		  ) ) ) {
	    $vl = HTML::Entities::encode($vl);
	$ent .= <<EOM;
<tr>
  <td class="fieldHead_$isNeed">
  $msg{"Head_$fld"} $ndd
  </td>
  <td class="fieldBody">
  <input name="edit_$fld" type="text" size="80" value="$vl" /><br />
  $msg{"Exp_$fld"}
  <input type="button" value="Auto Input" onclick="author_autoinput()" /><br />
  </td> 
</tr>
EOM
    } elsif (grep(/^$fld$/,( 
		      "author_e" 
		  ) ) ) {
	    $vl = HTML::Entities::encode($vl);
	$ent .= <<EOM;
<tr>
  <td class="fieldHead_$isNeed">
  $msg{"Head_$fld"} $ndd
  </td>
  <td class="fieldBody">
  <input name="edit_$fld" type="text" size="80" value="$vl" /><br />
  $msg{"Exp_$fld"}
  <script type="text/javascript">
      var keys = {
EOM
    $ent .= &getAuthorListDB();

	$ent .= <<EOM;
      };
  </script>
  <script type="text/javascript" src="lib/key_autoinput.js"></script>
  <input type="button" value="Auto Input" onclick="author_autoinput()" /><br />
  </td> 
</tr>
EOM
    } elsif (grep(/^$fld$/,( 
		      "abstract"
		  ) ) ) {
	$ent .= <<EOM;
<tr>
  <td class="fieldHead_$isNeed">
  $msg{"Head_$fld"} $ndd
  </td>
  <td class="fieldBody">
<textarea name="edit_$fld" rows="10" cols="80">$vl</textarea>
  $msg{"Exp_$fld"}
  </td> 
</tr>
EOM
    } elsif ($fld eq "month") {
	if ($isNeed ne "I") {
	    $ent .= <<EOM;
<tr>
  <td class="fieldHead_$isNeed">
  $msg{"Head_$fld"} $ndd
  </td>
  <td class="fieldBody">
  <select name="edit_month">
EOM

            for (0..12) {
		if ($vl == $_) {
		    $ent .= <<EOM;
<option value="$_" selected>$mlist{"$_,$lang"}
EOM
                } else {
  	            $ent .= <<EOM;
<option value="$_">$mlist{"$_,$lang"}
EOM
                }
            }
            $ent .= <<EOM;
  </select>
  $msg{'Exp_month'}
  </td> 
</tr>
EOM
        }
    } elsif ($fld eq "year") {
	if ($isNeed ne "I") {
	    $ent .= <<EOM;
<tr>
  <td class="fieldHead_$isNeed">
  $msg{'Head_year'} $ndd
  </td>
  <td class="fieldBody">
  <select name="edit_year">
EOM

            if ($vl == 9999) {
		$ent .= "<option value=\"9999\" selected>$msg{'accepted'}\n";
            } else {
		$ent .= "<option value=\"9999\">$msg{'accepted'}\n";
	    }
	    if ($vl == 10000) {
		$ent .= "<option value=\"10000\" selected>$msg{'submitted'}\n";
	    } else {
		$ent .= "<option value=\"10000\">$msg{'submitted'}\n";
	    }

	    my ($sc, $mn, $hr, $md, $mn, $yr,
		$wd, $yd, $isdst) = localtime(time());

	    $yr +=1903;
	    for (my $i = $yr; $i > 1970; --$i) {
		if ($vl == $i) {
		    $ent .= <<EOM;
<option value="$i" selected>$i
EOM
		} else {
		    $ent .= <<EOM;
<option value="$i">$i
EOM
	        }
	    }
    
	    $ent .= <<EOM;
  </select>
  </td> 
</tr>
EOM
        }
    }
    return $ent;
}

# 必要なbibエントリをチェック
sub bibNeededCheck {
    my ($st,$fld) = @_;
    my $isNeed = "I";

    if ($st eq "article") {
	if (grep(/^$fld$/,('author','title','journal','year'))) {
	    # 必須
	    $isNeed = "N";
	} elsif (grep(/^$fld$/,('author_e','title_e','journal_e','volume','number','pages','month','note','impactfactor'))) {
	    # 任意
	    $isNeed = "O";
	} else {
	    # 無視
	    $isNeed = "I";
	}
    } elsif ($st eq "book") {
	if (grep(/^$fld$/,('title','publisher','year'))) {
	    # 必須
	    $isNeed = "N";
	} elsif (grep(/^$fld$/,('author','editor'))) {
	    # 排他的必須
	    $isNeed = "A";
	} elsif (grep(/^$fld$/,('author_e','title_e','editor_e','publisher_e','volume','series','address','edition','month','note'))) {
	    # 任意
	    $isNeed = "O";
	} else {
	    # 無視
	    $isNeed = "I";
	}
    } elsif ($st eq "booklet") {
	if (grep(/^$fld$/,('title'))) {
	    # 必須
	    $isNeed = "N";
	} elsif (grep(/^$fld$/,('author_e','title_e','author','howpublishd','address','year','month','note'))) {
	    # 任意
	    $isNeed = "O";
	} else {
	    # 無視
	    $isNeed = "I";
	}
    } elsif ($st eq "inbook") {
	if (grep(/^$fld$/,('title','chapter','publisher','year'))) {
	    # 必須
	    $isNeed = "N";
	} elsif (grep(/^$fld$/,('author','editor'))) {
	    # 排他的必須
	    $isNeed = "A";
	} elsif (grep(/^$fld$/,('author_e','title_e','editor_e','publisher_e','volume','series','pages','address','edition','month','note'))) {
	    # 任意
	    $isNeed = "O";
	} else {
	    # 無視
	    $isNeed = "I";
	}
    } elsif ($st eq "incollection") {
	if (grep(/^$fld$/,('author','title','booktitle','publisher','year'))) {
	    # 必須
	    $isNeed = "N";
	} elsif (grep(/^$fld$/,('author_e','title_e','editor_e','booktitle_e','publisher_e','editor','chapter','pages','address','month','note'))) {
	    # 任意
	    $isNeed = "O";
	} else {
	    # 無視
	    $isNeed = "I";
	}
    } elsif ($st eq "inproceedings") {
	if (grep(/^$fld$/,('author','title','booktitle','year'))) {
	    # 必須
	    $isNeed = "N";
	} elsif (grep(/^$fld$/,('author_e','title_e','editor_e','booktitle_e','publisher_e','editor','volume','number','pages','organization','publisher','address','month','note','acceptance'))) {
	    # 任意
	    $isNeed = "O";
	} else {
	    # 無視
	    $isNeed = "I";
	}
    } elsif ($st eq "manual") {
	if (grep(/^$fld$/,('title'))) {
	    # 必須
	    $isNeed = "N";
	} elsif (grep(/^$fld$/,('author','organization','address','edition','year','month','note','author_e','title_e'))) {
	    # 任意
	    $isNeed = "O";
	} else {
	    # 無視
	    $isNeed = "I";
	}
    } elsif ($st eq "masterthesis") {
	if (grep(/^$fld$/,('author','title','school','year'))) {
	    # 必須
	    $isNeed = "N";
	} elsif (grep(/^$fld$/,('author_e','title_e','address','month','note'))) {
	    # 任意
	    $isNeed = "O";
	} else {
	    # 無視
	    $isNeed = "I";
	}
    } elsif ($st eq "phdthesis") {
	if (grep(/^$fld$/,('author','title','school','year'))) {
	    # 必須
	    $isNeed = "N";
	} elsif (grep(/^$fld$/,('author_e','title_e','address','month','note'))) {
	    # 任意
	    $isNeed = "O";
	} else {
	    # 無視
	    $isNeed = "I";
	}
    } elsif ($st eq "misc") {
	if (grep(/^$fld$/,('author_e','title_e','author','title','howpublished','month','year','note'))) {
	    # 任意
	    $isNeed = "O";
	} else {
	    # 無視
	    $isNeed = "I";
	}
    } elsif ($st eq "proceedings") {
	if (grep(/^$fld$/,('title','year'))) {
	    # 必須
	    $isNeed = "N";
	} elsif (grep(/^$fld$/,('title_e','editor_e','publisher_e','editor','publisher','organization','address','month','note'))) {
	    # 任意
	    $isNeed = "O";
	} else {
	    # 無視
	    $isNeed = "I";
	}
    } elsif ($st eq "techreport") {
	if (grep(/^$fld$/,('author','title','institution','year'))) {
	    # 必須
	    $isNeed = "N";
	} elsif (grep(/^$fld$/,('author_e','title_e','type','number','address','month','note'))) {
	    # 任意
	    $isNeed = "O";
	} else {
	    # 無視
	    $isNeed = "I";
	}
    } elsif ($st eq "unpublished") {
	if (grep(/^$fld$/,('author','title','note'))) {
	    # 必須
	    $isNeed = "N";
	} elsif (grep(/^$fld$/,('author_e','title_e','month','year'))) {
	    # 任意
	    $isNeed = "O";
	} else {
	    # 無視
	    $isNeed = "I";
	}
    }

    return $isNeed;
}

# Deleteによるエントリの削除
sub deleteEntry {
    if ($login != 1) {
	&printError('You must login first.');
    }

    my $id = $session->param('ID');
    &deleteDB($id);
    #redirect
    print $cgi->redirect("$scriptName?MODE=list");
 
    &clearSessionParams;
    &expireCacheFromCDB;
    $dbh->disconnect;
    exit(0);
}

# Editによるエントリの登録
sub registEntry {
    if ($login != 1) {
	&printError('You must login first.');
    }
    my $sess_params = $session->param_hashref();
    my %params;
    foreach my $p (grep(/edit_/,keys(%$sess_params))) {
	$$sess_params{$p} = &htmlScrub($$sess_params{$p});
    }

    if (&checkNeededField($sess_params)) {
	&printError($msg{'needederr'});
    }
    my $mode = $session->param('MODE');

    #write DB
    if ($mode =~/edit/) {
	&updateDB($sess_params);
    } elsif ($mode =~/add/) {
	&insertDB($sess_params);
    }

    my $tags = $cgi->param('edit_tags');
    if ($tags eq "") {
	$tags = &createTags($cgi->param('edit_title'),$cgi->param('edit_title_e'));
	if (!utf8::is_utf8($tags)) {
	    utf8::decode($tags);
	}
    }
    &updateTagDB($session->param('ID'),$tags);

    my $key;
    $key = $cgi->param('edit_author_e') || $cgi->param('edit_key');
    my @a;
    if ($cgi->param('edit_author')=~/\s+and\s+/) {
	@a = split(/\s+and\s+/,$cgi->param('edit_author'));
    } else {
	@a = split(/\s*(?<!\\),\s*/,$cgi->param('edit_author'));
    }
    my @k;
    if ($key=~/\s+and\s+/) {
	@k = split(/\s+and\s+/,$key);
    } else {
	@k = split(/\s*(?<!\\),\s*/,$key);
    }
    &deleteAuthorDB($session->param('ID'));
    for (my $i = 0;$i<=$#a;$i++) {
	&registAuthorDB($session->param('ID'),$i,$a[$i],$k[$i]);
    }

    #attachments
    my %efiles;
    my @faccess = $cgi->param('files_faccess');
    &getFileListDB($session->param('ID'),\%efiles);

    if (keys(%efiles)) {
	foreach (sort(grep(/,access/,keys(%efiles)))) {
	    $_=~/^(\d+),/;
	    my $fid = $1;
	    my $access = 0;
	    $access = 1 if (grep(/^$fid$/,@faccess));
	    &changeAccessFileDB($fid,$access);
	}

	foreach (sort(grep(/,file_desc/,keys(%efiles)))) {
	    $_=~/^(\d+),/;
	    my $fid = $1;
	    my $desc = $cgi->param("files_desc_$fid");
	    if ($desc ne "") {
		&changeDescFileDB($fid,$desc);
	    }
	}
    }	    

    my $fname = $cgi->param('edit_upfile');
    print STDERR $fname if $debug;
    if ($fname ne "") {
	my $fh = $cgi->upload('edit_upfile');
	# MIMEタイプ取得
	#my $mimetype = $cgi->uploadInfo($fh)->{'Content-Type'};
	my $refdata = by_suffix($fh);
	my ($mimetype, $encoding) = @$refdata;
	my $file_contents = join('',<$fh>);
	my $filedesc = $cgi->param('files_desc_new');
	if ($file_contents) {
	    print STDERR "Do insertFileDB now!" if $debug;
	    my $a = grep(/new/,@faccess) ? 1 : 0;
	    &insertFileDB($session->param('ID'),$fh,$mimetype,$file_contents,$a,$filedesc);
	}
    }
    $session->clear([grep(/edit_/,keys(%$sess_params))]);
    $session->clear([grep(/files_/,keys(%$sess_params))]);

    &expireCacheFromCDB;
    #redirect
    my $d = $session->param('ID');
    print $cgi->redirect("$scriptName?D=$d");

    $dbh->disconnect;
    exit(0);
}

# BiBからのエントリ登録
sub registEntryByBib {
    if ($login != 1) {
	&printError('You must login first.');
    }
    my $sess_params = $session->param_hashref();
    my %params;
    foreach my $p (grep(/edit_/,keys(%$sess_params))) {
	$$sess_params{$p} = &htmlScrub($$sess_params{$p});
    }

    my $mode = $session->param('MODE');
    my $bibent = $session->param('edit_bibentry');
    $session->clear('edit_bibentry');
    #write DB
    # Create parser object ...
    my $bibh = IO::String->new($bibent);
    my $parser = BibTeX::Parser->new($bibh);

    my $first_id = -1;
    # ... and iterate over entries
    while (my $entry = $parser->next ) {
	if ($entry->parse_ok) {
	    next if ($entry->field('author') eq "");
	    next if ($entry->field('title') eq "");
	    
	    my $pages = $entry->field('pages');
	    $pages =~s/\-\-/\-/g;
	    
	    my @authors = split(/\s+and\s+/,$entry->field('author')); 
	    my @author;
	    eval {
		foreach (@authors) {
		    my ($f,$v,$l,$j) = BibTeX::Parser::Author->split($_);
		    my $a;
		    $a = $f if ($f ne "");
		    $a .= " ".$v if ($v ne "");
		    $a .= " ".$l if ($l ne "");
		    $a .= " ".$j if ($j ne "");
		    push(@author,$a) if ($a);
		} 
	    };
	    my $comma_author = join(",",@author);
	    my @editors = split(/\s+and\s+/,$entry->field('editor')); 
	    my @editor;
	    eval {
		foreach (@editors) {
		    my ($f,$v,$l,$j) = BibTeX::Parser::Author->split($_);
		    my $a;
		    $a = $f if ($f ne "");
		    $a .= " ".$v if ($v ne "");
		    $a .= " ".$l if ($l ne "");
		    $a .= " ".$j if ($j ne "");
		    push(@editor,$a) if ($a);
		} 
	    };
	    next if ($@);
	    my $comma_editor = join(",",@editor);
	    my $url =  $entry->field('url') || $entry->field('doi');
	    my $note = $entry->field('location') || $entry->field('note');
	    my @v = (lc($entry->type), $$sess_params{'edit_ptype'}, $comma_author,
		     $comma_editor, $entry->field('key'), $entry->field('title'),
		     $entry->field('journal'),$entry->field('booktitle'),$entry->field('series'),
		     $entry->field('volume'),$entry->field('number'),$entry->field('chapter'),
		     $pages,$entry->field('edition'),$entry->field('school'),
		     $entry->field('type'),$entry->field('institution'),$entry->field('organization'),
		     $entry->field('publisher'),$entry->field('address'),$entry->field('month'),
		     $entry->field('year'),$entry->field('howpublished'),$note,
		     $entry->field('annote'),$entry->field('abstract'),"",
		     "","","",
		     "","","",
		     "",$url
		);
	    
	    my $sth;
	    eval {
		$sth = $dbh->prepare("INSERT INTO bib VALUES(null,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)");
		$sth->execute(@v);
	    };
	    if ($@) { 
		$dbh->rollback; $dbh->disconnect; 
		&printError("Error: $@");
	    }

	    my $maxid = $dbh->selectrow_array("SELECT MAX(id) FROM bib");
	    $first_id = $maxid if ($first_id == -1);

	    # Tagの登録
	    my $tags = $cgi->param('edit_tags');
	    if ($tags eq "") {
		$tags = &createTags($entry->field('title'),"");
	    } else {
		$tags .= ",".&createTags($entry->field('title'),"");
	    }
	    if (!utf8::is_utf8($tags)) {
		utf8::decode($tags);
	    }
	    &updateTagDB($maxid,$tags);

	    # AuthorsDBへの登録
	    for (my $j=0; $j<=$#author; $j++) {
		my $a = $author[$j];
		eval {
		    $sth = $dbh->prepare("INSERT INTO authors VALUES(null,?,?,?,?)");
		    $sth ->execute($maxid,$j,$a,$a); 
		};
		if ($@) { 
		    $dbh->rollback; $dbh->disconnect; 
		    &printError("Error: $@");
		}
	    }
	} else {
	    # warn "Error parsing file: " . $entry->error;
	}
    }
    $dbh->commit;
	    
    #attachments 1番目の文献にのみ添付する．それ以外には添付しない．
    my %efiles;
    my @faccess = $cgi->param('files_faccess');
    &getFileListDB($first_id,\%efiles);

    if (keys(%efiles)) {
	foreach (sort(grep(/,access/,keys(%efiles)))) {
	    $_=~/^(\d+),/;
	    my $fid = $1;
	    my $access = 0;
	    $access = 1 if (grep(/^$fid$/,@faccess));
	    &changeAccessFileDB($fid,$access);
	}

	foreach (sort(grep(/,file_desc/,keys(%efiles)))) {
	    $_=~/^(\d+),/;
	    my $fid = $1;
	    my $desc = $cgi->param("files_desc_$fid");
	    if ($desc ne "") {
		&changeDescFileDB($fid,$desc);
	    }
	}
    }	    

    my $fname = $cgi->param('edit_upfile');
    print STDERR $fname if $debug;
    if ($fname ne "") {
	my $fh = $cgi->upload('edit_upfile');
	# MIMEタイプ取得
	#my $mimetype = $cgi->uploadInfo($fh)->{'Content-Type'};
	my $refdata = by_suffix($fh);
	my ($mimetype, $encoding) = @$refdata;
	my $file_contents = join('',<$fh>);
	my $filedesc = $cgi->param('files_desc_new');
	if ($file_contents) {
	    print STDERR "Do insertFileDB now!" if $debug;
	    my $a = grep(/new/,@faccess) ? 1 : 0;
	    &insertFileDB($first_id,$fh,$mimetype,$file_contents,$a,$filedesc);
	}
    }
    $session->clear([grep(/edit_/,keys(%$sess_params))]);
    $session->clear([grep(/files_/,keys(%$sess_params))]);

    &expireCacheFromCDB;
    #redirect
    print $cgi->redirect("$scriptName?D=$first_id");
    $dbh->disconnect;
    exit(0);
}


# 必須フィールドをチェック
sub checkNeededField {
    my $sp = shift;
    my $err = 0;

    if ($$sp{'edit_style'} eq "article") {
	if ($$sp{'edit_author'}=~/^\s*$/ || $$sp{'edit_title'}=~/^\s*$/ || $$sp{'edit_journal'}=~/^\s*$/ || $$sp{'edit_year'}=~/^\s*$/ ) {
	    $err = 1;
        }
    } elsif ($$sp{'edit_style'} eq "book") {
	if ($$sp{'edit_title'}=~/^\s*$/ || $$sp{'edit_publisher'}=~/^\s*$/ || $$sp{'edit_year'}=~/^\s*$/ ) {
	    $err = 1;
        }
	if ($$sp{'edit_author'}=~/^\s*$/ && $$sp{'edit_editor'}=~/^\s*$/) {
	    $err = 1;
	}
    } elsif ($$sp{'edit_style'} eq "booklet") {
	if ($$sp{'edit_title'}=~/^\s*$/) {
	    $err = 1;
        }
    } elsif ($$sp{'edit_style'} eq "inbook") {
	if ($$sp{'edit_chapter'}=~/^\s*$/ || $$sp{'edit_title'}=~/^\s*$/ || $$sp{'edit_publisher'}=~/^\s*$/ || $$sp{'edit_year'}=~/^\s*$/ ) {
	    $err = 1;
        }
	if ($$sp{'edit_author'}=~/^\s*$/ && $$sp{'edit_editor'}=~/^\s*$/) {
	    $err = 1;
	}
    } elsif ($$sp{'edit_style'} eq "incollection") {
	if ($$sp{'edit_author'}=~/^\s*$/ || $$sp{'edit_title'}=~/^\s*$/ || $$sp{'edit_booktitle'}=~/^\s*$/|| $$sp{'edit_publisher'}=~/^\s*$/ || $$sp{'edit_year'}=~/^\s*$/ ) {
	    $err = 1;
        }
    } elsif ($$sp{'edit_style'} eq "inproceedings") {
	if ($$sp{'edit_author'}=~/^\s*$/ || $$sp{'edit_title'}=~/^\s*$/ || $$sp{'edit_booktitle'}=~/^\s*$/|| $$sp{'edit_year'}=~/^\s*$/ ) {
	    $err = 1;
        }
    } elsif ($$sp{'edit_style'} eq "manual") {
	if ($$sp{'edit_title'}=~/^\s*$/) {
	    $err = 1;
        }
    } elsif ($$sp{'edit_style'} eq "masterthesis") {
	if ($$sp{'edit_author'}=~/^\s*$/ || $$sp{'edit_title'}=~/^\s*$/ || $$sp{'edit_school'}=~/^\s*$/|| $$sp{'edit_year'}=~/^\s*$/ ) {
	    $err = 1;
        }
    } elsif ($$sp{'edit_style'} eq "phdthesis") {
	if ($$sp{'edit_author'}=~/^\s*$/ || $$sp{'edit_title'}=~/^\s*$/ || $$sp{'edit_school'}=~/^\s*$/|| $$sp{'edit_year'}=~/^\s*$/ ) {
	    $err = 1;
        }
    } elsif ($$sp{'edit_style'} eq "misc") {
	if ($$sp{'edit_author'}=~/^\s*$/ || $$sp{'edit_title'}=~/^\s*$/) {
	    $err = 1;
        }
    } elsif ($$sp{'edit_style'} eq "proceedings") {
	if ($$sp{'edit_year'}=~/^\s*$/ || $$sp{'edit_title'}=~/^\s*$/) {
	    $err = 1;
        }
    } elsif ($$sp{'edit_style'} eq "techreport") {
	if ($$sp{'edit_author'}=~/^\s*$/ || $$sp{'edit_title'}=~/^\s*$/ || $$sp{'edit_institution'}=~/^\s*$/|| $$sp{'edit_year'}=~/^\s*$/ ) {
	    $err = 1;
        }
    } elsif ($$sp{'edit_style'} eq "unpublished") {
	if ($$sp{'edit_author'}=~/^\s*$/ || $$sp{'edit_title'}=~/^\s*$/ || $$sp{'edit_note'}=~/^\s*$/ ) {
	    $err = 1;
        }
    }
    return $err;
}

# LaTeXのオンライン実行
sub doLaTeX {
    my $tex = shift;
    my $sid = $cgi->param('SID') || $cgi->cookie('SID');

    if ($sid eq "") {
	return;
    }

    my $latexfile = $sid.".tex"; 
    my $dvifile = $sid.".dvi"; 
    my $pdffile = $sid.".pdf"; 
    open(LATEX,">".$TMPDIR."/".$latexfile);
    if (utf8::is_utf8($tex)) {
	print LATEX Encode::encode('euc-jp',$tex);
    } else {
	print LATEX Encode::from_to($tex,'utf-8','euc-jp');
    }
    close(LATEX);
    $latexcmd = &shellEsc($latexcmd);
    $dvipdfcmd = &shellEsc($dvipdfcmd);

    my $retval = system("cd $TMPDIR; $latexcmd $latexfile > /dev/null 2>&1");
    if (!$retval) {
	$retval = system("cd $TMPDIR; $latexcmd $latexfile > /dev/null 2>&1");
	if(!$retval) {
	    $retval = system("cd $TMPDIR; $dvipdfcmd $dvifile > /dev/null 2>&1");
	    if (!$retval) {
		open(PDF,$TMPDIR."/".$pdffile);
		my @pdf = <PDF>;
		close(PDF);
		system("cd $TMPDIR; rm -f $sid.* > /dev/null 2>&1");
		&clearSessionParams;
		&printFile('publist.pdf','application/pdf',join('',@pdf));
		# will exit in printFile()
	    } elsif ($retval == 32512) {
		&printError('An error occurred while generating PDF. <br />Please check if your server has "'.$dvipdfcmd.'".');
	    } else {
		&printError('An error occurred while generating PDF with unknown reason.');
	    }
	} else {
	    &printError('An error occurred while typesetting LaTeX.');
	}
    } elsif ($retval == 256) {
	&printError('An error occurred while typesetting LaTeX. <br />Please check LaTeX header and footer carefully if you modified them.');
    } elsif ($retval == 32512) {
	&printError('An error occurred in execution of LaTeX. <br />Please check if your specified LaTeX command is correct or PATH is correct.');
    } else {
	&printError('An error occurred in execution of LaTeX with unknown reason.');
    }

}

sub shellEsc {
  $_ = shift;
  s/([\&\;\`\'\\\"\|\*\?\~\<\>\^\(\)\[\]\{\}\$\n\r])/\\$1/g;
  return $_;
}

# 添付ファイルの表示
sub printFile {
    my ($fname,$mime,$file) = @_;
    print <<EOM;
Content-type: $mime
Content-Transfer-Encoding:binary
Content-Disposition:inline;filename="$fname"

$file
EOM
$dbh->disconnect;
exit(0);
}

# 添付ファイル削除
sub deleteFile {
    if ($login != 1) {
	&printError('You must login first.');
    }

    my $fid = $session->param('FID');
    my $id = $session->param('ID');
    &deleteFileDB($fid);
    #redirect
    print $cgi->redirect("$scriptName?MODE=edit;ID=$id");
 
    &clearSessionParams;
    &expireCacheFromCDB;
    $dbh->disconnect;
    exit(0);
}

# カテゴリ操作
sub modifyCategory {
    if ($login != 1) {
	&printError('You must login first.');
    }

    my $op = $session->param('op');
    if ($op eq "add") {
        &add_categoryDB(&htmlScrub($session->param('cat_new'))) if ($session->param('cat_new') ne "");
    } elsif ( $op eq "del") {
# Delete
	if ($session->param('cat_del') ne "" && $session->param('cat_mov') ne "") {
	    &mov_categoryDB($session->param('cat_del'),$session->param('cat_mov'));
	    &del_categoryDB($session->param('cat_del'));
	}
    } elsif ( $op eq "ren") {
# Rename
	if ($session->param('cat_del') ne "" && $session->param('cat_new') ne "") {
	    &ren_categoryDB($session->param('cat_del'),&htmlScrub($session->param('cat_new')));
	}
    } elsif ( $op eq "ord") {
# Reorder
	my $sess = $session->param_hashref();
	foreach my $o (grep(/^cat_ord_/,keys(%$sess))) {
	    $o=~/^cat_ord_(\d+)$/;
	    my $old=$1;
	    my $new=$$sess{$o};
	    if ($new=~/^\d+$/) {
		if ($new < 10000) {
		} else {
		    &printError('Order value must be smaller than 10000.');
		}
	    } else {
		&printError('Order value must be an integer.');
	    }	    
	}

	foreach my $o (grep(/^cat_ord_/,keys(%$sess))) {
	    $o=~/^cat_ord_(\d+)$/;
	    my $typ=$1;
	    my $new=$sess->{$o};
	    &ord_categoryDB($typ,$new);
#	    &ord_categoryDB2();
	}
    }

    #redirect
    print $cgi->redirect("$scriptName?MODE=category");

    &clearSessionParams;
    &expireCacheFromCDB;
    $dbh->disconnect;    
    exit(0);
}

# オプション設定
sub doConfigSetting {
    if ($login != 1) {
	&printError('You must login first.');
    }

    my $pwd = $cgi->param('opt_PASSWD');
    if ($pwd ne "") {
	&updateOptionsDB('PASSWD',md5_hex($pwd));
	print $cgi->redirect("$scriptName?LOGIN=off");
	&clearSessionParams;
	$dbh->disconnect;    
	exit(0);
    }
    # texHeader, texFooter,
    my @op = ('titleOfSite','maintainerName','maintainerAddress',
	      'use_cache','use_DBforSession','use_AutoJapaneseTags','use_RSS',
	      'use_XML','use_mimetex','use_imgtex','texHeader','texFooter',
	      'use_latexpdf',
	      'latexcmd','dvipdfcmd','tmpl_name',
	      'title_list','title_table','title_latex','title_bbl','title_detail'
	);
    foreach (@op) {
	my $param = $cgi->param('opt_'.$_);
	if ($param ne "") {
	    &updateOptionsDB($_,"$param");
	}
    }
    
    my $tag = $cgi->param('tag');
    if ($tag eq "merge") {
	# (id, title, title_eを全文献について取得)
	&getTitleOnlyDB();
	foreach (@$bib) {
	    my $old_tags = &getTagListDB($_->{id});
	    my $new_tags = &createTags($_->{title},$_->{title_e});
	    my @t = split(/\s/,$old_tags);
	    push(@t,split(/,/,$new_tags));
	    my @tt = uniqArray(\@t);
	    $new_tags = join(",",sort(@tt));
	    if (!utf8::is_utf8($new_tags)) {
		utf8::decode($new_tags);
	    }
	    &updateTagDB( $_->{id}, $new_tags );
	}
	&expireCacheFromCDB;
    } elsif ($tag eq "rebuild") {
	# (id, title, title_eを全文献について取得)
	&getTitleOnlyDB;
	foreach (@$bib) {
	    my $new_tags = &createTags($_->{title},$_->{title_e});
	    my @t; 
	    push(@t,split(/,/,$new_tags));
	    my @tt = uniqArray(\@t);
	    $new_tags = join(",",sort(@tt));
	    if (!utf8::is_utf8($new_tags)) {
		utf8::decode($new_tags);
	    }
	    &updateTagDB( $_->{id}, $new_tags );
	}
	&expireCacheFromCDB;
    } elsif ($tag eq "stoptag") {
	my @st = split(/\s+/,$cgi->param("opt_stoptag"));
	&updateStoptagDB(\@st);
    } elsif ($tag eq "remove") {
	my @st = split(/\s+/,$cgi->param("opt_rmtag"));
	if ($cgi->param("opt_addstoptag") eq "add") {
	    &insertStoptagDB(\@st);
	}
	&deleteTagDB(\@st);
	&expireCacheFromCDB;
    }

    my $cache = $cgi->param('cache');
    if ($cache eq "delete") {
	&expireCacheFromCDB;
    }    
    #redirect
    print $cgi->redirect("$scriptName?MODE=config");
    &clearSessionParams;
    $dbh->disconnect;    
    exit(0);
}

sub updateStoptagDB {
    my $st = shift;
    my $SQL = "DELETE FROM stoptag";
    $dbh->do($SQL);
    $SQL = "INSERT INTO stoptag VALUES(null,?)";
    my $sth = $dbh->prepare($SQL);
    foreach (@$st) {
	$sth->execute(lc($_));
    }
    $dbh->commit;
}

sub insertStoptagDB {
    my $st = shift;
    my $SQL = "INSERT INTO stoptag VALUES(null,?)";
    my $sth = $dbh->prepare($SQL);
    foreach (@$st) {
	$sth->execute(lc($_));
    }
    $dbh->commit;
}

sub getStoptagFromDB {
    my $ret = shift;

    my $except = "A|AN|ABOUT|AMONG|AND|AS|AT|BETWEEN|BOTH|BUT|BY|FOR|FROM|IN|INTO|OF|ON|THE|THUS|TO|UNDER|USING|VS|WITH|WITHIN";
    $except .= "|NEW|BASED|ITS";
    $except .= "|PROC.|PROCEEDINGS|JOURNAL|TRANS.|TRANSACTION|TRANSACTIONS|INTERNATIONAL|CONFERENCE|SYMPOSIUM";
    $except .= "|論文|誌|学会誌|予稿|集|会誌|報告|ジャーナル";

    # stoptagDBの存在確認 なければ 作る
    my $SQL = "SELECT name FROM sqlite_master WHERE type='table'"; 
    my $ref = $dbh->selectall_arrayref($SQL);
    my @dbs;
    foreach (@$ref) {
	push(@dbs,$_->[0]);
    }
    my $sth;
    if (grep(/^stoptag$/,@dbs) == ()) {
	$SQL = "CREATE TABLE stoptag(id integer primary key autoincrement, name text not null)";
	$sth = $dbh->do($SQL);
	if(!$sth){
	    &printError($dbh->errstr);
	}
	$SQL = "INSERT INTO stoptag VALUES(null,?)";
	$sth = $dbh->prepare($SQL);
	foreach (split(/\|/,$except)) {
	    $sth->execute(lc($_));
	}
	$dbh->commit;
    }
    # stoptag取得
    $SQL = "SELECT name FROM stoptag;";
    my $stref = $dbh->selectall_arrayref($SQL);
    foreach my $stag (@$stref) {
	push(@$ret,$$stag[0]);
    }
    return;
}

# 与えられたテキストからタグを抽出
# テキストにはtitleを仮定 
sub createTags {
    my ($title,$title_e) = @_;
    my @t ;
    my @stoptag;
    &getStoptagFromDB(\@stoptag);
    if (&isJapanese($title)) {
	if ($use_AutoJapaneseTags) {
	    if (!utf8::is_utf8($title)) {
		utf8::decode($title);
	    }
	    $title =~s/[{}\$\_\:\'\`\(\)\"]/ /g;
	    require Text::MeCab;
	    my $m = Text::MeCab->new();
	    my $n = $m->parse($title);
	    do {
		my @f = split(/,/,$n->feature);
		utf8::decode($f[0]);
		if ($f[0] eq "名詞") {
		    my $str = $n->surface;
		    if ($str !~ /^[a-zA-Z0-9_\-.,\$\(\)\:\{\}]+$/ ) {
			utf8::decode($str);
			if (grep(/^$str$/i,@stoptag) == ()) {
			    push(@t,$str);
			}
		    }
		}
	    } while ($n = $n->next );
	}
	$title = $title_e;
    }
    # 英語部分
    #use Text::English;
    $title =~s/[\[\]{}\$\_\:\'\`\(\)\\\"]/ /g;
    my @words = split(/\s+/,$title);
    #my @words = Text::English::stem(split(/\s+/,$title));
    foreach my $str (@words) {
	if (grep(/^$str$/i,@stoptag) == () && $str !~ /^-+$/) {
	    push(@t,lc($str));
	}
    }
    return join(",",sort(&uniqArray(\@t)));
}

# あるページのセッション情報をURLの形で表示．
sub generateURL {
    my @p;
    my $mode = $session->param('MODE') || "list";

    push(@p,"MODE=".uri_escape_utf8($mode));
    if ($mode eq "detail") {
	my $id = $session->param('ID');
	push(@p,"ID=".uri_escape_utf8($id));
    } elsif ($mode =~/^(list|table|latex)$/) {
	my $m = $session->param('MENU') || "simple";
	push(@p,"MENU=".uri_escape_utf8($m));
	my $f = $session->param("FROM");
	push(@p,"FROM=".uri_escape_utf8($f));
	my $s = $session->param("SEARCH");
	push(@p,"SEARCH=".uri_escape_utf8($s));
	my $lg = $session->param("LOGIC");
	push(@p,"LOGIC=".uri_escape_utf8($lg));
	if ($m eq "detail") {
	    for (1..3) {
		my $f = $session->param("FROM$_");
		push(@p,"FROM$_=".uri_escape_utf8($f));
		my $s = $session->param("SEARCH$_");
		push(@p,"SEARCH$_=".uri_escape_utf8($s));
		my $lg = $session->param("LOGIC$_");
		push(@p,"LOGIC$_=".uri_escape_utf8($lg));
	    }
	}
    }

    my $st = $session->param('SORT');
    push(@p,"SORT=".uri_escape_utf8($st));

    
    my @pt = ();
    if (ref($session->param('PTYPE')) eq 'ARRAY') {
	@pt = @{$session->param('PTYPE')};
    } else {
	$pt[0] = $session->param('PTYPE') eq "" ? 'all': $session->param('PTYPE');
    }
    foreach (@pt) {
	push(@p,"PTYPE=".uri_escape_utf8($_)) ;
    }

    
    my @opt = ();
    if (ref($session->param('OPT')) eq 'ARRAY') {
	@opt = @{$session->param('OPT')};
    } elsif ($session->param('OPT') ne "") {
	$opt[0] = $session->param('OPT');
    } elsif ($session->param('OPT') eq "") {
	my @optlist = ('underline','abbrev','shortvn','jcr','note');
	foreach (@optlist) {
	    push(@opt,$_) if ($cgi->cookie($_) eq "checked");
	}
    }
    foreach (@opt) {
	push(@p,"OPT=".uri_escape_utf8($_)) if ($_ ne "xx");
    }
    my $l = $session->param('LANG') || 'ja';
    push(@p,"LANG=".uri_escape_utf8($l));

    my $url="$scriptName?".join(";",@p);
    return $url;
}


# 渡されたテキストのHTMLタグを削除して返す．
sub htmlScrub {
    my $html = shift;
    my $scrubber = HTML::Scrubber->new();
    return $scrubber->scrub($html);
}

# 日本語が含まれていれば1
sub isJapanese {
# utf-8での日本語判定ルーチン(下)がうまく動かないので，
# euc-jpへ変換して判定する．こっちのほうが確実と言えば確実．
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
#sub isJapanese {
#    my ($str) = @_;
#    if ($str =~ /(\p{Hiragana}+|\p{Katakana}+|\p{Punctuation}+|\p{Han}+)/) {
#	return 1;
#    } else {
#	return 0;
#    }
#}

sub uniqArray{
    my $array = shift;
    my %hash  = ();

    foreach my $value ( @$array ){
	if (utf8::is_utf8($value)) {
	    utf8::encode($value);
	}
        $hash{$value} = 1;
    }

    return(
        keys %hash
    );
}

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

sub latin_LaTeX2html {
    # see http://www.thesauruslex.com/typo/eng/enghtml.htm
    my $str = shift;

    $str =~ s/\\ss\{?\}?/\&szlig;/g;
    $str =~ s/\\\"\{?\\?([A-Za-z])\}?/\&\1uml;/g;
    $str =~ s/\\\'\{?\\?([A-Za-z])\}?/\&\1acute;/g;
    $str =~ s/\\\`\{?\\?([A-Za-z])\}?/\&\1grave;/g;
    $str =~ s/\\\^\{?\\?([A-Za-z])\}?/\&\1circ;/g;
    $str =~ s/\\\~\{?\\?([A-Za-z])\}?/\&\1tilde;/g;
    $str =~ s/\\\,\{?\\?([A-Za-z])\}?/\&\1tilde;/g;

    $str =~ s/\\c\{?\\?([A-Za-z])\}?/\&\1cedil;/g;
    $str =~ s/\\v\{?C\}?/\&\#268;/g;
    $str =~ s/\\v\{?c\}?/\&\#269;/g;
    $str =~ s/\\v\{?S\}?/\&\#352;/g;
    $str =~ s/\\v\{?s\}?/\&\#353;/g;
    $str =~ s/\\v\{?Z\}?/\&\#381;/g;
    $str =~ s/\\v\{?z\}?/\&\#382;/g;

    # Polish
    $str =~ s/\\L/\&\#321/g;
    $str =~ s/\\l/\&\#322/g;
    $str =~ s/\&Cacute;/\&\#262;/g;
    $str =~ s/\&Nacute;/\&\#323;/g;
    $str =~ s/\&Sacute;/\&\#346;/g;
    $str =~ s/\&Zacute;/\&\#377;/g;

    $str =~ s/\&cacute;/\&\#263;/g;
    $str =~ s/\&nacute;/\&\#324;/g;
    $str =~ s/\&sacute;/\&\#347;/g;
    $str =~ s/\&zacute;/\&\#378;/g;

    return $str;
}

sub genBib {
    my $abib = shift;
    my $bibent = "\@$$abib{'style'}\{id$$abib{'id'},\n";
    foreach (@bb_order) {
	my $aline = &genBibEntry($$abib{'style'},$_,$$abib{$_});
	$bibent .= $aline;
    }
    $bibent .= "}\n";
}

exit(0);
