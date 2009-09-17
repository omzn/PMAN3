#!/usr/bin/perl
use DBI;
#use Lingua::EN::Keywords;
use MIME::Types qw/by_suffix/;
use Encode;

if (!($ARGV[0] && $ARGV[1] && $ARGV[2])) {
    die "usage: convertDB.pl PMAN2.x_bibdat.csv PMAN2.x_category.txt pdf_directory";
}

my $dbh = DBI->connect("dbi:SQLite:dbname=db/bibdat.db", undef, undef, {AutoCommit => 0, RaiseError => 1 });
$dbh->{unicode} = 1;

my $databaseFile = $ARGV[0];
@db = ();
open(PDB,$databaseFile) || die "no such file";
my $i = 1;

my %a_names;

while (<PDB>) {
    my $tmp = $_;
    $tmp =~ s/(?:\x0D\x0A|[\x0D\x0A])?$/,/;
    my @values = map {/^"(.*)"$/ ? scalar($_ = $1, s/""/"/g, $_) : $_}
                ($tmp =~ /("[^"]*(?:""[^"]*)*"|[^,]*),/g);  #"

    print "$i\n";

    for (my $j=0;$j<=$#values;$j++) {
	Encode::from_to($values[$j],"euc-jp","utf-8");
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
	    my $refdata =  by_suffix($values[3]);
	    my ($mediatype, $encoding) = @$refdata;
	    $sth = $dbh->prepare("INSERT INTO files VALUES(null,?,?,?,?,?)");
	    open(IN,"$ARGV[2]/$values[3]");
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

	my $tags = &createTags($values[7],$values[28]);
	print $tags."\n";
	if ($tags) {
	    foreach (split(/,/,$tags)) {
		$sth = $dbh->prepare("INSERT INTO tags VALUES(null,?,?)");
		$sth ->execute($i,$_); 
	    }
	}
	    
	$dbh->commit;
	$i++;
	
    }; 

    if ($@) { 
	$dbh->rollback; $dbh->disconnect; 
	die "Error: $@";
    }

}

my $optionFile = $ARGV[1];
open(OPT,$optionFile);
my $line = <OPT>;
close(OPT,$optionFile);
$line =~s/\s*$//;
Encode::from_to($line, "euc-jp", "utf-8");
%jlist = split(/\t/,$line);

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
	die "Error: $@";
    }
} 


print "\n";

$dbh->disconnect or warn $!;

exit 0;

sub createTags(){
    my ($title,$title_e) = @_;
    my $except = "A|AN|ABOUT|AMONG|AND|AS|AT|BETWEEN|BOTH|BUT|BY|FOR|FROM|IN|INTO|OF|ON|THE|THUS|TO|UNDER|USING|VS|WITH|WITHIN";
    $except .= "|NEW|BASED|ITS|APPROACH|METHOD|SYSTEM|SYSTEMS";

    if (&isJapanese($title)) {
	$title = $title_e;
    }
    $title =~s/\s*$//;
    $title =~s/[{}\$\_\:\'\`\(\)]//g;
    my @t ;
    foreach (split(/\s+/,$title)) {
	if ($_ !~ /^($except)$/i && $_ !~ /^-+$/) {
	    push(@t,lc($_));
	}
    }
    return join(",",@t);
}

# EUCÈÇ
sub isJapanese {
    my ($str) = @_;
    if ($str =~ /[\xA1-\xFE][\xA1-\xFE]/) {
	return 1;
    } else {
	return 0;
    }
}

#sub createTags2(){
#    my ($title,$title_e) = @_;
#    if ($title =~/[\xA1-\xFE][\xA1-\xFE]/) {
#	$title = $title_e;
#    }
#    $title =~s/[{}\$\_\:\'\`\(\)]//g;
#    $title =~s/\s*$//;
#    return join(",",keywords($title));
#}


