#!/usr/bin/perl
# $Id: pman3.cgi,v 1.15 2010/02/11 09:32:09 o-mizuno Exp $
# =================================================================================
#                        PMAN 3 - Paper MANagement system
#                               
#              (c) 2002-2009 Osamu Mizuno, All right researved.
# 
our $VERSION = "3.1 Beta 5";
# 
# =================================================================================
use strict;
use utf8;

our $debug=0;

use DBI;
use CGI;
use CGI::Session;
use CGI::Cookie;
use HTML::Template;
use HTML::Scrubber;
use HTML::Entities;
use Encode;
use Digest::MD5 qw/md5_hex/;
use URI::Escape qw/uri_escape_utf8/;
use XML::Simple;
use XML::RSS;
use MIME::Types qw/by_suffix/;

our $PASSWD;
our $titleOfSite;
our $maintainerName;
our $maintainerAddress;
our $texHeader1;
our $texHeader2;
our $texFooter;

require 'config.pl';

our %bt;
our %viewMenu;
our %topMenu;
our %msg;

#=====================================================
# Constants
#=====================================================
our $LIBDIR = "./lib";
our $TMPLDIR = "./tmpl";
our $TMPDIR = "/tmp";
our $DB = "./db/bibdat.db";
our $SESS_DB = "./db/sess.db";
our $CACHE_DB = "./db/cache.db";

#=====================================================
# Options
#=====================================================
our $use_cache = 1;

our $useDBforSession = 0;
our $use_mimetex = 0;

our $MIMETEXPATH = "$LIBDIR/mimetex.cgi";

our $httpServerName = $ENV{'SERVER_NAME'};
our $scriptName = $ENV{'SCRIPT_NAME'};

#=====================================================
# Global Variables
#=====================================================
our $query = ""; 
our $cgi = new CGI;
our $session;
our $login;
our %sbk ; 

our $bib;
our %ptype;
our @jname;
our @ptype_order ;
our @bb_order = ( 'title', 'title_e', 'author', 'author_e', 'editor', 'editor_e', 'key',
		 'journal', 'journal_e', 'booktitle',
		 'booktitle_e', 'series', 'volume', 'number', 'chapter', 'pages',
		 'edition', 'school', 'type', 'institution', 'organization',
		 'publisher', 'publisher_e', 'address', 'month', 'year',
		 'howpublished', 'acceptance', 'impactfactor', 'url', 'note', 'annote',
		 'abstract' );
our %mlist = ("0,en"=>"","0,ja"=>"",
	     "1,en"=>"January","1,ja"=>"1月","2,en"=>"February","2,ja"=>"2月",
	     "3,en"=>"March","3,ja"=>"3月","4,en"=>"April","4,ja"=>"4月",
	     "5,en"=>"May","5,ja"=>"5月","6,en"=>"June","6,ja"=>"6月",
	     "7,en"=>"July","7,ja"=>"7月","8,en"=>"August","8,ja"=>"8月",
	     "9,en"=>"September","9,ja"=>"9月","10,en"=>"October","10,ja"=>"10月",
	     "11,en"=>"November","11,ja"=>"11月","12,en"=>"December","12,ja"=>"12月");

#=====================================================
# Main
#=====================================================

use Time::HiRes qw/gettimeofday tv_interval/;
our $t0 = [Time::HiRes::gettimeofday];

our $dbh = DBI->connect("dbi:SQLite:dbname=$DB", undef, undef, 
		       {AutoCommit => 0, RaiseError => 1 });
$dbh->{unicode} = 1;

&manageSession; 
# キャッシュ読み込み処理の実装部
#   LOGIN状態でない場合のみ．
#   ここでgenerateURLの内容をキーとしてcacheDBを検索．
#   発見したらその内容をprintして終了．
if ($use_cache) {
    my $page = &getCacheFromCDB;
    if ($page) {
	my $dt = Time::HiRes::tv_interval($t0);
	$page =~ s/Time to show this page: [\d\.]+ seconds\./Time to show this page: $dt seconds\. (cached)/;
#	print $page;

	if (utf8::is_utf8($page)) {
	    print encode('utf-8', $page);
	} else {
	    print $page;
	}
	exit 0;
    }
}
$query = &makeQuery;
&getDataDB($query);
&getPtypeDB;
&printScreen;
&clearSessionParams;

$dbh->disconnect;
exit(0);

#=====================================================
# Session 管理
#=====================================================

