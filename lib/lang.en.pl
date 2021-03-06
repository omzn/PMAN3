use utf8;

our %bt = (
        "article"=>"An article from a journal or magazine (article)",
        "inproceedings" => "An article in a conference proceedings (inproceedings)",
        "book" => "A book with an explicit publisher (book)", 
        "incollection" => "A part of a book having its own title (incollection)", 
        "inbook" => "A part of a book, chapter and/or range (inbook)",
        "manual" => "Technical documentation (manual)", 
        "booklet" => "A work without a named publisher (booklet)", 
        "mastersthesis" => "A Master\'s thesis (mastersthesis)", 
        "phdthesis" => "A PhD thesis (phdthesis)",
        "proceedings" => "The proceedings of a conference (proceedings)",
        "techreport" => "A report published by a school or other institution (techreport)",
        "unpublished" => "A document not formally published (unpublished)",
        "misc" => "Nothing else (misc)", 
	);

#%viewMenu = (
#    "list"=>"<img src=\"css/img/vm-list.png\">",
#    "table"=>"<img src=\"css/img/vm-table.png\">",
#    "latex"=>"<img src=\"css/img/vm-latex.png\">",
#    "add"=>"<img src=\"css/img/vm-add.png\">",
#    "edit"=>"<img src=\"css/img/vm-edit.png\">",
#    "delete"=>"<img src=\"css/img/vm-delete.png\">",
#    );
our %viewMenu = (
    "list"=>  "List",
    "table"=> "Table",
    "latex"=> "LaTeX",
    "bbl"=>   "BibTeX",
    "graph"=> "Statistics",
    "add"=>   "Add",
    "bib"=>   "Add bib",
    "edit"=>  "Edit",
    "delete"=>"Delete",
    );

#%topMenu = (
#    "simple"=>"<img src=\"css/img/tm-simple.png\">",
#    "detail"=>"<img src=\"css/img/tm-detailed.png\">",
#    "japanese"=>"<img src=\"css/img/tm-japanese.png\">",
#    "english"=>"<img src=\"css/img/tm-english.png\">",
#    "login"=>"<img src=\"css/img/tm-login.png\">",
#    "logout"=>"<img src=\"css/img/tm-logout.png\">",
#    "config"=>"<img src=\"css/img/tm-config.png\">",
#    "help"=>"<img src=\"css/img/tm-help.png\">",
#    );
our %topMenu = (
    "simple"=>"Simple",
    "detail"=>"Advanced",
    "japanese"=>"Japanese",
    "english"=>"English",
    "login"=>"Login",
    "logout"=>"Logout",
    "category"=>"Category",
    "config"=>"Config",
    "help"=>"Help",
    );