sub manageSession {
    if (!$useDBforSession) {
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

    # CGIで渡ってきた値をutf-8化
    for my $g ($cgi->param) {
	if ($g ne 'edit_upfile') { # upfileの破壊を防ぐ
	    my @v = map {Encode::decode('utf8',$_)} $cgi->param($g);
	    $cgi->param($g,@v);
	}
    }

    # 短縮パラメータ
    if (defined($cgi->param("D"))) {
	$cgi->param("MODE","detail");
	$cgi->param("ID",$cgi->param("D"));
    }
    if (defined($cgi->param("A"))) {
	$cgi->param("FROM","author");
	$cgi->param("LOGIC","and");
	$cgi->param("SEARCH",$cgi->param("A"));
    }
    if (defined($cgi->param("T"))) {
	$cgi->param("FROM","tag");
	$cgi->param("LOGIC","or");
	$cgi->param("SEARCH",$cgi->param("T"));
    }

    my $sid = $cgi->param('SID') || $cgi->cookie('SID') || undef ;

    if ($sid) {
        $session = new CGI::Session("driver:File", $sid, {Directory=>$TMPDIR})
	    if (!$useDBforSession);
        $session = new CGI::Session("driver:sqlite", $sid, {DataSource=>$SESS_DB}) 
	    if ($useDBforSession);
	
	if (defined($cgi->param('LOGIN')) && $cgi->param('LOGIN') eq "off") {
	    $cgi->delete('PASSWD');
	    $session->clear('PASSWD');
	}

	if ($cgi->param('PASSWD')) {
	    $cgi->param('PASSWD',md5_hex($cgi->param('PASSWD')));
	}
    } else {
        $session = new CGI::Session("driver:File", undef, {Directory=>$TMPDIR})
	    if (!$useDBforSession);
	$session = new CGI::Session("driver:sqlite", undef, {DataSource=>$SESS_DB})
	    if ($useDBforSession);

    }
    $session->expire('+3h');
    my $sp = $session->param_hashref();
#    %sbk = %$sp;
    foreach (keys(%$sp)) {
	$sbk{$_} = $sp->{$_} ;
    }
    $session->save_param($cgi); # OK?


    # 言語設定
    my $l = $session->param('LANG') || "ja";
    require "$LIBDIR/lang.$l.pl";

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
    if (defined($session->param('MODE')) && $session->param('MODE') eq "delete" ) {
	&deleteEntry();
    }
    if (defined($session->param('MODE')) && $session->param('MODE') eq "category2" ) {
	&modifyCategory();
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
    } elsif ($mode eq "add2" || $mode eq "edit2") {
	$session->clear('MODE');
    } elsif ($mode eq "filedelete") {
	$session->clear('MODE');
	$session->clear('FID');
    } elsif ($mode eq "category2") {
	$session->clear('MODE');
	$session->clear('op');
	my $sps = $session->param_hashref();
	$session->clear([grep(/cat_/,keys(%$sps))]);
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
	    return ("WHERE ID=$id AND ptype=pt_type AND pt_lang=$l;");
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
	$order .= "year asc,month asc";
    } elsif ($od eq "descend") {
	$order .= "year desc,month desc";
    } elsif ($od eq "t_ascend") {
	$order .= "pt_order,year asc,month asc";
    } elsif ($od eq "t_descend") {
	$order .= "pt_order,year desc,month desc";
    } elsif ($od eq "y_t_ascend") {
	$order .= "year asc,pt_order,month asc";
    } elsif ($od eq "y_t_descend") {
	$order .= "year desc,pt_order,month desc";
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

	$dbh->commit;	  
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
	    push(@q,"$1=$$sp{$p}") if ($1 ne 'upfile' && $1 ne 'tags');
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

sub insertFileDB {
    my ($fname,$mimetype,$fh,$fa,$desc) = @_;

    my $SQL = "INSERT INTO files VALUES(null,?,?,?,?,?,?)";
    my $sth = $dbh->prepare($SQL);
    eval {
	$sth->execute($session->param('ID'),$fname,$mimetype,$fh,$fa,$desc);
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
#	&printError "Error: $@ $SQL";
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
    my $f = $dbh->selectall_arrayref($SQL,{Columns => {}});
    foreach (@$f) {
	push(@taglist,$_->{'tag'});
    }

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
    my $f = $dbh->selectall_arrayref($SQL,{Columns => {}});
    foreach (@$f) {
	push(@idlist,$_->{'paper_id'});
    }

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
    my $f = $dbh->selectall_arrayref($SQL,{Columns => {}});
    foreach (@$f) {
	push(@tf,$_->{'tag'});
	push(@tf,$_->{'count(tag)'});
    }

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
    my $f = $dbh->selectall_arrayref($SQL,{Columns => {}});
    foreach (@$f) {
	push(@tf,$_->{'tag'});
	push(@tf,$_->{'count(tag)'});
    }

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
	my $emsg = "Incomplete query. While inserting a file.";
	$emsg .= "<br /> $@ <br /> query: $SQL" if ($debug);
	&printError($emsg);
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
    my $f = $dbh->selectall_arrayref($SQL,{Columns => {}});
    foreach (@$f) {
	push(@idlist,$_->{'paper_id'});
    }

    if ($@) { 
	$dbh->rollback; $dbh->disconnect; 
	my $emsg = "Incomplete query. While getting an id list from authors.";
	$emsg .= "<br /> $@ <br /> query: $SQL" if ($debug);
	&printError($emsg);
    }

    return join(",",@idlist);
}

#sub getAuthorFromAuthorsDB {
#    my ($pid,$aulist,$keylist) = @_;
#
#    my $SQL = "SELECT author_name,author_key FROM authors WHERE paper_id=$pid ORDER BY author_order";
#    my $f = $dbh->selectall_arrayref($SQL,{Columns => {}});
#    foreach (@$f) {
#	push(@$aulist,$_->{'author_name'});
#	push(@$keylist,$_->{'author_key'});
#    }
#}

sub getAuthorListDB {
    my @al;
    my $SQL = "SELECT author_name,author_key FROM authors WHERE author_key not null GROUP BY author_name;";
    my $f = $dbh->selectall_arrayref($SQL,{Columns => {}});
    foreach (@$f) {
	$_->{'author_name'}=~s/\s//g if (&isJapanese($_->{'author_name'}));
	push(@al,"\"$_->{'author_name'}\": \"$_->{'author_key'}\"");
    }

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

sub updateAuthorDB {
    my ($a_name,$a_name_e) = @_;

    my $SQL = "UPDATE authors SET author_key=".$dbh->quote($a_name_e)." WHERE author_name=".$dbh->quote($a_name);
    eval {
	my $sth = $dbh->do($SQL);
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
#    my $page = shift;

    # 非ログイン状態に限り
    my $SQL;
    my $cdbh;

    if (!-f $CACHE_DB) { # CACHE_DBが無かったら作る．
	$cdbh = DBI->connect("dbi:SQLite:dbname=$CACHE_DB", undef, undef, 
			     { RaiseError => 1 });
	$SQL = "CREATE TABLE cache(id integer primary key autoincrement, url text not null, page  text);";
	$cdbh->do($SQL);
    } else {
	$cdbh = DBI->connect("dbi:SQLite:dbname=$CACHE_DB", undef, undef, 
			     { RaiseError => 1 });
    }
    $cdbh->{unicode} = 1;

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
 
    my $cdbh = DBI->connect("dbi:SQLite:dbname=$CACHE_DB", undef, undef, 
		       {AutoCommit => 0, RaiseError => 1 });
    $cdbh->{unicode} = 1;
    my $url = &generateURL;
    my $SQL = '';
    eval {
	$SQL = "INSERT INTO cache VALUES(null,?,?)";
	my $sth = $cdbh->prepare($SQL);
	$sth->execute($url,$$h.$$d);
	$cdbh->commit;	  
    };

    if ($@) { 
	$cdbh->rollback; $cdbh->disconnect; 
	my $emsg = "Error while inserting CDB.";
	$emsg .= "<br /> $@ <br /> query: $SQL" if ($debug);
	&printError($emsg);
    }
    return;
}

sub expireCacheFromCDB {
    my $cdbh = DBI->connect("dbi:SQLite:dbname=$CACHE_DB", undef, undef, 
		       {AutoCommit => 0, RaiseError => 1 });
    $cdbh->{unicode} = 1;
    my $SQL = 'DELETE FROM cache;';
    eval {
	$cdbh->do($SQL);
	$cdbh->commit;	  
    };

    if ($@) { 
	$cdbh->rollback; $cdbh->disconnect; 
	my $emsg = "Error while deleting CDB.";
	$emsg .= "<br /> $@ <br /> query: $SQL" if ($debug);
	&printError($emsg);
    }
    return;
}

#=====================================================
# 画面描画 
#=====================================================

sub printScreen {

    my $document;
    my $mode = $session->param('MODE') || $session->param('prevMODE') || "list";

    my $doc;

    my $header; my $htmlh;
    if (defined($cgi->param('STATIC'))) {
	$document = HTML::Template->new(filename => "$TMPLDIR/static.tmpl");
	($header,$htmlh) = &printHeader;    
	$document->param(CHARSET => $htmlh);
	$document->param(MAIN_TITLE => $titleOfSite);
	$document->param(PAGE_TITLE => $msg{"Title_$mode"});
	$document->param(CONTENTS=> &printBody);    
	$document->param(FOOTER=> &printFooter);#

	$doc = $document->output;

    } elsif (defined($cgi->param('SSI'))) {
	$document = HTML::Template->new(filename => "$TMPLDIR/none.tmpl");
	($header,$htmlh) = &printHeader;    
	$document->param(CONTENTS=> &printBody);    
	$doc = $document->output;

    } elsif (defined($cgi->param('XML'))) {
	$header =  $cgi->header(
	    -type => 'text/xml',
	    -charset => 'utf-8'	
	    );
	my $bibhash;
	$bibhash->{'bib'} = [@$bib];

	$doc = XMLout($bibhash,XMLDecl => 1,NoAttr => 1,RootName => 'bibs');

    } elsif (defined($cgi->param('RSS'))) {
	$header =  $cgi->header(
	    -type => 'application/rss+xml',
	    -charset => 'utf-8'	
	    );
	my $rss = XML::RSS->new({version => "2.0" , encode_output => 0});
	my $url = &generateURL;
	$rss->channel(
	    title => "PMAN3 RSS",
	    link => "http://$httpServerName$url",
	    description => "Search result of PMAN3",
	    );
	foreach (@$bib) {
	    my $id = $_->{'id'};
	    my $aline;
	    &createAList(\$aline,$_);
	    $rss->add_item(
		title => "[$ptype{$_->{'ptype'}}] $_->{'title'}",
		link => "http://$httpServerName$scriptName?D=$id",
		description => $aline,
		);
	}
	$doc = $rss->as_string;
    } else {
	$document = HTML::Template->new(filename => "$TMPLDIR/main.tmpl");

	($header,$htmlh) = &printHeader;    
	$document->param(CHARSET => $htmlh);
	
	$document->param(MAIN_TITLE => $titleOfSite);
	$document->param(PAGE_TITLE => $msg{"Title_$mode"});
	
	my ($topm,$searchm,$viewm) = &printMenu;    
	$document->param(TOPMENU => $topm);
	$document->param(SEARCHMENU => $searchm);
	$document->param(VIEWMENU => $viewm);

	$document->param(TAGMENU => &printTagMenu);
	$document->param(MESSAGEMENU => &printMessageMenu);

	$document->param(CONTENTS=> &printBody);    
	$document->param(FOOTER=> &printFooter);
	
	$doc = $document->output;
	if ($use_cache) {
	    # $header と $doc をDBに保存．
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

    my $document = HTML::Template->new(filename => "$TMPLDIR/error.tmpl");
    my $l = $session->param('LANG') || "ja";
    require "$LIBDIR/lang.$l.pl";

    my ($header,$htmlh) = &printHeader;    
    $document->param(CHARSET => $htmlh);

    my ($topm,$searchm,$viewm) = &printMenu;    
    $document->param(TOPMENU => $topm);
    $document->param(VIEWMENU => $viewm);

    $document->param(CONTENTS=> $message);    
    $document->param(FOOTER=> &printFooter);

    my $doc = $document->output;
#    my $cs = $session->param('CHARSET') || $defaultEncoding;
#    Encode::from_to($doc, "euc-jp", $cs);

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

    if (grep(/^$mode$/,('list','table','latex'))) {

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
  <a class="toptab" href="$scriptName?MODE=category">$topMenu{'config'}</a><span class="hide"> | </span>
EOM
    } else {
	$topmenu .= <<EOM;
  <a class="toptab" href="$scriptName?LOGIN=on">$topMenu{'login'}</a><span class="hide"> | </span>
EOM
    }
    $topmenu .= <<EOM;
  Help: <a class="toptab" href="http://www-ise4.ist.osaka-u.ac.jp/~o-mizuno/pman3help.html">$topMenu{'help'}</a><span class="hide"> | </span>
  </p>
EOM

    # 検索メニュー
    my $searchmenu;

    if (grep(/^$mode$/,('list','table','latex'))) {
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

    my $multi = "onChange=\"document.search.submit();\"";
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
    utf8::decode($search);
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
	    utf8::decode($search);
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
<ul class="view">
EOM

    if ($login == 1) {
	my $id = $session->param('ID');
	$viewmenu .= <<EOM;
<li><a href="$scriptName?MODE=add">$viewMenu{'add'}</a></li>
EOM
        if ($mode eq "detail") {
	    $viewmenu .= <<EOM;
<li><a href="$scriptName?MODE=edit;ID=$id">$viewMenu{'edit'}</a></li>
EOM
        }	    

        if ($mode eq "edit") {
	    $viewmenu .= <<EOM;
<li><a href="$scriptName?MODE=delete;ID=$id" onClick="if( !confirm(\'$msg{'deleteConfirm'}\')) {return false;}">$viewMenu{'delete'}</a></li>
EOM
        }	    
	$viewmenu .= "<li><br /></li>";
    }

    $viewmenu .= <<EOM;
<li><a href="$scriptName?MODE=list">$viewMenu{'list'}</a></li>
<li><a href="$scriptName?MODE=table">$viewMenu{'table'}</a></li>
<li><a href="$scriptName?MODE=latex">$viewMenu{'latex'}</a></li>
</ul>
EOM

    return ($topmenu,$searchmenu,$viewmenu);
}

sub printMessageMenu {
    return if ($session->param('MODE') =~ /(add|category)/);
    my $message;

    my $numOfBib = $#$bib + 1;
    my $url = &generateURL;

    $message .= <<EOM;
<p class="right">$numOfBib $msg{'found'} : <a href="$url">$msg{'URL'}</a> : <a href="$url;STATIC">HTML</a> : <a href="$url;LIMIT=10;RSS">RSS</a> </p>
EOM
    return $message;
}

# 頻出タグを表示するメニュー
sub printTagMenu {
    return if ($session->param('MODE') =~ /(detail|edit|add|category)/);
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

    if ($mode eq "list" || $mode eq "latex" || $mode eq "table") {
	$session->param('prevMODE',$mode);
    }

    # EDIT 判定
    if (($session->param('MODE') eq "edit" || 
	 $session->param('MODE') eq "add" || 
	 $session->param('MODE') eq "category")
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

    if (@$bib == () && !( $mode eq "add" || $mode eq "category" )) {
	$body .= "<p>$msg{'nothingfound'}</p>";
	return $body;
    }

#### begin mode = list
    if ($mode eq "list") {

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

	if (!defined($cgi->param('SSI')) && !defined($cgi->param('STATIC')) && !defined($cgi->param('FEED'))) {
	    $body .= <<EOM;
<div class="opt">
<!-- <div class="small"><a href="" onclick="if(document.listoption.style.display == 'none') { document.listoption.style.display = 'block'} else {document.listoption.style.display = 'none'} ;return(false);">$msg{'showDisplayOptions'}Toggle</a></div> -->
<form name="listoption" method="POST">
<input type="checkbox" onclick="this.blur();" onchange="document.listoption.submit();" name="OPT" value="abbrev" $check{'abbrev'} id="c5" \><label for="c5">$msg{'showAbbrev'}</label>
<input type="checkbox" onclick="this.blur();" onchange="document.listoption.submit();" name="OPT" value="underline" $check{'underline'} id="c4" \><label for="c4">$msg{'showUL'}</label>
<input type="checkbox" onclick="this.blur();" onchange="document.listoption.submit();" name="OPT" value="shortvn" $check{'shortvn'} id="c1" \><label for="c1">$msg{'showShortVN'}</label>
<input type="checkbox" onclick="this.blur();" onchange="document.listoption.submit();" name="OPT" value="jcr" $check{'jcr'} id="c2" \><label for="c2">$msg{'showJCR'}</label>
<input type="checkbox" onclick="this.blur();" onchange="document.listoption.submit();" name="OPT" value="note" $check{'note'} id="c3" \><label for="c3">$msg{'showNote'}</label>
<input type="hidden"   name="OPT" value="xx" \>
</form>
</div>
<br />
EOM
	}

	$body .= <<EOM;
<dl>
EOM

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
		&createAList(\$body,$abib,"$scriptName?","$scriptName?")."</dd>\n";
	    } else {
		&createAList(\$body,$abib)."</dd>\n";
		
	    }	    
	    $counter ++;
	}

	$body .= <<EOM;
</dl>
EOM
#### end mode = list
#### begin mode = latex
    } elsif ($mode eq "latex") {

	my $texaff = $cgi->param("texaffi") || $cgi->cookie("texaffi") ;
	my $texttl = $cgi->param("textitle") || $cgi->cookie("textitle") ;
	my $texnme = $cgi->param("texname") || $cgi->cookie("texname") ;

	utf8::decode($texaff);
	utf8::decode($texttl);
	utf8::decode($texnme);

	$body .= <<EOM;
<div class="opt">
<form name="texparam" method="POST">
$msg{'texnme'}: <input type="text" name="texname" size="20" value="$texnme" \>
$msg{'texaff'}: <input type="text" name="texaffi" size="20" value="$texaff" \>
$msg{'texttl'}: <input type="text" name="textitle" size="20" value="$texttl" \>
<input type="submit" value="$msg{'save'}" />
</form>
</div>
EOM

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
<br />
<br />
<textarea rows="40" cols="80">
$texHeader1
\\author{$texaff \\\\ $texttl ~~ $texnme}
$texHeader2
EOM

        my $prevPtype = -1;
        my $counter = 1;
	my $s = $session->param('SORT') || "t_descend";
        if ($s !~ /t_/) {
	    $body .= "\\begin\{enumerate\}\n";
	}
	foreach my $abib (@$bib) {
	    # カテゴリヘッダ表示
	    if ($s =~/t_/) {
		if ($$abib{'ptype'} != $prevPtype) {
		    if ($prevPtype >= 0) {
			$body .= "\\end\{enumerate\}\n";
		    }
		    $prevPtype = $$abib{'ptype'};
		    $body .= <<EOM;
\\section\{$ptype{$prevPtype}\}
\\label\{sec:$prevPtype\}

\\renewcommand{\\labelenumi}{[\\ref{sec:$prevPtype}-\\arabic{enumi}]}
\\begin{enumerate}
EOM
		    $counter = 1;
		} 
	    }
	    $body .= "\\item\n";
	    # リスト1行生成
	    &createAList(\$body,$abib)."\n";
	    $counter ++;
	}

	$body .= <<EOM;
\\end{enumerate}
$texFooter
</textarea>
EOM
#### end mode = latex
#### begin mode = table
    } elsif ($mode eq "table") {
	my $lang=$session->param('LANG') || 'ja';

#	$body .= <<EOM;
#<table class="opttable">
#</table>
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
            my @aa = split(/,/,($lang eq 'en' && $$abib{'author_e'} ne '' ? 
			     $$abib{'author_e'}	: $$abib{'author'})) ;
	    for (0..$#aa) {
		my $enc = uri_escape_utf8($aa[$_]);
		my $htmenc = HTML::Entities::encode($aa[$_]);
		$aa[$_] = "<a title=\"$htmenc\" href=\"$scriptName?A=$enc\">$aa[$_]</a>";
	    }
	    $body .= join(", ",@aa);
	    my $t = $lang eq 'en' && $$abib{'title_e'} ne '' ? $$abib{'title_e'} 
		: $$abib{'title'};
	    &capitalizePaperTitle(\$t);
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

	my $abib = shift(@{$bib});
	$body .= <<EOM;
    <table>
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
  <dl class="bibent">
EOM
        $body .= "<dt>\@$$abib{'style'}\{paper$$abib{'id'},</dt>";

	foreach (@bb_order) {
	    my $aline = "<dd>".&createAbibEntry($$abib{'style'},$_,$$abib{$_});
	    $aline=~s/\n/<\/dd>/g;
	    $body .= $aline;
	}
        $body .= "<dt>\}</dt>";

	$body .= <<EOM;
  </dl>
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
	    $body .= &editEntry($$abib{'style'},$_,$$abib{$_}) ;
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
    if (defined($cgi->param('texname'))) {
	$c = new CGI::Cookie(-name    =>  'texname',
			    -value   =>  $cgi->param('texname'),
			    -expires =>  '+300d');
	$head1 .= "Set-Cookie: $c\n";
    }
    if (defined($cgi->param('textitle'))) {
	$c = new CGI::Cookie(-name    =>  'textitle',
			    -value   =>  $cgi->param('textitle'),
			    -expires =>  '+300d');
	$head1 .= "Set-Cookie: $c\n";
    }
    if (defined($cgi->param('texaffi'))) {
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
    <link rel="alternate" type="application/rss+xml" title="RSS" href="$url;RSS" />
EOM

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
<a href="http://www-ise4.ist.osaka-u.ac.jp/~o-mizuno/pman3.html">PMAN $VERSION</a> - Paper MANagement system / (C) 2002-2010, <a href="http://www-ise4.ist.osaka-u.ac.jp/~o-mizuno/">Osamu Mizuno</a> / All rights reserved.
<br />
Time to show this page: $drawingTime seconds.
</p>
EOM

    return $footer;

}

sub createAList {
    my ($rbody,$ent,$alink,$tlink) = @_;

    my $mode = $cgi->param('MODE') || $session->param('MODE') || 'list';

    my %check;
    my @opt = $cgi->param('OPT');
    if (@opt != ()) {
	foreach (@opt) {
	    $check{$_} = 'checked' if ($_);
	}	
    } else {
	@opt = ('underline','abbrev','shortvn','jcr','note');
	foreach (@opt) {
	    $check{$_} = $cgi->cookie($_) if (defined($cgi->cookie($_)));
	}
#	$session->param('OPT',keys(%check));
    }

    # 英語モード判定
    my $lang = $cgi->param('LANG') || $session->param('LANG') || "ja";

    # タイトルの処理
    #   英語モードならtitle_e利用だけど，title_eが無ければtitle
    my $t = ($lang eq "en" && $$ent{'title_e'} ne "") ? $$ent{'title_e'} : $$ent{'title'};
    &capitalizePaperTitle(\$t);
    $t = ($tlink ne "" ? "<a href=\"".$tlink."D=$$ent{'id'}\">$t</a>" : $t);

    # 著者の処理
    ## DBを使って書き直し． <- これが遅い？？
    # replacement
    my $tmp_a = $lang eq 'en' && $$ent{'author_e'} ne '' ? 
	$$ent{'author_e'}: $$ent{'author'};
    my $tmp_k = $$ent{'key'};

    my @authors; my @keys;
    if ($tmp_a =~/\s+and\s+/) {
	@authors = split(/\s+and\s+/,$tmp_a) ;
    } else {
	@authors = split(/\s*,\s*/,$tmp_a) ;
    }
    if ($tmp_k =~/\s+and\s+/) {
	@keys = split(/\s+and\s+/,$tmp_k) ;
    } else {
	@keys = split(/\s*,\s*/,$tmp_k) ;
    }
    #&getAuthorFromAuthorsDB($$ent{'id'},\@authors,\@keys);

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
	    if ($keys[$_]=~/^(.+),(.+)$/) {
		$keys[$_] = "$2 $1";
	    }
	    $enc = $keys[$_];
	}	#追加(keyがあればそちらで検索) by Manabe
	$enc =~s/(^\s*|\s*$)//;
	$enc = uri_escape_utf8($enc);

	# 下線処理 (始)
	my $ul1 = '';
	my $ul2 = '';
	my $a = $authors[$_];
	my $k = $keys[$_];

	my $mmode = $cgi->param('MENU') || $session->param('MENU');
	if ($check{'underline'} ne '') {
	    my @al;
	    my @loop = ('');
	    if ($mmode eq 'detail') {
		push(@loop,1);
		push(@loop,2);
		push(@loop,3);
	    }
	    foreach (@loop) {
		my $f = $cgi->param("FROM$_") || $session->param("FROM$_");
		if ($f eq 'author') {
		    my $s = $cgi->param("SEARCH$_") || $session->param("SEARCH$_");
		    push(@al,split(/\s+/,$s));
		}
	    }
	    foreach (@al) {
		my $q = $_;
		if ($a=~/$q/i || $k =~/$q/i) {
		    if ($mode eq 'list' ) {
			$ul1 = '<U>'; $ul2 = '</U>';
		    } else {
			$ul1 = '\\underline\{'; $ul2 = '\}';
		    }
		    last;
		}
	    }
	}
	# 下線処理 (終)

	# 略称作成 (始)
	my $isJ = &isJapanese($authors[$_]);
	if ($authors[$_]=~/,/) {
	    my @as = split(/\s*,\s*/,$authors[$_]);
	    if ($#as == 1) { # Last, First -> First Last
		if ($check{'abbrev'}) {
		    if (!$isJ) {
			my @newas;
			foreach (split(/\s+/,$as[1])) { # First内をスペース分割
			    $_=~s/^(.).*$/\U$1\./; # 頭文字だけ残す
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
			    $_=~s/^(.).*$/\U$1\./;
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
			$_=~s/^(.).*$/\U$1\./;
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
	    $authors[$_] =~s/\\ss\{?\}?/\&szlig;/g;
	    $authors[$_] =~s/\\\"\{?([A-Za-z])\}?/\&\1uml;/g;
	    $authors[$_] =~s/\\\'\{?([A-Za-z])\}?/\&\1acute;/g;
	    $authors[$_] =~s/\\\`\{?([A-Za-z])\}?/\&\1grave;/g;
	    $authors[$_] =~s/\\\~\{?([A-Za-z])\}?/\&\1tilde;/g;
	    $authors[$_] =~s/\&Cacute;/\&\#262;/g;
	    $authors[$_] =~s/\&Sacute;/\&\#346;/g;
	    $authors[$_] =~s/\&Nacute;/\&\#323;/g;
	    $authors[$_] =~s/\&Zacute;/\&\#377;/g;
	    # see http://www.thesauruslex.com/typo/eng/enghtml.htm
	    $authors[$_] = "<a href=\"".$alink."A=$enc\">$ul1$authors[$_]$ul2</a>";
	} else {
	    $authors[$_] = "$ul1$authors[$_]$ul2";
	}
    }
    # 個々の著者の処理終わり

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
	if ($mode eq "list") {
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
    
# 各文献スタイルに応じた出力生成
    my $aline = "$strauth, ";

    my $jj = ($lang eq "en" && $$ent{'journal_e'} ne "") ? $$ent{'journal_e'} : $$ent{'journal'};

    my $lquot = "``";
    my $rquot = "''";

    $lquot = $rquot = "&#34;" if ($mode eq "list");

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
    } else {
	my $note = $$ent{'note'};
	$note .= ',' if ($note ne "");
	$aline .= "$t, $note $yy.";
    }

    if ($mode eq 'list') {
	if ($$ent{'year'} > 9999) {
	    $aline = "<span class=\"red\">".$aline."</span>";
	}
    }	

    if ($mode eq 'latex') {
	$aline=~s/\%/\\\%/g;
	$aline=~s/\_/\\\_/g;
	$aline=~s/\&/\\\&/g;
    }
    $$rbody .= $aline;
    
#    return $aline;
}

sub capitalizePaperTitle {
    my $string = shift; 
    my $alwaysLower = "A|AN|ABOUT|AMONG|AND|AS|AT|BETWEEN|BOTH|BUT|BY|FOR|FROM|IN|INTO|OF|ON|THE|THUS|TO|UNDER|WITH|WITHIN";

    my $mode = $session->param('MODE');

    # 日本語を含んでいたら数式処理のみ
    if (&isJapanese($$string) && $mode ne "latex") {
	if($use_mimetex) {
	    $$string=~s/\$([^\$]*)\$/<img class="math" src="${MIMETEXPATH}\?\1" \/>/g;
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
	    next if ($mode eq "latex") ; 
 	    if($use_mimetex) {
		$words[$i]=~s/\$([^\$]*)\$/<img class="math" src="${MIMETEXPATH}\?\1" \/>/g;
	    } else {
		$words[$i]=~s/\$([^\$]*)\$/\1/g;
	    }
	    next;
	}
	# {}に囲まれた部分はそのまま
	if ($words[$i]=~/\{([^\}]*)\}/) {
	    next if ($mode eq "latex") ; 
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

sub createAbibEntry {
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
		$vl = join(" and ",split(/,/,$vl));
	    }
	    $vl =~s/\&/\\\&/g;
	    $aline = "$fld = {$vl},\n";
	}
    } elsif ($fld eq "annote" && $vl ne "") {
	$vl =~s/\&/\\\&/g;
	$aline = "$fld = {$vl}\n";
    } elsif ($fld eq "year" && $vl ne "") {
	if ($isNeed ne "I") {
	    $aline = ($vl == 9999 ? "(to appear)": ($vl == 10000 ? "(submitted)":$vl));
	    $aline = "$fld = {$aline},\n";
	}
    } elsif ($fld =~ /_e$/) {
    } elsif ($vl ne "") {
	if ($isNeed ne "I") {
	    $vl =~s/\&/\\\&/g;
	    $vl =~s/\%/\\\%/g;
	    $aline = "$fld = {$vl},\n";
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
	$vl=~s/\$([^\$]*)\$/<img class="math" src="${MIMETEXPATH}\?\1" \/>/g if ($use_mimetex);
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
<textarea name="edit_$fld" rows="10" cols="80">
$vl
</textarea>
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
	if (grep(/^$fld$/,('author_e','title_e','author','title','howpublishd','month','year','note'))) {
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
    }
    &updateTagDB($session->param('ID'),$tags);

    my $key;
    $key = $cgi->param('edit_author_e') || $cgi->param('edit_key');
    my @a;
    if ($cgi->param('edit_author')=~/\s+and\s+/) {
	@a = split(/\s+and\s+/,$cgi->param('edit_author'));
    } else {
	@a = split(/\s*,\s*/,$cgi->param('edit_author'));
    }
    my @k;
    if ($key=~/\s+and\s+/) {
	@k = split(/\s+and\s+/,$key);
    } else {
	@k = split(/\s*,\s*/,$key);
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
    if ($fname ne "") {
	my $fh = $cgi->upload('edit_upfile');
	# MIMEタイプ取得
	#my $mimetype = $cgi->uploadInfo($fh)->{'Content-Type'};
	my $refdata = by_suffix($fh);
	my ($mimetype, $encoding) = @$refdata;
	my $file_contents = join('',<$fh>);	
	my $filedesc = $cgi->param('files_desc_new');
	if ($file_contents) {
	    my $a = grep(/new/,@faccess) ? 1 : 0;
	    &insertFileDB($fh,$mimetype,$file_contents,$a,$filedesc);
	}
    }
    $session->clear([grep(/edit_/,keys(%$sess_params))]);
    $session->clear([grep(/files_/,keys(%$sess_params))]);

    &expireCacheFromCDB;
    #redirect
    print $cgi->redirect("$scriptName?MODE=detail");

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

# 与えられたテキストからタグを抽出
# テキストにはtitleを仮定
sub createTags(){
    my ($title,$title_e) = @_;
    my $except = "A|AN|ABOUT|AMONG|AND|AS|AT|BETWEEN|BOTH|BUT|BY|FOR|FROM|IN|INTO|OF|ON|THE|THUS|TO|UNDER|USING|VS|WITH|WITHIN";
    $except .= "|NEW|BASED|ITS|APPROACH|APPROACHES|METHOD|METHODS|SYSTEM|SYSTEMS";

    if (&isJapanese($title)) {
	$title = $title_e;
    }
    $title =~s/[{}\$\_\:\'\`\(\)]//g;
    my @t ;
    foreach (split(/\s+/,$title)) {
	if ($_ !~ /^($except)$/i && $_ !~ /^-+$/) {
	    push(@t,lc($_));
	}
    }
    return join(",",@t);
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
    return $html;
    my $scrubber = HTML::Scrubber->new();
    return $scrubber->scrub($html);
}

# 日本語が含まれていれば1
sub isJapanese {
# utf-8での日本語判定ルーチン(下)がうまく動かないので，
# euc-jpへ変換して判定する．こっちのほうが確実と言えば確実．
    my ($str) = @_;
    utf8::encode($str);
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

exit(0);