our %msg = (
	"texname" => "Name",
	"texaffi" => "Affiliation",
	"textitl" => "Job title",
	"texnme" => "Input name",
	"texaff" => "Input affiliation",
	"texttl" => "Input job title",
	"needederr" => "Needed fields are not filled.<br>Please go back with browser button and retry.<br>Title field must be filled whenever.",
	"category" => "Category",
	"addcat" => "Add a category",
	"delcat" => "Delete a category",
	"rencat" => "Rename a category",

	"ordcat" => "Change order of category",
	"ordercat" => "Specify new order",
        "chgord" => "Change",
        "catname" => "Category",
        "order" => "Order",
        "neworder" => "New order (in integer)",

	"namenewcat" => "New category name",
	"selectdelcat" => "Select a category to delete",
        "selectmovcat" => "Select a category to which works in deleted category will move",
    
	"selectcat" => "Select a category",
	"del" => "Delete",
	"add" => "Add",
	"efile" => "Electronic file",
	"ed" => "Ed.",
        "save" => "Save",
	"makePDF" => "PDF",
	"listPDF" => "List of Works (PDF)",
	"editcat" => "Edit category",
	"uploadfile" => "File to upload",
	"doEdit" => "Update",
	"selectType" => "Select type of a work",
	"editContents" => "Edit contents",
	"addNew" => "Add this work",
	"import" => "Import",
	"export" => "Export",
	"imex" => "Import/Export",
	"langconf"=>"Language Setting",
	"japanese"=>"Japanese",
	"english"=>"English",
	"all"=>"All",
	"author"=>"Author",
	"1stauthor"=>"First author",
	"title"=>"Title",
	"publish"=>"Journal/Conference",
	"year"=>"Year",
	"filter"=>"Filter",
	"found" => "publications are found.",
	"ascend" => "Ascend by date",
	"descend" => "Descend by date",
	"t_ascend" => "Ascend by date (categ'd)",
	"t_descend" => "Descend by date (categ'd)",
	"y_t_ascend" => "Ascend by date (categ'd by year)",
	"y_t_descend" => "Descend by date (categ'd by year)",
	"ffdetail" => "Detail",       
	"ffsimple" => "Simple",       
	"URL" => "URL for this page.",
	"detailviewTitle"=>"Detailed view",
	"editTitle"=>"Edit data",
	"addTitle"=>"Add data",
	"configTitle"=>"Configuration",
	"importTitle"=>"Import data",
	"neededErrorTitle"=>"Error: Needed field(s)",
	"askPasswdTitle"=>"Password authentication",
	"askPasswd"=>"Please input password for editing:",
	"auth"=>"Authenticate",

        "faccess"=>"Available only for login user.",
        "open"=>"[Open]",
        "hidden"=>"[Hidden]",
        "filedesc"=>"Description",

	#Add by Manabe
	"clrcookie"=>"Init cookie",
	"misc"=>"Misc.",

	"need" => "[NEEDED]",
	"altneed" => "[ALTERNATIVELY NEEDED]",

        "accepted" => "(accepted, to appear)",
        "submitted" => "(submitted)",

	"Head_address" => "Address (address)",
	"Exp_address" => "Usually the address of the publisher or other type of institution.",
	"Head_annote"=>"Annote (annote)",
	"Exp_annote"=>"An annotation. It is not used by the standard bibliography styles.",
	"Head_author"=>"Author (author)",
	"Exp_author"=>"The name(s) of the author(s). Separate each name by comma(,) or 'and'.",
	"Head_author_e"=>"Author in English",
	"Exp_author_e"=>"If author is specified in Japanese, fill in name(s) of the author(s) in English here.",
	"Head_abstract"=>"Abstract",
	"Head_booktitle"=>"Title of Book or Proceedings (booktitle)",
	"Exp_booktitle"=>"Title of a book, part of which is being cited.",
	"Head_booktitle_e"=>"Title of Book or Proceedings in English",
	"Exp_booktitle_e"=>"If booktitle is specified in Japanese, fill in booktitle in English here.",
	"Head_chapter"=>"Chapter (chapter)",
	"Exp_chapter"=>"A chapter (or section or whatever) number. ",
	"Head_edition"=>"Edition (edition)",
	"Exp_edition"=>"The edition of a book---for example, ``Second''.",
	"Head_editor"=>"Editor (editor)",
	"Exp_editor"=>"The name(s) of the editor(s). Separate each name by comma(,) or 'and'.",
	"Head_editor_e"=>"Editor in English",
	"Exp_editor_e"=>"If editor is specified in Japanese, fill in name(s) of the editor(s) in English here.",
	"Head_howpublished"=>"How published (howpublished)",
	"Exp_howpublished"=>"How something strange has been published.",
	"Head_institution"=>"Institution (institution)",
	"Exp_institution"=>"The sponsoring institution of a technical report.",
	"Head_journal"=>"Journal (journal)",
	"Exp_journal"=>"A journal name.",
	"Head_journal_e"=>"Journal name in English",
	"Exp_journal_e"=>"If journal is not specified in English, fill in journal name in English here.",
	"Head_key"=>"Key (key)",
	"Exp_key"=>"Used for alphabetizing, cross referencing, and creating a label when the ``author'' information is missing. (Local rule: If author names are in Japanese, fill in English name here.)",
	"Head_month"=>"Month (month)",
	"Exp_month"=>"The month in which the work was published",
	"Head_note"=>"Note (note)",
	"Exp_note"=>"Any additional information that can help the reader. (Local rule: Fill in place of conference held.)",
	"Head_number"=>"Number (number)",
	"Exp_number"=>"The number of a journal, magazine, technical report.",
	"Head_organization"=>"Organization (organization)",
	"Exp_organization"=>"The organization that sponsors a conference or that publishes a manual.",
	"Head_pages"=>"Pages (pages)",
	"Exp_pages"=>"One or more page numbers or range of numbers, such as 42--111 or 7,41,73--97 or 43+.",
	"Head_publisher"=>"Publisher (publisher)",
	"Exp_publisher"=>"The publisher's name.",
	"Head_publisher_e"=>"Publisher in English",
	"Exp_publisher_e"=>"If the publisher's name is not specified in English, fill in English here.",
	"Head_school"=>"School (school)",
	"Exp_school"=>"The name of the school where a thesis was written.",
	"Head_series"=>"Series (series)",
	"Exp_series"=>"The name of a series or set of books.",
	"Head_style"=>"Bib style (\@...)",
	"Exp_style"=>"A style for the publication.",
	"Head_title"=>"Title (title)",
	"Exp_title"=>"The work's title.",
	"Head_title_e"=>"Title in English",
	"Exp_title_e"=>"If the work's title is not specified in English, fill in English here",
	"Head_type"=>"Type (type)",
	"Exp_type"=>"The type of a technical report---for example, ``Research Note''. ",
	"Head_volume"=>"Volume (volume)",
	"Exp_volume"=>"The volume of a journal or multi-volume book.",
	"Head_year"=>"Year (year)",
	"Exp_year"=>"The year of publication.",
	"Head_acceptance"=>"Acceptance rate",
	"Exp_acceptance"=>"Acceptance rate of the conference.",
	"Head_impactfactor"=>"Impact factor (JCR)",
	"Exp_impactfactor"=>"Journal's impact factor.",
	"Head_bibent"=>"BiBTeX entry",
	"Head_url"=>"URL",
	"Exp_url"=>"URL for this publication",
	"Head_enterbib"=>"Bib entry",
	"Exp_enterbib"=>"Describe Bib entries. Above category is applied to all entries. Electronic file is only attatched to the first entry. Tags are appended to each entry.",

	"volnum"=>"Volume / Number",
	"ifacc"=>"Impact factor / Acceptance",
        "yearmonth"=>"Published date",
           
        "Title_list"=>"List of publications",
        "Title_table"=>"Table of publications",
        "Title_latex"=>"LaTeX of publications",
        "Title_bbl"=>"BibTeX of publications",
        "Title_graph"=>"Statistics of publications",
        "Title_detail"=>"Detail of a publication",
        "Title_edit"=>"Edit a publication",
        "Title_add"=>"Add a publication",
        "Title_bib"=>"Add publications from bib",
        "Title_category"=>"Modify categories",

        "deleteConfirm"=>"Are you sure to delete this publication?",
        "fileDeleteConfirm"=>"Are you sure to delete this file?",

        "tags"=>"Tags",
        "filedelete"=>"Delete file",

        "showUL"=>"Show underline on searched authors.",
        "showAbbrev"=>"Show abbrev. authors.",
        "showShortVN"=>"Show Vol./Num. in short.",
        "showJCR"=>"Show the impact factor and acceptance rate.",
        "showNote"=>"Show location info(note).",

        "frequenttags"=>"Frequent tags in this search: ",

        "notavailable"=>"Not available.",
        "nothingfound"=>"No publication is found.",

        "Title_config" => "Option Configuration",       
    "tagsetting"=>"Tag setting",
    "tag_rebuild"=>"Rebuild tags",
    "tag_rebuild_exp"=>"Rebuild tag database for all bibs. Current tags are deleted. Be careful!",
    "rebuild"=>"Rebuild",
    "tag_merge"=>"Merge tags",
    "tag_merge_exp"=>"Rebuild tag database for all bibs. Currennt tags remain and merged.",
    "merge"=>"Merge",
    "tag_remove"=>"Remove tags from DB",
    "tag_remove_exp"=>"Specify tags separated by space to remove from the tag DB.",
    "addstoptag"=>"Add stop tags",
    "tag_stoptaglist"=>"Edit stop tags",
    "tag_stoptaglist_exp"=>"These words are excluded from auto generation of tags.",

    "cachesetting"=>"Cache setting",
    "cache_delete"=>"Expire cache",
    "cache_delete_exp"=>"Force to expire page caches.",

    "optionsetting"=>"Feature settings",

    "use_cache"=>"Page cache",
    "use_cache_exp"=>"Enables page cache feature.",
    "use_DBforSession"=>"Session DB",
    "use_DBforSession_exp"=>"Enables database for session management.",
    "use_AutoJapaneseTags"=>"Auto generation of Japanese tags",
    "use_AutoJapaneseTags_exp"=>"Enables auto Japanese tag generation feature. (Requires Text::Mecab module and mecab.)",
    "use_RSS"=>"RSS feed",
    "use_RSS_exp"=>"Enables RSS feed feature. (Requires XML::RSS module.)",

    "use_XML"=>"XML output",
    "use_XML_exp"=>"Enable XML output feature. (Requires XML::Simple module.)",

    "use_highcharts"=>"Support <a href=\"http://www.highcharts.com\" target=\"_blank\">highcharts</a>",
    "use_highcharts_exp"=>"Enable <a href=\"http://www.highcharts.com\" target=\"_blank\">highchart</a> support.",

    "use_mathjaxtex"=>"Support <a href=\"http://www.mathjax.org/\" target=\"_blank\">MathJax</a>",
    "use_mathjax_exp"=>"Enable <a href=\"http://www.mathjax.org/\" target=\"_blank\">MathJax</a> support. Formulas are shown in TeX format by MathJax.",

    "set_passwd"=>"Password setting",
    "set_passwd_exp"=>"Set password for administrator.",
    "set_auth_ldap"=>"LDAP authentication setting",
    "set_auth_ldap_exp"=>"Use LDAP to authenticate PMAN",
    "set_auth_ldap_host"=>"LDAP authentication server",
    "set_auth_ldap_host_exp"=>"Specify LDAP server hostname.",
    "set_auth_ldap_baseDN"=>"LDAP search base DN",
    "set_auth_ldap_baseDN_exp"=>"Specify LDAP search base DN for users information.",

    "set_titleofsite"=>"Site title",
    "set_titleofsite_exp"=>"Specify site's title.",
    "set_maintainername"=>"Maintainer's name",
    "set_maintainername_exp"=>"Specify maintainer's name.",
    "set_maintaineraddress"=>"Maintainer's address",
    "set_maintaineraddress_exp"=>"Specify maintainer's address (URL).",

    "texsetting"=>"LaTeX settings",
    "set_texHeader"=>"LaTeX header",
    "set_texHeader_exp"=>"LaTeX document header for LaTeX mode.",
    "set_texFooter"=>"LaTeX footer",
    "set_texFooter_exp"=>"LaTeX document footer for LaTeX mode.",

    "adminsetting"=>"Administrator settings",

    "use_latexpdf"=>"PDF online generation",
    "use_latexpdf_exp"=>"Generate PDF file from LaTeX mode online. To use this mode, specify following two commands to be run on the web server.",
    "set_latexcmd"=>"LaTeX command",
    "set_latexcmd_exp"=>"Specify latex command. (ex. platex)",
    "set_dvipdfcmd"=>"DVIPDF command",
    "set_dvipdfcmd_exp"=>"Specify command to generate PDF file from DVI. (ex. dvipdfmx -V 4)",

    "latex_exp"=>"Copy the contents in the following text field and paste it to text editor. <br />If online PDF construction is allowed in this system, you can get PDF file from a link named 'PDF' somewhere in this page.",

    'tmpl' => 'Select skin',
    'tmpl_exp' => 'Select your favorite skins. You can <a href="http://se.is.kit.ac.jp/~o-mizuno/pman3download.html">download</a> several skins from <a href="http://se.is.kit.ac.jp/~o-mizuno/pman3download.html">PMAN3 website</a>.',

    "use"=>"Use",
    "dontuse"=>"Don't use",

    "notInstalled"=>"Not installed",

    "set_title_list"=>"Header of list mode",
    "set_title_list_exp"=>"Specify a header of list mode.",
    "set_title_table"=>"Header of table mode",
    "set_title_table_exp"=>"Specify a header of table mode.",
    "set_title_latex"=>"Header of LaTeX mode",
    "set_title_latex_exp"=>"Specify a header of LaTeX mode.",
    "set_title_bbl"=>"Header of BibTeX mode",
    "set_title_bbl_exp"=>"Specify a header of BibTeX mode.",
    "set_title_detail"=>"Header of detail mode",
    "set_title_detail_exp"=>"Specify a header of detail mode.",,

    "numPapersYear"=>"Number of publications for each year",
    "numPapersYear"=>"Number of publications for each type",
    "stackedType"=>"Types stacked",
    "numOfPub"=>"Number of publications",
    "tagdist"=>"Distribution of top 30 tags",
    "authordist"=>"Distribution of authors",
    "authorTransition"=>"Trend of top 10 frequent author appearance",

    "path_highcharts"=>"Path to highcharts.js",

    "path_highcharts_exp"=>"From <a href=\"http://www.higicharts.com/download/\" target=\"_blank\">Highcharts.com</a>, you can download zip archive of highcharts. In the archive, you will find 'js' directory. Rename 'js' directory to 'highcharts', and place under lib/. You can see highcharts.js, modules/, and themes/ under lib/highcharts.",
    "theme_highcharts"=>"Theme of Highcharts",
    "theme_highcharts_exp"=>"Select a theme for highcharts.",

	);

1;

